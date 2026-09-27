"""What the daily check of models and prices found (familydb/model_watch.py): the models, what
changed, and how each source answered. Three small tables, read and written together by one job,
so one repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel


class Seen(BaseModel):
    provider: str
    model: str
    listed: bool | None = None
    tools: bool | None = None
    input: float | None = None
    output: float | None = None
    cached: float | None = None
    priced_by: str | None = None
    retires_on: str | None = None
    released: str | None = None
    first_seen: str
    last_seen: str | None


class Change(BaseModel):
    id: int
    provider: str
    model: str
    what: str
    before: str | None = None
    after: str | None = None
    at: str


class Source(BaseModel):
    source: str
    checked_at: str
    ok: bool
    note: str = ""
    failures: int = 0


def all_seen(conn: sqlite3.Connection) -> dict[tuple[str, str], Seen]:
    rows = conn.execute("SELECT * FROM models").fetchall()
    return {(row["provider"], row["model"]): Seen(**dict(row)) for row in rows}


def save(conn: sqlite3.Connection, seen: Seen) -> None:
    """Keep one model as found. Call inside a transaction."""
    data = seen.model_dump()
    columns = list(data)
    conn.execute(
        f"INSERT INTO models ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)}) "
        "ON CONFLICT (provider, model) DO UPDATE SET "
        + ", ".join(
            f"{column} = excluded.{column}" for column in columns if column != "first_seen"
        ),
        [_stored(data[column]) for column in columns],
    )


def _stored(value: Any) -> Any:
    return int(value) if isinstance(value, bool) else value


def record_change(
    conn: sqlite3.Connection,
    provider: str,
    model: str,
    what: str,
    *,
    before: str | None,
    after: str | None,
    at: str,
) -> None:
    conn.execute(
        "INSERT INTO model_changes (provider, model, what, before, after, at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (provider, model, what, before, after, at),
    )


def changes_since(conn: sqlite3.Connection, *, since: str, limit: int = 50) -> list[Change]:
    rows = conn.execute(
        "SELECT * FROM model_changes WHERE at >= ? ORDER BY id DESC LIMIT ?", (since, limit)
    ).fetchall()
    return [Change(**dict(row)) for row in rows]


def source_answered(conn: sqlite3.Connection, source: str, *, ok: bool, note: str, at: str) -> int:
    """Record how a source answered; returns how many checks in a row it has now failed."""
    conn.execute(
        "INSERT INTO model_sources (source, checked_at, ok, note, failures) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT (source) DO UPDATE SET "
        "checked_at = excluded.checked_at, ok = excluded.ok, note = excluded.note, "
        "failures = CASE WHEN excluded.ok THEN 0 ELSE model_sources.failures + 1 END",
        (source, at, int(ok), note[:300], 0 if ok else 1),
    )
    row = conn.execute("SELECT failures FROM model_sources WHERE source = ?", (source,)).fetchone()
    return int(row["failures"])


def sources(conn: sqlite3.Connection) -> list[Source]:
    rows = conn.execute("SELECT * FROM model_sources ORDER BY source").fetchall()
    return [Source(**dict(row)) for row in rows]


def stamp(conn: sqlite3.Connection) -> str | None:
    """When the check last ran, so a process knows to load what it found."""
    row = conn.execute("SELECT max(checked_at) AS at FROM model_sources").fetchone()
    return row["at"] if row else None
