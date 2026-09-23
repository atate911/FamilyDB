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
    assert out["properties"]["note"]["anyOf"][1] == {"type": "null"}  # already nullable, untouched
    # Strict mode will not let a property be absent, so the ones that were optional because they
    # have a default get a way to say nothing; the handler then applies the default.
    nested = out["properties"]["nested"]
    assert nested["anyOf"][1] == {"type": "null"}
    assert nested["anyOf"][0]["required"] == ["a"]
    assert nested["anyOf"][0]["additionalProperties"] is False
    assert out["properties"]["items"]["anyOf"][0]["items"]["required"] == ["b"]
    assert out["properties"]["title"] == {"type": "string"}  # already required, untouched
    assert out["additionalProperties"] is False


def test_the_request_carries_instructions_tools_and_a_cache_key(settings) -> None:
    tool = ToolDef(name="now", description="the time", schema={"type": "object", "properties": {}})
    request = TurnRequest(
        system=[SystemBlock("rules", cacheable=True), SystemBlock("today")],
        messages=[Message("user", ["Today is Sunday.", "[Sam] hello"])],
        tools=[tool],
    )
    payload = _provider(settings).payload(request)
    assert payload["model"] == "gpt-6-luna"
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


def test_effort_names_collapse_onto_the_three_older_models_take(settings) -> None:
    for ours, theirs in [("low", "low"), ("medium", "medium"), ("xhigh", "high"), ("max", "high")]:
        request = TurnRequest(system=[], messages=[], effort=ours, model="gpt-5")
        assert _provider(settings).payload(request)["reasoning"] == {"effort": theirs}


def test_gpt6_takes_every_effort_name_as_it_is(settings) -> None:
    for ours in ("low", "medium", "high", "xhigh", "max"):
        request = TurnRequest(system=[], messages=[], effort=ours, model="gpt-6-luna")
        assert _provider(settings).payload(request)["reasoning"] == {"effort": ours}


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
    assert provider.model_for("chat") == "gpt-6-luna"
    assert provider.model_for("worker") == "gpt-6-luna"
    split = _provider(settings, openai_model="gpt-5", openai_worker_model="gpt-5-mini")
    assert (split.model_for("chat"), split.model_for("worker")) == ("gpt-5", "gpt-5-mini")
    same = _provider(settings, openai_model="gpt-5", openai_worker_model="")
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


def test_a_reply_in_the_history_is_sent_in_a_shape_this_api_accepts(settings, clock) -> None:
    """The second message of any conversation carries an assistant turn from the history."""
    import pydantic
    from openai.types.responses.response_input_param import ResponseInputItemParam
    from pydantic import TypeAdapter

    from familydb.agent.history import HistoryTurn

    messages = build_messages(
        [HistoryTurn("user", "[Sam] hello"), HistoryTurn("assistant", "Hi Sam.")],
        render_user_turn("Sam", "and again", clock),
    )
    items = _provider(settings).payload(TurnRequest(system=[], messages=messages))["input"]
    adapter = TypeAdapter(ResponseInputItemParam)
    for item in items:
        try:
            adapter.validate_python(item)
        except pydantic.ValidationError as exc:  # pragma: no cover - the assert carries the detail
            raise AssertionError(f"the API would refuse {item}: {exc}") from exc
    assert items[1] == {"role": "assistant", "content": "Hi Sam."}
    assert items[-1]["content"][0]["type"] == "input_text"  # the new message keeps its parts


def test_a_failed_response_is_not_a_cheerful_empty_answer(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(fakes.oa_response([], status="failed"))
    with pytest.raises(AgentError) as info:
        _run(api, settings, registry, ctx)
    assert info.value.retryable is True  # worth another go, unlike a malformed request


def test_token_columns_do_not_double_count(settings, registry, ctx) -> None:
    api = fakes.FakeResponsesAPI(
        fakes.oa_response(
            [fakes.oa_text("hi")],
            usage={
                "input_tokens": 5000,  # this API counts the cached ones inside this
                "input_tokens_details": {"cached_tokens": 4000, "cache_write_tokens": 500},
                "output_tokens": 50,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 5050,
            },
        )
    )
    usage = _run(api, settings, registry, ctx).usage
    assert usage["input_tokens"] == 500  # everything not already accounted for
    assert usage["cache_read_input_tokens"] == 4000
    assert usage["cache_creation_input_tokens"] == 500
    assert (
        usage["input_tokens"]
        + usage["cache_read_input_tokens"]
        + usage["cache_creation_input_tokens"]
        == 5000
    )


def test_the_cache_key_survives_a_restart(settings) -> None:
    import subprocess
    import sys

    blocks = [SystemBlock("rules", cacheable=True), SystemBlock("volatile")]
    here = _provider(settings).cache_key(blocks)
    assert here and here.startswith("familydb-")
    # A salted hash would differ in a fresh interpreter, and the key would stop finding its cache.
    script = (
        "import hashlib;"
        "print('familydb-' + hashlib.sha256('rules'.encode('utf-8')).hexdigest()[:16])"
    )
    elsewhere = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert here == elsewhere
    assert _provider(settings).cache_key([SystemBlock("volatile")]) is None


def test_the_family_is_not_moved_to_another_country(settings) -> None:
    from familydb.agent.worker import home_location

    located = settings.model_copy(update={"home_area": "Vancouver, BC"})
    request = TurnRequest(
        system=[], messages=[], web=WebAccess(user_location=home_location(located))
    )
    where = _provider(settings).payload(request)["tools"][0]["user_location"]
    assert where["city"] == "Vancouver" and where["region"] == "BC"
    assert "country" not in where  # nobody said which country, so nobody should guess


def test_a_property_forced_to_be_required_can_still_say_nothing(registry) -> None:
    """Strict mode forbids an absent field, so an optional one needs a null to fall back on."""
    from familydb.agent.providers.openai import openai_schema

    schema = openai_schema(registry.get("add_idea").api_definition()["input_schema"])
    assert set(schema["required"]) == set(schema["properties"])
    for name in ("setting", "tags", "needs_booking"):  # optional through a default, not a None
        assert {"type": "null"} in schema["properties"][name]["anyOf"], name
    assert schema["properties"]["title"] == {
        "description": "Short name for the idea, e.g. 'Ramen place on Main St'.",
        "type": "string",
    }


def test_a_null_means_use_the_default(registry, ctx) -> None:
    result = registry.dispatch(
        "add_idea",
        {"title": "Ramen place", "kind": "restaurant", "setting": None, "tags": None},
        ctx,
    )
    assert not result.is_error, result.content
    from familydb.store import ideas

    saved = ideas.get(ctx.conn, 1)
    assert saved.setting == "either" and saved.tags == []  # the model's own defaults
