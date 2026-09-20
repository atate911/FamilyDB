import json

import pytest

from familydb.agent.loop import REFUSAL_REPLY, run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.render import render_user_turn
from familydb.errors import AgentError
from familydb.store import calls, ideas
from tests import fakes


def _run(api, settings, registry, ctx, text="hello"):
    system = build_system_blocks(ctx.conn, settings)
    messages = build_messages([], render_user_turn("Sam", text, ctx.clock))
    return run_turn(
        api=api, settings=settings, registry=registry, ctx=ctx, system=system, messages=messages
    ), messages


def test_plain_reply(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi Sam!")]))
    result, _ = _run(api, settings, registry, ctx)
    assert result.status == "ok"
    assert result.text == "Hi Sam!"
    assert result.iterations == 1
    assert result.usage["input_tokens"] == 100
    request = api.requests[0]
    assert request["model"] == "claude-opus-5"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["fallbacks"] == "default"
    assert request["thinking"] == {"type": "adaptive"}
    assert request["output_config"] == {"effort": "medium"}
    assert len(request["system"]) == 2
    assert [t["name"] for t in request["tools"]] == registry.names()
    assert len(calls.recent_llm_calls(ctx.conn)) == 1


def test_tool_call_then_reply(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved #1.")]),
    )
    result, messages = _run(api, settings, registry, ctx, "we should try the ramen place")
    assert result.status == "ok"
    assert result.text == "Saved #1."
    assert result.actions == [{"tool": "add_idea", "ok": True, "id": 1}]
    assert ideas.get(ctx.conn, 1).title == "Ramen place"
    second = api.requests[1]["messages"]
    assert second[-2]["role"] == "assistant"
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["type"] == "tool_result"
    assert second[-1]["content"][0]["tool_use_id"] == "tu_1"
    assert second[-1]["content"][0]["is_error"] is False
    assert ctx.conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0] == 1
    assert len(messages) == 4


def test_parallel_tools_return_one_user_message(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use("tu_a", "now", {}),
                fakes.tool_use("tu_b", "teleport", {}),
            ],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("done")]),
    )
    result, _ = _run(api, settings, registry, ctx)
    assert result.status == "ok"
    results = api.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["tu_a", "tu_b"]
    assert results[0]["is_error"] is False
    assert results[1]["is_error"] is True
    assert "unknown tool" in json.loads(results[1]["content"])["error"]
    assert [a["ok"] for a in result.actions] == [True, False]


def test_pause_turn_resumes_without_tool_results(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("searching...")], stop_reason="pause_turn"),
        fakes.message([fakes.text("found it")]),
    )
    result, _ = _run(api, settings, registry, ctx)
    assert result.status == "ok"
    assert result.text == "found it"
    assert result.iterations == 2
    resumed = api.requests[1]["messages"]
    assert resumed[-1]["role"] == "assistant"


def test_iteration_cap(settings, registry, ctx) -> None:
    capped = settings.model_copy(update={"agent_max_iterations": 2})
    looping = fakes.message([fakes.tool_use("tu", "now", {})], stop_reason="tool_use")
    api = fakes.FakeMessagesAPI(looping, looping, looping)
    result, _ = _run(api, capped, registry, ctx)
    assert result.status == "failed"
    assert result.error == "max_iterations"
    assert len(api.requests) == 2


def test_refusal_and_max_tokens(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [], stop_reason="refusal", stop_details={"type": "refusal", "category": "general_harms"}
        )
    )
    result, _ = _run(api, settings, registry, ctx)
    assert result.status == "refused"
    assert result.text == REFUSAL_REPLY
    assert result.error == "refusal:general_harms"
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("partial")], stop_reason="max_tokens"))
    result, _ = _run(api, settings, registry, ctx)
    assert result.status == "failed" and result.error == "max_tokens"


@pytest.mark.parametrize(
    ("error", "retryable"),
    [
        (fakes.rate_limit_error(), True),
        (fakes.server_error(), True),
        (fakes.connection_error(), True),
        (fakes.bad_request_error(), False),
    ],
)
def test_api_errors_become_agent_errors(settings, registry, ctx, error, retryable) -> None:
    api = fakes.FakeMessagesAPI(error)
    with pytest.raises(AgentError) as info:
        _run(api, settings, registry, ctx)
    assert info.value.retryable is retryable


def test_missing_credentials_is_a_configuration_error(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        TypeError("Could not resolve authentication method. Expected one of api_key ...")
    )
    with pytest.raises(AgentError) as info:
        _run(api, settings, registry, ctx)
    assert info.value.retryable is False
    api = fakes.FakeMessagesAPI(TypeError("unrelated"))
    with pytest.raises(TypeError):
        _run(api, settings, registry, ctx)
