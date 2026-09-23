"""Read household tasks with their current reminder. Mutations live in task_service."""

from __future__ import annotations

import sqlite3
from typing import Any


def get(conn: sqlite3.Connection, task_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT t.*, m.display_name AS owner FROM tasks t "
        "LEFT JOIN members m ON m.id=t.owner_id WHERE t.id=?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    reminder = conn.execute(
        "SELECT r.*, m.delivered_at FROM reminders r LEFT JOIN messages m ON m.id=r.message_id "
        "WHERE r.task_id=? AND r.cancelled_at IS NULL ORDER BY r.id DESC LIMIT 1",
        (task_id,),
    ).fetchone()
    result["reminder"] = dict(reminder) if reminder else None
    result.pop("operation_key")
    return result


def list_all(
    conn: sqlite3.Connection, *, status: str = "open", query: str = "", owner_id: int | None = None
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id FROM tasks WHERE (?='all' OR status=?) "
        "AND (? IS NULL OR owner_id=?) AND (instr(lower(title),lower(?))>0 "
        "OR instr(lower(notes),lower(?))>0) ORDER BY due_at IS NULL, due_at, id LIMIT 100",
        (status, status, owner_id, owner_id, query, query),
    ).fetchall()
    return [get(conn, row["id"]) for row in rows]
