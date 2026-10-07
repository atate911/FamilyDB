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
    # What the stronger call chose (suggest/choosing.py): {"picks": [...], "framing": ...}.
    picks: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Suggestion:
        data = dict(row)
        data["candidates"] = from_json(data.get("candidates"), [])
        data["web_finds"] = from_json(data.get("web_finds"), [])
        data["picks"] = from_json(data.get("picks"))
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


def set_reply(conn: sqlite3.Connection, suggestion_id: int, message_id: int) -> None:
    conn.execute(
        "UPDATE suggestions SET reply_message_id = ? WHERE id = ?", (message_id, suggestion_id)
    )


def set_picks(conn: sqlite3.Connection, suggestion_id: int, picks: dict[str, Any]) -> None:
    """Keep what was chosen for a suggestion. Call inside a transaction."""
    conn.execute("UPDATE suggestions SET picks = ? WHERE id = ?", (to_json(picks), suggestion_id))


def picked_since(conn: sqlite3.Connection, *, since: str) -> list[Suggestion]:
    """Suggestions made at or after `since` that a choice was made for, newest first."""
    rows = conn.execute(
        "SELECT * FROM suggestions WHERE picks IS NOT NULL AND asked_at >= ? ORDER BY id DESC",
        (since,),
    ).fetchall()
    return [Suggestion.from_row(row) for row in rows]


def list_recent(conn: sqlite3.Connection, *, limit: int = 10) -> list[Suggestion]:
    rows = conn.execute("SELECT * FROM suggestions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [Suggestion.from_row(row) for row in rows]


def recently_suggested(conn: sqlite3.Connection, *, since: str) -> set[int]:
    """Idea ids shown as 'good' in any suggestion since `since`. Every verdict is logged, shown or
    not; one logged before that was recorded counts as shown."""
    rows = conn.execute("SELECT candidates FROM suggestions WHERE asked_at >= ?", (since,))
    ids: set[int] = set()
    for row in rows:
        for candidate in from_json(row["candidates"], []) or []:
            if (
                isinstance(candidate, dict)
                and candidate.get("verdict") == "good"
                and candidate.get("shown", True)
            ):
                idea_id = candidate.get("idea_id")
                if isinstance(idea_id, int):
                    ids.add(idea_id)
    return ids
