import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

from familydb.app import App
from familydb.store import db, ideas
from familydb.tools import ToolContext, ToolRegistry


def _call(registry: ToolRegistry, ctx: ToolContext, name: str, **payload):
    result = registry.dispatch(name, payload, ctx)
    return result, json.loads(result.content)


def test_add_idea_infers_defaults_and_attributes_to_sender(registry, ctx) -> None:
    result, data = _call(
        registry,
        ctx,
        "add_idea",
        title="Ramen place on Main St",
        kind="Restaurant",
        tags=["Food"],
        participants=["whole family"],
    )
    assert not result.is_error
    assert result.summary == {"tool": "add_idea", "ok": True, "id": data["id"]}
    assert data["kind"] == "restaurant"
    assert data["tags"] == ["food"]
    assert data["suggested_by_name"] == "Sam"
    assert data["enrichment"] == "pending"
    assert data["status"] == "idea"


def test_add_idea_with_named_suggester_and_kid_participants(registry, ctx) -> None:
    _, data = _call(
        registry,
        ctx,
        "add_idea",
        title="Hopscotch, Portland",
        kind="outing",
        participants=["with the girls"],
        location_name="Portland",
        suggested_by="alex",
    )
    assert data["suggested_by_name"] == "Alex"
    assert data["participants"] == ["with the girls"]
    result, data = _call(registry, ctx, "add_idea", title="X", kind="other", suggested_by="Nobody")
    assert result.is_error and "no family member" in data["error"]


def test_add_idea_reports_duplicates_instead_of_adding(registry, ctx) -> None:
    _, first = _call(registry, ctx, "add_idea", title="Ramen place on Main St", kind="restaurant")
    result, data = _call(registry, ctx, "add_idea", title="ramen place on Main Street", kind="food")
    assert not result.is_error
    assert data["duplicate_of"] == first["id"]
    assert result.summary["duplicate_of"] == first["id"]
    assert len(ideas.list_all(ctx.conn)) == 1


def test_update_and_describe_idea(registry, ctx) -> None:
    _, created = _call(registry, ctx, "add_idea", title="The falls hike", kind="outing")
    result, updated = _call(
        registry,
        ctx,
        "update_idea",
        id=created["id"],
        status="planned",
        tags=["hike", "Kids"],
        duration_min=120,
    )
    assert not result.is_error
    assert updated["status"] == "planned"
    assert updated["tags"] == ["hike", "kids"]
    result, data = _call(registry, ctx, "update_idea", id=created["id"])
    assert result.is_error and "nothing to change" in data["error"]
    result, data = _call(registry, ctx, "update_idea", id=999, status="dropped")
    assert result.is_error and "no idea #999" in data["error"]
    _, described = _call(registry, ctx, "describe_idea", id=created["id"])
    assert described["idea"]["title"] == "The falls hike"
    assert described["place"] is None
    assert described["outcomes"] == []


def test_search_ideas_returns_compact_lines(registry, ctx) -> None:
    _call(
        registry, ctx, "add_idea", title="Ramen place on Main St", kind="restaurant", tags=["food"]
    )
    _call(registry, ctx, "add_idea", title="The falls hike", kind="outing", setting="outdoor")
    _, everything = _call(registry, ctx, "search_ideas")
    assert everything["count"] == 2
    assert everything["ideas"][0].startswith("#1 | [restaurant] | Ramen place on Main St")
    _, hikes = _call(registry, ctx, "search_ideas", text="hike", limit=500)
    assert hikes["count"] == 1 and "falls hike" in hikes["ideas"][0]
    _, indoor = _call(registry, ctx, "search_ideas", setting="indoor")
    assert indoor["count"] == 1  # the hike is outdoor-only; the restaurant defaults to 'either'


def test_simultaneous_edits_only_commit_one_revision(settings, conn, clock, family):
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Museum", kind="outing")
    seen = ideas.revision(idea)
    barrier = threading.Barrier(2)
    app = App(settings, clock)

    def edit(title):
        with closing(app.connect()) as own:
            ctx = ToolContext(own, settings, clock, idea_revision=seen)
            barrier.wait(timeout=10)
            return app.registry.dispatch("update_idea", {"id": idea.id, "title": title}, ctx)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["First edit", "Second edit"]))
    assert sum(not result.is_error for result in results) == 1


def test_an_idea_keeps_the_ages_it_suits(registry, ctx) -> None:
    from familydb.agent.render import render_idea_line

    _, data = _call(registry, ctx, "add_idea", title="Trampoline park", kind="activity", min_age=6)
    assert data["min_age"] == 6 and data["max_age"] is None
    assert "| ages 6+ |" in render_idea_line(ideas.get(ctx.conn, data["id"]))
    # The oldest is checked against the youngest it already has.
    refused, said = _call(registry, ctx, "update_idea", id=data["id"], max_age=4)
    assert refused.is_error and said["error"] == "min_age 6 is over max_age 4"
    _, data = _call(registry, ctx, "update_idea", id=data["id"], max_age=12)
    assert "| ages 6-12 |" in render_idea_line(ideas.get(ctx.conn, data["id"]))
    refused, said = _call(registry, ctx, "add_idea", title="Odd", kind="other", min_age=-1)
    assert refused.is_error and said["error"] == "an age is 0 to 120"


def test_an_idea_keeps_only_durations_that_can_be(registry, ctx) -> None:
    refused, said = _call(
        registry, ctx, "add_idea", title="Odd walk", kind="outing", duration_min=-30
    )
    assert refused.is_error and said["error"] == "a duration is in minutes, at least 1"
    refused, said = _call(
        registry, ctx, "add_idea", title="Odd walk", kind="outing", duration_min=90, duration_max=60
    )
    assert refused.is_error and said["error"] == "duration_min 90 is over duration_max 60"
    refused, said = _call(
        registry, ctx, "add_idea", title="Odd walk", kind="outing", lead_time_days=-2
    )
    assert refused.is_error and "0 or more" in said["error"]
    assert ideas.find_similar_title(ctx.conn, "Odd walk") is None
    _, data = _call(registry, ctx, "add_idea", title="Falls walk", kind="outing", duration_min=60)
    # The longest is checked against the shortest it already has, and nothing is saved.
    refused, said = _call(registry, ctx, "update_idea", id=data["id"], duration_max=30)
    assert refused.is_error and said["error"] == "duration_min 60 is over duration_max 30"
    assert ideas.get(ctx.conn, data["id"]).duration_max is None
    _, data = _call(registry, ctx, "update_idea", id=data["id"], duration_max=120)
    assert (data["duration_min"], data["duration_max"]) == (60, 120)


def _looked_up(ctx: ToolContext, idea_id: int, name: str) -> int:
    from familydb.store import places

    with db.transaction(ctx.conn):
        place = places.insert(ctx.conn, name=name, now="2026-09-01T00:00:00Z", lat=49.2, lon=-123.1)
        ideas.update(
            ctx.conn,
            idea_id,
            {"place_id": place.id, "enrichment": "done", "enriched_at": "2026-09-01T00:00:00Z"},
        )
    return place.id


def test_another_branch_lets_go_of_the_old_places_facts(registry, ctx) -> None:
    from familydb.store import places

    _, data = _call(
        registry,
        ctx,
        "add_idea",
        title="Dumpling house",
        kind="restaurant",
        location_name="Old branch",
        description="the soup ones",
        cost_level=1,
    )
    old_place = _looked_up(ctx, data["id"], "Old branch")
    # Said again as it was (the page's form sends it every time): nothing to look up again.
    _, same = _call(registry, ctx, "update_idea", id=data["id"], location_name=" old  Branch")
    assert same["place_id"] == old_place and same["enrichment"] == "done"
    moved_call, moved = _call(
        registry, ctx, "update_idea", id=data["id"], location_name="New branch"
    )
    assert moved["place_id"] is None
    assert moved["enrichment"] == "pending" and moved["enriched_at"] is None
    # What the family said of it stands, and the old place is still the old place.
    assert moved["description"] == "the soup ones" and moved["cost_level"] == 1
    assert places.get(ctx.conn, old_place).name == "Old branch"
    # Undo puts the old place back with the old name.
    ctx.undo_target = moved_call.call_id
    result = registry.dispatch("undo", {}, ctx)
    assert not result.is_error, result.content
    back = ideas.get(ctx.conn, data["id"])
    assert back.place_id == old_place and back.location_name == same["location_name"]


def test_a_recipe_given_a_place_keeps_its_reading(registry, ctx) -> None:
    _, data = _call(registry, ctx, "add_idea", title="Mum's dal", kind="recipe")
    _, changed = _call(registry, ctx, "update_idea", id=data["id"], location_name="Grandma's")
    assert changed["enrichment"] == "skipped"
