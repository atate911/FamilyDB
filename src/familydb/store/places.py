"""Places: looked-up facts about where an idea happens, filled in by enrichment."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso

EDITABLE_FIELDS = frozenset(
    {
        "name",
        "summary",
        "address",
        "lat",
        "lon",
        "website",
        "booking_url",
        "phone",
        "hours",
        "price_note",
        "travel_minutes",
        "travel_km",
        "source_urls",
        "last_checked_at",
    }
)


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


def _encode(values: dict[str, Any]) -> dict[str, Any]:
    out = dict(values)
    if "name" in out and out["name"] is not None:
        out["name"] = str(out["name"]).strip()
    if "hours" in out and out["hours"] is not None:
        out["hours"] = to_json(out["hours"])
    if "source_urls" in out and out["source_urls"] is not None:
        out["source_urls"] = to_json(list(out["source_urls"]))
    return out


def get(conn: sqlite3.Connection, place_id: int) -> Place | None:
    row = conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
    return Place.from_row(row) if row else None


def find_by_name(conn: sqlite3.Connection, name: str) -> Place | None:
    row = conn.execute(
        "SELECT * FROM places WHERE lower(name) = lower(?) ORDER BY id LIMIT 1", (name.strip(),)
    ).fetchone()
    return Place.from_row(row) if row else None


def insert(conn: sqlite3.Connection, *, name: str, now: str | None = None, **fields: Any) -> Place:
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"unknown place fields: {sorted(unknown)}")
    stamp = now or utcnow_iso()
    data = _encode({"name": name, **fields})
    if data.get("source_urls") is None:
        data["source_urls"] = "[]"
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


def update(
    conn: sqlite3.Connection, place_id: int, changes: dict[str, Any], *, now: str | None = None
) -> Place | None:
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"unknown place fields: {sorted(unknown)}")
    data = _encode(changes)
    data["updated_at"] = now or utcnow_iso()
    assignments = ", ".join(f"{column} = ?" for column in data)
    conn.execute(f"UPDATE places SET {assignments} WHERE id = ?", [*data.values(), place_id])
    return get(conn, place_id)
