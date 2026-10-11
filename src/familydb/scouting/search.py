"""The searches made while answering somebody (docs/FINDS.md, "searching on request"): what is
on for the days asked (`discover`) and a place nothing saved fits (`find_places`). Each is one
worker turn that hands back with `report_finds`, kept in the shared cache under the request
(with the day). The request is built from the framing, never the question's wording, so
differently worded questions share one search. `saved` marks what the family already has.

When each is asked for is the engine's (suggest/engine.py, suggest/places.wanted)."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import date, timedelta
from typing import Any, Literal, TypeVar
from urllib.parse import urlsplit

from familydb.agent import gateway
from familydb.availability import web_tools_available
from familydb.base.config import Settings
from familydb.base.errors import AgentError
from familydb.moment import DAY_END, DAY_START, Constraints, Context, clock
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn
from familydb.scouting.types import Found
from familydb.store import ideas, places

log = logging.getLogger(__name__)

F = TypeVar("F", bound=Found)

DISCOVER_CACHE_SECONDS = 12 * 3600
NOTE_OFF = "web discovery off"
NOTE_FAILED = "web discovery failed"
NOTE_NO_KEY = "web discovery waits for a model key"
# A place's hours change slowly; the request's hour keeps "open now" honest.
PLACES_CACHE_SECONDS = 3600
PLACE_NOTE_FAILED = "place search failed"


def cache_key(window: tuple[date, date] | None) -> str:
    if window is None:
        return "someday"
    return f"{window[0].isoformat()}:{window[1].isoformat()}"


def _hours(bounds: tuple[int, int]) -> str:
    """A day's bounds to the whole hour, outward, so questions minutes apart share one search."""
    start, end = bounds
    return f"{clock(start // 60 * 60)}-{clock(min(24 * 60, -(-end // 60) * 60))}"


def render_discover_request(context: Context, constraints: Constraints, settings: Settings) -> str:
    """What the worker is asked (window, hours, home, where they are, topic), from the framing
    only, so the same ask in other words shares one cached search."""
    lines = ["Find time-bound things a family could go to near home."]
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


def discover(
    reach: Reach, context: Context, constraints: Constraints
) -> tuple[list[Found], str | None]:
    """Finds for the window, plus a `skipped_checks` note when discovery did not run."""
    if not web_tools_available(reach.settings):
        return [], NOTE_OFF
    if not gateway.can_ask(reach.settings, "discover", api=reach.api):
        return [], NOTE_NO_KEY
    request = render_discover_request(context, constraints, reach.settings)
    window = cache_key(context.window)
    about = f"what is on, {window.replace(':', ' to ')}"
    return search(reach, "discover", window, request, about, failed=NOTE_FAILED)


def search(
    reach: Reach,
    kind: Literal["discover", "places"],
    prefix: str,
    request: str,
    about: str,
    *,
    failed: str,
    seconds: int = DISCOVER_CACHE_SECONDS,
) -> tuple[list[Found], str | None]:
    """One worker turn of `kind` that hands back with `report_finds`, kept in the shared cache
    under the request (with the day) for `seconds`; a failure is a note, never cached."""
    key = f"{prefix}:" + hashlib.sha256((str(reach.clock.today()) + request).encode()).hexdigest()
    # Shared by the chat and scheduler threads; a dict suffices (worst case one duplicate search).
    cache: dict[str, Any] = reach.cache if reach.cache is not None else {}
    now = reach.clock.now()
    entry = cache.get(key)
    if entry is not None and entry["expires_at"] > now:
        return [Found(**find) for find in entry["finds"]], None

    try:
        turn = reach_turn(reach, kind, request, about)
    except AgentError as exc:
        log.warning("%s failed for %s: %s", kind, key, exc)
        return [], f"{failed}: {exc}"
    except Exception as exc:  # must not fail the whole suggestion
        log.exception("%s crashed for %s", kind, key)
        return [], f"{failed}: {type(exc).__name__}: {exc}"
    if turn.result.status != "ok":
        reason = turn.result.error or turn.result.status
        log.warning("%s turn for %s ended %s: %s", kind, key, turn.result.status, reason)
        return [], f"{failed}: {reason}"
    if not turn.handed_back("report_finds"):
        return [], f"{failed}: worker ended without reporting"

    finds: list[dict[str, Any]] = list(turn.ctx.scratch.get("finds", []))
    cache[key] = {"expires_at": now + timedelta(seconds=seconds), "finds": finds}
    log.info("%s for %s found %d item(s)", kind, key, len(finds))
    return [Found(**find) for find in finds], None


def render_places_request(context: Context, constraints: Constraints, settings: Settings) -> str:
    """What the worker is asked, from the framing only, so the same ask in other words is one
    search: what, when (to the hour), where, and the limits."""
    lines = [f"Find places for: {constraints.topic}."]
    if context.window is not None:
        start, end = context.window
        days = [day for day in context.days if day.bounds[1] > day.bounds[0]]
        if days and start == end:
            first, last = days[0].bounds
            hours = f"{clock(first // 60 * 60)}-{clock(min(24 * 60, -(-last // 60) * 60))}"
            lines.append(f"Open: {start:%A %d %B %Y}, {hours}.")
        else:
            lines.append(f"Open: {start:%A %d %B} to {end:%A %d %B %Y}.")
    lines.append(f"Home area: {settings.home_area or 'not set'}.")
    if context.origin is not None:
        origin = context.origin
        lines.append(f"They are near: {origin.label} ({origin.lat:.3f}, {origin.lon:.3f}).")
    limits = {
        "max_cost_level": constraints.max_cost_level,
        "setting": constraints.setting,
        "max_travel_minutes": constraints.max_travel_minutes,
        "avoid": constraints.avoid or None,
    }
    said = [
        f"{key} {', '.join(value) if isinstance(value, list) else value}"
        for key, value in limits.items()
        if value is not None
    ]
    if said:
        lines.append("Keep to: " + "; ".join(said) + ".")
    return "\n".join(lines)


def find_places(
    reach: Reach, context: Context, constraints: Constraints
) -> tuple[list[Found], str | None]:
    """Places found for the topic, each marked when already saved; a note when none could be."""
    if not gateway.can_ask(reach.settings, "places", api=reach.api):
        return [], "place search waits for a model key"
    request = render_places_request(context, constraints, reach.settings)
    found, note = search(
        reach,
        "places",
        "places",
        request,
        f"places for {constraints.topic}",
        failed=PLACE_NOTE_FAILED,
        seconds=PLACES_CACHE_SECONDS,
    )
    return saved(reach.conn, found), note


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
