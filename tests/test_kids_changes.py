"""What a kid may change by asking the bot: add an idea, remember something and her own to-dos;
never edit an idea, say how a plan went or make, move or cancel a plan (docs/DESIGN.md, section
16). The tools are declared the same for everyone; dispatch refuses (tools/registry.py `needs`)."""

from __future__ import annotations

import dataclasses
import json

from familydb.store import ideas, outcomes, plans
from familydb.tools.registry import NOT_THEIRS


def _call(registry, ctx, name, **payload):
    result = registry.dispatch(name, payload, ctx)
    return result, json.loads(result.content)


def test_a_kid_may_add_an_idea_and_remember_but_not_change_the_households_plans(
    registry, ctx, conn, family
) -> None:
    _, idea = _call(registry, ctx, "add_idea", title="Silver Falls hike", kind="outing")
    _, made = _call(registry, ctx, "create_event", title="Hike", start="2026-09-26T10:00")
    plan_id = made["plan"]["id"]
    kid = dataclasses.replace(ctx, member=family["girls"])

    added, _ = _call(registry, kid, "add_idea", title="Mini golf", kind="activity")
    assert not added.is_error
    kept, _ = _call(
        registry,
        kid,
        "remember",
        changes=[{"action": "add", "about": "the girls", "category": "food", "fact": "vegetarian"}],
    )
    assert not kept.is_error

    refused = [
        _call(registry, kid, "update_idea", id=idea["id"], title="Renamed"),
        _call(registry, kid, "record_outcome", idea_id=idea["id"], rating=9),
        _call(registry, kid, "create_event", title="Zoo", start="2026-09-27T10:00"),
        _call(registry, kid, "update_event", plan_id=plan_id, title="Moved"),
        _call(registry, kid, "delete_event", plan_id=plan_id),
    ]
    for result, data in refused:
        assert result.is_error and data == {"error": NOT_THEIRS}
    # Nothing moved.
    assert ideas.get(conn, idea["id"]).title == "Silver Falls hike"
    assert outcomes.list_for_idea(conn, idea["id"]) == []
    assert [plan.title for plan in plans.everything(conn)] == ["Hike"]
    assert plans.get(conn, plan_id).status != "cancelled"
    # And what the model is told leaves out how the bot works.
    for word in ("role", "permission", "settings", "model", "tool"):
        assert word not in NOT_THEIRS


def test_a_parent_a_job_and_the_shared_password_still_change_things(
    registry, ctx, conn, family
) -> None:
    _, idea = _call(registry, ctx, "add_idea", title="Silver Falls hike", kind="outing")
    for member in (family["alex"], None):  # a parent; a job, the command line, the shared password
        who = dataclasses.replace(ctx, member=member)
        result, _ = _call(registry, who, "update_idea", id=idea["id"], title="Silver Falls")
        assert not result.is_error


def test_every_turn_is_declared_the_same_tools_and_none_says_who_may_use_it(registry) -> None:
    declared = registry.tool_defs()
    assert {"update_idea", "record_outcome", "create_event"} <= {tool.name for tool in declared}
    five = [tool for tool in declared if registry.get(tool.name).needs]
    assert len(five) == 5 and not any("needs" in vars(tool) for tool in five)
