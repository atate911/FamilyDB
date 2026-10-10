"""Her picks for a moment: the "What about…" set on Now (docs/INTERFACE.md sections 3 and 4).

Made ahead, by code, so no page view asks a model: the suggestion engine's own assessment of the
family's ideas and the finds the sources list (`suggest.engine.assess`, no lookup re-queued, no
discovery), cut to one pick a kind for this moment, each with its reason. Where a stronger call
chose lately (the weekend digest's picks, `suggestions.picks`), its picks lead the weekend's set.
Two windows: `now` (the next hours, remade every few hours while the day runs) and `weekend`
(remade each morning). A kid gets a weekend set of her own, the engine asked as her, so her rules
and age hold. The page reads the newest set (`store/picks.py`); the hourly job and the catch-up
on start keep them fresh (`jobs/picks.py`). "Different ones" on the page is a message to her, and
costs what a message costs.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta
from typing import Any

from familydb import roles
from familydb.app import App
from familydb.availability import calendar_available, weather_available
from familydb.dates import clock_time, spoken_times, utc_iso
from familydb.store import members as member_store
from familydb.store import picks as pick_store
from familydb.store import suggestions
from familydb.store.db import transaction
from familydb.store.ideas import Idea
from familydb.store.members import Member
from familydb.store.picks import PickSet, Window
from familydb.suggest.engine import Assessment, assess
from familydb.suggest.types import Candidate, Context, SuggestInput
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

# How far "now" looks ahead, and how long each set stands before the job remakes it.
NOW_HOURS = 6
FRESH_FOR = {"now": timedelta(hours=3), "weekend": timedelta(hours=20)}
# A kid's weekend set stands as long as the family's.
# How many tiles each set holds at most.
MOST = {"now": 4, "weekend": 6}
# The stronger call's picks lead for this long after it chose (Thursday's digest through Sunday).
CHOSEN_FOR = timedelta(days=4)
# Nobody is up for a pick before this hour, so the "now" set is not remade through the night.
QUIET_UNTIL = 8
QUIET_FROM = 22
# What each kind of idea is called on a tile, and the order the kinds take when every slot is open.
KIND_WORDS = {
    "restaurant": "Eat",
    "activity": "Do",
    "outing": "Go out",
    "day_trip": "Day trip",
    "trip": "Trip",
    "show": "A show",
    "event": "Something on",
    "seasonal": "Seasonal",
    "home": "Stay in",
    "other": "Idea",
}
FOUND = "New"
# Kinds that are somewhere to go, so "you haven't been" rather than "not done yet".
PLACES = frozenset({"restaurant", "outing", "day_trip", "trip", "show", "event", "seasonal"})
# Only so many reasons on a tile.
WHY_PARTS = 2
QUESTIONS = {"now": "What could we do in the next few hours?", "weekend": "What about the weekend?"}


def due(app: App, conn: sqlite3.Connection, window: Window, member_id: int | None = None) -> bool:
    """Whether a set for this window needs making: none yet, past its freshness, or its days
    over. The "now" window is left alone through the night."""
    now = app.clock.now()
    local = now.astimezone(app.settings.tzinfo)
    if window == "now" and not QUIET_UNTIL <= local.hour < QUIET_FROM:
        return False
    found = pick_store.latest(conn, window=window, member_id=member_id)
    if found is None:
        return True
    today = app.clock.today().isoformat()
    return found.stale_at <= utc_iso(now) or found.window_end < today


def refresh(app: App, *, force: bool = False) -> dict[str, int]:
    """Make every set that is due: the family's "now" and "weekend", and each kid's weekend.
    Returns how many were made per window. No model call."""
    app.refresh()
    made = {"now": 0, "weekend": 0}
    if not app.settings.picks:
        return made
    with closing(app.connect()) as conn:
        people = member_store.list_all(conn)
        kids = [
            m
            for m in people
            if m.active and roles.may(m.role, "wish") and not roles.may(m.role, "decide")
        ]
        for window in pick_store.WINDOWS:
            if (force or due(app, conn, window)) and make(app, conn, window) is not None:
                made[window] += 1
        for kid in kids:
            wanted = force or due(app, conn, "weekend", kid.id)
            if wanted and make(app, conn, "weekend", member=kid) is not None:
                made["weekend"] += 1
        with transaction(conn):
            pick_store.prune(conn, before=utc_iso(app.clock.now() - timedelta(days=7)))
    return made


def make(
    app: App, conn: sqlite3.Connection, window: Window, *, member: Member | None = None
) -> PickSet | None:
    """One set for a window, stored; None when the engine could not run (logged)."""
    settings = app.settings
    ctx = ToolContext(
        conn,
        settings,
        app.clock,
        member=member,
        calendar=app.calendar if calendar_available(settings) else None,
        weather=app.weather if weather_available(settings) else None,
        geocoder=app.geocoder,
        source="job",
    )
    if window == "now":
        asked = SuggestInput(
            window="now", hours=NOW_HOURS, discover=False, question=QUESTIONS[window]
        )
    else:
        asked = SuggestInput(window="this_weekend", discover=False, question=QUESTIONS[window])
    try:
        found = assess(ctx, asked, refresh_stale=False, record=False)
    except Exception:
        log.exception("the picks for %s could not be made", window)
        return None
    found.kid_names = {
        m.id: m.display_name
        for m in member_store.list_all(conn)
        if roles.may(m.role, "wish") and not roles.may(m.role, "decide")
    }
    chosen = _chosen(conn, app.clock.now(), found) if window == "weekend" and member is None else []
    tiles = _tiles(found, chosen, MOST[window], window, app.clock.now().astimezone(settings.tzinfo))
    start, end = found.context.window or (app.clock.today(), app.clock.today())
    now = app.clock.now()
    with transaction(conn):
        return pick_store.insert(
            conn,
            member_id=member.id if member else None,
            window=window,
            window_start=start.isoformat(),
            window_end=end.isoformat(),
            header=_header(found.context, window),
            picks=tiles,
            made_at=utc_iso(now),
            stale_at=utc_iso(now + FRESH_FOR[window]),
            source="chosen" if chosen else "code",
        )


def _chosen(conn: sqlite3.Connection, now: datetime, found: Assessment) -> list[dict[str, Any]]:
    """The stronger call's latest picks for these days, while fresh, as (idea id, reason)."""
    since = utc_iso(now - CHOSEN_FOR)
    for row in sorted(
        suggestions.picked_since(conn, since=since), key=lambda s: s.asked_at, reverse=True
    ):
        start = found.context.window[0] if found.context.window else None
        if start is not None and row.window_start and row.window_start != start.isoformat():
            continue
        picks = (row.picks or {}).get("picks") or []
        return [p for p in picks if isinstance(p, dict) and p.get("idea_id")]
    return []


def _tiles(
    found: Assessment,
    chosen: list[dict[str, Any]],
    most: int,
    window: Window,
    local_now: datetime,
) -> list[dict[str, Any]]:
    """One pick a kind, the stronger call's first, then the engine's best of each kind, then one
    of what the sources list; never a ruled-out idea, never the same kind twice."""
    offered = [c for c in found.shown if c.verdict != "ruled_out"]
    by_id = {c.idea_id: c for c in offered}
    tiles: list[dict[str, Any]] = []
    kinds_taken: set[str] = set()
    for pick in chosen:
        candidate = by_id.get(pick["idea_id"])
        if candidate is None or len(tiles) >= most:
            continue
        kind = (found.by_id[candidate.idea_id].kind or "other").lower().replace(" ", "_")
        kinds_taken.add(kind)
        tiles.append(_tile(candidate, kind, pick.get("reason") or "", found, window, local_now))
    for candidate in offered:
        if len(tiles) >= most:
            break
        if any(t.get("idea_id") == candidate.idea_id for t in tiles):
            continue
        kind = (found.by_id[candidate.idea_id].kind or "other").lower().replace(" ", "_")
        if kind in kinds_taken:
            continue
        kinds_taken.add(kind)
        tiles.append(_tile(candidate, kind, "", found, window, local_now))
    for find in found.finds:
        if len(tiles) >= most:
            break
        if find.saved_as is not None and find.saved_as in by_id:
            continue
        tiles.append(
            {
                "kind": FOUND,
                "when": find.dates or "",
                "title": find.title,
                "why": " ".join(part for part in (find.summary, find.source) if part)[:140],
                "url": find.url or None,
                "idea_id": None,
                "find_id": find.id,
            }
        )
        break  # one of hers: the rest are on Happening soon
    return tiles


def _tile(
    candidate: Candidate,
    kind: str,
    reason: str,
    found: Assessment,
    window: Window,
    local_now: datetime,
) -> dict[str, Any]:
    idea = found.by_id[candidate.idea_id]
    why = reason or _why(candidate, idea, found)
    return {
        "kind": KIND_WORDS.get(kind, KIND_WORDS["other"]),
        "when": _when(candidate, window, local_now),
        "title": idea.title,
        "why": why[:1].upper() + why[1:] if why else "",
        "idea_id": idea.id,
        "url": None,
    }


def _why(candidate: Candidate, idea: Idea, found: Assessment) -> str:
    """One line of why, as a person would say it, from what the engine checked: when it is open,
    how far, that they have not been, that they loved it, or who pitched it. Never the engine's
    own words about missing details."""
    parts = []
    checks = candidate.checks
    if checks.open == "open" and checks.hours:
        last = checks.hours.split(",")[-1].split("-")[-1].strip()
        parts.append(f"open till {spoken_times(last)}" if last and last != "24:00" else "open")
    if checks.travel_minutes:
        parts.append(f"{checks.travel_minutes} min")
    if idea.suggested_by in found.kid_names:
        parts.append(f"{found.kid_names[idea.suggested_by]}\u2019s idea")
    if candidate.idea_id in found.loved:
        parts.append("you loved it")
    elif not idea.times_done:
        parts.append("you haven\u2019t been" if idea.kind in PLACES else "not done yet")
    if checks.weather == "ok" and idea.setting == "outdoor":
        parts.append("and it\u2019s dry")
    return ", ".join(parts[:3])


def _when(candidate: Candidate, window: Window, local_now: datetime) -> str:
    """When a pick fits, briefly: "tonight", "this afternoon", "Sat", "Sat or Sun"."""
    if window == "now":
        if local_now.hour >= 17:
            return "tonight"
        return "this afternoon" if local_now.hour >= 12 else "this morning"
    days = sorted({date.fromisoformat(d) for d in candidate.fits_days})
    names = [f"{d:%a}" for d in days]
    if not names:
        return "weekend"
    return names[0] if len(names) == 1 else " or ".join(names[:2])


def _header(context: Context, window: Window) -> str | None:
    """The one line that drove the set: the weather and the free time of its days. "Dry Saturday,
    free from noon" or "Free this evening"."""
    parts = []
    for day in context.days:
        said = []
        if day.forecast is not None and day.forecast.summary:
            said.append(day.forecast.summary.lower())
        if day.free_known and day.spans:
            first, last = day.spans[0][0], day.spans[-1][1]
            if day.whole:
                said.append("free all day" if window == "weekend" else f"free {_part(first)}")
            elif first > day.bounds[0]:
                said.append(f"free from {_clock(first)}")
            else:
                said.append(f"free till {_clock(last)}")
        if not said:
            continue
        line = ", ".join(said)
        parts.append(f"{day.date:%A}: {line}" if window == "weekend" else line)
    if not parts:
        return None
    header = " · ".join(parts)
    return header[:1].upper() + header[1:]


def _clock(minute: int) -> str:
    """A minute of the day as the family reads it: "9 pm", "12 am" for the day's end."""
    return clock_time(time(minute // 60 % 24, minute % 60))


def _part(minute: int) -> str:
    hour = minute // 60
    return "this evening" if hour >= 17 else "this afternoon" if hour >= 12 else "today"
