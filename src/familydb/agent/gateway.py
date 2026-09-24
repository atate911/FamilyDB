"""The one door to a model. Everything that wants an answer from one comes through `ask`.

Each kind of call is declared once, in `KINDS`: what it is for, which model setting answers it,
which prompt it is given, which tools it may use, how much of the web it may search, and which
settings cap it. The caller says which kind and brings what is particular to this one call (the
conversation, and the context its tools run in); this module does the rest the same way every
time, and every call it makes is recorded under its kind.

What goes into the request, part by part, is built and measured by `agent.compose`. What the
answer means stays with the caller: this module knows how to ask, not what a good weekend is.
`docs/AI_CALLS.md` is the reasoning behind it; a test checks that nothing else in the package
starts a turn.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from familydb.agent import compose
from familydb.agent.compose import Composed
from familydb.agent.history import HistoryTurn
from familydb.agent.loop import MessagesAPI, TurnResult, run_turn
from familydb.agent.providers import Provider, Surface, fallback_for, for_surface, ready
from familydb.config import Settings
from familydb.tools import ToolContext, ToolRegistry

Kind = Literal["chat", "digest", "retry", "enrich", "discover"]


@dataclass(frozen=True)
class CallSpec:
    """Everything about one kind of call that does not change from one call to the next."""

    kind: Kind
    purpose: str  # for people: what these calls were for, as `debug cost` and /status say it
    surface: Surface  # which model answers: the chat model, or the lookup (worker) model
    prompt: str  # the file in agent/prompts/; "system" also brings the family and the ideas
    tools: tuple[str, ...] | None  # None: every chat tool, the same list on every turn
    hand_back: tuple[str, ...] = ()  # the tools whose success is the result of a worker turn
    web_searches: int | None = None  # hosted web search, capped; None means no web at all
    iterations: str = "agent_max_iterations"  # the setting that caps model calls in one turn
    effort: str | None = None  # the setting naming the effort; None is the provider's default
    max_tokens: int | None = None  # the output cap, thinking included; None: max_output_tokens

    @property
    def is_worker(self) -> bool:
        return self.web_searches is not None


_CHAT = {"surface": "chat", "prompt": "system", "tools": None}
# A worker's only real output is one hand-back call, a few hundred tokens. The cap bounds a
# runaway turn and leaves room for the thinking every vendor counts against it at low effort.
WORKER_MAX_TOKENS = 4000
_WORKER = {
    "surface": "worker",
    "iterations": "worker_max_iterations",
    "effort": "worker_effort",
    "max_tokens": WORKER_MAX_TOKENS,
}

KINDS: dict[str, CallSpec] = {
    spec.kind: spec
    for spec in (
        CallSpec("chat", "answering the family", **_CHAT),
        CallSpec("digest", "the weekend digest", **_CHAT),
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


def spec(kind: str) -> CallSpec:
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"no such kind of model call: {kind}") from None


def purpose(kind: str | None) -> str:
    """What a recorded call was for, in words. Calls from before kinds were recorded have none."""
    if kind is None:
        return "not recorded (older calls)"
    return KINDS[kind].purpose if kind in KINDS else kind


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
    )


def handed_back(call: CallSpec, result: TurnResult, tool: str | None = None) -> bool:
    """Whether a worker turn delivered its result: a successful call to its hand-back tool."""
    wanted = (tool,) if tool else call.hand_back
    return any(a.get("tool") in wanted and a.get("ok") for a in result.actions)
