"""The generic adapter for a company the settings define (agent/providers/chat.py), through the real
turn loop and the real OpenAI SDK, against a fake server on httpx's mock transport. What a company
does differently (where its thinking comes back, what its usage is called, how it says "out of
credit") is shown as dialects of the same conversation."""

import json

import httpx
import pytest

from familydb.agent import gateway, providers
from familydb.agent.loop import run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import companies, parts, prices
from familydb.agent.providers.base import ToolDef, TurnRequest, WebAccess
from familydb.agent.providers.chat import ChatProvider
from familydb.agent.render import render_user_turn
from familydb.base.config import CompanyDef, ModelPrice
from familydb.base.errors import AgentError
from familydb.store import calls, ideas

MODEL = "vendor/model-one"


def defined(**more):
    return CompanyDef(
        **{
            "slug": "acme",
            "label": "Acme AI",
            "base_url": "https://api.acme.example/v1",
            "model": MODEL,
            **more,
        }
    )


def completion(message=None, *, finish="stop", usage=None, model=MODEL, **more):
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi Sam.", **(message or {})},
                "finish_reason": finish,
            }
        ],
        "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050},
        **more,
    }


def tool_call(name="add_idea", **arguments):
    return {
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }
        ],
    }


class Wire:
    """A fake server: answers each request from a script, in order, and keeps what it was sent."""

    def __init__(self, *answers, models=None, models_status=200, key_status=200):
        self.answers = list(answers)
        self.models_status = models_status
        self.key_status = key_status
        self.requests: list[tuple[str, str, dict]] = []
        self.models = models if models is not None else [{"id": MODEL, "object": "model"}]
        self.headers: list[httpx.Headers] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        self.requests.append((request.method, request.url.path, body))
        self.headers.append(request.headers)
        if request.url.path.endswith("/key"):
            if self.key_status != 200:
                return httpx.Response(self.key_status, json={"error": {"message": "no"}})
            return httpx.Response(200, json={"data": {"label": "k"}})
        if request.url.path.endswith("/models"):
            if self.models_status != 200:
                return httpx.Response(self.models_status, json={"error": {"message": "no"}})
            return httpx.Response(200, json={"object": "list", "data": self.models})
        answer = self.answers.pop(0)
        if isinstance(answer, bytes):  # a body that is not what it should be
            return httpx.Response(200, content=answer)
        if isinstance(answer, tuple):  # (status, message)
            status, said = answer
            return httpx.Response(status, json={"error": {"message": said, "type": "x"}})
        return httpx.Response(200, json=answer)

    @property
    def chats(self):
        return [body for _, path, body in self.requests if path.endswith("/chat/completions")]


def provider(settings, wire, *, key="sk-acme", **more):
    one = defined(**more)
    live = settings.model_copy(update={"companies": [one], "company_keys": {"acme": key}})
    companies.use(live.companies)
    client = httpx.Client(transport=httpx.MockTransport(wire))
    return live, ChatProvider(live, companies.get("acme", live), http_client=client, retries=0)


def run(live, prov, registry, ctx, text="hello", **extra):
    return run_turn(
        provider=prov,
        settings=live,
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, live),
        messages=build_messages([], render_user_turn("Sam", text, ctx.clock)),
        **extra,
    )


# -- a conversation ---------------------------------------------------------------------------


def test_a_plain_reply_goes_through_the_loop_and_is_recorded_under_the_company(
    settings, registry, ctx
):
    wire = Wire(completion())
    live, prov = provider(settings, wire)
    result = run(live, prov, registry, ctx)
    assert result.status == "ok" and result.text == "Hi Sam."
    row = calls.recent_llm_calls(ctx.conn)[0]
    assert (row["provider"], row["model"]) == ("acme", MODEL)
    assert row["input_tokens"] == 1000 and row["output_tokens"] == 50
    assert row["cost_estimated"] == 1  # nothing priced it, so it was counted at the dearer rate
    sent = wire.chats[0]
    assert sent["model"] == MODEL and sent["messages"][0]["role"] == "system"
    assert sent["messages"][-1]["role"] == "user" and "hello" in sent["messages"][-1]["content"]
    assert wire.headers[0]["authorization"] == "Bearer sk-acme"
    assert "strict" not in json.dumps(
        sent["tools"]
    )  # companies disagree on it; the schema is plain


def test_a_priced_model_is_costed_at_its_price(settings, registry, ctx):
    live, prov = provider(
        settings,
        Wire(completion()),
        prices=[ModelPrice(name=MODEL, input=1.0, output=2.0, cached=0.5)],
    )
    run(live, prov, registry, ctx)
    row = calls.recent_llm_calls(ctx.conn)[0]
    assert row["cost_estimated"] == 0
    assert row["cost_usd"] == pytest.approx((1000 * 1.0 + 50 * 2.0) / 1_000_000)


def test_a_tool_call_runs_and_the_thinking_goes_back_with_it(settings, registry, ctx):
    first = completion(
        {**tool_call(title="Ramen place", kind="restaurant"), "reasoning_content": "save it"},
        finish="tool_calls",
    )
    wire = Wire(first, completion({"content": "Saved #1."}))
    live, prov = provider(settings, wire)
    result = run(live, prov, registry, ctx, "try the ramen place")
    assert result.text == "Saved #1." and ideas.get(ctx.conn, 1).title == "Ramen place"
    again = wire.chats[1]["messages"]
    assert again[-2]["role"] == "assistant" and again[-2]["reasoning_content"] == "save it"
    assert again[-2]["tool_calls"][0]["function"]["name"] == "add_idea"
    assert again[-1] == {"role": "tool", "tool_call_id": "call_1", "content": again[-1]["content"]}


def test_only_the_first_thinking_field_the_company_sends_is_kept_and_sent_back(
    settings, registry, ctx
):
    details = [{"type": "reasoning.text", "text": "because"}]
    first = completion(
        {
            **tool_call(title="A", kind="restaurant"),
            "reasoning": "text",
            "reasoning_details": details,
        },
        finish="tool_calls",
    )
    wire = Wire(first, completion())
    live, prov = provider(settings, wire, reasoning_fields=["reasoning_details", "reasoning"])
    run(live, prov, registry, ctx)
    turn = wire.chats[1]["messages"][-2]
    assert turn["reasoning_details"] == details and "reasoning" not in turn  # unchanged, once


def test_no_thinking_is_sent_back_when_the_definition_names_no_field(settings, registry, ctx):
    first = completion(
        {**tool_call(title="A", kind="restaurant"), "reasoning_content": "x"}, finish="tool_calls"
    )
    wire = Wire(first, completion())
    live, prov = provider(settings, wire, reasoning_fields=[])
    run(live, prov, registry, ctx)
    assert "reasoning_content" not in wire.chats[1]["messages"][-2]


def test_the_companys_own_switches_ride_every_request(settings, registry, ctx):
    extra = {"provider": {"data_collection": "deny"}, "thinking": {"type": "disabled"}}
    wire = Wire(completion())
    live, prov = provider(settings, wire, extra_body=extra)
    run(live, prov, registry, ctx)
    sent = wire.chats[0]
    assert sent["provider"] == {"data_collection": "deny"} and sent["thinking"] == {
        "type": "disabled"
    }


@pytest.mark.parametrize(
    "usage, fresh, cached",
    [
        # The OpenAI protocol's own name for it.
        (
            {
                "prompt_tokens": 1000,
                "completion_tokens": 5,
                "prompt_tokens_details": {"cached_tokens": 600},
            },
            400,
            600,
        ),
        # DeepSeek's.
        (
            {
                "prompt_tokens": 1000,
                "completion_tokens": 5,
                "prompt_cache_hit_tokens": 800,
                "prompt_cache_miss_tokens": 200,
            },
            200,
            800,
        ),
        # Nothing said about a cache.
        ({"prompt_tokens": 1000, "completion_tokens": 5}, 1000, None),
    ],
)
def test_usage_is_read_under_each_companys_names_for_the_cache(
    settings, registry, ctx, usage, fresh, cached
):
    live, prov = provider(settings, Wire(completion(usage=usage)))
    run(live, prov, registry, ctx)
    row = calls.recent_llm_calls(ctx.conn)[0]
    assert row["input_tokens"] == fresh and row["cache_read_input_tokens"] == cached


@pytest.mark.parametrize(
    "finish, stop",
    [("length", "max_tokens"), ("content_filter", "refusal"), ("something_new", "end")],
)
def test_a_finish_reason_is_read_as_the_loop_understands_it(settings, finish, stop):
    _live, prov = provider(settings, Wire(completion(finish=finish)))
    reply = prov.send(TurnRequest(system=[], messages=[]))
    assert reply.stop == stop


def test_a_service_that_stopped_short_is_asked_again(settings):
    _live, prov = provider(settings, Wire(completion(finish="insufficient_system_resource")))
    with pytest.raises(AgentError) as info:
        prov.send(TurnRequest(system=[], messages=[]))
    assert info.value.retryable


def test_a_200_with_no_answer_in_it_is_asked_again(settings):
    _live, prov = provider(settings, Wire({"id": "x", "object": "chat.completion", "choices": []}))
    with pytest.raises(AgentError) as info:
        prov.send(TurnRequest(system=[], messages=[]))
    assert info.value.retryable


def test_a_tool_call_with_arguments_that_are_not_json_comes_through_as_no_arguments(settings):
    broken = {
        "content": None,
        "tool_calls": [
            {"id": "c", "type": "function", "function": {"name": "n", "arguments": "{oops"}}
        ],
    }
    _live, prov = provider(settings, Wire(completion(broken, finish="tool_calls")))
    reply = prov.send(TurnRequest(system=[], messages=[]))
    assert reply.stop == "tool_use" and reply.tool_calls[0].arguments == {}


# -- failures ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, said, trouble, retryable",
    [
        (402, "Insufficient Balance", "credit", False),
        (401, "Invalid API key", "key", False),
        (403, "Your API key lacks permission", "key", False),
        (403, "Input flagged by moderation", "refused", False),
        (429, "Too many requests", None, True),
        (429, "Per-minute quota exceeded, retry in 20s", None, True),
        (429, "Account in arrears", "credit", False),
        (429, "You exceeded your current quota", "credit", False),
        (500, "upstream broke", None, True),
        (503, "overloaded", None, True),
        (404, "The model `x` does not exist", "model", False),
        (404, "route not found", "refused", False),
        (400, "bad request", "refused", False),
    ],
)
def test_a_refusal_is_read_the_way_the_loop_and_the_alerts_expect(
    settings, status, said, trouble, retryable
):
    _live, prov = provider(settings, Wire((status, said)))
    with pytest.raises(AgentError) as info:
        prov.send(TurnRequest(system=[], messages=[]))
    assert (info.value.trouble, info.value.retryable) == (trouble, retryable)
    assert "Acme AI" in str(info.value)  # an admin is told whose it was


def test_a_400_naming_the_thinking_sent_back_is_sent_again_without_it(settings, registry, ctx):
    first = completion(
        {**tool_call(title="A", kind="restaurant"), "reasoning_content": "x"}, finish="tool_calls"
    )
    wire = Wire(first, (400, "unknown field reasoning_content in messages"), completion())
    live, prov = provider(settings, wire)
    result = run(live, prov, registry, ctx)
    assert result.status == "ok"
    sent = wire.chats
    assert "reasoning_content" in sent[1]["messages"][-2]  # tried whole first
    assert "reasoning_content" not in sent[2]["messages"][-2]  # then without
    assert parts.left_out("acme", MODEL)  # and stays out while the process runs


def test_the_extra_fields_are_never_dropped_to_get_an_answer(settings):
    extra = {"provider": {"data_collection": "deny"}}
    wire = Wire((400, "unknown field provider"))
    _live, prov = provider(settings, wire, extra_body=extra)
    with pytest.raises(AgentError) as info:
        prov.send(TurnRequest(system=[], messages=[]))
    assert info.value.trouble == "refused" and len(wire.chats) == 1


# -- what it will not do ----------------------------------------------------------------------


def test_a_lookup_is_not_given_to_a_company_without_hosted_search(settings):
    _live, prov = provider(settings, Wire())
    assert prov.searches is False
    with pytest.raises(AgentError, match="no web search") as info:
        prov.payload(TurnRequest(system=[], messages=[], web=WebAccess(max_uses=3)))
    assert info.value.trouble == "refused" and not info.value.retryable
    with pytest.raises(AgentError):
        prov.transcribe(None, "")  # type: ignore[arg-type]
    assert prov.listener() is None and prov.viewer() is None


def test_a_lookup_goes_to_a_company_that_can_search_when_the_chosen_one_cannot(settings):
    live, _ = provider(settings, Wire())
    live = live.model_copy(update={"provider": "acme", "worker_provider": "acme"})
    chat = gateway.answering(live, "chat")[0]
    lookup = gateway.answering(live, "enrich")[0]
    assert chat.name == "acme" and lookup.name == "anthropic"  # the built-in with a key
    assert gateway.can_ask(live, "enrich") and gateway.can_ask(live, "chat")
    # With no other that can search, a lookup is not asked at all; the chat still is.
    alone = live.model_copy(
        update={"anthropic_api_key": None, "openai_api_key": None, "gemini_api_key": None}
    )
    assert not gateway.can_ask(alone, "enrich") and gateway.can_ask(alone, "chat")
    # Weighing a change takes no web, so the company chosen answers it (once it is turned on).
    weighing = alone.model_copy(update={"judgements": True})
    assert gateway.answering(weighing, "judge")[0].name == "acme"


def test_a_company_with_no_model_named_is_not_ready(settings):
    live, prov = provider(settings, Wire(), model="")
    assert not prov.configured()
    alone = live.model_copy(update={"provider": "acme", "provider_fallback": False})
    assert not providers.ready(alone, "chat")


def test_a_company_may_stand_in_only_when_its_admin_says_so(settings):
    keyed = settings.model_copy(
        update={"anthropic_api_key": None, "openai_api_key": None, "gemini_api_key": None}
    )
    for allowed in (False, True):
        one = defined(stand_in=allowed)
        live = keyed.model_copy(update={"companies": [one], "company_keys": {"acme": "k"}})
        spare = providers.fallback_for(live, "chat", "anthropic")
        assert (spare is not None and spare.name == "acme") is allowed


def test_a_service_on_the_family_network_needs_no_key(settings):
    one = defined(base_url="http://192.168.1.20:11434/v1", local=True)
    live = settings.model_copy(update={"companies": [one]})
    companies.use(live.companies)
    wire = Wire()
    client = httpx.Client(transport=httpx.MockTransport(wire))
    local = ChatProvider(live, companies.get("acme", live), http_client=client, retries=0)
    assert local.configured() and local.check_key() == "works"
    assert wire.headers[0]["authorization"] == "Bearer none"  # the SDK's placeholder, never a key
    # The same service out on the internet needs one.
    remote_live = live.model_copy(update={"companies": [defined()]})
    companies.use(remote_live.companies)
    remote = ChatProvider(remote_live, companies.get("acme", remote_live))
    assert not remote.configured() and remote.check_key() == "no_key"


# -- the free questions -----------------------------------------------------------------------


def test_the_key_and_the_models_are_checked_without_a_message(settings):
    wire = Wire(models=[{"id": MODEL}, {"id": "Other/Model"}])
    _live, prov = provider(settings, wire)
    assert prov.check_key() == "works"
    assert prov.listed_models() == [MODEL, "Other/Model"]
    assert prov.model_exists("other/model") is True and prov.model_exists("nope") is False
    assert wire.chats == []  # nothing was sent to a model


def test_a_key_the_service_refuses_is_a_definite_no_and_an_unreachable_one_is_not(settings):
    _live, prov = provider(settings, Wire(models_status=401))
    assert prov.check_key() == "refused"
    _live, prov = provider(settings, Wire(models_status=500))
    assert prov.check_key() == "unchecked"
    assert prov.listed_models() is None  # not an answer, and never read as "no models"


def test_a_model_the_list_does_not_have_is_said_so(settings):
    _live, prov = provider(settings, Wire(models=[{"id": "something-else"}]))
    assert prov.check_key() == "unknown_model"


def test_prices_are_read_from_the_services_own_list_when_it_has_them(settings):
    listed = [
        {
            "id": "Vendor/Model-One",
            "pricing": {
                "prompt": "0.0000002",
                "completion": "0.0000008",
                "input_cache_read": "0.00000005",
            },
        },
        {"id": "vendor/free", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "vendor/odd", "pricing": {"prompt": "?", "completion": "1"}},
        {"id": "vendor/none"},
    ]
    _live, prov = provider(settings, Wire(models=listed))
    found = prov.priced_models()
    assert found["vendor/model-one"] == (0.2, 0.8, 0.05)
    assert found["vendor/free"] == (0.0, 0.0, None)
    assert "vendor/odd" not in found and "vendor/none" not in found
    _live, bare = provider(settings, Wire(models=[{"id": MODEL}]))
    assert bare.priced_models() == {}


def test_the_request_is_shown_as_it_would_be_sent(settings):
    _live, prov = provider(settings, Wire(), extra_body={"x_switch": 1})
    tool = ToolDef("t", "does t", {"type": "object", "properties": {}})
    shown = prov.payload(TurnRequest(system=[], messages=[], tools=[tool], max_tokens=77))
    assert shown["model"] == MODEL and shown["max_tokens"] == 77 and shown["x_switch"] == 1
    assert shown["tools"][0]["function"] == {
        "name": "t",
        "description": "does t",
        "parameters": {"type": "object", "properties": {}},
    }


def test_an_unlisted_model_is_counted_at_the_dearer_rate_by_the_daily_limit(settings):
    _live, _prov = provider(settings, Wire())
    unlisted = prices.cost("acme", MODEL, {"input_tokens": 1000})
    assert not unlisted[1] and unlisted[0] == pytest.approx(0.015)


def test_the_adapter_never_follows_a_redirect(settings):
    """The SDK's own client follows them, which would send the family's words to an address that
    was never checked."""
    one = defined()
    live = settings.model_copy(update={"companies": [one], "company_keys": {"acme": "k"}})
    companies.use(live.companies)
    prov = ChatProvider(live, companies.get("acme", live))
    assert prov.client._client.follow_redirects is False


def test_a_redirect_answer_is_a_refusal_not_a_second_request(settings):
    wire = Wire()

    def redirecting(request):
        wire.requests.append((request.method, request.url.path, {}))
        return httpx.Response(307, headers={"location": "http://192.168.1.5/steal"})

    one = defined()
    live = settings.model_copy(update={"companies": [one], "company_keys": {"acme": "k"}})
    companies.use(live.companies)
    client = httpx.Client(transport=httpx.MockTransport(redirecting), follow_redirects=False)
    prov = ChatProvider(live, companies.get("acme", live), http_client=client, retries=0)
    with pytest.raises(AgentError):
        prov.send(TurnRequest(system=[], messages=[]))
    assert len(wire.requests) == 1


def _acme_chat_with(settings, **more):
    live, _ = provider(settings, Wire())
    return live.model_copy(update={"provider": "acme", **more})


def test_a_lookup_goes_to_the_cheaper_of_two_companies_that_can_search(settings):
    live = _acme_chat_with(settings, openai_api_key="sk-o")  # and Claude's key from the fixture
    assert gateway.answering(live, "enrich")[0].name == "openai"  # Luna, not Haiku
    assert gateway.answering(live, "chat")[0].name == "acme"


def test_with_the_second_company_off_a_lookup_waits_rather_than_go_to_one(settings):
    live = _acme_chat_with(settings, openai_api_key="sk-o", provider_fallback=False)
    assert gateway.answering(live, "enrich")[0].name == "acme"
    assert not gateway.can_ask(live, "enrich") and gateway.can_ask(live, "chat")
    # Chosen for lookups on purpose, it is the family's own word.
    chosen = live.model_copy(update={"worker_provider": "openai"})
    assert gateway.answering(chosen, "enrich")[0].name == "openai"
    assert gateway.can_ask(chosen, "enrich")


def test_a_companys_list_that_is_public_does_not_vouch_for_a_key(settings):
    """OpenRouter lists its models to anyone, so a template names a path only a good key opens."""
    for key_status, expected in ((401, "refused"), (500, "unchecked"), (200, "works")):
        wire = Wire(key_status=key_status)
        _live, prov = provider(settings, wire, template="openrouter")
        assert prov.check_key() == expected, key_status
        assert any(path.endswith("/key") for _, path, _ in wire.requests)
    # A company with no template asks only for the list, as before.
    wire = Wire()
    _live, prov = provider(settings, wire)
    assert prov.check_key() == "works"
    assert not any(path.endswith("/key") for _, path, _ in wire.requests)


# -- an answer in a shape the protocol allows or a company invents


def test_a_message_whose_content_is_a_list_of_parts_is_read_as_its_text(settings):
    parts_ = [{"type": "text", "text": "Hi "}, {"type": "text", "text": "Sam."}, {"type": "x"}]
    _live, prov = provider(settings, Wire(completion({"content": parts_})))
    assert prov.send(TurnRequest(system=[], messages=[])).text == "Hi Sam."


def test_an_answer_that_cannot_be_read_is_asked_again_and_never_a_bare_exception(settings):
    for answer in (
        b'{"id": "x", "choices": [',  # cut off
        b"<html>gateway error</html>",  # not JSON at all
        {"id": "x", "object": "chat.completion", "choices": [{"index": 0, "message": None}]},
    ):
        _live, prov = provider(settings, Wire(answer))
        with pytest.raises(AgentError) as info:
            prov.send(TurnRequest(system=[], messages=[]))
        assert info.value.retryable, answer


def test_the_protocols_older_function_call_is_a_tool_call(settings):
    legacy = {"content": None, "function_call": {"name": "add_idea", "arguments": '{"title": "A"}'}}
    _live, prov = provider(settings, Wire(completion(legacy, finish="function_call")))
    reply = prov.send(TurnRequest(system=[], messages=[]))
    assert reply.stop == "tool_use"
    assert (reply.tool_calls[0].name, reply.tool_calls[0].arguments) == ("add_idea", {"title": "A"})


def test_a_call_is_priced_by_the_model_asked_for_when_the_company_answers_with_a_snapshot(
    settings, registry, ctx
):
    wire = Wire(completion(model=MODEL + "-20260101"))
    live, prov = provider(
        settings, wire, prices=[ModelPrice(name=MODEL, input=1.0, output=2.0, cached=0.5)]
    )
    run(live, prov, registry, ctx)
    row = calls.recent_llm_calls(ctx.conn)[0]
    assert row["served_model"] == MODEL + "-20260101"  # who answered is still what was said
    assert row["cost_estimated"] == 0
    assert row["cost_usd"] == pytest.approx((1000 * 1.0 + 50 * 2.0) / 1_000_000)
