"""OpenAI, through the Responses API.

Written against the same Provider protocol as the Claude side, so the loop cannot tell them
apart. The differences that matter here: the system prompt is `instructions` rather than blocks;
caching happens automatically on a long prefix instead of being marked, so `cacheable` is used
only to key the cache; strict function calling wants every property listed as required, with the
optional ones nullable; and a hosted search is capped by the number of tool calls a turn may make
rather than by a per-tool limit.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from familydb.agent.providers.base import (
    ModelReply,
    Stop,
    Surface,
    SystemBlock,
    ToolCall,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.errors import AgentError

log = logging.getLogger(__name__)

NAME = "openai"
NO_CREDENTIALS = "no OpenAI credentials configured: set OPENAI_API_KEY (see .env.example)"
# The Responses API takes one reasoning effort; ours has five names, so the top ones collapse.
EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}
REFUSAL_REASONS = {"content_filter", "refusal"}


def make_client(settings: Settings) -> openai.OpenAI:
    if not settings.openai_api_key:
        raise AgentError(NO_CREDENTIALS, retryable=False)
    return openai.OpenAI(api_key=settings.openai_api_key, max_retries=2, timeout=120.0)


def openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The same JSON Schema, as strict function calling wants it.

    Strict mode will not accept a property that is merely absent from `required`, so every
    property is required and the ones our models treat as optional are already nullable through
    the `anyOf` pydantic emits. Nested objects are rewritten the same way.
    """
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
        out["required"] = list(out["properties"])
        out.setdefault("additionalProperties", False)
    return out


def _search_effort(max_uses: int | None) -> str:
    """How much of the web to pull back. Fewer allowed searches means a smaller context."""
    if max_uses is None or max_uses >= 5:
        return "high"
    return "medium" if max_uses >= 3 else "low"


class OpenAIProvider:
    """The Provider protocol over `client.responses`."""

    name = NAME

    def __init__(self, settings: Settings, api: Any = None) -> None:
        self.settings = settings
        self._api = api

    # -- wiring ---------------------------------------------------------------------------
    def configured(self) -> bool:
        return self._api is not None or bool(self.settings.openai_api_key)

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = make_client(self.settings).responses
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.openai_worker_model or self.settings.openai_model
        return self.settings.openai_model

    # -- translation ----------------------------------------------------------------------
    def instructions(self, system: list[SystemBlock]) -> str:
        return "\n\n".join(block.text for block in system if block.text)

    def cache_key(self, system: list[SystemBlock]) -> str | None:
        """Steers repeat requests at the same cached prefix. The content itself is not sent."""
        cached = [block.text for block in system if block.cacheable]
        if not cached:
            return None
        return f"familydb-{hash(tuple(cached)) & 0xFFFFFFFF:08x}"

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
        """One hosted tool covers searching and reading, unlike the two on the Claude side."""
        tool: dict[str, Any] = {
            "type": "web_search",
            "search_context_size": _search_effort(access.max_uses),
        }
        if access.user_location:
            where = access.user_location
            tool["user_location"] = {
                "type": "approximate",
                "country": where.get("country", "US"),
                "city": where.get("city"),
                "region": where.get("region"),
                "timezone": where.get("timezone"),
            }
        return tool

    def transcript(self, request: TurnRequest) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in request.messages:
            kind = "input_text" if message.role == "user" else "output_text"
            items.append(
                {
                    "role": message.role,
                    "content": [{"type": kind, "text": part} for part in message.parts],
                }
            )
        for exchange in request.exchanges:
            # `raw` is the output list this API handed back; sending it again is how the turn
            # carries on, and it keeps any reasoning the model wants to refer to.
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
        payload: dict[str, Any] = {
            "model": request.model or settings.openai_model,
            "instructions": self.instructions(request.system),
            "input": self.transcript(request),
            "tools": self.tools(request),
            "max_output_tokens": request.max_tokens or settings.anthropic_max_tokens,
            "reasoning": {
                "effort": EFFORT.get(request.effort or settings.anthropic_effort, "medium")
            },
            "store": False,  # the family's messages are not left on someone else's server
        }
        key = self.cache_key(request.system)
        if key:
            payload["prompt_cache_key"] = key
        if request.web is not None and request.web.max_uses is not None:
            # There is no per-tool cap here, only a cap on the whole turn, and that cap counts
            # the hand-back call too. Leaving room for each declared tool once means a worker
            # that has used all its searches can still report what it found.
            payload["max_tool_calls"] = request.web.max_uses + len(request.tools)
        return payload

    def _stop(self, response: Any, calls: list[ToolCall]) -> tuple[Stop, str | None]:
        status = getattr(response, "status", None)
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
            # It went looking and has not said anything yet. Sending the transcript back lets it
            # carry on, the same way a paused turn resumes on the other provider.
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
        return ModelReply(
            stop=stop,
            text="\n".join(texts).strip(),
            tool_calls=calls,
            usage={
                "input_tokens": getattr(usage, "input_tokens", None),
                "cache_read_input_tokens": getattr(details, "cached_tokens", None),
                "cache_creation_input_tokens": getattr(details, "cache_write_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
            model=getattr(response, "model", None),
            request_id=getattr(response, "id", None),
            refusal=detail,
            raw=[item.model_dump(exclude_none=True) for item in output],
        )

    # -- the call -------------------------------------------------------------------------
    def count_tokens(self, request: TurnRequest) -> int:
        raise NotImplementedError(
            "OpenAI has no token-counting endpoint; send a short message to check the schemas"
        )

    def send(self, request: TurnRequest) -> ModelReply:
        try:
            response = self.api.create(**self.payload(request))
        except openai.RateLimitError as exc:
            raise AgentError(f"rate limited: {exc}", retryable=True) from exc
        except openai.APIConnectionError as exc:
            raise AgentError(f"connection error: {exc}", retryable=True) from exc
        except openai.APIStatusError as exc:
            status = getattr(exc, "status_code", None) or 0
            raise AgentError(
                f"API error {status}: {exc}",
                retryable=status >= 500,
                request_id=getattr(exc, "request_id", None),
            ) from exc
        except openai.OpenAIError as exc:
            raise AgentError(f"OpenAI error: {exc}", retryable=False) from exc
        return self.reply(response)


def _arguments(item: Any) -> dict[str, Any]:
    """Arguments arrive as a JSON string here, unlike the parsed object on the Claude side."""
    raw = getattr(item, "arguments", None)
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        log.warning("could not read tool arguments for %s: %r", getattr(item, "name", "?"), raw)
        return {}
    return parsed if isinstance(parsed, dict) else {}
