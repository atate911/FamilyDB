"""What follows a plan, kept in step when the plan changes.

A plan changes two ways: through the tools (`update_event`, a cancel) and in Google, when somebody
moves or deletes its event there (`calendar_sync.apply_event`). Both call `changed`, inside the
transaction that stored the change, so what hangs on the plan never lags behind it:

- a plan that moved is checked again the evening before its new day and asked about after it
  (`checked_at`, `followed_up_at`);
- a reminder tied to it ("a week before the concert": a task with `plan_id`, made with the plan's
  `remind_before`) moves with it, worked out again from the new start, and goes when the plan is
  cancelled. Before, it stayed on the old day and went off for a plan nobody was going to.

Such a reminder says when the plan is (`when_words`), and is done once the plan is over
(`finish_over`, from the reminders job): it was a heads-up, not an errand left to tick.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from typing import Literal, get_args
from zoneinfo import ZoneInfo

from familydb.dates import utc_iso
from familydb.errors import ToolError
from familydb.store import ideas, places, plans, tasks
from familydb.store.plans import Plan

RemindBefore = Literal[
    "1 week", "3 days", "1 day", "morning of", "2 hours", "1 hour", "time to leave"
]
REMIND_BEFORE: tuple[str, ...] = get_args(RemindBefore)
# Reminders days ahead come in the morning, at nine; "morning of" at eight.
DAYS_AHEAD = {"1 week": 7, "3 days": 3, "1 day": 1}
DAY_AHEAD_AT = time(9, 0)
MORNING_OF_AT = time(8, 0)
HOURS_AHEAD = {"2 hours": 2, "1 hour": 1}
# Time to leave is the drive (an estimate, places.travel_minutes) and this much to spare.
LEAVE_SPARE = timedelta(minutes=10)


def remind_at(conn: sqlite3.Connection, plan: Plan, word: str, tz: ZoneInfo) -> datetime:
    """When a reminder tied to this plan goes, on the family's clock. A ToolError says why one
    cannot be worked out (an all-day plan has no hour to count back from)."""
    if plan.all_day:
        day, start = date.fromisoformat(plan.start[:10]), None
    else:
        start = datetime.fromisoformat(plan.start).astimezone(tz)
        day = start.date()
    if word in DAYS_AHEAD:
        return datetime.combine(day - timedelta(days=DAYS_AHEAD[word]), DAY_AHEAD_AT, tzinfo=tz)
    if word == "morning of":
        morning = datetime.combine(day, MORNING_OF_AT, tzinfo=tz)
        # A plan before eight is reminded of an hour before instead.
        return morning if start is None or morning < start else start - timedelta(hours=1)
    if start is None:
        raise ToolError(f'"{word}" needs a time; the plan is all day')
    if word in HOURS_AHEAD:
        return start - timedelta(hours=HOURS_AHEAD[word])
    if word == "time to leave":
        travel = _travel_minutes(conn, plan)
        if travel is None:
            raise ToolError('"time to leave" needs a travel time, and none is known for it')
        return start - timedelta(minutes=travel) - LEAVE_SPARE
    raise ToolError(f'"{word}" is not one of {", ".join(REMIND_BEFORE)}')


def when_words(plan: Plan, at: datetime, tz: ZoneInfo) -> str:
    """When a plan is, said from `at`: "today at 19:30", "tomorrow", "on Wed 19 Nov at 19:30"."""
    if plan.all_day:
        day, hour = date.fromisoformat(plan.start[:10]), ""
    else:
        start = datetime.fromisoformat(plan.start).astimezone(tz)
        day, hour = start.date(), f" at {start:%H:%M}"
    today = at.astimezone(tz).date()
    if day == today:
        return f"today{hour}"
    if day == today + timedelta(days=1):
        return f"tomorrow{hour}"
    return f"on {day:%a %d %b}{hour}"


def finish_over(conn: sqlite3.Connection, *, today: str, now: str) -> int:
    """Reminders tied to a plan that is over, done: a plan that ended before `today` (the
    family's date) has nothing left to remind of. Returns how many. Call inside a transaction."""
    return tasks.finish_linked(conn, ended_before=today, now=now)


def _travel_minutes(conn: sqlite3.Connection, plan: Plan) -> int | None:
    idea = ideas.get(conn, plan.idea_id) if plan.idea_id is not None else None
    place = places.get(conn, idea.place_id) if idea is not None and idea.place_id else None
    return place.travel_minutes if place is not None else None


def changed(conn: sqlite3.Connection, before: Plan, after: Plan, *, now: str, tz: ZoneInfo) -> None:
    """Put right what follows a plan that changed from `before` to `after`. Call inside the
    transaction that stored `after`."""
    if after.status == "cancelled":
        if before.status != "cancelled":
            for task in tasks.linked_to(conn, after.id):
                tasks.cancel(conn, task.id, now)
        return
    if after.start == before.start:
        return
    # Checked or asked about for the day it was on: its new day has its own evening before, and
    # its own day after.
    plans.ask_again(conn, after.id)
    moment = datetime.fromisoformat(now)
    for task in tasks.linked_to(conn, after.id):
        if tasks.reminder_in_flight(conn, task.id, now):
            continue  # going out this minute; the next sync puts it right
        try:
            when = remind_at(conn, after, task.plan_remind or "", tz)
        except ToolError:
            when = None
        tasks.cancel_reminders(conn, task.id, now)
        if when is None or when <= moment:
            # Nothing left to remind of before the plan's new time: the reminder has had its day.
            tasks.cancel(conn, task.id, now)
        else:
            tasks.add_reminder(conn, task.id, utc_iso(when))
            tasks.update(conn, task.id, {"updated_at": now})  # and its revision moves on
