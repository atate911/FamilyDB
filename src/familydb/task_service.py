"""Task rules and atomic writes, shared by model tools and browser forms."""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.errors import ToolError
from familydb.store import members, tasks
from familydb.store.db import transaction


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
) -> dict[str, Any]:
    with transaction(conn):
        previous = conn.execute(
            "SELECT id FROM tasks WHERE operation_key=?", (operation_key,)
        ).fetchone()
        if previous:
            return tasks.get(conn, previous["id"])
        _validate(conn, values)
        cur = conn.execute(
            "INSERT INTO tasks(title,notes,owner_id,due_at,preferred_window,operation_key,"
            "channel,chat_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                values["title"],
                values.get("notes", ""),
                values.get("owner_id"),
                values.get("due_at"),
                values.get("preferred_window", ""),
                operation_key,
                channel,
                chat_id,
                now,
                now,
            ),
        )
        task_id = cur.lastrowid
        if reminder:
            conn.execute(
                "INSERT INTO reminders(task_id,remind_at) VALUES (?,?)", (task_id, reminder)
            )
        return tasks.get(conn, task_id)


def update(
    conn: sqlite3.Connection,
    task_id: int,
    values: dict[str, Any],
    *,
    now: str,
    reminder: str | None = None,
    replace_reminder: bool = False,
    revision: int | None = None,
) -> dict[str, Any]:
    with transaction(conn):
        current = tasks.get(conn, task_id)
        if current is None:
            raise ToolError(f"No task #{task_id}.")
        if revision is not None and revision != current["revision"]:
            raise ToolError("This task changed since you opened it. Reload before editing.")
        _validate(conn, values)
        resulting_status = values.get("status", current["status"])
        if reminder and resulting_status != "open":
            raise ToolError("Reopen the task before setting a reminder.")
        # Refuse cancellation while a send is in flight.
        if conn.execute(
            "SELECT 1 FROM reminders r JOIN messages m ON m.id=r.message_id "
            "WHERE r.task_id=? AND r.cancelled_at IS NULL AND m.claim_until>?",
            (task_id, now),
        ).fetchone():
            raise ToolError("A reminder is being delivered. Try again in a moment.")
        if reminder and current["reminder"] and reminder == current["reminder"]["remind_at"]:
            replace_reminder = False
        if replace_reminder or resulting_status != "open":
            conn.execute(
                "UPDATE messages SET cancelled_at=? WHERE delivered_at IS NULL AND id IN "
                "(SELECT message_id FROM reminders WHERE task_id=? AND cancelled_at IS NULL)",
                (now, task_id),
            )
            conn.execute(
                "UPDATE reminders SET cancelled_at=? WHERE task_id=? AND cancelled_at IS NULL",
                (now, task_id),
            )
            if reminder and resulting_status == "open":
                conn.execute(
                    "INSERT INTO reminders(task_id,remind_at) VALUES (?,?)", (task_id, reminder)
                )
        allowed = {"title", "notes", "owner_id", "due_at", "preferred_window", "status"}
        changes = {key: value for key, value in values.items() if key in allowed}
        changes["updated_at"] = now
        assignment = ", ".join(f"{key}=?" for key in changes)
        conn.execute(
            f"UPDATE tasks SET {assignment}, revision=revision+1 WHERE id=?",
            (*changes.values(), task_id),
        )
        # A queued but unsent reminder should use the current wording.
        latest = tasks.get(conn, task_id)
        conn.execute(
            "UPDATE messages SET text=? WHERE delivered_at IS NULL AND cancelled_at IS NULL "
            "AND id IN (SELECT message_id FROM reminders WHERE task_id=?)",
            (reminder_text(latest), task_id),
        )
        return latest


def reminder_text(task: dict[str, Any]) -> str:
    who = f" ({task['owner']})" if task.get("owner") else ""
    return (
        f"Reminder: {task['title']}{who}  -  task #{task['id']}. "
        "Tell me when it's done or ask to snooze it."
    )
