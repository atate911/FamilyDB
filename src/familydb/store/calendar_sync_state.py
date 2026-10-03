"""The sync token Google gave for each calendar the last time its changes were read."""

from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, calendar_id: str) -> str | None:
    row = conn.execute(
        "SELECT sync_token FROM calendar_sync_state WHERE calendar_id = ?", (calendar_id,)
    ).fetchone()
    return row["sync_token"] if row else None


def save(conn: sqlite3.Connection, calendar_id: str, token: str, *, now: str) -> None:
    conn.execute(
        "INSERT INTO calendar_sync_state(calendar_id, sync_token, synced_at) VALUES (?, ?, ?) "
        "ON CONFLICT(calendar_id) DO UPDATE SET sync_token = excluded.sync_token, "
        "synced_at = excluded.synced_at",
        (calendar_id, token, now),
    )
