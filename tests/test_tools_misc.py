import json

from familydb.store import db
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


def _past_plan(ctx: ToolContext, title: str, idea_id: int):
    from familydb.store import plans

    with db.transaction(ctx.conn):
        return plans.insert(
            ctx.conn,
            title=title,
            start="2026-09-19T10:00:00-07:00",
            end="2026-09-19T12:00:00-07:00",
            all_day=False,
            idea_id=idea_id,
        )


def test_a_visit_is_counted_once_however_often_its_message_is_answered(registry, ctx) -> None:
    """A turn answered again after a failure (between the outcome's write and the call's record,
    or after both) finds the visit it already counted; another day is another visit."""
    from familydb.store import messages, outcomes

    _, idea = _call(registry, ctx, "add_idea", title="Climbing gym", kind="activity")
    with db.transaction(ctx.conn):
        inbound = messages.insert_in(
            ctx.conn,
            channel="telegram",
            channel_update_id=None,
            chat_id="1",
            member_id=ctx.member.id,
            text="we went climbing yesterday, 8/10",
            now="2026-09-20T21:00:00Z",
        )
    ctx.message_id = inbound.id
    first, data = _call(
        registry, ctx, "record_outcome", idea_id=idea["id"], rating=8, happened_on="2026-09-19"
    )
    assert not first.is_error and data["idea"]["times_done"] == 1
    again, said = _call(
        registry, ctx, "record_outcome", idea_id=idea["id"], rating=8, happened_on="2026-09-19"
    )
    assert not again.is_error
    assert said["already"] and said["outcome"]["id"] == data["outcome"]["id"]
    assert said["idea"]["times_done"] == 1
    assert len(outcomes.list_for_idea(ctx.conn, idea["id"])) == 1
    # The same visit named by its plan is the same visit.
    plan = _past_plan(ctx, "Climbing", idea["id"])
    by_plan, said = _call(
        registry, ctx, "record_outcome", plan_id=plan.id, happened_on="2026-09-19"
    )
    assert not by_plan.is_error and said["already"]
    assert said["outcome"]["id"] == data["outcome"]["id"]
    # Another day in the same message is another visit; so is a message of its own.
    _, other = _call(registry, ctx, "record_outcome", idea_id=idea["id"], happened_on="2026-09-12")
    assert "already" not in other and other["idea"]["times_done"] == 2
    ctx.message_id = None
    _, page = _call(registry, ctx, "record_outcome", idea_id=idea["id"], happened_on="2026-09-19")
    assert "already" not in page and page["idea"]["times_done"] == 3


def test_a_visit_already_counted_when_its_record_failed_is_not_counted_again(
    registry, ctx, monkeypatch
) -> None:
    """The review's case: the outcome commits, then keeping the call fails, so the retry note
    knows nothing of it; the tool itself still finds it."""
    import pytest

    from familydb.store import calls, messages

    _, idea = _call(registry, ctx, "add_idea", title="Bowling", kind="activity")
    with db.transaction(ctx.conn):
        inbound = messages.insert_in(
            ctx.conn,
            channel="telegram",
            channel_update_id=None,
            chat_id="1",
            member_id=ctx.member.id,
            text="bowling was fun",
            now="2026-09-20T21:00:00Z",
        )
    ctx.message_id = inbound.id
    keep = calls.log_tool_call

    def broken(*_args, **_kwargs):
        raise RuntimeError("disk went away")

    monkeypatch.setattr(calls, "log_tool_call", broken)
    with pytest.raises(RuntimeError):
        registry.dispatch("record_outcome", {"idea_id": idea["id"], "rating": 9}, ctx)
    monkeypatch.setattr(calls, "log_tool_call", keep)
    assert calls.tool_calls_for_message(ctx.conn, inbound.id) == []
    _, said = _call(registry, ctx, "record_outcome", idea_id=idea["id"], rating=9)
    assert said["idea"]["times_done"] == 1 and said["already"]


def test_an_outcome_names_one_thing_that_happened(registry, ctx) -> None:
    from familydb.store import ideas, outcomes

    _, museum = _call(registry, ctx, "add_idea", title="Museum", kind="activity")
    _, ramen = _call(registry, ctx, "add_idea", title="Ramen bar", kind="restaurant")
    made = _past_plan(ctx, "Museum", museum["id"])
    refused, said = _call(
        registry, ctx, "record_outcome", plan_id=made.id, idea_id=ramen["id"], rating=7
    )
    assert refused.is_error
    assert said["error"] == (
        f"plan #{made.id} is for idea #{museum['id']}, not #{ramen['id']}; nothing was recorded"
    )
    assert outcomes.list_for_idea(ctx.conn, ramen["id"]) == []
    assert ideas.get(ctx.conn, museum["id"]).times_done == 0
    # Its own idea, given or read off the plan, is fine.
    ok, said = _call(
        registry,
        ctx,
        "record_outcome",
        plan_id=made.id,
        idea_id=museum["id"],
        happened_on="2026-09-19",
    )
    assert not ok.is_error and said["outcome"]["plan_id"] == made.id
