"""Members' last shared locations: one row each, replaced by the next share."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel


class SharedLocation(BaseModel):
    member_id: int
    lat: float
    lon: float
    live: bool
    shared_at: str


def get(conn: sqlite3.Connection, member_id: int) -> SharedLocation | None:
    row = conn.execute(
        "SELECT * FROM member_locations WHERE member_id = ?", (member_id,)
    ).fetchone()
    return SharedLocation(**dict(row)) if row else None


def record(
    conn: sqlite3.Connection, member_id: int, *, lat: float, lon: float, live: bool, now: str
) -> None:
    conn.execute(
        "INSERT INTO member_locations (member_id, lat, lon, live, shared_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(member_id) DO UPDATE SET "
        "lat = excluded.lat, lon = excluded.lon, live = excluded.live, "
        "shared_at = excluded.shared_at",
        (member_id, lat, lon, int(live), now),
    )


def forget_before(conn: sqlite3.Connection, before: str) -> int:
    return conn.execute("DELETE FROM member_locations WHERE shared_at < ?", (before,)).rowcount
