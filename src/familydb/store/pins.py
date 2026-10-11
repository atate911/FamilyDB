"""Her replies each person keeps at hand (docs/INTERFACE.md section 8), written only through
familydb/family.py's `pin` and `unpin`."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

# A shelf holds this many; pinning another lets the oldest go.
MOST = 8


class Pin(BaseModel):
    message_id: int
    text: str
    said_at: str
    pinned_at: str


def pin(conn: sqlite3.Connection, member_id: int, message_id: int, *, now: str) -> None:
    """Keep this reply at hand for this person; pinned again, it is where it was. Call inside a
    transaction."""
    conn.execute(
        "INSERT OR IGNORE INTO pins (member_id, message_id, pinned_at) VALUES (?, ?, ?)",
        (member_id, message_id, now),
    )


def keep_newest(conn: sqlite3.Connection, member_id: int, most: int) -> int:
    """Let the oldest go past `most`. Call inside a transaction."""
    return conn.execute(
        "DELETE FROM pins WHERE member_id = ? AND id NOT IN (SELECT id FROM pins "
        "WHERE member_id = ? ORDER BY pinned_at DESC, id DESC LIMIT ?)",
        (member_id, member_id, most),
    ).rowcount


def unpin(conn: sqlite3.Connection, member_id: int, message_id: int) -> int:
    """Call inside a transaction."""
    return conn.execute(
        "DELETE FROM pins WHERE member_id = ? AND message_id = ?", (member_id, message_id)
    ).rowcount


def for_member(conn: sqlite3.Connection, member_id: int, *, limit: int) -> list[Pin]:
    """This person's, newest first; none whose words were let go."""
    rows = conn.execute(
        "SELECT p.message_id, m.text, m.received_at AS said_at, p.pinned_at FROM pins p "
        "JOIN messages m ON m.id = p.message_id WHERE p.member_id = ? "
        "AND trim(coalesce(m.text, '')) != '' ORDER BY p.pinned_at DESC, p.id DESC LIMIT ?",
        (member_id, limit),
    )
    return [Pin(**dict(row)) for row in rows]
