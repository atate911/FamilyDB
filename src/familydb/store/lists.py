"""The family's lists and what is on them (tools/lists.py)."""

from __future__ import annotations

import re
import sqlite3

from pydantic import BaseModel

# Words that say nothing of what the thing is: "some milk", "more eggs" are milk and eggs.
FILLER = re.compile(r"^(?:(?:a|an|some|more|the|another|extra)\s+)+")


class Item(BaseModel):
    id: int
    list_id: int
    text: str
    ticked_at: str | None = None
    added_at: str
    # Who put it there (None when nobody now on the family list did); the Lists page names them.
    added_by: int | None = None


def fold(text: str) -> str:
    """The same thing however it is written, for keeping it on a list once."""
    plain = " ".join(text.casefold().replace("\u2019", "'").split()).strip(" .,;:!?")
    return FILLER.sub("", plain)


def name_of(text: str) -> str:
    return " ".join(text.casefold().split()) or "shopping"


def list_id(conn: sqlite3.Connection, name: str, now: str) -> int:
    """The list by its name, made the first time it is used. Call inside a transaction."""
    conn.execute("INSERT OR IGNORE INTO lists (name, created_at) VALUES (?, ?)", (name, now))
    row = conn.execute("SELECT id FROM lists WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def find(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM lists WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None


def name_by_id(conn: sqlite3.Connection, list_ref: int) -> str | None:
    row = conn.execute("SELECT name FROM lists WHERE id = ?", (list_ref,)).fetchone()
    return row["name"] if row else None


def names(conn: sqlite3.Connection) -> list[str]:
    return [row["name"] for row in conn.execute("SELECT name FROM lists ORDER BY id")]


def items(conn: sqlite3.Connection, list_ref: int) -> list[Item]:
    """What is on a list: still to get first, in the order added, then what was ticked."""
    rows = conn.execute(
        "SELECT id, list_id, text, ticked_at, added_at, added_by FROM list_items WHERE list_id = ? "
        "ORDER BY ticked_at IS NOT NULL, ticked_at DESC, id",
        (list_ref,),
    )
    return [Item(**dict(row)) for row in rows]


def item(conn: sqlite3.Connection, item_id: int) -> Item | None:
    row = conn.execute(
        "SELECT id, list_id, text, ticked_at, added_at, added_by FROM list_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    return Item(**dict(row)) if row else None


def by_text(conn: sqlite3.Connection, list_ref: int, text: str) -> Item | None:
    row = conn.execute(
        "SELECT id, list_id, text, ticked_at, added_at, added_by FROM list_items "
        "WHERE list_id = ? AND folded = ?",
        (list_ref, fold(text)),
    ).fetchone()
    return Item(**dict(row)) if row else None


def add(
    conn: sqlite3.Connection, list_ref: int, text: str, *, by: int | None, now: str
) -> Item | None:
    """Put a thing on a list; None when it is there already (ticked, it is unticked: wanted
    again). Call inside a transaction."""
    there = by_text(conn, list_ref, text)
    if there is not None:
        if there.ticked_at is not None:
            set_ticked(conn, there.id, by=None, now=None)
            return item(conn, there.id)
        return None
    cur = conn.execute(
        "INSERT INTO list_items (list_id, text, folded, added_by, added_at) VALUES (?, ?, ?, ?, ?)",
        (list_ref, text.strip(), fold(text), by, now),
    )
    return item(conn, int(cur.lastrowid or 0))


def set_ticked(conn: sqlite3.Connection, item_id: int, *, by: int | None, now: str | None) -> None:
    """Ticked (bought) at `now`, or unticked with None. Call inside a transaction."""
    conn.execute(
        "UPDATE list_items SET ticked_at = ?, ticked_by = ? WHERE id = ?",
        (now, by if now else None, item_id),
    )


def remove(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute("DELETE FROM list_items WHERE id = ?", (item_id,))


def clear_ticked(conn: sqlite3.Connection, list_ref: int) -> int:
    return conn.execute(
        "DELETE FROM list_items WHERE list_id = ? AND ticked_at IS NOT NULL", (list_ref,)
    ).rowcount
