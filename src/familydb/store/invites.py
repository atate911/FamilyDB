"""Invitations that link somebody's Telegram to them (familydb/family.py). Only a hash of each
code is kept, so a database copy is no way in; one per person, a new one replaces it."""

from __future__ import annotations

import hashlib
import sqlite3

from pydantic import BaseModel


class Invite(BaseModel):
    code_hash: str
    member_id: int
    made_by: int | None = None
    made_at: str
    expires_at: str


def digest(code: str) -> str:
    """What is kept of a code; a plain hash will do for a long random code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def put(
    conn: sqlite3.Connection,
    member_id: int,
    code_hash: str,
    *,
    made_by: int | None,
    now: str,
    expires: str,
) -> None:

    conn.execute(
        "INSERT INTO telegram_invites (code_hash, member_id, made_by, made_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT (member_id) DO UPDATE SET "
        "code_hash = excluded.code_hash, made_by = excluded.made_by, "
        "made_at = excluded.made_at, expires_at = excluded.expires_at",
        (code_hash, member_id, made_by, now, expires),
    )


def find(conn: sqlite3.Connection, code_hash: str) -> Invite | None:
    row = conn.execute(
        "SELECT * FROM telegram_invites WHERE code_hash = ?", (code_hash,)
    ).fetchone()
    return Invite(**dict(row)) if row else None


def remove(conn: sqlite3.Connection, code_hash: str) -> None:
    conn.execute("DELETE FROM telegram_invites WHERE code_hash = ?", (code_hash,))


def forget_expired(conn: sqlite3.Connection, now: str) -> int:
    """Drop every invitation past its time; returns how many."""
    return conn.execute("DELETE FROM telegram_invites WHERE expires_at <= ?", (now,)).rowcount
