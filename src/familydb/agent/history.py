"""Rebuild the recent conversation of a chat from the message log."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from familydb.agent.render import render_history_line
from familydb.clock import Clock
from familydb.dates import utc_iso
from familydb.store import members, messages


@dataclass(frozen=True)
class HistoryTurn:
    role: Literal["user", "assistant"]
    text: str


def load_history(
    conn: sqlite3.Connection,
    chat_id: str,
    *,
    clock: Clock,
    limit: int,
    since_hours: float,
    exclude_message_id: int | None = None,
    exclude_replies_to: int | None = None,
) -> list[HistoryTurn]:
    """The last `limit` messages of a chat from the last `since_hours`, as plain text turns.

    `exclude_replies_to` drops the bot's own notices about a message (used when retrying it).
    """
    since = utc_iso(clock.now() - timedelta(hours=since_hours))
    names = {m.id: m.display_name for m in members.list_all(conn, active_only=False)}
    # The current inbound message is already stored and is the newest row; fetch one extra
    # so excluding it still leaves `limit` earlier messages.
    fetch = limit + 1 if exclude_message_id is not None else limit
    turns: list[HistoryTurn] = []
    for message in messages.recent_for_chat(conn, chat_id, limit=fetch, since=since):
        if message.id == exclude_message_id:
            continue
        if exclude_replies_to is not None and message.reply_to == exclude_replies_to:
            continue
        if message.direction == "in":
            sender = names.get(message.member_id or -1, "someone")
            turns.append(HistoryTurn("user", render_history_line(sender, message.text)))
        else:
            turns.append(HistoryTurn("assistant", message.text))
    return turns
