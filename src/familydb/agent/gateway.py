"""The one door to a model. Everything that wants an answer from one comes through `ask`.

Each kind of call is declared once, in `KINDS`: what it is for, which model setting answers it
and at which level, which prompt it is given, which tools it may use, how much of the web it may
search, and which settings cap it. The caller says which kind and brings what is particular to
this one call (the conversation, and the context its tools run in); this module does the rest the
same way every time, and every call it makes is recorded under its kind.

What goes into the request, part by part, is built and measured by `agent.compose`. What the
answer means stays with the caller: this module knows how to ask, not what a good weekend is.
`docs/AI_CALLS.md` is the reasoning behind it; a test checks that nothing else in the package
starts a turn.

Hearing a voice note (`listen`) comes through here too. It is not a turn: a recording goes in and
its words come out, with no prompt file, no tools and one request. But it is paid for like any
other call, so the spending limit is checked first and the call is recorded under its own kind.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from familydb.agent import compose, spending
from familydb.agent.compose import Composed
from familydb.agent.history import HistoryTurn
from familydb.agent.loop import MessagesAPI, TurnResult, run_turn, worth_switching
from familydb.agent.providers import (
    Audio,
    Heard,
    Provider,
    Surface,
    fallback_for,
    for_surface,
    hearers,
    model_at,
    prices,
    ready,
)
from familydb.clock import Clock
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls
from familydb.store.db import transaction
from familydb.tools import ToolContext, ToolRegistry

log = logging.getLogger(__name__)

Kind = Literal["chat", "digest", "retry", "enrich", "discover"]


@dataclass(frozen=True)
class CallSpec:
    """Everything about one kind of call that does not change from one call to the next."""

    kind: Kind
    purpose: str  # for people: what these calls were for, as `debug cost` and /status say it
    surface: Surface  # which model answers: the chat model, or the lookup (worker) model
    level: str  # the setting naming how strong a model answers (catalog.LEVELS)
    prompt: str  # the file in agent/prompts/; "system" also brings the family and the ideas
    tools: tuple[str, ...] | None  # None: every chat tool, the same list on every turn
    hand_back: tuple[str, ...] = ()  # the tools whose success is the result of a worker turn
    # Tools that may end a chat turn with the reply they carry, when they are all a step did:
    # remembering needs no second call just to say "noted" (tools/memory.py).
    closes: tuple[str, ...] = ()
    web_searches: int | None = None  # hosted web search, capped; None means no web at all
    iterations: str = "agent_max_iterations"  # the setting that caps model calls in one turn
    effort: str | None = None  # the setting naming the effort; None is the provider's default
    max_tokens: int | None = None  # the output cap, thinking included; None: max_output_tokens


_CHAT = {
    "surface": "chat",
    "level": "chat_level",
    "prompt": "system",
    "tools": None,
    "closes": ("remember",),
}
# A worker's only real output is one hand-back call, a few hundred tokens. The cap bounds a
# runaway turn and leaves room for the thinking every vendor counts against it at low effort.
WORKER_MAX_TOKENS = 4000
_WORKER = {
    "surface": "worker",
    "level": "lookup_level",
    "iterations": "worker_max_iterations",
    "effort": "worker_effort",
    "max_tokens": WORKER_MAX_TOKENS,
}

KINDS: dict[str, CallSpec] = {
    spec.kind: spec
    for spec in (
        CallSpec("chat", "answering the family", **_CHAT),
        CallSpec("digest", "the weekend digest", **{**_CHAT, "level": "digest_level"}),
        CallSpec("retry", "answering a message again after a failure", **_CHAT),
        CallSpec(
            "enrich",
            "looking ideas up",
            prompt="enrich",
            tools=("save_place", "skip_place"),
            hand_back=("save_place", "skip_place"),
            web_searches=3,
            **_WORKER,
        ),
        CallSpec(
            "discover",
            "searching for what is on",
            prompt="discover",
            tools=("report_finds",),
            hand_back=("report_finds",),
            web_searches=4,
            **_WORKER,
        ),
    )
}


# The one kind of call that is not a turn: hearing a voice note, recorded under this kind.
LISTEN = "transcribe"
LISTEN_PURPOSE = "listening to voice notes"


def spec(kind: str) -> CallSpec:
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"no such kind of model call: {kind}") from None


def purpose(kind: str | None) -> str:
    """What a recorded call was for, in words. Calls from before kinds were recorded have none."""
    if kind is None:
        return "not recorded (older calls)"
    if kind == LISTEN:
        return LISTEN_PURPOSE
    return KINDS[kind].purpose if kind in KINDS else kind


def answering(
    settings: Settings, kind: str, api: MessagesAPI | None = None
) -> tuple[Provider, str]:
    """Who answers this kind of call first, and with which model: what `ask` would send to.

    For the pages and the command line, which say it without asking anything of a model.
    """
    call = spec(kind)
    provider = for_surface(settings, call.surface, api=api)
    return provider, model_at(provider, call.surface, getattr(settings, call.level))


def can_ask(settings: Settings, kind: str, api: MessagesAPI | None = None) -> bool:
    """Whether any model can take this kind of call: a key for the chosen one or for the spare."""
    return ready(settings, spec(kind).surface, api=api)


def build_request(
    kind: str,
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    registry: ToolRegistry,
    provider: Provider,
    current: list[str],
    history: Sequence[HistoryTurn] = (),
    user_location: dict[str, Any] | None = None,
) -> Composed:
    """The request `ask` would open with, and the size of each part of it.

    `familydb debug prompt` prints it without sending, so what it shows is what goes.
    """
    call = spec(kind)
    composed = compose.compose(
        call,
        conn=conn,
        settings=settings,
        registry=registry,
        provider=provider,
        current=current,
        history=history,
        user_location=user_location,
    )
    if call.max_tokens is not None:
        # Never above the ceiling the family set for every call.
        composed.request.max_tokens = min(call.max_tokens, settings.max_output_tokens)
    return composed


def ask(
    kind: str,
    *,
    settings: Settings,
    registry: ToolRegistry,
    ctx: ToolContext,
    current: list[str],
    history: Sequence[HistoryTurn] = (),
    api: MessagesAPI | None = None,
    provider: Provider | None = None,
    fallback: Provider | None = None,
    user_location: dict[str, Any] | None = None,
) -> TurnResult:
    """Ask a model: one turn of the given kind, run to its answer, every call recorded.

    `current` is what this call is about (today's date, who is asking, what they said) and
    `history` the conversation before it; `ctx` is what the tools run in. An injected `api` (a
    test's fake) means the configured provider and no spare; otherwise the spare is whichever
    other provider is switched on and has a key.
    """
    call = spec(kind)
    chosen = provider or for_surface(settings, call.surface, api=api)
    spare = fallback
    if spare is None and api is None:
        spare = fallback_for(settings, call.surface, chosen.name)
    composed = build_request(
        kind,
        conn=ctx.conn,
        settings=settings,
        registry=registry,
        provider=chosen,
        current=current,
        history=history,
        user_location=user_location,
    )
    request = composed.request
    return run_turn(
        provider=chosen,
        surface=call.surface,
        level=getattr(settings, call.level),
        fallback=spare,
        settings=settings,
        registry=registry,
        ctx=ctx,
        system=request.system,
        messages=request.messages,
        tools=request.tools,
        web=request.web,
        max_iterations=getattr(settings, call.iterations),
        model=request.model,
        effort=request.effort,
        max_tokens=request.max_tokens,
        kind=call.kind,
        sections=composed.sections,
        final_tools=frozenset(call.hand_back),
        closing_tools=frozenset(call.closes),
    )


def handed_back(call: CallSpec, result: TurnResult, tool: str | None = None) -> bool:
    """Whether a worker turn delivered its result: a successful call to its hand-back tool."""
    wanted = (tool,) if tool else call.hand_back
    return any(a.get("tool") in wanted and a.get("ok") for a in result.actions)


def can_listen(settings: Settings, audio: Any = None) -> bool:
    """Whether any model can hear a voice note: one that can hear, with a key, is switched on."""
    return bool(hearers(settings, audio=audio))


def listen(
    *,
    settings: Settings,
    conn: sqlite3.Connection,
    clock: Clock,
    audio: Audio,
    hints: str = "",
    message_id: int | None = None,
    api: Any = None,
) -> Heard:
    """Hear one recording: its words, the call checked against the limit and recorded first.

    Asked of whoever `providers.hearers` puts first; one that is busy, unreachable or has lost
    its key hands over to the next, if there is one. Nothing is done with the words here: the
    caller decides what they mean, as `ask` leaves the answer to its caller. An injected `api`
    (a test's stand-in) is the hearing endpoint of whoever would be asked.
    """
    candidates = hearers(settings, audio=api)
    if not candidates:
        raise AgentError("no model that can hear voice notes has a key", retryable=False)
    failure: AgentError | None = None
    for provider in candidates:
        model = provider.listener()
        held = spending.admit(
            conn,
            settings,
            clock.now(),
            spending.estimate_hearing(provider.name, model, audio.seconds),
        )
        started = time.monotonic()
        try:
            heard = provider.transcribe(audio, hints)
        except AgentError as exc:
            _let_go(conn, held, clock.now())
            if not worth_switching(exc):
                raise
            log.warning("%s could not hear a voice note (%s)", provider.name, exc)
            failure = exc
            continue
        except BaseException:
            _let_go(conn, held, clock.now())
            raise
        dollars, listed = prices.cost(provider.name, heard.model or model, heard.usage)
        with transaction(conn):
            calls.log_llm_call(
                conn,
                message_id=message_id,
                iteration=1,
                model=model or provider.name,
                served_model=heard.model,
                request_id=heard.request_id,
                stop_reason="end",
                usage=heard.usage,
                duration_ms=int((time.monotonic() - started) * 1000),
                now=utc_iso(clock.now()),
                provider=provider.name,
                cost_usd=dollars,
                cost_estimated=not listed,
                kind=LISTEN,
            )
            spending.settle(conn, held, clock.now())
        return heard
    assert failure is not None
    raise failure


def _let_go(conn: sqlite3.Connection, held: int, now: datetime) -> None:
    with transaction(conn):
        spending.settle(conn, held, now)
