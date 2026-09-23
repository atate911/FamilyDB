"""Household tasks with their current reminder. The rules for changing them live in task_service."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from pydantic import BaseModel


class Reminder(BaseModel):
    id: int
    task_id: int
    remind_at: str
    message_id: int | None = None
    cancelled_at: str | None = None
    # When the message carrying it was delivered, from the message log.
    delivered_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Reminder:
        return cls(**dict(row))


class Task(BaseModel):
    id: int
    title: str
    notes: str = ""
    owner_id: int | None = None
    # The owner's display name, from the family list.
    owner: str | None = None
    due_at: str | None = None
    preferred_window: str = ""
    status: Literal["open", "done", "cancelled"] = "open"
    revision: int = 1
    channel: str
    chat_id: str
    created_at: str
    updated_at: str
    reminder: Reminder | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row, reminder: Reminder | None) -> Task:
        data = dict(row)
        # The idempotency key is how a write finds itself again, not part of the task.
        data.pop("operation_key", None)
        return cls(**data, reminder=reminder)


def get(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute(
        "SELECT t.*, m.display_name AS owner FROM tasks t "
        "LEFT JOIN members m ON m.id=t.owner_id WHERE t.id=?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    reminder = conn.execute(
        "SELECT r.*, m.delivered_at FROM reminders r LEFT JOIN messages m ON m.id=r.message_id "
        "WHERE r.task_id=? AND r.cancelled_at IS NULL ORDER BY r.id DESC LIMIT 1",
        (task_id,),
    ).fetchone()
    return Task.from_row(row, Reminder.from_row(reminder) if reminder else None)


def list_all(
    conn: sqlite3.Connection, *, status: str = "open", query: str = "", owner_id: int | None = None
) -> list[Task]:
    rows = conn.execute(
        "SELECT id FROM tasks WHERE (?='all' OR status=?) "
        "AND (? IS NULL OR owner_id=?) AND (instr(lower(title),lower(?))>0 "
        "OR instr(lower(notes),lower(?))>0) ORDER BY due_at IS NULL, due_at, id LIMIT 100",
        (status, status, owner_id, owner_id, query, query),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def find_by_operation(conn: sqlite3.Connection, operation_key: str) -> Task | None:
    """The task an earlier attempt at the same request already saved, if any."""
    row = conn.execute("SELECT id FROM tasks WHERE operation_key=?", (operation_key,)).fetchone()
    return get(conn, row["id"]) if row else None


def insert(
    conn: sqlite3.Connection,
    *,
    title: str,
    notes: str,
    owner_id: int | None,
    due_at: str | None,
    preferred_window: str,
    operation_key: str,
    channel: str,
    chat_id: str,
    now: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO tasks(title,notes,owner_id,due_at,preferred_window,operation_key,"
        "channel,chat_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            title,
            notes,
            owner_id,
            due_at,
            preferred_window,
            operation_key,
            channel,
            chat_id,
            now,
            now,
        ),
    )
    return int(cur.lastrowid or 0)


def update(conn: sqlite3.Connection, task_id: int, changes: dict[str, Any]) -> None:
    """Set the given columns and move the revision on. Callers pass only editable columns."""
    assignment = ", ".join(f"{key}=?" for key in changes)
    conn.execute(
        f"UPDATE tasks SET {assignment}, revision=revision+1 WHERE id=?",
        (*changes.values(), task_id),
    )


def add_reminder(conn: sqlite3.Connection, task_id: int, remind_at: str) -> None:
    conn.execute("INSERT INTO reminders(task_id,remind_at) VALUES (?,?)", (task_id, remind_at))


def reminder_in_flight(conn: sqlite3.Connection, task_id: int, now: str) -> bool:
    """Whether a live reminder's message is claimed for sending right now."""
    row = conn.execute(
        "SELECT 1 FROM reminders r JOIN messages m ON m.id=r.message_id "
        "WHERE r.task_id=? AND r.cancelled_at IS NULL AND m.claim_until>?",
        (task_id, now),
    ).fetchone()
    return row is not None


def cancel_reminders(conn: sqlite3.Connection, task_id: int, now: str) -> None:
    """Cancel a task's live reminders and any of their messages not yet delivered."""
    conn.execute(
        "UPDATE messages SET cancelled_at=? WHERE delivered_at IS NULL AND id IN "
        "(SELECT message_id FROM reminders WHERE task_id=? AND cancelled_at IS NULL)",
        (now, task_id),
    )
    conn.execute(
        "UPDATE reminders SET cancelled_at=? WHERE task_id=? AND cancelled_at IS NULL",
        (now, task_id),
    )


def reword_queued(conn: sqlite3.Connection, task_id: int, text: str) -> None:
    """Give a queued but unsent reminder message for this task new words."""
    conn.execute(
        "UPDATE messages SET text=? WHERE delivered_at IS NULL AND cancelled_at IS NULL "
        "AND id IN (SELECT message_id FROM reminders WHERE task_id=?)",
        (text, task_id),
    )


def due_reminders(conn: sqlite3.Connection, now: str, *, limit: int = 100) -> list[Reminder]:
    """Live reminders of open tasks whose time has come and that have no message yet."""
    rows = conn.execute(
        "SELECT r.id,r.task_id,r.remind_at FROM reminders r JOIN tasks t ON t.id=r.task_id "
        "WHERE r.cancelled_at IS NULL AND r.message_id IS NULL AND r.remind_at<=? "
        "AND t.status='open' ORDER BY r.remind_at LIMIT ?",
        (now, limit),
    ).fetchall()
    return [Reminder.from_row(row) for row in rows]


def attach_message(conn: sqlite3.Connection, reminder_id: int, message_id: int) -> None:
    conn.execute("UPDATE reminders SET message_id=? WHERE id=?", (message_id, reminder_id))
