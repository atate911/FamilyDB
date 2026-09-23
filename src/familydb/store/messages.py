"""The message log: every inbound message and every reply, with what happened."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso

# What the Ideas page's "save a thought" box puts before the words, so the model knows to save
# them. It is an instruction, not what anybody said, so `as_said` takes it off again.
CAPTURE_PREFIX = "Save this idea for later:\n"


def as_said(text: str) -> str:
    """A stored message's words as the family typed them."""
    return text.removeprefix(CAPTURE_PREFIX)


class Message(BaseModel):
    id: int
    channel: str
    channel_update_id: str | None = None
    chat_id: str
    member_id: int | None = None
    direction: Literal["in", "out"]
    text: str
    received_at: str
    status: Literal["received", "processed", "failed"] = "received"
    actions: Any = None
    error: str | None = None
    reply_to: int | None = None
    processed_at: str | None = None
    retries: int = 0
    give_up: bool = False
    claim_token: str | None = None
    claim_until: str | None = None
    delivered_at: str | None = None
    cancelled_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Message:
        data = dict(row)
        data["actions"] = from_json(data.get("actions"))
        return cls(**data)


def exists_update(conn: sqlite3.Connection, channel: str, channel_update_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM messages WHERE channel = ? AND channel_update_id = ?",
        (channel, channel_update_id),
    ).fetchone()
    return row is not None


def insert_in(
    conn: sqlite3.Connection,
    *,
    channel: str,
    channel_update_id: str | None,
    chat_id: str,
    member_id: int | None,
    text: str,
    now: str | None = None,
) -> Message:
    cur = conn.execute(
        "INSERT INTO messages (channel, channel_update_id, chat_id, member_id, direction, text, "
        "received_at, status) VALUES (?, ?, ?, ?, 'in', ?, ?, 'received')",
        (channel, channel_update_id, chat_id, member_id, text, now or utcnow_iso()),
    )
    message = get(conn, int(cur.lastrowid or 0))
    assert message is not None
    return message


def insert_out(
    conn: sqlite3.Connection,
    *,
    channel: str,
    chat_id: str,
    text: str,
    reply_to: int | None = None,
    now: str | None = None,
) -> Message:
    stamp = now or utcnow_iso()
    cur = conn.execute(
        "INSERT INTO messages (channel, chat_id, direction, text, received_at, status, reply_to, "
        "processed_at) VALUES (?, ?, 'out', ?, ?, 'processed', ?, ?)",
        (channel, chat_id, text, stamp, reply_to, stamp),
    )
    message = get(conn, int(cur.lastrowid or 0))
    assert message is not None
    return message


def mark_processed(
    conn: sqlite3.Connection, message_id: int, actions: Any, *, now: str | None = None
) -> None:
    conn.execute(
        "UPDATE messages SET status = 'processed', actions = ?, error = NULL, processed_at = ? "
        "WHERE id = ?",
        (to_json(actions), now or utcnow_iso(), message_id),
    )


def mark_failed(
    conn: sqlite3.Connection, message_id: int, error: str, *, now: str | None = None
) -> None:
    conn.execute(
        "UPDATE messages SET status = 'failed', error = ?, processed_at = ? WHERE id = ?",
        (error[:2000], now or utcnow_iso(), message_id),
    )


def get(conn: sqlite3.Connection, message_id: int) -> Message | None:
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return Message.from_row(row) if row else None


def recent_for_chat(
    conn: sqlite3.Connection, chat_id: str, *, limit: int, since: str
) -> list[Message]:
    """The last `limit` messages in a chat received at or after `since`, oldest first."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_id = ? AND cancelled_at IS NULL "
        "AND received_at >= ? ORDER BY id DESC LIMIT ?",
        (chat_id, since, limit),
    ).fetchall()
    return [Message.from_row(row) for row in reversed(rows)]


def claimed_in_chat(conn: sqlite3.Connection, chat_id: str, *, now: str) -> bool:
    """Whether some worker holds a live claim on a message in this chat: a turn is running."""
    row = conn.execute(
        "SELECT 1 FROM messages WHERE chat_id = ? AND direction = 'in' AND claim_until > ? LIMIT 1",
        (chat_id, now),
    ).fetchone()
    return row is not None


def member_is_being_answered(conn: sqlite3.Connection, member_id: int, *, now: str) -> bool:
    """Whether a worker holds a live claim on one of this member's messages."""
    row = conn.execute(
        "SELECT 1 FROM messages WHERE member_id = ? AND direction = 'in' AND claim_until > ? "
        "LIMIT 1",
        (member_id, now),
    ).fetchone()
    return row is not None


def give_up_for_member(conn: sqlite3.Connection, member_id: int, *, now: str) -> int:
    """Stop the retry job answering anything this member left unanswered. Returns how many."""
    cur = conn.execute(
        "UPDATE messages SET status = 'failed', error = 'member_inactive', processed_at = ?, "
        "give_up = 1 WHERE member_id = ? AND direction = 'in' "
        "AND status IN ('received', 'failed') AND give_up = 0",
        (now, member_id),
    )
    return int(cur.rowcount)


def last_for_chat(conn: sqlite3.Connection, chat_id: str, *, limit: int) -> list[Message]:
    """The last `limit` messages in a chat, however old, oldest first.

    What the page shows. The agent's own view of a chat is `recent_for_chat`, which also draws a
    line under anything said long enough ago that the model should not be reading it again.
    """
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_id = ? AND cancelled_at IS NULL "
        "ORDER BY id DESC LIMIT ?",
        (chat_id, limit),
    ).fetchall()
    return [Message.from_row(row) for row in reversed(rows)]


def failed(conn: sqlite3.Connection, *, max_retries: int | None = None) -> list[Message]:
    """Failed inbound messages, oldest first, optionally only those still eligible for a retry."""
    sql = "SELECT * FROM messages WHERE status = 'failed' AND direction = 'in'"
    params: list[Any] = []
    if max_retries is not None:
        sql += " AND retries < ? AND give_up = 0"
        params.append(max_retries)
    rows = conn.execute(sql + " ORDER BY id", params)
    return [Message.from_row(row) for row in rows]


def pending(conn: sqlite3.Connection, *, max_retries: int, now: str) -> list[Message]:
    rows = conn.execute(
        "SELECT * FROM messages WHERE direction = 'in' AND status IN ('received', 'failed') "
        "AND give_up = 0 AND retries < ? AND (claim_until IS NULL OR claim_until <= ?) ORDER BY id",
        (max_retries, now),
    )
    return [Message.from_row(row) for row in rows]


def recent_failures(conn: sqlite3.Connection, *, limit: int = 10) -> list[Message]:
    """Inbound messages that did not go through, newest first, whether or not they are done with."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE direction = 'in' AND status = 'failed' "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [Message.from_row(row) for row in rows]


def claim_retry(conn: sqlite3.Connection, message_id: int, retries: int) -> bool:
    """Take the next attempt at a failed message, if nobody else has it.

    The running bot's retry job and `familydb db retry-failed` can both be looking at the same
    row. Reading it and then bumping the count in a second statement would let both of them pay
    for a model call and send the family two answers, so the bump is the claim: whoever changes
    the row from the count they read wins, and the other is told to leave it alone.
    """
    changed = conn.execute(
        "UPDATE messages SET retries = retries + 1 "
        "WHERE id = ? AND direction = 'in' AND status = 'failed' AND give_up = 0 AND retries = ?",
        (message_id, retries),
    )
    return changed.rowcount == 1


def give_up(conn: sqlite3.Connection, message_id: int) -> None:
    """Stop the retry job from picking a message up, e.g. after a configuration error."""
    conn.execute("UPDATE messages SET give_up = 1 WHERE id = ?", (message_id,))


def reset_retries(conn: sqlite3.Connection) -> int:
    """Make every failed message eligible again (after fixing a configuration problem)."""
    cur = conn.execute(
        "UPDATE messages SET retries = 0, give_up = 0 WHERE status = 'failed' AND direction = 'in'"
    )
    return int(cur.rowcount)


def chats(conn: sqlite3.Connection, channel: str) -> list[dict[str, str]]:
    """Each chat on a channel the family has written in, with when it was last written in."""
    rows = conn.execute(
        "SELECT chat_id, max(received_at) AS last_at FROM messages "
        "WHERE channel = ? AND direction = 'in' GROUP BY chat_id ORDER BY last_at DESC",
        (channel,),
    ).fetchall()
    return [{"chat_id": row["chat_id"], "last_at": row["last_at"]} for row in rows]
