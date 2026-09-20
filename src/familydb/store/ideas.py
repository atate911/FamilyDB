"""Ideas: the things the family might do one day."""

from __future__ import annotations

import difflib
import re
import sqlite3
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel

from familydb.store.db import from_json, to_json, utcnow_iso

KIND_SUGGESTIONS: tuple[str, ...] = (
    "restaurant",
    "activity",
    "outing",
    "day_trip",
    "trip",
    "show",
    "event",
    "seasonal",
    "home",
    "other",
)
Setting = Literal["indoor", "outdoor", "either"]
Weather = Literal["any", "dry", "warm", "snow"]
Status = Literal["idea", "planned", "done", "dropped"]
Enrichment = Literal["pending", "done", "failed", "skipped"]

JSON_FIELDS: tuple[str, ...] = ("participants", "tags", "seasons")
EDITABLE_FIELDS = frozenset(
    {
        "kind",
        "title",
        "description",
        "participants",
        "location_name",
        "url",
        "tags",
        "setting",
        "seasons",
        "weather",
        "duration_min",
        "duration_max",
        "cost_level",
        "needs_booking",
        "lead_time_days",
        "status",
        "place_id",
        "enrichment",
        "enriched_at",
        "enrichment_note",
    }
)
INSERT_FIELDS = EDITABLE_FIELDS | {"suggested_by", "source_message_id"}

_SELECT = (
    "SELECT i.*, m.display_name AS suggested_by_name "
    "FROM ideas i LEFT JOIN members m ON m.id = i.suggested_by"
)


class Idea(BaseModel):
    id: int
    kind: str
    title: str
    description: str | None = None
    participants: list[str] = []
    location_name: str | None = None
    url: str | None = None
    tags: list[str] = []
    setting: Setting = "either"
    seasons: list[str] = []
    weather: Weather = "any"
    duration_min: int | None = None
    duration_max: int | None = None
    cost_level: int | None = None
    needs_booking: bool = False
    lead_time_days: int | None = None
    status: Status = "idea"
    place_id: int | None = None
    enrichment: Enrichment = "pending"
    enriched_at: str | None = None
    enrichment_note: str | None = None
    suggested_by: int | None = None
    suggested_by_name: str | None = None
    source_message_id: int | None = None
    times_done: int = 0
    last_done_at: str | None = None
    avg_rating: float | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Idea:
        data = dict(row)
        for key in JSON_FIELDS:
            data[key] = from_json(data.get(key), [])
        return cls(**data)


def normalize_title(title: str) -> str:
    """Casefolded, punctuation-free, single-spaced form used for duplicate checks."""
    return " ".join(re.sub(r"[^\w\s]", " ", title.casefold()).split())


def fts_query(text: str) -> str | None:
    """Turn free text into a safe FTS5 query: quoted tokens joined with OR."""
    tokens = re.findall(r"\w+", text)
    return " OR ".join(f'"{token}"' for token in tokens) or None


def _encode(values: dict[str, Any]) -> dict[str, Any]:
    out = dict(values)
    if "kind" in out and out["kind"] is not None:
        out["kind"] = str(out["kind"]).strip().lower()
    if "title" in out and out["title"] is not None:
        out["title"] = str(out["title"]).strip()
        out["title_norm"] = normalize_title(out["title"])
    if out.get("tags") is not None:
        out["tags"] = sorted({str(t).strip().lower() for t in out["tags"] if str(t).strip()})
    for key in JSON_FIELDS:
        if key in out and out[key] is not None:
            items = [str(item).strip() for item in out[key] if str(item).strip()]
            out[key] = to_json(items)
    if "needs_booking" in out and out["needs_booking"] is not None:
        out["needs_booking"] = int(bool(out["needs_booking"]))
    return out


def insert(
    conn: sqlite3.Connection, *, title: str, kind: str, now: str | None = None, **fields: Any
) -> Idea:
    unknown = set(fields) - INSERT_FIELDS
    if unknown:
        raise ValueError(f"unknown idea fields: {sorted(unknown)}")
    stamp = now or utcnow_iso()
    data = _encode({"title": title, "kind": kind, **fields})
    data["created_at"] = stamp
    data["updated_at"] = stamp
    columns = list(data)
    cur = conn.execute(
        f"INSERT INTO ideas ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        [data[column] for column in columns],
    )
    idea = get(conn, int(cur.lastrowid or 0))
    assert idea is not None
    return idea


def update(
    conn: sqlite3.Connection, idea_id: int, changes: dict[str, Any], *, now: str | None = None
) -> Idea | None:
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"unknown idea fields: {sorted(unknown)}")
    data = _encode(changes)
    data["updated_at"] = now or utcnow_iso()
    assignments = ", ".join(f"{column} = ?" for column in data)
    conn.execute(f"UPDATE ideas SET {assignments} WHERE id = ?", [*data.values(), idea_id])
    return get(conn, idea_id)


def get(conn: sqlite3.Connection, idea_id: int) -> Idea | None:
    row = conn.execute(f"{_SELECT} WHERE i.id = ?", (idea_id,)).fetchone()
    return Idea.from_row(row) if row else None


def list_for_prompt(conn: sqlite3.Connection) -> list[Idea]:
    """Every idea the model should know about, oldest first. Dropped ideas are left out."""
    return list_all(conn, include_dropped=False)


def pending_enrichment(conn: sqlite3.Connection, *, limit: int) -> list[Idea]:
    """Ideas waiting for a place lookup, oldest first."""
    rows = conn.execute(
        f"{_SELECT} WHERE i.enrichment = 'pending' AND i.status != 'dropped' ORDER BY i.id LIMIT ?",
        (limit,),
    )
    return [Idea.from_row(row) for row in rows]


def requeue_enrichment(
    conn: sqlite3.Connection, idea_ids: Iterable[int], *, now: str | None = None
) -> int:
    """Put ideas back in the lookup queue (stale details). Returns how many changed."""
    ids = [int(i) for i in idea_ids]
    if not ids:
        return 0
    placeholders = ", ".join("?" for _ in ids)
    cur = conn.execute(
        f"UPDATE ideas SET enrichment = 'pending', updated_at = ? "
        f"WHERE id IN ({placeholders}) AND enrichment != 'pending'",
        [now or utcnow_iso(), *ids],
    )
    return int(cur.rowcount)


def list_all(conn: sqlite3.Connection, *, include_dropped: bool = False) -> list[Idea]:
    where = "" if include_dropped else " WHERE i.status != 'dropped'"
    rows = conn.execute(f"{_SELECT}{where} ORDER BY i.id")
    return [Idea.from_row(row) for row in rows]


def search(
    conn: sqlite3.Connection,
    *,
    text: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    participant: str | None = None,
    setting: str | None = None,
    max_duration: int | None = None,
    max_cost: int | None = None,
    tags: list[str] | None = None,
    exclude_done_within_days: int | None = None,
    today: date | None = None,
    limit: int = 50,
) -> list[Idea]:
    """Filtered ideas. No filters returns everything that isn't dropped."""
    where: list[str] = []
    params: list[Any] = []
    if kind:
        where.append("i.kind = ?")
        params.append(kind.strip().lower())
    if status:
        where.append("i.status = ?")
        params.append(status)
    else:
        where.append("i.status != 'dropped'")
    if setting and setting != "either":
        where.append("(i.setting = ? OR i.setting = 'either')")
        params.append(setting)
    if max_duration is not None:
        where.append("(i.duration_min IS NULL OR i.duration_min <= ?)")
        params.append(max_duration)
    if max_cost is not None:
        where.append("(i.cost_level IS NULL OR i.cost_level <= ?)")
        params.append(max_cost)
    if participant:
        where.append(
            "EXISTS (SELECT 1 FROM json_each(i.participants) WHERE lower(value) = lower(?))"
        )
        params.append(participant.strip())
    for tag in tags or []:
        where.append("EXISTS (SELECT 1 FROM json_each(i.tags) WHERE value = ?)")
        params.append(tag.strip().lower())
    if exclude_done_within_days is not None and today is not None:
        cutoff = (today - timedelta(days=exclude_done_within_days)).isoformat()
        where.append("(i.last_done_at IS NULL OR i.last_done_at < ?)")
        params.append(cutoff)

    order = "i.id"
    if text and text.strip():
        query = fts_query(text)
        ids: list[int] | None = None
        if query:
            try:
                ids = [
                    int(row[0])
                    for row in conn.execute(
                        "SELECT rowid FROM ideas_fts WHERE ideas_fts MATCH ? "
                        "ORDER BY rank LIMIT 200",
                        (query,),
                    )
                ]
            except sqlite3.OperationalError:
                ids = None
        if ids is None:
            like = f"%{text.strip()}%"
            where.append("(i.title LIKE ? OR i.description LIKE ? OR i.location_name LIKE ?)")
            params.extend([like, like, like])
        elif not ids:
            return []
        else:
            where.append(f"i.id IN ({', '.join('?' for _ in ids)})")
            params.extend(ids)
            ranking = " ".join(f"WHEN {idea_id} THEN {n}" for n, idea_id in enumerate(ids))
            order = f"CASE i.id {ranking} END"

    sql = f"{_SELECT} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?"
    params.append(limit)
    return [Idea.from_row(row) for row in conn.execute(sql, params)]


def find_similar_title(
    conn: sqlite3.Connection, title: str, *, threshold: float = 0.85
) -> Idea | None:
    """An existing, non-dropped idea whose title is the same or nearly the same."""
    norm = normalize_title(title)
    if not norm:
        return None
    row = conn.execute(
        f"{_SELECT} WHERE i.title_norm = ? AND i.status != 'dropped' ORDER BY i.id LIMIT 1",
        (norm,),
    ).fetchone()
    if row:
        return Idea.from_row(row)
    query = fts_query(norm)
    if not query:
        return None
    try:
        rows = conn.execute(
            f"{_SELECT} WHERE i.status != 'dropped' AND i.id IN "
            "(SELECT rowid FROM ideas_fts WHERE ideas_fts MATCH ? ORDER BY rank LIMIT 20)",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    best: sqlite3.Row | None = None
    best_ratio = 0.0
    for candidate in rows:
        ratio = difflib.SequenceMatcher(None, norm, candidate["title_norm"]).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best is not None and best_ratio >= threshold:
        return Idea.from_row(best)
    return None


def apply_outcome(
    conn: sqlite3.Connection,
    idea_id: int,
    *,
    happened_on: str,
    avg_rating: float | None,
    now: str | None = None,
) -> Idea | None:
    """Bookkeeping after an outcome is recorded: done count, last date, average, status."""
    conn.execute(
        "UPDATE ideas SET times_done = times_done + 1, "
        "last_done_at = CASE WHEN last_done_at IS NULL OR last_done_at < ? THEN ? "
        "ELSE last_done_at END, "
        "avg_rating = ?, status = 'done', updated_at = ? WHERE id = ?",
        (happened_on, happened_on, avg_rating, now or utcnow_iso(), idea_id),
    )
    return get(conn, idea_id)
