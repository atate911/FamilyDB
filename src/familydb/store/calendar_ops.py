"""The durable log of calendar events asked of Google: one row per creation, keyed by intent.

`calendar_creations` holds each attempt's event id before Google is contacted and its result
once the plan is saved. `calendar_unfinished` lets the same browser session asking again from a
freshly drawn form take over an attempt whose answer never came back.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel

from familydb.store.db import from_json, to_json


class Creation(BaseModel):
    operation_key: str
    event_id: str
    # The tool result once the plan was saved; None while the attempt is unfinished.
    result: Any = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Creation:
        data = dict(row)
        data["result"] = from_json(data.get("result"))
        return cls(**data)


def get(conn: sqlite3.Connection, operation_key: str) -> Creation | None:
    row = conn.execute(
        "SELECT * FROM calendar_creations WHERE operation_key = ?", (operation_key,)
    ).fetchone()
    return Creation.from_row(row) if row else None


def reserve(conn: sqlite3.Connection, operation_key: str, event_id: str) -> Creation:
    """The creation for this key, recording `event_id` for it unless one is already there."""
    conn.execute(
        "INSERT OR IGNORE INTO calendar_creations(operation_key, event_id) VALUES (?, ?)",
        (operation_key, event_id),
    )
    creation = get(conn, operation_key)
    assert creation is not None
    return creation


def record_result(conn: sqlite3.Connection, operation_key: str, result: Any) -> None:
    conn.execute(
        "UPDATE calendar_creations SET result = ? WHERE operation_key = ?",
        (to_json(result), operation_key),
    )


def unfinished_key(conn: sqlite3.Connection, resume_key: str) -> str | None:
    """The operation key of an unfinished creation this browser session started, if any."""
    row = conn.execute(
        "SELECT c.operation_key FROM calendar_unfinished u "
        "JOIN calendar_creations c ON c.event_id = u.event_id "
        "WHERE u.resume_key = ? AND c.result IS NULL",
        (resume_key,),
    ).fetchone()
    return row["operation_key"] if row else None


def mark_unfinished(conn: sqlite3.Connection, resume_key: str, event_id: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO calendar_unfinished(resume_key, event_id) VALUES (?, ?)",
        (resume_key, event_id),
    )


def clear_unfinished(conn: sqlite3.Connection, resume_key: str) -> None:
    conn.execute("DELETE FROM calendar_unfinished WHERE resume_key = ?", (resume_key,))
