"""OpenAI, through the Responses API. Caching is automatic on a long prefix, so `cacheable` only
keys it; strict function calling wants every property required (optional ones nullable); web
search is capped per turn, not per tool; voice notes use the speech-to-text endpoint."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

import openai

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
    TurnRequest,
    WebAccess,
)
from familydb.base.config import Settings
from familydb.base.errors import AgentError

log = logging.getLogger(__name__)

NAME = "openai"
NO_CREDENTIALS = "no OpenAI credentials configured: set OPENAI_API_KEY (see .env.example)"
# GPT-6 takes all five effort names; older reasoning models stop at high (xhigh is a 400), and
# GPT-4o/4.1 take no `reasoning`. Older models are named, so a later release gets everything.
EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}
HIGH_AT_MOST_MODELS = ("gpt-5", "o1", "o3", "o4")
NO_REASONING_MODELS = ("gpt-3", "gpt-4", "chatgpt-")

# Parts a model may refuse (providers/parts.py); capping effort is tried before dropping reasoning.
TOP_EFFORT = parts.Part("the top effort levels", ("xhigh", "'max'", '"max"'))
REASONING = parts.Part("reasoning settings", ("reasoning",))
CACHE_KEY = parts.Part("the prompt cache key", ("prompt_cache_key",))
TOOL_CAP = parts.Part("the cap on tool calls", ("max_tool_calls",))
PARTS = (TOP_EFFORT, REASONING, CACHE_KEY, TOOL_CAP)
REFUSAL_REASONS = {"content_filter", "refusal"}


def make_client(settings: Settings) -> openai.OpenAI:
    if not settings.openai_api_key:
        raise AgentError(NO_CREDENTIALS, retryable=False)
    return openai.OpenAI(api_key=settings.openai_api_key, max_retries=2, timeout=120.0)


def openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The schema as strict mode wants it: every property required, optional ones nullable."""
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            out[key] = {name: openai_schema(child) for name, child in value.items()}
        elif key in {"items", "additionalProperties"} and isinstance(value, dict):
            out[key] = openai_schema(value)
        elif key in {"anyOf", "oneOf", "allOf"} and isinstance(value, list):
            out[key] = [openai_schema(child) for child in value]
        elif key == "$defs" and isinstance(value, dict):
            out[key] = {name: openai_schema(child) for name, child in value.items()}
        else:
            out[key] = value
    if "properties" in out:
        already = set(out.get("required") or [])
        for name, child in out["properties"].items():
            if name in already or _accepts_null(child):
                continue
            # Null stands for "left out"; dispatch drops nulls so the model's default applies.
            out["properties"][name] = {"anyOf": [child, {"type": "null"}]}
        out["required"] = list(out["properties"])
        out.setdefault("additionalProperties", False)
    return out


def _accepts_null(schema: dict[str, Any]) -> bool:
    if not isinstance(schema, dict):
        return False
    if schema.get("type") == "null" or "null" in (schema.get("type") or []):
        return True
    return any(_accepts_null(branch) for branch in schema.get("anyOf") or [])


def reasoning_effort(model: str, effort: str) -> str:
    if model.startswith(HIGH_AT_MOST_MODELS) or TOP_EFFORT.name in parts.left_out(NAME, model):
        return EFFORT.get(effort, "medium")
    return effort


def reasons(model: str) -> bool:
    """Whether this model takes reasoning settings."""
    return not model.startswith(NO_REASONING_MODELS) and (
        REASONING.name not in parts.left_out(NAME, model)
    )


def _carried(payload: dict[str, Any]) -> set[str]:
    carried: set[str] = set()
    reasoning = payload.get("reasoning")
    if reasoning:
        carried.add(REASONING.name)
        if reasoning.get("effort") in ("xhigh", "max"):
            carried.add(TOP_EFFORT.name)
    if "prompt_cache_key" in payload:
        carried.add(CACHE_KEY.name)
    if "max_tool_calls" in payload:
        carried.add(TOOL_CAP.name)
    return carried


def _search_effort(max_uses: int | None) -> str:
    """How much of the web to pull back: fewer searches, smaller context."""
    if max_uses is None or max_uses >= 5:
        return "high"
    return "medium" if max_uses >= 3 else "low"


class OpenAIProvider:
    """The Provider protocol over `client.responses`."""

    name = NAME

    def __init__(self, settings: Settings, api: Any = None, audio: Any = None) -> None:
        self.settings = settings
        self._api = api
        self._audio = audio  # `client.audio.transcriptions`, or a test's stand-in for it

    def configured(self) -> bool:
        injected = self._api is not None or self._audio is not None
        return injected or bool(self.settings.openai_api_key)

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = make_client(self.settings).responses
        return self._api

    @property
    def audio_api(self) -> Any:
        if self._audio is None:
            self._audio = make_client(self.settings).audio.transcriptions
        return self._audio

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.openai_worker_model or self.settings.openai_model
        return self.settings.openai_model

    def cache_ttl(self) -> str:
        return ""

    def instructions(self, system: list[SystemBlock]) -> str:
        return "\n\n".join(block.text for block in system if block.text)

    def cache_key(self, system: list[SystemBlock]) -> str | None:
        """Steers repeat requests at the same cached prefix; the content is not sent."""
        cached = [block.text for block in system if block.cacheable]
        if not cached:
            return None
        # Not hash(): salted per interpreter, so every restart would change the key.
        digest = hashlib.sha256("\n\n".join(cached).encode("utf-8")).hexdigest()
        return f"familydb-{digest[:16]}"

    def tools(self, request: TurnRequest) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": openai_schema(tool.schema),
                "strict": True,
            }
            for tool in request.tools
        ]
        if request.web is not None:
            tools.append(self.web_tool(request.web))
        return tools

    def web_tool(self, access: WebAccess) -> dict[str, Any]:
        """One hosted tool covers searching and reading."""
        tool: dict[str, Any] = {
            "type": "web_search",
            "search_context_size": _search_effort(access.max_uses),
        }
        if access.user_location:
            where = access.user_location
            tool["user_location"] = {
                key: value
                for key, value in {
                    "type": "approximate",
                    "country": where.get("country"),
                    "city": where.get("city"),
                    "region": where.get("region"),
                    "timezone": where.get("timezone"),
                }.items()
                if value is not None
            }
        return tool

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        last = request.messages[-1] if request.messages else None
        for message in request.messages:
            if message.role == "assistant" or message is not last:
                items.append({"role": message.role, "content": message.text})
            else:
                items.append(
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": part} for part in message.parts],
                    }
                )
        for exchange in request.exchanges:
            # `raw` is the output list handed back; replaying it keeps the model's reasoning.
            items.extend(exchange.reply.raw or [])
            for outcome in exchange.outcomes:
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": outcome.id,
                        "output": outcome.content,
                    }
                )
        return items

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        settings = self.settings
        model = request.model or settings.openai_model
        payload: dict[str, Any] = {
            "model": model,
            "instructions": self.instructions(request.system),
            "input": self.transcript(request),
            "tools": self.tools(request),
            "max_output_tokens": request.max_tokens or settings.max_output_tokens,
            "store": False,  # the family's messages are not left on someone else's server
        }
        if reasons(model):
            payload["reasoning"] = {
                "effort": reasoning_effort(model, request.effort or settings.effort)
            }
        left_out = parts.left_out(NAME, model)
        key = self.cache_key(request.system)
        if key and CACHE_KEY.name not in left_out:
            payload["prompt_cache_key"] = key
        if (
            request.web is not None
            and request.web.max_uses is not None
            and TOOL_CAP.name not in left_out
        ):
            # The cap is per turn and counts the hand-back call: room for each declared tool once
            # lets a worker that used all its searches still report.
            payload["max_tool_calls"] = request.web.max_uses + len(request.tools)
        return payload

    def _stop(self, response: Any, calls: list[ToolCall]) -> tuple[Stop, str | None]:
        status = getattr(response, "status", None)
        if status in {"failed", "cancelled"}:
            # A 200 carrying a failure.
            detail = getattr(getattr(response, "error", None), "message", None) or status
            raise AgentError(f"response {status}: {detail}", retryable=True)
        if status == "incomplete":
            reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
            if reason in REFUSAL_REASONS:
                return "refusal", reason
            return "max_tokens", reason
        if calls:
            return "tool_use", None
        output = list(getattr(response, "output", []) or [])
        for item in output:
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "refusal":
                    return "refusal", getattr(part, "refusal", None)
        searched = any(getattr(i, "type", "").endswith("_call") for i in output)
        spoke = any(getattr(i, "type", None) == "message" for i in output)
        if searched and not spoke:
            # It searched and has not spoken yet: resend the transcript, as a paused turn resumes.
            return "paused", None
        return "end", None

    def reply(self, response: Any) -> ModelReply:
        output = list(getattr(response, "output", []) or [])
        calls = [
            ToolCall(id=item.call_id, name=item.name, arguments=_arguments(item))
            for item in output
            if getattr(item, "type", None) == "function_call"
        ]
        texts = [
            part.text
            for item in output
            for part in (getattr(item, "content", None) or [])
            if getattr(part, "type", None) == "output_text"
        ]
        stop, detail = self._stop(response, calls)
        usage = getattr(response, "usage", None)
        details = getattr(usage, "input_tokens_details", None)
        # input_tokens here includes cached ones; the column means "everything else".
        total_in = getattr(usage, "input_tokens", None)
        cached = getattr(details, "cached_tokens", None)
        written = getattr(details, "cache_write_tokens", None)
        fresh = None if total_in is None else max(total_in - (cached or 0) - (written or 0), 0)
        return ModelReply(
            stop=stop,
            text="\n".join(texts).strip(),
            tool_calls=calls,
            usage={
                "input_tokens": fresh,
                "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": written,
                "output_tokens": getattr(usage, "output_tokens", None),
                "web_searches": sum(
                    1 for item in output if getattr(item, "type", None) == "web_search_call"
                ),
            },
            model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None) or getattr(response, "id", None),
            refusal=detail,
            raw=[item.model_dump(exclude_none=True) for item in output],
        )

    def model_exists(self, model: str) -> bool | None:
        try:
            client = make_client(self.settings)
        except AgentError:
            return None
        try:
            client.with_options(timeout=10.0, max_retries=0).models.retrieve(model)
        except openai.NotFoundError:
            return False
        except Exception as exc:  # unreachable, unauthorised: not an answer about the name
            log.info("could not ask OpenAI about %s: %s", model, exc)
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
            return [model.id for model in client.with_options(timeout=20.0).models.list()]
        except Exception as exc:  # unreachable, unauthorised: not an answer about the models
            log.info("could not ask OpenAI for its models: %s", exc)
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
        except openai.AuthenticationError:
            return "refused"
        except openai.NotFoundError:
            return "unknown_model"
        except Exception as exc:  # unreachable, or a key limited to what it may read
            log.info("could not check the OpenAI key: %s", exc)
            return "unchecked"
        finally:
            client.close()
        return "works"

    def count_tokens(self, request: TurnRequest) -> int:
        raise NotImplementedError(
            "OpenAI has no token-counting endpoint; send a short message to check the schemas"
        )

    def send(self, request: TurnRequest) -> ModelReply:
        response, dropped = self._create(lambda: self.payload(request))
        return dataclasses.replace(self.reply(response), dropped=dropped)

    def _create(self, build: Callable[[], dict[str, Any]]) -> tuple[Any, tuple[str, ...]]:
        """One request, retried without any part a 400 names (PARTS), each once."""
        dropped: list[str] = []
        while True:
            payload = build()
            try:
                return self.api.create(**payload), tuple(dropped)
            except openai.BadRequestError as exc:
                part = parts.refused(str(exc), PARTS, _carried(payload))
                if part is None or part.name in dropped:
                    raise _failure(exc) from exc
                log.warning("OpenAI refused %s for %s; leaving it out", part.name, payload["model"])
                parts.leave_out(NAME, payload["model"], part.name)
                dropped.append(part.name)
            except openai.OpenAIError as exc:
                raise _failure(exc) from exc

    def listener(self) -> str | None:
        return self.settings.openai_transcribe_model or None

    def transcribe(self, audio: Audio, hints: str) -> Heard:

        model = self.listener()
        if model is None:
            raise AgentError("no OpenAI model is set to hear voice notes", retryable=False)
        payload: dict[str, Any] = {
            "model": model,
            "file": (audio.name, audio.data, audio.mime),
            "response_format": "json",
        }
        if hints:
            payload["prompt"] = hints
        try:
            result = self.audio_api.create(**payload)
        except openai.OpenAIError as exc:
            raise _failure(exc) from exc
        usage = getattr(result, "usage", None)
        heard: dict[str, int | None] = {}
        if getattr(usage, "type", None) == "tokens":
            heard = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            }
        elif getattr(usage, "type", None) == "duration":
            heard = {"audio_seconds": round(getattr(usage, "seconds", 0) or 0)}
        return Heard(
            text=(getattr(result, "text", "") or "").strip(),
            usage=heard,
            model=model,
            request_id=getattr(result, "_request_id", None),
        )

    def viewer(self) -> str | None:
        return self.model_for("worker")

    def seeing(self, picture: Picture, ask: str) -> dict[str, Any]:
        """The request for one picture, to the lookup model at low effort."""
        shape = TurnRequest(
            system=[], messages=[], model=self.viewer(), effort="low", max_tokens=LOOK_TOKENS
        )
        payload = {
            key: value for key, value in self.payload(shape).items() if value not in ("", [])
        }
        image = base64.b64encode(picture.data).decode("ascii")
        payload["input"] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:{picture.mime};base64,{image}"},
                    {"type": "input_text", "text": ask},
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


def _failure(exc: openai.OpenAIError) -> AgentError:
    """A failed request as the loop understands it. Out of credit is a 429 like "slow down";
    the code tells them apart, and credit is not worth waiting for."""
    if isinstance(exc, openai.RateLimitError):
        if getattr(exc, "code", None) == "insufficient_quota" or "insufficient_quota" in str(exc):
            return AgentError(f"out of credit: {exc}", retryable=False, trouble="credit")
        return AgentError(f"rate limited: {exc}", retryable=True)
    if isinstance(exc, openai.APIConnectionError):
        return AgentError(f"connection error: {exc}", retryable=True)
    if isinstance(exc, openai.APIStatusError):
        status = getattr(exc, "status_code", None) or 0
        return AgentError(
            f"API error {status}: {exc}",
            retryable=status >= 500,
            request_id=getattr(exc, "request_id", None),
            trouble=_trouble(status, str(exc)),
        )
    return AgentError(f"OpenAI error: {exc}", retryable=False)


def _trouble(status: int, said: str) -> str | None:
    """What an admin would have to fix, from a refusal (a 429 is read above)."""
    if status in (401, 403):
        return "key"
    if status == 404 and "model" in said.lower():
        return "model"  # retired, or never was
    if 400 <= status < 500 and status != 429:
        return "refused"  # something about the request this module cannot name
    return None


def _arguments(item: Any) -> dict[str, Any]:
    """Arguments arrive as a JSON string."""
    raw = getattr(item, "arguments", None)
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        log.warning("could not read tool arguments for %s: %r", getattr(item, "name", "?"), raw)
        return {}
    return parsed if isinstance(parsed, dict) else {}
