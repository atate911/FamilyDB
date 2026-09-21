"""Claude, through the Anthropic SDK. The behaviour the bot was built on.

Everything specific to this vendor lives here: the request shape, prompt-cache markers, the
server-side web tools, the content blocks a reply comes back in, and which failures are worth
retrying. A paused turn is resumed by replaying the assistant output verbatim, so that output is
carried on the reply as `raw` rather than normalised away.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from familydb.agent.providers.base import (
    ModelReply,
    Stop,
    Surface,
    ToolCall,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.errors import AgentError
from familydb.store.calls import USAGE_KEYS

log = logging.getLogger(__name__)

NAME = "anthropic"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
CREDENTIAL_ATTRS = ("api_key", "auth_token", "credentials")
WEB_SEARCH: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
WEB_FETCH: dict[str, Any] = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5}
NO_CREDENTIALS = "no Anthropic credentials configured: set ANTHROPIC_API_KEY (see .env.example)"


def ensure_credentials(client: Any) -> None:
    """Fail early, and clearly, when the SDK found no credentials from any source."""
    if all(getattr(client, name, None) is None for name in CREDENTIAL_ATTRS):
        raise AgentError(NO_CREDENTIALS, retryable=False)


def make_client(settings: Settings) -> anthropic.Anthropic:
    """A client for the configured key. With no key the SDK uses its own credential lookup."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)
    ensure_credentials(client)
    return client


def _request_id(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    return headers.get("request-id") if headers is not None else None


def web_tools(access: WebAccess) -> list[dict[str, Any]]:
    search, fetch = dict(WEB_SEARCH), dict(WEB_FETCH)
    if access.max_uses is not None:
        search["max_uses"] = access.max_uses
        fetch["max_uses"] = access.max_uses
    if access.user_location:
        search["user_location"] = dict(access.user_location)
    return [search, fetch]


class AnthropicProvider:
    """The Provider protocol over `client.beta.messages`."""

    name = NAME

    def __init__(self, settings: Settings, api: Any = None) -> None:
        self.settings = settings
        self._api = api  # tests and the CLI inject a scripted stand-in

    # -- wiring ---------------------------------------------------------------------------
    def configured(self) -> bool:
        if self._api is not None:
            return True
        try:
            make_client(self.settings)
        except AgentError:
            return False
        return True

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = make_client(self.settings).beta.messages
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.worker_model or self.settings.anthropic_model
        return self.settings.anthropic_model

    def effort_for(self, surface: Surface) -> str:
        return (
            self.settings.worker_effort if surface == "worker" else self.settings.anthropic_effort
        )

    # -- translation ----------------------------------------------------------------------
    def cache_marker(self) -> dict[str, str]:
        if self.settings.anthropic_cache_ttl == "1h":
            return {"type": "ephemeral", "ttl": "1h"}
        return {"type": "ephemeral"}

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        settings = self.settings
        system = []
        for block in request.system:
            item: dict[str, Any] = {"type": "text", "text": block.text}
            if block.cacheable:
                item["cache_control"] = self.cache_marker()
            system.append(item)

        tools: list[dict[str, Any]] = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.schema,
                "strict": True,
            }
            for tool in request.tools
        ]
        if request.web is not None:
            tools += web_tools(request.web)

        payload: dict[str, Any] = {
            "model": request.model or settings.anthropic_model,
            "max_tokens": request.max_tokens or settings.max_output_tokens,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": request.effort or settings.anthropic_effort},
            "system": system,
            "tools": tools,
            "messages": self.transcript(request),
        }
        if settings.anthropic_fallbacks:
            payload["betas"] = [FALLBACK_BETA]
            payload["fallbacks"] = "default"
        return payload

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "assistant" or len(message.parts) == 1:
                # One part goes as plain text, which is what this API has always been sent.
                messages.append({"role": message.role, "content": message.text})
            else:
                messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": part} for part in message.parts],
                    }
                )
        for exchange in request.exchanges:
            # The assistant turn goes back exactly as it arrived: a paused web turn only resumes
            # when its opaque search results are replayed untouched.
            messages.append({"role": "assistant", "content": exchange.reply.raw})
            if exchange.outcomes:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": outcome.id,
                                "content": outcome.content,
                                "is_error": outcome.is_error,
                            }
                            for outcome in exchange.outcomes
                        ],
                    }
                )
        return messages

    def _stop(self, response: Any) -> Stop:
        reason = getattr(response, "stop_reason", None)
        if reason == "refusal":
            return "refusal"
        if reason == "max_tokens":
            return "max_tokens"
        if reason == "pause_turn":
            return "paused"
        if any(block.type == "tool_use" for block in response.content):
            return "tool_use"
        return "end"

    def reply(self, response: Any) -> ModelReply:
        usage = getattr(response, "usage", None)
        stop = self._stop(response)
        refusal = None
        if stop == "refusal":
            details = getattr(response, "stop_details", None)
            refusal = getattr(details, "category", None)
        return ModelReply(
            stop=stop,
            text="\n".join(b.text for b in response.content if b.type == "text").strip(),
            tool_calls=[
                ToolCall(id=b.id, name=b.name, arguments=b.input)
                for b in response.content
                if b.type == "tool_use"
            ],
            usage={key: getattr(usage, key, None) for key in USAGE_KEYS},
            model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None),
            refusal=refusal,
            raw=response.content,
        )

    # -- the call -------------------------------------------------------------------------
    def count_tokens(self, request: TurnRequest) -> int:
        payload = self.payload(request)
        for key in ("max_tokens", "thinking", "output_config", "betas", "fallbacks"):
            payload.pop(key, None)
        if not payload.get("system"):
            payload.pop("system", None)
        return int(self.api.count_tokens(**payload).input_tokens)

    def send(self, request: TurnRequest) -> ModelReply:
        try:
            response = self.api.create(**self.payload(request))
        except anthropic.RateLimitError as exc:
            raise AgentError(
                f"rate limited: {exc}", retryable=True, request_id=_request_id(exc)
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise AgentError(f"connection error: {exc}", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise AgentError(
                f"API error {exc.status_code}: {exc.message}",
                retryable=exc.status_code >= 500,
                request_id=_request_id(exc),
            ) from exc
        except TypeError as exc:
            # The SDK raises a bare TypeError when it finds no credentials at all.
            if "authentication" not in str(exc).lower():
                raise
            raise AgentError(f"no API credentials configured: {exc}", retryable=False) from exc
        return self.reply(response)
