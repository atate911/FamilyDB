"""What only an admin can fix, while it lasts: a row per trouble kind and subject (kinds and
telling rules: familydb/alerts.py)."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

MAX_DETAIL = 300


class Alert(BaseModel):
    kind: str
    subject: str
    detail: str
    first_at: str
    last_at: str
    times: int
    told_at: str | None = None


def note(
    conn: sqlite3.Connection,
    kind: str,
    subject: str,
    detail: str,
    *,
    now: str,
    keep_after: str,
    once: bool = False,
) -> None:
    """Record that a trouble happened (again); rows not seen since `keep_after` are dropped.
    `once` is for news (a price moved): kept as is if already there, so it is told once."""
    conn.execute("DELETE FROM alerts WHERE last_at < ?", (keep_after,))
    again = (
        "DO NOTHING"
        if once
        else "DO UPDATE SET detail = excluded.detail, last_at = excluded.last_at, times = times + 1"
    )
    conn.execute(
        "INSERT INTO alerts (kind, subject, detail, first_at, last_at) VALUES (?, ?, ?, ?, ?) "
        f"ON CONFLICT (kind, subject) {again}",
        (kind, subject, detail[:MAX_DETAIL], now, now),
    )


def clear(conn: sqlite3.Connection, kind: str, subject: str = "") -> int:
    """It works again: forget the trouble so the next is told at once."""
    return conn.execute(
        "DELETE FROM alerts WHERE kind = ? AND subject = ?", (kind, subject)
    ).rowcount


def times(conn: sqlite3.Connection, kind: str, subject: str) -> int:
    """How often a trouble has been seen while it lasts; 0 when not noted."""
    row = conn.execute(
        "SELECT times FROM alerts WHERE kind = ? AND subject = ?", (kind, subject)
    ).fetchone()
    return int(row["times"]) if row else 0


def any_for(conn: sqlite3.Connection, kinds: tuple[str, ...], subject: str) -> bool:
    marks = ", ".join("?" for _ in kinds)
    row = conn.execute(
        f"SELECT 1 FROM alerts WHERE kind IN ({marks}) AND subject = ? LIMIT 1", (*kinds, subject)
    ).fetchone()
    return row is not None


def due(conn: sqlite3.Connection, *, told_before: str) -> list[Alert]:
    """Troubles untold, or told before `told_before` and seen again since."""
    rows = conn.execute(
        "SELECT * FROM alerts WHERE told_at IS NULL OR (told_at < ? AND last_at > told_at) "
        "ORDER BY first_at",
        (told_before,),
    ).fetchall()
    return [Alert(**dict(row)) for row in rows]


def mark_told(conn: sqlite3.Connection, kind: str, subject: str, *, now: str) -> None:
    conn.execute(
        "UPDATE alerts SET told_at = ? WHERE kind = ? AND subject = ?", (now, kind, subject)
    )


def current(conn: sqlite3.Connection, *, since: str) -> list[Alert]:
    """Every trouble seen since a moment, newest first."""
    rows = conn.execute(
        "SELECT * FROM alerts WHERE last_at >= ? ORDER BY last_at DESC", (since,)
    ).fetchall()
    return [Alert(**dict(row)) for row in rows]
