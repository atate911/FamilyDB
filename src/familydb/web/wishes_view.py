"""A kid's wish lists as the page shows them (docs/WISHES.md): her three lists in her order, what
was answered lately and the countdowns, for Now's glance and the Kids page alike, so the two
never disagree."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from familydb.base import roles
from familydb.base.dates import next_birthday
from familydb.store import members as member_store
from familydb.store import wishes as wish_store
from familydb.web import auth, views

ANSWERED_DAYS = 30
TOP_WISHES = 3


def is_kid(member: member_store.Member) -> bool:
    """A kid, by roles.py: keeps a wish list and decides on nobody's."""
    return roles.may(member.role, "wish") and not roles.may(member.role, "decide")


def lists(conn: Any, kid: member_store.Member, today: date) -> dict[str, Any]:
    """A kid's three lists in her order, what was answered lately, and the countdowns."""
    christmas = date(today.year, 12, 25)
    if christmas < today:
        christmas = date(today.year + 1, 12, 25)
    birthday = next_birthday(kid.birth_date, today)
    days = {
        "christmas": (christmas - today).days,
        "birthday": (birthday - today).days if birthday else None,
    }
    lists = [
        {
            "occasion": occasion,
            "value": occasion or "everyday",
            "name": name,
            "lede": lede,
            "countdown": views.countdown(days.get(occasion)) if occasion else None,
            "rows": [
                views.wish_row(wish, today) for wish in wish_store.open_list(conn, kid.id, occasion)
            ],
        }
        for occasion, name, lede in views.WISH_LISTS
    ]
    since = (today - timedelta(days=ANSWERED_DAYS)).isoformat()
    everything = wish_store.for_member(conn, kid.id)
    answered = [
        views.wish_row(wish, today)
        for wish in everything
        if wish.status in ("granted", "declined") and (wish.answered_at or "") >= since
    ]
    turned = [
        views.wish_row(wish, today)
        for wish in everything
        if wish.status == "turned_away" and wish.created_at >= since
    ]
    return {
        "id": kid.id,
        "name": kid.display_name,
        "slot": kid.slot or 0,
        "initial": kid.display_name[:1].upper(),
        "lists": lists,
        "answered": answered,
        "turned": turned,
        "open": sum(len(each["rows"]) for each in lists),
    }


def kids(conn: Any) -> list[member_store.Member]:
    return [m for m in member_store.list_all(conn) if is_kid(m)]


def glance(conn: Any, today: date) -> dict[str, Any] | None:
    """For Home: a kid's own lists, or for a parent each kid's and what waits on them."""
    visitor = auth.visitor()
    if visitor.may("decide"):
        shown = [lists(conn, kid, today) for kid in kids(conn)]
        if not shown:
            return None
        waiting = [
            {**row, "kid": kid["name"], "kid_id": kid["id"]}
            for kid in shown
            for row in kid["turned"]
            if row["to_decide"]
        ]
        return {"parent": True, "kids": shown, "waiting": waiting, "top": TOP_WISHES}
    if visitor.member is not None and visitor.may("wish"):
        return {"parent": False, "mine": lists(conn, visitor.member, today), "top": TOP_WISHES}
    return None
