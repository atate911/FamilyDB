"""Task rules and atomic writes, shared by model tools and browser forms.

A task can come round again: every so many days, weeks, months or years, either on a schedule
("bins out every Sunday at 19:00", counted from its first reminder) or counted from when it was
last done ("the dentist six months after the last visit"). Done on a repeating task records this
time round rather than ending it; cancelling ends it. A scheduled one's next reminder is added as
each is sent (`schedule_next`), and one counted from done gets its next when it is done. Times go
on in the family's wall time, from the first one, so a reminder keeps its hour when the clocks
change and one on the 31st stays on the last day of a shorter month, rather than drifting.
"""

from __future__ import annotations

import sqlite3
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any

from familydb import voice
from familydb.dates import utc_iso
from familydb.errors import ToolError
from familydb.store import members, messages, tasks
from familydb.store.db import transaction
from familydb.store.tasks import Task

# A reminder queued later than this after its time says when it was due.
LATE_AFTER = timedelta(minutes=10)
UNITS = ("day", "week", "month", "year")
FROM = ("schedule", "done")
# Far enough for "every 18 months" or "every 52 weeks"; further is a slip of the tongue.
MOST_EVERY = 400
NEEDS_FIRST = "A repeating task needs the time of its first reminder."


def _validate(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    if "title" in values:
        values["title"] = values["title"].strip()
        if not values["title"] or len(values["title"]) > 200:
            raise ToolError("Give the task a title of 1 to 200 characters.")
    for key in ("notes", "preferred_window"):
        if key in values and len(values[key]) > 4000:
            raise ToolError(f"{key} must be at most 4000 characters.")
    if values.get("owner_id") is not None:
        owner = members.get(conn, values["owner_id"])
        if owner is None or not owner.active:
            raise ToolError("Choose an active family member.")


def _validate_repeat(repeat: dict[str, Any]) -> None:
    every, unit = repeat.get("repeat_every"), repeat.get("repeat_unit")
    if every is None or unit is None:
        raise ToolError("Say how often it repeats: repeat_every and repeat_unit together.")
    if not 1 <= every <= MOST_EVERY:
        raise ToolError(f"repeat_every must be between 1 and {MOST_EVERY}.")
    if unit not in UNITS or repeat.get("repeat_from", "schedule") not in FROM:
        raise ToolError("Repeat by day, week, month or year, from the schedule or when done.")


def create(
    conn: sqlite3.Connection,
    values: dict[str, Any],
    *,
    reminder: str | None,
    operation_key: str,
    channel: str,
    chat_id: str,
    now: str,
    repeat: dict[str, Any] | None = None,
) -> Task:
    """A new task. `repeat` (repeat_every, repeat_unit, repeat_from) makes it come round again,
    counted from its first reminder, which it then needs."""
    with transaction(conn):
        previous = tasks.find_by_operation(conn, operation_key)
        if previous:
            return previous
        _validate(conn, values)
        columns = None
        if repeat is not None:
            _validate_repeat(repeat)
            if not reminder:
                raise ToolError(NEEDS_FIRST)
            columns = _repeat_columns(repeat, anchor=reminder)
        task_id = tasks.insert(
            conn,
            title=values["title"],
            notes=values.get("notes", ""),
            owner_id=values.get("owner_id"),
            due_at=values.get("due_at"),
            preferred_window=values.get("preferred_window", ""),
            operation_key=operation_key,
            channel=channel,
            chat_id=chat_id,
            now=now,
            repeat=columns,
        )
        if reminder:
            tasks.add_reminder(conn, task_id, reminder)
        return _read(conn, task_id)


def update(
    conn: sqlite3.Connection,
    task_id: int,
    values: dict[str, Any],
    *,
    now: str,
    reminder: str | None = None,
    replace_reminder: bool = False,
    revision: int | None = None,
    settings: Any = None,
    repeat: dict[str, Any] | None = None,
    stop_repeating: bool = False,
) -> Task:
    """Change a task. `repeat` sets how it comes round again, from `reminder` if one is given,
    else from its reminder now; `stop_repeating` makes it a one-off. A plain new `reminder` on a
    repeating task is a snooze of this time round, and leaves its schedule where it was."""
    zone = settings.tzinfo if settings is not None else UTC
    with transaction(conn):
        current = tasks.get(conn, task_id)
        if current is None:
            raise ToolError(f"No task #{task_id}.")
        if revision is not None and revision != current.revision:
            raise ToolError("This task changed since you opened it. Reload before editing.")
        _validate(conn, values)
        columns: dict[str, Any] = {}
        if stop_repeating:
            columns = dict.fromkeys(("repeat_every", "repeat_unit", "repeat_from"), None)
            columns["repeat_anchor"] = None
        elif repeat is not None:
            _validate_repeat(repeat)
            anchor = reminder or (current.reminder.remind_at if current.reminder else None)
            if anchor is None:
                raise ToolError(NEEDS_FIRST)
            columns = _repeat_columns(repeat, anchor=anchor)
        rule = None if stop_repeating else (columns or _rule_of(current))
        # Done with this time round, not with the task: recorded, and it comes round again.
        round_done = values.get("status") == "done" and rule is not None
        if round_done:
            values = {**values, "status": "open"}
        resulting_status = values.get("status", current.status)
        if reminder and resulting_status != "open":
            raise ToolError("Reopen the task before setting a reminder.")
        # Refuse cancellation while a send is in flight.
        if tasks.reminder_in_flight(conn, task_id, now):
            raise ToolError("A reminder is being delivered. Try again in a moment.")
        if reminder and current.reminder and reminder == current.reminder.remind_at:
            replace_reminder = False
        if round_done and not reminder and rule is not None and rule["repeat_from"] == "done":
            # Counted from now: the next time round replaces whatever was waiting.
            reminder = utc_iso(_after_done(rule, datetime.fromisoformat(now), zone))
            replace_reminder = True
        if replace_reminder or resulting_status != "open":
            tasks.cancel_reminders(conn, task_id, now)
            if reminder and resulting_status == "open":
                tasks.add_reminder(conn, task_id, reminder)
        if round_done and rule is not None and rule["repeat_from"] == "schedule":
            # On a schedule it keeps going; one paused with nothing waiting starts again.
            _add_next(conn, task_id, rule, after=datetime.fromisoformat(now), zone=zone)
        allowed = {"title", "notes", "owner_id", "due_at", "preferred_window", "status"}
        changes = {key: value for key, value in values.items() if key in allowed}
        changes.update(columns)
        if round_done:
            changes["last_done_at"] = now
        changes["updated_at"] = now
        tasks.update(conn, task_id, changes)
        # A queued but unsent reminder should use the current wording.
        latest = _read(conn, task_id)
        if settings is not None:
            # One queued late keeps saying when it was due.
            due_when = None
            reminder = latest.reminder
            if reminder and reminder.message_id:
                message = messages.get(conn, reminder.message_id)
                if message:
                    due_when = late_note(reminder.remind_at, message.received_at, settings.tzinfo)
            tasks.reword_queued(conn, task_id, reminder_text(latest, settings, due_when=due_when))
        return latest


def schedule_next(conn: sqlite3.Connection, task: Task, *, after: datetime, zone: tzinfo) -> None:
    """After one of a scheduled task's reminders is sent: the next time round, if none waits.

    From the first one, not the last, so a snooze or a stretch with the bot off never moves the
    schedule, and missed times are not sent in a flood: the next is the first after `after`.
    Inside the caller's transaction."""
    rule = _rule_of(task)
    if rule is not None and rule["repeat_from"] == "schedule" and task.status == "open":
        _add_next(conn, task.id, rule, after=after, zone=zone)


def _add_next(
    conn: sqlite3.Connection, task_id: int, rule: dict[str, Any], *, after: datetime, zone: tzinfo
) -> None:
    if tasks.has_pending_reminder(conn, task_id):
        return
    anchor = datetime.fromisoformat(rule["repeat_anchor"]).astimezone(zone)
    moment = next_time(anchor, rule["repeat_every"], rule["repeat_unit"], after)
    tasks.add_reminder(conn, task_id, utc_iso(moment))


def _rule_of(task: Task) -> dict[str, Any] | None:
    if not task.repeats:
        return None
    return {
        "repeat_every": task.repeat_every,
        "repeat_unit": task.repeat_unit,
        "repeat_from": task.repeat_from or "schedule",
        "repeat_anchor": task.repeat_anchor,
    }


def _repeat_columns(repeat: dict[str, Any], *, anchor: str) -> dict[str, Any]:
    return {
        "repeat_every": repeat["repeat_every"],
        "repeat_unit": repeat["repeat_unit"],
        "repeat_from": repeat.get("repeat_from") or "schedule",
        "repeat_anchor": anchor,
    }


def shifted(day: date, count: int, unit: str) -> date:
    """A day moved on `count` units; a month or year from the 31st, or 29 February, lands on the
    last day there is."""
    if unit == "day":
        return day + timedelta(days=count)
    if unit == "week":
        return day + timedelta(weeks=count)
    months = count * (12 if unit == "year" else 1)
    year, month = divmod(day.month - 1 + months, 12)
    year, month = day.year + year, month + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def next_time(anchor: datetime, every: int, unit: str, after: datetime) -> datetime:
    """The first time a schedule comes round after `after`: the first one (`anchor`, in the
    family's time) moved on whole intervals, at its own hour on the wall."""
    if anchor > after:
        return anchor
    step = every if unit in ("day", "week") else every * (12 if unit == "year" else 1)
    if unit == "day":
        passed = (after.date() - anchor.date()).days
    elif unit == "week":
        passed = (after.date() - anchor.date()).days // 7
    else:
        passed = (after.year - anchor.year) * 12 + after.month - anchor.month
    rounds = max(1, passed // step)  # a short way before the answer, never past it
    while True:
        day = shifted(anchor.date(), rounds * every, unit)
        moment = datetime.combine(day, anchor.timetz().replace(tzinfo=None), tzinfo=anchor.tzinfo)
        if moment > after:
            return moment
        rounds += 1


def _after_done(rule: dict[str, Any], done: datetime, zone: tzinfo) -> datetime:
    """The next time round of a task counted from when it was done: that many units on from
    the day it was done, at the hour of its first reminder."""
    first = datetime.fromisoformat(rule["repeat_anchor"]).astimezone(zone)
    day = shifted(done.astimezone(zone).date(), rule["repeat_every"], rule["repeat_unit"])
    return datetime.combine(day, first.timetz().replace(tzinfo=None), tzinfo=zone)


def repeat_words(task: Task) -> str | None:
    """How often a task comes round, briefly: "every week", "every 6 months after done"."""
    if not task.repeats:
        return None
    unit = (
        task.repeat_unit if task.repeat_every == 1 else f"{task.repeat_every} {task.repeat_unit}s"
    )
    after = " after done" if task.repeat_from == "done" else ""
    return f"every {unit}{after}"


def _read(conn: sqlite3.Connection, task_id: int) -> Task:
    task = tasks.get(conn, task_id)
    if task is None:
        raise ToolError(f"No task #{task_id}.")
    return task


def late_note(remind_at: str, queued_at: str, tz: tzinfo) -> str | None:
    """When a reminder queued at `queued_at` was due, if that was over LATE_AFTER before."""
    due = datetime.fromisoformat(remind_at)
    if datetime.fromisoformat(queued_at) - due <= LATE_AFTER:
        return None
    return due.astimezone(tz).strftime("%a %d %b at %H:%M")


def reminder_text(task: Task, settings: Any, *, due_when: str | None = None) -> str:
    """The reminder as sent, in the assistant's voice. `due_when` marks one sent late."""
    who = f" ({task.owner})" if task.owner else ""
    facts = {"title": task.title, "who": who, "task": task.id}
    # Each time it is due is its own message, by the reminder in force: a snoozed reminder may
    # take another of her wordings, and the same one worded again (a changed title) the same.
    seed = f"{task.id}:{task.reminder.id if task.reminder else ''}"
    if due_when:
        return voice.say(settings, "reminder_late", seed=seed, due=due_when, **facts)
    return voice.say(settings, "reminder", seed=seed, **facts)
