"""Plans: calendar events linked to ideas."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.db import utcnow_iso

EDITABLE_FIELDS = frozenset(
    {"title", "start", "end", "all_day", "location", "notes", "status", "google_event_id"}
)


class Plan(BaseModel):
    id: int
    idea_id: int | None = None
    google_event_id: str | None = None
    calendar_id: str | None = None
    title: str
    start: str
    end: str | None = None
    all_day: bool = False
    location: str | None = None
    notes: str | None = None
    status: Literal["confirmed", "tentative", "cancelled"] = "confirmed"
    created_by: int | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Plan:
        return cls(**dict(row))


def insert(
    conn: sqlite3.Connection,
    *,
    title: str,
    start: str,
    end: str | None,
    all_day: bool,
    idea_id: int | None = None,
    google_event_id: str | None = None,
    calendar_id: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    created_by: int | None = None,
    now: str | None = None,
) -> Plan:
    stamp = now or utcnow_iso()
    cur = conn.execute(
        "INSERT INTO plans (idea_id, google_event_id, calendar_id, title, start, end, all_day, "
        "location, notes, status, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?)",
        (
            idea_id,
            google_event_id,
            calendar_id,
            title,
            start,
            end,
            int(all_day),
            location,
            notes,
            created_by,
            stamp,
            stamp,
        ),
    )
    plan = get(conn, int(cur.lastrowid or 0))
    assert plan is not None
    return plan


def update(
    conn: sqlite3.Connection, plan_id: int, changes: dict[str, Any], *, now: str | None = None
) -> Plan | None:
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"unknown plan fields: {sorted(unknown)}")
    data = dict(changes)
    if "all_day" in data and data["all_day"] is not None:
        data["all_day"] = int(bool(data["all_day"]))
    data["updated_at"] = now or utcnow_iso()
    assignments = ", ".join(f"{column} = ?" for column in data)
    conn.execute(f"UPDATE plans SET {assignments} WHERE id = ?", [*data.values(), plan_id])
    return get(conn, plan_id)


def get(conn: sqlite3.Connection, plan_id: int) -> Plan | None:
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return Plan.from_row(row) if row else None


def for_idea(conn: sqlite3.Connection, idea_id: int) -> list[Plan]:
    rows = conn.execute("SELECT * FROM plans WHERE idea_id = ? ORDER BY start", (idea_id,))
    return [Plan.from_row(row) for row in rows]


def list_between(conn: sqlite3.Connection, start: str, end: str) -> list[Plan]:
    rows = conn.execute(
        "SELECT * FROM plans WHERE status != 'cancelled' AND start >= ? AND start < ? "
        "ORDER BY start",
        (start, end),
    )
    return [Plan.from_row(row) for row in rows]
