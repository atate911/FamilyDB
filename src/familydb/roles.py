"""Who may do what: the three roles on the family list, and what each may do on the page.

- admin: looks after FamilyDB. Whatever a parent may, and the settings, setup, and the family
  list, which is who the bot talks to and who signs in. There is always at least one.
- parent: uses all the rest: chat, ideas, plans, things to do, how things went.
- kid: for now, whatever a parent may. Kids hardly use the page yet; when they do, what they may
  not do is decided in `PERMISSIONS` below, and nowhere else.

The page asks about a permission (`may`), never about a role, so giving kids limits of their
own, or adding a role, is a change to this table alone. The gate in web/auth.py says which part
of the page needs which permission.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["admin", "parent", "kid"]
ROLES: tuple[Role, ...] = ("admin", "parent", "kid")

Permission = Literal["sign_in", "chat", "change", "manage"]
# sign_in: sign in to the page, and read everything on it: home, ideas, plans, things to do,
#          what is connected and what it costs.
# chat:    talk to the bot on the page. Every message is paid for.
# change:  the forms that add and change ideas, plans, things to do and how things went.
# manage:  the settings, setup, and the family list: who the bot talks to and who signs in.

PARENT: frozenset[Permission] = frozenset({"sign_in", "chat", "change"})
PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": PARENT | {"manage"},
    "parent": PARENT,
    # A stand-in: a kid may do what a parent may until kids have limits of their own.
    "kid": PARENT,
}


def may(role: str, permission: Permission) -> bool:
    """Whether somebody in this role may do this. An unknown role may do nothing."""
    return permission in PERMISSIONS.get(role, frozenset())
