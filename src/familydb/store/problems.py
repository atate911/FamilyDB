"""The problem log: warnings and errors the program logged, kept for an admin to read
(`problem_log.py` feeds it, the Troubleshooting page reads it). The same trouble again within a
day is one row with a count, so a job failing every minute is one line, not a thousand."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

LEVELS = ("WARNING", "ERROR", "CRITICAL")
# The same trouble within this long is counted, not listed again.
SAME_WITHIN = timedelta(hours=24)
# How many rows to keep, whatever their age, and how long.
MOST_ROWS = 2000
KEEP_DAYS = 30
MESSAGE_CHARS = 600
DETAIL_CHARS = 8000

_NUMBERS = re.compile(r"\d+")


def _stamp(moment: datetime | None) -> str:
    return (moment or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def key_of(level: str, source: str, message: str, detail: str | None) -> str:
    """What makes two troubles the same one: numbers in the words do not (ids, times, counts),
    and a traceback is told by its last line."""
    ending = (detail or "").strip().splitlines()[-1:] or [""]
    text = "|".join((level, source, _NUMBERS.sub("#", message)[:300], _NUMBERS.sub("#", ending[0])))
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def record(
    conn: sqlite3.Connection,
    *,
    level: str,
    source: str,
    message: str,
    detail: str | None = None,
    now: datetime | None = None,
) -> None:
    """Write one trouble down, or count it again if it is the one already listed. Call inside a
    transaction (or alone: it is one statement or two)."""
    message, detail = message[:MESSAGE_CHARS], (detail or None) and detail[-DETAIL_CHARS:]
    stamp = _stamp(now)
    key = key_of(level, source, message, detail)
    again = conn.execute(
        "UPDATE problems SET count = count + 1, last_at = ?, message = ?, detail = ? "
        "WHERE id = (SELECT id FROM problems WHERE key = ? AND last_at >= ? "
        "ORDER BY id DESC LIMIT 1)",
        (stamp, message, detail, key, _stamp((now or datetime.now(UTC)) - SAME_WITHIN)),
    )
    if again.rowcount == 0:
        conn.execute(
            "INSERT INTO problems (key, level, source, message, detail, count, first_at, last_at) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (key, level, source, message, detail, stamp, stamp),
        )


def recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    errors_only: bool = False,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """The troubles most lately seen, newest first."""
    where, args = [], []
    if errors_only:
        where.append("level != 'WARNING'")
    if source:
        where.append("source = ?")
        args.append(source)
    clause = f"WHERE {' AND '.join(where)} " if where else ""
    rows = conn.execute(
        f"SELECT * FROM problems {clause}ORDER BY last_at DESC, id DESC LIMIT ?", (*args, limit)
    ).fetchall()
    return [dict(row) for row in rows]


def counts_since(conn: sqlite3.Connection, *, since: str) -> dict[str, int]:
    """How many times each level was logged since a UTC timestamp."""
    rows = conn.execute(
        "SELECT level, coalesce(sum(count), 0) AS n FROM problems WHERE last_at >= ? "
        "GROUP BY level",
        (since,),
    ).fetchall()
    return {row["level"]: int(row["n"]) for row in rows}


def clear(conn: sqlite3.Connection) -> int:
    return conn.execute("DELETE FROM problems").rowcount


def trim(conn: sqlite3.Connection, *, now: datetime | None = None) -> int:
    """Forget what is old, and the oldest of what is too many."""
    cut = _stamp((now or datetime.now(UTC)) - timedelta(days=KEEP_DAYS))
    gone = conn.execute("DELETE FROM problems WHERE last_at < ?", (cut,)).rowcount
    gone += conn.execute(
        "DELETE FROM problems WHERE id IN (SELECT id FROM problems ORDER BY id DESC "
        "LIMIT -1 OFFSET ?)",
        (MOST_ROWS,),
    ).rowcount
    return gone
