"""Keeping up with the companies: which models each offers the family's key, what they cost, and
what changed. Once a day (the `model_watch` job), with no model call.

Three things are read. Each company the family has a key for is asked which models the key can
use (`Provider.listed_models`, free). Two public price lists, LiteLLM's and OpenRouter's, are
read for what each model costs, whether it can use tools, and any date it goes
(integrations/price_lists.py). A price is taken when both lists agree; when they disagree, or
one sends a price far from the last (more than `JUMP` times it), or a price no model could cost,
the last good one is kept and an admin is told. prices.py's built-in table is only where a new
install starts. What was found is kept (store/model_watch.py) and put in force in every process
(`load`, from App.refresh), so the spending limit counts at the new prices and the settings
page offers the new models, without a new release.

What changed is recorded, and told to each admin with a Telegram id (alerts.py): a model the
family uses that the company no longer lists, or that a list says goes soon; a price of one they
use that moved; a price list that could not be read for `SOURCE_FAILURES` checks in a row, or
lists at odds about a model in use; and new models to choose from. The weekly look at what the
calls themselves cost and do is usage_watch.py, run from the same job.
"""

from __future__ import annotations

import logging
import math
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta
from typing import Any

from familydb import alerts
from familydb.agent import gateway, providers
from familydb.agent.providers import catalog, parts, prices
from familydb.agent.providers.prices import Price
from familydb.dates import utc_iso
from familydb.integrations.price_lists import Listed, PriceLists, PriceListsAPI, Prices
from familydb.store import judgements as judgement_store
from familydb.store import model_watch as store
from familydb.store.db import transaction
from familydb.store.model_watch import Seen

log = logging.getLogger(__name__)

COMPANIES = ("openai", "anthropic", "gemini")
SOURCES = {"litellm": "LiteLLM's price list", "openrouter": "OpenRouter's price list"}
AGREE = 0.05  # two lists agree when within 5% of each other
MOST = 500.0  # dollars a million tokens: more than any model costs, so a mistake
JUMP = 5.0  # a price moving more than fivefold in a day is held until a person has looked
RETIRING_DAYS = 60  # a model in use that goes within this many days is told of
SOON_DAYS = 14  # and told again this close to the day
SOURCE_FAILURES = 3  # checks in a row a list may fail before an admin is told
NEW_SHOWN = 5  # new models named in one notice
UNSEEN = timedelta(days=7)  # no list has named a model this long: no longer offered
NEW_FOR = timedelta(days=30)  # a model first seen this lately is marked new where it is offered
# A model to take another's place is looked for at about its price: one no more than this much
# dearer if there is any, the nearest in price among those.
DEARER = 1.25
# What the family spends is theirs to decide: a model goes in another's place by itself only when
# it costs no more than this much more. A dearer one is suggested, and waits for an admin.
SWAP_DEARER = 2.0
# Words in a model's name that say it is not for chatting, or not a model of its own (an alias
# that moves, an experiment, an open model Google also serves), whatever a list calls it.
NOT_FOR_CHAT = (
    "audio",
    "realtime",
    "tts",
    "transcribe",
    "image",
    "embed",
    "search",
    "computer",
    "instruct",
    "gemma",
    "-exp",
    "latest",
    "-16k",
    "robotics",
)
# A dated snapshot of another model: claude-haiku-4-5-20251001, gpt-5-2025-08-07, gpt-4-0613.
SNAPSHOT = re.compile(r"^(?P<family>.+?)-(?:\d{8}|\d{4}-\d{2}-\d{2}|\d{4})$")
# A model out longer than this is not offered unless it is in this version's lineup: the lists go
# on pricing a company's older models for as long as it sells them.
OLDEST_OFFERED = timedelta(days=365)


def check(
    app: Any,
    *,
    lists: PriceListsAPI | None = None,
    listers: dict[str, Callable[[], list[str] | None]] | None = None,
) -> dict[str, int]:
    """Read the companies' lists and the price lists, keep what was found, and tell admins what
    changed that matters to them. Returns counts, for the log and the tests.

    `lists` and `listers` stand in for the price lists and each company's own list in tests."""
    with closing(app.connect()) as conn:
        app.refresh(conn)
        settings = app.settings
        if not settings.model_watch:
            return {}
        now = app.clock.now()
        at = utc_iso(now)
        read = _read_price_lists(conn, lists or PriceLists(), now)
        listed = _read_company_lists(conn, settings, listers, at)
        before = store.all_seen(conn)
        in_use = models_in_use(settings)
        changes: list[tuple[str, str, str, str | None, str | None]] = []
        doubts: dict[tuple[str, str], str] = {}
        with transaction(conn):
            for company in COMPANIES:
                for name in _candidates(company, read, listed[company], before, in_use):
                    old = before.get((company, name))
                    seen, doubt = _merge(company, name, old, read, listed[company], at)
                    store.save(conn, seen)
                    if doubt:
                        doubts[(company, name)] = doubt
                    if before:  # the first check only learns what there is
                        for what, was, now_is in _differences(old, seen, now.date()):
                            store.record_change(
                                conn, company, name, what, before=was, after=now_is, at=at
                            )
                            changes.append((company, name, what, was, now_is))
        judged = judged_replacements(conn)
        after = store.all_seen(conn)
        _tell(conn, settings, after, changes, doubts, in_use, now, judged)
        _file_questions(conn, settings, after, read, changes, doubts, in_use, now, judged)
        load(conn, today=now.date())
        counts = {"models": len(store.all_seen(conn)), "changes": len(changes)}
    from familydb import usage_watch

    counts["shifts"] = usage_watch.check(app)
    log.info("models and prices checked: %s", counts)
    return counts


# -- reading --------------------------------------------------------------------------------------


def _read_price_lists(
    conn: sqlite3.Connection, lists: PriceListsAPI, now: datetime
) -> dict[str, Prices]:
    read: dict[str, Prices] = {}
    for source, fetch in (("litellm", lists.litellm), ("openrouter", lists.openrouter)):
        try:
            read[source] = fetch()
            ok, note = True, f"{sum(len(models) for models in read[source].values())} models"
        except Exception as exc:  # a list that cannot be read is told of, never a crash
            ok, note = False, str(exc)
            log.warning("%s could not be read: %s", SOURCES[source], exc)
        with transaction(conn):
            failures = store.source_answered(conn, source, ok=ok, note=note, at=utc_iso(now))
        if ok:
            alerts.working(conn, "prices", source)
        elif failures >= SOURCE_FAILURES:
            alerts.note(
                conn,
                "prices",
                source,
                f"{SOURCES[source]} could not be read for {failures} days running ({note})",
                now,
            )
    return read


def _read_company_lists(
    conn: sqlite3.Connection,
    settings: Any,
    listers: dict[str, Callable[[], list[str] | None]] | None,
    at: str,
) -> dict[str, set[str] | None]:
    """Each company's own list of models for the family's key; None when it has no key here or
    could not be asked, which is never taken as "none"."""
    listed: dict[str, set[str] | None] = {}
    for company in COMPANIES:
        provider = providers.build(company, settings)
        ask = provider.listed_models if listers is None else listers.get(company)
        if ask is None or (listers is None and not provider.configured()):
            listed[company] = None
            continue
        names = ask()
        listed[company] = {name.lower() for name in names} if names is not None else None
        with transaction(conn):
            store.source_answered(
                conn,
                company,
                ok=names is not None,
                note=f"{len(names)} models for the key" if names is not None else "not answering",
                at=at,
            )
    return listed


def models_in_use(settings: Any) -> set[tuple[str, str]]:
    """The models the family's calls go to now: each kind of call's, its spare's, and those that
    hear voice notes and look at photos."""
    used: set[tuple[str, str]] = set()
    for kind in gateway.KINDS:
        call = gateway.spec(kind)
        level = getattr(settings, call.level)
        primary = providers.for_surface(settings, call.surface)
        used.add((primary.name, providers.model_at(primary, call.surface, level).lower()))
        spare = providers.fallback_for(settings, call.surface, primary.name)
        if spare is not None:
            used.add((spare.name, providers.model_at(spare, call.surface, level).lower()))
    for hearer in providers.hearers(settings):
        if hearer.listener():
            used.add((hearer.name, str(hearer.listener()).lower()))
    for looker in providers.lookers(settings):
        if looker.viewer():
            used.add((looker.name, str(looker.viewer()).lower()))
    return used


def _candidates(
    company: str,
    read: dict[str, Prices],
    listed: set[str] | None,
    before: dict[tuple[str, str], Seen],
    in_use: set[tuple[str, str]],
) -> set[str]:
    """Every model of this company worth keeping track of: what a price list has for chatting,
    what is built in, what was kept before, and what the family uses."""
    names = {name for source in read.values() for name in source.get(company, {})}
    names |= set(prices.PRICES.get(company, {}))
    names |= {name for (owner, name) in before if owner == company}
    names |= {name for (owner, name) in in_use if owner == company}
    return names


# -- deciding -------------------------------------------------------------------------------------


def _sane(listed: Listed | None) -> bool:
    return (
        listed is not None
        and listed.input is not None
        and listed.output is not None
        and 0 <= listed.input <= MOST
        and 0 < listed.output <= MOST
    )


def _agree(one: Listed, other: Listed) -> bool:
    def close(a: float | None, b: float | None) -> bool:
        if a is None or b is None:
            return True
        return abs(a - b) <= AGREE * max(a, b, 1e-9)

    return close(one.input, other.input) and close(one.output, other.output)


def _merge(
    company: str,
    name: str,
    old: Seen | None,
    read: dict[str, Prices],
    listed: set[str] | None,
    at: str,
) -> tuple[Seen, str | None]:
    """What is known of one model now, and a doubt about its price when there is one."""
    found = {source: read[source].get(company, {}).get(name) for source in read}
    sane = {source: entry for source, entry in found.items() if _sane(entry)}
    built_in = prices.PRICES.get(company, {}).get(name) or prices.HEARING.get(company, {}).get(name)
    last = (old.input, old.output, old.cached) if old and old.output is not None else None
    if last is None and built_in is not None:
        last = (built_in.input, built_in.output, built_in.cached)
    doubt = None
    chosen: tuple[float, float, float | None] | None = last
    by = old.priced_by if old else ("built in" if built_in else None)
    if len(sane) == 2:
        one, other = sane["litellm"], sane["openrouter"]
        if _agree(one, other):
            chosen = (one.input, one.output, one.cached if one.cached is not None else other.cached)  # type: ignore[assignment]
            by = "both"
        else:
            doubt = (
                f"the price lists disagree about {name}: LiteLLM says {_dollars(one)}, "
                f"OpenRouter {_dollars(other)}"
            )
            if chosen is None:  # nothing to keep: count it at the dearer, which stops early
                dearer = max(one, other, key=lambda entry: entry.output or 0)
                chosen, by = (dearer.input, dearer.output, dearer.cached), "the dearer list"  # type: ignore[assignment]
    elif len(sane) == 1:
        (source, entry) = next(iter(sane.items()))
        chosen, by = (entry.input, entry.output, entry.cached), source  # type: ignore[assignment]
    if chosen is not None and last is not None and chosen != last and _jumped(last, chosen):
        doubt = (
            f"a price list says {name} now costs ${chosen[0]:g} in and ${chosen[1]:g} out a "
            f"million tokens, far from ${last[0]:g} and ${last[1]:g}: the old price is kept"
        )
        chosen, by = last, (old.priced_by if old else "built in")
    tools = [
        entry.tools for entry in found.values() if entry is not None and entry.tools is not None
    ]
    dates = [entry.retires_on for entry in found.values() if entry is not None and entry.retires_on]
    out = [entry.released for entry in found.values() if entry is not None and entry.released]
    named = any(entry is not None for entry in found.values()) or bool(listed and name in listed)
    seen = Seen(
        provider=company,
        model=name,
        listed=(name in listed) if listed is not None else (old.listed if old else None),
        tools=any(tools) if tools else (old.tools if old else None),
        input=chosen[0] if chosen else None,
        output=chosen[1] if chosen else None,
        cached=chosen[2] if chosen else None,
        priced_by=by if chosen else None,
        retires_on=min(dates) if dates else None,
        released=min(out) if out else (old.released if old else None),
        first_seen=old.first_seen if old else at,
        last_seen=at if named else (old.last_seen if old else None),
    )
    return seen, doubt


def _jumped(
    last: tuple[float, float, float | None], now: tuple[float, float, float | None]
) -> bool:
    for was, is_now in ((last[0], now[0]), (last[1], now[1])):
        if was and is_now and not (1 / JUMP <= is_now / was <= JUMP):
            return True
    return False


def _differences(
    old: Seen | None, seen: Seen, today: date
) -> list[tuple[str, str | None, str | None]]:
    """What changed about one model since the last check, as (what, before, after)."""
    if old is None:
        return [("new", None, _price_words(seen))] if _offerable(seen, today) else []
    found: list[tuple[str, str | None, str | None]] = []
    if old.listed is True and seen.listed is False:
        found.append(("gone", "listed", "not listed"))
    elif old.listed is False and seen.listed is True:
        found.append(("back", "not listed", "listed"))
    if (
        old.output is not None
        and seen.output is not None
        and (_moved(old.input, seen.input) or _moved(old.output, seen.output))
    ):
        found.append(("price", _price_words(old), _price_words(seen)))
    if seen.retires_on and seen.retires_on != old.retires_on:
        found.append(("retiring", old.retires_on, seen.retires_on))
    return found


def _moved(was: float | None, now: float | None) -> bool:
    if was is None or now is None:
        return was != now
    return abs(was - now) > 0.005 * max(was, now, 1e-9)


def _price_words(seen: Seen | Listed) -> str:
    return f"${seen.input:g} in, ${seen.output:g} out" if seen.output is not None else "no price"


def _dollars(listed: Listed) -> str:
    return f"${listed.input:g} in and ${listed.output:g} out"


# -- telling --------------------------------------------------------------------------------------


def _tell(
    conn: sqlite3.Connection,
    settings: Any,
    seen: dict[tuple[str, str], Seen],
    changes: list[tuple[str, str, str, str | None, str | None]],
    doubts: dict[tuple[str, str], str],
    in_use: set[tuple[str, str]],
    now: datetime,
    judged: dict[str, str] | None = None,
) -> None:
    """Note for admins what matters to the family (alerts.py tells them): about the models in
    use, whatever changed; about the rest, only that there are new ones to choose from."""
    today = now.date()
    for company, name in sorted(in_use):
        model = seen.get((company, name))
        subject = f"{company}:{name}"
        company_name = alerts.COMPANY_NAMES.get(company, company)
        instead = replacement(seen, company, name, today, judged)
        if model is not None and model.listed is False:
            if instead and swaps_for(model, instead):
                in_place = (
                    f"; {instead.model} ({_price_words(instead)}) answers in its place until "
                    "another is chosen"
                )
            elif instead:
                in_place = (
                    f", so everything asked of it fails until another is chosen; "
                    f"{instead.model} ({_price_words(instead)}) is the nearest on offer"
                )
            else:
                in_place = ", so everything asked of it fails until another is chosen"
            alerts.note(
                conn,
                "model",
                subject,
                f"{company_name} no longer offers {name} to the family's key{in_place}",
                now,
            )
        else:
            alerts.working(conn, "model", subject)
        if model is not None and model.retires_on:
            left = (date.fromisoformat(model.retires_on) - today).days
            if 0 <= left <= RETIRING_DAYS:
                soon = ":soon" if left <= SOON_DAYS else ""
                could = ""
                if instead:
                    could = f"; {instead.model} ({_price_words(instead)}) could take its place"
                    if swaps_for(model, instead):
                        could += ", and will on the day unless another is chosen"
                alerts.note(
                    conn,
                    "model",
                    f"{subject}:{model.retires_on}{soon}",
                    f"{company_name} retires {name} on {model.retires_on}, in {left} days{could}",
                    now,
                    once=True,
                )
        if (company, name) in doubts:
            alerts.note(conn, "prices", subject, doubts[(company, name)], now, once=True)
    for company, name, what, was, now_is in changes:
        if what == "price" and (company, name) in in_use:
            alerts.note(
                conn,
                "price",
                f"{company}:{name}:{now_is}",
                f"{name} ({alerts.COMPANY_NAMES.get(company, company)}) now costs {now_is} a "
                f"million tokens, was {was}",
                now,
                once=True,
            )
    for company in COMPANIES:
        new = [
            seen[(owner, name)]
            for owner, name, what, _, _ in changes
            if owner == company
            and what in ("new", "back")
            and _offerable(seen[(owner, name)], today)
        ]
        if new:
            shown = ", ".join(f"{m.model} ({_price_words(m)})" for m in new[:NEW_SHOWN])
            more = f", and {len(new) - NEW_SHOWN} more" if len(new) > NEW_SHOWN else ""
            alerts.note(
                conn,
                "new",
                f"{company}:{today.isoformat()}",
                f"{alerts.COMPANY_NAMES.get(company, company)}: {shown}{more}",
                now,
                once=True,
            )


# -- putting it in force --------------------------------------------------------------------------


def _offerable(seen: Seen, today: date) -> bool:
    """Worth offering on the settings page: named by a list lately, priced, able to use tools,
    for chatting, not listed as missing for the key, and not gone; and either in this version's
    lineup or served now and out within the year. Only the built-in table knowing of a model is
    not enough: that is how a retired one would go on being offered."""
    if seen.output is None or seen.tools is False or seen.listed is False:
        return False
    if seen.last_seen is None or seen.last_seen[:10] < (today - UNSEEN).isoformat():
        return False
    if any(word in seen.model for word in NOT_FOR_CHAT):
        return False
    if seen.model in {model.name for model in catalog.lineup(seen.provider)}:
        return not (seen.retires_on and seen.retires_on <= today.isoformat())
    # Served now: the company lists it for the key, or OpenRouter serves it (and so says when it
    # came out). LiteLLM's list goes on pricing a model long after it is anything to choose.
    if not (seen.listed or seen.released):
        return False
    if seen.released and seen.released < (today - OLDEST_OFFERED).isoformat():
        return False
    return not (seen.retires_on and seen.retires_on <= today.isoformat())


def gone(seen: Seen, today: date) -> bool:
    """Whether asking this model now would fail: the company no longer lists it for the key, or
    a list says its day has passed."""
    return seen.listed is False or bool(seen.retires_on and seen.retires_on <= today.isoformat())


def swaps_for(old: Seen | None, instead: Seen) -> bool:
    """Whether `instead` may answer in `old`'s place without anybody choosing it: when it costs
    no more than `SWAP_DEARER` times as much, or either price is unknown to compare."""
    if old is None or not old.output or not instead.output:
        return True
    return instead.output <= SWAP_DEARER * old.output


def replacement(
    seen: dict[tuple[str, str], Seen],
    company: str,
    name: str,
    today: date,
    judged: dict[str, str] | None = None,
) -> Seen | None:
    """The model to suggest in this one's place: the one a judgement chose (judgement.py) while
    it is still on offer, else the nearest in price of the shortlist. None when there is none."""
    options = shortlist(seen, company, name, today)
    chosen = (judged or {}).get(f"{company}:{name.lower()}")
    for model in options:
        if model.model == chosen:
            return model
    return options[0] if options else None


def shortlist(
    seen: dict[tuple[str, str], Seen], company: str, name: str, today: date, most: int = 5
) -> list[Seen]:
    """The models that could take this one's place, best first by the rule: the same company's
    on offer, not going within `RETIRING_DAYS` themselves, at about its price (no more than
    `DEARER` times it when any is), nearest in price first."""
    old = seen.get((company, name.lower()))
    horizon = (today + timedelta(days=RETIRING_DAYS)).isoformat()
    choices = [
        model
        for (owner, other), model in seen.items()
        if owner == company
        and other != name.lower()
        and _offerable(model, today)
        and not (model.retires_on and model.retires_on <= horizon)
    ]
    names = {model.model for model in choices}
    choices = [model for model in choices if not _snapshot_of(model.model, names)]
    target = old.output if old is not None and old.output else None

    def nearness(model: Seen) -> tuple[bool, float, float]:
        cost = model.output or 0.0
        if target is None or not cost:
            return (False, 0.0, cost)
        return (cost > DEARER * target, abs(math.log(cost / target)), cost)

    return sorted(choices, key=lambda model: (nearness(model), model.model))[:most]


def replacement_for(conn: sqlite3.Connection, company: str, name: str, today: date) -> Seen | None:
    """As `replacement`, from what the last check kept: for the status page."""
    return replacement(store.all_seen(conn), company, name, today, judged_replacements(conn))


def judged_replacements(conn: sqlite3.Connection) -> dict[str, str]:
    """What the judgement calls chose to take each going model's place, by company:model."""
    return {
        subject: str((answer.answer or {}).get("choice") or "")
        for subject, answer in judgement_store.choices(conn, "replacement").items()
    }


def uses_of(settings: Any, company: str, name: str) -> list[str]:
    """What the family's calls use this model for, in words: for a judgement to weigh."""
    uses: list[str] = []
    provider = providers.build(company, settings)
    for kind in gateway.KINDS:
        call = gateway.spec(kind)
        if providers.model_at(provider, call.surface, getattr(settings, call.level)) == name:
            uses.append(call.purpose)
    for hearer in providers.hearers(settings):
        if hearer.name == company and str(hearer.listener()).lower() == name:
            uses.append(gateway.LISTEN_PURPOSE)
    for looker in providers.lookers(settings):
        if looker.name == company and str(looker.viewer()).lower() == name:
            uses.append(gateway.LOOK_PURPOSE)
    return sorted(set(uses))


def _file_questions(
    conn: sqlite3.Connection,
    settings: Any,
    seen: dict[tuple[str, str], Seen],
    read: dict[str, Prices],
    changes: list[tuple[str, str, str, str | None, str | None]],
    doubts: dict[tuple[str, str], str],
    in_use: set[tuple[str, str]],
    now: datetime,
    judged: dict[str, str],
) -> None:
    """File for a judgement what a rule cannot settle well (familydb/judgement.py): a model in
    use going with more than one to take its place, new models for a company in use, a price
    of one in use the lists disagree on. Filed once each, and only while judgements are on."""
    from familydb import judgement

    if not settings.judgements:
        return
    today = now.date()
    at = utc_iso(now)
    horizon = (today + timedelta(days=RETIRING_DAYS)).isoformat()
    for company, name in sorted(in_use):
        model = seen.get((company, name))
        if model is None:
            continue
        going = model.listed is False or bool(model.retires_on and model.retires_on <= horizon)
        options = shortlist(seen, company, name, today)
        if going and len(options) > 1 and f"{company}:{name}" not in judged:
            judgement.file_replacement(conn, model, options, uses_of(settings, company, name), at)
        if (company, name) in doubts:
            judgement.file_price(conn, model, read, at)
    for company in sorted({company for company, _ in in_use}):
        if any(owner == company and what in ("new", "back") for owner, _, what, _, _ in changes):
            judgement.file_lineup(conn, settings, company, seen, today, at)


def load(conn: sqlite3.Connection, *, today: date | None = None) -> None:
    """Put what the checks found in force in this process: prices first from them, the built-in
    table for the rest; the models the settings page offers; a word on those new lately or
    going; and, for each model gone, the one that answers in its place (`prices.swapped`)."""
    today = today or date.today()
    seen = store.all_seen(conn)
    live: dict[str, dict[str, Price]] = {}
    offered: dict[str, list[Seen]] = {}
    notes: dict[tuple[str, str], str] = {}
    swaps: dict[tuple[str, str], str] = {}
    judged = judged_replacements(conn)
    # Everything kept on the first check is as old as the first check: only what came after is new.
    first = min((model.first_seen for model in seen.values()), default="")[:10]
    lately = (today - NEW_FOR).isoformat()
    for (company, name), model in seen.items():
        if model.retires_on and model.retires_on > today.isoformat():
            notes[(company, name)] = f"goes {model.retires_on}"
        elif model.first_seen[:10] > max(first, lately):
            notes[(company, name)] = "new"
        instead = replacement(seen, company, name, today, judged) if gone(model, today) else None
        if instead is not None and swaps_for(model, instead):
            swaps[(company, name)] = instead.model
        if model.input is None or model.output is None:
            continue
        live.setdefault(company, {})[name] = Price(
            input=model.input,
            output=model.output,
            cached=model.cached if model.cached is not None else model.input,
            search=prices.SEARCH.get(company, 0.01),
        )
        if _offerable(model, today):
            offered.setdefault(company, []).append(model)
    shown: dict[str, tuple[str, ...]] = {}
    for company, models in offered.items():
        names = {m.model for m in models}
        keep = [m for m in models if not _snapshot_of(m.model, names)]
        keep.sort(key=lambda m: (m.output or 0, m.model))
        shown[company] = tuple(m.model for m in keep)
    prices.use(live, shown, notes, swaps)
    # What a judgement found a company no longer takes, for every process (providers/parts.py).
    for question in judgement_store.choices(conn, "refused").values():
        choice = str((question.answer or {}).get("choice") or "")
        if choice.startswith("part:") and question.facts.get("model"):
            parts.leave_out(question.facts["company"], question.facts["model"], choice[5:])


def _snapshot_of(name: str, names: set[str]) -> bool:
    match = SNAPSHOT.match(name)
    return bool(match and match.group("family") in names)


def run_model_watch(app: Any) -> dict[str, int]:
    """The scheduler's job."""
    return check(app)


def due(conn: sqlite3.Connection, now: datetime) -> bool:
    """Whether a day has passed since the last check, for the catch-up after a restart."""
    last = store.stamp(conn)
    if last is None:
        return True
    return now - datetime.fromisoformat(last.replace("Z", "+00:00")) >= timedelta(hours=23)
