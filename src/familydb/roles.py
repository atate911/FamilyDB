"""Who may do what: the three roles and what each may do on the page, in `PERMISSIONS` and nowhere
else.

- admin: looks after FamilyDB: whatever a parent may, plus settings, setup and the family list
(who the bot talks to and who signs in). Always at least one. - parent: everything else: chat,
ideas, plans, things to do, outcomes, answering the kids' wishes. - kid: reads ideas and plans,
chats, keeps her own wish lists and her own things to do; sees none of the household's pages or
anybody else's tasks; limited to `kid_daily_messages` a day (every role in `DAILY_LIMITED`).

The page asks about a permission (`may`), never a role, so a new role or limit is a change to
this table alone; web/auth.py says which part of the page needs which.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["admin", "parent", "kid"]
ROLES: tuple[Role, ...] = ("admin", "parent", "kid")

Permission = Literal["sign_in", "chat", "change", "own_tasks", "browse", "wish", "decide", "manage"]
# sign_in: sign in, read ideas and plans. chat: talk to the bot (every message is paid for). change:
# the forms for ideas, plans, things to do and outcomes, and the chat tools that edit an idea,
# record an outcome or make, move or cancel a plan (`ToolSpec.needs`); a kid's chat adds ideas.
# own_tasks: tick off or change your own things to do, on the page and by asking the bot (`change`
# allows any). browse: the household's pages (memory, connections, cost) and everybody's things to
# do. wish: keep your own wish lists.
# decide: see every kid's wishes and answer them. manage: settings, setup and the family list.

PARENT: frozenset[Permission] = frozenset(
    {"sign_in", "chat", "change", "own_tasks", "browse", "wish", "decide"}
)
KID: frozenset[Permission] = frozenset({"sign_in", "chat", "wish", "own_tasks"})
PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": PARENT | {"manage"},
    "parent": PARENT,
    "kid": KID,
}


DAILY_LIMITED: frozenset[str] = frozenset({"kid"})


def daily_limited(role: str) -> bool:
    return role in DAILY_LIMITED


def may(role: str, permission: Permission) -> bool:
    return permission in PERMISSIONS.get(role, frozenset())
