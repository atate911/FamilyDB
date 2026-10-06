"""What is on, day by day, for the Plans and home pages.

With Google connected this is Google's calendar: a phone edit shows within a minute (the page
keeps Google's answer `PAGE_READ_SECONDS`, and at once for anything the bot wrote). The bot's own
plans are recognised by their event and keep their number, which the move and cancel forms need.
Without Google, or when it does not answer, it is the saved plans, and the page says which of the
three it shows.

Reading only: bringing stored plans up to date is a write, done where the bot acts on a plan
(calendar_sync).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal

from familydb.app import App
from familydb.calendar_sync import event_changes
from familydb.store import plans as plan_store
from familydb.store.plans import Plan

log = logging.getLogger(__name__)

Source = Literal["google", "saved", "unavailable"]


@dataclass(frozen=True)
class Entry:
    title: str
    start: str
    end: str | None
    all_day: bool
    location: str | None
    notes: str | None
    status: str
    plan_id: int | None
    idea_id: int | None

    def days(self) -> list[date]:
        first = date.fromisoformat(self.start[:10])
        if self.end is None:
            return [first]
        if self.all_day:
            last = date.fromisoformat(self.end[:10])
        else:
            ends = datetime.fromisoformat(self.end) - timedelta(minutes=1)
            last = ends.date()
        span = max(0, (last - first).days)
        return [first + timedelta(days=offset) for offset in range(span + 1)]


@dataclass(frozen=True)
class Agenda:
    entries: list[Entry]
    source: Source


def _from_plan(plan: Plan) -> Entry:
    return Entry(
        title=plan.title,
        start=plan.start,
        end=plan.end,
        all_day=plan.all_day,
        location=plan.location,
        notes=plan.notes,
        status=plan.status,
        plan_id=plan.id,
        idea_id=plan.idea_id,
    )


def read(app: App, conn: sqlite3.Connection, first: date, last: date) -> Agenda:
    kept = plan_store.overlapping(conn, str(first), str(last))
    saved = [_from_plan(plan) for plan in kept]
    calendar = app.calendar
    if calendar is None:
        return Agenda(saved, "saved")
    tz = app.clock.tz
    try:
        events = calendar.recent_events(
            datetime.combine(first, time.min, tzinfo=tz),
            datetime.combine(last + timedelta(days=1), time.min, tzinfo=tz),
        )
    except Exception as exc:
        log.warning("the calendar could not be read for the page: %s", exc)
        return Agenda(saved, "unavailable")
    ours = plan_store.by_google_event(conn, app.settings.google_calendar_id)
    entries = []
    for event in events:
        fields = event_changes(event)
        plan = ours.get(event.id)
        entries.append(
            Entry(
                title=fields["title"],
                start=fields["start"],
                end=fields["end"],
                all_day=fields["all_day"],
                location=fields["location"],
                notes=fields["notes"],
                status=fields["status"],
                plan_id=plan.id if plan else None,
                idea_id=plan.idea_id if plan else None,
            )
        )
    # Kept here before Google was connected, and not on it yet (calendar_sync.adopt_local).
    entries += [_from_plan(plan) for plan in kept if plan.calendar_id is None]
    return Agenda(sorted(entries, key=lambda entry: entry.start), "google")


def on(seen: Agenda, day: date) -> list[Entry]:
    """What is on that day, as read."""
    return [entry for entry in seen.entries if day in entry.days()]


def entry_key(entry: Entry, day: date) -> str:
    """Its place in a day's list: all day first, then by time."""
    return "" if entry.all_day or entry.start[:10] < day.isoformat() else entry.start[11:16]


def entry_text(entry: Entry, day: date, *, numbers: bool = True) -> str:
    """One line of a day ("10:00-12:00 Zoo (#4)"), as /today and the morning message say it;
    without `numbers` no idea number (where a kid reads, the numbers being the workings)."""
    title = entry.title + (f" (#{entry.idea_id})" if entry.idea_id and numbers else "")
    if entry.status == "tentative":
        title += ", tentative"
    if entry.all_day:
        return f"All day: {title}"
    started_before = entry.start[:10] < day.isoformat()
    ends_today = entry.end is not None and entry.end[:10] == day.isoformat()
    if started_before:
        return (
            f"until {entry.end[11:16]} {title}" if ends_today and entry.end else f"All day: {title}"
        )
    if ends_today and entry.end:
        return f"{entry.start[11:16]}-{entry.end[11:16]} {title}"
    return f"{entry.start[11:16]} {title}"
