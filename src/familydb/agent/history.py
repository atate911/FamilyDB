"""Rebuild the recent conversation of a chat from the message log."""

from __future__ import annotations

import sqlite3
from collections.abc import Collection
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from familydb.agent.render import render_history_line
from familydb.clock import Clock
from familydb.dates import utc_iso
from familydb.store import members, messages

# History is paid for on every call, so it is budgeted: the newest messages fitting HISTORY_CHARS
# (about 1,500 tokens), each cut to MESSAGE_CHARS so one long paste is not re-paid for hours.
# Characters, because this runs before any provider is chosen.
HISTORY_CHARS = 6000
MESSAGE_CHARS = 1500
CUT = " [...]"


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
    budget: int = HISTORY_CHARS,
    also_exclude: Collection[int] = (),
    before_id: int | None = None,
) -> list[HistoryTurn]:
    """The last `limit` messages of a chat from the last `since_hours`, as text turns within
    `budget`. `exclude_replies_to` drops the bot's own notices about a message (on retry)."""
    since = utc_iso(clock.now() - timedelta(hours=since_hours))
    names = {m.id: m.display_name for m in members.list_all(conn, active_only=False)}
    # The current message is already stored as the newest row, so fetch one extra; `also_exclude`
    # are the earlier messages of a burst answered with it (pipeline.receive).
    fetch = (limit + 1 if exclude_message_id is not None else limit) + len(also_exclude)
    turns: list[HistoryTurn] = []
    for message in messages.recent_for_chat(conn, chat_id, limit=fetch, since=since):
        if message.id == exclude_message_id or message.id in also_exclude:
            continue
        # A later message still waits for its own turn (pipeline.receive).
        if before_id is not None and message.direction == "in" and message.id > before_id:
            continue
        if exclude_replies_to is not None and message.reply_to == exclude_replies_to:
            continue
        if message.direction == "in":
            sender = names.get(message.member_id or -1, "someone")
            turns.append(HistoryTurn("user", render_history_line(sender, message.text)))
        else:
            turns.append(HistoryTurn("assistant", message.text))
    return within_budget(turns, budget)


def within_budget(
    turns: list[HistoryTurn], budget: int, *, each: int = MESSAGE_CHARS
) -> list[HistoryTurn]:
    """The newest turns fitting `budget` characters, each cut to `each` first."""
    kept: list[HistoryTurn] = []
    used = 0
    for turn in reversed(turns):
        text = turn.text if len(turn.text) <= each else turn.text[: each - len(CUT)] + CUT
        if used + len(text) > budget:
            break
        kept.append(HistoryTurn(turn.role, text))
        used += len(text)
    kept.reverse()
    return kept
