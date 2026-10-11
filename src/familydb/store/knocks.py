"""Strangers who messaged the bot: who and when, never what they said. Kept a month and at most
`KEEP`, so strangers cannot fill the disk."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from pydantic import BaseModel

from familydb.base.dates import utc_iso

KEEP = 200
KEEP_DAYS = 30
MAX_NAME = 80


class Knock(BaseModel):
    channel: str
    channel_user_id: str
    name: str | None = None
    chat_id: str | None = None
    first_at: str
    last_at: str
    times: int


def record(
    conn: sqlite3.Connection,
    *,
    channel: str,
    channel_user_id: str,
    name: str | None,
    chat_id: str | None,
    now: datetime,
) -> None:
    stamp = utc_iso(now)
    conn.execute(
        "INSERT INTO knocks (channel, channel_user_id, name, chat_id, first_at, last_at) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (channel, channel_user_id) DO UPDATE SET "
        "name = coalesce(excluded.name, knocks.name), chat_id = excluded.chat_id, "
        "last_at = excluded.last_at, times = knocks.times + 1",
        (channel, channel_user_id, (name or "")[:MAX_NAME] or None, chat_id, stamp, stamp),
    )
    forget_old(conn, now)


def forget_old(conn: sqlite3.Connection, now: datetime) -> int:
    """Drop knocks past `KEEP_DAYS` and any beyond the newest `KEEP`; returns how many."""
    old = conn.execute(
        "DELETE FROM knocks WHERE last_at < ?", (utc_iso(now - timedelta(KEEP_DAYS)),)
    ).rowcount
    extra = conn.execute(
        "DELETE FROM knocks WHERE rowid NOT IN "
        "(SELECT rowid FROM knocks ORDER BY last_at DESC LIMIT ?)",
        (KEEP,),
    ).rowcount
    return old + extra


def recent(conn: sqlite3.Connection, *, channel: str, limit: int = 20) -> list[Knock]:
    """Newest first, excluding anybody since put on the family list."""
    rows = conn.execute(
        "SELECT k.* FROM knocks k WHERE k.channel = ? AND NOT EXISTS ("
        "SELECT 1 FROM members m WHERE m.channel = k.channel "
        "AND m.channel_user_id = k.channel_user_id) ORDER BY k.last_at DESC LIMIT ?",
        (channel, limit),
    ).fetchall()
    return [Knock(**dict(row)) for row in rows]
