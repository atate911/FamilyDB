import httpx
import pytest

from familydb.agent.loop import REFUSAL_REPLY, run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import build
from familydb.agent.providers.base import Message, SystemBlock, ToolDef, TurnRequest, WebAccess
from familydb.agent.providers.gemini import GeminiProvider
from familydb.agent.render import render_user_turn
from familydb.errors import AgentError
from familydb.store import calls, ideas
from tests import fakes


def _settings(settings, **overrides):
    return settings.model_copy(update={"provider": "gemini", "gemini_api_key": "gm-t", **overrides})


def _provider(settings, api=None, **overrides):
    return build("gemini", _settings(settings, **overrides), api=api or object())


def _run(api, settings, registry, ctx, text="hello", **extra):
    return run_turn(
        provider=build("gemini", _settings(settings), api=api),
        settings=_settings(settings),
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, settings),
        messages=build_messages([], render_user_turn("Sam", text, ctx.clock)),
        **extra,
    )


def test_the_request_shape(settings) -> None:
    tool = ToolDef(name="now", description="the time", schema={"type": "object", "properties": {}})
    request = TurnRequest(
        system=[SystemBlock("rules", cacheable=True), SystemBlock("today")],
        messages=[Message("user", ["Today is Sunday.", "[Sam] hello"])],
        tools=[tool],
    )
    # Gemini 2.5, whose thinking is a token budget; Gemini 3 takes a level instead.
    payload = _provider(settings, gemini_model="gemini-2.5-pro").payload(request)
    assert payload["model"] == "gemini-2.5-pro"
    config = payload["config"]
    assert config["system_instruction"] == "rules\n\ntoday"  # one instruction, not blocks
    assert config["max_output_tokens"] == 16000
    assert config["thinking_config"] == {"thinking_budget": -1}  # medium: let it decide
    assert config["tools"] == [
        {
            "function_declarations": [
                {
                    "name": "now",
                    "description": "the time",
                    "parameters_json_schema": {"type": "object", "properties": {}},
                }
            ]
        }
    ]
    assert payload["contents"] == [
        {
            "role": "user",
            "parts": [{"text": "Today is Sunday."}, {"text": "[Sam] hello"}],
        }
    ]


def test_effort_becomes_a_thinking_budget(settings) -> None:
    for ours, budget in [("low", 0), ("medium", -1), ("xhigh", 24576), ("max", 32768)]:
        request = TurnRequest(system=[], messages=[], effort=ours, model="gemini-2.5-pro")
        assert _provider(settings).payload(request)["config"]["thinking_config"] == {
            "thinking_budget": budget
        }


def test_search_rides_alongside_our_own_tools(settings) -> None:
    tool = ToolDef(name="save_place", description="save", schema={"type": "object"})
    request = TurnRequest(
        system=[],
        messages=[],
        tools=[tool],
        web=WebAccess(max_uses=3),
        model=settings.gemini_worker_model,
    )
    tools = _provider(settings).payload(request)["config"]["tools"]
    assert len(tools) == 2  # our declarations in one group, the hosted search in another
    assert "function_declarations" in tools[0] and "google_search" in tools[1]
    plain = _provider(settings).payload(TurnRequest(system=[], messages=[], tools=[tool]))
    assert len(plain["config"]["tools"]) == 1


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


def test_a_plain_reply(settings, registry, ctx) -> None:
    api = fakes.FakeGeminiAPI(fakes.gm_response([fakes.gm_text("Hi Sam!")]))
    result = _run(api, settings, registry, ctx)
    assert result.status == "ok" and result.text == "Hi Sam!" and result.provider == "gemini"
    assert result.usage["input_tokens"] == 100 and result.usage["output_tokens"] == 10
    assert calls.recent_llm_calls(ctx.conn)[0]["served_model"] == "gemini-2.5-pro"


def test_a_tool_call_then_a_reply(settings, registry, ctx) -> None:
    api = fakes.FakeGeminiAPI(
        fakes.gm_response(
            [fakes.gm_tool_call("c1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})]
        ),
        fakes.gm_response([fakes.gm_text("Saved #1.")]),
    )
    result = _run(api, settings, registry, ctx, "we should try the ramen place")
    assert result.status == "ok" and result.text == "Saved #1."
    assert ideas.get(ctx.conn, 1).title == "Ramen place"
    # The answer names the tool as well as the call, which is how this API matches them up.
    answer = api.requests[1]["contents"][-1]
    assert answer["role"] == "user"
    response = answer["parts"][0]["function_response"]
    assert response["name"] == "add_idea" and response["id"] == "c1"
    assert "Ramen place" in response["response"]["result"]


def test_thinking_is_counted_as_output(settings, registry, ctx) -> None:
    api = fakes.FakeGeminiAPI(
        fakes.gm_response(
            [fakes.gm_text("Thought about it.")],
            usage={
                "prompt_token_count": 500,
                "cached_content_token_count": 200,
                "candidates_token_count": 30,
                "thoughts_token_count": 120,
                "total_token_count": 650,
            },
        )
    )
    result = _run(api, settings, registry, ctx)
    assert result.usage["output_tokens"] == 150  # the answer plus the thinking, both billed
    assert result.usage["cache_read_input_tokens"] == 200
    assert result.usage["input_tokens"] == 300  # cached tokens are counted inside the prompt


def test_a_refusal_and_a_cut_off_answer(settings, registry, ctx) -> None:
    api = fakes.FakeGeminiAPI(fakes.gm_response([], finish_reason="SAFETY"))
    assert _run(api, settings, registry, ctx).text == REFUSAL_REPLY
    api = fakes.FakeGeminiAPI(fakes.gm_response([fakes.gm_text("cut")], finish_reason="MAX_TOKENS"))
    assert _run(api, settings, registry, ctx).error == "max_tokens"


def test_api_failures_become_agent_errors(settings, registry, ctx) -> None:
    for error, retryable in [
        (fakes.gemini_rate_limit(), True),
        (fakes.gemini_server_error(), True),
        (httpx.ReadTimeout("timed out"), True),
    ]:
        with pytest.raises(AgentError) as info:
            _run(fakes.FakeGeminiAPI(error), settings, registry, ctx)
        assert info.value.retryable is retryable


def test_a_client_gives_up_after_two_minutes(settings) -> None:
    from familydb.agent.providers.gemini import make_client

    client = make_client(_settings(settings))
    assert client._api_client._http_options.timeout == 120_000


def test_the_model_per_surface_and_the_key(settings) -> None:
    provider = _provider(settings)
    assert provider.model_for("chat") == "gemini-3.1-flash-lite"
    assert provider.model_for("worker") == "gemini-3.1-flash-lite"
    split = _provider(settings, gemini_model="gemini-3.1-pro-preview", gemini_worker_model="")
    assert split.model_for("worker") == "gemini-3.1-pro-preview"
    from familydb.agent.providers.gemini import GeminiProvider

    assert not GeminiProvider(settings).configured()
    assert GeminiProvider(_settings(settings)).configured()
