import json

import pytest

from familydb.agent.loop import REFUSAL_REPLY, run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import build
from familydb.agent.providers.base import Message, SystemBlock, ToolDef, TurnRequest, WebAccess
from familydb.agent.providers.openai import openai_schema
from familydb.agent.render import render_user_turn
from familydb.errors import AgentError
from familydb.store import calls, ideas
from tests import fakes


def _settings(settings, **overrides):
    return settings.model_copy(update={"provider": "openai", "openai_api_key": "sk-t", **overrides})


def _provider(settings, api=None, **overrides):
    return build("openai", _settings(settings, **overrides), api=api or object())


def _run(api, settings, registry, ctx, text="hello", **extra):
    return run_turn(
        provider=build("openai", _settings(settings), api=api),
        settings=_settings(settings),
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, settings),
        messages=build_messages([], render_user_turn("Sam", text, ctx.clock)),
        **extra,
    )


def test_strict_function_schemas_require_every_property() -> None:
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "nested": {"type": "object", "properties": {"a": {"type": "string"}}},
            "items": {"type": "array", "items": {"type": "object", "properties": {"b": {}}}},
        },
        "required": ["title"],
        "additionalProperties": False,
    }
    out = openai_schema(schema)
    assert out["required"] == ["title", "note", "nested", "items"]
    assert out["properties"]["nested"]["required"] == ["a"]
    assert out["properties"]["items"]["items"]["required"] == ["b"]
    assert out["properties"]["note"]["anyOf"][1] == {"type": "null"}  # optional stays nullable
    assert all(o.get("additionalProperties") is False for o in (out, out["properties"]["nested"]))


def test_the_request_carries_instructions_tools_and_a_cache_key(settings) -> None:
    tool = ToolDef(name="now", description="the time", schema={"type": "object", "properties": {}})
    request = TurnRequest(
        system=[SystemBlock("rules", cacheable=True), SystemBlock("today")],
        messages=[Message("user", ["Today is Sunday.", "[Sam] hello"])],
        tools=[tool],
    )
    payload = _provider(settings).payload(request)
    assert payload["model"] == "gpt-5"
    assert payload["instructions"] == "rules\n\ntoday"  # one string, not blocks
    assert payload["store"] is False  # the family's messages stay off their servers
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["prompt_cache_key"].startswith("familydb-")
    assert payload["tools"] == [
        {
            "type": "function",
            "name": "now",
            "description": "the time",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]
    assert payload["input"] == [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Today is Sunday."},
                {"type": "input_text", "text": "[Sam] hello"},
            ],
        }
    ]


def test_effort_names_collapse_onto_the_three_it_takes(settings) -> None:
    for ours, theirs in [("low", "low"), ("medium", "medium"), ("xhigh", "high"), ("max", "high")]:
        request = TurnRequest(system=[], messages=[], effort=ours)
        assert _provider(settings).payload(request)["reasoning"] == {"effort": theirs}


def test_a_plain_reply(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hi Sam!")]))
    result = _run(api, settings, registry, ctx)
    assert result.status == "ok" and result.text == "Hi Sam!"
    assert result.provider == "openai"
    assert result.usage["input_tokens"] == 100
    logged = calls.recent_llm_calls(ctx.conn)
    assert len(logged) == 1 and logged[0]["served_model"] == "gpt-5"


def test_a_tool_call_then_a_reply(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(
        fakes.oa_response(
            [
                fakes.oa_tool_call(
                    "call_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"}
                )
            ]
        ),
        fakes.oa_response([fakes.oa_text("Saved #1.")]),
    )
    result = _run(api, settings, registry, ctx, "we should try the ramen place")
    assert result.status == "ok" and result.text == "Saved #1."
    assert result.actions == [{"tool": "add_idea", "ok": True, "id": 1}]
    assert ideas.get(ctx.conn, 1).title == "Ramen place"
    # The second request replays the call and answers it the way this API expects.
    second = api.requests[1]["input"]
    assert second[-2]["type"] == "function_call" and second[-2]["call_id"] == "call_1"
    assert second[-1] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": second[-1]["output"],
    }
    assert json.loads(second[-1]["output"])["title"] == "Ramen place"


def test_a_refusal_and_a_cut_off_answer(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_refusal("no")]))
    result = _run(api, settings, registry, ctx)
    assert result.status == "refused" and result.text == REFUSAL_REPLY

    api = fakes.FakeResponsesAPI(
        fakes.oa_response([], status="incomplete", incomplete="max_output_tokens")
    )
    assert _run(api, settings, registry, ctx).error == "max_tokens"

    api = fakes.FakeResponsesAPI(
        fakes.oa_response([], status="incomplete", incomplete="content_filter")
    )
    assert _run(api, settings, registry, ctx).status == "refused"


def test_api_failures_become_agent_errors(settings, registry, ctx) -> None:
    for error, retryable in [
        (fakes.openai_rate_limit(), True),
        (fakes.openai_server_error(), True),
    ]:
        api = fakes.FakeResponsesAPI(error)
        with pytest.raises(AgentError) as info:
            _run(api, settings, registry, ctx)
        assert info.value.retryable is retryable


def test_unreadable_tool_arguments_do_not_crash_the_turn(settings, registry, ctx) -> None:
    broken = fakes.oa_tool_call("call_x", "now", {})
    broken["arguments"] = "{not json"
    api = fakes.FakeResponsesAPI(
        fakes.oa_response([broken]), fakes.oa_response([fakes.oa_text("ok")])
    )
    result = _run(api, settings, registry, ctx)
    assert result.status == "ok"  # `now` takes no input, so an empty object is a valid call
    assert result.actions[0]["tool"] == "now"


def test_hosted_search_is_one_tool_and_caps_the_turn(settings) -> None:
    request = TurnRequest(
        system=[],
        messages=[],
        web=WebAccess(
            max_uses=3,
            user_location={"city": "Vancouver", "region": "WA", "timezone": "America/Vancouver"},
        ),
    )
    payload = _provider(settings).payload(request)
    assert [t["type"] for t in payload["tools"]] == ["web_search"]
    assert payload["tools"][0]["user_location"]["city"] == "Vancouver"
    assert payload["tools"][0]["search_context_size"] == "medium"
    assert payload["max_tool_calls"] == 3
    # No web access means no hosted tool and no cap.
    plain = _provider(settings).payload(TurnRequest(system=[], messages=[]))
    assert plain["tools"] == [] and "max_tool_calls" not in plain


def test_the_model_per_surface(settings) -> None:
    provider = _provider(settings)
    assert provider.model_for("chat") == "gpt-5"
    assert provider.model_for("worker") == "gpt-5-mini"
    same = _provider(settings, openai_worker_model="")
    assert same.model_for("worker") == "gpt-5"


def test_it_says_when_there_is_no_key(settings) -> None:
    from familydb.agent.providers.openai import OpenAIProvider

    assert not OpenAIProvider(settings).configured()  # the base fixture has no OpenAI key
    assert OpenAIProvider(_settings(settings)).configured()


def test_a_search_with_nothing_said_yet_resumes(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(
        fakes.oa_response([fakes.oa_web_call("ws_1")]),  # went looking, said nothing
        fakes.oa_response([fakes.oa_text("Found it.")]),
    )
    result = _run(api, settings, registry, ctx)
    assert result.status == "ok" and result.text == "Found it." and result.iterations == 2
    # The second request carries the first response's output back, so it can carry on.
    assert api.requests[1]["input"][-1]["type"] == "web_search_call"


def test_the_turn_cap_leaves_room_for_the_hand_back(settings) -> None:
    tools = [
        ToolDef(name="save_place", description="save", schema={"type": "object", "properties": {}}),
        ToolDef(name="skip_place", description="skip", schema={"type": "object", "properties": {}}),
    ]
    request = TurnRequest(system=[], messages=[], tools=tools, web=WebAccess(max_uses=3))
    # Three searches plus one call for each declared tool, so a worker that used every search
    # can still report what it found.
    assert _provider(settings).payload(request)["max_tool_calls"] == 5
