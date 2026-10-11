"""Stage: record what was suggested and why."""

from __future__ import annotations

import sqlite3

from familydb.store import suggestions
from familydb.store.db import transaction
from familydb.suggest.types import Candidate, WebFind


def _rows(candidates: list[Candidate], shown: set[int]) -> list[dict]:
    return [{**c.model_dump(mode="json"), "shown": c.idea_id in shown} for c in candidates]


def log_suggestion(
    conn: sqlite3.Connection,
    *,
    asked_by: int | None,
    window_start: str | None,
    window_end: str | None,
    candidates: list[Candidate],
    shown: set[int],
    finds: list[WebFind],
    now: str,
) -> int:
    """Every verdict, and which the model was shown: only those count as suggested, so asking
    again brings up the others (`taken.sinking`)."""
    with transaction(conn):
        row = suggestions.insert(
            conn,
            asked_by=asked_by,
            window_start=window_start,
            window_end=window_end,
            candidates=_rows(candidates, shown),
            web_finds=[f.model_dump(mode="json") for f in finds],
            now=now,
        )
    return row.id


def log_reframed(
    conn: sqlite3.Connection,
    suggestion_id: int,
    *,
    window_start: str | None,
    window_end: str | None,
    candidates: list[Candidate],
    shown: set[int],
    finds: list[WebFind],
) -> None:
    """The same question asked again in the framing the stronger call corrected
    (suggest/choosing.py): its row now says what the family was shown."""
    with transaction(conn):
        suggestions.reframe(
            conn,
            suggestion_id,
            window_start=window_start,
            window_end=window_end,
            candidates=_rows(candidates, shown),
            web_finds=[f.model_dump(mode="json") for f in finds],
        )
