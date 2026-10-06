"""Where a message the bot sends of its own accord goes: to whoever it is for.

What is only for one person (their task's reminder, the note on an idea they added, how their plan
went) goes to them, which the family asked for as a Telegram notification (docs/DESIGN.md section
16): from a family group, from the page, or from somebody else's chat, to their own Telegram chat
with the bot, once they have written in it (Telegram lets a bot write to nobody who has not; an
invite's link writes /start there), and otherwise to their own conversation on the page. Asked for
in their own chat, it stays there. What is for everyone stays where it began, and a task nobody
owns, which is everyone's, goes to the family's chat (`family_chat_id`) when it was asked for
anywhere else. `private_when_personal` turns the moving off. It is decided as each message goes,
never when the task is made, so somebody who opens their chat with the bot next week is reached
there from then on.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb import audience
from familydb.store import members, messages
from familydb.store.tasks import Task

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


def reach(conn: sqlite3.Connection, member_id: int | None) -> tuple[str, str] | None:
    """Where this person hears from the bot: their own Telegram chat, else their conversation on
    the page (a kid her own, everybody else the family's). None for nobody on the list."""
    person = members.get(conn, member_id) if member_id is not None else None
    if person is None or not person.active:
        return None
    return own_chat(conn, person.id) or audience.page_chat(person)


def channel_of(chat_id: str) -> str:
    """Which channel a configured chat id belongs to: "console" or "web" by name, else Telegram."""
    for named in ("console", "web"):
        if chat_id.startswith(named):
            return named
    return TELEGRAM


def family_chat(settings: Any) -> tuple[str, str] | None:
    """The family's chat, where what is for everyone goes when it was not asked for in a group:
    `family_chat_id`, else the one the weekend ideas go to. None when neither is chosen."""
    chosen = settings.family_chat_id or settings.digest_chat_id
    return (channel_of(chosen), chosen) if chosen else None


def someone_elses(conn: sqlite3.Connection, channel: str, chat_id: str, member_id: int) -> bool:
    """Whether this chat is known to be somebody other than this person's: the page's shared
    conversation, another's own conversation there, or another's private Telegram chat (whose id
    is theirs). A private chat code cannot place on anybody is taken for theirs, and left alone."""
    if channel == "web":
        return chat_id != audience.private_chat(member_id)
    if channel != TELEGRAM:
        return True  # the console, which hears nothing once it is closed
    holder = members.resolve(conn, TELEGRAM, chat_id)
    return holder is not None and holder.id != member_id


def for_person(
    conn: sqlite3.Connection,
    settings: Any,
    channel: str,
    chat_id: str,
    member_id: int | None,
) -> tuple[str, str]:
    """Where something only for this person goes, when it began in this chat: here when this is
    their own chat or the switch is off; else to them (`reach`), or here when they cannot be.
    """
    if not settings.private_when_personal or member_id is None:
        return channel, chat_id
    if is_group(channel, chat_id):
        # In a group, only their own Telegram chat takes it out: the page is no place to move a
        # message that everybody in the group could otherwise read where it was asked for.
        return own_chat(conn, member_id) or (channel, chat_id)
    if not someone_elses(conn, channel, chat_id, member_id):
        return channel, chat_id
    return reach(conn, member_id) or (channel, chat_id)


def for_task(conn: sqlite3.Connection, settings: Any, task: Task) -> tuple[str, str]:
    """Where a task's reminder or nudge goes: to its owner (`for_person`); a task nobody owns is
    everyone's, and asked for anywhere but a group it goes to the family's chat, when one is
    chosen."""
    if task.owner_id is None:
        if is_group(task.channel, task.chat_id):
            return task.channel, task.chat_id
        return family_chat(settings) or (task.channel, task.chat_id)
    return for_person(conn, settings, task.channel, task.chat_id, task.owner_id)


def where_words(conn: sqlite3.Connection, channel: str, chat_id: str, *, sender: Any = None) -> str:
    """A chat in words, for the model to tell the family where something will arrive."""
    if is_group(channel, chat_id):
        return "the Telegram group"
    if channel == TELEGRAM:
        person = members.resolve(conn, TELEGRAM, chat_id)
        if person is None:
            return "a Telegram chat"
        if sender is not None and person.id == sender.id:
            return "your own chat on Telegram"
        return f"{person.display_name}'s own chat on Telegram"
    if channel == "web":
        number = chat_id.removeprefix(audience.WEB_PRIVATE)
        if chat_id.startswith(audience.WEB_PRIVATE) and number.isdigit():
            person = members.get(conn, int(number))
            return f"{person.display_name}'s page" if person else "a page"
        return "the chat on the page"
    return "this chat"


def is_group(channel: str, chat_id: str) -> bool:
    return channel == TELEGRAM and chat_id.startswith("-")


def is_confirmation(text: str) -> bool:
    return text.strip() in {CONFIRMED, "✔", "✔️", "✅"}
