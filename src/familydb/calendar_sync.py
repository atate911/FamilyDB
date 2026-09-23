"""Keep the plans the bot made in step with what Google now says about them.

People move and cancel events in Google Calendar itself, on their phones, without telling the
bot. So a plan is checked against its event before anything acts on it — moving it, asking how
it went, listing it for the model — and brought up to date: a moved event moves the plan, and a
deleted one cancels it and puts its idea back on the list.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from familydb.dates import iso_date, iso_datetime
from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent
from familydb.store import ideas, plans
from familydb.store.db import transaction
from familydb.store.plans import Plan


def event_changes(event: CalendarEvent) -> dict[str, Any]:
    """The plan fields an event decides, spelled the way plans are stored.

    The spelling matters. A timed plan is stored to the minute with its offset, and an all-day
    plan with the last day it covers, where Google's all-day end is the day after. Any other
    spelling of the same instant compares as a change, and every read of the calendar would then
    rewrite every plan on it.
    """
    if event.all_day:
        first = event.start if not isinstance(event.start, datetime) else event.start.date()
        after = event.end if not isinstance(event.end, datetime) else event.end.date()
        start, end = iso_date(first), iso_date(max(first, after - timedelta(days=1)))
    else:
        start, end = iso_datetime(event.start), iso_datetime(event.end)  # type: ignore[arg-type]
    return {
        "title": event.title,
        "start": start,
        "end": end,
        "all_day": event.all_day,
        "location": event.location,
        "notes": event.description,
        "status": event.status if event.status in {"confirmed", "tentative"} else "confirmed",
    }


def refresh_plan(
    conn: sqlite3.Connection, calendar: CalendarAPI, plan: Plan, calendar_id: str | None, now: str
) -> Plan:
    """The plan as its event now stands, stored if anything moved. One call to Google."""
    if not plan.google_event_id or plan.calendar_id != calendar_id:
        return plan
    event = calendar.get_event(plan.google_event_id)
    changes = event_changes(event) if event is not None else {"status": "cancelled"}
    if all(getattr(plan, key) == value for key, value in changes.items()):
        return plan
    with transaction(conn):
        updated = plans.update(conn, plan.id, changes, now=now)
        if event is None and plan.idea_id:
            idea = ideas.get(conn, plan.idea_id)
            if idea is not None and idea.status == "planned":
                ideas.update(conn, idea.id, {"status": "idea"}, now=now)
    return updated or plan


def sync_plans(
    conn: sqlite3.Connection,
    calendar: CalendarAPI,
    calendar_id: str | None,
    now: str,
    *,
    first: date | None = None,
    last: date | None = None,
) -> None:
    """Refresh every live plan on this calendar, or only those starting from `first` to `last`.

    One call to Google per plan, so a caller that only cares about some days says which: the
    model reading one weekend should not wait on every plan the family has made.
    """
    sql = (
        "SELECT * FROM plans WHERE calendar_id = ? AND google_event_id IS NOT NULL "
        "AND status != 'cancelled' AND followed_up_at IS NULL"
    )
    params: list[Any] = [calendar_id]
    if first is not None:
        sql += " AND start >= ?"
        params.append(first.isoformat())
    if last is not None:
        # A date sorts before that day's timed plans, so the bound is the day after.
        sql += " AND start < ?"
        params.append((last + timedelta(days=1)).isoformat())
    for row in conn.execute(sql, params).fetchall():
        refresh_plan(conn, calendar, Plan.from_row(row), calendar_id, now)
