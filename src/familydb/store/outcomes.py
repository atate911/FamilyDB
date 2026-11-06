"""Outcomes: how a plan or idea went, once it happened."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

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
    message_id: int | None = None,
    now: str | None = None,
) -> Outcome:
    cur = conn.execute(
        "INSERT INTO outcomes (idea_id, plan_id, happened_on, rating, would_repeat, notes, "
        "recorded_by, message_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            idea_id,
            plan_id,
            happened_on,
            rating,
            None if would_repeat is None else int(would_repeat),
            notes,
            recorded_by,
            message_id,
            now or utcnow_iso(),
        ),
    )
    row = conn.execute("SELECT * FROM outcomes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Outcome.from_row(row)


def for_message(
    conn: sqlite3.Connection, message_id: int, *, idea_id: int, happened_on: str
) -> Outcome | None:
    """The outcome already recorded for this message, idea and day: what a turn answered again
    after a failure finds, so the visit is counted once however the call names it, by its plan
    or its idea (tools/outcomes.py). Another day, or another idea, is another visit."""
    row = conn.execute(
        "SELECT * FROM outcomes WHERE message_id = ? AND idea_id = ? AND happened_on = ? "
        "ORDER BY id LIMIT 1",
        (message_id, idea_id, happened_on),
    ).fetchone()
    return Outcome.from_row(row) if row else None


def list_for_idea(conn: sqlite3.Connection, idea_id: int) -> list[Outcome]:
    rows = conn.execute(
        "SELECT * FROM outcomes WHERE idea_id = ? ORDER BY happened_on, id", (idea_id,)
    )
    return [Outcome.from_row(row) for row in rows]


def exists_since(
    conn: sqlite3.Connection, *, idea_id: int | None, plan_id: int | None, since: str
) -> bool:
    """Whether an outcome for this idea or plan is dated on or after `since`."""
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


def latest_preferences(conn: sqlite3.Connection) -> dict[int, bool]:
    """Each idea's latest explicit word on doing it again; feedback without one keeps it. A
    "would not" given before the idea was put back (Again?, Bring it back: `ideas.reconsidered_at`)
    is no word at all; one given after it stands again."""
    rows = conn.execute(
        "SELECT o.idea_id, o.would_repeat, o.created_at, i.reconsidered_at FROM outcomes o "
        "JOIN ideas i ON i.id = o.idea_id "
        "WHERE o.would_repeat IS NOT NULL ORDER BY o.happened_on, o.id"
    )
    latest = {row["idea_id"]: row for row in rows}
    return {
        idea_id: bool(row["would_repeat"])
        for idea_id, row in latest.items()
        if row["would_repeat"]
        or not row["reconsidered_at"]
        or row["created_at"] >= row["reconsidered_at"]
    }


def do_not_repeat(conn: sqlite3.Connection) -> set[int]:
    """Ideas whose latest explicit preference is not to repeat; unrated feedback keeps it."""
    return {idea_id for idea_id, again in latest_preferences(conn).items() if not again}


def recent_ratings(conn: sqlite3.Connection, *, since: str, last: int = 2) -> dict[int, list[int]]:
    """Each idea's latest ratings on or after `since` (YYYY-MM-DD), newest first, at most `last`."""
    rows = conn.execute(
        "SELECT idea_id, rating FROM outcomes "
        "WHERE idea_id IS NOT NULL AND rating IS NOT NULL AND happened_on >= ? "
        "ORDER BY happened_on DESC, id DESC",
        (since,),
    )
    kept: dict[int, list[int]] = {}
    for row in rows:
        mine = kept.setdefault(row["idea_id"], [])
        if len(mine) < last:
            mine.append(row["rating"])
    return kept


def get(conn: sqlite3.Connection, outcome_id: int) -> Outcome | None:
    """One outing as it was recorded, for its own page."""
    row = conn.execute("SELECT * FROM outcomes WHERE id = ?", (outcome_id,)).fetchone()
    return Outcome.from_row(row) if row else None


def recent(conn: sqlite3.Connection, *, since: str) -> list[Outcome]:
    """Every outcome for a day on or after `since` (YYYY-MM-DD), the latest first."""
    rows = conn.execute(
        "SELECT * FROM outcomes WHERE happened_on >= ? ORDER BY happened_on DESC, id DESC",
        (since,),
    )
    return [Outcome.from_row(row) for row in rows]


def latest_for(conn: sqlite3.Connection, idea_ids: Iterable[int]) -> dict[int, Outcome]:
    """The latest outcome of each of these ideas that has one."""
    wanted = sorted(set(idea_ids))
    if not wanted:
        return {}
    marks = ", ".join("?" for _ in wanted)
    rows = conn.execute(
        f"SELECT * FROM outcomes WHERE idea_id IN ({marks}) ORDER BY happened_on, id", wanted
    )
    return {row["idea_id"]: Outcome.from_row(row) for row in rows}
