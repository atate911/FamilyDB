"""OpenAI, through the Responses API.

Written against the same Provider protocol as the Claude side, so the loop cannot tell them
apart. The differences that matter here: the system prompt is `instructions` rather than blocks;
caching happens automatically on a long prefix instead of being marked, so `cacheable` is used
only to key the cache; strict function calling wants every property listed as required, with the
optional ones nullable; and a hosted search is capped by the number of tool calls a turn may make
rather than by a per-tool limit.
"""

from __future__ import annotations

import hashlib
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
# GPT-6 takes all five of our effort names as they are. The models before it stop at high, so
# the top two collapse there; sending them xhigh would be a 400 on every request.
EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}
FULL_EFFORT_MODELS = ("gpt-6",)
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
        already = set(out.get("required") or [])
        for name, child in out["properties"].items():
            if name in already or _accepts_null(child):
                continue
            # It was optional because it has a default. Strict mode will not let it be absent,
            # so it gets a way to say nothing instead, and the handler applies the default.
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
    if model.startswith(FULL_EFFORT_MODELS):
        return effort
    return EFFORT.get(effort, "medium")


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
        # Not hash(): that is salted per interpreter, so every restart would ask for a new shard.
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
        """One hosted tool covers searching and reading, unlike the two on the Claude side."""
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
                # output_text is only legal on the way out; an incoming turn is plain text.
                items.append({"role": message.role, "content": message.text})
            else:
                items.append(
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": part} for part in message.parts],
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
        model = request.model or settings.openai_model
        payload: dict[str, Any] = {
            "model": model,
            "instructions": self.instructions(request.system),
            "input": self.transcript(request),
            "tools": self.tools(request),
            "max_output_tokens": request.max_tokens or settings.max_output_tokens,
            "reasoning": {"effort": reasoning_effort(model, request.effort or settings.effort)},
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
        if status in {"failed", "cancelled"}:
            # A 200 carrying a failure. Saying "Done." to the family would be a lie.
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
        # This API counts cached and newly-cached tokens inside input_tokens; the column means
        # "everything else", as it does on the other providers, so the three stay disjoint.
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
