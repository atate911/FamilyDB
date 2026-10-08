"""The morning messages sent (jobs/morning.py): one a day in a chat at most."""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store.db import from_json, to_json


def sent(conn: sqlite3.Connection, channel: str, chat_id: str, day: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM mornings WHERE channel = ? AND chat_id = ? AND day = ?",
        (channel, chat_id, day),
    ).fetchone()
    return row is not None


def record(
    conn: sqlite3.Connection,
    *,
    channel: str,
    chat_id: str,
    day: str,
    message_id: int,
    parts: list[str],
    now: str,
) -> None:
    """This chat had its morning message today. Call inside the transaction that stored it."""
    conn.execute(
        "INSERT INTO mornings (channel, chat_id, day, message_id, parts, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (channel, chat_id, day, message_id, to_json(parts), now),
    )


def part_counts(conn: sqlite3.Connection, *, since: str) -> dict[str, tuple[int, str]]:
    """How many mornings since `since` carried each part, and the last, as "morning:<part>": the
    Messages page counts each part as its own kind of message."""
    counts: dict[str, tuple[int, str]] = {}
    rows = conn.execute(
        "SELECT parts, created_at FROM mornings WHERE created_at >= ? ORDER BY created_at",
        (since,),
    )
    for row in rows:
        parts: Any = from_json(row["parts"], [])
        for part in parts:
            count, _ = counts.get(f"morning:{part}", (0, ""))
            counts[f"morning:{part}"] = (count + 1, row["created_at"])
    return counts
