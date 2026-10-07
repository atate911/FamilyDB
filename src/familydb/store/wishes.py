"""The kids' wish lists, one row per ask. The rules for changing them live in wish_service."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.ideas import normalize_title

Occasion = Literal["christmas", "birthday"]
OCCASIONS: tuple[Occasion, ...] = ("christmas", "birthday")
Status = Literal["open", "granted", "declined", "withdrawn", "turned_away"]
Concern = Literal["rule", "sibling", "inappropriate", "too_many"]
Review = Literal["none", "offered", "asked"]
# What a change may set; the rest is bookkeeping or fixed at the start.
CHANGEABLE = frozenset(
    {
        "occasion",
        "title",
        "notes",
        "category",
        "topic",
        "rank",
        "status",
        "answer_note",
        "answered_by",
        "answered_at",
        "locked_until",
        "refusal_rung",
        "parent_review",
    }
)
MAX_TOPIC = 40

_SELECT = "SELECT * FROM wishes"


class Wish(BaseModel):
    id: int
    member_id: int
    occasion: Occasion | None = None
    title: str
    title_norm: str
    notes: str | None = None
    category: str | None = None
    topic: str
    rank: int = 0
    status: Status = "open"
    concern: Concern | None = None
    answer_note: str | None = None
    answered_by: int | None = None
    answered_at: str | None = None
    locked_until: str | None = None
    refusal_rung: int | None = None
    parent_review: Review = "none"
    idea_id: int | None = None
    source_message_id: int | None = None
    revision: int = 1
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Wish:
        return cls(**dict(row))


def normalize_topic(topic: str) -> str:
    """A topic as compared: folded like a title, cut short."""
    return normalize_title(topic)[:MAX_TOPIC].strip()


def insert(
    conn: sqlite3.Connection,
    *,
    member_id: int,
    title: str,
    topic: str,
    occasion: Occasion | None,
    rank: int,
    now: str,
    status: Status = "open",
    **fields: Any,
) -> Wish:
    unknown = set(fields) - {
        "notes",
        "category",
        "concern",
        "parent_review",
        "idea_id",
        "source_message_id",
    }
    if unknown:
        raise ValueError(f"unknown wish fields: {sorted(unknown)}")
    values = {
        "member_id": member_id,
        "title": title.strip(),
        "title_norm": normalize_title(title),
        "topic": normalize_topic(topic),
        "occasion": occasion,
        "rank": rank,
        "status": status,
        "created_at": now,
        "updated_at": now,
        **fields,
    }
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    cur = conn.execute(f"INSERT INTO wishes ({columns}) VALUES ({marks})", tuple(values.values()))
    wish = get(conn, int(cur.lastrowid or 0))
    assert wish is not None
    return wish


def get(conn: sqlite3.Connection, wish_id: int) -> Wish | None:
    row = conn.execute(f"{_SELECT} WHERE id = ?", (wish_id,)).fetchone()
    return Wish.from_row(row) if row else None


def update(conn: sqlite3.Connection, wish_id: int, changes: dict[str, Any], *, now: str) -> Wish:
    """Set these fields and bump the revision, so a form drawn before is refused."""
    unknown = set(changes) - CHANGEABLE
    if unknown:
        raise ValueError(f"unknown wish fields: {sorted(unknown)}")
    values = dict(changes)
    if "title" in values:
        values["title"] = str(values["title"]).strip()
        values["title_norm"] = normalize_title(values["title"])
    if "topic" in values:
        values["topic"] = normalize_topic(values["topic"])
    sets = ", ".join(f"{column} = ?" for column in values)
    conn.execute(
        f"UPDATE wishes SET {sets}, revision = revision + 1, updated_at = ? WHERE id = ?",
        (*values.values(), now, wish_id),
    )
    wish = get(conn, wish_id)
    assert wish is not None
    return wish


def open_list(conn: sqlite3.Connection, member_id: int, occasion: Occasion | None) -> list[Wish]:
    """One of her lists as ordered: open wishes, top first."""
    rows = conn.execute(
        f"{_SELECT} WHERE member_id = ? AND occasion IS ? AND status = 'open' ORDER BY rank, id",
        (member_id, occasion),
    )
    return [Wish.from_row(row) for row in rows]


def for_member(conn: sqlite3.Connection, member_id: int, *, limit: int = 200) -> list[Wish]:
    """Everything she asked for, newest first."""
    rows = conn.execute(
        f"{_SELECT} WHERE member_id = ? ORDER BY id DESC LIMIT ?", (member_id, limit)
    )
    return [Wish.from_row(row) for row in rows]


def day_of(conn: sqlite3.Connection, member_id: int, day: str) -> tuple[int, int]:
    """Her everyday asks that day, and her moves."""
    row = conn.execute(
        "SELECT asks, moves FROM wish_days WHERE member_id = ? AND day = ?", (member_id, day)
    ).fetchone()
    return (int(row[0]), int(row[1])) if row else (0, 0)


def count_day(
    conn: sqlite3.Connection, member_id: int, day: str, *, asks: int = 0, moves: int = 0
) -> None:
    conn.execute(
        "INSERT INTO wish_days (member_id, day, asks, moves) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (member_id, day) DO UPDATE SET asks = asks + excluded.asks, "
        "moves = moves + excluded.moves",
        (member_id, day, asks, moves),
    )


def mark_wording(conn: sqlite3.Connection, member_id: int, day: str, kind: str) -> None:
    """Note that her wording was nudged, or praised, that day."""
    column = {"nudge": "nudged", "praise": "praised"}[kind]
    conn.execute(
        f"INSERT INTO wish_days (member_id, day, {column}) VALUES (?, ?, 1) "
        f"ON CONFLICT (member_id, day) DO UPDATE SET {column} = 1",
        (member_id, day),
    )


def last_wording(conn: sqlite3.Connection, member_id: int, kind: str) -> str | None:
    """The last day her wording was nudged, or praised."""
    column = {"nudge": "nudged", "praise": "praised"}[kind]
    row = conn.execute(
        f"SELECT max(day) FROM wish_days WHERE member_id = ? AND {column} = 1", (member_id,)
    ).fetchone()
    return row[0] if row else None


def topics(conn: sqlite3.Connection, member_id: int, now: str) -> list[tuple[str, str | None]]:
    """Her topics as the bot is told them: locked ones on her everyday list (with unlock time),
    then open ones, each once."""
    locked = conn.execute(
        "SELECT topic, max(locked_until) FROM wishes WHERE member_id = ? AND occasion IS NULL "
        "AND status = 'declined' AND locked_until > ? GROUP BY topic ORDER BY min(id)",
        (member_id, now),
    ).fetchall()
    open_ = conn.execute(
        "SELECT topic FROM wishes WHERE member_id = ? AND status = 'open' "
        "GROUP BY topic ORDER BY min(rank), min(id)",
        (member_id,),
    ).fetchall()
    seen: dict[str, str | None] = {row[0]: row[1] for row in locked}
    for row in open_:
        seen.setdefault(row[0], None)
    return list(seen.items())


def renumber(conn: sqlite3.Connection, ordered: list[int]) -> None:
    """Rank these wishes 1, 2, 3... in order; the revision stays, so a move never stales a form."""
    for rank, wish_id in enumerate(ordered, start=1):
        conn.execute("UPDATE wishes SET rank = ? WHERE id = ?", (rank, wish_id))
