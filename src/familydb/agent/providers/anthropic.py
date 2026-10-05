"""Claude, through the Anthropic SDK. A paused turn resumes by replaying the assistant output
verbatim, so it rides on the reply as `raw`."""

from __future__ import annotations

import base64
import dataclasses
import logging
import threading
from collections.abc import Callable
from typing import Any

import anthropic

from familydb.agent.providers import parts
from familydb.agent.providers.base import (
    LOOK_TOKENS,
    Audio,
    Heard,
    KeyCheck,
    ModelReply,
    Picture,
    Seen,
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

# What a request carries depends on the model name; a wrong guess is a 400. Adaptive thinking and
# effort go to every model but these (Haiku 4.5 rejects effort). Older models are named, not the
# current ones, so a later release gets the current shape.
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
# Dynamic-filtering web tools run on Opus/Sonnet 4.6 and later; older models get the basic ones.
BASIC_WEB_MODELS = OLDER_MODELS
# Refusal fallbacks exist only for the strongest models (Sonnet and Haiku have no such classifier).
NO_REFUSAL_FALLBACK_MODELS = (*OLDER_MODELS, "claude-sonnet", "claude-haiku")

# Parts a company may refuse: sent again without when a 400 names one (providers/parts.py).
FALLBACK = parts.Part(
    "the refusal fallback", (FALLBACK_BETA, "fallbacks", "anthropic-beta", "betas")
)
NEWER_WEB = parts.Part(
    "the newer web tools", (WEB_SEARCH["type"], WEB_FETCH["type"], "dynamic filtering")
)
THINKING = parts.Part("thinking and effort", ("thinking", "effort", "output_config"))
PARTS = (FALLBACK, NEWER_WEB, THINKING)


def thinks(model: str) -> bool:
    """Whether this model takes adaptive thinking and an effort level."""
    return not model.startswith(OLDER_MODELS) and THINKING.name not in parts.left_out(NAME, model)


def falls_back(model: str) -> bool:
    """Whether a refusal on this model may be answered by the server's fallback model."""
    return not model.startswith(NO_REFUSAL_FALLBACK_MODELS) and (
        FALLBACK.name not in parts.left_out(NAME, model)
    )


NO_CREDENTIALS = "no Anthropic credentials configured: set ANTHROPIC_API_KEY (see .env.example)"


def ensure_credentials(client: Any) -> None:
    """Fail early, and clearly, when the SDK found no credentials from any source."""
    if all(getattr(client, name, None) is None for name in CREDENTIAL_ATTRS):
        raise AgentError(NO_CREDENTIALS, retryable=False)


# A client builds its own connection pool (loading the certificate bundle, ~50 ms) and pages ask
# whether credentials exist on every view; nothing is sent through this shared idle pool.
_idle_http: Any = None
_idle_lock = threading.Lock()


def _idle_pool() -> Any:
    global _idle_http
    with _idle_lock:
        if _idle_http is None:
            _idle_http = anthropic.DefaultHttpxClient()
        return _idle_http


def has_credentials(settings: Settings) -> bool:
    """Whether the SDK finds credentials, in the settings or in any of its own places."""
    try:
        # Not closed: closing it would close the shared idle pool with it.
        ensure_credentials(
            anthropic.Anthropic(api_key=settings.anthropic_api_key, http_client=_idle_pool())
        )
    except AgentError:
        return False
    return True


def trouble(status: int, said: str) -> str | None:
    """What an admin would have to fix, from a refusal: key, credit (a 400 saying so) or model."""
    if status in (401, 403):
        return "key"
    if status in (400, 402) and "credit balance" in said.lower():
        return "credit"
    if status == 404 and "model" in said.lower():
        return "model"  # retired, or never was
    if 400 <= status < 500 and status != 429:
        return "refused"  # something about the request this module cannot name
    return None


def make_client(settings: Settings) -> anthropic.Anthropic:
    """A client for the configured key; with none, the SDK's own credential lookup."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)
    try:
        ensure_credentials(client)
    except AgentError:
        client.close()
        raise
    return client


def _request_id(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    return headers.get("request-id") if headers is not None else None


def _status_failure(exc: anthropic.APIStatusError) -> AgentError:
    return AgentError(
        f"API error {exc.status_code}: {exc.message}",
        retryable=exc.status_code >= 500,
        request_id=_request_id(exc),
        trouble=trouble(exc.status_code, str(exc.message)),
    )


def _carried(payload: dict[str, Any]) -> set[str]:
    """Which of the parts a company may refuse this request carries."""
    carried: set[str] = set()
    if payload.get("betas") or "fallbacks" in payload:
        carried.add(FALLBACK.name)
    newer = {WEB_SEARCH["type"], WEB_FETCH["type"]}
    if any(tool.get("type") in newer for tool in payload.get("tools") or []):
        carried.add(NEWER_WEB.name)
    if "thinking" in payload or "output_config" in payload:
        carried.add(THINKING.name)
    return carried


def web_tools(access: WebAccess, model: str) -> list[dict[str, Any]]:
    search, fetch = dict(WEB_SEARCH), dict(WEB_FETCH)
    if model.startswith(BASIC_WEB_MODELS) or NEWER_WEB.name in parts.left_out(NAME, model):
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
        self._api = api  # a test's scripted stand-in, when one is injected

    def configured(self) -> bool:
        """Whether a call could be made at all; asks the SDK, which looks beyond the settings."""
        if self._api is not None:
            return True
        return has_credentials(self.settings)

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = make_client(self.settings).beta.messages
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.worker_model or self.settings.anthropic_model
        return self.settings.anthropic_model

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
        if settings.anthropic_fallbacks and falls_back(model):
            payload["betas"] = [FALLBACK_BETA]
            payload["fallbacks"] = "default"
        return payload

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        last = request.messages[-1] if request.messages else None
        for message in request.messages:
            if message.role == "assistant" or message is not last:
                messages.append({"role": message.role, "content": message.text})
            else:
                messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": part} for part in message.parts],
                    }
                )
        for exchange in request.exchanges:
            # Verbatim: a paused web turn resumes only with its opaque search results untouched.
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

    def listed_models(self) -> list[str] | None:
        try:
            client = make_client(self.settings)
        except AgentError:
            return None
        try:
            return [model.id for model in client.with_options(timeout=20.0).models.list(limit=1000)]
        except Exception as exc:  # unreachable, unauthorised: not an answer about the models
            log.info("could not ask Anthropic for its models: %s", exc)
            return None
        finally:
            client.close()

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

    def listener(self) -> str | None:
        return None  # Claude takes text, images and documents, but no recordings

    def transcribe(self, audio: Audio, hints: str) -> Heard:
        raise AgentError("Claude cannot hear recordings; OpenAI or Gemini can", retryable=False)

    def count_tokens(self, request: TurnRequest) -> int:
        payload = self.payload(request)
        for key in ("max_tokens", "thinking", "output_config", "betas", "fallbacks"):
            payload.pop(key, None)
        if not payload.get("system"):
            payload.pop("system", None)
        return int(self.api.count_tokens(**payload).input_tokens)

    def send(self, request: TurnRequest) -> ModelReply:
        response, dropped = self._create(lambda: self.payload(request))
        return dataclasses.replace(self.reply(response), dropped=dropped)

    def viewer(self) -> str | None:
        return self.model_for("worker")

    def seeing(self, picture: Picture, ask: str) -> dict[str, Any]:
        """The request for one picture, to the lookup model at low effort."""
        shape = TurnRequest(
            system=[], messages=[], model=self.viewer(), effort="low", max_tokens=LOOK_TOKENS
        )
        payload = {key: value for key, value in self.payload(shape).items() if value != []}
        image = base64.b64encode(picture.data).decode("ascii")
        payload["messages"] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": picture.mime, "data": image},
                    },
                    {"type": "text", "text": ask},
                ],
            }
        ]
        return payload

    def describe(self, picture: Picture, ask: str) -> Seen:
        response, dropped = self._create(lambda: self.seeing(picture, ask))
        reply = self.reply(response)
        return Seen(
            text=reply.text,
            usage=reply.usage,
            model=reply.model,
            request_id=reply.request_id,
            stop=reply.stop,
            dropped=dropped,
        )

    def _create(self, build: Callable[[], dict[str, Any]]) -> tuple[Any, tuple[str, ...]]:
        """One request, retried without any part a 400 names (PARTS), each once. Returns the
        response and what was left out."""
        dropped: list[str] = []
        while True:
            payload = build()
            try:
                return self._send_once(payload), tuple(dropped)
            except anthropic.BadRequestError as exc:
                part = parts.refused(str(exc.message), PARTS, _carried(payload))
                if part is None or part.name in dropped:
                    raise _status_failure(exc) from exc
                log.warning(
                    "Anthropic refused %s for %s; leaving it out", part.name, payload["model"]
                )
                parts.leave_out(NAME, payload["model"], part.name)
                dropped.append(part.name)

    def _send_once(self, payload: dict[str, Any]) -> Any:
        try:
            return self.api.create(**payload)
        except anthropic.BadRequestError:
            raise
        except anthropic.RateLimitError as exc:
            raise AgentError(
                f"rate limited: {exc}", retryable=True, request_id=_request_id(exc)
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise AgentError(f"connection error: {exc}", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise _status_failure(exc) from exc
        except TypeError as exc:
            # The SDK raises a bare TypeError when it finds no credentials.
            if "authentication" not in str(exc).lower():
                raise
            raise AgentError(f"no API credentials configured: {exc}", retryable=False) from exc
