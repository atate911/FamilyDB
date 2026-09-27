"""Where a message the bot sends of its own accord goes: to whoever it is for.

Most of them go back to the chat they began in. In a family group that means everyone gets
everything, so what is only for one person goes to that person's own chat with her instead: the
reminder for their own task, the note on an idea they added, how a plan they made went. Anything
for everyone (the weekend ideas, the evening before a plan) stays in the group.

A person's own chat is their Telegram chat with the bot, once they have written in it: Telegram
lets a bot write to nobody who has not (an invite's link opens that chat and writes /start in it).
Without one, it goes where it began, as before. `private_when_personal` turns it off.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store import members, messages

TELEGRAM = "telegram"
# Her whole reply in a group when she has only saved what was asked and has nothing to add. The
# channel shows it as a reaction on the message it answers (REACTION), which buzzes nobody, rather
# than a message everyone in the group is sent.
CONFIRMED = "✓"
REACTION = "👌"


def own_chat(conn: sqlite3.Connection, member_id: int | None) -> tuple[str, str] | None:
    """This person's own Telegram chat with the bot, when they have written in it."""
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
    """Where something only for this person goes, when it began in this chat: their own chat,
    if it began in a group and they have one; else this chat."""
    if not settings.private_when_personal or not is_group(channel, chat_id):
        return channel, chat_id
    return own_chat(conn, member_id) or (channel, chat_id)


def is_group(channel: str, chat_id: str) -> bool:
    """A Telegram group: its chat id is negative."""
    return channel == TELEGRAM and chat_id.startswith("-")


def is_confirmation(text: str) -> bool:
    """Whether a reply says nothing but that it was done (`CONFIRMED`)."""
    return text.strip() in {CONFIRMED, "✔", "✔️", "✅"}
