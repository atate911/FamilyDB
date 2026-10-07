"""Stage: record what was suggested and why."""

from __future__ import annotations

import sqlite3

from familydb.store import suggestions
from familydb.store.db import transaction
from familydb.suggest.types import Candidate, WebFind


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
    again brings up the others (`suggestions.recently_suggested`)."""
    with transaction(conn):
        row = suggestions.insert(
            conn,
            asked_by=asked_by,
            window_start=window_start,
            window_end=window_end,
            candidates=[
                {**c.model_dump(mode="json"), "shown": c.idea_id in shown} for c in candidates
            ],
            web_finds=[f.model_dump(mode="json") for f in finds],
            now=now,
        )
    return row.id
