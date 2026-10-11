"""What the family says of something she found (docs/FINDS.md): saved as an idea, or not for
them; either taken back by undo, and a kid may do neither for everyone."""

from __future__ import annotations

import json

from familydb.store import db, finds, ideas, messages
from familydb.tools import ToolContext, build_registry
from familydb.tools.registry import NOT_THEIRS
from tests.conftest import NOW_ISO

REGISTRY = build_registry()


def _as(settings, clock, conn, member, update: str) -> ToolContext:
    with db.transaction(conn):
        said = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=update,
            chat_id="42",
            member_id=member.id,
            text="…",
            now=NOW_ISO,
        )
    return ToolContext(conn=conn, settings=settings, clock=clock, member=member, message_id=said.id)


def _run(ctx: ToolContext, name: str, **args):
    result = REGISTRY.dispatch(name, args, ctx)
    return result, json.loads(result.content)


def _found(conn, *titles: str) -> list[finds.Find]:
    with db.transaction(conn):
        kept, _ = finds.keep(
            conn,
            "request",
            "request",
            [
                finds.NewFind(title=title, url=f"https://example.org/{n}")
                for n, title in enumerate(titles)
            ],
            now=NOW_ISO,
        )
    return kept


def test_saving_a_find_makes_it_an_idea_and_undo_offers_it_again(settings, clock, conn, family):
    [market] = _found(conn, "Night market")
    sam = family["sam"]
    result, idea = _run(
        _as(settings, clock, conn, sam, "u1"),
        "add_idea",
        title="Night market",
        kind="outing",
        find_id=market.id,
    )
    assert not result.is_error
    saved = finds.get(conn, market.id)
    assert (saved.state, saved.idea_id) == ("saved", idea["id"])
    _, undone = _run(_as(settings, clock, conn, sam, "u2"), "undo")
    assert "undone" in undone
    assert ideas.get(conn, idea["id"]).status == "dropped"
    back = finds.get(conn, market.id)
    assert (back.state, back.idea_id, back.saved_at) == ("new", None, None)


def test_an_idea_saved_by_its_page_or_title_links_the_find(settings, clock, conn, family):
    market, choir = _found(conn, "Night market", "Choir")
    ctx = _as(settings, clock, conn, family["sam"], "u1")
    _, by_page = _run(
        ctx, "add_idea", title="The market", kind="outing", url="https://EXAMPLE.org/0"
    )
    _, by_title = _run(ctx, "add_idea", title="choir", kind="show")
    assert finds.get(conn, market.id).idea_id == by_page["id"]
    assert finds.get(conn, choir.id).idea_id == by_title["id"]
    result, said = _run(ctx, "add_idea", title="Zoo", kind="outing", find_id=999)
    assert result.is_error and said["error"] == "no find 999"


def test_not_for_us_by_title_stops_her_offering_it_until_undone(settings, clock, conn, family):
    market, _ = _found(conn, "Night market", "Night market tour")
    sam = family["sam"]
    ctx = _as(settings, clock, conn, sam, "u1")
    result, said = _run(ctx, "pass_find", title="night")
    assert result.is_error and "name its number" in said["error"]
    result, said = _run(ctx, "pass_find", title="Night Market!", why="too late for the girls")
    assert not result.is_error and said == {
        "find_id": market.id,
        "title": "Night market",
        "passed": True,
    }
    passed = finds.get(conn, market.id)
    assert (passed.state, passed.passed_by, passed.passed_why) == (
        "passed",
        sam.id,
        "too late for the girls",
    )
    _, undone = _run(_as(settings, clock, conn, sam, "u2"), "undo")
    assert undone == {"undone": "passed on Night market"}
    assert finds.get(conn, market.id).state == "new"


def test_a_kid_may_not_pass_on_a_find_for_everyone(settings, clock, conn, family):
    [market] = _found(conn, "Night market")
    result, said = _run(
        _as(settings, clock, conn, family["girls"], "u1"), "pass_find", find_id=market.id
    )
    assert result.is_error and said == {"error": NOT_THEIRS}
    assert finds.get(conn, market.id).state == "new"


def test_a_saved_find_is_not_passed_on_but_its_idea_dropped(settings, clock, conn, family):
    [market] = _found(conn, "Night market")
    ctx = _as(settings, clock, conn, family["sam"], "u1")
    _, idea = _run(ctx, "add_idea", title="Night market", kind="outing", find_id=market.id)
    result, said = _run(ctx, "pass_find", find_id=market.id)
    assert result.is_error and f"idea #{idea['id']}" in said["error"]
