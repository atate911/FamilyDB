"""The durable log of calendar events asked of Google, one row per attempt keyed by intent. The
event id is written before Google is contacted, so a retry after a crash or lost answer asks for
the same event; an attempt is finished when a plan holds its id.

`resume_key` names the event for a browser session: a redrawn form (new identity) whose session
left an unfinished attempt takes it over, pointing at the same event id, and so finds the event
Google may already have made."""

from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, operation_key: str) -> str | None:
    """The event id this attempt asks Google for, if begun."""
    row = conn.execute(
        "SELECT event_id FROM calendar_creations WHERE operation_key = ?", (operation_key,)
    ).fetchone()
    return row["event_id"] if row else None


def reserve(
    conn: sqlite3.Connection, operation_key: str, event_id: str, *, resume_key: str | None = None
) -> str:
    """Begin an attempt: the key's event id (`event_id` unless one is already there)."""
    conn.execute(
        "INSERT OR IGNORE INTO calendar_creations(operation_key, event_id, resume_key) "
        "VALUES (?, ?, ?)",
        (operation_key, event_id, resume_key),
    )
    kept = get(conn, operation_key)
    assert kept is not None
    return kept


def unfinished(conn: sqlite3.Connection, resume_key: str) -> str | None:
    """The event id of this session's attempt that no plan holds yet."""
    row = conn.execute(
        "SELECT c.event_id FROM calendar_creations c "
        "LEFT JOIN plans p ON p.google_event_id = c.event_id "
        "WHERE c.resume_key = ? AND p.id IS NULL",
        (resume_key,),
    ).fetchone()
    return row["event_id"] if row else None
