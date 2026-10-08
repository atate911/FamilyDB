"""Taking a forgotten place name out of what still holds it. A shared location is deleted after a
day (`member_locations`), but its name, said once by reverse geocode, went into the "location
shared" reply and into the words and results of the turns that followed. Each name given is kept
here with the reply that said it, and once the location is forgotten the name is replaced where it
was kept: the reply loses its parenthesis, the rest say `GONE`. Nothing else is touched, and
nothing is read by a model."""

from __future__ import annotations

import json
import sqlite3

GONE = "[place forgotten]"
# A shorter name would match too much of what others said to be taken out of it by sight.
LEAST_CHARS = 3

# Where a name went besides the reply: (table, column, when the row was made, kept as JSON).
HELD_IN = (
    ("ai_texts", "request", "created_at", False),
    ("ai_texts", "reply", "created_at", False),
    ("tool_calls", "output", "created_at", True),
    ("suggestions", "candidates", "asked_at", True),
)


def note(
    conn: sqlite3.Connection,
    member_id: int,
    label: str,
    *,
    at: str,
    message_id: int | None = None,
) -> None:
    """A place name was given to somebody's location, and `message_id` said it, if a reply did."""
    conn.execute(
        "INSERT INTO place_names (member_id, label, named_at, message_id) VALUES (?, ?, ?, ?)",
        (member_id, label, at, message_id),
    )


def forget_names(conn: sqlite3.Connection, before: str) -> int:
    """Take out the names given before a UTC timestamp, unless a location still carries one;
    returns how many were taken out. Call inside a transaction, after old locations are deleted."""
    rows = conn.execute(
        "SELECT * FROM place_names WHERE named_at < ? ORDER BY id", (before,)
    ).fetchall()
    gone = 0
    for row in rows:
        if conn.execute(
            "SELECT 1 FROM member_locations WHERE label = ?", (row["label"],)
        ).fetchone():
            continue
        _scrub(conn, row)
        gone += 1
    return gone


def forget_of_member(conn: sqlite3.Connection, member_id: int) -> int:
    """Every name given to somebody's locations, at once (taking them off for good). Call inside a
    transaction."""
    rows = conn.execute("SELECT * FROM place_names WHERE member_id = ?", (member_id,)).fetchall()
    for row in rows:
        _scrub(conn, row)
    return len(rows)


def _scrub(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    label = row["label"]
    if row["message_id"] is not None:
        said = conn.execute("SELECT text FROM messages WHERE id = ?", (row["message_id"],))
        found = said.fetchone()
        if found is not None and label in found["text"]:
            text = found["text"].replace(f" ({label})", "").replace(label, GONE)
            conn.execute("UPDATE messages SET text = ? WHERE id = ?", (text, row["message_id"]))
    quoted = json.dumps(label, ensure_ascii=False)[1:-1]  # as it reads inside a JSON string
    for table, column, made, as_json in HELD_IN if len(label) >= LEAST_CHARS else ():
        for form in dict.fromkeys((quoted,) if as_json else (label, quoted)):
            conn.execute(
                f"UPDATE {table} SET {column} = replace({column}, ?, ?) "
                f"WHERE {made} >= ? AND instr({column}, ?) > 0",
                (form, GONE, row["named_at"], form),
            )
    conn.execute("DELETE FROM place_names WHERE id = ?", (row["id"],))
