"""Reconcile bot-owned plans with their current Google Calendar events."""

from __future__ import annotations

from datetime import timedelta

from familydb.store import ideas, plans
from familydb.store.db import transaction


def event_changes(event):
    end = event.end - timedelta(days=1) if event.all_day else event.end
    return {
        "title": event.title,
        "start": event.start.isoformat(),
        "end": end.isoformat(),
        "all_day": event.all_day,
        "location": event.location,
        "notes": event.description,
        "status": event.status if event.status in {"confirmed", "tentative"} else "confirmed",
    }


def refresh_plan(conn, calendar, plan, calendar_id, now):
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
    return updated


def sync_plans(conn, calendar, calendar_id, now):
    rows = conn.execute(
        "SELECT * FROM plans WHERE calendar_id = ? AND google_event_id IS NOT NULL "
        "AND status != 'cancelled' AND followed_up_at IS NULL",
        (calendar_id,),
    ).fetchall()
    for row in rows:
        refresh_plan(conn, calendar, plans.Plan.from_row(row), calendar_id, now)
