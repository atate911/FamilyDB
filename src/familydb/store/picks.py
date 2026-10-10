"""Her picks for a moment: the "What about…" set on Now (familydb/picks.py makes them, the page
reads them). One row a set; the newest for a window and a person is the one in force."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.db import from_json, to_json

Window = Literal["now", "weekend"]
WINDOWS: tuple[Window, ...] = ("now", "weekend")


class PickSet(BaseModel):
    id: int
    member_id: int | None = None
    window: Window
    window_start: str
    window_end: str
    header: str | None = None
    picks: list[dict[str, Any]] = []
    made_at: str
    stale_at: str
    source: str = "code"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> PickSet:
        data = dict(row)
        data["picks"] = from_json(data.get("picks"), [])
        return cls(**data)


def insert(
    conn: sqlite3.Connection,
    *,
    member_id: int | None,
    window: Window,
    window_start: str,
    window_end: str,
    header: str | None,
    picks: list[dict[str, Any]],
    made_at: str,
    stale_at: str,
    source: str = "code",
) -> PickSet:
    cur = conn.execute(
        "INSERT INTO pick_sets (member_id, window, window_start, window_end, header, picks, "
        "made_at, stale_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            member_id,
            window,
            window_start,
            window_end,
            header,
            to_json(picks),
            made_at,
            stale_at,
            source,
        ),
    )
    row = conn.execute("SELECT * FROM pick_sets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return PickSet.from_row(row)


def latest(
    conn: sqlite3.Connection, *, window: Window, member_id: int | None = None
) -> PickSet | None:
    """The newest set for a window and a person (the family's when None), stale or not."""
    row = conn.execute(
        "SELECT * FROM pick_sets WHERE window = ? AND member_id IS ? "
        "ORDER BY made_at DESC, id DESC LIMIT 1",
        (window, member_id),
    ).fetchone()
    return PickSet.from_row(row) if row else None


def current(
    conn: sqlite3.Connection, *, member_id: int | None = None, today: str | None = None
) -> PickSet | None:
    """What Now shows: the newest set for this person whose days are not over, the nearer window
    first. A kid with no set of her own sees none (hers are made for her)."""
    for window in WINDOWS:
        found = latest(conn, window=window, member_id=member_id)
        if found is not None and (today is None or found.window_end >= today):
            return found
    return None


def prune(conn: sqlite3.Connection, *, before: str) -> int:
    """Drop sets made before `before`, keeping the newest of each window and person."""
    cur = conn.execute(
        "DELETE FROM pick_sets WHERE made_at < ? AND id NOT IN (SELECT max(id) FROM pick_sets "
        "GROUP BY member_id, window)",
        (before,),
    )
    return cur.rowcount
