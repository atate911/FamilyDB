"""Memories: what the family has told the bot about itself (docs/MEMORY.md).

Rows are never deleted. A corrected memory is marked `replaced` and points at what replaced it;
a forgotten one keeps its words, marked `forgotten`, so the same thing said before the forgetting
can be recognised and not saved again. Which memories a message needs is chosen elsewhere
(`familydb/memory.py`); the rules for changing them are the `remember` tool's.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from typing import Literal

from pydantic import BaseModel

from familydb.store.db import utcnow_iso

Category = Literal["food", "activities", "places", "health", "routine", "other"]
Status = Literal["active", "replaced", "forgotten"]

_SELECT = (
    "SELECT r.*, about.display_name AS about_name, said.display_name AS said_by_name, "
    "gone.display_name AS forgotten_by_name, m.text AS source_text, "
    "m.received_at AS source_at FROM memories r "
    "LEFT JOIN members about ON about.id = r.member_id "
    "LEFT JOIN members said ON said.id = r.said_by "
    "LEFT JOIN members gone ON gone.id = r.forgotten_by "
    "LEFT JOIN messages m ON m.id = r.source_message_id"
)


class Memory(BaseModel):
    id: int
    member_id: int | None = None
    about_name: str | None = None  # None: the whole family
    category: Category = "other"
    fact: str
    fact_norm: str
    firm: bool = False
    inferred: bool = False
    until: str | None = None
    status: Status = "active"
    replaced_by: int | None = None
    source_message_id: int | None = None
    source_text: str | None = None
    source_at: str | None = None
    said_by: int | None = None
    said_by_name: str | None = None
    created_at: str
    updated_at: str
    forgotten_at: str | None = None
    forgotten_by: int | None = None
    forgotten_by_name: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Memory:
        return cls(**dict(row))


def normalize(fact: str) -> str:
    """Casefolded, punctuation-free, single-spaced: "Vegetarian!" and "vegetarian" are one."""
    return " ".join(re.sub(r"[^\w\s]", " ", fact.casefold()).split())


def insert(
    conn: sqlite3.Connection,
    *,
    member_id: int | None,
    category: str,
    fact: str,
    firm: bool,
    inferred: bool,
    until: str | None,
    source_message_id: int | None,
    said_by: int | None,
    now: str | None = None,
) -> Memory:
    stamp = now or utcnow_iso()
    cur = conn.execute(
        "INSERT INTO memories (member_id, category, fact, fact_norm, firm, inferred, until, "
        "source_message_id, said_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            member_id,
            category,
            fact.strip(),
            normalize(fact),
            int(firm),
            int(inferred),
            until,
            source_message_id,
            said_by,
            stamp,
            stamp,
        ),
    )
    memory = get(conn, int(cur.lastrowid or 0))
    assert memory is not None
    return memory


def get(conn: sqlite3.Connection, memory_id: int) -> Memory | None:
    row = conn.execute(f"{_SELECT} WHERE r.id = ?", (memory_id,)).fetchone()
    return Memory.from_row(row) if row else None


def matching(
    conn: sqlite3.Connection, member_id: int | None, fact: str, status: Status
) -> Memory | None:
    """The newest memory about the same person saying the same thing, in this status."""
    row = conn.execute(
        f"{_SELECT} WHERE r.member_id IS ? AND r.fact_norm = ? AND r.status = ? "
        "ORDER BY r.id DESC LIMIT 1",
        (member_id, normalize(fact), status),
    ).fetchone()
    return Memory.from_row(row) if row else None


def firm_up(conn: sqlite3.Connection, memory_id: int, *, firm: bool, now: str) -> None:
    """Said again, and outright this time: no longer a guess, and a must if it now is one."""
    conn.execute(
        "UPDATE memories SET inferred = 0, firm = max(firm, ?), updated_at = ? WHERE id = ?",
        (int(firm), now, memory_id),
    )


def replace(conn: sqlite3.Connection, memory_id: int, *, by: int, now: str) -> None:
    conn.execute(
        "UPDATE memories SET status = 'replaced', replaced_by = ?, updated_at = ? WHERE id = ?",
        (by, now, memory_id),
    )


def forget(conn: sqlite3.Connection, memory_id: int, *, by: int | None, now: str) -> None:
    conn.execute(
        "UPDATE memories SET status = 'forgotten', forgotten_at = ?, forgotten_by = ?, "
        "updated_at = ? WHERE id = ?",
        (now, by, now, memory_id),
    )


def active(conn: sqlite3.Connection, *, today: date) -> list[Memory]:
    """Every memory in force today, oldest first."""
    rows = conn.execute(
        f"{_SELECT} WHERE r.status = 'active' AND (r.until IS NULL OR r.until >= ?) ORDER BY r.id",
        (today.isoformat(),),
    )
    return [Memory.from_row(row) for row in rows]


def list_all(conn: sqlite3.Connection) -> list[Memory]:
    """Every memory there has been, newest first, for the page."""
    return [Memory.from_row(row) for row in conn.execute(f"{_SELECT} ORDER BY r.id DESC")]
