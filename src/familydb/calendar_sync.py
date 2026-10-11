"""Keep the plans the bot made in step with what Google says about them.

People move and cancel events in Google Calendar without telling the bot, so a plan is checked
against its event before anything acts on it: a moved event moves the plan, a deleted one cancels
it and puts its idea back. One request covers every plan (`sync_plans`).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from familydb import plan_service
from familydb.base.dates import iso_date, iso_datetime
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
    conn: sqlite3.Connection, plan: Plan, event: CalendarEvent | None, now: str, *, tz: ZoneInfo
) -> Plan:
    changes = event_changes(event) if event is not None else {"status": "cancelled"}
    if all(getattr(plan, key) == value for key, value in changes.items()):
        return plan
    with transaction(conn):
        updated = plans.update(conn, plan.id, changes, now=now)
        if updated is not None:
            plan_service.changed(conn, plan, updated, now=now, tz=tz)
        if event is None and plan.idea_id:
            idea = ideas.get(conn, plan.idea_id)
            if idea is not None and idea.status == "planned":
                ideas.update(conn, idea.id, {"status": "idea"}, now=now)
    return updated or plan


def adopt(
    conn: sqlite3.Connection, calendar: CalendarAPI, plan: Plan, calendar_id: str | None, now: str
) -> Plan:
    """Put a plan kept here, while no calendar was connected, on Google. It goes with the id it
    was given when it was made (tools/gcal.py create_event), so doing this twice makes one event:
    the second finds the first."""
    if calendar_id is None:
        return plan
    event_id = plan.google_event_id or None
    event = calendar.get_event(event_id) if event_id else None
    if event is None:
        start, end = _times(plan)
        event = calendar.insert_event(
            title=plan.title,
            start=start,
            end=end,
            all_day=plan.all_day,
            location=plan.location,
            description=plan.notes,
            event_id=event_id,
        )
    with transaction(conn):
        on_google = plans.adopted(
            conn, plan.id, google_event_id=event.id, calendar_id=calendar_id, now=now
        )
    return on_google or plan


def adopt_local(
    conn: sqlite3.Connection, calendar: CalendarAPI, calendar_id: str | None, now: str
) -> int:
    """Every plan still to come that was kept here while no calendar was connected, on Google
    now that one is. Nothing to do costs one query. Returns how many went."""
    if calendar_id is None:
        return 0
    waiting = plans.kept_here(conn, since=now[:10])
    for plan in waiting:
        adopt(conn, calendar, plan, calendar_id, now)
    return len(waiting)


def _times(plan: Plan) -> tuple[datetime | date, datetime | date]:
    """A stored plan's start and end as Google takes them: all-day as dates, the end the day
    after the last (exclusive); timed as the instants stored, in the offset stored with them."""
    if plan.all_day:
        first = date.fromisoformat(plan.start[:10])
        last = date.fromisoformat((plan.end or plan.start)[:10])
        return first, max(first, last) + timedelta(days=1)
    start = datetime.fromisoformat(plan.start)
    end = datetime.fromisoformat(plan.end) if plan.end else start + timedelta(hours=2)
    return start, end


def refresh_plan(
    conn: sqlite3.Connection,
    calendar: CalendarAPI,
    plan: Plan,
    calendar_id: str | None,
    now: str,
    *,
    tz: ZoneInfo,
) -> Plan:
    if not plan.google_event_id or plan.calendar_id != calendar_id:
        return plan
    return apply_event(conn, plan, calendar.get_event(plan.google_event_id), now, tz=tz)


def sync_plans(
    conn: sqlite3.Connection,
    calendar: CalendarAPI,
    calendar_id: str | None,
    now: str,
    *,
    tz: ZoneInfo,
) -> None:
    """Bring every live plan in line with Google in one request.

    Google is asked what changed since last time (`calendar_sync_state` keeps the token):
    nothing, most of the time; the whole calendar the first time or after the token is forgotten.
    The token is kept only after the plans are updated, so a failure reads the same changes
    again, harmlessly.
    """
    if calendar_id is None:
        return
    # Plans kept here before Google was connected go on it first, so Google's answer holds them.
    adopt_local(conn, calendar, calendar_id, now)
    changed = calendar.changes(calendar_sync_state.get(conn, calendar_id))
    live = conn.execute(
        "SELECT * FROM plans WHERE calendar_id = ? AND google_event_id IS NOT NULL "
        "AND status != 'cancelled' AND followed_up_at IS NULL",
        (calendar_id,),
    ).fetchall()
    for row in live:
        plan = Plan.from_row(row)
        if plan.google_event_id in changed.events:
            apply_event(conn, plan, changed.events[plan.google_event_id], now, tz=tz)
        elif changed.full:
            apply_event(conn, plan, None, now, tz=tz)
    with transaction(conn):
        calendar_sync_state.save(conn, calendar_id, changed.token, now=now)
