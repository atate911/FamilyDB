"""Plans: calendar events linked to ideas. Written once the calendar integration lands."""

from __future__ import annotations

import sqlite3
from typing import Literal

from pydantic import BaseModel


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


def get(conn: sqlite3.Connection, plan_id: int) -> Plan | None:
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return Plan.from_row(row) if row else None


def list_between(conn: sqlite3.Connection, start: str, end: str) -> list[Plan]:
    rows = conn.execute(
        "SELECT * FROM plans WHERE status != 'cancelled' AND start >= ? AND start < ? "
        "ORDER BY start",
        (start, end),
    )
    return [Plan.from_row(row) for row in rows]
