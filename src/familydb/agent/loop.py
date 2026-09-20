"""The turn loop: call the model, run the tools it asks for, repeat until it answers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import anthropic

from familydb.agent.client import request_params
from familydb.config import Settings
from familydb.errors import AgentError
from familydb.store import calls
from familydb.store.calls import USAGE_KEYS
from familydb.store.db import transaction
from familydb.tools import ToolContext, ToolRegistry

log = logging.getLogger(__name__)

REFUSAL_REPLY = "Sorry, I couldn't process that message."


class MessagesAPI(Protocol):
    """The slice of `client.beta.messages` the loop uses; tests supply a scripted fake."""

    def create(self, **kwargs: Any) -> Any: ...


@dataclass
class TurnResult:
    status: Literal["ok", "refused", "failed"]
    text: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None


def _usage(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    return {key: getattr(usage, key, None) for key in USAGE_KEYS}


def _request_id(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    return headers.get("request-id") if headers is not None else None


def run_turn(
    *,
    api: MessagesAPI,
    settings: Settings,
    registry: ToolRegistry,
    ctx: ToolContext,
    system: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_iterations: int | None = None,
) -> TurnResult:
    """Drive one inbound message to a reply. `messages` is extended in place with the transcript."""
    params = request_params(settings)
    tools = tools if tools is not None else registry.api_tools(settings)
    limit = max_iterations or settings.agent_max_iterations
    actions: list[dict[str, Any]] = []
    totals: dict[str, int] = dict.fromkeys(USAGE_KEYS, 0)

    for iteration in range(1, limit + 1):
        started = time.monotonic()
        try:
            response = api.create(**params, system=system, tools=tools, messages=messages)
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
        duration_ms = int((time.monotonic() - started) * 1000)

        usage = _usage(response)
        for key in USAGE_KEYS:
            totals[key] += usage.get(key) or 0
        with transaction(ctx.conn):
            calls.log_llm_call(
                ctx.conn,
                message_id=ctx.message_id,
                iteration=iteration,
                model=settings.anthropic_model,
                served_model=getattr(response, "model", None),
                request_id=getattr(response, "_request_id", None),
                stop_reason=response.stop_reason,
                usage=usage,
                duration_ms=duration_ms,
                now=ctx.now_iso(),
            )

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None)
            log.warning("model refused the request (category=%s)", category)
            return TurnResult(
                "refused", REFUSAL_REPLY, actions, iteration, totals, error=f"refusal:{category}"
            )
        if response.stop_reason == "max_tokens":
            return TurnResult("failed", "", actions, iteration, totals, error="max_tokens")

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "pause_turn":
            continue  # a server-side tool paused; re-sending the transcript resumes it

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            text = "\n".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
            return TurnResult("ok", text, actions, iteration, totals)

        results: list[dict[str, Any]] = []
        for block in tool_uses:
            tool_started = time.monotonic()
            result = registry.dispatch(block.name, block.input, ctx)
            with transaction(ctx.conn):
                calls.log_tool_call(
                    ctx.conn,
                    message_id=ctx.message_id,
                    iteration=iteration,
                    tool_use_id=block.id,
                    tool_name=block.name,
                    input=block.input,
                    output=result.content,
                    is_error=result.is_error,
                    duration_ms=int((time.monotonic() - tool_started) * 1000),
                    now=ctx.now_iso(),
                )
            actions.append(result.summary)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.content,
                    "is_error": result.is_error,
                }
            )
        messages.append({"role": "user", "content": results})

    return TurnResult("failed", "", actions, limit, totals, error="max_iterations")
