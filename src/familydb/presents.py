"""Whom a present is kept from.

A present (an idea of kind "gift") is hidden from exactly the people it names, and the page says
whom: "Hidden from Maya and Theo". Nobody chose, which is every present until somebody does, means
the people it is for (`gifts_for` finds them by name among its participants). A present that names
nobody a family member is kept from the kids, as every present was before this, so saving one with
no name never shows it to them by accident. Choosing a list of people, even an empty one, overrides
all of that (the idea form, `ideas.hidden_from`).

Everything that shows ideas asks here, so the pages and the chat tools agree.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from familydb import roles
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store.ideas import Idea
from familydb.store.members import Member

KIDS = "the kids"


@dataclass(frozen=True)
class Kept:
    """Whom one present is kept from: their ids, and the words for it ("Maya and Theo")."""

    ids: frozenset[int]
    words: str

    @property
    def label(self) -> str:
        return f"Hidden from {self.words}" if self.words else ""


def join_names(names: list[str]) -> str:
    """ "Maya", "Maya and Theo", "Sam, Maya and Theo"."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _named(member: Member, idea: Idea) -> bool:
    wanted = re.compile(rf"\b{re.escape(member.display_name.strip().casefold())}\b")
    return any(wanted.search(person.casefold()) for person in idea.participants)


def default_for(idea: Idea, people: list[Member]) -> Kept:
    """Whom a present is kept from when nobody chose: the people it names, else the kids."""
    active = [member for member in people if member.active]
    named = [member for member in active if _named(member, idea)]
    if named:
        return Kept(
            frozenset(member.id for member in named),
            join_names([member.display_name for member in named]),
        )
    kids = [member for member in active if not roles.may(member.role, "decide")]
    return Kept(frozenset(member.id for member in kids), KIDS if kids else "")


def of_presents(
    conn: sqlite3.Connection, found: list[Idea], people: list[Member]
) -> dict[int, Kept]:
    """For each present among `found`, whom it is kept from. Other ideas are not in the answer."""
    gifts = [idea for idea in found if idea_store.is_gift(idea)]
    chosen = idea_store.chosen_hidden_from(conn, [idea.id for idea in gifts])
    active = {member.id: member for member in people if member.active}
    kept: dict[int, Kept] = {}
    for idea in gifts:
        ids = chosen.get(idea.id)
        if ids is None:
            kept[idea.id] = default_for(idea, people)
            continue
        names = [active[one].display_name for one in ids if one in active]
        kept[idea.id] = Kept(frozenset(one for one in ids if one in active), join_names(names))
    return kept


def choose(conn: sqlite3.Connection, idea: Idea, member_ids: list[int]) -> None:
    """Save the people the idea form chose to keep a present from. Exactly the default is kept as
    no choice at all, so the present goes on following whom it is for if that changes."""
    people = member_store.list_all(conn)
    wanted = {one.id for one in people if one.active and one.id in set(member_ids)}
    chosen = None if wanted == set(default_for(idea, people).ids) else sorted(wanted)
    idea_store.set_hidden_from(conn, idea.id, chosen)


def kept_ids(
    conn: sqlite3.Connection, who: Member | None, *, kids_see_none: bool = False
) -> set[int]:
    """The ideas this person must not see: the presents hidden from them. Nobody in particular (the
    family sharing one password, a job) is kept from nothing, as the grown-ups always were.

    The pages tell a kid of the presents that are not hers, tagged; the chat does not
    (`kids_see_none`), because a model told of a present can say so anywhere, and the prompt
    promises a kid never hears of one."""
    if who is None:
        return set()
    everything = idea_store.list_all(conn, include_dropped=True)
    kept = of_presents(conn, everything, member_store.list_all(conn))
    if kids_see_none and not roles.may(who.role, "decide"):
        return set(kept)
    return {idea_id for idea_id, one in kept.items() if who.id in one.ids}


def is_kept_from(
    conn: sqlite3.Connection,
    idea: Idea | None,
    who: Member | None,
    *,
    kids_see_none: bool = False,
) -> bool:
    """Whether this one idea is a present hidden from this person."""
    if idea is None or who is None or not idea_store.is_gift(idea):
        return False
    if kids_see_none and not roles.may(who.role, "decide"):
        return True
    kept = of_presents(conn, [idea], member_store.list_all(conn))
    return who.id in kept[idea.id].ids
