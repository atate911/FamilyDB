"""The scheduler's heartbeat: one row, when it last ticked and whether it stopped on purpose."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Beat:
    jobs_at: str
    stopped_at: str | None


def beat(conn: sqlite3.Connection, now: str) -> None:
    """The scheduler is running: now."""
    conn.execute(
        "INSERT INTO heartbeat (id, jobs_at, stopped_at) VALUES (1, ?, NULL) "
        "ON CONFLICT (id) DO UPDATE SET jobs_at = excluded.jobs_at, stopped_at = NULL",
        (now,),
    )


def stopped(conn: sqlite3.Connection, now: str) -> None:
    """It was stopped on purpose, so its silence is not trouble."""
    conn.execute("UPDATE heartbeat SET stopped_at = ? WHERE id = 1", (now,))


def read(conn: sqlite3.Connection) -> Beat | None:
    row = conn.execute("SELECT jobs_at, stopped_at FROM heartbeat WHERE id = 1").fetchone()
    return Beat(row["jobs_at"], row["stopped_at"]) if row else None
