import json

from familydb.tools import ToolContext, ToolRegistry


def _call(registry: ToolRegistry, ctx: ToolContext, tool_name: str, payload=None, **fields):
    result = registry.dispatch(tool_name, {**(payload or {}), **fields}, ctx)
    return result, json.loads(result.content)


def test_record_outcome_updates_idea(registry, ctx) -> None:
    _, idea = _call(registry, ctx, "add_idea", title="Ramen place on Main St", kind="restaurant")
    result, data = _call(
        registry,
        ctx,
        "record_outcome",
        idea_id=idea["id"],
        rating=8,
        would_repeat=True,
        happened_on="2026-09-19",
        notes="great broth",
    )
    assert not result.is_error
    assert data["idea"]["times_done"] == 1
    assert data["idea"]["avg_rating"] == 8.0
    assert data["idea"]["status"] == "done"
    assert data["outcome"]["recorded_by"] == ctx.member.id
    result, data = _call(registry, ctx, "record_outcome", idea_id=idea["id"], rating=11)
    assert result.is_error and "between 1 and 10" in data["error"]
    result, data = _call(
        registry, ctx, "record_outcome", idea_id=idea["id"], happened_on="2026-09-21"
    )
    assert result.is_error and "future" in data["error"]
    result, data = _call(registry, ctx, "record_outcome", rating=5)
    assert result.is_error and "idea_id" in data["error"]
    result, data = _call(registry, ctx, "record_outcome", idea_id=42)
    assert result.is_error and "no idea #42" in data["error"]
    result, data = _call(registry, ctx, "record_outcome", idea_id=idea["id"], plan_id=999)
    assert result.is_error and "no plan #999" in data["error"]


def test_now_reports_family_time(registry, ctx) -> None:
    result, data = _call(registry, ctx, "now")
    assert not result.is_error
    assert data["date"] == "2026-09-20"
    assert data["weekday"] == "Sunday"
    assert data["time"] == "14:03"
    assert data["timezone"] == "America/Vancouver"
    assert data["season"] == "autumn"
    assert data["weekend"] == {"start": "2026-09-20", "end": "2026-09-20"}


def test_stubs_report_unavailable_without_erroring(registry, ctx) -> None:
    for name, payload in [
        ("get_calendar", {"start": "2026-09-26", "end": "2026-09-27"}),
        ("create_event", {"title": "Symphony", "start": "2026-09-26T20:00"}),
        ("update_event", {"plan_id": 1, "start": "2026-09-27T20:00"}),
        ("delete_event", {"plan_id": 1}),
        ("get_forecast", {"start": "2026-09-26", "end": "2026-09-27"}),
    ]:
        result, data = _call(registry, ctx, name, payload)
        assert not result.is_error, name
        assert data["available"] is False, name
        assert data["reason"], name
        assert result.summary["unavailable"] is True


def test_invalid_input_and_unknown_tools_are_errors(registry, ctx) -> None:
    result, data = _call(registry, ctx, "add_idea", kind="restaurant")  # missing title
    assert result.is_error and "title" in data["error"]
    result, data = _call(registry, ctx, "add_idea", title="X", kind="other", setting="underwater")
    assert result.is_error and "setting" in data["error"]
    result, data = _call(registry, ctx, "teleport", {})
    assert result.is_error and "unknown tool" in data["error"]
