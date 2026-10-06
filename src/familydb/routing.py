"""Where a message the bot sends of its own accord goes: to whoever it is for.

Most go back to the chat they began in. In a family group what is only for one person (their
task's reminder, the note on their idea, how their plan went) goes to their own chat instead;
anything for everyone stays. A person's own chat is their Telegram chat with the bot once they
have written in it (Telegram lets a bot write to nobody who has not; an invite's link writes
/start there). Without one it goes where it began. `private_when_personal` turns it off.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store import members, messages

TELEGRAM = "telegram"
# Her whole reply in a group when she only saved what was asked: the channel shows it as a reaction
# (REACTION), which buzzes nobody.
CONFIRMED = "✓"
REACTION = "👌"


def own_chat(conn: sqlite3.Connection, member_id: int | None) -> tuple[str, str] | None:
    person = members.get(conn, member_id) if member_id is not None else None
    if person is None or not person.active or person.channel != TELEGRAM:
        return None
    chat_id = person.channel_user_id
    if not chat_id or not messages.has_written(conn, TELEGRAM, chat_id):
        return None
    return TELEGRAM, chat_id


def for_person(
    conn: sqlite3.Connection,
    settings: Any,
    channel: str,
    chat_id: str,
    member_id: int | None,
) -> tuple[str, str]:
    """Where something only for this person goes: their own chat if it began in a group and they
    have one, else this chat.
    """
    if not settings.private_when_personal or not is_group(channel, chat_id):
        return channel, chat_id
    return own_chat(conn, member_id) or (channel, chat_id)


def is_group(channel: str, chat_id: str) -> bool:
    return channel == TELEGRAM and chat_id.startswith("-")


def is_confirmation(text: str) -> bool:
    return text.strip() in {CONFIRMED, "✔", "✔️", "✅"}
