"""Task rules and atomic writes, shared by model tools and browser forms."""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb import voice
from familydb.errors import ToolError
from familydb.store import members, tasks
from familydb.store.db import transaction
from familydb.store.tasks import Task


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


def create(
    conn: sqlite3.Connection,
    values: dict[str, Any],
    *,
    reminder: str | None,
    operation_key: str,
    channel: str,
    chat_id: str,
    now: str,
) -> Task:
    with transaction(conn):
        previous = tasks.find_by_operation(conn, operation_key)
        if previous:
            return previous
        _validate(conn, values)
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
) -> Task:
    with transaction(conn):
        current = tasks.get(conn, task_id)
        if current is None:
            raise ToolError(f"No task #{task_id}.")
        if revision is not None and revision != current.revision:
            raise ToolError("This task changed since you opened it. Reload before editing.")
        _validate(conn, values)
        resulting_status = values.get("status", current.status)
        if reminder and resulting_status != "open":
            raise ToolError("Reopen the task before setting a reminder.")
        # Refuse cancellation while a send is in flight.
        if tasks.reminder_in_flight(conn, task_id, now):
            raise ToolError("A reminder is being delivered. Try again in a moment.")
        if reminder and current.reminder and reminder == current.reminder.remind_at:
            replace_reminder = False
        if replace_reminder or resulting_status != "open":
            tasks.cancel_reminders(conn, task_id, now)
            if reminder and resulting_status == "open":
                tasks.add_reminder(conn, task_id, reminder)
        allowed = {"title", "notes", "owner_id", "due_at", "preferred_window", "status"}
        changes = {key: value for key, value in values.items() if key in allowed}
        changes["updated_at"] = now
        tasks.update(conn, task_id, changes)
        # A queued but unsent reminder should use the current wording.
        latest = _read(conn, task_id)
        if settings is not None:
            tasks.reword_queued(conn, task_id, reminder_text(latest, settings))
        return latest


def _read(conn: sqlite3.Connection, task_id: int) -> Task:
    task = tasks.get(conn, task_id)
    if task is None:
        raise ToolError(f"No task #{task_id}.")
    return task


def reminder_text(task: Task, settings: Any, *, due_when: str | None = None) -> str:
    """The reminder as sent, in the assistant's voice. `due_when` marks one sent late."""
    who = f" ({task.owner})" if task.owner else ""
    facts = {"title": task.title, "who": who, "task": task.id}
    if due_when:
        return voice.say(settings, "reminder_late", due=due_when, **facts)
    return voice.say(settings, "reminder", **facts)
