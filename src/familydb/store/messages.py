"""The message log: every inbound message and every reply, with what happened."""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso

# The Ideas page's "save a thought" box puts this before the words; it is an instruction, not
# what anybody said, so `as_said` takes it off again.
CAPTURE_PREFIX = "Save this idea for later:\n"
# Marks that say how a message arrived, so the model, history and page know it was not typed.
# A voice note keeps its heard words after VOICE_PREFIX (UNHEARD, with its length, until then).
VOICE_PREFIX = "(voice note) "
UNHEARD = "(voice note, {length}, not heard)"
# A tapped button is kept as a message from whoever tapped it (familydb/buttons.py).
TAP_PREFIX = "(tapped) "
# Words that came with something nobody could look at (a video, a file).
UNSEEN = "(with {what}, not seen) "
# A photo is kept as what a model saw in it (the picture is not kept); an album's photos each
# under their number.
PHOTO_PREFIX = "(photo) "
UNLOOKED = "(photo, not looked at)"
UNLOOKED_ALBUM = "({count} photos, not looked at)"
UNLOOKED_FORM = re.compile(r"\((?:photo|\d+ photos), not looked at\)")


def as_said(text: str) -> str:
    """A stored message's words as the family typed them (a voice note keeps its mark)."""
    return text.removeprefix(CAPTURE_PREFIX)


def unseen(what: str, words: str) -> str:
    """Words that came with something not looked at: "(with a video, not seen) we should..."."""
    return UNSEEN.format(what=what) + words


def unheard(seconds: int) -> str:
    """What a voice note is stored as until its words are known."""
    minutes, rest = divmod(max(int(seconds), 0), 60)
    return UNHEARD.format(length=f"{minutes}:{rest:02d}")


def unlooked(count: int) -> str:
    """What a photo, or an album of them, is stored as until it is looked at."""
    return UNLOOKED if count == 1 else UNLOOKED_ALBUM.format(count=count)


def is_unlooked(text: str) -> bool:
    """Whether a stored message is a photo, or an album, nobody ever looked at."""
    return UNLOOKED_FORM.fullmatch(text) is not None


def seen_in_photos(seen: list[str | None], total: int) -> str:
    """What was seen in a photo or album as kept: "(photo) ..." for one, else each by number."""
    if total == 1 and seen and seen[0]:
        return PHOTO_PREFIX + seen[0]
    parts = [
        f"(photo {number} of {total}) {words}"
        if words
        else f"(photo {number} of {total}, not seen)"
        for number, words in enumerate(seen, start=1)
    ]
    if total > len(seen):
        parts.append(f"(photos {len(seen) + 1} to {total}, not looked at)")
    return "\n\n".join(parts)


def is_unheard(text: str) -> bool:
    """Whether a stored message is a voice note whose words never arrived."""
    return text.startswith(UNHEARD.split("{", 1)[0]) and text.endswith(", not heard)")


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
    buttons: list[dict[str, str]] | None = None
    # The kind of message she sent unprompted (a voice event, or "digest"); None otherwise.
    sent_as: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Message:
        data = dict(row)
        data["actions"] = from_json(data.get("actions"))
        data["buttons"] = from_json(data.get("buttons"))
        return cls(**data)


def exists_update(conn: sqlite3.Connection, channel: str, channel_update_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM messages WHERE channel = ? AND channel_update_id = ?",
        (channel, channel_update_id),
    ).fetchone()
    return row is not None


def has_written(conn: sqlite3.Connection, channel: str, chat_id: str) -> bool:
    """Whether anybody has written in this chat (the bot may not write first)."""
    row = conn.execute(
        "SELECT 1 FROM messages WHERE channel = ? AND chat_id = ? AND direction = 'in' LIMIT 1",
        (channel, chat_id),
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
    buttons: list[dict[str, str]] | None = None,
    sent_as: str | None = None,
) -> Message:
    stamp = now or utcnow_iso()
    row = {
        "channel": channel,
        "chat_id": chat_id,
        "direction": "out",
        "text": text,
        "received_at": stamp,
        "status": "processed",
        "reply_to": reply_to,
        "processed_at": stamp,
    }
    if buttons:  # columns named only when used, so an older database can still be written
        row["buttons"] = to_json(buttons)
    if sent_as:
        row["sent_as"] = sent_as
    cur = conn.execute(
        f"INSERT INTO messages ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
        tuple(row.values()),
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


def set_text(conn: sqlite3.Connection, message_id: int, text: str) -> None:
    """Replace what an inbound message says: a voice note's words, once they are heard."""
    conn.execute("UPDATE messages SET text = ? WHERE id = ?", (text, message_id))


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


def last_inbound_at(conn: sqlite3.Connection, channel: str, chat_id: str) -> str | None:
    """When the family last wrote in this chat, or None."""
    row = conn.execute(
        "SELECT max(received_at) AS at FROM messages WHERE channel = ? AND chat_id = ? "
        "AND direction = 'in'",
        (channel, chat_id),
    ).fetchone()
    return row["at"] if row else None


def replies_to(conn: sqlite3.Connection, message_id: int) -> list[Message]:
    """What was said back to a message, in order."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE reply_to = ? AND direction = 'out' ORDER BY id", (message_id,)
    ).fetchall()
    return [Message.from_row(row) for row in rows]


def gathering(
    conn: sqlite3.Connection,
    chat_id: str,
    member_id: int,
    *,
    now: str,
    after: int | None = None,
    before: int | None = None,
) -> list[Message]:
    """One person's messages in one chat held to be answered together (pipeline.receive), oldest
    first; one whose hold lapsed is the retry job's."""
    sql = (
        "SELECT * FROM messages WHERE direction = 'in' AND chat_id = ? AND member_id = ? "
        "AND status = 'received' AND give_up = 0 AND claim_token = 'gather' AND claim_until > ?"
    )
    params: list[Any] = [chat_id, member_id, now]
    if after is not None:
        sql += " AND id > ?"
        params.append(after)
    if before is not None:
        sql += " AND id < ?"
        params.append(before)
    rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    return [Message.from_row(row) for row in rows]


def fold_into(conn: sqlite3.Connection, message_ids: list[int], into: int, *, now: str) -> None:
    """Mark a burst's earlier messages processed and `reply_to` the later one, so its reply or
    retry answers them too. Call inside a transaction."""
    conn.executemany(
        "UPDATE messages SET status = 'processed', processed_at = ?, reply_to = ? WHERE id = ?",
        [(now, into, message_id) for message_id in message_ids],
    )


def folded_into(conn: sqlite3.Connection, message_id: int) -> list[Message]:
    """The earlier messages of a burst folded into this one, oldest first."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE direction = 'in' AND reply_to = ? ORDER BY id",
        (message_id,),
    ).fetchall()
    return [Message.from_row(row) for row in rows]


def cancel_unsent(conn: sqlite3.Connection, channel: str, chat_id: str, *, now: str) -> int:
    """Stop everything stored for a chat and not sent yet from going. Call inside a transaction."""
    return conn.execute(
        "UPDATE messages SET cancelled_at = ? WHERE direction = 'out' AND channel = ? "
        "AND chat_id = ? AND delivered_at IS NULL AND cancelled_at IS NULL",
        (now, channel, chat_id),
    ).rowcount


def mark_sent_as(conn: sqlite3.Connection, message_id: int, kind: str) -> None:
    """Say which kind of message she sent of her own accord (voice.hand_over)."""
    conn.execute("UPDATE messages SET sent_as = ? WHERE id = ?", (kind, message_id))


def sent_on_their_own(conn: sqlite3.Connection, *, since: str, limit: int) -> list[Message]:
    """What she sent of her own accord since a moment, newest first."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE sent_as IS NOT NULL AND received_at >= ? "
        "ORDER BY received_at DESC, id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [Message.from_row(row) for row in rows]


def sent_on_their_own_counts(conn: sqlite3.Connection, *, since: str) -> dict[str, tuple[int, str]]:
    """How many of each kind she sent of her own accord since a moment, and the last one's time."""
    rows = conn.execute(
        "SELECT sent_as, count(*) AS n, max(received_at) AS last FROM messages "
        "WHERE sent_as IS NOT NULL AND received_at >= ? GROUP BY sent_as",
        (since,),
    ).fetchall()
    return {row["sent_as"]: (int(row["n"]), row["last"]) for row in rows}


def mark_delivered(conn: sqlite3.Connection, message_ids: list[int], *, now: str) -> None:
    """Carried by another message (a reply that mentioned it), so there is nothing to send."""
    conn.executemany(
        "UPDATE messages SET delivered_at = ? WHERE id = ? AND delivered_at IS NULL",
        [(now, message_id) for message_id in message_ids],
    )


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
    """The last `limit` messages in a chat, however old, oldest first (what the page shows)."""
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
    """Inbound messages that failed, newest first, retried or not."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE direction = 'in' AND status = 'failed' "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [Message.from_row(row) for row in rows]


def give_up(conn: sqlite3.Connection, message_id: int) -> None:
    """Stop the retry job from picking a message up, e.g. after a configuration error."""
    conn.execute("UPDATE messages SET give_up = 1 WHERE id = ?", (message_id,))


def reset_retries(conn: sqlite3.Connection) -> int:
    """Make every failed message eligible for retry again."""
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


def said_by_since(conn: sqlite3.Connection, member_id: int, since: str) -> list[str]:
    """What somebody said since then, oldest first: their words, for code that reads them."""
    rows = conn.execute(
        "SELECT text FROM messages WHERE member_id = ? AND direction = 'in' AND received_at >= ? "
        "ORDER BY id",
        (member_id, since),
    )
    return [row[0] for row in rows]
