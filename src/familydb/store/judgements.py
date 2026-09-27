"""The `judgements` table: questions for a stronger model, and what came of them."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel

from familydb.store.db import from_json, to_json


class Judgement(BaseModel):
    id: int
    kind: str
    subject: str
    facts: dict[str, Any]
    asked_at: str
    urgent: bool = False
    tries: int = 0
    answered_at: str | None = None
    answer: dict[str, Any] | None = None
    reason: str | None = None
    outcome: str | None = None


def _row(row: sqlite3.Row) -> Judgement:
    data = dict(row)
    data["facts"] = from_json(data["facts"]) or {}
    data["answer"] = from_json(data["answer"]) if data["answer"] else None
    return Judgement(**data)


def file(
    conn: sqlite3.Connection,
    kind: str,
    subject: str,
    facts: dict[str, Any],
    *,
    now: str,
    urgent: bool = False,
) -> bool:
    """File a question, once for each kind and subject: one still open takes the newer facts
    (a model released since, say), one answered stays as it was. True when it was not there.
    Call inside a transaction."""
    there = conn.execute(
        "SELECT 1 FROM judgements WHERE kind = ? AND subject = ?", (kind, subject)
    ).fetchone()
    conn.execute(
        "INSERT INTO judgements (kind, subject, facts, asked_at, urgent) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (kind, subject) DO UPDATE SET facts = excluded.facts "
        "WHERE judgements.answered_at IS NULL",
        (kind, subject, to_json(facts), now, int(urgent)),
    )
    return there is None


def open_questions(conn: sqlite3.Connection) -> list[Judgement]:
    rows = conn.execute(
        "SELECT * FROM judgements WHERE answered_at IS NULL ORDER BY asked_at, id"
    ).fetchall()
    return [_row(row) for row in rows]


def answered(
    conn: sqlite3.Connection,
    judgement_id: int,
    *,
    answer: dict[str, Any] | None,
    reason: str | None,
    outcome: str,
    now: str,
) -> None:
    conn.execute(
        "UPDATE judgements SET answered_at = ?, answer = ?, reason = ?, outcome = ? WHERE id = ?",
        (now, to_json(answer) if answer is not None else None, reason, outcome, judgement_id),
    )


def tried(conn: sqlite3.Connection, judgement_id: int, *, now: str) -> int:
    """No answer came back: it waits for the next evening, however urgent it was. Returns how
    many times it has been asked."""
    conn.execute(
        "UPDATE judgements SET tries = tries + 1, asked_at = ?, urgent = 0 WHERE id = ?",
        (now, judgement_id),
    )
    row = conn.execute("SELECT tries FROM judgements WHERE id = ?", (judgement_id,)).fetchone()
    return int(row["tries"]) if row else 0


def recent(conn: sqlite3.Connection, *, since: str, limit: int = 20) -> list[Judgement]:
    rows = conn.execute(
        "SELECT * FROM judgements WHERE coalesce(answered_at, asked_at) >= ? "
        "ORDER BY coalesce(answered_at, asked_at) DESC, id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [_row(row) for row in rows]


def choices(conn: sqlite3.Connection, kind: str) -> dict[str, Judgement]:
    """The answered questions of a kind, by subject, that an answer was accepted for."""
    rows = conn.execute(
        "SELECT * FROM judgements WHERE kind = ? AND answer IS NOT NULL", (kind,)
    ).fetchall()
    return {row["subject"]: _row(row) for row in rows}


def last_answered(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT max(answered_at) FROM judgements").fetchone()
    return row[0] if row else None


def forget_before(conn: sqlite3.Connection, when: str) -> int:
    """Questions filed long ago: answered, or never answered (the family had it off)."""
    return conn.execute("DELETE FROM judgements WHERE asked_at < ?", (when,)).rowcount
