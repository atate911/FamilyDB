"""Who reads a chat, for what code says in it and where it sends things.

Code cannot see who is in a Telegram group, so it assumes the worst: everyone on the family list.
A private chat is read by the one person it belongs to (a Telegram chat with one person, whose id
is the chat's; a kid's own conversation on the page, which a parent may also read); the page's
shared conversation by those who may decide, since everybody else talks in their own
(web/chat.my_chat). The console is whoever is typing.

Two questions are asked of it. `plain` is whether what the bot says of its own accord there must
leave out how it works: keys, models, limits in dollars, admins, the settings page, the logs
(`voice.say(..., plain=True)`). Only somebody who may `browse` the household's pages sees that
(roles.py), so the kids never do. `everyone_may` is the general form, which the routing of a
birthday's gift ideas asks with `decide`: presents never go where a kid reads.
"""

from __future__ import annotations

import sqlite3

from familydb import roles
from familydb.roles import Permission
from familydb.store import members
from familydb.store.members import Member

# The page's conversations: the family's shared one, and a kid's own (web/chat.py).
WEB_SHARED = "web"
WEB_PRIVATE = "member:"


def readers(
    conn: sqlite3.Connection, channel: str, chat_id: str, sender: Member | None = None
) -> list[Member]:
    """Everybody who may read this chat, as far as code can tell."""
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
    """Whether everybody who may read this chat may do this (roles.py). The sender counts too:
    somebody talking in a chat reads it."""
    people = readers(conn, channel, chat_id, sender)
    if sender is not None:
        people.append(sender)
    return all(roles.may(member.role, permission) for member in people)


def plain(
    conn: sqlite3.Connection, channel: str, chat_id: str, sender: Member | None = None
) -> bool:
    """Whether somebody who reads this chat may not see how the bot works, so its own lines
    there must leave the workings out (`voice.PLAIN`)."""
    return not everyone_may(conn, channel, chat_id, "browse", sender)
