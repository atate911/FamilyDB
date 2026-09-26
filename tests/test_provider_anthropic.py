from types import SimpleNamespace

import pytest

from familydb.agent.providers import build
from familydb.agent.providers.anthropic import AnthropicProvider, ensure_credentials
from familydb.agent.providers.base import Message, SystemBlock, ToolDef, TurnRequest, WebAccess
from familydb.errors import AgentError


def _provider(settings, **overrides):
    return build("anthropic", settings.model_copy(update=overrides), api=object())


def test_ensure_credentials_requires_some_source() -> None:
    empty = SimpleNamespace(api_key=None, auth_token=None, credentials=None)
    with pytest.raises(AgentError) as info:
        ensure_credentials(empty)
    assert info.value.retryable is False
    ensure_credentials(SimpleNamespace(api_key="sk", auth_token=None, credentials=None))
    ensure_credentials(SimpleNamespace(api_key=None, auth_token="tok", credentials=None))


def test_the_request_follows_the_settings(settings) -> None:
    request = TurnRequest(system=[], messages=[Message("user", ["hi"])])
    payload = _provider(settings).payload(request)
    assert payload["model"] == "claude-opus-5"
    assert payload["betas"] == ["server-side-fallback-2026-07-01"]
    assert payload["fallbacks"] == "default"
    assert payload["output_config"] == {"effort": "medium"}
    assert payload["thinking"] == {"type": "adaptive"}

    quiet = _provider(settings, anthropic_fallbacks=False, effort="low")
    payload = quiet.payload(request)
    assert "fallbacks" not in payload and "betas" not in payload
    assert payload["output_config"] == {"effort": "low"}


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


def test_system_blocks_carry_the_cache_marker(settings) -> None:
    request = TurnRequest(
        system=[SystemBlock("rules", cacheable=True), SystemBlock("volatile")],
        messages=[Message("user", ["hi"])],
    )
    blocks = _provider(settings).payload(request)["system"]
    assert blocks[0] == {
        "type": "text",
        "text": "rules",
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }
    assert blocks[1] == {"type": "text", "text": "volatile"}
    brief = _provider(settings, anthropic_cache_ttl="5m").payload(request)["system"]
    assert brief[0]["cache_control"] == {"type": "ephemeral"}


def test_only_the_newest_turn_is_sent_as_blocks(settings) -> None:
    """History goes as one piece of text; the message being answered keeps its parts apart."""
    request = TurnRequest(
        system=[],
        messages=[
            Message("user", ["[Sam] hello", "[Alex] me too"]),
            Message("assistant", ["Hi both."]),
            Message("user", ["Today is Sunday.", "[Sam] and again"]),
        ],
    )
    turns = _provider(settings).payload(request)["messages"]
    assert turns[0] == {"role": "user", "content": "[Sam] hello\n\n[Alex] me too"}
    assert turns[1] == {"role": "assistant", "content": "Hi both."}
    assert turns[2] == {
        "role": "user",
        "content": [
            {"type": "text", "text": "Today is Sunday."},
            {"type": "text", "text": "[Sam] and again"},
        ],
    }


def test_tools_and_web_access_are_rendered(settings) -> None:
    tool = ToolDef(name="now", description="the time", schema={"type": "object"})
    request = TurnRequest(system=[], messages=[Message("user", ["hi"])], tools=[tool])
    plain = _provider(settings).payload(request)["tools"]
    assert plain == [
        {
            "name": "now",
            "description": "the time",
            "input_schema": {"type": "object"},
            "strict": True,
        }
    ]
    request.web = WebAccess(max_uses=3, user_location={"type": "approximate", "city": "Vancouver"})
    tools = _provider(settings).payload(request)["tools"]
    assert [t.get("name") for t in tools] == ["now", "web_search", "web_fetch"]
    assert tools[1]["max_uses"] == 3 and tools[2]["max_uses"] == 3
    assert tools[1]["user_location"]["city"] == "Vancouver"
    assert "user_location" not in tools[2]


def test_the_model_per_surface(settings) -> None:
    provider = _provider(settings)
    assert provider.model_for("chat") == "claude-opus-5"
    assert provider.model_for("worker") == "claude-haiku-4-5"
    same = _provider(settings, worker_model="")
    assert same.model_for("worker") == same.model_for("chat")
