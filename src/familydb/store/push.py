"""Devices to tell, and the install's key for telling them (familydb/push.py)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from familydb.store.db import transaction


@dataclass(frozen=True)
class Device:
    member_id: int
    endpoint: str
    p256dh: str
    auth: str


def key(conn: sqlite3.Connection) -> str | None:
    """The key's secret, base64url, or None until it is made."""
    row = conn.execute("SELECT secret FROM push_key WHERE id = 1").fetchone()
    return row["secret"] if row else None


def public_key(conn: sqlite3.Connection) -> str | None:
    """What a browser subscribes with (applicationServerKey), base64url."""
    row = conn.execute("SELECT public FROM push_key WHERE id = 1").fetchone()
    return row["public"] if row else None


def save_key(conn: sqlite3.Connection, *, secret: str, public: str, now: str) -> None:
    with transaction(conn):
        conn.execute(
            "INSERT OR IGNORE INTO push_key (id, secret, public, created_at) VALUES (1, ?, ?, ?)",
            (secret, public, now),
        )


def subscribe(
    conn: sqlite3.Connection, member_id: int, *, endpoint: str, p256dh: str, auth: str, now: str
) -> None:
    """This device tells this person, whoever it told before. Call inside a transaction."""
    conn.execute(
        "INSERT INTO push_subscriptions (member_id, endpoint, p256dh, auth, created_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT (endpoint) DO UPDATE SET "
        "member_id = excluded.member_id, p256dh = excluded.p256dh, auth = excluded.auth",
        (member_id, endpoint, p256dh, auth, now),
    )


def unsubscribe(conn: sqlite3.Connection, member_id: int, endpoint: str) -> int:
    """This person's device tells nobody now. Call inside a transaction."""
    return conn.execute(
        "DELETE FROM push_subscriptions WHERE member_id = ? AND endpoint = ?",
        (member_id, endpoint),
    ).rowcount


def for_members(conn: sqlite3.Connection, member_ids: list[int]) -> list[Device]:
    if not member_ids:
        return []
    marks = ",".join("?" * len(member_ids))
    rows = conn.execute(
        f"SELECT member_id, endpoint, p256dh, auth FROM push_subscriptions "
        f"WHERE member_id IN ({marks}) ORDER BY id",
        member_ids,
    )
    return [Device(**dict(row)) for row in rows]


def count_for(conn: sqlite3.Connection, member_id: int) -> int:
    row = conn.execute(
        "SELECT count(*) FROM push_subscriptions WHERE member_id = ?", (member_id,)
    ).fetchone()
    return int(row[0])


def forget(conn: sqlite3.Connection, endpoint: str) -> None:
    """The push service says this device has gone."""
    with transaction(conn):
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def heard(conn: sqlite3.Connection, endpoint: str, now: str) -> None:
    with transaction(conn):
        conn.execute(
            "UPDATE push_subscriptions SET last_ok_at = ? WHERE endpoint = ?", (now, endpoint)
        )
