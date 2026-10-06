"""Who reads a chat, for what code says in it and where it sends things.

Code cannot see who is in a Telegram group, so it assumes the worst: everyone on the family list.
A private chat is read by its one person (a kid's own page conversation also by a parent); the
page's shared conversation by those who may decide (web/chat.my_chat); the console by whoever
types.

`plain`: whether the bot's own lines there must leave out how it works (keys, models, dollar
limits, admins, settings, logs: `voice.say(..., plain=True)`); only somebody who may `browse`
sees that (roles.py), so kids never do. `everyone_may` is the general form: a birthday's gift
ideas are never sent where a kid reads (`decide`).
"""

from __future__ import annotations

import sqlite3

from familydb import roles
from familydb.roles import Permission
from familydb.store import members
from familydb.store.members import Member

WEB_SHARED = "web"
WEB_PRIVATE = "member:"


def readers(
    conn: sqlite3.Connection, channel: str, chat_id: str, sender: Member | None = None
) -> list[Member]:
    everyone = [member for member in members.list_all(conn) if member.active]
    if channel == "telegram" and chat_id.startswith("-"):
        return everyone
    if channel == "telegram":
        person = members.resolve(conn, "telegram", chat_id)
        return [person] if person is not None else ([sender] if sender else [])
    if channel == "web" and chat_id.startswith(WEB_PRIVATE):
        number = chat_id.removeprefix(WEB_PRIVATE)
        owner = members.get(conn, int(number)) if number.isdigit() else None
        parents = [member for member in everyone if roles.may(member.role, "decide")]
        return ([owner] if owner is not None else []) + parents
    if channel == "web" and chat_id == WEB_SHARED:
        return [member for member in everyone if roles.may(member.role, "decide")]
    return [sender] if sender is not None else []


def everyone_may(
    conn: sqlite3.Connection,
    channel: str,
    chat_id: str,
    permission: Permission,
    sender: Member | None = None,
) -> bool:
    """Whether everybody who may read this chat may do this (roles.py); the sender counts, as
    somebody talking in a chat reads it.
    """
    people = readers(conn, channel, chat_id, sender)
    if sender is not None:
        people.append(sender)
    return all(roles.may(member.role, permission) for member in people)


def plain(
    conn: sqlite3.Connection, channel: str, chat_id: str, sender: Member | None = None
) -> bool:
    """Whether somebody reading this chat may not see how the bot works, so its own lines leave the
    workings out (`voice.PLAIN`).
    """
    return not everyone_may(conn, channel, chat_id, "browse", sender)
