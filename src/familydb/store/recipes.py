"""Recipes: what an idea of kind recipe keeps beside the idea (docs/RECIPES.md), one row an idea,
as `places` is for a place. Every statement on `recipes` is here."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

from familydb.store.db import from_json, to_json
from familydb.store.ideas import RECIPE, Idea

# The situations a recipe suits, in the order the page names them. The tool, the page, the guess
# and the picker read this list and no other.
OCCASIONS: tuple[str, ...] = (
    "weeknight",
    "family_dinner",
    "prep_ahead",
    "slow",
    "date_night",
    "guests",
    "kids_cook",
    "lunchbox",
    "breakfast",
    "freezer",
)
Occasion = Literal[
    "weeknight",
    "family_dinner",
    "prep_ahead",
    "slow",
    "date_night",
    "guests",
    "kids_cook",
    "lunchbox",
    "breakfast",
    "freezer",
]
FilledBy = Literal["family", "page", "lookup"]
JSON_FIELDS = ("ingredients", "steps", "occasions", "occasions_guessed")
FIELDS = frozenset(
    {
        "name",
        "source_url",
        "source_site",
        "ingredients",
        "steps",
        "active_minutes",
        "total_minutes",
        "serves",
        "occasions",
        "occasions_guessed",
        "prep_note",
        "filled_at",
        "filled_by",
        "fill_note",
        "name_wanted",
    }
)


class Ingredient(BaseModel):
    """A line as written, and what to buy read out of it (familydb/groceries.py)."""

    text: str
    item: str
    amount: str | None = None


class Recipe(BaseModel):
    idea_id: int
    name: str | None = None
    source_url: str | None = None
    source_site: str | None = None
    ingredients: list[Ingredient] = []
    steps: list[str] = []
    active_minutes: int | None = None
    total_minutes: int | None = None
    serves: int | None = None
    occasions: list[str] = []
    occasions_guessed: list[str] = []
    prep_note: str | None = None
    filled_at: str | None = None
    filled_by: FilledBy | None = None
    fill_note: str | None = None
    name_wanted: bool = False
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Recipe:
        data = dict(row)
        for key in JSON_FIELDS:
            data[key] = from_json(data.get(key), [])
        data["name_wanted"] = bool(data.get("name_wanted"))
        return cls(**data)

    @property
    def minutes(self) -> int | None:
        """Start to table, as well as anybody said it."""
        return self.total_minutes if self.total_minutes is not None else self.active_minutes

    @property
    def read(self) -> bool:
        """Whether its link was read, by code or a lookup."""
        return self.filled_at is not None


def site_of(url: str | None) -> str | None:
    """The host a recipe came from, without its www: "seriouseats.com"."""
    if not url:
        return None
    host = (urlsplit(url).hostname or "").casefold()
    return host.removeprefix("www.") or None


def _encode(fields: dict[str, Any]) -> dict[str, Any]:
    unknown = set(fields) - FIELDS
    if unknown:
        raise ValueError(f"unknown recipe fields: {sorted(unknown)}")
    out = dict(fields)
    for key in JSON_FIELDS:
        if key in out:
            values = out[key] or []
            out[key] = to_json([v.model_dump() if isinstance(v, BaseModel) else v for v in values])
    if "name_wanted" in out:
        out["name_wanted"] = int(bool(out["name_wanted"]))
    return out


def get(conn: sqlite3.Connection, idea_id: int) -> Recipe | None:
    row = conn.execute("SELECT * FROM recipes WHERE idea_id = ?", (idea_id,)).fetchone()
    return Recipe.from_row(row) if row else None


def of_ideas(conn: sqlite3.Connection, idea_ids: Iterable[int]) -> dict[int, Recipe]:
    wanted = sorted({int(one) for one in idea_ids})
    if not wanted:
        return {}
    marks = ", ".join("?" for _ in wanted)
    rows = conn.execute(f"SELECT * FROM recipes WHERE idea_id IN ({marks})", wanted)
    return {row["idea_id"]: Recipe.from_row(row) for row in rows}


def upsert(conn: sqlite3.Connection, idea_id: int, fields: dict[str, Any], *, now: str) -> Recipe:
    """Make the idea's row if it has none, then set what is given. Call inside a transaction."""
    data = _encode(fields)
    conn.execute(
        "INSERT OR IGNORE INTO recipes (idea_id, updated_at) VALUES (?, ?)", (idea_id, now)
    )
    data["updated_at"] = now
    assignments = ", ".join(f"{column} = ?" for column in data)
    conn.execute(f"UPDATE recipes SET {assignments} WHERE idea_id = ?", [*data.values(), idea_id])
    found = get(conn, idea_id)
    assert found is not None
    return found


def by_source_url(conn: sqlite3.Connection, url: str) -> int | None:
    """The live recipe idea already kept for this link, if any."""
    row = conn.execute(
        "SELECT r.idea_id FROM recipes r JOIN ideas i ON i.id = r.idea_id "
        "WHERE r.source_url = ? AND i.status != 'dropped' ORDER BY r.idea_id LIMIT 1",
        (url,),
    ).fetchone()
    return int(row["idea_id"]) if row else None


def live(conn: sqlite3.Connection, exclude_ids: Iterable[int] = ()) -> list[tuple[Idea, Recipe]]:
    """Every recipe idea not dropped, with its row (an empty one where it has none), oldest first,
    leaving out `exclude_ids` (the presents kept from whoever asks)."""
    left_out = sorted({int(one) for one in exclude_ids})
    where = "i.kind = ? AND i.status != 'dropped'"
    params: list[Any] = [RECIPE]
    if left_out:
        where += f" AND i.id NOT IN ({', '.join('?' for _ in left_out)})"
        params.extend(left_out)
    rows = conn.execute(
        "SELECT i.*, m.display_name AS suggested_by_name FROM ideas i "
        f"LEFT JOIN members m ON m.id = i.suggested_by WHERE {where} ORDER BY i.id",
        params,
    ).fetchall()
    found = of_ideas(conn, [row["id"] for row in rows])
    return [(Idea.from_row(row), found.get(row["id"]) or Recipe(idea_id=row["id"])) for row in rows]


def links_to_read(conn: sqlite3.Connection, limit: int) -> list[int]:
    """Recipe ideas with a link nobody has tried to read yet, oldest first."""
    rows = conn.execute(
        "SELECT r.idea_id FROM recipes r JOIN ideas i ON i.id = r.idea_id "
        "WHERE r.source_url IS NOT NULL AND r.filled_at IS NULL AND r.fill_note IS NULL "
        "AND i.status != 'dropped' AND i.enrichment = 'pending' ORDER BY r.idea_id LIMIT ?",
        (limit,),
    )
    return [int(row["idea_id"]) for row in rows]


def clear_read(conn: sqlite3.Connection, idea_id: int, *, now: str) -> None:
    """Read its link afresh on the next run (look it up again). Call inside a transaction."""
    conn.execute(
        "UPDATE recipes SET filled_at = NULL, fill_note = NULL, updated_at = ? WHERE idea_id = ?",
        (now, idea_id),
    )
