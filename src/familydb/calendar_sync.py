"""Keep the plans the bot made in step with what Google says about them.

People move and cancel events in Google Calendar without telling the bot, so a plan is checked
against its event before anything acts on it: a moved event moves the plan, a deleted one cancels
it and puts its idea back. One request covers every plan (`sync_plans`).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from familydb.dates import iso_date, iso_datetime
from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent
from familydb.store import calendar_sync_state, ideas, plans
from familydb.store.db import transaction
from familydb.store.plans import Plan


def event_changes(event: CalendarEvent) -> dict[str, Any]:
    """The plan fields an event decides, spelled as plans are stored.

    The spelling matters: a timed plan is stored to the minute with its offset, an all-day plan
    with the last day it covers (Google's all-day end is the day after). Any other spelling of
    the same instant compares as a change and every read of the calendar would rewrite every
    plan.
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


def apply_event(
    conn: sqlite3.Connection, plan: Plan, event: CalendarEvent | None, now: str
) -> Plan:
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


def refresh_plan(
    conn: sqlite3.Connection, calendar: CalendarAPI, plan: Plan, calendar_id: str | None, now: str
) -> Plan:
    if not plan.google_event_id or plan.calendar_id != calendar_id:
        return plan
    return apply_event(conn, plan, calendar.get_event(plan.google_event_id), now)


def sync_plans(
    conn: sqlite3.Connection, calendar: CalendarAPI, calendar_id: str | None, now: str
) -> None:
    """Bring every live plan in line with Google in one request.

    Google is asked what changed since last time (`calendar_sync_state` keeps the token):
    nothing, most of the time; the whole calendar the first time or after the token is forgotten.
    The token is kept only after the plans are updated, so a failure reads the same changes
    again, harmlessly.
    """
    if calendar_id is None:
        return
    changed = calendar.changes(calendar_sync_state.get(conn, calendar_id))
    live = conn.execute(
        "SELECT * FROM plans WHERE calendar_id = ? AND google_event_id IS NOT NULL "
        "AND status != 'cancelled' AND followed_up_at IS NULL",
        (calendar_id,),
    ).fetchall()
    for row in live:
        plan = Plan.from_row(row)
        if plan.google_event_id in changed.events:
            apply_event(conn, plan, changed.events[plan.google_event_id], now)
        elif changed.full:
            apply_event(conn, plan, None, now)
    with transaction(conn):
        calendar_sync_state.save(conn, calendar_id, changed.token, now=now)
