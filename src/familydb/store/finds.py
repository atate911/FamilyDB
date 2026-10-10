"""What is on near home (jobs/happening.py): the dated things each source lists, how each
source answered, and the calendars the app found near home for an admin to tick. Three small
tables read and written together by one job, so one repository. Callers own the transactions."""

from __future__ import annotations

import sqlite3
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from familydb.integrations.events import FoundEvent, stored_end, stored_when

# What a source may put in a row. Feeds and pages say what they like; the page and the prompt
# show a line of each, so anything longer is cut here rather than wherever it is read.
TITLE_MAX = 200
TEXT_MAX = 300
NOTE_MAX = 300
# A proposed calendar that has not read as one for this many proposal runs in a row is let go.
PROPOSAL_MISSES = 3


class Find(BaseModel):
    id: int
    source: str
    kind: str
    external_id: str
    title: str
    starts_at: str
    ends_at: str | None = None
    all_day: bool = False
    venue: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    url: str | None = None
    price_note: str | None = None
    summary: str | None = None
    category: str | None = None
    first_seen_at: str
    last_seen_at: str
    gone: bool = False

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Find:
        return cls(**dict(row))


class FindSource(BaseModel):
    source: str
    kind: str
    checked_at: str
    ok: bool
    note: str = ""
    failures: int = 0
    found: int = 0


class FeedProposal(BaseModel):
    url: str
    title: str
    note: str = ""
    home_area: str
    events: int = 0
    found_at: str
    last_seen_at: str
    misses: int = 0


@dataclass(frozen=True)
class Readable:
    """A calendar that read as one on this proposal run, newly found or found before."""

    url: str
    title: str
    note: str
    events: int


def _cut(text: str | None, most: int) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    if not text:
        return None
    return text if len(text) <= most else text[: most - 1].rstrip() + "…"


def upsert_many(
    conn: sqlite3.Connection,
    source: str,
    kind: str,
    events: Iterable[FoundEvent],
    *,
    tz: ZoneInfo,
    now: str,
) -> tuple[int, int]:
    """Keep what a source listed: new rows added, known ones brought up to date and no longer
    gone. Returns (added, updated)."""
    added = updated = 0
    for event in events:
        starts = stored_when(event.starts, tz)
        title = _cut(event.title, TITLE_MAX)
        if starts is None or title is None or not event.external_id:
            continue
        known = conn.execute(
            "SELECT 1 FROM finds WHERE source = ? AND external_id = ?",
            (source, event.external_id),
        ).fetchone()
        conn.execute(
            "INSERT INTO finds (source, kind, external_id, title, starts_at, ends_at, all_day, "
            "venue, address, lat, lon, url, price_note, summary, category, first_seen_at, "
            "last_seen_at, gone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0) "
            "ON CONFLICT (source, external_id) DO UPDATE SET kind = excluded.kind, "
            "title = excluded.title, starts_at = excluded.starts_at, ends_at = excluded.ends_at, "
            "all_day = excluded.all_day, venue = excluded.venue, address = excluded.address, "
            "lat = excluded.lat, lon = excluded.lon, url = excluded.url, "
            "price_note = excluded.price_note, summary = excluded.summary, "
            "category = excluded.category, last_seen_at = excluded.last_seen_at, gone = 0",
            (
                source,
                kind,
                event.external_id[:TEXT_MAX],
                title,
                starts,
                stored_end(event, tz),
                int(event.all_day),
                _cut(event.venue, TITLE_MAX),
                _cut(event.address, TITLE_MAX),
                event.lat,
                event.lon,
                event.url,
                _cut(event.price_note, TITLE_MAX),
                _cut(event.summary, TEXT_MAX),
                _cut(event.category, TITLE_MAX),
                now,
                now,
            ),
        )
        if known:
            updated += 1
        else:
            added += 1
    return added, updated


def mark_gone(
    conn: sqlite3.Connection,
    source: str,
    *,
    seen: Collection[str],
    start: date,
    end: date,
    now: str,
) -> int:
    """Mark gone what this source listed for these days before and no longer does: a thing
    cancelled or moved off its list. Outside the days read, nothing is touched."""
    rows = conn.execute(
        "SELECT id, external_id FROM finds WHERE source = ? AND gone = 0 "
        "AND starts_at >= ? AND starts_at < ?",
        (source, start.isoformat(), (end + timedelta(days=1)).isoformat()),
    ).fetchall()
    gone = [row["id"] for row in rows if row["external_id"] not in seen]
    for find_id in gone:
        conn.execute("UPDATE finds SET gone = 1, last_seen_at = ? WHERE id = ?", (now, find_id))
    return len(gone)


_ON = "gone = 0 AND starts_at < ? AND coalesce(ends_at, starts_at) >= ?"  # overlaps the days asked


def get(conn: sqlite3.Connection, find_id: int) -> Find | None:
    """One thing a source listed, gone or not, for its own page."""
    row = conn.execute("SELECT * FROM finds WHERE id = ?", (find_id,)).fetchone()
    return Find.from_row(row) if row else None


def upcoming(conn: sqlite3.Connection, *, start: date, end: date, limit: int) -> list[Find]:
    """What is on at some point from `start` to `end` (both days included), soonest first."""
    rows = conn.execute(
        f"SELECT * FROM finds WHERE {_ON} ORDER BY starts_at, title, id LIMIT ?",
        ((end + timedelta(days=1)).isoformat(), start.isoformat(), limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def count_upcoming(conn: sqlite3.Connection, *, start: date, end: date) -> int:
    row = conn.execute(
        f"SELECT count(*) AS n FROM finds WHERE {_ON}",
        ((end + timedelta(days=1)).isoformat(), start.isoformat()),
    ).fetchone()
    return int(row["n"])


def prune(conn: sqlite3.Connection, *, before: date) -> int:
    """Forget what was over before `before`."""
    cur = conn.execute(
        "DELETE FROM finds WHERE coalesce(ends_at, starts_at) < ?", (before.isoformat(),)
    )
    return cur.rowcount


def source_answered(
    conn: sqlite3.Connection, source: str, kind: str, *, ok: bool, note: str, found: int, at: str
) -> int:
    """Record how a source answered; returns how many reads in a row it has now failed. A
    failed read keeps the count it listed last time."""
    conn.execute(
        "INSERT INTO find_sources (source, kind, checked_at, ok, note, failures, found) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (source) DO UPDATE SET "
        "kind = excluded.kind, checked_at = excluded.checked_at, ok = excluded.ok, "
        "note = excluded.note, "
        "found = CASE WHEN excluded.ok THEN excluded.found ELSE find_sources.found END, "
        "failures = CASE WHEN excluded.ok THEN 0 ELSE find_sources.failures + 1 END",
        (source, kind, at, int(ok), note[:NOTE_MAX], 0 if ok else 1, found if ok else 0),
    )
    row = conn.execute("SELECT failures FROM find_sources WHERE source = ?", (source,)).fetchone()
    return int(row["failures"])


def sources(conn: sqlite3.Connection) -> list[FindSource]:
    rows = conn.execute("SELECT * FROM find_sources ORDER BY source").fetchall()
    return [FindSource(**dict(row)) for row in rows]


def source(conn: sqlite3.Connection, name: str) -> FindSource | None:
    row = conn.execute("SELECT * FROM find_sources WHERE source = ?", (name,)).fetchone()
    return FindSource(**dict(row)) if row else None


def forget_sources(conn: sqlite3.Connection, keep: Collection[str]) -> int:
    """Forget every source not in `keep`, and what it listed: a feed taken off the list, a key
    removed. Returns how many sources went."""
    names = [row["source"] for row in conn.execute("SELECT source FROM find_sources")]
    names += [row["source"] for row in conn.execute("SELECT DISTINCT source FROM finds")]
    going = sorted({name for name in names if name not in keep})
    for name in going:
        conn.execute("DELETE FROM finds WHERE source = ?", (name,))
        conn.execute("DELETE FROM find_sources WHERE source = ?", (name,))
    return len(going)


def proposals(conn: sqlite3.Connection, home_area: str) -> list[FeedProposal]:
    rows = conn.execute(
        "SELECT * FROM feed_proposals WHERE home_area = ? ORDER BY found_at DESC, title",
        (home_area,),
    ).fetchall()
    return [FeedProposal(**dict(row)) for row in rows]


def known_feed_urls(conn: sqlite3.Connection) -> set[str]:
    return {row["url"] for row in conn.execute("SELECT url FROM feed_proposals")}


def merge_proposals(
    conn: sqlite3.Connection, home_area: str, readable: Iterable[Readable], *, now: str
) -> tuple[int, int, int]:
    """Bring the proposals in line with one proposal run.

    `readable` is every calendar that read as one this run, found before or newly. Those are
    kept (and their misses forgotten); one found before that did not read gets a miss, and goes
    at `PROPOSAL_MISSES`. Proposals for another home area go at once: the family moved, or put
    the home right. Returns (new, kept, dropped).
    """
    dropped = conn.execute("DELETE FROM feed_proposals WHERE home_area != ?", (home_area,)).rowcount
    before = {proposal.url for proposal in proposals(conn, home_area)}
    read = {}
    for one in readable:
        read[one.url] = one
    new = kept = 0
    for one in read.values():
        title = _cut(one.title, TITLE_MAX) or one.url
        note = _cut(one.note, NOTE_MAX) or ""
        if one.url in before:
            conn.execute(
                "UPDATE feed_proposals SET title = ?, note = ?, events = ?, last_seen_at = ?, "
                "misses = 0 WHERE url = ?",
                (title, note, one.events, now, one.url),
            )
            kept += 1
        else:
            conn.execute(
                "INSERT INTO feed_proposals (url, title, note, home_area, events, found_at, "
                "last_seen_at, misses) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (one.url, title, note, home_area, one.events, now, now),
            )
            new += 1
    for url in before - set(read):
        conn.execute("UPDATE feed_proposals SET misses = misses + 1 WHERE url = ?", (url,))
    dropped += conn.execute(
        "DELETE FROM feed_proposals WHERE misses >= ?", (PROPOSAL_MISSES,)
    ).rowcount
    return new, kept, dropped
