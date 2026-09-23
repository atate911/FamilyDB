"""Regressions from the September 2026 alpha review (PR #2): each one was a real defect.

The review is written up in docs/ALPHA_READINESS.md. These tests arrived with the fixes, one
theme per commit, so each can be read beside the change that made it pass.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from familydb.agent.providers.anthropic import AnthropicProvider
from familydb.agent.providers.base import Message, TurnRequest, WebAccess
from familydb.agent.providers.gemini import GeminiProvider
from familydb.app import App
from familydb.errors import AgentError
from familydb.suggest.context import build_context
from familydb.suggest.discover import discover
from familydb.tools import ToolContext, build_registry
from tests.fakes import FakeCalendar, FakeMessagesAPI, discover_script


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
