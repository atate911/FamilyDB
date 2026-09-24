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
    KeyCheck,
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
# The versions without dynamic filtering, for the models that cannot run it.
BASIC_WEB_SEARCH = "web_search_20250305"
BASIC_WEB_FETCH = "web_fetch_20250910"

# What a request may carry depends on the model, and the settings page can point either surface
# at any model, so it is read from the name each time. Getting it wrong is not a degraded answer
# but a 400 on every request: that is how lookups on the default Haiku worker failed before.
#
# Adaptive thinking and effort: every current model takes them, the older ones below do not
# (Haiku 4.5 still wants a fixed thinking budget and rejects effort outright). Listed by what
# they are rather than by what works, so a model released later gets thinking by default.
OLDER_MODELS = (
    "claude-3",
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-opus-4-1",
    "claude-opus-4-0",
    "claude-sonnet-4-0",
    "claude-opus-4-2",  # the undotted first Claude 4 names, claude-opus-4-20250514
    "claude-sonnet-4-2",
)
# The web tools with dynamic filtering: only these families. Anything else gets the basic
# versions, which are slower to read a page but work everywhere.
DYNAMIC_WEB_MODELS = (
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-opus-5",  # and claude-opus-5-5
    "claude-sonnet-4-6",
    "claude-sonnet-5",
)
# Server-side refusal fallbacks exist for the models whose safety classifiers can decline a
# request. A worker on Haiku has no such classifier, so the parameter is not sent to it.
REFUSAL_FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5", "claude-mythos-5")


def thinks(model: str) -> bool:
    """Whether this model takes adaptive thinking and an effort level."""
    return not model.startswith(OLDER_MODELS)


NO_CREDENTIALS = "no Anthropic credentials configured: set ANTHROPIC_API_KEY (see .env.example)"


def ensure_credentials(client: Any) -> None:
    """Fail early, and clearly, when the SDK found no credentials from any source."""
    if all(getattr(client, name, None) is None for name in CREDENTIAL_ATTRS):
        raise AgentError(NO_CREDENTIALS, retryable=False)


def make_client(settings: Settings) -> anthropic.Anthropic:
    """A client for the configured key. With no key the SDK uses its own credential lookup."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)
    try:
        ensure_credentials(client)
    except AgentError:
        client.close()  # it holds a connection pool; nobody is going to use this one
        raise
    return client


def _request_id(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    return headers.get("request-id") if headers is not None else None


def web_tools(access: WebAccess, model: str) -> list[dict[str, Any]]:
    search, fetch = dict(WEB_SEARCH), dict(WEB_FETCH)
    if not model.startswith(DYNAMIC_WEB_MODELS):
        search["type"], fetch["type"] = BASIC_WEB_SEARCH, BASIC_WEB_FETCH
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
        """Whether a call could be made at all.

        This one builds a throwaway client, because the SDK looks for credentials in places the
        settings never see. It is closed again straight away: the status page asks this question
        on every view, and a leaked pool per view is a slow way to run out of sockets.
        """
        if self._api is not None:
            return True
        try:
            make_client(self.settings).close()
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
        model = request.model or settings.anthropic_model
        if request.web is not None:
            tools += web_tools(request.web, model)

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or settings.max_output_tokens,
            "system": system,
            "tools": tools,
            "messages": self.transcript(request),
        }
        if thinks(model):
            payload["thinking"] = {"type": "adaptive"}
            payload["output_config"] = {"effort": request.effort or settings.effort}
        if settings.anthropic_fallbacks and model.startswith(REFUSAL_FALLBACK_MODELS):
            payload["betas"] = [FALLBACK_BETA]
            payload["fallbacks"] = "default"
        return payload

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        last = request.messages[-1] if request.messages else None
        for message in request.messages:
            if message.role == "assistant" or message is not last:
                # Only the newest turn is sent as separate blocks; everything behind it is one
                # piece of text, which is how this API has always been sent it.
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
            usage={
                **{key: getattr(usage, key, None) for key in USAGE_KEYS},
                "web_searches": getattr(
                    getattr(usage, "server_tool_use", None), "web_search_requests", None
                ),
            },
            model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None),
            refusal=refusal,
            raw=response.content,
        )

    # -- the call -------------------------------------------------------------------------
    def model_exists(self, model: str) -> bool | None:
        try:
            client = make_client(self.settings)
        except AgentError:
            return None
        try:
            client.with_options(timeout=10.0, max_retries=0).models.retrieve(model)
        except anthropic.NotFoundError:
            return False
        except Exception as exc:  # unreachable, unauthorised: not an answer about the name
            log.info("could not ask Anthropic about %s: %s", model, exc)
            return None
        finally:
            client.close()
        return True

    def check_key(self) -> KeyCheck:
        try:
            client = make_client(self.settings)
        except AgentError:
            return "no_key"
        try:
            client.with_options(timeout=10.0, max_retries=0).models.retrieve(self.model_for("chat"))
        except anthropic.AuthenticationError:
            return "refused"
        except anthropic.NotFoundError:
            return "unknown_model"
        except Exception as exc:  # unreachable, or refused for some other reason than the key
            log.info("could not check the Anthropic key: %s", exc)
            return "unchecked"
        finally:
            client.close()
        return "works"

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
