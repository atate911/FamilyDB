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
    """A service that is not set up answers so, without an error. The calendar tools used to be
    among them; without Google they keep the plans here now (tests/test_calendar.py)."""
    for name, payload in [
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


def test_a_null_at_any_depth_leaves_the_field_to_its_default(registry, ctx) -> None:
    """OpenAI's strict mode makes every field required, so a model sends null for one it leaves
    unsaid, inside each of remember's changes too. The default applies there as at the top."""
    change = {"action": "add", "id": None, "about": None, "category": None, "fact": "vegetarian"}
    result, data = _call(
        registry,
        ctx,
        "remember",
        changes=[{**change, "firm": None, "inferred": None, "until": None}],
        reply=None,
    )
    assert not result.is_error, data
    assert data["remembered"][0]["about"] == "family"


def test_every_tool_call_is_kept_with_who_made_it_and_from_where(settings, clock, conn, family):
    """Only the chat's model's calls and a tap's were kept; a page form's, a command's and the
    command line's were not. Dispatch keeps every one (tools/registry.py)."""
    from familydb.tools import ToolContext, build_registry
    from tests.test_web_edits import _client
    from tests.test_web_edits import _idea_form as idea_form

    registry = build_registry()
    asked = ToolContext(conn=conn, settings=settings, clock=clock, member=family["alex"])
    first = registry.dispatch("list_tasks", {}, asked, call_id="call_1", iteration=2)
    page = _client(settings, clock)
    page.post("/ideas/new", data=idea_form(page, who="Sam"))
    rows = conn.execute("SELECT * FROM tool_calls ORDER BY id").fetchall()
    kept = [(r["tool_name"], r["source"], r["member_id"], r["tool_use_id"]) for r in rows]
    assert kept == [
        ("list_tasks", "chat", family["alex"].id, "call_1"),
        ("add_idea", "page", family["sam"].id, None),
    ]
    assert first.call_id == rows[0]["id"] and rows[0]["iteration"] == 2
