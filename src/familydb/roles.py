"""Who may do what: the three roles on the family list, and what each may do on the page.

- admin: looks after FamilyDB. Whatever a parent may, and the settings, setup, and the family
  list, which is who the bot talks to and who signs in. There is always at least one.
- parent: uses all the rest: chat, ideas, plans, things to do, how things went, and answers what
  the kids wish for.
- kid: reads the ideas and the plans, talks to the bot, keeps her own wish lists, and ticks
  off (or changes) her own things to do; changes nothing else, and does not see the household's
  pages (what she remembers, what it costs) or anybody else's things to do; all within a
  number of messages a day the family sets (`kid_daily_messages`, for every role in
  `DAILY_LIMITED`). What she may not do is decided in
  `PERMISSIONS` below, and nowhere else.

The page asks about a permission (`may`), never about a role, so giving kids limits of their
own, or adding a role, is a change to this table alone. The gate in web/auth.py says which part
of the page needs which permission.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["admin", "parent", "kid"]
ROLES: tuple[Role, ...] = ("admin", "parent", "kid")

Permission = Literal["sign_in", "chat", "change", "own_tasks", "browse", "wish", "decide", "manage"]
# sign_in: sign in to the page, and read the ideas and the plans on it.
# chat:    talk to the bot on the page. Every message is paid for.
# change:  the forms that add and change ideas, plans, things to do and how things went.
# own_tasks: tick off, or change, your own things to do (not the household's, nor anybody
#          else's), on the page and by asking the bot. Whoever may `change` may do it to any.
# browse:  the household's pages: what she remembers, what is connected and what it costs, and
#          everybody's things to do rather than only your own.
# wish:    keep your own wish lists.
# decide:  see every kid's wishes and answer them.
# manage:  the settings, setup, and the family list: who the bot talks to and who signs in.

PARENT: frozenset[Permission] = frozenset(
    {"sign_in", "chat", "change", "own_tasks", "browse", "wish", "decide"}
)
# The family decided the girls tick off their own things to do (docs/DESIGN.md section 16).
KID: frozenset[Permission] = frozenset({"sign_in", "chat", "wish", "own_tasks"})
PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": PARENT | {"manage"},
    "parent": PARENT,
    "kid": KID,
}


# Whose messages count against the day's number the family sets (`kid_daily_messages`).
DAILY_LIMITED: frozenset[str] = frozenset({"kid"})


def daily_limited(role: str) -> bool:
    """Whether somebody in this role has a number of messages a day."""
    return role in DAILY_LIMITED


def may(role: str, permission: Permission) -> bool:
    """Whether somebody in this role may do this. An unknown role may do nothing."""
    return permission in PERMISSIONS.get(role, frozenset())
