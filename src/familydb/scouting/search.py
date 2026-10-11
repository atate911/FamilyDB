"""The search made while answering somebody (docs/FINDS.md, "searching on request"): one worker
turn for events on the days asked and places to go alike, told the question in their words and
everything known about the family (scouting/brief.py), that hands back with `report_finds`. What
it finds is kept as finds (kind `request`) so nothing paid for is lost, and offered with the
answer. One search a turn (noted in the turn's scratch), cached in the shared cache under the
framing and the brief's steady part (with the day), so the same ask in other words is not
searched again. `saved` marks what the family already has.

When it is asked for is the engine's (suggest/engine.py): every planning question, while web
lookups are on."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import date, timedelta
from typing import Any, TypeVar
from urllib.parse import urlsplit

from familydb.agent import gateway
from familydb.availability import web_tools_available
from familydb.base.config import Settings
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.moment import DAY_END, DAY_START, Constraints, Context, clock
from familydb.scouting.brief import brief
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn
from familydb.scouting.types import Found
from familydb.store import finds, ideas, places
from familydb.store.db import transaction

log = logging.getLogger(__name__)

F = TypeVar("F", bound=Found)

DISCOVER_CACHE_SECONDS = 12 * 3600
# The most of the question's words a search is told.
QUESTION_MOST = 500
NOTE_OFF = "web discovery off"
NOTE_FAILED = "web discovery failed"
NOTE_NO_KEY = "web discovery waits for a model key"
NOTE_ONCE = "the web was searched once already for this message"
# Where the turn notes the search it made (Reach.turn_notes).
SEARCHED = "searched_for"
# Kept as finds under this source and kind (store/finds.py).
SOURCE = "request"


def cache_key(window: tuple[date, date] | None) -> str:
    if window is None:
        return "someday"
    return f"{window[0].isoformat()}:{window[1].isoformat()}"


def _hours(bounds: tuple[int, int]) -> str:
    """A day's bounds to the whole hour, outward, so questions minutes apart share one search."""
    start, end = bounds
    return f"{clock(start // 60 * 60)}-{clock(min(24 * 60, -(-end // 60) * 60))}"


def render_discover_request(context: Context, constraints: Constraints, settings: Settings) -> str:
    """The framing of the search (window, hours, home, where they are, topic, limits): with the
    brief, what the cache knows it by, so the same ask in other words shares one search."""
    lines = ["Find things this family would enjoy: events on these days, and places to go."]
    if constraints.topic:
        lines.append(f"Looking for: {constraints.topic}.")
    if context.window is None:
        lines.append("Window: no fixed dates; look at the next four weeks or so.")
    else:
        start, end = context.window
        if start == end:
            lines.append(f"Window: {start:%A %d %B %Y}.")
        else:
            lines.append(f"Window: {start:%A %d %B} to {end:%A %d %B %Y}.")
        hours = [_hours(day.bounds) for day in context.days]
        if len(set(hours)) == 1 and hours[0] != _hours((DAY_START, DAY_END)):
            lines.append(f"Hours: {hours[0]}.")
        elif len(set(hours)) > 1:
            each = zip(context.days, hours, strict=True)
            lines.append("Hours: " + "; ".join(f"{d.date:%a} {h}" for d, h in each) + ".")
    lines.append(f"Home area: {settings.home_area or 'not set'}.")
    if context.origin is not None:
        # About a hundred metres, so a phone moving along a street shares the search.
        origin = context.origin
        lines.append(f"They are near: {origin.label} ({origin.lat:.3f}, {origin.lon:.3f}).")
    wanted = {
        "who": constraints.participants or None,
        "max_cost_level": constraints.max_cost_level,
        "setting": constraints.setting,
        "max_travel_minutes": constraints.max_travel_minutes,
        "max_duration_minutes": constraints.max_duration_minutes,
        "avoid": constraints.avoid or None,
    }
    wanted = {k: v for k, v in wanted.items() if v is not None}
    if wanted:
        lines.append("Constraints: " + json.dumps(wanted, sort_keys=True))
    return "\n".join(lines)


def render_search_request(framing: str, question: str, about_family: str) -> str:
    """What the worker is asked: the framing, the question in their words, and the family."""
    said = " ".join(question.split())[:QUESTION_MOST]
    return f"{framing}\nThey asked: {said}\n\nAbout the family:\n{about_family}"


def search_for(
    reach: Reach, context: Context, constraints: Constraints, question: str
) -> tuple[list[Found], str | None]:
    """What suits them for the window, found on the web and kept as finds, plus a
    `skipped_checks` note when no search ran."""
    if not web_tools_available(reach.settings):
        return [], NOTE_OFF
    if not gateway.can_ask(reach.settings, "discover", api=reach.api):
        return [], NOTE_NO_KEY
    framing = render_discover_request(context, constraints, reach.settings)
    about_family = brief(reach.conn, reach.settings, today=reach.clock.today())
    window = cache_key(context.window)
    key = (
        f"{window}:"
        + hashlib.sha256(
            (str(reach.clock.today()) + framing + about_family.steady).encode()
        ).hexdigest()
    )
    # One search a turn: a second look at other days reads the pocket, not the web.
    notes = reach.turn_notes if reach.turn_notes is not None else {}
    if notes.get(SEARCHED, key) != key:
        return [], NOTE_ONCE
    request = render_search_request(framing, question, about_family.text)
    about = f"what suits them, {window.replace(':', ' to ')}"
    found, note = search(reach, key, request, about, failed=NOTE_FAILED)
    if note is None:
        notes[SEARCHED] = key
    return keep(reach, found), note


def search(
    reach: Reach,
    key: str,
    request: str,
    about: str,
    *,
    failed: str,
    seconds: int = DISCOVER_CACHE_SECONDS,
) -> tuple[list[Found], str | None]:
    """One `discover` worker turn that hands back with `report_finds`, kept in the shared cache
    under `key` for `seconds`; a failure is a note, never cached."""
    # Shared by the chat and scheduler threads; a dict suffices (worst case one duplicate search).
    cache: dict[str, Any] = reach.cache if reach.cache is not None else {}
    now = reach.clock.now()
    entry = cache.get(key)
    if entry is not None and entry["expires_at"] > now:
        return [Found(**find) for find in entry["finds"]], None

    try:
        turn = reach_turn(reach, "discover", request, about)
    except AgentError as exc:
        log.warning("discover failed for %s: %s", key, exc)
        return [], f"{failed}: {exc}"
    except Exception as exc:  # must not fail the whole suggestion
        log.exception("discover crashed for %s", key)
        return [], f"{failed}: {type(exc).__name__}: {exc}"
    if turn.result.status != "ok":
        reason = turn.result.error or turn.result.status
        log.warning("discover turn for %s ended %s: %s", key, turn.result.status, reason)
        return [], f"{failed}: {reason}"
    if not turn.handed_back("report_finds"):
        return [], f"{failed}: worker ended without reporting"

    found: list[dict[str, Any]] = list(turn.ctx.scratch.get("finds", []))
    cache[key] = {"expires_at": now + timedelta(seconds=seconds), "finds": found}
    log.info("discover for %s found %d item(s)", key, len(found))
    return [Found(**find) for find in found], None


def as_new(one: Found) -> finds.NewFind | None:
    """A search's find as the back pocket keeps it; None for one whose day code cannot read
    (dates only as words): kept with no day it would read as any time."""
    if not (one.starts or one.any_time):
        return None
    return finds.NewFind(
        title=one.title,
        url=one.url,
        starts=one.starts,
        address=one.address,
        summary=one.summary or None,
        category=one.kind,
        participants=one.for_whom,
        why=one.why,
        min_age=one.min_age,
        max_age=one.max_age,
    )


def keep(reach: Reach, found: list[Found]) -> list[Found]:
    """Keep what a search on request found in the back pocket, each with its find's number;
    what the family passed on is left out of the answer, and one that cannot be kept
    (`as_new`) is offered all the same."""
    keeping = [new for new in (as_new(one) for one in found) if new is not None]
    if not keeping:
        return found
    with transaction(reach.conn):
        kept, _ = finds.keep(reach.conn, SOURCE, SOURCE, keeping, now=utc_iso(reach.clock.now()))
    by_url = {one.url.lower(): one for one in kept if one.url}
    offered = []
    for one in found:
        row = by_url.get(one.url.lower())
        if row is None:
            offered.append(one)
        elif row.state != "passed":
            offered.append(one.model_copy(update={"find_id": row.id}))
    return offered


def _host(url: str | None) -> str | None:
    host = urlsplit(url).hostname if url else None
    return host.removeprefix("www.") if host else None


def saved(conn: sqlite3.Connection, finds: list[F]) -> list[F]:
    """Each find already on the list marked with its idea's number, by its name or its site."""
    if not finds:
        return finds
    sites: dict[str, int] = {}
    for idea in ideas.list_all(conn):
        if idea.status == "dropped":
            continue
        place = places.get(conn, idea.place_id) if idea.place_id else None
        for url in (idea.url, place.website if place else None):
            if host := _host(url):
                sites.setdefault(host, idea.id)
    marked = []
    for find in finds:
        same = ideas.find_similar_title(conn, find.title)
        number = same.id if same is not None and same.status != "dropped" else None
        marked.append(find.model_copy(update={"saved_as": number or sites.get(_host(find.url))}))
    return marked
