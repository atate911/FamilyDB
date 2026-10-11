"""The one door to a model (`docs/AI_CALLS.md`): `KINDS` declares each kind of call, `ask` runs one
and records it under its kind. `listen` (voice note) and `look` (photo) are single requests, not
turns, but are limited and recorded the same way. What an answer means stays with the caller."""

from __future__ import annotations

import dataclasses
import logging
import sqlite3
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from familydb import alerts
from familydb.agent import compose, spending, transcript, uses
from familydb.agent.compose import Composed
from familydb.agent.history import HistoryTurn
from familydb.agent.loop import MessagesAPI, TurnResult, run_turn, worth_switching
from familydb.agent.prompt import load_prompt
from familydb.agent.providers import (
    Audio,
    Heard,
    Picture,
    Provider,
    Seen,
    Surface,
    Withheld,
    can_search,
    fallback_for,
    model_at,
    prices,
)
from familydb.base.clock import Clock
from familydb.base.config import Settings
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.store import calls
from familydb.store.db import transaction
from familydb.tools import ToolContext, ToolRegistry

log = logging.getLogger(__name__)

Kind = Literal[
    "chat",
    "digest",
    "retry",
    "enrich",
    "discover",
    "places",
    "scout",
    "find_feeds",
    "choose",
    "judge",
    "price_check",
]


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
    # Tools whose reply may end a chat turn when they are all a step did (no "noted" call).
    closes: tuple[str, ...] = ()
    web_searches: int | None = None  # hosted web search, capped; None means no web at all
    iterations: str = "agent_max_iterations"  # the setting that caps model calls in one turn
    effort: str | None = None  # the setting naming the effort; None is the provider's default
    max_tokens: int | None = None  # the output cap, thinking included; None: max_output_tokens
    # The setting naming its month's budget in dollars, shared by the kinds that name the same
    # one (`month_room`); None: the day's limit alone bounds it.
    budget: str | None = None


_CHAT = {
    "surface": "chat",
    "level": "chat_level",
    "prompt": "system",
    "tools": None,
    "closes": ("remember",),
}
# A worker's output is one hand-back call; the cap bounds a runaway turn and leaves room for
# the thinking vendors count against it.
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
        # A place nothing saved fits, found on the web for now or the next days, while the family
        # has `find_places` on (suggest/places.py); never an event, which is discovery's.
        CallSpec(
            "places",
            "searching for a place nothing saved fits",
            prompt="places",
            tools=("report_finds",),
            hand_back=("report_finds",),
            web_searches=4,
            **_WORKER,
        ),
        # The weekly search for what is on near home over the next four weeks (jobs/happening.py):
        # discovery's prompt and hand-back, a kind of its own so its cost is held to the
        # family's monthly budget for it rather than counted with the chat's.
        CallSpec(
            "scout",
            "searching for what is on near home",
            budget="happening_budget",
            prompt="discover",
            tools=("report_finds",),
            hand_back=("report_finds",),
            web_searches=4,
            **_WORKER,
        ),
        # Looking for event calendars near home to offer the family (jobs/happening.py): what
        # it hands back is only addresses, each read by code before anyone is offered it.
        CallSpec(
            "find_feeds",
            "looking for event calendars near home",
            budget="happening_budget",
            prompt="find_feeds",
            tools=("report_feeds",),
            hand_back=("report_feeds",),
            web_searches=6,
            **_WORKER,
        ),
        # Choosing what to suggest for a planning question (suggest/choosing.py): the family's own
        # words and memories go into it, so it answers on the chat surface, the company the
        # family already writes to, at the level the family chose for it, with no web. Its only
        # output is one hand-back, checked by code; at most two calls, since each re-sends the
        # whole dossier at the strong level.
        CallSpec(
            "choose",
            "choosing what to suggest",
            budget="choose_budget",
            surface="chat",
            level="choose_level",
            prompt="choose",
            tools=("give_picks",),
            hand_back=("give_picks",),
            iterations="choose_max_iterations",
            max_tokens=6000,
        ),
        # Weighs a change the code narrowed to a few options (familydb/judgement.py); no web.
        CallSpec(
            "judge",
            "weighing a change in the models",
            budget="judgement_budget",
            prompt="judge",
            tools=("give_judgement",),
            hand_back=("give_judgement",),
            **{**_WORKER, "level": "judgement_level", "effort": None},
        ),
        # Extraction, not judgement: the lookup model reads a company's pricing page.
        CallSpec(
            "price_check",
            "checking a disputed price",
            budget="judgement_budget",
            prompt="price_check",
            tools=("report_price",),
            hand_back=("report_price",),
            web_searches=3,
            **_WORKER,
        ),
    )
}


LISTEN = "transcribe"
LISTEN_PURPOSE = "listening to voice notes"
LOOK = "look"
LOOK_PURPOSE = "reading photos"


def spec(kind: str) -> CallSpec:
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"no such kind of model call: {kind}") from None


def purpose(kind: str | None) -> str:
    """What a recorded call was for, in words."""
    if kind is None:
        return "not recorded (older calls)"
    if kind == LISTEN:
        return LISTEN_PURPOSE
    if kind == LOOK:
        return LOOK_PURPOSE
    return KINDS[kind].purpose if kind in KINDS else kind


def month_room(
    conn: sqlite3.Connection, settings: Settings, kind: str, now: datetime, *, estimate: float = 0.0
) -> bool:
    """Whether this kind's month budget has room for one more call costing `estimate`: the
    setting its spec names, against what every kind naming that setting has cost since the
    family's month began. Always, for a kind with no budget of its own; never, for one whose
    budget is unset or zero."""
    call = spec(kind)
    if call.budget is None:
        return True
    budget = getattr(settings, call.budget)
    if not budget:
        return False
    sharing = tuple(name for name, each in KINDS.items() if each.budget == call.budget)
    spent = calls.spent_on(conn, sharing, since=spending.month_start(settings, now))
    return spent + estimate <= budget


def answering(
    settings: Settings, kind: str, api: MessagesAPI | None = None
) -> tuple[Provider, str]:
    """Who answers this kind of call first, and with which model, without asking a model."""
    who = uses.answering(settings, kind, api=api)
    return who.provider, who.model


def can_ask(settings: Settings, kind: str, api: MessagesAPI | None = None) -> bool:
    """Whether any model can take this kind of call: a key for the chosen one or for the spare."""
    call = spec(kind)
    if not uses.on(settings, uses.use_of(kind).key):
        return False
    web = call.web_searches is not None
    primary = uses.answering(settings, kind, api=api).provider
    if web and api is None and not can_search(primary):
        return False
    return (
        primary.configured()
        or fallback_for(settings, call.surface, primary.name, web=web) is not None
    )


def build_request(
    kind: str,
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    registry: ToolRegistry,
    current: list[str],
    history: Sequence[HistoryTurn] = (),
    user_location: dict[str, Any] | None = None,
    who: uses.Answering | None = None,
    api: MessagesAPI | None = None,
) -> Composed:
    """The request `ask` would open with (`debug prompt` prints it), and each part's size. `who`
    is who answers it (`uses.answering`), worked out here when not given."""
    call = spec(kind)
    who = who or uses.answering(settings, kind, api=api)
    composed = compose.compose(
        call,
        conn=conn,
        settings=settings,
        registry=registry,
        model=who.model,
        effort=who.effort,
        current=current,
        history=history,
        user_location=user_location,
    )
    if call.max_tokens is not None:
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
    """One turn of `kind`, run to its answer, every call recorded. `current` is the uncached turn
    (date, sender, message). An injected `api` (a test's fake) means no spare provider."""
    call = spec(kind)
    # Who answers, worked out once here and passed on whole; a stand-in answers at the level of
    # the model the use was chosen to, not the setting's.
    who = uses.answering(settings, kind, api=api)
    web = call.web_searches is not None
    chosen = provider or who.provider
    if chosen.name != who.provider.name:  # a caller's own provider: its model at the level
        who = dataclasses.replace(
            who, provider=chosen, model=model_at(chosen, call.surface, who.level)
        )
    spare = fallback
    if spare is None and api is None:
        spare = fallback_for(settings, call.surface, chosen.name, web=web)
    if spare is not None and spending.company_full(
        ctx.conn, settings, ctx.clock.now(), chosen.name
    ):
        # The company's month is spent: it is not asked, and the loop goes to the stand-in.
        chosen = Withheld(chosen)
    composed = build_request(
        kind,
        conn=ctx.conn,
        settings=settings,
        registry=registry,
        current=current,
        history=history,
        user_location=user_location,
        who=who,
    )
    request = composed.request
    return run_turn(
        provider=chosen,
        surface=call.surface,
        level=who.level,
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
    return bool(uses.hearing(settings, audio=audio))


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
    """Hear one recording, limit-checked and recorded; `hearers` order, next on failure."""
    candidates = uses.hearing(settings, audio=api)
    if not candidates:
        raise AgentError("no model that can hear voice notes has a key", retryable=False)
    return _written_down(
        candidates,
        settings=settings,
        conn=conn,
        clock=clock,
        message_id=message_id,
        kind=LISTEN,
        sent=f"[a voice note, {audio.seconds} seconds, {audio.mime}; the recording is not kept]"
        + (f"\n[hints] {hints}" if hints else ""),
        doing="hear a voice note",
        estimate=lambda provider, model: spending.estimate_hearing(
            provider.name, model, audio.seconds
        ),
        request=lambda provider, model: provider.transcribe(audio, hints, model),
    )


def can_look(settings: Settings, api: Any = None) -> bool:
    """Whether any model can look at a photo: one with a key, which all three can."""
    return bool(uses.looking(settings, api=api))


def look(
    *,
    settings: Settings,
    conn: sqlite3.Connection,
    clock: Clock,
    picture: Picture,
    hints: str = "",
    message_id: int | None = None,
    api: Any = None,
) -> Seen:
    """Write down what one photo shows (`prompts/look.md`), limit-checked and recorded;
    `providers.lookers` order, next on failure."""
    candidates = uses.looking(settings, api=api)
    if not candidates:
        raise AgentError("no model that can look at photos has a key", retryable=False)
    ask = " ".join(part for part in (load_prompt("look").strip(), hints) if part)
    return _written_down(
        candidates,
        settings=settings,
        conn=conn,
        clock=clock,
        message_id=message_id,
        kind=LOOK,
        sent=f"[a photo, {picture.mime}; the picture is not kept]\n[asked] {ask}",
        doing="look at a photo",
        estimate=lambda provider, model: spending.estimate_looking(provider.name, model),
        request=lambda provider, model: provider.describe(picture, ask, model),
    )


def _written_down(
    candidates: list[tuple[Provider, str | None]],
    *,
    settings: Settings,
    conn: sqlite3.Connection,
    clock: Clock,
    message_id: int | None,
    kind: str,
    sent: str,
    doing: str,
    estimate: Callable[[Provider, str | None], float],
    request: Callable[[Provider, str | None], Heard],
) -> Heard:
    """One request to the first candidate (a provider and the model to ask it for) that takes it:
    cost held before sending, next candidate when busy or out of reach. A refusal is recorded
    first (it was paid for), then raised."""
    failure: AgentError | None = None
    for provider, model in candidates:
        try:
            held = spending.admit(
                conn, settings, clock.now(), estimate(provider, model), company=provider.name
            )
        except spending.CompanyLimitReached as exc:
            failure = failure or exc  # the next company that may answer is asked
            continue
        started = time.monotonic()
        try:
            written = request(provider, model)
        except AgentError as exc:
            _let_go(conn, held, clock.now())
            alerts.noticed(conn, exc, provider=provider.name, now=clock.now(), model=model)
            transcript.keep_failure(
                conn,
                settings,
                None,
                exc,
                message_id=message_id,
                turn=None,
                iteration=1,
                kind=kind,
                about=None,
                provider=provider.name,
                model=model or provider.name,
                now=clock.now(),
            )
            if not worth_switching(exc):
                raise
            log.warning("%s could not %s (%s)", provider.name, doing, exc)
            failure = exc
            continue
        except BaseException:
            _let_go(conn, held, clock.now())
            raise
        dollars, listed = prices.cost(provider.name, written.model or model, written.usage)
        turn = uuid.uuid4().hex[:16]
        with transaction(conn):
            call_id = calls.log_llm_call(
                conn,
                message_id=message_id,
                iteration=1,
                model=model or provider.name,
                served_model=written.model,
                request_id=written.request_id,
                stop_reason=written.stop,
                usage=written.usage,
                duration_ms=int((time.monotonic() - started) * 1000),
                now=utc_iso(clock.now()),
                provider=provider.name,
                cost_usd=dollars,
                cost_estimated=not listed,
                kind=kind,
                turn=turn,
            )
            spending.settle(conn, held, clock.now())
            alerts.answered(conn, provider.name, model)
        transcript.keep_heard(
            conn,
            settings,
            call_id=call_id,
            message_id=message_id,
            turn=turn,
            kind=kind,
            provider=provider.name,
            model=written.model or model or provider.name,
            sent=sent,
            heard=written.text,
            now=clock.now(),
        )
        if written.dropped:
            alerts.dropped(conn, provider.name, model, written.dropped, clock.now())
        if written.stop == "refusal":
            raise AgentError(f"{provider.name} would not {doing}", retryable=False)
        if written.stop == "max_tokens":
            log.warning("%s ran out of room to %s; keeping what came", provider.name, doing)
        return written
    assert failure is not None
    raise failure


def _let_go(conn: sqlite3.Connection, held: int, now: datetime) -> None:
    with transaction(conn):
        spending.settle(conn, held, now)
