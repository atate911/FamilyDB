"""What nearly every page reads first about the household: who is on the family list, the
colour slot each wears (`views.slot_map`), and the presents kept from the visitor
(`presents.kept_ids`). Read once a page, as one thing."""

from __future__ import annotations

import sqlite3
from typing import Any, NamedTuple

from familydb import presents
from familydb.store import members as member_store
from familydb.store.members import Member
from familydb.web import views


class Household(NamedTuple):
    people: list[Member]
    slots: dict[str, int]
    kept: Any  # the ideas kept from this visitor, as presents.kept_ids gives them


def read(conn: sqlite3.Connection, visitor_member: Member | None) -> Household:
    people = member_store.list_all(conn)
    return Household(people, views.slot_map(people), presents.kept_ids(conn, visitor_member))
