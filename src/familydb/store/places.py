"""Places: looked-up facts about where an idea happens. Filled by enrichment (later milestone)."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso


class Place(BaseModel):
    id: int
    name: str
    summary: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    website: str | None = None
    booking_url: str | None = None
    phone: str | None = None
    hours: dict[str, Any] | None = None
    price_note: str | None = None
    travel_minutes: int | None = None
    travel_km: float | None = None
    source_urls: list[str] = []
    last_checked_at: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Place:
        data = dict(row)
        data["hours"] = from_json(data.get("hours"))
        data["source_urls"] = from_json(data.get("source_urls"), [])
        return cls(**data)


def get(conn: sqlite3.Connection, place_id: int) -> Place | None:
    row = conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
    return Place.from_row(row) if row else None


def insert(conn: sqlite3.Connection, *, name: str, now: str | None = None, **fields: Any) -> Place:
    stamp = now or utcnow_iso()
    data: dict[str, Any] = {"name": name.strip(), **fields}
    if data.get("hours") is not None:
        data["hours"] = to_json(data["hours"])
    data["source_urls"] = to_json(list(data.get("source_urls") or []))
    data["created_at"] = stamp
    data["updated_at"] = stamp
    columns = list(data)
    cur = conn.execute(
        f"INSERT INTO places ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        [data[column] for column in columns],
    )
    place = get(conn, int(cur.lastrowid or 0))
    assert place is not None
    return place
