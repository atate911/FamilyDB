"""The durable log of calendar events asked of Google: one row per attempt, keyed by intent.

A row holds the event id an attempt will ask Google for, written before Google is contacted, so a
retry after a crash or a lost answer asks for the same event instead of making a second. An
attempt is finished when a plan holds its event id, so nothing else is kept about how it ended.

`resume_key` is the browser session's name for the event it asked for. A form drawn again after
a lost reply has a new identity of its own; if its session left an attempt at that event without
a plan, it takes the attempt over (a row of its own, pointing at the same event id) and so finds
the event Google may already have made.
"""

from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, operation_key: str) -> str | None:
    """The event id this attempt is asking Google for, if it has begun."""
    row = conn.execute(
        "SELECT event_id FROM calendar_creations WHERE operation_key = ?", (operation_key,)
    ).fetchone()
    return row["event_id"] if row else None


def reserve(
    conn: sqlite3.Connection, operation_key: str, event_id: str, *, resume_key: str | None = None
) -> str:
    """Begin an attempt: the event id for this key, which is `event_id` unless one is there."""
    conn.execute(
        "INSERT OR IGNORE INTO calendar_creations(operation_key, event_id, resume_key) "
        "VALUES (?, ?, ?)",
        (operation_key, event_id, resume_key),
    )
    kept = get(conn, operation_key)
    assert kept is not None
    return kept


def unfinished(conn: sqlite3.Connection, resume_key: str) -> str | None:
    """The event id of an attempt this browser session began and that no plan holds yet."""
    row = conn.execute(
        "SELECT c.event_id FROM calendar_creations c "
        "LEFT JOIN plans p ON p.google_event_id = c.event_id "
        "WHERE c.resume_key = ? AND p.id IS NULL",
        (resume_key,),
    ).fetchone()
    return row["event_id"] if row else None
