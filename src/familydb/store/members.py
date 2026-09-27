"""Family members: everybody the bot knows, by name and role (familydb/roles.py)."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

# Re-exported: everything that knows a member knows their role by these names.
from familydb.roles import ROLES as ROLES
from familydb.roles import Role as Role
from familydb.store.db import utcnow_iso

# Channels with no account of their own on another service behind them: the console, where
# whoever is at the keyboard says who they are, and the web page, which names whoever is signed
# in (or, while the family still shares one password, whoever they said they were). Both name a
# member by display name instead of a channel user id.
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
    role: Role = "parent",
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


def update_profile(
    conn: sqlite3.Connection,
    member_id: int,
    *,
    display_name: str,
    role: Role,
    active: bool,
    channel: str | None,
    channel_user_id: str | None,
) -> Member | None:
    """Change who somebody is to the bot, keeping their id and so everything they ever said."""
    conn.execute(
        "UPDATE members SET display_name = ?, role = ?, active = ?, channel = ?, "
        "channel_user_id = ? WHERE id = ?",
        (display_name.strip(), role, int(active), channel, channel_user_id, member_id),
    )
    return get(conn, member_id)


# Every column that points at a member, and what taking somebody off the list for good does to
# it, as the family chose: what was theirs alone goes with them (how they signed in, where they
# were, a link for their Telegram, what she remembers about them), and what they said and did
# stays, with nobody's name on it, so a conversation still reads. `erase` works through this
# list, and a test holds it to the schema: a table added later that points at a member has to
# be named here, or taking somebody off would fail on it.
POINTING_AT = {
    ("app_settings", "updated_by"): "unname",
    ("ideas", "suggested_by"): "unname",
    ("member_locations", "member_id"): "delete",
    ("member_logins", "member_id"): "delete",
    ("member_logins", "set_by"): "unname",
    ("memories", "forgotten_by"): "unname",
    ("memories", "member_id"): "delete",
    ("memories", "said_by"): "unname",
    ("messages", "member_id"): "unname",
    ("outcomes", "recorded_by"): "unname",
    ("plans", "created_by"): "unname",
    ("settings_log", "changed_by"): "unname",
    ("suggestions", "asked_by"): "unname",
    ("tasks", "owner_id"): "unname",
    ("telegram_invites", "made_by"): "unname",
    ("telegram_invites", "member_id"): "delete",
}


def erase(conn: sqlite3.Connection, member_id: int) -> dict[str, int]:
    """Take a member off the list for good, as POINTING_AT says. Call inside a transaction.

    Returns how many rows each table lost or had the name taken off, for the log.
    """
    touched: dict[str, int] = {}
    # A memory about them may have replaced another, or been replaced by one that stays.
    conn.execute(
        "UPDATE memories SET replaced_by = NULL WHERE replaced_by IN "
        "(SELECT id FROM memories WHERE member_id = ?)",
        (member_id,),
    )
    for (table, column), how in sorted(POINTING_AT.items(), key=lambda item: item[1] == "delete"):
        if how == "unname":
            sql = f"UPDATE {table} SET {column} = NULL WHERE {column} = ?"
        else:
            sql = f"DELETE FROM {table} WHERE {column} = ?"
        count = conn.execute(sql, (member_id,)).rowcount
        if count:
            touched[f"{table}.{column}"] = count
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    return touched
