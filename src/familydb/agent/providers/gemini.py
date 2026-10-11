"""Gemini, through the google-genai SDK. Caching is implicit, so `cacheable` steers nothing;
thinking is a level on Gemini 3 and a token budget before it; voice notes and photos go to the
same endpoint as inline data."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

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
    SystemBlock,
    ToolCall,
    ToolDef,
    TurnRequest,
    WebAccess,
)
from familydb.base.config import Settings
from familydb.base.errors import AgentError

log = logging.getLogger(__name__)

NAME = "gemini"
NO_CREDENTIALS = "no Gemini credentials configured: set GEMINI_API_KEY (see .env.example)"
# Effort as a thinking budget in tokens for pre-Gemini 3 models (-1: the model decides).
THINKING = {"low": 0, "medium": -1, "high": -1, "xhigh": 24576, "max": 32768}
# Generations before Gemini 3: a thinking budget, no search beside our own tools. Older ones are
# named so later releases and aliases get the current shape.
OLDER_MODELS = ("gemini-1", "gemini-2")


def current(model: str) -> bool:
    """Whether a model takes a thinking level and hosted search beside our tools."""
    return not model.lower().startswith(OLDER_MODELS)


# Parts a model may refuse (providers/parts.py); Gemini 2.5 Pro cannot take a budget of 0.
THINKING_OFF = parts.Part("switching thinking off", ("budget 0", "thinking mode", "budget"))
THINKING_LEVEL = parts.Part("the thinking level", ("thinking_level", "thinking level"))
SEARCH_BESIDE_TOOLS = parts.Part(
    "search beside our own tools", ("include_server_side_tool_invocations", "server_side")
)
PARTS = (THINKING_OFF, THINKING_LEVEL, SEARCH_BESIDE_TOOLS)


def _carried(payload: dict[str, Any]) -> set[str]:
    config = payload.get("config") or {}
    thinking = config.get("thinking_config") or {}
    carried: set[str] = set()
    if thinking.get("thinking_budget") == 0:
        carried.add(THINKING_OFF.name)
    if "thinking_level" in thinking:
        carried.add(THINKING_LEVEL.name)
    if "tool_config" in config:
        carried.add(SEARCH_BESIDE_TOOLS.name)
    return carried


REFUSAL_REASONS = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "RECITATION",
    "IMAGE_SAFETY",
}
RETRYABLE_STATUS = (429, 500, 502, 503, 504)
TIMEOUT_MS = 120_000
HEAR = (
    "Write down what is said in this recording, word for word, in the language it is spoken. "
    "Only the words: no timestamps, speaker labels, notes or summary."
)
# Output room for a recording's words plus thinking.
HEARD_TOKENS = 400
HEARD_TOKENS_PER_SECOND = 8


def make_client(settings: Settings, timeout_ms: int = TIMEOUT_MS) -> Any:
    if not settings.gemini_api_key:
        raise AgentError(NO_CREDENTIALS, retryable=False)
    # The SDK's default is no timeout.
    return genai.Client(
        api_key=settings.gemini_api_key, http_options=genai_types.HttpOptions(timeout=timeout_ms)
    )


# Google answers a key it does not recognise with a 400 rather than a 401, so the words decide.
BAD_KEY_WORDS = ("API_KEY_INVALID", "API key not valid")
CHECK_TIMEOUT_MS = 10_000


def _status(exc: Exception) -> int:
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return 0


class GeminiProvider:
    """The Provider protocol over `client.models.generate_content`."""

    name = NAME

    def __init__(self, settings: Settings, api: Any = None) -> None:
        self.settings = settings
        self._api = api
        self._client: Any = None

    def configured(self) -> bool:
        return self._api is not None or bool(self.settings.gemini_api_key)

    @property
    def api(self) -> Any:
        if self._api is None:
            # Keep the Client itself: its finalizer closes the HTTP client that `.models` shares,
            # so letting it go leaves every later request failing with "client has been closed".
            self._client = make_client(self.settings)
            self._api = self._client.models
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.gemini_worker_model or self.settings.gemini_model
        return self.settings.gemini_model

    def cache_ttl(self) -> str:
        return ""

    def instructions(self, system: list[SystemBlock]) -> str:
        return "\n\n".join(block.text for block in system if block.text)

    def tools(self, request: TurnRequest) -> list[dict[str, Any]]:
        """Our tools in one group, hosted search as its own. Only Gemini 3 takes both, so an older
        web worker is refused here, before anything is sent."""
        tools: list[dict[str, Any]] = []
        model = request.model or self.settings.gemini_model
        if request.web is not None and request.tools and not current(model):
            raise AgentError(
                "Gemini web workers require a Gemini 3 model; set GEMINI_WORKER_MODEL",
                retryable=False,
            )
        if request.tools:
            tools.append({"function_declarations": [_declaration(t) for t in request.tools]})
        if request.web is not None:
            tools.append({"google_search": _search(request.web)})
        return tools

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": part} for part in message.parts]})
        for exchange in request.exchanges:
            contents.append({"role": "model", "parts": exchange.reply.raw or []})
            if exchange.outcomes:
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "id": outcome.id,
                                    "name": outcome.name,
                                    "response": {"result": outcome.content},
                                }
                            }
                            for outcome in exchange.outcomes
                        ],
                    }
                )
        return contents

    def config(self, request: TurnRequest) -> dict[str, Any]:
        settings = self.settings
        effort = request.effort or settings.effort
        model = request.model or settings.gemini_model
        left_out = parts.left_out(NAME, model)
        budget = THINKING.get(effort, -1)
        if budget == 0 and THINKING_OFF.name in left_out:
            budget = -1
        config: dict[str, Any] = {
            "system_instruction": self.instructions(request.system) or None,
            "max_output_tokens": request.max_tokens or settings.max_output_tokens,
            "thinking_config": {"thinking_budget": budget},
        }
        tools = self.tools(request)
        if current(model):
            level = {"thinking_level": "LOW" if effort == "low" else "HIGH"}
            config["thinking_config"] = None if THINKING_LEVEL.name in left_out else level
        if request.web is not None and request.tools and SEARCH_BESIDE_TOOLS.name not in left_out:
            config["tool_config"] = {"include_server_side_tool_invocations": True}
        if tools:
            config["tools"] = tools
            # Our loop runs the tools; the SDK's own would only warn about non-callables.
            config["automatic_function_calling"] = {"disable": True}
        return {key: value for key, value in config.items() if value is not None}

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        return {
            "model": request.model or self.settings.gemini_model,
            "contents": self.transcript(request),
            "config": self.config(request),
        }

    def _stop(self, candidate: Any, calls: list[ToolCall]) -> tuple[Stop, str | None]:
        reason = getattr(candidate, "finish_reason", None)
        name = getattr(reason, "name", None) or (str(reason) if reason else "")
        if name in REFUSAL_REASONS:
            return "refusal", name
        if name == "MAX_TOKENS":
            return "max_tokens", name
        if calls:
            return "tool_use", None
        return "end", None

    def reply(self, response: Any) -> ModelReply:
        candidates = list(getattr(response, "candidates", None) or [])
        candidate = candidates[0] if candidates else None
        parts = list(getattr(getattr(candidate, "content", None), "parts", None) or [])
        calls = [
            ToolCall(
                id=part.function_call.id or f"call_{index}",
                name=part.function_call.name,
                arguments=dict(part.function_call.args or {}),
            )
            for index, part in enumerate(parts)
            if getattr(part, "function_call", None)
        ]
        texts = [
            part.text
            for part in parts
            if getattr(part, "text", None) and not getattr(part, "thought", False)
        ]
        stop, detail = self._stop(candidate, calls)
        usage = getattr(response, "usage_metadata", None)
        cached = getattr(usage, "cached_content_token_count", None)
        prompt = getattr(usage, "prompt_token_count", None)
        if prompt is not None and cached:
            prompt = max(prompt - cached, 0)  # cached tokens are counted inside the prompt
        answer = getattr(usage, "candidates_token_count", None)
        thoughts = getattr(usage, "thoughts_token_count", None)
        if thoughts:
            # Thinking is billed as output.
            answer = (answer or 0) + thoughts
        grounding = getattr(candidate, "grounding_metadata", None)
        searches = len(getattr(grounding, "web_search_queries", None) or [])
        return ModelReply(
            stop=stop,
            text="\n".join(texts).strip(),
            tool_calls=calls,
            usage={
                "input_tokens": prompt,
                "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": None,
                "output_tokens": answer,
                "web_searches": searches,
            },
            model=getattr(response, "model_version", None),
            request_id=getattr(response, "response_id", None),
            refusal=detail,
            raw=[part.model_dump(exclude_none=True) for part in parts],
        )

    def model_exists(self, model: str) -> bool | None:
        try:
            client = make_client(self.settings)
        except AgentError:
            return None
        try:
            client.models.get(model=model)
        except genai_errors.ClientError as exc:
            if _status(exc) == 404:
                return False
            log.info("could not ask Gemini about %s: %s", model, exc)
            return None
        except Exception as exc:  # unreachable: not an answer about the name
            log.info("could not ask Gemini about %s: %s", model, exc)
            return None
        return True

    def listed_models(self) -> list[str] | None:
        try:
            client = make_client(self.settings, timeout_ms=CHECK_TIMEOUT_MS)
        except AgentError:
            return None
        try:
            # Listed as "models/<name>", sent without the prefix.
            return [str(model.name).removeprefix("models/") for model in client.models.list()]
        except Exception as exc:  # unreachable, unauthorised: not an answer about the models
            log.info("could not ask Gemini for its models: %s", exc)
            return None

    def check_key(self) -> KeyCheck:
        try:
            client = make_client(self.settings, timeout_ms=CHECK_TIMEOUT_MS)
        except AgentError:
            return "no_key"
        try:
            client.models.get(model=self.model_for("chat"))
        except genai_errors.ClientError as exc:
            status = _status(exc)
            if status == 401 or (status == 400 and any(w in str(exc) for w in BAD_KEY_WORDS)):
                return "refused"
            if status == 404:
                return "unknown_model"
            log.info("could not check the Gemini key: %s", exc)
            return "unchecked"
        except Exception as exc:  # unreachable: not an answer about the key
            log.info("could not check the Gemini key: %s", exc)
            return "unchecked"
        return "works"

    def count_tokens(self, request: TurnRequest) -> int:
        payload = self.payload(request)
        counted = self.api.count_tokens(model=payload["model"], contents=payload["contents"])
        return int(counted.total_tokens)

    def send(self, request: TurnRequest) -> ModelReply:
        response, dropped = self._create(lambda: self.payload(request))
        return dataclasses.replace(self.reply(response), dropped=dropped)

    def _create(self, build: Callable[[], dict[str, Any]]) -> tuple[Any, tuple[str, ...]]:
        """One request, retried without any part a 400 names (PARTS), each once."""
        dropped: list[str] = []
        while True:
            payload = build()
            try:
                return self.api.generate_content(**payload), tuple(dropped)
            except genai_errors.ClientError as exc:
                part = parts.refused(str(exc), PARTS, _carried(payload))
                if _status(exc) != 400 or part is None or part.name in dropped:
                    raise _failure(exc) from exc
                log.warning("Gemini refused %s for %s; leaving it out", part.name, payload["model"])
                parts.leave_out(NAME, payload["model"], part.name)
                dropped.append(part.name)
            except (genai_errors.APIError, httpx.TransportError) as exc:
                raise _failure(exc) from exc

    def listener(self) -> str | None:
        return self.settings.gemini_transcribe_model or self.model_for("worker")

    def hearing(self, audio: Audio, hints: str, model: str | None = None) -> dict[str, Any]:
        model = model or self.listener() or self.settings.gemini_model
        ask = f"{HEAR} {hints}".strip()
        budget = HEARD_TOKENS + HEARD_TOKENS_PER_SECOND * max(audio.seconds, 1)
        shape = TurnRequest(system=[], messages=[], model=model, effort="low", max_tokens=budget)
        config = self.config(shape)
        config["max_output_tokens"] = min(budget, self.settings.max_output_tokens)
        return {
            "model": model,
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": audio.mime, "data": audio.data}},
                        {"text": ask},
                    ],
                }
            ],
            "config": config,
        }

    def transcribe(self, audio: Audio, hints: str, model: str | None = None) -> Heard:
        response, dropped = self._create(lambda: self.hearing(audio, hints, model))
        reply = self.reply(response)
        return Heard(
            text=reply.text,
            usage={
                key: reply.usage.get(key)
                for key in ("input_tokens", "cache_read_input_tokens", "output_tokens")
            },
            model=reply.model or self.listener(),
            request_id=reply.request_id,
            stop=reply.stop,
            dropped=dropped,
        )

    def viewer(self) -> str | None:
        return self.model_for("worker")

    def seeing(self, picture: Picture, ask: str, model: str | None = None) -> dict[str, Any]:
        model = model or self.viewer() or self.settings.gemini_model
        shape = TurnRequest(
            system=[], messages=[], model=model, effort="low", max_tokens=LOOK_TOKENS
        )
        return {
            "model": model,
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": picture.mime, "data": picture.data}},
                        {"text": ask},
                    ],
                }
            ],
            "config": self.config(shape),
        }

    def describe(self, picture: Picture, ask: str, model: str | None = None) -> Seen:
        response, dropped = self._create(lambda: self.seeing(picture, ask, model))
        reply = self.reply(response)
        return Seen(
            text=reply.text,
            usage={
                key: reply.usage.get(key)
                for key in ("input_tokens", "cache_read_input_tokens", "output_tokens")
            },
            model=reply.model or self.viewer(),
            request_id=reply.request_id,
            stop=reply.stop,
            dropped=dropped,
        )


def _failure(exc: Exception) -> AgentError:
    """A failed request as the loop understands it."""
    if isinstance(exc, genai_errors.ServerError):
        return AgentError(f"server error: {exc}", retryable=True)
    if isinstance(exc, genai_errors.ClientError):
        status = _status(exc)
        said = str(exc).lower()
        # A bad key is as often a 400 as a 401/403; out of credit is a 429, like "slow down".
        if status in (401, 403) or (status == 400 and "api key" in said):
            return AgentError(f"API error {status}: {exc}", retryable=False, trouble="key")
        if status == 429 and ("billing" in said or "credit" in said or "prepay" in said):
            return AgentError(f"out of credit: {exc}", retryable=False, trouble="credit")
        if status == 404 and "model" in said:
            return AgentError(f"API error 404: {exc}", retryable=False, trouble="model")
        refused = 400 <= status < 500 and status not in RETRYABLE_STATUS
        return AgentError(
            f"API error {status or '?'}: {exc}",
            retryable=status in RETRYABLE_STATUS,
            trouble="refused" if refused else None,
        )
    if isinstance(exc, genai_errors.APIError):
        return AgentError(f"Gemini error: {exc}", retryable=_status(exc) in RETRYABLE_STATUS)
    # httpx.TransportError
    return AgentError(f"could not reach Gemini: {exc}", retryable=True)


def _declaration(tool: ToolDef) -> dict[str, Any]:

    return {
        "name": tool.name,
        "description": tool.description,
        "parameters_json_schema": tool.schema,
    }


def _search(access: WebAccess) -> dict[str, Any]:
    """Grounded search; no per-turn cap here, the iteration budget is it."""
    if access.user_location:
        log.debug("gemini search takes no location; %s is ignored", access.user_location)
    return {}
