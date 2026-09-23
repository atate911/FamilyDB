"""Outcomes: how a plan or idea went, once it happened."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from familydb.store.db import utcnow_iso


class Outcome(BaseModel):
    id: int
    idea_id: int | None = None
    plan_id: int | None = None
    happened_on: str
    rating: int | None = None
    would_repeat: bool | None = None
    notes: str | None = None
    recorded_by: int | None = None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Outcome:
        return cls(**dict(row))


def insert(
    conn: sqlite3.Connection,
    *,
    idea_id: int | None,
    plan_id: int | None,
    happened_on: str,
    rating: int | None,
    would_repeat: bool | None,
    notes: str | None,
    recorded_by: int | None,
    now: str | None = None,
) -> Outcome:
    cur = conn.execute(
        "INSERT INTO outcomes (idea_id, plan_id, happened_on, rating, would_repeat, notes, "
        "recorded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            idea_id,
            plan_id,
            happened_on,
            rating,
            None if would_repeat is None else int(would_repeat),
            notes,
            recorded_by,
            now or utcnow_iso(),
        ),
    )
    row = conn.execute("SELECT * FROM outcomes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Outcome.from_row(row)


def list_for_idea(conn: sqlite3.Connection, idea_id: int) -> list[Outcome]:
    rows = conn.execute(
        "SELECT * FROM outcomes WHERE idea_id = ? ORDER BY happened_on, id", (idea_id,)
    )
    return [Outcome.from_row(row) for row in rows]


def exists_since(
    conn: sqlite3.Connection, *, idea_id: int | None, plan_id: int | None, since: str
) -> bool:
    """Whether an outcome for this idea or plan was recorded for a date on or after `since`."""
    conditions = []
    params: list[object] = []
    if idea_id is not None:
        conditions.append("idea_id = ?")
        params.append(idea_id)
    if plan_id is not None:
        conditions.append("plan_id = ?")
        params.append(plan_id)
    if not conditions:
        return False
    sql = f"SELECT 1 FROM outcomes WHERE ({' OR '.join(conditions)}) AND happened_on >= ? LIMIT 1"
    params.append(since)
    return conn.execute(sql, params).fetchone() is not None


def average_rating(conn: sqlite3.Connection, idea_id: int) -> float | None:
    row = conn.execute(
        "SELECT AVG(rating) AS avg FROM outcomes WHERE idea_id = ? AND rating IS NOT NULL",
        (idea_id,),
    ).fetchone()
    return float(row["avg"]) if row and row["avg"] is not None else None


def do_not_repeat(conn: sqlite3.Connection) -> set[int]:
    """Latest explicit preference wins; unrated feedback does not erase a preference."""
    rows = conn.execute(
        "SELECT idea_id, would_repeat FROM outcomes "
        "WHERE idea_id IS NOT NULL AND would_repeat IS NOT NULL ORDER BY happened_on, id"
    )
    preferences = {row["idea_id"]: row["would_repeat"] for row in rows}
    return {idea_id for idea_id, repeat in preferences.items() if not repeat}
