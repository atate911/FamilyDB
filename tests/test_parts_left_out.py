"""A part of a request a company stops taking (a dated beta, a tool version, a setting a new
model does not know) is left out and the request sent again, not a 400 on every message."""

from __future__ import annotations

import anthropic
import pytest
from google.genai import errors as genai_errors

from familydb.agent.providers import build
from familydb.agent.providers.base import Message, TurnRequest, WebAccess
from familydb.errors import AgentError
from tests import fakes
from tests.test_alerts import _found
from tests.test_fallback import _turn


def _refusal(said: str) -> anthropic.BadRequestError:
    return anthropic.BadRequestError(said, response=fakes._response(400), body=None)


def _asked(model: str, **extra) -> TurnRequest:
    return TurnRequest(system=[], messages=[Message("user", ["hi"])], model=model, **extra)


def test_a_retired_beta_is_left_out_and_the_request_sent_again(settings) -> None:
    api = fakes.FakeMessagesAPI(
        _refusal("Unexpected value(s) `server-side-fallback-2026-07-01` for anthropic-beta"),
        fakes.message([fakes.text("Hi.")]),
    )
    provider = build("anthropic", settings, api=api)
    reply = provider.send(_asked("claude-opus-5"))
    assert reply.text == "Hi." and reply.dropped == ("the refusal fallback",)
    assert "betas" in api.requests[0] and "betas" not in api.requests[1]
    assert "fallbacks" not in api.requests[1] and api.requests[1]["thinking"]  # the rest stays
    # Remembered for that model: the next request goes without it, first time.
    api.queue.append(fakes.message([fakes.text("Again.")]))
    assert provider.send(_asked("claude-opus-5")).dropped == ()
    assert "betas" not in api.requests[2]
    assert "betas" in provider.payload(_asked("claude-fable-5"))  # only for the one refused


def test_the_newer_web_tools_then_thinking_are_left_out_for_a_model_that_takes_neither(
    settings,
) -> None:
    api = fakes.FakeMessagesAPI(
        _refusal("tools.2: 'web_search_20260209' is not supported on this model"),
        _refusal("thinking: adaptive thinking is not supported on this model"),
        fakes.message([fakes.text("Found it.")]),
    )
    provider = build("anthropic", settings, api=api)
    reply = provider.send(_asked("claude-haiku-5", web=WebAccess()))
    assert reply.dropped == ("the newer web tools", "thinking and effort")
    last = api.requests[-1]
    assert [t["type"] for t in last["tools"]] == ["web_search_20250305", "web_fetch_20250910"]
    assert "thinking" not in last and "output_config" not in last


def test_a_refusal_that_names_nothing_it_carried_is_raised_as_it_came(settings) -> None:
    api = fakes.FakeMessagesAPI(_refusal("messages.0: content cannot be empty"))
    with pytest.raises(AgentError) as info:
        build("anthropic", settings, api=api).send(_asked("claude-opus-5"))
    assert info.value.trouble == "refused" and len(api.requests) == 1


def test_openai_caps_the_effort_then_leaves_reasoning_out(settings) -> None:
    import openai

    def refusal(said: str) -> openai.BadRequestError:
        return openai.BadRequestError(said, response=fakes._response(400), body=None)

    api = fakes.FakeResponsesAPI(
        refusal("Unsupported value: 'reasoning.effort' does not support 'xhigh' with this model."),
        refusal("Unsupported parameter: 'reasoning.effort' is not supported with this model."),
        fakes.oa_response([fakes.oa_text("Hi.")]),
    )
    paired = settings.model_copy(update={"provider": "openai", "openai_api_key": "sk-t"})
    provider = build("openai", paired, api=api)
    reply = provider.send(_asked("gpt-7", effort="xhigh"))
    assert reply.dropped == ("the top effort levels", "reasoning settings")
    assert [r.get("reasoning") for r in api.requests] == [
        {"effort": "xhigh"},
        {"effort": "high"},
        None,
    ]


def test_openai_names_the_older_models_rather_than_the_current_one(settings) -> None:
    paired = settings.model_copy(update={"provider": "openai", "openai_api_key": "sk-t"})
    provider = build("openai", paired, api=object())

    def reasoning(model):
        return provider.payload(_asked(model, effort="max")).get("reasoning")

    assert reasoning("gpt-6-luna") == {"effort": "max"}
    assert reasoning("gpt-7") == {"effort": "max"}  # released later: taken as current
    assert reasoning("gpt-5-mini") == {"effort": "high"}
    assert reasoning("o4-mini") == {"effort": "high"}
    assert reasoning("gpt-4.1-mini") is None and reasoning("gpt-4o") is None  # no reasoning


def test_gemini_that_cannot_stop_thinking_is_left_to_decide(settings) -> None:
    api = fakes.FakeGeminiAPI(
        genai_errors.ClientError(
            400,
            {"error": {"message": "Budget 0 is invalid. This model only works in thinking mode."}},
        ),
        fakes.gm_response([fakes.gm_text("Hi.")]),
    )
    paired = settings.model_copy(update={"provider": "gemini", "gemini_api_key": "gm-t"})
    reply = build("gemini", paired, api=api).send(_asked("gemini-2.5-pro", effort="low"))
    assert reply.dropped == ("switching thinking off",)
    budgets = [r["config"]["thinking_config"]["thinking_budget"] for r in api.requests]
    assert budgets == [0, -1]


def test_an_admin_hears_once_what_was_left_out(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        _refusal("fallbacks: Extra inputs are not permitted"),
        fakes.message([fakes.text("Hi.")]),
    )
    primary = build("anthropic", settings, api=api)
    assert _turn(settings, registry, ctx, primary, None).text == "Hi."
    asked = primary.model_for("chat")
    assert _found(ctx.conn) == {("api", f"anthropic:{asked}:the refusal fallback")}
    detail = ctx.conn.execute("SELECT detail FROM alerts").fetchone()[0]
    assert detail.startswith(f"Anthropic no longer takes the refusal fallback for {asked}")
