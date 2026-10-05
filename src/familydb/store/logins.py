"""Each person's own web password, hashed, apart from `members` so a hash never travels with a
member record into the prompt. Who may sign in is their role's permission (familydb/roles.py),
so every read that lets somebody in checks the member as well as the row."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from familydb import roles
from familydb.store.members import Member


class Login(BaseModel):
    member_id: int
    password_hash: str
    temporary: bool  # a starting password somebody else made up, to be replaced at first use
    set_at: str
    set_by: int | None = None


class SignIn(BaseModel):
    """Somebody who may sign in, and the password they sign in with."""

    member: Member
    login: Login


# Everybody on the list with a password; `_may` asks roles.py per row.
_SIGNS_IN = (
    "SELECT m.*, l.password_hash, l.temporary, l.set_at, l.set_by FROM members m "
    "JOIN member_logins l ON l.member_id = m.id WHERE m.active = 1"
)


def _may(row: sqlite3.Row) -> bool:
    return roles.may(row["role"], "sign_in")


def _sign_in(row: sqlite3.Row) -> SignIn:
    data = dict(row)
    login = Login(
        member_id=data["id"],
        password_hash=data.pop("password_hash"),
        temporary=bool(data.pop("temporary")),
        set_at=data.pop("set_at"),
        set_by=data.pop("set_by"),
    )
    return SignIn(member=Member(**data), login=login)


def get(conn: sqlite3.Connection, member_id: int) -> Login | None:
    """The stored row, whether or not the person may use it."""
    row = conn.execute("SELECT * FROM member_logins WHERE member_id = ?", (member_id,)).fetchone()
    return Login(**dict(row)) if row else None


def by_member(conn: sqlite3.Connection) -> dict[int, Login]:
    """Every stored row, by member."""
    rows = conn.execute("SELECT * FROM member_logins ORDER BY member_id")
    return {row["member_id"]: Login(**dict(row)) for row in rows}


def signing_in(conn: sqlite3.Connection, member_id: int) -> SignIn | None:
    """This person and their password, if they may sign in."""
    row = conn.execute(_SIGNS_IN + " AND m.id = ?", (member_id,)).fetchone()
    return _sign_in(row) if row and _may(row) else None


def by_name(conn: sqlite3.Connection, name: str) -> SignIn | None:
    """Whoever signs in by this name, ignoring case and spacing; None when nobody (or two) does.
    Compared in Python: SQL lower() leaves non-ASCII letters alone ("émile" vs Émile)."""
    wanted = " ".join(name.split()).casefold()
    if not wanted:
        return None
    found = [
        row
        for row in conn.execute(_SIGNS_IN)
        if row["display_name"].casefold() == wanted and _may(row)
    ]
    return _sign_in(found[0]) if len(found) == 1 else None


def admins_signing_in(conn: sqlite3.Connection) -> list[Member]:
    """The admins who can sign in as themselves, oldest first."""
    rows = conn.execute(_SIGNS_IN + " AND m.role = 'admin' ORDER BY m.id")
    return [_sign_in(row).member for row in rows if _may(row)]


def admin_can_sign_in(conn: sqlite3.Connection) -> bool:
    """Whether some admin signs in as themselves; from then on the shared password opens nothing."""
    return any(_may(row) for row in conn.execute(_SIGNS_IN + " AND m.role = 'admin'"))


def put(
    conn: sqlite3.Connection,
    member_id: int,
    password_hash: str,
    *,
    temporary: bool,
    now: str,
    set_by: int | None = None,
) -> None:
    """Store somebody's password, replacing the one they had."""
    conn.execute(
        "INSERT INTO member_logins (member_id, password_hash, temporary, set_at, set_by) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(member_id) DO UPDATE SET "
        "password_hash = excluded.password_hash, temporary = excluded.temporary, "
        "set_at = excluded.set_at, set_by = excluded.set_by",
        (member_id, password_hash, int(temporary), now, set_by),
    )


def remove(conn: sqlite3.Connection, member_id: int) -> bool:
    return conn.execute("DELETE FROM member_logins WHERE member_id = ?", (member_id,)).rowcount > 0
