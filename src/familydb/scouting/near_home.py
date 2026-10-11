"""The searches for what is on near home (docs/FINDS.md, "scouting"): the night's scouting for new
things this family would enjoy, on a theme that turns with the week and told the family's brief,
and the lookup for event calendars to offer the family. Each is one worker turn that hands back
(`report_finds`, `report_feeds`); a turn that fails is a note, never raised. What scouting hands
back is sorted by code (`sort`) before it is kept. When each runs, what it may spend, and what is
kept and told is the hourly job's (jobs/happening.py)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from typing import Any

from familydb.agent.worker import WorkerKind, WorkerTurn
from familydb.base.errors import AgentError
from familydb.scouting.brief import brief
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn
from familydb.scouting.search import saved
from familydb.scouting.types import Found
from familydb.store import finds, memories

log = logging.getLogger(__name__)


# Tonight's theme, by the day of the week (Monday first), so nights do not repeat themselves.
THEMES = (
    "food and drink: restaurants, markets, tastings, cooking classes",
    "outdoors: parks, trails, gardens, farms, the water",
    "shows and music: theater, concerts, film, comedy, readings",
    "grown-ups' evenings: date nights, bars, tastings, talks",
    "the weekend ahead: fairs, festivals, markets, family events",
    "classes and clubs: lessons, workshops, sports, groups to join",
    "the weeks ahead: anything worth planning for",
)


def theme_for(day: date) -> str:
    return THEMES[day.weekday()]


def render_scout_request(
    settings: Any, start: date, end: date, *, theme: str, about_family: str
) -> str:
    """The night's scouting: the theme, the four weeks, the home area, and the family's brief
    (scouting/brief.py)."""
    return "\n".join(
        [
            f"Tonight's theme: {theme}.",
            f"Window: {start:%A %d %B} to {end:%A %d %B %Y}.",
            f"Home area: {settings.home_area or 'not set'}.",
            "",
            "About the family:",
            about_family,
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


def ask(reach: Reach, kind: WorkerKind, request: str, about: str) -> WorkerTurn | str:
    """One worker turn; the note saying why when it did not hand back."""
    try:
        turn = reach_turn(reach, kind, request, about)
    except AgentError as exc:
        log.warning("%s turn failed: %s", kind, exc)
        return str(exc)
    if turn.result.status != "ok" or not turn.handed_back():
        return turn.result.error or turn.result.status or "ended without handing back"
    return turn


def scout(reach: Reach, *, start: date, end: date, theme: str) -> list[Found] | str:
    """The night's scouting, aimed at the family: what it handed back, sorted by `sort`; a note
    when it did not run through."""
    about = brief(reach.conn, reach.settings, today=start)
    request = render_scout_request(reach.settings, start, end, theme=theme, about_family=about.text)
    found = ask(reach, "scout", request, f"scouting: {theme.split(':')[0]}")
    if isinstance(found, str):
        return found
    handed = [Found(**one) for one in found.ctx.scratch.get("finds", [])]
    return sort(reach.conn, handed, today=start, end=end)


def sort(conn: sqlite3.Connection, found: list[Found], *, today: date, end: date) -> list[Found]:
    """What scouting found that is new and may be kept: on a day code can read inside the weeks
    searched, or any time; not already an idea, nor something the family saved, planned or
    passed on (by its page or its name); and not something a firm rule avoids by its words."""
    avoid = sorted(
        {
            str(tag).casefold()
            for memory in memories.held(conn, today=today)
            for tag in (memory.rule or {}).get("avoid", ())
            if not memory.inferred
        }
    )
    kept = []
    for one in saved(conn, found):
        day = _day(one.starts)
        if day is None and not one.any_time:
            continue  # its day only in words: kept with none it would read as any time
        if day is not None and not today <= day <= end:
            continue
        if one.saved_as is not None:
            continue
        known = finds.by_url_or_title(conn, one.url, one.title)
        if known is not None and known.state not in finds.OFFERED:
            continue
        words = " ".join(p for p in (one.title, one.summary, one.kind, one.why) if p).casefold()
        if any(tag in words for tag in avoid):
            continue
        kept.append(one)
    return kept


def _day(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None


def look_for_calendars(
    reach: Reach, known: list[str], stopped: list[str]
) -> dict[str, dict[str, Any]] | str:
    """Event calendars near home, by address, as the lookup handed them back; a note when it
    did not run through."""
    found = ask(
        reach,
        "find_feeds",
        render_feeds_request(reach.settings, known, stopped),
        "event calendars near home",
    )
    if isinstance(found, str):
        return found
    return {one["url"]: one for one in found.ctx.scratch.get("feeds", [])}
