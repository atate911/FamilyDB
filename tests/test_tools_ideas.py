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
