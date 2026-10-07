"""The backups written (`familydb db backup`), and whether each copy was sound."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Kept a year: enough to see a habit, and a nightly row costs nothing.
KEEP_ROWS = 400


@dataclass(frozen=True)
class Backup:
    path: str
    bytes: int
    ok: bool
    detail: str | None
    made_at: str


def record(
    conn: sqlite3.Connection, *, path: str, size: int, ok: bool, detail: str | None, now: str
) -> None:
    conn.execute(
        "INSERT INTO backups (path, bytes, ok, detail, made_at) VALUES (?, ?, ?, ?, ?)",
        (path, size, int(ok), detail, now),
    )
    conn.execute(
        "DELETE FROM backups WHERE id NOT IN (SELECT id FROM backups ORDER BY id DESC LIMIT ?)",
        (KEEP_ROWS,),
    )


def latest(conn: sqlite3.Connection, *, good: bool = False) -> Backup | None:
    """The newest backup, or the newest that was sound."""
    row = conn.execute(
        "SELECT path, bytes, ok, detail, made_at FROM backups "
        f"{'WHERE ok = 1 ' if good else ''}ORDER BY made_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return Backup(row["path"], row["bytes"], bool(row["ok"]), row["detail"], row["made_at"])
