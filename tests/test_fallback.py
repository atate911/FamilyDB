"""When one provider cannot take a message, the other one does, and nothing runs twice."""

import pytest

from familydb.agent.loop import run_turn, worth_switching
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import build, fallback_for
from familydb.agent.render import render_user_turn
from familydb.errors import AgentError
from familydb.store import calls, ideas
from tests import fakes

BOTH = {"openai_api_key": "sk-openai", "provider_fallback": True}


def _both(settings, **overrides):
    return settings.model_copy(update={**BOTH, **overrides})


def _turn(settings, registry, ctx, primary, spare, text="hello"):
    return run_turn(
        provider=primary,
        settings=settings,
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, settings),
        messages=build_messages([], render_user_turn("Sam", text, ctx.clock)),
        fallback=spare,
    )


def test_a_busy_provider_hands_over(settings, registry, ctx) -> None:
    paired = _both(settings)
    busy = build("anthropic", paired, api=fakes.FakeMessagesAPI(fakes.rate_limit_error()))
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hi Sam!")]))
    spare = build("openai", paired, api=spare_api)
    result = _turn(paired, registry, ctx, busy, spare)
    assert result.status == "ok" and result.text == "Hi Sam!"
    assert result.provider == "openai"
    assert spare_api.requests[0]["model"] == "gpt-6-luna"  # the other provider's own model
    assert calls.recent_llm_calls(ctx.conn)[0]["served_model"] == "gpt-5"


def test_a_provider_with_no_key_is_skipped_before_asking(settings, registry, ctx) -> None:
    paired = _both(settings, anthropic_api_key=None)
    empty = build("anthropic", paired)  # no api injected, no key: nothing to ask
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Over here.")]))
    result = _turn(paired, registry, ctx, empty, build("openai", paired, api=spare_api))
    assert result.status == "ok" and result.provider == "openai"
    assert len(spare_api.requests) == 1


def test_nothing_is_run_twice(settings, registry, ctx) -> None:
    """A failure after a tool has run stays a failure; starting again would save the idea twice."""
    paired = _both(settings)
    primary = build(
        "anthropic",
        paired,
        api=fakes.FakeMessagesAPI(
            fakes.message(
                [
                    fakes.tool_use(
                        "tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"}
                    )
                ],
                stop_reason="tool_use",
            ),
            fakes.rate_limit_error(),  # falls over only after the idea was saved
        ),
    )
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("should never be asked")]))
    with pytest.raises(AgentError):
        _turn(paired, registry, ctx, primary, build("openai", paired, api=spare_api))
    assert spare_api.requests == []
    assert ideas.get(ctx.conn, 1).title == "Ramen place"
    assert ctx.conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 1


def test_a_failure_that_would_repeat_is_not_handed_over(settings, registry, ctx) -> None:
    """A malformed request fails the same way everywhere, so trying again is only more cost."""
    paired = _both(settings)
    primary = build("anthropic", paired, api=fakes.FakeMessagesAPI(fakes.bad_request_error()))
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("unused")]))
    with pytest.raises(AgentError) as info:
        _turn(paired, registry, ctx, primary, build("openai", paired, api=spare_api))
    assert info.value.retryable is False and spare_api.requests == []


def test_which_failures_are_worth_moving_for() -> None:
    assert worth_switching(AgentError("rate limited", retryable=True))
    assert worth_switching(AgentError("no Anthropic credentials configured", retryable=False))
    assert worth_switching(AgentError("invalid api key", retryable=False))
    assert not worth_switching(AgentError("API error 400: bad tool schema", retryable=False))


def test_there_is_no_fallback_without_a_second_key_or_the_setting(settings) -> None:
    alone = settings.model_copy(update={"provider_fallback": True})
    assert fallback_for(alone, "chat", "anthropic") is None  # no OpenAI key
    paired = _both(settings)
    assert fallback_for(paired, "chat", "anthropic").name == "openai"
    assert fallback_for(paired, "chat", "openai").name == "anthropic"
    off = _both(settings, provider_fallback=False)
    assert fallback_for(off, "chat", "anthropic") is None


def test_the_whole_pipeline_hands_over(settings, clock, conn, family, monkeypatch) -> None:
    """A real message, with the chosen provider unusable and the other one answering."""
    from types import SimpleNamespace

    from familydb.app import App
    from familydb.channels.console import one_shot

    only_openai = _both(settings, anthropic_api_key=None)
    api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hello from the spare.")]))
    monkeypatch.setattr(
        "familydb.agent.providers.openai.make_client",
        lambda settings_: SimpleNamespace(responses=api),
    )
    reply = one_shot(App(only_openai, clock), "hi there", "Sam")
    assert reply.status == "ok" and reply.text == "Hello from the spare."
    assert len(api.requests) == 1
    assert api.requests[0]["model"] == "gpt-6-luna"


def test_the_spare_is_asked_with_its_own_model(settings, registry, ctx) -> None:
    """A worker turn names its model, and that name belonged to the provider it just left."""
    from familydb.agent.worker import run_worker_turn

    paired = _both(settings, web_tools_enabled=True)
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("looked it up")]))
    turn = run_worker_turn(
        kind="enrich",
        settings=paired,
        clock=ctx.clock,
        registry=registry,
        conn=ctx.conn,
        request="look up idea #1",
        provider=build("anthropic", paired, api=fakes.FakeMessagesAPI(fakes.rate_limit_error())),
        fallback=build("openai", paired, api=spare_api),
    )
    assert turn.result.status == "ok" and turn.result.provider == "openai"
    # OpenAI's lookup model, not claude-haiku: asking for the other one's model would be a 404.
    assert spare_api.requests[0]["model"] == "gpt-6-luna"


def test_a_spare_that_also_fails_reports_the_first_failure(settings, registry, ctx) -> None:
    """A rate limit is worth retrying later; a spare's bad request must not hide that."""
    paired = _both(settings)
    busy = build("anthropic", paired, api=fakes.FakeMessagesAPI(fakes.rate_limit_error()))
    broken = build("openai", paired, api=fakes.FakeResponsesAPI(fakes.openai_bad_request()))
    with pytest.raises(AgentError) as info:
        _turn(paired, registry, ctx, busy, broken)
    assert info.value.retryable is True  # the primary's verdict, so the retry job still tries
    assert "rate limited" in str(info.value)
