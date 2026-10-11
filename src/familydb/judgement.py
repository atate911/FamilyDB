"""Judgement calls: a stronger model weighs a change code has narrowed to a few options.

model_watch.py settles what rules settle (two lists agree on a price; a gone model is replaced by
the nearest in price). The rest needs judgement: which of several models suits the family, what
an unreadable refusal means, which new model belongs at which level, what a disputed price really
is. Code files a question (`file_*`) with the facts and the options it allows, and this job asks
them. The five answers of docs/AI_CALLS.md:

1. Only while `judgements` is on, for a filed question, within `judgement_budget` a month and the
day's limit. Questions wait for the evening's lookups (`lookup_hour`, or at once under
`lookups_when` asap) and go in one call; a refusal is asked at once, since the bot may be failing
meanwhile. 2. It sees model names, prices, what the calls use a model for, and a refusal's status
and error text: never the family's messages. Nothing volatile in the cached prompt. 3. It may
only hand back `give_judgement` (a choice among the options) or `report_price`, read from the
company's own page (the one kind with the web, at the lookup level since it is reading, not
weighing). 4. Its choice must be one of the options, checked by the tool; a price is taken only
when it matches a list. What follows is code's: under `judgement_acts` "within_cost" a model goes
in by itself only when it costs no more than `SAME_COST` times the one it replaces; anything
dearer is a suggestion with an admin's button; every change is told to admins with a way to put
it back (alert "advice"). 5. A cent or three a question on the best level, recorded under `judge`
and `price_check` like every call; the Status page lists each question, answer and outcome.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta
from typing import Any

from familydb import alerts
from familydb.agent import gateway, spending, uses
from familydb.agent.loop import MessagesAPI
from familydb.agent.providers import catalog, companies, prices
from familydb.agent.worker import worker_turn
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.integrations.price_lists import Prices
from familydb.store import calls
from familydb.store import judgements as store
from familydb.store import model_watch as watch_store
from familydb.store import settings as settings_store
from familydb.store.db import to_json, transaction
from familydb.store.model_watch import Seen
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

KINDS = ("judge", "price_check")
# What a model may cost to be put in by itself: the same as the one it replaces, give or take a
# tenth. Dearer is the family's to choose.
SAME_COST = 1.10
# An urgent question not answered in this long is no longer about now; any is forgotten after the
# second.
URGENT_FOR = timedelta(days=2)
FORGET_AFTER = timedelta(days=60)
CALL_ALLOWANCE = 0.05
MOST_PRICE_CHECKS = 2
LEVELS_ASKED = ("everyday", "better", "best")
MOST_OPTIONS = 8
MOST_TRIES = 2
LEVEL_KEYS = {
    company.slug: (company.chat_setting, company.better_setting, company.best_setting)
    for company in companies.BUILT_IN
}
SOURCE = "judgement"


def _dollars(seen: Seen | None) -> str:
    if seen is None or seen.output is None:
        return "price unknown"
    return f"${seen.input:g} in, ${seen.output:g} out a million tokens"


def _option(seen: Seen) -> dict[str, Any]:
    known = catalog.known(seen.provider, seen.model)
    facts: dict[str, Any] = {"model": seen.model, "price": _dollars(seen)}
    if known is not None:
        facts["known_as"] = f"{known.label}, the {known.level} level in this version's lineup"
    if seen.released:
        facts["released"] = seen.released
    if seen.retires_on:
        facts["retires_on"] = seen.retires_on
    return facts


def _file(
    conn: sqlite3.Connection,
    kind: str,
    subject: str,
    facts: dict[str, Any],
    at: str,
    *,
    urgent: bool = False,
) -> None:
    try:
        with transaction(conn):
            if store.file(conn, kind, subject, facts, now=at, urgent=urgent):
                log.info("filed a %s question about %s for a judgement", kind, subject)
    except sqlite3.Error as exc:
        log.warning("could not file a %s question: %s", kind, exc)


def file_replacement(
    conn: sqlite3.Connection, model: Seen, options: list[Seen], uses: list[str], at: str
) -> None:
    facts = {
        "company": model.provider,
        "model": model.model,
        "price": _dollars(model),
        "going": "the company no longer lists it for the key"
        if model.listed is False
        else f"retires on {model.retires_on}",
        "used_for": uses,
        "options": [_option(option) for option in options],
    }
    _file(conn, "replacement", f"{model.provider}:{model.model}", facts, at)


def file_lineup(
    conn: sqlite3.Connection,
    settings: Any,
    company: str,
    seen: dict[tuple[str, str], Seen],
    today: date,
    at: str,
) -> None:
    """Which of a company's models belongs at each level, now that it has new ones. At most one
    question a month per company.
    """
    from familydb import model_watch
    from familydb.agent import providers

    offered = [
        model
        for (owner, _), model in seen.items()
        if owner == company and model_watch._offerable(model, today)
    ]
    names = {model.model for model in offered}
    offered = [model for model in offered if not model_watch._snapshot_of(model.model, names)]
    if len(offered) < 2:
        return
    provider = providers.build(company, settings)
    now_at = {level: providers.model_at(provider, "chat", level) for level in LEVELS_ASKED}
    everyday = seen.get((company, now_at["everyday"].lower()))
    levels: dict[str, list[str]] = {}
    for level in LEVELS_ASKED:
        pool = offered
        if level == "everyday" and everyday is not None and everyday.output:
            pool = [m for m in offered if (m.output or 0) <= SAME_COST * everyday.output]
        pool = sorted(pool, key=lambda m: (m.output or 0, m.model))[:MOST_OPTIONS]
        options = [m.model for m in pool]
        if now_at[level] not in options:
            options.append(now_at[level])
        levels[level] = options
    facts = {
        "company": company,
        "now": now_at,
        "levels": levels,
        "models": [_option(model) for model in sorted(offered, key=lambda m: m.output or 0)],
    }
    _file(conn, "lineup", f"{company}:{today.isoformat()[:7]}", facts, at)


def file_price(conn: sqlite3.Connection, model: Seen, read: dict[str, Prices], at: str) -> None:
    listed = {}
    for source, found in read.items():
        entry = found.get(model.provider, {}).get(model.model)
        if entry is not None and entry.output is not None:
            listed[source] = {"input": entry.input, "output": entry.output}
    facts = {
        "company": model.provider,
        "model": model.model,
        "kept": {"input": model.input, "output": model.output},
        "lists": listed,
    }
    _file(conn, "price", f"{model.provider}:{model.model}:{at[:10]}", facts, at)


def file_refused(
    conn: sqlite3.Connection,
    provider: str,
    model: str | None,
    said: str,
    parts: tuple[str, ...],
    now: datetime,
) -> None:
    """What an unreadable refusal most likely is: asked at once, once a day at most per company."""
    facts = {
        "company": provider,
        "model": (model or "").lower(),
        "error": " ".join(said.split())[:600],
        "parts": list(parts),
    }
    _file(conn, "refused", f"{provider}:{now.date().isoformat()}", facts, utc_iso(now), urgent=True)


def _evening(settings: Any, now: datetime) -> str | None:
    """The last evening lookup hour passed, as the enrichment job reads it: questions filed before
    it are due. None when lookups go as they come.
    """
    if settings.lookups_when == "asap":
        return None
    zone = settings.tzinfo
    local = now.astimezone(zone)
    evening = datetime.combine(local.date(), time(settings.lookup_hour), tzinfo=zone)
    if local < evening:
        evening -= timedelta(days=1)
    return utc_iso(evening)


def due(questions: list[store.Judgement], settings: Any, now: datetime) -> list[store.Judgement]:
    before = _evening(settings, now)
    return [q for q in questions if q.urgent or before is None or q.asked_at < before]


def spent_this_month(conn: sqlite3.Connection, settings: Any, now: datetime) -> float:
    local = now.astimezone(settings.tzinfo)
    start = datetime.combine(local.date().replace(day=1), time(), tzinfo=settings.tzinfo)
    return calls.spent_on(conn, KINDS, since=utc_iso(start))


def _room(conn: sqlite3.Connection, settings: Any, now: datetime) -> bool:
    budget = settings.judgement_budget
    if not budget or spent_this_month(conn, settings, now) + CALL_ALLOWANCE > budget:
        return False
    return not spending.used_up(conn, settings, now)


def run_judgements(app: Any, *, api: MessagesAPI | None = None) -> dict[str, int]:
    counts = {"asked": 0, "answered": 0}
    with closing(app.connect()) as conn:
        app.refresh(conn)
        settings = app.settings
        if not uses.on(settings, "judge"):
            return counts
        now = app.clock.now()
        waiting = [
            q
            for q in store.open_questions(conn)
            if not (q.urgent and q.asked_at < utc_iso(now - URGENT_FOR))
        ]
        ready = due(waiting, settings, now)
        if not ready or not gateway.can_ask(settings, "judge", api=api):
            return counts
        with transaction(conn):
            store.forget_before(conn, utc_iso(now - FORGET_AFTER))
        weighed = [q for q in ready if q.kind != "price"]
        if weighed and _room(conn, settings, now):
            counts["asked"] += 1
            counts["answered"] += _weigh(app, conn, weighed, api=api)
        for question in [q for q in ready if q.kind == "price"][:MOST_PRICE_CHECKS]:
            if not _room(conn, settings, now):
                break
            counts["asked"] += 1
            counts["answered"] += _check_price(app, conn, question, api=api)
    if counts["answered"]:
        log.info("judgements: %s", counts)
    return counts


def _names(question: store.Judgement) -> dict[str, list[str]]:
    facts = question.facts
    if question.kind == "replacement":
        return {f"q{question.id}": [option["model"] for option in facts["options"]]}
    if question.kind == "refused":
        options = ["credit", "key", "model", "other", *(f"part:{p}" for p in facts["parts"])]
        return {f"q{question.id}": options}
    if question.kind == "lineup":
        return {f"q{question.id}.{level}": list(facts["levels"][level]) for level in LEVELS_ASKED}
    return {}


def _weigh(
    app: Any, conn: sqlite3.Connection, questions: list[store.Judgement], *, api: Any
) -> int:
    asked: dict[str, list[str]] = {}
    listed = []
    for question in questions:
        names = _names(question)
        asked |= names
        listed.append({"questions": sorted(names), "kind": question.kind, "facts": question.facts})
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        about=f"weighing {len(questions)} change{'s' if len(questions) != 1 else ''}",
        source="job",
    )
    ctx.scratch["questions"] = asked
    request = "Answer each question with give_judgement, choosing among its options:\n" + to_json(
        {"asked": listed, "options": asked}
    )
    try:
        result = gateway.ask(
            "judge",
            settings=app.settings,
            registry=app.registry,
            ctx=ctx,
            current=worker_turn(app.clock, request),
            api=api,
        )
    except AgentError as exc:
        log.warning("the judgement could not be asked: %s", exc)
        _no_answer(app, conn, questions, str(exc))
        return 0
    picks: dict[str, dict[str, str]] = ctx.scratch.get("picks") or {}
    if not gateway.handed_back(gateway.spec("judge"), result) or not picks:
        log.warning("the judgement came back without an answer: %s", result.status)
        _no_answer(app, conn, questions, result.error or result.status)
        return 0
    answered = 0
    for question in questions:
        try:
            _apply(app, conn, question, picks)
            answered += 1
        except Exception:
            log.exception("could not apply the judgement on %s", question.subject)
    return answered


def _check_price(app: Any, conn: sqlite3.Connection, question: store.Judgement, *, api: Any) -> int:
    from familydb.agent.worker import home_location

    facts = question.facts
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        about=f"the price of {facts['model']}",
        source="job",
    )
    ctx.scratch["price_of"] = facts["model"]
    company = companies.named(facts["company"])
    request = f"What does {company} charge for {facts['model']}? The price lists say: " + to_json(
        facts["lists"]
    )
    try:
        gateway.ask(
            "price_check",
            settings=app.settings,
            registry=app.registry,
            ctx=ctx,
            current=worker_turn(app.clock, request),
            api=api,
            user_location=home_location(app.settings),
        )
    except AgentError as exc:
        log.warning("the price of %s could not be checked: %s", facts["model"], exc)
        _no_answer(app, conn, [question], str(exc))
        return 0
    found = ctx.scratch.get("price")
    if found is None:
        _no_answer(app, conn, [question], "no price came back")
        return 0
    _settle_price(app, conn, question, found)
    return 1


def _no_answer(
    app: Any, conn: sqlite3.Connection, questions: list[store.Judgement], why: str
) -> None:
    at = utc_iso(app.clock.now())
    with transaction(conn):
        for question in questions:
            if store.tried(conn, question.id, now=at) >= MOST_TRIES:
                store.answered(
                    conn,
                    question.id,
                    answer=None,
                    reason=None,
                    outcome=f"no answer came back ({why[:120]}); the rule's choice stands",
                    now=at,
                )


def _apply(
    app: Any, conn: sqlite3.Connection, question: store.Judgement, picks: dict[str, Any]
) -> None:
    now = app.clock.now()
    facts = question.facts
    company_name = companies.named(facts.get("company", ""))
    answer: dict[str, Any]
    if question.kind == "lineup":
        chosen = {level: picks[f"q{question.id}.{level}"] for level in LEVELS_ASKED}
        answer = {level: pick["choice"] for level, pick in chosen.items()}
        reason = "; ".join(f"{level}: {pick['reason']}" for level, pick in chosen.items())
        done = _lineup(app, conn, facts, dict(answer))
    else:
        pick = picks[f"q{question.id}"]
        answer, reason = {"choice": pick["choice"]}, pick["reason"]
        if question.kind == "replacement":
            done = _replacement(app, conn, facts, pick["choice"])
        else:
            done = Done(_refused(conn, facts, pick["choice"], now))
    answer |= {"undo": done.undo, "waiting": done.waiting}
    outcome = done.said
    with transaction(conn):
        store.answered(
            conn, question.id, answer=answer, reason=reason, outcome=outcome, now=utc_iso(now)
        )
    alerts.note(
        conn,
        "advice",
        f"{question.kind}:{question.subject}",
        f"{outcome} ({company_name}): {reason}",
        now,
        once=True,
    )


def _costs(conn: sqlite3.Connection, company: str, name: str) -> float | None:
    seen = watch_store.all_seen(conn).get((company, name.lower()))
    if seen is not None and seen.output is not None:
        return seen.output
    price = prices.price(company, name)
    return price.output if price is not None else None


def _within_cost(conn: sqlite3.Connection, company: str, old: str, new: str) -> bool:
    before, after = _costs(conn, company, old), _costs(conn, company, new)
    return before is not None and after is not None and after <= SAME_COST * before


class Done:
    """What code made of one answer: what it changed and what waits for an admin, each as the
    settings they would be (kept for the Status page's buttons).
    """

    def __init__(self, said: str, undo: dict[str, str] | None = None, waiting=None) -> None:
        self.said = said
        self.undo = undo or {}
        self.waiting: dict[str, str] = waiting or {}


def _put_in(app: Any, conn: sqlite3.Connection, values: dict[str, str]) -> dict[str, str]:
    """Save settings a judgement may change by itself, logged as the judgement's. Returns each one's
    previous value (empty for the default), to put back.
    """
    with transaction(conn):
        before = settings_store.overrides(conn)
        changed = settings_store.set_many(conn, values, source=SOURCE)
    if changed:
        app.refresh(conn)
    return {key: str(before.get(key) or "") for key in changed}


def _boxes_naming(settings: Any, company: str, name: str) -> list[str]:
    from familydb.web import fields

    return [
        one.key
        for one in fields.FIELDS
        if one.company == company and str(getattr(settings, one.key, "") or "").lower() == name
    ]


def _replacement(app: Any, conn: sqlite3.Connection, facts: dict[str, Any], choice: str) -> Done:
    company, old = facts["company"], facts["model"]
    boxes = _boxes_naming(app.settings, company, old)
    acts = app.settings.judgement_acts == "within_cost"
    if boxes and acts and _within_cost(conn, company, old, choice):
        undo = _put_in(app, conn, dict.fromkeys(boxes, choice))
        return Done(f"{choice} put in place of {old}, at about the same cost", undo=undo)
    if boxes:
        return Done(
            f"{choice} suggested in place of {old}; it waits for an admin on the Status page",
            waiting=dict.fromkeys(boxes, choice),
        )
    return Done(f"{choice} will answer in place of {old} once it has gone")


def _lineup(
    app: Any, conn: sqlite3.Connection, facts: dict[str, Any], answer: dict[str, str]
) -> Done:
    company = facts["company"]
    keys = dict(zip(LEVELS_ASKED, LEVEL_KEYS[company], strict=True))
    moved = {level: name for level, name in answer.items() if name != facts["now"][level]}
    if not moved:
        return Done("the models at each level stay as they are")
    acts = app.settings.judgement_acts == "within_cost"
    fine = {
        keys[level]: name
        for level, name in moved.items()
        if acts and _within_cost(conn, company, facts["now"][level], name)
    }
    waiting = {keys[level]: name for level, name in moved.items() if keys[level] not in fine}
    undo = _put_in(app, conn, fine) if fine else {}
    said = [
        f"{name} at {level}" + ("" if keys[level] in fine else " (waits for an admin)")
        for level, name in moved.items()
    ]
    return Done(("put in: " if fine else "suggested: ") + ", ".join(said), undo, waiting)


def _refused(conn: sqlite3.Connection, facts: dict[str, Any], choice: str, now: datetime) -> str:
    from familydb.agent.providers import parts

    company, model = facts["company"], facts.get("model") or ""
    if choice in ("credit", "key"):
        alerts.note(conn, choice, company, f"read as such from: {facts['error']}", now)
        return "read as " + ("out of credit" if choice == "credit" else "the key refused")
    if choice == "model" and model:
        alerts.note(
            conn,
            "model",
            f"{company}:{model}",
            f"{companies.named(company)} seems to have no model called "
            f"{model}, so everything asked of it fails until another is chosen",
            now,
        )
        return f"read as {model} gone"
    if choice.startswith("part:") and model:
        parts.leave_out(company, model, choice[5:])
        return f"{choice[5:]} is now left out for {model}"
    return "not something FamilyDB can put right by itself"


def _settle_price(
    app: Any, conn: sqlite3.Connection, question: store.Judgement, found: dict[str, Any]
) -> None:
    from familydb import model_watch

    facts = question.facts
    now = app.clock.now()
    company, name = facts["company"], facts["model"]
    if not found.get("found"):
        outcome = "the company's own page does not give it; the last good price is kept"
    else:
        candidates = [*facts["lists"].values(), facts["kept"]]
        agrees = any(
            value.get("output")
            and abs(found["output"] - value["output"]) <= model_watch.AGREE * value["output"]
            for value in candidates
        )
        if agrees:
            seen = watch_store.all_seen(conn).get((company, name))
            if seen is not None:
                taken = seen.model_copy(
                    update={
                        "input": found["input"],
                        "output": found["output"],
                        "cached": found.get("cached"),
                        "priced_by": "the company's page",
                    }
                )
                with transaction(conn):
                    watch_store.save(conn, taken)
                model_watch.load(conn, today=now.date())
            alerts.working(conn, "prices", f"{company}:{name}")
            outcome = (
                f"${found['input']:g} in, ${found['output']:g} out, from {found['source_url']}"
            )
        else:
            outcome = (
                f"the page says ${found['output']:g} out, which matches no list; the last good "
                "price is kept"
            )
    with transaction(conn):
        store.answered(
            conn, question.id, answer=found, reason=None, outcome=outcome, now=utc_iso(now)
        )
    alerts.note(conn, "advice", f"price:{question.subject}", f"{name}: {outcome}", now, once=True)
