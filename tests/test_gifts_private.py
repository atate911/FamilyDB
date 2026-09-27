"""Presents stay a surprise: kept out of the prompt every chat shares, and from the kids' tools."""

from __future__ import annotations

import json

from familydb.agent.prompt import chat_prefix
from familydb.store import db, ideas
from familydb.tools.registry import ToolContext
from tests.conftest import NOW_ISO


def _run(registry, name, values, ctx):
    result = registry.dispatch(name, values, ctx)
    output = json.loads(result.content)
    return {"error": output} if result.is_error else output


def _gift_and_outing(conn):
    with db.transaction(conn):
        gift = ideas.insert(
            conn, title="Roller skates", kind="gift", participants=["the girls"], now=NOW_ISO
        )
        outing = ideas.insert(conn, title="Zoo lights", kind="outing", now=NOW_ISO)
    return gift, outing


def test_the_shared_prompt_lists_no_presents(conn, settings, family) -> None:
    _gift_and_outing(conn)
    *_, idea_list = chat_prefix(conn, settings)
    assert "Zoo lights" in idea_list and "Roller skates" not in idea_list


def test_a_kid_cannot_find_a_present_but_a_parent_can(
    conn, settings, clock, family, registry
) -> None:
    gift, _ = _gift_and_outing(conn)
    kid = ToolContext(conn=conn, settings=settings, clock=clock, member=family["girls"])
    parent = ToolContext(conn=conn, settings=settings, clock=clock, member=family["alex"])

    found = _run(registry, "search_ideas", {}, kid)
    assert found["count"] == 1 and "Roller skates" not in str(found)
    assert "Roller skates" in str(_run(registry, "search_ideas", {"kind": "gift"}, parent))

    described = _run(registry, "describe_idea", {"id": gift.id}, kid)
    assert "error" in described and "Roller skates" not in str(described)
    assert _run(registry, "describe_idea", {"id": gift.id}, parent)["idea"]["id"] == gift.id

    changed = _run(registry, "update_idea", {"id": gift.id, "title": "Skates!"}, kid)
    assert "error" in changed and ideas.get(conn, gift.id).title == "Roller skates"

    again = _run(registry, "add_idea", {"title": "Roller skates", "kind": "gift"}, kid)
    assert "error" in again and "Roller skates" not in str(again.get("idea", ""))
