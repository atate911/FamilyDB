"""What the page's frame says around every page: who is signed in, how the assistant stands (the
health pill), and the counts that sit by a page's name in the sidebar ("3 late", "1 to decide").
Read from the log and the tables, no model call. Only a page built on `base.html` asks, so
a page that has not moved to it costs nothing."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from flask import session

from familydb import personas, presents
from familydb.app import App
from familydb.store import members as member_store
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
    # Her messages in this visitor's page conversation since this browser last looked.
    unread: int = 0
    # Everyone on the family list as marks (name, colour, letter), so a thing that is everyone's can
    # show the family stacked rather than a word (docs/STYLE.md, "Owner mark").
    family: tuple[dict[str, Any], ...] = ()
    # Whether anybody on the list is a kid: without one there is no Kids in the row.
    kids: bool = False

    @property
    def look_at(self) -> int:
        """Things worth a look now; the phone's picture carries a dot while there are any. (What
        she said that is new has its own count on Chat.)"""
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
            unread = _unread(conn) if visitor.may("chat") else 0
            everyone = member_store.list_all(conn)
            family = tuple(
                {"name": m.display_name, "slot": m.slot or 0, "initial": m.display_name[:1].upper()}
                for m in everyone
            )
            kids = any(m.active and m.role == "kid" for m in everyone)
    except sqlite3.OperationalError:
        # A database not yet migrated: the frame is drawn without counts, so a page that says
        # "not found" or "not yours" never fails itself.
        log.warning("the menu's counts could not be read", exc_info=True)
        return Frame(me)
    return Frame(me, pill, late, decide, rate, check, unread, family, kids)


def _unread(conn: sqlite3.Connection) -> int:
    """Her messages in this visitor's conversation since this browser last saw it. A browser
    that never looked starts from now, not from everything ever said."""
    chat_id = chat.my_chat()
    seen = session.get(chat.SEEN_KEY)
    if not isinstance(seen, dict) or seen.get("chat") != chat_id:
        session[chat.SEEN_KEY] = {
            "chat": chat_id,
            "id": message_store.newest_from_her(conn, chat_id),
        }
        return 0
    return message_store.unread(conn, chat_id, after=int(seen.get("id") or 0))


def _late(conn: sqlite3.Connection, visitor: auth.Visitor, tz: Any, today: Any) -> int:
    """Open to-dos whose day has passed: everybody's for a grown-up, her own for a kid."""
    if not (visitor.may("change") or visitor.may("own_tasks")):
        return 0
    own = None if visitor.may("browse") or visitor.member is None else visitor.member.id
    found = task_store.list_all(conn, status="open", owner_id=own)
    return sum(
        views.is_late(task, tz, today)
        for task in presents.visible_tasks(conn, found, visitor.member)
    )


def _to_decide(conn: sqlite3.Connection, visitor: auth.Visitor, today: Any) -> int:
    """Wishes waiting on a parent's answer, as Now asks about them."""
    if not visitor.may("decide"):
        return 0
    return len(wishes_waiting(conn, today))


# A turned-away wish waits on a parent this long before it is let go (docs/WISHES.md).
WAITING_DAYS = 30


def wishes_waiting(conn: sqlite3.Connection, today: Any) -> list[dict[str, Any]]:
    """Every kid's wishes that wait on a parent: she asked, or it was turned away as not OK and the
    parents were told. Oldest first, each with the kid and when it was asked."""
    from familydb import roles
    from familydb.store import wishes as wish_store

    since = (today - timedelta(days=WAITING_DAYS)).isoformat()
    rows = []
    for kid in member_store.list_all(conn):
        if not (roles.may(kid.role, "wish") and not roles.may(kid.role, "decide") and kid.active):
            continue
        for wish in wish_store.for_member(conn, kid.id):
            if wish.status != "turned_away" or wish.created_at < since:
                continue
            if not (wish.parent_review == "asked" or wish.concern == "inappropriate"):
                continue
            rows.append(
                {
                    "id": wish.id,
                    "title": wish.title,
                    "kid": kid.display_name,
                    "kid_id": kid.id,
                    "concern": views.CONCERN_WORDS.get(wish.concern or ""),
                    "asked_at": wish.updated_at,
                }
            )
    rows.sort(key=lambda row: row["asked_at"])
    return rows


def _to_rate(conn: sqlite3.Connection, visitor: auth.Visitor, today: Any) -> int:
    """Plans of the last two weeks nobody has said how they went."""
    if not visitor.may("change"):
        return 0
    since = today - timedelta(days=RATE_DAYS)
    waiting = plan_store.unrated(conn, today=today.isoformat(), since=since.isoformat())
    return len(presents.without(waiting, presents.kept_ids(conn, visitor.member)))


def _pill(app: App, conn: sqlite3.Connection, visitor: auth.Visitor) -> status_page.Pill:
    name = personas.active(app.settings).name
    chat_id = chat.my_chat()
    thread = message_store.last_for_chat(conn, chat_id, limit=chat.GLANCE_LIMIT)
    state, _ = chat.standing(app, thread, chat_id)
    return status_page.pill(app, conn, name=name, busy=state == "thinking")


# -- the row of destinations (docs/INTERFACE.md section 2) ----------------------------------------


@dataclass(frozen=True)
class Destination:
    """One place in the row at the foot of every page: its word, where it goes, whether this is
    it, and a count where one waits there ("1 to decide")."""

    key: str
    label: str
    href: str
    current: bool = False
    count: int = 0
    word: str = ""


# Which pages belong to each place, so the row marks the one you are on.
OWNS: dict[str, frozenset[str]] = {
    "now": frozenset({"web.home", "go.about", "go.board"}),
    "eat": frozenset({"web.restaurants"}),
    "do": frozenset({"web.ideas", "web.idea", "web.new_idea", "web.edit_idea"}),
    "week": frozenset(
        {
            "go.week",
            "go.day",
            "go.plan",
            "web.plans",
            "web.plans_month",
            "web.tasks",
            "web.edit_task",
        }
    ),
    "kids": frozenset({"web.wishes"}),
    "soon": frozenset({"web.happening_page", "web.find"}),
    "lists": frozenset({"web.lists_page"}),
    "did": frozenset({"go.did", "go.outing"}),
}


def destinations(frame: Frame) -> list[Destination]:
    """The row for this visitor: a grown-up's eight places, a kid's four (docs/INTERFACE.md
    section 9). Each is a want, not a table: Eat, Do, Week."""
    from flask import request, url_for

    visitor = auth.visitor()
    here = request.endpoint or ""
    grown_up = visitor.may("browse")
    places: list[tuple[str, str, str, int, str]] = [("now", "Now", url_for("web.home"), 0, "")]
    if grown_up:
        places.append(("eat", "Eat", url_for("web.restaurants"), 0, ""))
        places.append(("do", "Do", url_for("web.ideas"), 0, ""))
        places.append(("week", "Week", url_for("go.week"), frame.late, "late"))
        if visitor.may("decide") and frame.kids:
            places.append(("kids", "Kids", url_for("web.wishes"), frame.decide, "to decide"))
        places.append(("soon", "Soon", url_for("web.happening_page"), 0, ""))
        if visitor.may("change"):
            places.append(("lists", "Lists", url_for("web.lists_page"), 0, ""))
        places.append(("did", "Did", url_for("go.did"), frame.rate, "to rate"))
    else:
        places.append(("do", "Do", url_for("web.ideas"), 0, ""))
        places.append(("week", "My week", url_for("go.week"), 0, ""))
        if visitor.may("wish") and visitor.member is not None:
            places.append(("kids", "My list", url_for("web.wishes"), 0, ""))
    return [
        Destination(key, label, href, here in OWNS.get(key, frozenset()), count, word)
        for key, label, href, count, word in places
    ]
