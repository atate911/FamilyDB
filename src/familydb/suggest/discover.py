"""Stage: time-bound things on the web, found by a discovery worker turn and cached for a while.

The chat agent never searches the web itself. When discovery is on, this stage runs one worker
turn (its own prompt, the web tools, `report_finds` as the hand-back) and keeps the finds per
window for `DISCOVER_CACHE_SECONDS`, so a digest and the questions that follow it share one search.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from familydb.agent.worker import home_location, run_worker_turn
from familydb.availability import web_tools_available
from familydb.config import Settings
from familydb.errors import AgentError
from familydb.suggest.types import Context, WebFind
from familydb.tools import ToolContext, build_registry

log = logging.getLogger(__name__)

DISCOVER_CACHE_SECONDS = 12 * 3600
NOTE_OFF = "web discovery off"
NOTE_NO_API = "web discovery not available here"
NOTE_FAILED = "web discovery failed"


def cache_key(window: tuple[date, date] | None) -> str:
    if window is None:
        return "someday"
    return f"{window[0].isoformat()}:{window[1].isoformat()}"


def render_discover_request(context: Context, question: str, settings: Settings) -> str:
    """What the worker is asked: the window, the home area and the family's own words."""
    lines = ["Find time-bound things a family could go to near home."]
    if context.window is None:
        lines.append("Window: no fixed dates; look at the next four weeks or so.")
    else:
        start, end = context.window
        if start == end:
            lines.append(f"Window: {start:%A %d %B %Y}.")
        else:
            lines.append(f"Window: {start:%A %d %B} to {end:%A %d %B %Y}.")
    lines.append(f"Home area: {settings.home_area or 'not set'}.")
    if question.strip():
        lines.append(f'The family asked: "{question.strip()}"')
    return "\n".join(lines)


def discover(ctx: ToolContext, context: Context, question: str) -> tuple[list[WebFind], str | None]:
    """Finds for the window, plus a note for `skipped_checks` when discovery did not run."""
    if not web_tools_available(ctx.settings):
        return [], NOTE_OFF
    if ctx.api is None:
        return [], NOTE_NO_API

    key = cache_key(context.window)
    # The cache lives on the App and is shared by the chat thread and the scheduler thread; a
    # dict is safe enough for that, the worst case being one duplicated search.
    cache: dict[str, Any] = ctx.discover_cache if ctx.discover_cache is not None else {}
    now = ctx.clock.now()
    entry = cache.get(key)
    if entry is not None and entry["expires_at"] > now:
        return [WebFind(**find) for find in entry["finds"]], None

    request = render_discover_request(context, question, ctx.settings)
    try:
        turn = run_worker_turn(
            kind="discover",
            api=ctx.api,
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
