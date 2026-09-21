"""The turn loop: call the model, run the tools it asks for, repeat until it answers.

Nothing here knows which vendor is answering. The loop builds a provider-neutral request, hands
it to a Provider, and reads back a ModelReply. What that costs, which tools ran and how it ended
are logged the same way whoever served it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from familydb.agent.providers.base import (
    Exchange,
    Message,
    ModelReply,
    Provider,
    SystemBlock,
    ToolDef,
    ToolOutcome,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.errors import AgentError
from familydb.store import calls
from familydb.store.calls import USAGE_KEYS
from familydb.store.db import transaction
from familydb.tools import ToolContext, ToolRegistry

log = logging.getLogger(__name__)

REFUSAL_REPLY = "Sorry, I couldn't process that message."


class MessagesAPI(Protocol):
    """The slice of an SDK the providers use; tests supply a scripted fake."""

    def create(self, **kwargs: Any) -> Any: ...


@dataclass
class TurnResult:
    status: Literal["ok", "refused", "failed"]
    text: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    provider: str | None = None


def worth_switching(exc: AgentError) -> bool:
    """Whether the other provider might do better: this one is busy, unreachable or unusable."""
    if exc.retryable:
        return True
    reason = str(exc).lower()
    return "credential" in reason or "api key" in reason or "authentication" in reason


def run_turn(
    *,
    provider: Provider,
    settings: Settings,
    registry: ToolRegistry,
    ctx: ToolContext,
    system: list[SystemBlock],
    messages: list[Message],
    tools: list[ToolDef] | None = None,
    web: WebAccess | None = None,
    max_iterations: int | None = None,
    model: str | None = None,
    effort: str | None = None,
    max_tokens: int | None = None,
    surface: str = "chat",
    fallback: Provider | None = None,
) -> TurnResult:
    """Drive one inbound message to a reply.

    With a `fallback` provider, a first call the chosen one cannot take is tried there instead.
    Only the first call: once a tool has run, starting again elsewhere would repeat whatever it
    did, and a half-finished turn is the retry job's business rather than this one's.
    """
    request = TurnRequest(
        system=system,
        messages=messages,
        tools=tools if tools is not None else registry.tool_defs(),
        web=web,
        model=model,
        effort=effort,
        max_tokens=max_tokens,
    )
    limit = max_iterations or settings.agent_max_iterations
    actions: list[dict[str, Any]] = []
    totals: dict[str, int] = dict.fromkeys(USAGE_KEYS, 0)

    active = provider
    if fallback is not None and not active.configured():
        log.warning("%s has no credentials; asking %s instead", active.name, fallback.name)
        active = fallback
        # Whatever model the caller named belonged to the provider we just left.
        request.model = active.model_for(surface)

    for iteration in range(1, limit + 1):
        started = time.monotonic()
        try:
            reply = active.send(request)
        except AgentError as exc:
            switchable = fallback is not None and active is not fallback
            if not (switchable and first_call_only(request) and worth_switching(exc)):
                raise
            log.warning("%s could not take this (%s); asking %s", active.name, exc, fallback.name)
            active = fallback
            request.model = active.model_for(surface)
            try:
                reply = active.send(request)
            except AgentError as spare_exc:
                # 4. Report the first failure, not the second. A message the primary would have
                # answered after a pause must not be given up on because the spare said 400.
                log.warning("%s could not take it either: %s", active.name, spare_exc)
                raise exc from spare_exc
        duration_ms = int((time.monotonic() - started) * 1000)

        for key in USAGE_KEYS:
            totals[key] += reply.usage.get(key) or 0
        with transaction(ctx.conn):
            calls.log_llm_call(
                ctx.conn,
                message_id=ctx.message_id,
                iteration=iteration,
                model=request.model or active.model_for(surface),
                served_model=reply.model,
                request_id=reply.request_id,
                stop_reason=reply.stop,
                usage=reply.usage,
                duration_ms=duration_ms,
                now=ctx.now_iso(),
            )

        if reply.stop == "refusal":
            log.warning("%s refused the request (category=%s)", active.name, reply.refusal)
            return TurnResult(
                "refused",
                REFUSAL_REPLY,
                actions,
                iteration,
                totals,
                error=f"refusal:{reply.refusal}",
                provider=active.name,
            )
        if reply.stop == "max_tokens":
            return TurnResult(
                "failed", "", actions, iteration, totals, error="max_tokens", provider=active.name
            )

        exchange = Exchange(reply=reply)
        request.exchanges.append(exchange)
        if reply.stop == "paused":
            continue  # a hosted tool paused the turn; sending the transcript back resumes it
        if not reply.tool_calls:
            return TurnResult("ok", reply.text, actions, iteration, totals, provider=active.name)

        for call in reply.tool_calls:
            tool_started = time.monotonic()
            result = registry.dispatch(call.name, call.arguments, ctx)
            with transaction(ctx.conn):
                calls.log_tool_call(
                    ctx.conn,
                    message_id=ctx.message_id,
                    iteration=iteration,
                    tool_use_id=call.id,
                    tool_name=call.name,
                    input=call.arguments,
                    output=result.content,
                    is_error=result.is_error,
                    duration_ms=int((time.monotonic() - tool_started) * 1000),
                    now=ctx.now_iso(),
                )
            actions.append(result.summary)
            exchange.outcomes.append(
                ToolOutcome(
                    id=call.id,
                    name=call.name,
                    content=result.content,
                    is_error=result.is_error,
                )
            )

    return TurnResult(
        "failed", "", actions, limit, totals, error="max_iterations", provider=active.name
    )


def first_call_only(request: TurnRequest) -> bool:
    """Whether nothing has been run yet, so starting again elsewhere repeats no side effect."""
    return not request.exchanges


__all__ = [
    "REFUSAL_REPLY",
    "AgentError",
    "Exchange",
    "Message",
    "MessagesAPI",
    "ModelReply",
    "Provider",
    "SystemBlock",
    "ToolDef",
    "TurnResult",
    "WebAccess",
    "first_call_only",
    "run_turn",
    "worth_switching",
]
