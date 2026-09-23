"""Regressions from the September 2026 alpha review (PR #2): each one was a real defect.

The review is written up in docs/ALPHA_READINESS.md. These tests arrived with the fixes, one
theme per commit, so each can be read beside the change that made it pass.
"""

import json
from contextlib import closing
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from familydb.agent.providers.anthropic import AnthropicProvider
from familydb.agent.providers.base import Message, TurnRequest, WebAccess
from familydb.agent.providers.gemini import GeminiProvider
from familydb.agent.worker import run_worker_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.delivery import deliver, lease, run_deliveries
from familydb.errors import AgentError
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.retry_failed import run_retries
from familydb.pipeline import handle_incoming
from familydb.store import db, ideas, messages, outcomes, places, plans
from familydb.suggest.context import build_context
from familydb.suggest.discover import discover
from familydb.suggest.engine import run
from familydb.suggest.evaluate import overlap_minutes
from familydb.suggest.types import SuggestInput
from familydb.tools import ToolContext, build_registry
from familydb.tools.gcal import free_blocks
from tests.fakes import FakeCalendar, FakeMessagesAPI, discover_script, message, text, tool_use


@pytest.fixture
def env(full_settings, thursday_clock, conn, family):
    settings = full_settings.model_copy(update={"web_tools_enabled": True})
    calendar = FakeCalendar(thursday_clock.tz)
    app = App(settings, clock=thursday_clock, calendar=calendar)
    ctx = ToolContext(conn, settings, app.clock, member=family["sam"], calendar=calendar)
    return SimpleNamespace(
        app=app,
        conn=conn,
        ctx=ctx,
        cal=calendar,
        settings=settings,
        registry=build_registry(),
        member=family["sam"],
    )


def call(env, name, **args):
    result = env.registry.dispatch(name, args, env.ctx)
    return result, json.loads(result.content)


# --- lookups and discovery on the models that are actually configured ----------------------------


def test_discovery_uses_configured_provider_without_injected_api(env, monkeypatch):
    from familydb.agent.providers import build

    api = FakeMessagesAPI(*discover_script([]))
    monkeypatch.setattr(
        "familydb.agent.worker.for_surface",
        lambda settings, surface, api=None: build("anthropic", settings, api=fake),
    )
    fake = api
    context = build_context(env.ctx, (date(2026, 9, 26), date(2026, 9, 27)))
    finds, note = discover(env.ctx, context, "Find things to do")
    assert note is None and finds == [] and api.requests
    assert env.ctx.api is None


def test_discovery_cache_separates_questions_and_reuses_identical_search(env):
    env.ctx.discover_cache = {}
    env.ctx.api = FakeMessagesAPI(*discover_script([]), *discover_script([]))
    context = build_context(env.ctx, (date(2026, 9, 26), date(2026, 9, 27)))
    assert discover(env.ctx, context, "Adult concerts")[1] is None
    first_calls = len(env.ctx.api.requests)
    assert discover(env.ctx, context, "Adult concerts")[1] is None
    assert len(env.ctx.api.requests) == first_calls
    assert discover(env.ctx, context, "Free indoor toddler activities")[1] is None
    assert len(env.ctx.api.requests) > first_calls
    assert len(env.ctx.discover_cache) == 2


def test_default_haiku_request_omits_unsupported_thinking(env):
    provider = AnthropicProvider(env.settings)
    payload = provider.payload(
        TurnRequest(
            system=[],
            messages=[Message("user", ["lookup"])],
            model=provider.model_for("worker"),
            effort="low",
        )
    )
    assert "thinking" not in payload and "output_config" not in payload
    request = TurnRequest(
        system=[], messages=[], model=provider.model_for("worker"), web=WebAccess()
    )
    tools = provider.payload(request)["tools"]
    assert [tool["type"] for tool in tools] == ["web_search_20250305", "web_fetch_20250910"]


def test_gemini_rejects_unsupported_combination_before_network(env):
    from familydb.agent.providers.base import ToolDef

    provider = GeminiProvider(env.settings)
    request = TurnRequest(
        system=[],
        messages=[],
        tools=[ToolDef("save", "save", {})],
        web=WebAccess(),
        model="gemini-2.5-flash",
    )
    with pytest.raises(AgentError, match="Gemini 3"):
        provider.payload(request)
    request.model = env.settings.gemini_worker_model
    payload = provider.payload(request)
    assert payload["config"]["tool_config"]["include_server_side_tool_invocations"]
    # Check against the installed SDK, not just a dict our fake accepts.
    from google.genai.types import GenerateContentConfig

    GenerateContentConfig.model_validate(payload["config"])


def test_what_a_request_carries_follows_the_model(env) -> None:
    """Thinking and effort for every current model, the fast web tools only where they run, and
    refusal fallbacks only where a classifier can refuse. Each wrong guess is a 400 every time."""
    provider = AnthropicProvider(env.settings)

    def payload(model: str, **extra):
        return provider.payload(TurnRequest(system=[], messages=[], model=model, **extra))

    for model in ("claude-opus-5", "claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5"):
        assert payload(model)["thinking"] == {"type": "adaptive"}, model
        assert "effort" in payload(model)["output_config"], model
    for model in ("claude-haiku-4-5-20251001", "claude-sonnet-4-5", "claude-opus-4-20250514"):
        assert "thinking" not in payload(model) and "output_config" not in payload(model), model

    worker = payload("claude-sonnet-5", web=WebAccess())["tools"]
    assert [t["type"] for t in worker] == ["web_search_20260209", "web_fetch_20260209"]

    assert payload("claude-opus-5")["fallbacks"] == "default"
    assert payload("claude-fable-5-1")["fallbacks"] == "default"
    assert "fallbacks" not in payload("claude-haiku-4-5-20251001")
    assert "betas" not in payload("claude-sonnet-5")


# --- a lookup turn may use only the tools it was given, on its own idea ---------------------------


def test_worker_rejects_undeclared_mutation_and_wrong_idea(env):
    _, data = call(env, "add_idea", title="Keep this idea", kind="activity")
    for name, args in [
        ("update_idea", {"id": data["id"], "status": "dropped"}),
        ("skip_place", {"idea_id": data["id"], "status": "skipped", "reason": "wrong"}),
    ]:
        api = FakeMessagesAPI(
            message([tool_use("injected", name, args)], stop_reason="tool_use"),
            message([text("Done")]),
        )
        turn = run_worker_turn(
            kind="enrich",
            api=api,
            settings=env.settings,
            clock=env.app.clock,
            registry=env.registry,
            conn=env.conn,
            request="Look up another venue",
            idea_id=999,
        )
        assert not turn.result.actions[0]["ok"]
        assert ideas.get(env.conn, data["id"]).status == "idea"
        assert ideas.get(env.conn, data["id"]).enrichment == "pending"


# --- suggestions checked against the day as it really is ------------------------------------------


def test_busy_all_day_trip_blocks_but_transparent_birthday_does_not(env):
    day = date(2026, 9, 26)
    event = env.cal.seed("Away camping", day, day + timedelta(days=2), all_day=True)
    assert free_blocks([event], day, env.app.clock.tz) == []
    context = build_context(env.ctx, (day, day))
    assert context.days[0].free_known and context.days[0].free == []
    assert "Away camping" in context.days[0].commitments
    transparent = replace(event, busy=False)
    assert free_blocks([transparent], day, env.app.clock.tz) == ["morning", "afternoon", "evening"]


def test_four_hour_visit_cannot_fit_one_hour_open(env):
    _, data = call(
        env,
        "add_idea",
        title="Four hour museum",
        kind="activity",
        duration_min=240,
        duration_max=240,
        setting="indoor",
    )
    place = places.insert(
        env.conn,
        name="Museum",
        hours={"sat": [{"open": "10:00", "close": "11:00"}]},
        last_checked_at="2026-09-24T19:00:00Z",
    )
    ideas.update(env.conn, data["id"], {"place_id": place.id, "enrichment": "done"})
    result = run(
        env.ctx,
        SuggestInput(
            window="dates",
            start="2026-09-26",
            end="2026-09-26",
            discover=False,
            question="What can we do?",
        ),
    )
    assert next(c for c in result.candidates if c.idea_id == data["id"]).verdict == "ruled_out"


def test_opening_intersection_is_continuous_and_allows_round_trip():
    split = [{"open": "10:00", "close": "11:00"}, {"open": "14:00", "close": "15:00"}]
    assert overlap_minutes(split, ["morning", "afternoon"]) == 60
    assert overlap_minutes([{"open": "08:00", "close": "12:00"}], ["morning"], travel=30) == 180


def test_do_not_repeat_is_honored_and_explicit_new_preference_can_override(env):
    _, data = call(env, "add_idea", title="Unwanted repeat", kind="restaurant")
    result, _ = call(
        env,
        "record_outcome",
        idea_id=data["id"],
        happened_on="2026-06-01",
        would_repeat=False,
        notes="Never again",
    )
    assert not result.is_error
    result = run(
        env.ctx, SuggestInput(window="someday", discover=False, question="What can we do?")
    )
    assert next(c for c in result.candidates if c.idea_id == data["id"]).verdict == "ruled_out"
    call(env, "record_outcome", idea_id=data["id"], happened_on="2026-06-02", would_repeat=True)
    assert data["id"] not in outcomes.do_not_repeat(env.conn)


# --- nothing lost to a restart or a failed send ---------------------------------------------------


def test_crashed_received_message_recovers_once_and_preserves_original_date(env):
    with db.transaction(env.conn):
        row = messages.insert_in(
            env.conn,
            channel="telegram",
            channel_update_id="crash",
            chat_id="100",
            member_id=env.member.id,
            text="Tomorrow, save a picnic idea",
            now="2026-09-23T19:00:00Z",
        )
    sent = []
    env.app.senders["telegram"] = lambda *args: sent.append(args)
    api = FakeMessagesAPI(message([text("Saved")]))
    assert run_retries(env.app, api=api) == 1
    assert messages.get(env.conn, row.id).status == "processed"
    assert run_retries(env.app, api=api) == 0
    assert (
        handle_incoming(
            env.app, IncomingMessage("telegram", "crash", "100", "1001", "same"), api=api
        )
        is None
    )
    assert len(sent) == 1
    assert "23 September" in api.requests[0]["messages"][-1]["content"][0]["text"]


def test_active_message_claim_blocks_second_connection_and_expired_claim_recovers(env):
    row = messages.insert_in(
        env.conn,
        channel="console",
        channel_update_id="claim",
        chat_id="c",
        member_id=env.member.id,
        text="hello",
    )
    with lease(env.app, env.conn, row.id) as owned:
        assert owned
        with closing(env.app.connect()) as other, lease(env.app, other, row.id) as second:
            assert not second
        assert run_retries(env.app, api=FakeMessagesAPI()) == 0
    env.conn.execute(
        "UPDATE messages SET claim_token='dead', claim_until='2026-01-01T00:00:00Z' WHERE id=?",
        (row.id,),
    )
    assert run_retries(env.app, api=FakeMessagesAPI(message([text("Recovered")]))) == 1


def test_failed_followup_delivery_retries_without_repeating_job_or_model(env):
    plans.insert(
        env.conn,
        title="Museum",
        start="2026-09-23T10:00:00-07:00",
        end="2026-09-23T12:00:00-07:00",
        all_day=False,
        channel="telegram",
        chat_id="100",
    )
    attempts = []

    def fail(*args):
        attempts.append(args)
        raise ConnectionError("Telegram unavailable")

    env.app.senders["telegram"] = fail
    assert run_follow_ups(env.app) == 1
    assert run_follow_ups(env.app) == 0
    assert len(attempts) == 2
    delivered = []
    env.app.senders["telegram"] = lambda *args: delivered.append(args)
    assert run_deliveries(env.app) == 1
    assert run_deliveries(env.app) == 0
    assert len(delivered) == 1
    assert (
        env.conn.execute("SELECT count(*) FROM messages WHERE direction='out'").fetchone()[0] == 1
    )


def test_normal_reply_uses_same_outbox_and_is_not_sent_twice(env):
    api = FakeMessagesAPI(message([text("Saved")]))
    reply = handle_incoming(
        env.app, IncomingMessage("telegram", "normal", "100", "1001", "hello"), api=api
    )
    assert messages.get(env.conn, reply.out_message_id).delivered_at is None
    sent = []
    env.app.senders["telegram"] = lambda *args: sent.append(args)
    assert deliver(env.app, reply.out_message_id)
    assert not deliver(env.app, reply.out_message_id)
    assert len(sent) == len(api.requests) == 1
