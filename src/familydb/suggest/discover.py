"""Stage: time-bound things found by one discovery worker turn (`report_finds` hands back) and
cached per window for `DISCOVER_CACHE_SECONDS`. The request is built from the framing, never the
question's wording, so differently worded questions share one search."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from typing import Any, Literal

from familydb.agent import gateway
from familydb.agent.worker import home_location, run_worker_turn
from familydb.availability import web_tools_available
from familydb.base.config import Settings
from familydb.base.errors import AgentError
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
    ctx: ToolContext, context: Context, constraints: Constraints
) -> tuple[list[WebFind], str | None]:
    """Finds for the window, plus a `skipped_checks` note when discovery did not run."""
    if not web_tools_available(ctx.settings):
        return [], NOTE_OFF
    if not gateway.can_ask(ctx.settings, "discover", api=ctx.api):
        return [], NOTE_NO_KEY
    request = render_discover_request(context, constraints, ctx.settings)
    window = cache_key(context.window)
    about = f"what is on, {window.replace(':', ' to ')}"
    return search(ctx, "discover", window, request, about, failed=NOTE_FAILED)


def search(
    ctx: ToolContext,
    kind: Literal["discover", "places"],
    prefix: str,
    request: str,
    about: str,
    *,
    failed: str,
    seconds: int = DISCOVER_CACHE_SECONDS,
) -> tuple[list[WebFind], str | None]:
    """One worker turn of `kind` that hands back with `report_finds`, kept in the shared cache
    under the request (with the day) for `seconds`; a failure is a note, never cached."""
    key = f"{prefix}:" + hashlib.sha256((str(ctx.clock.today()) + request).encode()).hexdigest()
    # Shared by the chat and scheduler threads; a dict suffices (worst case one duplicate search).
    cache: dict[str, Any] = ctx.discover_cache if ctx.discover_cache is not None else {}
    now = ctx.clock.now()
    entry = cache.get(key)
    if entry is not None and entry["expires_at"] > now:
        return [WebFind(**find) for find in entry["finds"]], None

    try:
        turn = run_worker_turn(
            kind=kind,
            api=ctx.api,
            settings=ctx.settings,
            clock=ctx.clock,
            registry=build_registry(),
            conn=ctx.conn,
            request=request,
            message_id=ctx.message_id,
            user_location=home_location(ctx.settings),
            about=about,
        )
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
    return [WebFind(**find) for find in finds], None
