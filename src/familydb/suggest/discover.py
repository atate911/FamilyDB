"""Stage: time-bound things on the web, found by a discovery worker turn and cached for a while.

The chat agent never searches the web itself. When discovery is on, this stage runs one worker
turn (its own prompt, the web tools, `report_finds` as the hand-back) and keeps the finds per
window for `DISCOVER_CACHE_SECONDS`, so a digest and the questions that follow it share one search.
The request is built from the framing (the window, where they are, the constraints), never the
question's wording, so "what's on this weekend" and "anything fun Saturday" share one search.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from typing import Any

from familydb.agent import providers
from familydb.agent.worker import home_location, run_worker_turn
from familydb.availability import web_tools_available
from familydb.config import Settings
from familydb.errors import AgentError
from familydb.suggest.types import DAY_END, DAY_START, Constraints, Context, WebFind, clock
from familydb.tools import ToolContext, build_registry

log = logging.getLogger(__name__)

DISCOVER_CACHE_SECONDS = 12 * 3600
NOTE_OFF = "web discovery off"
NOTE_FAILED = "web discovery failed"
NOTE_NO_KEY = "web discovery waits for a model key"


def cache_key(window: tuple[date, date] | None) -> str:
    if window is None:
        return "someday"
    return f"{window[0].isoformat()}:{window[1].isoformat()}"


def _hours(bounds: tuple[int, int]) -> str:
    """A day's bounds to the whole hour, outward: close enough to search by, and the same for
    questions asked a few minutes apart, so they share one search."""
    start, end = bounds
    return f"{clock(start // 60 * 60)}-{clock(min(24 * 60, -(-end // 60) * 60))}"


def render_discover_request(context: Context, constraints: Constraints, settings: Settings) -> str:
    """What the worker is asked: the window and its hours, the home area, where they are, and
    what it is for.

    Built from the framing, never the question's wording: two ways of asking for the same thing
    ask the same, and share one cached search, while a different subject asks something else.
    """
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
        # Rounded to about a hundred metres: close enough to search by, and the same for a phone
        # that has moved along the street, so the search is shared.
        origin = context.origin
        lines.append(f"They are near: {origin.label} ({origin.lat:.3f}, {origin.lon:.3f}).")
    wanted = {
        "who": constraints.participants or None,
        "max_cost_level": constraints.max_cost_level,
        "setting": constraints.setting,
        "max_travel_minutes": constraints.max_travel_minutes,
        "max_duration_minutes": constraints.max_duration_minutes,
    }
    wanted = {k: v for k, v in wanted.items() if v is not None}
    if wanted:
        lines.append("Constraints: " + json.dumps(wanted, sort_keys=True))
    return "\n".join(lines)


def discover(
    ctx: ToolContext, context: Context, constraints: Constraints
) -> tuple[list[WebFind], str | None]:
    """Finds for the window, plus a note for `skipped_checks` when discovery did not run."""
    if not web_tools_available(ctx.settings):
        return [], NOTE_OFF
    if not providers.ready(ctx.settings, "worker", api=ctx.api):
        return [], NOTE_NO_KEY
    request = render_discover_request(context, constraints, ctx.settings)
    key = (
        cache_key(context.window)
        + ":"
        + hashlib.sha256((str(context.today) + request).encode()).hexdigest()
    )
    # The cache lives on the App and is shared by the chat thread and the scheduler thread; a
    # dict is safe enough for that, the worst case being one duplicated search.
    cache: dict[str, Any] = ctx.discover_cache if ctx.discover_cache is not None else {}
    now = ctx.clock.now()
    entry = cache.get(key)
    if entry is not None and entry["expires_at"] > now:
        return [WebFind(**find) for find in entry["finds"]], None

    try:
        turn = run_worker_turn(
            kind="discover",
            api=ctx.api,  # a stand-in when a test injects one; otherwise the settings decide
            settings=ctx.settings,
            clock=ctx.clock,
            registry=build_registry(),
            conn=ctx.conn,
            request=request,
            message_id=ctx.message_id,
            user_location=home_location(ctx.settings),
        )
    except AgentError as exc:
        log.warning("discovery failed for %s: %s", key, exc)
        return [], f"{NOTE_FAILED}: {exc}"
    except Exception as exc:  # a crash in the worker must not fail the whole suggestion
        log.exception("discovery crashed for %s", key)
        return [], f"{NOTE_FAILED}: {type(exc).__name__}: {exc}"
    if turn.result.status != "ok":
        reason = turn.result.error or turn.result.status
        log.warning("discovery turn for %s ended %s: %s", key, turn.result.status, reason)
        return [], f"{NOTE_FAILED}: {reason}"
    if not turn.handed_back("report_finds"):
        return [], f"{NOTE_FAILED}: worker ended without reporting"

    finds: list[dict[str, Any]] = list(turn.ctx.scratch.get("finds", []))
    cache[key] = {"expires_at": now + timedelta(seconds=DISCOVER_CACHE_SECONDS), "finds": finds}
    log.info("discovery for %s found %d item(s)", key, len(finds))
    return [WebFind(**find) for find in finds], None
