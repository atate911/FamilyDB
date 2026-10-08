"""Whom a present is kept from.

A present (an idea of kind "gift") is kept from every kid, always, and from the grown-up it is for;
a grown-up may keep one from another grown-up too. The page says whom: "Hidden from the kids and
Alex". What the idea form chooses (`ideas.hidden_from`) is only the grown-ups; kids are kept from
by role, so no list can let one see a present. Nobody chose, which is every present until somebody
does, means the grown-ups the present names (`gifts_for` finds them by name among its
participants). Choosing a list of grown-ups, even an empty one, overrides that.

Everything that shows ideas, and the to-dos about them (`tasks.idea_id`), asks here, so the pages
and the chat tools agree.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from familydb import roles
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store.ideas import Idea
from familydb.store.members import Member
from familydb.store.tasks import Task

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


def _kids(people: list[Member]) -> list[Member]:
    return [member for member in people if member.active and not roles.may(member.role, "decide")]


def _words(people: list[Member], grown_ups: list[Member]) -> str:
    return join_names([*([KIDS] if _kids(people) else []), *(m.display_name for m in grown_ups)])


def _kept(people: list[Member], grown_ups: list[Member]) -> Kept:
    ids = {member.id for member in [*_kids(people), *grown_ups]}
    return Kept(frozenset(ids), _words(people, grown_ups))


def default_for(idea: Idea, people: list[Member]) -> Kept:
    """Whom a present is kept from when nobody chose: every kid, and the grown-ups it names."""
    named = [
        member
        for member in people
        if member.active and roles.may(member.role, "decide") and _named(member, idea)
    ]
    return _kept(people, named)


def of_presents(
    conn: sqlite3.Connection, found: list[Idea], people: list[Member]
) -> dict[int, Kept]:
    """For each present among `found`, whom it is kept from. Other ideas are not in the answer."""
    gifts = [idea for idea in found if idea_store.is_gift(idea)]
    chosen = idea_store.chosen_hidden_from(conn, [idea.id for idea in gifts])
    grown = {
        member.id: member for member in people if member.active and roles.may(member.role, "decide")
    }
    kept: dict[int, Kept] = {}
    for idea in gifts:
        ids = chosen.get(idea.id)
        if ids is None:
            kept[idea.id] = default_for(idea, people)
            continue
        kept[idea.id] = _kept(people, [grown[one] for one in ids if one in grown])
    return kept


def choose(conn: sqlite3.Connection, idea: Idea, member_ids: list[int]) -> None:
    """Save the grown-ups the idea form chose to keep a present from (a kid in the list is
    ignored: kids are kept from by role). Exactly the default is kept as no choice at all, so the
    present goes on following whom it is for if that changes."""
    people = member_store.list_all(conn)
    grown = {m.id for m in people if m.active and roles.may(m.role, "decide")}
    wanted = {one for one in member_ids if one in grown}
    named = {m.id for m in people if m.id in grown and _named(m, idea)}
    idea_store.set_hidden_from(conn, idea.id, None if wanted == named else sorted(wanted))


def kept_ids(conn: sqlite3.Connection, who: Member | None) -> set[int]:
    """The ideas this person must not see: every present for a kid, and for a grown-up the ones
    kept from them. Nobody in particular (the family sharing one password, a job) is kept from
    nothing, as the grown-ups always were."""
    if who is None:
        return set()
    everything = idea_store.list_all(conn, include_dropped=True)
    kept = of_presents(conn, everything, member_store.list_all(conn))
    return {idea_id for idea_id, one in kept.items() if who.id in one.ids}


def without(items: list[Any], kept: set[int]) -> list[Any]:
    """These plans or agenda entries (anything with an `idea_id`) minus the ones made from an idea
    in `kept`, the present a plan is for being the idea it was made from."""
    return [item for item in items if getattr(item, "idea_id", None) not in kept]


def is_kept_from(conn: sqlite3.Connection, idea: Idea | None, who: Member | None) -> bool:
    """Whether this one idea is a present kept from this person."""
    if idea is None or who is None or not idea_store.is_gift(idea):
        return False
    return who.id in of_presents(conn, [idea], member_store.list_all(conn))[idea.id].ids


def visible_tasks(conn: sqlite3.Connection, found: list[Task], who: Member | None) -> list[Task]:
    """These to-dos without the ones about a present kept from this person."""
    about = {task.idea_id for task in found if task.idea_id}
    if not about or who is None:
        return found
    kept = kept_ids(conn, who) & about
    return [task for task in found if task.idea_id not in kept]
