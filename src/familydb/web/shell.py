"""What the page's frame says around every page: who is signed in, how the assistant stands (the
health pill), and the counts that sit by a page's name in the sidebar ("3 late", "1 to decide").
Read from the log and the tables, no model call. Only a page built on `base_kitchen.html` asks, so
a page that has not moved to it costs nothing."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from familydb import personas
from familydb.app import App
from familydb.store import messages as message_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.web import auth, chat, views
from familydb.web import settings as settings_page
from familydb.web import status as status_page

log = logging.getLogger(__name__)

# How far back a plan still waits to be rated; the follow-up job asks about the same ones.
RATE_DAYS = 14
ROLE_WORDS = {"admin": "Admin", "parent": "Parent", "kid": "Kid"}


@dataclass(frozen=True)
class Me:
    """The person at the page. With the family sharing one password nobody in particular is
    signed in, so there is no name and the colour is Everyone's (slot 0)."""

    name: str | None
    initial: str
    slot: int
    role: str | None


@dataclass(frozen=True)
class Frame:
    me: Me
    # Grown-ups only: kids never see how it works (roles.py `browse`).
    pill: status_page.Pill | None = None
    late: int = 0
    decide: int = 0
    rate: int = 0
    check: int = 0

    @property
    def look_at(self) -> int:
        """Things worth a look now; the phone's picture carries a dot while there are any."""
        return self.late + self.decide + self.rate + self.check

    @property
    def menu_label(self) -> str:
        """What a screen reader says for the phone's picture, which opens the menu."""
        who = self.me.name or "Your"
        label = f"{who}: your menu" if self.me.name else "Your menu"
        if self.look_at:
            label += f", {self.look_at} thing{'' if self.look_at == 1 else 's'} to look at"
        return label


def _me() -> Me:
    visitor = auth.visitor()
    member = visitor.member
    if member is None:
        return Me(None, "", 0, None)
    return Me(member.display_name, member.display_name[:1].upper(), member.slot or 0, member.role)


def frame(app: App) -> Frame:
    """The frame for this visitor on this request."""
    visitor = auth.visitor()
    me = _me()
    if visitor.kind == "stranger":
        return Frame(me)
    today = app.clock.today()
    tz = app.settings.tzinfo
    try:
        with closing(app.connect()) as conn:
            late = _late(conn, visitor, tz, today)
            decide = _to_decide(conn, visitor, today)
            rate = _to_rate(conn, visitor, today)
            check = settings_page.needs_look(app, conn) if visitor.may("manage") else 0
            pill = _pill(app, conn, visitor) if visitor.may("browse") else None
    except sqlite3.OperationalError:
        # A database not yet migrated: the frame is drawn without counts, so a page that says
        # "not found" or "not yours" never fails itself.
        log.warning("the menu's counts could not be read", exc_info=True)
        return Frame(me)
    return Frame(me, pill, late, decide, rate, check)


def _late(conn: sqlite3.Connection, visitor: auth.Visitor, tz: Any, today: Any) -> int:
    """Open to-dos whose day has passed: everybody's for a grown-up, her own for a kid."""
    if not (visitor.may("change") or visitor.may("own_tasks")):
        return 0
    own = None if visitor.may("browse") or visitor.member is None else visitor.member.id
    return sum(
        views.is_late(task, tz, today)
        for task in task_store.list_all(conn, status="open", owner_id=own)
    )


def _to_decide(conn: sqlite3.Connection, visitor: auth.Visitor, today: Any) -> int:
    """Wishes waiting on a parent's answer, as Home counts them."""
    if not visitor.may("decide"):
        return 0
    from familydb.web import routes  # not at the top: routes draws pages that use this frame

    glance = routes.wish_glance(conn, today)
    return len(glance["waiting"]) if glance and glance.get("parent") else 0


def _to_rate(conn: sqlite3.Connection, visitor: auth.Visitor, today: Any) -> int:
    """Plans of the last two weeks nobody has said how they went."""
    if not visitor.may("change"):
        return 0
    since = today - timedelta(days=RATE_DAYS)
    return len(plan_store.unrated(conn, today=today.isoformat(), since=since.isoformat()))


def _pill(app: App, conn: sqlite3.Connection, visitor: auth.Visitor) -> status_page.Pill:
    name = personas.active(app.settings).name
    chat_id = chat.my_chat()
    thread = message_store.last_for_chat(conn, chat_id, limit=chat.GLANCE_LIMIT)
    state, _ = chat.standing(app, thread, chat_id)
    return status_page.pill(app, conn, name=name, busy=state == "thinking")
