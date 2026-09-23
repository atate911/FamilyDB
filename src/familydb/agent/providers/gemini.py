"""Gemini, through the google-genai SDK.

The third provider behind the same protocol. What differs here: the system prompt is one
`system_instruction`; tools are function declarations grouped into a Tool, and the hosted search
is a Tool of its own alongside them; a tool call's arguments arrive already parsed; caching is
implicit for a long enough prefix, so the cacheable flag steers nothing; and thinking is a token
budget rather than a named effort.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors

from familydb.agent.providers.base import (
    ModelReply,
    Stop,
    Surface,
    SystemBlock,
    ToolCall,
    ToolDef,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.errors import AgentError

log = logging.getLogger(__name__)

NAME = "gemini"
NO_CREDENTIALS = "no Gemini credentials configured: set GEMINI_API_KEY (see .env.example)"
# Our five effort names as a thinking budget in tokens. -1 lets the model decide.
THINKING = {"low": 0, "medium": -1, "high": -1, "xhigh": 24576, "max": 32768}
REFUSAL_REASONS = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "RECITATION",
    "IMAGE_SAFETY",
}
RETRYABLE_STATUS = (429, 500, 502, 503, 504)


def make_client(settings: Settings) -> Any:
    if not settings.gemini_api_key:
        raise AgentError(NO_CREDENTIALS, retryable=False)
    return genai.Client(api_key=settings.gemini_api_key)


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

    # -- wiring ---------------------------------------------------------------------------
    def configured(self) -> bool:
        return self._api is not None or bool(self.settings.gemini_api_key)

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = make_client(self.settings).models
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.settings.gemini_worker_model or self.settings.gemini_model
        return self.settings.gemini_model

    # -- translation ----------------------------------------------------------------------
    def instructions(self, system: list[SystemBlock]) -> str:
        return "\n\n".join(block.text for block in system if block.text)

    def tools(self, request: TurnRequest) -> list[dict[str, Any]]:
        """Our own tools in one group, then the hosted search as its own, which is how this API
        expects them. Models that cannot take both together will say so."""
        tools: list[dict[str, Any]] = []
        model = request.model or self.settings.gemini_model
        if request.web is not None and request.tools and not model.startswith("gemini-3"):
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
        config: dict[str, Any] = {
            "system_instruction": self.instructions(request.system) or None,
            "max_output_tokens": request.max_tokens or settings.max_output_tokens,
            "thinking_config": {"thinking_budget": THINKING.get(effort, -1)},
        }
        tools = self.tools(request)
        if (request.model or settings.gemini_model).startswith("gemini-3"):
            config["thinking_config"] = {"thinking_level": "LOW" if effort == "low" else "HIGH"}
        if request.web is not None and request.tools:
            config["tool_config"] = {"include_server_side_tool_invocations": True}
        if tools:
            config["tools"] = tools
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
            prompt = max(prompt - cached, 0)  # this API counts cached tokens inside the prompt
        answer = getattr(usage, "candidates_token_count", None)
        thoughts = getattr(usage, "thoughts_token_count", None)
        if thoughts:
            # Thinking is billed as output, so it belongs in the same column as the answer.
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

    # -- the call -------------------------------------------------------------------------
    def count_tokens(self, request: TurnRequest) -> int:
        payload = self.payload(request)
        counted = self.api.count_tokens(model=payload["model"], contents=payload["contents"])
        return int(counted.total_tokens)

    def send(self, request: TurnRequest) -> ModelReply:
        try:
            response = self.api.generate_content(**self.payload(request))
        except genai_errors.ServerError as exc:
            raise AgentError(f"server error: {exc}", retryable=True) from exc
        except genai_errors.ClientError as exc:
            status = _status(exc)
            raise AgentError(
                f"API error {status or '?'}: {exc}", retryable=status in RETRYABLE_STATUS
            ) from exc
        except genai_errors.APIError as exc:
            raise AgentError(
                f"Gemini error: {exc}", retryable=_status(exc) in RETRYABLE_STATUS
            ) from exc
        return self.reply(response)


def _declaration(tool: ToolDef) -> dict[str, Any]:
    """Our JSON Schema goes through untouched; this API takes it as it stands."""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters_json_schema": tool.schema,
    }


def _search(access: WebAccess) -> dict[str, Any]:
    """Grounded search. There is no per-turn cap on this API, so the iteration budget is it."""
    if access.user_location:
        log.debug("gemini search takes no location; %s is ignored", access.user_location)
    return {}
