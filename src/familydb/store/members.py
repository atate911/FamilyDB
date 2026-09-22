"""Family members: the people who message the bot, plus kids who don't."""

from __future__ import annotations

import sqlite3
from typing import Literal

from pydantic import BaseModel

from familydb.store.db import utcnow_iso

Role = Literal["admin", "member", "kid"]
ROLES: tuple[str, ...] = ("admin", "member", "kid")


# Channels with no account of their own behind them: the console, where whoever is at the
# keyboard says who they are, and the web page, which is behind one shared family password and
# so has to ask. Both name a member by display name instead of a channel user id.
BY_NAME = frozenset({"console", "web"})


class Member(BaseModel):
    id: int
    display_name: str
    role: Role
    channel: str | None = None
    channel_user_id: str | None = None
    active: bool = True
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Member:
        return cls(**dict(row))


def add(
    conn: sqlite3.Connection,
    display_name: str,
    role: Role = "member",
    *,
    channel: str | None = None,
    channel_user_id: str | None = None,
    now: str | None = None,
) -> Member:
    cur = conn.execute(
        "INSERT INTO members (display_name, role, channel, channel_user_id, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (display_name.strip(), role, channel, channel_user_id, now or utcnow_iso()),
    )
    member = get(conn, int(cur.lastrowid or 0))
    assert member is not None
    return member


def get(conn: sqlite3.Connection, member_id: int) -> Member | None:
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    return Member.from_row(row) if row else None


def list_all(conn: sqlite3.Connection, *, active_only: bool = True) -> list[Member]:
    sql = "SELECT * FROM members" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
    return [Member.from_row(row) for row in conn.execute(sql)]


def find_by_name(conn: sqlite3.Connection, name: str) -> Member | None:
    row = conn.execute(
        "SELECT * FROM members WHERE active = 1 AND lower(display_name) = lower(?)",
        (name.strip(),),
    ).fetchone()
    return Member.from_row(row) if row else None


def resolve(conn: sqlite3.Connection, channel: str, channel_user_id: str) -> Member | None:
    """Who is messaging. Some channels identify people by display name rather than by an id."""
    if channel in BY_NAME:
        return find_by_name(conn, channel_user_id)
    row = conn.execute(
        "SELECT * FROM members WHERE active = 1 AND channel = ? AND channel_user_id = ?",
        (channel, channel_user_id),
    ).fetchone()
    return Member.from_row(row) if row else None


def set_active(conn: sqlite3.Connection, member_id: int, active: bool) -> None:
    conn.execute("UPDATE members SET active = ? WHERE id = ?", (int(active), member_id))
