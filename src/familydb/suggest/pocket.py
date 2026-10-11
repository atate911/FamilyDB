"""Stage: checking covers finds (docs/FINDS.md), as it covers the family's ideas. Each find is
checked by the same code, with no model: its days against the window, the free time and the hours
asked, who it is for and the ages of the kids coming, the family's firm rules against its words,
the weather when it is outdoors, and the drive when its place is known. Each gets a verdict
(good, possible, ruled out) and its reasons.

A find stands in as an idea (`_stand_in`) with a negative id that never leaves this module, and
goes through `shortlist` and `evaluate` with its own place: the one a lookup filled in, else one
made from what the listing says, where a timed event's time is its "hours", so the free-time
check holds it to when it is on. A find on all day has no hours to be held to. What it says in an
idea's words ("open Saturday 19:00-21:00") is said in an event's ("on Saturday 19:00-21:00").
"""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from familydb.base.clock import Clock
from familydb.base.config import Settings
from familydb.hours import DAYS
from familydb.integrations.geocode import estimate_travel
from familydb.store import finds, places
from familydb.store.ideas import Idea
from familydb.store.members import Member
from familydb.store.places import Place
from familydb.suggest.evaluate import MIN_VISIT_MINUTES, evaluate
from familydb.suggest.shortlist import shortlist
from familydb.suggest.types import Constraints, Context, WebFind

# A timed event's run is given as hours for at most this many days.
RUN_DAYS = 14
# Said of something on a date the page gave only in words.
UNREAD_DAY = "day as the page says it, not checked"
# The reasons kept with a find, as an idea's are shown (compose.py).
REASONS_KEPT = 3
# An idea's words for its hours, as an event's.
AS_EVENT = (
    ("open only part of the free time", "on during part of the free time"),
    ("not enough continuous opening and free time", "not enough free time around it"),
    ("hours not listed", "times not listed"),
    ("open ", "on "),
    # A day of its run is never closed: no free time while it is on is all "closed" can mean.
    ("closed ", "busy while it is on, "),
)


def _day(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None


def _minute(text: str) -> str | None:
    """The "HH:MM" of a stored "YYYY-MM-DDTHH:MM", or None for a day alone."""
    return text[11:16] if "T" in text and len(text) >= 16 else None


def _words(found: WebFind, row: finds.Find | None) -> str:
    parts = (found.title, found.summary, found.kind, found.why, row.category if row else None)
    return " ".join(part for part in parts if part).casefold()


def _length(starts: str, ends: str | None) -> int | None:
    """Minutes from a timed start to an end the same day; None when either is no time."""
    if ends is None or _minute(starts) is None or _minute(ends) is None:
        return None
    first, last = datetime.fromisoformat(starts), datetime.fromisoformat(ends)
    minutes = int((last - first).total_seconds() // 60)
    return minutes if 0 < minutes < 24 * 60 and first.date() == last.date() else None


def _hours(starts: str, ends: str | None, last: date) -> dict[str, list[dict[str, str]]] | None:
    """A timed event's time as the hours of each day of its run."""
    opens = _minute(starts)
    first = _day(starts)
    if opens is None or first is None:
        return None
    length = _length(starts, ends) or MIN_VISIT_MINUTES
    start = datetime.fromisoformat(starts[:16])
    closes = min(start + timedelta(minutes=length), start.replace(hour=23, minute=59))
    hours: dict[str, list[dict[str, str]]] = {}
    day = first
    while day <= min(last, first + timedelta(days=RUN_DAYS - 1)):
        hours.setdefault(DAYS[day.weekday()], [{"open": opens, "close": f"{closes:%H:%M}"}])
        day += timedelta(days=1)
    return hours


def _stand_in(
    number: int,
    found: WebFind,
    row: finds.Find | None,
    constraints: Constraints,
) -> Idea:
    """The find as an idea, for the checks ideas go through."""
    starts = (row.starts_at if row else None) or found.starts
    ends = row.ends_at if row else None
    first = _day(starts)
    text = _words(found, row)
    tags = [one for one in (found.kind, row.category if row else None) if one]
    # The family's firm "avoid" rules are tags on an idea; on a find, words in what it says.
    tags += [word for word in constraints.avoid if word in text]
    return Idea(
        id=number,
        kind="event" if first else "outing",
        title=found.title,
        participants=found.for_whom or (row.participants if row else []),
        location_name=(row.venue or row.address) if row else found.address,
        url=found.url or None,
        tags=tags,
        setting=(row.setting if row and row.setting else "either"),  # type: ignore[arg-type]
        duration_min=(_length(starts, ends) if starts else None)
        or (row.duration_min if row else None),
        cost_level=row.cost_level if row else None,
        needs_booking=bool(row.needs_booking) if row else False,
        min_age=found.min_age if found.min_age is not None else (row.min_age if row else None),
        max_age=found.max_age if found.max_age is not None else (row.max_age if row else None),
        happens_from=first.isoformat() if first else None,
        happens_until=(_day(ends) or first).isoformat() if first else None,
        enrichment="done",
        created_at="",
        updated_at="",
    )


def _place(
    conn: sqlite3.Connection,
    idea: Idea,
    found: WebFind,
    row: finds.Find | None,
    settings: Settings,
) -> Place | None:
    """Where it is: the place a lookup filled in, else one made from the listing, with a timed
    event's time as its hours. None when nothing says where or when."""
    filled = places.get(conn, row.place_id) if row and row.place_id else None
    starts = (row.starts_at if row else None) or found.starts
    last = idea.last_day or idea.first_day
    timed = _hours(starts, row.ends_at if row else None, last) if starts and last else None
    if filled is not None:
        return filled.model_copy(update={"hours": timed}) if timed else filled
    lat, lon = (row.lat, row.lon) if row else (None, None)
    address = (row.address if row else None) or found.address
    if timed is None and lat is None and not address:
        return None
    drive = estimate_travel(settings, lat, lon) if lat is not None and lon is not None else None
    return Place(
        id=idea.id,
        name=found.title,
        address=address,
        lat=lat,
        lon=lon,
        hours=timed,
        travel_minutes=drive[0] if drive else None,
        travel_km=drive[1] if drive else None,
        created_at="",
        updated_at="",
    )


def _as_event(reason: str) -> str:
    for said, meant in AS_EVENT:
        if reason.startswith(said):
            return meant + reason[len(said) :]
    return reason


def check_finds(
    conn: sqlite3.Connection,
    found: Sequence[WebFind],
    context: Context,
    constraints: Constraints,
    settings: Settings,
    clock: Clock,
    *,
    people: Sequence[Member],
) -> list[WebFind]:
    """Each find with its verdict, its reasons and the days it fits, in the order given."""
    if not found:
        return []
    stand_ins: dict[int, Idea] = {}
    where: dict[int, Place | None] = {}
    timed: set[int] = set()
    for number, one in enumerate(found, start=1):
        row = finds.get(conn, one.find_id) if one.find_id is not None else None
        idea = _stand_in(-number, one, row, constraints)
        stand_ins[idea.id] = idea
        where[idea.id] = _place(conn, idea, one, row, settings)
        if (row.starts_at if row else None) or one.starts:
            starts = (row.starts_at if row else None) or one.starts or ""
            if _minute(starts) is not None:
                timed.add(idea.id)
    # Every find is checked, whatever ideas the question named.
    asked = dataclasses.replace(constraints, idea_ids=[])
    kept, ruled_out = shortlist(list(stand_ins.values()), context, asked, settings, people=people)
    checked, _ = evaluate(
        conn,
        kept,
        context,
        asked,
        settings,
        clock,
        place_of=lambda idea: where.get(idea.id),
        # A timed event is held to its time, and a place to go any time to its hours (unknown
        # until a lookup finds them); a dated thing on all day to none.
        held_to_hours=lambda idea: idea.id in timed or idea.first_day is None,
        stale=False,
    )
    by_id = {candidate.idea_id: candidate for candidate in checked + ruled_out}
    out = []
    for number, one in enumerate(found, start=1):
        candidate = by_id.get(-number)
        if candidate is None:
            out.append(one)
            continue
        reasons, verdict, days = candidate.reasons, candidate.verdict, candidate.fits_days
        if -number in timed:
            reasons = [_as_event(reason) for reason in reasons]
        elif stand_ins[-number].first_day is None and not one.any_time and one.dates:
            # On a date the page gave only in words: its day is not known, so possible at best.
            reasons = [UNREAD_DAY] + [r for r in reasons if r != "hours not listed"]
            verdict = "possible" if verdict == "good" else verdict
            days = []
        out.append(
            one.model_copy(
                update={
                    "verdict": verdict,
                    "reasons": reasons[:REASONS_KEPT],
                    "fits_days": days,
                }
            )
        )
    return out
