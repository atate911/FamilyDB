"""What is on near home, kept up to date (familydb/happening.py): the calendars the family reads,
Ticketmaster, a weekly web search, and a lookup every few weeks for calendars to offer them.

Hourly, and each source only when it is due: a calendar and Ticketmaster once a day (`PULL_GAP`),
the search once a week (`SEARCH_GAP`), the lookup for calendars every `happening_refind_days`
and at once when the home area changes. An hour after a calendar is pasted it has been read; an
idle tick reads the list of sources and returns.

Reading a calendar or Ticketmaster is code, with no model, and costs nothing. The search and the
calendar lookup are worker turns (agent/gateway.KINDS `scout` and `find_feeds`), made only while
web lookups are on, home is set, a worker key is there, and both the day's limit and the job's
own monthly budget (`happening_budget`) have room. No transaction is open around a turn.

A source that cannot be read is retried the next day, and told to admins once it has failed
three days running (alerts `happening`), forgotten when it reads again. Calendars the lookup
found are each read by code before they are offered, and admins are told once when there are
new ones (alerts `calendars`). A source taken off the settings is forgotten with what it found.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from typing import Any

from familydb import alerts, happening
from familydb.agent import gateway, spending
from familydb.agent.loop import MessagesAPI
from familydb.agent.worker import home_location, run_worker_turn
from familydb.availability import (
    happening_available,
    happening_search_available,
    ticketmaster_available,
)
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.integrations.events import FoundEvent
from familydb.integrations.ical import FeedAPI, FeedError, IcalFeeds, parse_feed
from familydb.integrations.ticketmaster import Ticketmaster, TicketmasterAPI
from familydb.store import finds as store
from familydb.store.db import transaction

log = logging.getLogger(__name__)

PULL_GAP = timedelta(hours=23)
SEARCH_GAP = timedelta(days=6, hours=12)
SOURCE_FAILURES = 3
KEEP_PAST_DAYS = 3
# How far ahead a proposed calendar must list something to be offered.
PROPOSAL_DAYS = 60
# A worker turn's cost is held before it is made and counted once it is recorded; this is the
# room the budget must have for one more, so the last one of a month does not overrun it.
CALL_ALLOWANCE = 0.12
COUNTS = ("read", "failed", "added", "updated", "gone", "searched", "proposed")


def configured_sources(settings: Any) -> dict[str, str]:
    """Every source the settings call for, by name, with its kind."""
    wanted = {happening.feed_source(url): happening.FEED for url in happening.feed_urls(settings)}
    if ticketmaster_available(settings):
        wanted[happening.TICKETMASTER_SOURCE] = happening.TICKETMASTER
    if happening_search_available(settings):
        wanted[happening.WEB_SOURCE] = happening.WEB
        if settings.home_area:
            wanted[happening.proposals_source(settings.home_area)] = "proposals"
    return wanted


def _when(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def due(last: store.FindSource | None, gap: timedelta, now: datetime) -> bool:
    """Never read, or last read at least `gap` ago, however it went."""
    checked = _when(last.checked_at) if last else None
    return checked is None or now - checked >= gap


def _look_due(settings: Any, last: dict[str, store.FindSource], now: datetime) -> bool:
    """The lookup for calendars: never made for this home area (a new one asks at once), made
    `happening_refind_days` ago, or failed and a week has gone by."""
    if not settings.home_area:
        return False
    look = last.get(happening.proposals_source(settings.home_area))
    if look is not None and not look.ok:
        return due(look, SEARCH_GAP, now)
    return due(look, timedelta(days=settings.happening_refind_days), now)


def within_budget(conn: sqlite3.Connection, settings: Any, now: datetime) -> bool:
    if not gateway.month_room(conn, settings, "scout", now, estimate=CALL_ALLOWANCE):
        return False
    return not spending.used_up(conn, settings, now)


def _answered(
    conn: sqlite3.Connection,
    source: str,
    kind: str,
    *,
    ok: bool,
    note: str,
    found: int,
    now: datetime,
) -> None:
    """Keep how a source answered, and tell admins of one that has failed days running."""
    with transaction(conn):
        failures = store.source_answered(
            conn, source, kind, ok=ok, note=note, found=found, at=utc_iso(now)
        )
    if ok:
        alerts.working(conn, "happening", source)
    elif failures >= SOURCE_FAILURES:
        name = happening.source_name(source)
        alerts.note(
            conn,
            "happening",
            source,
            f"{name} could not be read for {failures} days running ({note})",
            now,
        )


def _keep(
    conn: sqlite3.Connection,
    source: str,
    kind: str,
    events: list[FoundEvent],
    *,
    tz: Any,
    start: date,
    end: date,
    now: datetime,
    gone: bool = True,
) -> tuple[int, int, int]:
    """Keep what a source listed; with `gone`, mark gone what it no longer lists in the days
    read. Returns (added, updated, gone)."""
    at = utc_iso(now)
    with transaction(conn):
        added, updated = store.upsert_many(conn, source, kind, events, tz=tz, now=at)
        dropped = (
            store.mark_gone(
                conn, source, seen={e.external_id for e in events}, start=start, end=end, now=at
            )
            if gone
            else 0
        )
    return added, updated, dropped


def render_scout_request(settings: Any, start: date, end: date) -> str:
    """The weekly search, in the discovery worker's terms: the window and the home area, and
    nothing about the family."""
    return "\n".join(
        [
            "Find time-bound things a family could go to near home.",
            f"Window: {start:%A %d %B} to {end:%A %d %B %Y}.",
            f"Home area: {settings.home_area or 'not set'}.",
        ]
    )


def render_feeds_request(settings: Any, known: list[str], stopped: list[str]) -> str:
    lines = [
        "Find public event calendars near home that a family could subscribe to.",
        f"Home area: {settings.home_area}.",
    ]
    if known:
        lines.append("Already known, do not report:")
        lines.extend(f"- {url}" for url in known)
    if stopped:
        lines.append("Stopped answering; another address for the same calendar is welcome:")
        lines.extend(f"- {url}" for url in stopped)
    return "\n".join(lines)


def scout_events(
    found: list[dict[str, Any]], *, tz: Any, start: date, end: date
) -> list[FoundEvent]:
    """The search's finds that say when they start, inside the days searched."""
    events = []
    for one in found:
        starts_text = one.get("starts")
        if not starts_text:
            continue
        try:
            if "T" in starts_text:
                starts: datetime | date = datetime.fromisoformat(starts_text).replace(tzinfo=tz)
            else:
                starts = date.fromisoformat(starts_text)
        except ValueError:
            continue
        day = starts.date() if isinstance(starts, datetime) else starts
        if not start <= day <= end:
            continue
        summary = one.get("summary") or ""
        if one.get("dates"):
            summary = f"{summary} ({one['dates']})".strip()
        events.append(
            FoundEvent(
                external_id=one["url"],
                title=one.get("title") or one["url"],
                starts=starts,
                all_day=not isinstance(starts, datetime),
                url=one["url"],
                summary=summary or None,
            )
        )
    return events


def _ask(app: Any, conn: sqlite3.Connection, kind: str, request: str, about: str, api: Any) -> Any:
    """One worker turn; None when it did not hand back."""
    try:
        turn = run_worker_turn(
            kind=kind,
            api=api,
            settings=app.settings,
            clock=app.clock,
            registry=app.registry,
            conn=conn,
            request=request,
            user_location=home_location(app.settings),
            about=about,
        )
    except AgentError as exc:
        log.warning("%s turn failed: %s", kind, exc)
        return str(exc)
    if turn.result.status != "ok" or not turn.handed_back():
        return turn.result.error or turn.result.status or "ended without handing back"
    return turn


def search_web(
    app: Any, conn: sqlite3.Connection, *, start: date, end: date, now: datetime, api: Any
) -> tuple[int, int]:
    """The weekly search near home. Returns (finds kept, 1 when it ran)."""
    settings = app.settings
    turn = _ask(
        app, conn, "scout", render_scout_request(settings, start, end), "what is on near home", api
    )
    if isinstance(turn, str):
        _answered(conn, happening.WEB_SOURCE, happening.WEB, ok=False, note=turn, found=0, now=now)
        return 0, 1
    events = scout_events(
        list(turn.ctx.scratch.get("finds", [])), tz=settings.tzinfo, start=start, end=end
    )
    added, updated, _ = _keep(
        conn,
        happening.WEB_SOURCE,
        happening.WEB,
        events,
        tz=settings.tzinfo,
        start=start,
        end=end,
        now=now,
        gone=False,  # a week's search finds what it finds; last week's are still on
    )
    _answered(
        conn,
        happening.WEB_SOURCE,
        happening.WEB,
        ok=True,
        note=f"{len(events)} dated",
        found=len(events),
        now=now,
    )
    return added + updated, 1


def _readable(feeds: FeedAPI, url: str, *, tz: Any, today: date) -> int | None:
    """How many things a calendar lists in the next weeks, or None when it is not one."""
    try:
        body = feeds.read(url)
        return len(parse_feed(body, tz=tz, start=today, end=today + timedelta(days=PROPOSAL_DAYS)))
    except FeedError as exc:
        log.info("proposed calendar %s did not read: %s", url, exc)
        return None


def propose_feeds(
    app: Any, conn: sqlite3.Connection, feeds: FeedAPI, *, today: date, now: datetime, api: Any
) -> int:
    """Look for calendars near home, keep those that read as one, and tell admins of new ones.
    Returns how many are new."""
    settings = app.settings
    area = settings.home_area
    source = happening.proposals_source(area)
    tz = settings.tzinfo
    reading = happening.feed_urls(settings)
    before = {one.url: one for one in store.proposals(conn, area)}
    stopped = [
        s.source[len(happening.FEED_PREFIX) :]
        for s in store.sources(conn)
        if s.source.startswith(happening.FEED_PREFIX) and s.failures >= SOURCE_FAILURES
    ]
    known = sorted(set(before) | set(reading))
    turn = _ask(
        app,
        conn,
        "find_feeds",
        render_feeds_request(settings, known, stopped),
        "event calendars near home",
        api,
    )
    if isinstance(turn, str):
        _answered(conn, source, "proposals", ok=False, note=turn, found=0, now=now)
        return 0
    handed = {one["url"]: one for one in turn.ctx.scratch.get("feeds", [])}
    readable: list[store.Readable] = []
    for url, one in before.items():  # those offered before, read again to see they still are
        events = _readable(feeds, url, tz=tz, today=today)
        if events:
            readable.append(store.Readable(url=url, title=one.title, note=one.note, events=events))
    new_names = []
    for url, one in handed.items():
        if url in before or url in reading:
            continue
        events = _readable(feeds, url, tz=tz, today=today)
        if events:
            readable.append(
                store.Readable(url=url, title=one["title"], note=one["why"], events=events)
            )
            new_names.append(one["title"])
    with transaction(conn):
        new, kept, dropped = store.merge_proposals(conn, area, readable, now=utc_iso(now))
    _answered(
        conn,
        source,
        "proposals",
        ok=True,
        note=f"{new} new, {kept} kept, {dropped} let go",
        found=new + kept,
        now=now,
    )
    if new_names:
        shown = ", ".join(new_names[:4]) + (
            f" and {len(new_names) - 4} more" if len(new_names) > 4 else ""
        )
        count = len(new_names)
        alerts.note(
            conn,
            "calendars",
            f"{area}:{today.isoformat()}",
            f"{count} new event calendar{'' if count == 1 else 's'}: {shown}",
            now,
            once=True,
        )
    return new


def run_happening(
    app: Any,
    *,
    api: MessagesAPI | None = None,
    feeds: FeedAPI | None = None,
    ticketmaster: TicketmasterAPI | None = None,
    everything: bool = False,
) -> dict[str, int]:
    """The scheduler's job: read every source that is due, or with `everything` every source
    (`familydb happening --now`). Returns counts, for the log and the tests. `feeds`,
    `ticketmaster` and `api` stand in for the network and the model in tests."""
    counts = dict.fromkeys(COUNTS, 0)
    with closing(app.connect()) as conn:
        app.refresh(conn)
        settings = app.settings
        wanted = configured_sources(settings) if happening_available(settings) else {}
        last = {one.source: one for one in store.sources(conn)}
        if set(last) - set(wanted):
            with transaction(conn):
                store.forget_sources(conn, wanted)
        if not wanted:
            return counts
        if everything:
            last = {}  # as if none had been read: each is read now, the budget still holding
        now = app.clock.now()
        today = now.astimezone(settings.tzinfo).date()
        start, end = today, today + timedelta(days=happening.HORIZON_DAYS)
        tz = settings.tzinfo
        feeds = feeds or IcalFeeds()

        for url in happening.feed_urls(settings):
            source = happening.feed_source(url)
            if not due(last.get(source), PULL_GAP, now):
                continue
            try:
                events = parse_feed(feeds.read(url), tz=tz, start=start, end=end)
            except Exception as exc:  # a calendar that cannot be read is told of, never a crash
                note = str(exc) if isinstance(exc, FeedError) else f"{type(exc).__name__}: {exc}"
                _answered(conn, source, happening.FEED, ok=False, note=note, found=0, now=now)
                counts["failed"] += 1
                continue
            added, updated, gone = _keep(
                conn, source, happening.FEED, events, tz=tz, start=start, end=end, now=now
            )
            _answered(
                conn,
                source,
                happening.FEED,
                ok=True,
                note=f"{len(events)} on",
                found=len(events),
                now=now,
            )
            counts["read"] += 1
            counts["added"] += added
            counts["updated"] += updated
            counts["gone"] += gone

        source = happening.TICKETMASTER_SOURCE
        if source in wanted and due(last.get(source), PULL_GAP, now):
            client = ticketmaster or Ticketmaster(settings)
            try:
                events = client.events(
                    settings.home_lat, settings.home_lon, settings.happening_radius_km, start, end
                )
            except Exception as exc:
                _answered(conn, source, "ticketmaster", ok=False, note=str(exc), found=0, now=now)
                counts["failed"] += 1
            else:
                added, updated, gone = _keep(
                    conn, source, "ticketmaster", events, tz=tz, start=start, end=end, now=now
                )
                _answered(
                    conn,
                    source,
                    "ticketmaster",
                    ok=True,
                    note=f"{len(events)} on",
                    found=len(events),
                    now=now,
                )
                counts["read"] += 1
                counts["added"] += added
                counts["updated"] += updated
                counts["gone"] += gone

        if happening.WEB_SOURCE in wanted:
            look_due = _look_due(settings, last, now)
            search_due = due(last.get(happening.WEB_SOURCE), SEARCH_GAP, now)
            if (look_due or search_due) and app.can_ask("worker", api=api, kind="scout"):
                if look_due and within_budget(conn, settings, now):
                    counts["proposed"] = propose_feeds(
                        app, conn, feeds, today=today, now=now, api=api
                    )
                if search_due and within_budget(conn, settings, now):
                    kept, ran = search_web(app, conn, start=start, end=end, now=now, api=api)
                    counts["added"] += kept
                    counts["searched"] += ran

        if counts["read"] or counts["searched"]:  # once a day, with the day's reads
            with transaction(conn):
                store.prune(conn, before=today - timedelta(days=KEEP_PAST_DAYS))
    if any(counts.values()):
        log.info("what is on near home: %s", counts)
    return counts
