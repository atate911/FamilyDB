"""What is on, day by day: the family calendar as the Plans page and the home page show it.

With Google Calendar connected this is Google's calendar, read live, so an event somebody added
on their phone is there and a plan somebody moved in Google shows where it is now. The bot's own
plans are recognised by their event and keep their number, which is what the move and cancel
forms need. Without Google, or when it does not answer, it is the plans the bot saved, and the
page says which of the three it is showing rather than letting a stale list pass for the truth.

Reading only. The page does not bring the stored plans up to date on the way past: that is a
write, and it happens where the bot acts on a plan (see calendar_sync).
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
    """One thing on the calendar, from Google or from the bot's own plans."""

    title: str
    start: str  # as plans are stored: a date, or a family-time datetime to the minute
    end: str | None
    all_day: bool
    location: str | None
    notes: str | None
    status: str
    plan_id: int | None  # set when the bot made it, so it can be moved and cancelled here
    idea_id: int | None

    def days(self) -> list[date]:
        """Every day this takes up, first to last. A timed end at midnight is the day before."""
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
    """Everything on from `first` to `last` inclusive, and where it came from."""
    saved = [_from_plan(plan) for plan in plan_store.overlapping(conn, str(first), str(last))]
    calendar = app.calendar
    if calendar is None:
        return Agenda(saved, "saved")
    tz = app.clock.tz
    try:
        events = calendar.list_events(
            datetime.combine(first, time.min, tzinfo=tz),
            datetime.combine(last + timedelta(days=1), time.min, tzinfo=tz),
        )
    except Exception as exc:  # a page must still draw when Google is having a bad day
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
    return Agenda(sorted(entries, key=lambda entry: entry.start), "google")
