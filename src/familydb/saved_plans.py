"""The family's own plans, read as a calendar, for when no Google calendar is connected.

Without Google the plans are still kept (tools/gcal.py), and they still take time up: the
suggestion engine, the nudges and `get_calendar` read busy time through the same calendar protocol
they read Google through, so a saved plan on Saturday at 10 is as busy as a Google event. Reading
only: plans are written by the tools.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from familydb.integrations.google_calendar import CalendarChanges, CalendarEvent
from familydb.store import plans
from familydb.store.plans import Plan


def as_event(plan: Plan, tz: ZoneInfo) -> CalendarEvent:
    """A saved plan as the event it would be, its id the one it holds for Google."""
    if plan.all_day:
        first = date.fromisoformat(plan.start[:10])
        last = date.fromisoformat((plan.end or plan.start)[:10])
        start: datetime | date = first
        end: datetime | date = max(first, last) + timedelta(days=1)  # exclusive, as Google's
    else:
        start = datetime.fromisoformat(plan.start).astimezone(tz)
        end = (
            datetime.fromisoformat(plan.end).astimezone(tz)
            if plan.end
            else start + timedelta(hours=2)
        )
    return CalendarEvent(
        id=plan.google_event_id or f"plan-{plan.id}",
        title=plan.title,
        start=start,
        end=end,
        all_day=plan.all_day,
        location=plan.location,
        description=plan.notes,
        status=plan.status,
    )


class SavedPlans:
    """The live plans as a read-only calendar (the read half of `CalendarAPI`)."""

    def __init__(self, conn: sqlite3.Connection, tz: ZoneInfo) -> None:
        self.conn = conn
        self.tz = tz

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        first = start.astimezone(self.tz).date()
        last = (end - timedelta(microseconds=1)).astimezone(self.tz).date()
        found = []
        for plan in plans.overlapping(self.conn, first.isoformat(), last.isoformat()):
            event = as_event(plan, self.tz)
            if _overlaps(event, start, end, self.tz):
                found.append(event)
        return found

    def recent_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return self.list_events(start, end)

    def get_event(self, event_id: str) -> CalendarEvent | None:
        plan = plans.for_event(self.conn, event_id)
        return as_event(plan, self.tz) if plan is not None and plan.status != "cancelled" else None

    def changes(self, sync_token: str | None) -> CalendarChanges:
        raise NotImplementedError("saved plans are read, never synced")

    def insert_event(self, **_: Any) -> CalendarEvent:
        raise NotImplementedError("saved plans are written by the tools")

    def patch_event(self, event_id: str, **changes: Any) -> CalendarEvent:
        raise NotImplementedError("saved plans are written by the tools")

    def delete_event(self, event_id: str) -> None:
        raise NotImplementedError("saved plans are written by the tools")


def _overlaps(event: CalendarEvent, start: datetime, end: datetime, tz: ZoneInfo) -> bool:
    if event.all_day:
        assert isinstance(event.start, date) and isinstance(event.end, date)
        begins = datetime.combine(event.start, datetime.min.time(), tzinfo=tz)
        ends = datetime.combine(event.end, datetime.min.time(), tzinfo=tz)
    else:
        assert isinstance(event.start, datetime) and isinstance(event.end, datetime)
        begins, ends = event.start, event.end
    return begins < end and ends > start
