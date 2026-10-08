"""The words of every model call, kept for a while so an admin can read what a model was sent and
what it said, and why a call failed. Private words from every chat: only the Troubleshooting
pages read it (admins), `keep_ai_text_days` says how long it is kept (0 keeps none), and the tidy
job lets go of it.

The system prompt and the tool list repeat from one call to the next, so each is kept once as a
blob and a call points at it."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

# One part of a request or reply is cut at this many characters, and the whole at the second.
PART_CHARS = 20_000
CALL_CHARS = 150_000
CUT = "\n[… cut: too long to keep …]"


def cut(text: str, room: int = PART_CHARS) -> str:
    return text if len(text) <= room else text[:room] + CUT


def _stamp(moment: datetime | None) -> str:
    return (moment or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def keep_blob(conn: sqlite3.Connection, text: str, *, now: datetime | None = None) -> str:
    """Keep a text that repeats between calls, once; returns its hash."""
    digest = hashlib.sha256(text.encode()).hexdigest()[:24]
    conn.execute(
        "INSERT OR IGNORE INTO ai_blobs (hash, text, created_at) VALUES (?, ?, ?)",
        (digest, text, _stamp(now)),
    )
    return digest


def record(
    conn: sqlite3.Connection,
    *,
    call_id: int | None,
    message_id: int | None,
    turn: str | None,
    iteration: int,
    kind: str | None,
    about: str | None,
    provider: str | None,
    model: str,
    error: str | None,
    system: str | None,
    tools: str | None,
    request: str,
    reply: str,
    now: datetime | None = None,
) -> int:
    """Keep one call's words: `error` set means the call failed and `reply` is what is known of
    it. Call inside a transaction."""
    system_hash = keep_blob(conn, system, now=now) if system else None
    tools_hash = keep_blob(conn, tools, now=now) if tools else None
    cur = conn.execute(
        "INSERT INTO ai_texts (call_id, message_id, turn, iteration, kind, about, provider, model, "
        "outcome, error, system_hash, tools_hash, request, reply, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            call_id,
            message_id,
            turn,
            iteration,
            kind,
            about,
            provider,
            model,
            "failed" if error else "answered",
            error,
            system_hash,
            tools_hash,
            cut(request, CALL_CHARS),
            cut(reply, CALL_CHARS),
            _stamp(now),
        ),
    )
    return int(cur.lastrowid or 0)


def recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    failed_only: bool = False,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    """The newest calls, without their words (the list)."""
    where, args = [], []
    if failed_only:
        where.append("outcome = 'failed'")
    if kind:
        where.append("kind = ?")
        args.append(kind)
    clause = f"WHERE {' AND '.join(where)} " if where else ""
    rows = conn.execute(
        "SELECT id, call_id, message_id, turn, iteration, kind, about, provider, model, outcome, "
        "error, length(request) AS request_chars, length(reply) AS reply_chars, created_at "
        f"FROM ai_texts {clause}ORDER BY id DESC LIMIT ?",
        (*args, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, text_id: int) -> dict[str, Any] | None:
    """One call's words in full, with its system prompt and tool list."""
    row = conn.execute(
        "SELECT t.*, s.text AS system, d.text AS tools FROM ai_texts t "
        "LEFT JOIN ai_blobs s ON s.hash = t.system_hash "
        "LEFT JOIN ai_blobs d ON d.hash = t.tools_hash WHERE t.id = ?",
        (text_id,),
    ).fetchone()
    return dict(row) if row else None


def for_call(conn: sqlite3.Connection, call_id: int) -> int | None:
    row = conn.execute("SELECT id FROM ai_texts WHERE call_id = ?", (call_id,)).fetchone()
    return int(row["id"]) if row else None


def for_calls(conn: sqlite3.Connection, call_ids: list[int]) -> dict[int, int]:
    """By model call, the id of its kept words, for those that have them."""
    if not call_ids:
        return {}
    marks = ",".join("?" * len(call_ids))
    rows = conn.execute(
        f"SELECT call_id, id FROM ai_texts WHERE call_id IN ({marks})", call_ids
    ).fetchall()
    return {int(row["call_id"]): int(row["id"]) for row in rows}


def failed_in(
    conn: sqlite3.Connection, *, message_id: int | None = None, turn: str | None = None
) -> list[dict[str, Any]]:
    """The calls of a message or turn that did not get an answer, oldest first."""
    column, value = ("message_id", message_id) if message_id is not None else ("turn", turn)
    rows = conn.execute(
        f"SELECT id, kind, provider, model, error, created_at FROM ai_texts "
        f"WHERE outcome = 'failed' AND {column} = ? ORDER BY id",
        (value,),
    ).fetchall()
    return [dict(row) for row in rows]


def failures_since(conn: sqlite3.Connection, *, since: str) -> int:
    row = conn.execute(
        "SELECT count(*) AS n FROM ai_texts WHERE outcome = 'failed' AND created_at >= ?",
        (since,),
    ).fetchone()
    return int(row["n"])


def sizes(conn: sqlite3.Connection) -> dict[str, int]:
    """How much is kept: calls, and characters."""
    row = conn.execute(
        "SELECT count(*) AS calls, coalesce(sum(length(request) + length(reply)), 0) AS chars "
        "FROM ai_texts"
    ).fetchone()
    shared = conn.execute("SELECT coalesce(sum(length(text)), 0) AS chars FROM ai_blobs").fetchone()
    return {"calls": int(row["calls"]), "chars": int(row["chars"]) + int(shared["chars"])}


def forget_before(conn: sqlite3.Connection, before: str) -> int:
    """Let go of the words kept before a UTC timestamp, and of any blob nothing points at now.
    Call inside a transaction."""
    gone = conn.execute("DELETE FROM ai_texts WHERE created_at < ?", (before,)).rowcount
    conn.execute(
        "DELETE FROM ai_blobs WHERE hash NOT IN (SELECT system_hash FROM ai_texts "
        "WHERE system_hash IS NOT NULL UNION SELECT tools_hash FROM ai_texts "
        "WHERE tools_hash IS NOT NULL)"
    )
    return gone


def forget_all(conn: sqlite3.Connection) -> int:
    gone = conn.execute("DELETE FROM ai_texts").rowcount
    conn.execute("DELETE FROM ai_blobs")
    return gone


def forget_of_messages(conn: sqlite3.Connection, member_id: int) -> int:
    """Let go of the words of the calls made for somebody's messages (taking them off for good:
    the prompts carry their name). Call inside a transaction."""
    return conn.execute(
        "DELETE FROM ai_texts WHERE message_id IN (SELECT id FROM messages WHERE member_id = ?)",
        (member_id,),
    ).rowcount


def cutoff(days: int, *, now: datetime | None = None) -> str:
    return _stamp((now or datetime.now(UTC)) - timedelta(days=days))
