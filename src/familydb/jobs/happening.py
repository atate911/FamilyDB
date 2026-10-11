"""What is on near home, kept up to date (familydb/happening.py): the calendars the family reads,
Ticketmaster, scouting each night, and a lookup every few weeks for calendars to offer them.

Hourly, and each source only when it is due: a calendar and Ticketmaster once a day (`PULL_GAP`),
scouting once each evening after the evening's lookups (`lookup_hour`), the lookup for calendars
every `happening_refind_days` and at once when the home area changes. An hour after a calendar
is pasted it has been read; an idle tick reads the list of sources and returns.

Reading a calendar or Ticketmaster is code, with no model, and costs nothing. Scouting and the
calendar lookup are worker turns (agent/gateway.KINDS `scout` and `find_feeds`), made only while
web lookups are on, home is set, a worker key is there, and both the day's limit and the job's
own monthly budget (`happening_budget`) have room. Scouting is rationed besides: a night's share
is what is left of the month over the nights left, and it runs only when a scouting turn, as
they have cost lately, fits it (`affordable`). No transaction is open around a turn.

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
from familydb.availability import (
    calendar_available,
    happening_available,
    happening_search_available,
    ticketmaster_available,
    weather_available,
)
from familydb.base.dates import last_hour_passed, utc_iso
from familydb.integrations.events import FoundEvent
from familydb.integrations.ical import FeedAPI, FeedError, IcalFeeds, parse_feed
from familydb.integrations.ticketmaster import Ticketmaster, TicketmasterAPI
from familydb.scouting import fill, judging, near_home, search
from familydb.scouting.brief import brief
from familydb.scouting.reach import Reach
from familydb.store import calls, memories
from familydb.store import finds as store
from familydb.store import members as member_store
from familydb.store.db import transaction
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

PULL_GAP = timedelta(hours=23)
# A calendar lookup that failed is tried again after this long.
RETRY_GAP = timedelta(days=6, hours=12)
# What each of an evening's calls is taken to cost until some have been measured, and how far
# back they are measured.
ESTIMATES = {"scout": 0.05, "fill_find": 0.03, "curate": 0.01}
MEASURED_DAYS = 30
# What an evening fills in at most, and how much of the pocket is checked and judged.
FILLS_AN_EVENING = 3
POCKET_MOST = 30
SOURCE_FAILURES = 3
KEEP_PAST_DAYS = 3
# How far ahead a proposed calendar must list something to be offered.
PROPOSAL_DAYS = 60
# A worker turn's cost is held before it is made and counted once it is recorded; this is the
# room the budget must have for one more, so the last one of a month does not overrun it.
CALL_ALLOWANCE = 0.12
COUNTS = ("read", "failed", "added", "updated", "gone", "searched", "proposed", "filled", "judged")


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
        return due(look, RETRY_GAP, now)
    return due(look, timedelta(days=settings.happening_refind_days), now)


def scout_due(settings: Any, last: store.FindSource | None, now: datetime) -> bool:
    """Not yet scouted since this evening's lookups began (`lookup_hour`), however it went."""
    checked = _when(last.checked_at) if last else None
    return checked is None or checked < last_hour_passed(now, settings.lookup_hour, settings.tzinfo)


def evening_room(conn: sqlite3.Connection, settings: Any, now: datetime) -> float:
    """What is left to spend this evening: the evening's share of what was left of the month's
    budget when it began (over the nights left, tonight among them), less what it has spent."""
    evening = utc_iso(last_hour_passed(now, settings.lookup_hour, settings.tzinfo))
    tonight = calls.spent_on(conn, happening.KINDS, since=evening)
    local = now.astimezone(settings.tzinfo).date()
    month_end = (local.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    before = happening.spent_this_month(conn, settings, now) - tonight
    share = max(0.0, settings.happening_budget - before) / ((month_end - local).days + 1)
    return share - tonight


def affordable(conn: sqlite3.Connection, settings: Any, now: datetime, kind: str = "scout") -> bool:
    """Whether one more call of this kind, at what it has cost lately, fits the evening's room."""
    since = utc_iso(now - timedelta(days=MEASURED_DAYS))
    turns, average = calls.average_turn_cost(conn, kind, since=since)
    likely = average if turns else ESTIMATES[kind]
    return likely <= evening_room(conn, settings, now)


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


def search_web(
    app: Any, conn: sqlite3.Connection, *, start: date, end: date, now: datetime, api: Any
) -> tuple[int, int]:
    """The night's scouting, on the theme of the day. Returns (new finds kept, 1 when it ran)."""
    theme = near_home.theme_for(start)
    found = near_home.scout(Reach.of_app(app, conn, api), start=start, end=end, theme=theme)
    if isinstance(found, str):
        _answered(conn, happening.WEB_SOURCE, happening.WEB, ok=False, note=found, found=0, now=now)
        return 0, 1
    keeping = [new for new in (search.as_new(one) for one in found) if new is not None]
    with transaction(conn):
        _, added = store.keep(conn, happening.WEB_SOURCE, happening.WEB, keeping, now=utc_iso(now))
    _answered(
        conn,
        happening.WEB_SOURCE,
        happening.WEB,
        ok=True,
        note=f"{len(keeping)} found, on {theme.split(':')[0]}",
        found=len(keeping),
        now=now,
    )
    return added, 1


def _room(app: Any, conn: sqlite3.Connection, kind: str) -> bool:
    now = app.clock.now()
    return within_budget(conn, app.settings, now) and affordable(conn, app.settings, now, kind)


def fill_finds(app: Any, conn: sqlite3.Connection, *, today: date, api: Any) -> int:
    """Fill in the newest finds nobody has looked up, a few an evening, while it has room.
    Returns how many were filled in or found to have nothing more."""
    reach = Reach.of_app(app, conn, api)
    done = 0
    for found in store.to_fill(conn, today=today, limit=FILLS_AN_EVENING):
        if not _room(app, conn, "fill_find"):
            break
        outcome = fill.fill_find(reach, found)
        if outcome == "deferred":
            break
        done += outcome in ("done", "skipped")
    return done


def checked_pocket(app: Any, conn: sqlite3.Connection, *, today: date) -> list[Any]:
    """The pocket as checked by code over the next weeks (suggest/pocket.py), against the
    family's calendar, the forecast and their firm rules; what is ruled out is left out."""
    from familydb.suggest.context import build_context
    from familydb.suggest.listed import to_web_find
    from familydb.suggest.pocket import check_finds
    from familydb.suggest.rules import fold
    from familydb.suggest.types import Constraints

    settings = app.settings
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=app.clock,
        calendar=app.calendar if calendar_available(settings) else None,
        weather=app.weather if weather_available(settings) else None,
        geocoder=app.geocoder,
        source="job",
    )
    context = build_context(ctx, (today, today + timedelta(days=happening.HORIZON_DAYS)))
    people = member_store.list_all(conn)
    held = fold(Constraints(), memories.held(conn, today=today), people, None)
    found = [to_web_find(one) for one in store.pocket(conn, today=today, limit=POCKET_MOST)]
    checked = check_finds(conn, found, context, held, settings, app.clock, people=people)
    return [one for one in checked if one.verdict != "ruled_out"]


def judge_pocket(app: Any, conn: sqlite3.Connection, *, today: date, api: Any) -> int:
    """Judge the pocket when something in it is new or newly filled in, while the evening has
    room: which finds to put forward, and when. Returns how many were recommended."""
    if not store.judging_due(conn, today=today) or not _room(app, conn, "curate"):
        return 0
    looked_at = [one.id for one in store.pocket(conn, today=today, limit=POCKET_MOST)]
    chosen: dict[int, dict[str, str | None]] = {}
    try:
        pocket = checked_pocket(app, conn, today=today)
        if pocket:
            about = brief(conn, app.settings, today=today).text
            said = judging.judge(Reach.of_app(app, conn, api), pocket, about)
            if isinstance(said, str):
                log.warning("the pocket was not judged: %s", said)
                return 0
            chosen = said
    except Exception:  # the calendars and Ticketmaster were read; tomorrow evening tries again
        log.exception("the pocket could not be judged")
        return 0
    with transaction(conn):
        store.judged(conn, looked_at, chosen, now=utc_iso(app.clock.now()))
    return len(chosen)


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
    handed = near_home.look_for_calendars(Reach.of_app(app, conn, api), known, stopped)
    if isinstance(handed, str):
        _answered(conn, source, "proposals", ok=False, note=handed, found=0, now=now)
        return 0
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
            search_due = scout_due(settings, last.get(happening.WEB_SOURCE), now)
            if (look_due or search_due) and app.can_ask("worker", api=api, kind="scout"):
                if look_due and within_budget(conn, settings, now):
                    counts["proposed"] = propose_feeds(
                        app, conn, feeds, today=today, now=now, api=api
                    )
                if search_due and within_budget(conn, settings, now):
                    if affordable(conn, settings, now):
                        kept, ran = search_web(app, conn, start=start, end=end, now=now, api=api)
                        counts["added"] += kept
                        counts["searched"] += ran
                    # Then, while the evening has room, a few finds filled in and the pocket
                    # judged (docs/FINDS.md, "A night").
                    counts["filled"] = fill_finds(app, conn, today=today, api=api)
                    counts["judged"] = judge_pocket(app, conn, today=today, api=api)

        if counts["read"] or counts["searched"]:  # once a day, with the day's reads
            with transaction(conn):
                store.prune(conn, before=today - timedelta(days=KEEP_PAST_DAYS))
    if any(counts.values()):
        log.info("what is on near home: %s", counts)
    return counts
