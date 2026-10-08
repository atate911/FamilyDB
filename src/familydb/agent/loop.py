"""The turn loop: call the model, run the tools it asks for, repeat until it answers. Vendor-blind:
it builds a provider-neutral request and reads back a ModelReply."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from familydb import alerts
from familydb.agent import spending, transcript
from familydb.agent.compose import exchange_chars
from familydb.agent.providers import model_at, prices
from familydb.agent.providers.base import (
    Exchange,
    Message,
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
    if exc.retryable or exc.trouble in ("credit", "key", "model"):
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
    level: str = "everyday",
    fallback: Provider | None = None,
    kind: str | None = None,
    sections: dict[str, int] | None = None,
    final_tools: frozenset[str] = frozenset(),
    closing_tools: frozenset[str] = frozenset(),
) -> TurnResult:
    """Drive one inbound message to a reply; callers go through `gateway.ask`, which passes `kind`
    and `sections` (request part sizes) to be recorded with every call.

    A `fallback` takes only a failed first call, at the same `level`: after a tool has run,
    starting again elsewhere would repeat its writes (the retry job's business).

    `final_tools` (a worker's hand-back) end the turn once one succeeds and nothing else in that
    step failed, saving a call. `closing_tools` end a chat turn with the reply they carried
    (`ToolContext.offer_reply`) only when they are all the step did and all succeeded.
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
    ctx.allowed_tools = frozenset(tool.name for tool in request.tools)
    if ctx.turn is None:
        ctx.turn = uuid.uuid4().hex[:16]
    actions: list[dict[str, Any]] = []
    totals: dict[str, int] = dict.fromkeys(USAGE_KEYS, 0)

    active = provider
    if fallback is not None and not active.configured():
        log.warning("%s has no credentials; asking %s instead", active.name, fallback.name)
        active = fallback
        # The caller's model belonged to the provider we just left.
        request.model = model_at(active, surface, level)  # type: ignore[arg-type]

    for iteration in range(1, limit + 1):
        try:
            held = spending.admit(
                ctx.conn, settings, ctx.clock.now(), _estimate(request, active, surface, settings)
            )
        except spending.SpendingLimitReached as exc:
            written = {spec.name for spec in registry.specs() if spec.writes}
            completed = [a for a in actions if a.get("ok") and a.get("tool") in written]
            if not completed:
                raise
            return TurnResult(
                "ok",
                spending.completed_reply(completed, settings, ctx.message_id, plain=ctx.plain),
                actions,
                iteration - 1,
                totals,
                error=str(exc),
                provider=active.name,
            )
        started = time.monotonic()
        try:
            try:
                reply = active.send(request)
            except AgentError as exc:
                alerts.noticed(
                    ctx.conn,
                    exc,
                    provider=active.name,
                    now=ctx.clock.now(),
                    model=request.model or active.model_for(surface),  # type: ignore[arg-type]
                )
                _failed(ctx, settings, request, active, surface, exc, iteration, kind)
                switchable = fallback is not None and active is not fallback
                if not (switchable and first_call_only(request) and worth_switching(exc)):
                    raise
                log.warning(
                    "%s could not take this (%s); asking %s", active.name, exc, fallback.name
                )
                active = fallback
                request.model = model_at(active, surface, level)  # type: ignore[arg-type]
                spending.adjust(
                    ctx.conn,
                    settings,
                    ctx.clock.now(),
                    held,
                    _estimate(request, active, surface, settings),
                )
                try:
                    reply = active.send(request)
                except AgentError as spare_exc:
                    alerts.noticed(
                        ctx.conn,
                        spare_exc,
                        provider=active.name,
                        now=ctx.clock.now(),
                        model=request.model or active.model_for(surface),  # type: ignore[arg-type]
                    )
                    _failed(ctx, settings, request, active, surface, spare_exc, iteration, kind)
                    # Keep the primary's (possibly retryable) failure even if the spare says 400.
                    log.warning("%s could not take it either: %s", active.name, spare_exc)
                    raise exc from spare_exc
        except BaseException:
            with transaction(ctx.conn):
                spending.settle(ctx.conn, held, ctx.clock.now())
            raise
        duration_ms = int((time.monotonic() - started) * 1000)

        for key in USAGE_KEYS:
            totals[key] += reply.usage.get(key) or 0
        asked = request.model or active.model_for(surface)
        # Priced by the name the company answered with, unless that is a snapshot or alias nobody
        # priced and the model asked for is: one asked for by name costs what that name does.
        priced_as = reply.model or asked
        if prices.price(active.name, priced_as) is None and prices.price(active.name, asked):
            priced_as = asked
        dollars, listed = prices.cost(
            active.name,
            priced_as,
            reply.usage,
            cache_ttl=settings.anthropic_cache_ttl,
        )
        with transaction(ctx.conn):
            call_id = calls.log_llm_call(
                ctx.conn,
                message_id=ctx.message_id,
                iteration=iteration,
                model=asked,
                served_model=reply.model,
                request_id=reply.request_id,
                stop_reason=reply.stop,
                usage=reply.usage,
                duration_ms=duration_ms,
                now=ctx.now_iso(),
                provider=active.name,
                cost_usd=dollars,
                cost_estimated=not listed,
                kind=kind,
                sections=_sizes(sections, request),
                turn=ctx.turn,
                about=ctx.about,
            )
            spending.settle(ctx.conn, held, ctx.clock.now())
            alerts.answered(ctx.conn, active.name, asked)
        transcript.keep_answer(
            ctx.conn,
            settings,
            request,
            reply,
            call_id=call_id,
            message_id=ctx.message_id,
            turn=ctx.turn,
            iteration=iteration,
            kind=kind,
            about=ctx.about,
            provider=active.name,
            model=asked,
            now=ctx.clock.now(),
        )
        if reply.dropped:
            alerts.dropped(ctx.conn, active.name, asked, reply.dropped, ctx.clock.now())

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
            continue  # a hosted tool paused the turn; resending the transcript resumes it
        if not reply.tool_calls:
            return TurnResult("ok", reply.text, actions, iteration, totals, provider=active.name)

        for call in reply.tool_calls:
            # Kept as it goes (tool_calls), with the turn and the model's id for the call.
            result = registry.dispatch(
                call.name, call.arguments, ctx, call_id=call.id, iteration=iteration
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
        if _handed_back(exchange, final_tools):
            return TurnResult("ok", reply.text, actions, iteration, totals, provider=active.name)
        offered = ctx.take_reply()
        if offered and _closed(exchange, closing_tools):
            return TurnResult("ok", offered, actions, iteration, totals, provider=active.name)

    return TurnResult(
        "failed", "", actions, limit, totals, error="max_iterations", provider=active.name
    )


def _failed(
    ctx: ToolContext,
    settings: Settings,
    request: TurnRequest,
    provider: Provider,
    surface: str,
    exc: AgentError,
    iteration: int,
    kind: str | None,
) -> None:
    """Write down a call that got no answer, with what it was sent (Troubleshooting)."""
    transcript.keep_failure(
        ctx.conn,
        settings,
        request,
        exc,
        message_id=ctx.message_id,
        turn=ctx.turn,
        iteration=iteration,
        kind=kind,
        about=ctx.about,
        provider=provider.name,
        model=request.model or provider.model_for(surface),  # type: ignore[arg-type]
        now=ctx.clock.now(),
    )


def _handed_back(exchange: Exchange, final_tools: frozenset[str]) -> bool:
    """Whether a final tool ran and nothing in the step failed."""
    outcomes = exchange.outcomes
    if any(outcome.is_error for outcome in outcomes):
        return False
    return any(outcome.name in final_tools for outcome in outcomes)


def _closed(exchange: Exchange, closing_tools: frozenset[str]) -> bool:
    """Whether the step was only closing tools, all of which worked."""
    outcomes = exchange.outcomes
    return bool(outcomes) and all(
        outcome.name in closing_tools and not outcome.is_error for outcome in outcomes
    )


def _estimate(request: TurnRequest, provider: Provider, surface: str, settings: Settings) -> float:
    """The most this call could cost, held against the limit in flight."""
    chars = (
        sum(len(block.text) for block in request.system)
        + sum(len(message.text) for message in request.messages)
        + sum(len(tool.description) + len(json.dumps(tool.schema)) for tool in request.tools)
        + exchange_chars(request.exchanges)
    )
    return spending.estimate(
        provider.name,
        request.model or provider.model_for(surface),
        input_chars=chars,
        max_tokens=request.max_tokens or settings.max_output_tokens,
        searches=(request.web.max_uses or 0) if request.web else 0,
        cache_ttl=settings.anthropic_cache_ttl,
    )


def _sizes(sections: dict[str, int] | None, request: TurnRequest) -> dict[str, int] | None:
    if sections is None:
        return None
    earlier = exchange_chars(request.exchanges)
    return {**sections, "earlier steps": earlier} if earlier else dict(sections)


def first_call_only(request: TurnRequest) -> bool:
    """Whether nothing has run yet, so starting again elsewhere repeats no side effect."""
    return not request.exchanges


__all__ = [
    "REFUSAL_REPLY",
    "MessagesAPI",
    "TurnResult",
    "first_call_only",
    "run_turn",
    "worth_switching",
]
