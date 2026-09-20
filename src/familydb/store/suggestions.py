"""Suggestions log: what was proposed, with the verdict on every candidate."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso


class Suggestion(BaseModel):
    id: int
    asked_by: int | None = None
    asked_at: str
    window_start: str | None = None
    window_end: str | None = None
    candidates: list[dict[str, Any]] = []
    web_finds: list[dict[str, Any]] = []
    reply_message_id: int | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Suggestion:
        data = dict(row)
        data["candidates"] = from_json(data.get("candidates"), [])
        data["web_finds"] = from_json(data.get("web_finds"), [])
        return cls(**data)


def insert(
    conn: sqlite3.Connection,
    *,
    asked_by: int | None,
    window_start: str | None,
    window_end: str | None,
    candidates: list[dict[str, Any]],
    web_finds: list[dict[str, Any]],
    reply_message_id: int | None = None,
    now: str | None = None,
) -> Suggestion:
    cur = conn.execute(
        "INSERT INTO suggestions (asked_by, asked_at, window_start, window_end, candidates, "
        "web_finds, reply_message_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            asked_by,
            now or utcnow_iso(),
            window_start,
            window_end,
            to_json(candidates),
            to_json(web_finds),
            reply_message_id,
        ),
    )
    row = conn.execute("SELECT * FROM suggestions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Suggestion.from_row(row)


def get(conn: sqlite3.Connection, suggestion_id: int) -> Suggestion | None:
    row = conn.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)).fetchone()
    return Suggestion.from_row(row) if row else None
