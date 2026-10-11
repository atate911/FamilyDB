"""The searches for what is on near home (docs/FINDS.md, "scouting"): the search for things to go
to, and the lookup for event calendars to offer the family. Each is one worker turn that hands
back (`report_finds`, `report_feeds`); a turn that fails is a note, never raised. When each runs,
what it may spend, and what is kept and told is the hourly job's (jobs/happening.py)."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from familydb.agent.worker import WorkerKind, WorkerTurn
from familydb.base.errors import AgentError
from familydb.integrations.events import FoundEvent
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn

log = logging.getLogger(__name__)


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


def scout(reach: Reach, *, start: date, end: date) -> list[FoundEvent] | str:
    """The search for what is on near home, as events in the days searched; a note when it did
    not run through."""
    found = ask(
        reach, "scout", render_scout_request(reach.settings, start, end), "what is on near home"
    )
    if isinstance(found, str):
        return found
    return scout_events(
        list(found.ctx.scratch.get("finds", [])), tz=reach.settings.tzinfo, start=start, end=end
    )


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
