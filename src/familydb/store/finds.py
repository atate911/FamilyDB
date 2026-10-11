"""Her back pocket (docs/FINDS.md): what the app found outside the family's list, dated events
from the calendars, Ticketmaster and searches, and places to go any time; how each source
answered; and the calendars found near home for an admin to tick. Three small tables read and
written together, so one repository. A find keeps what became of it (recommended, saved as an
idea, planned, passed on), which outlives the listing. Callers own the transactions."""

from __future__ import annotations

import sqlite3
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from familydb.integrations.events import FoundEvent, stored_end, stored_when
from familydb.store.db import from_json, to_json

# What a source may put in a row. Feeds and pages say what they like; the page and the prompt
# show a line of each, so anything longer is cut here rather than wherever it is read.
TITLE_MAX = 200
TEXT_MAX = 300
NOTE_MAX = 300
# A proposed calendar that has not read as one for this many proposal runs in a row is let go.
PROPOSAL_MISSES = 3
# What became of a find. new and recommended are hers to offer; saved, planned and passed are the
# family's word on it, kept a year so the same thing is not offered again and Status can count.
STATES = ("new", "recommended", "saved", "planned", "passed")
OFFERED = ("new", "recommended")
# A place found any time, never seen again in this many days, is let go.
ANYTIME_DAYS = 90
REMEMBER_DAYS = 365


class Find(BaseModel):
    id: int
    source: str
    kind: str  # where it came from: feed, ticketmaster, web (scouting), request
    external_id: str
    title: str
    starts_at: str | None = None  # None: any time, a place rather than an event
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
    participants: list[str] = []  # who it is for, as an idea's
    why: str | None = None
    state: str = "new"
    idea_id: int | None = None
    place_id: int | None = None
    setting: str | None = None
    cost_level: int | None = None
    duration_min: int | None = None
    min_age: int | None = None
    max_age: int | None = None
    needs_booking: bool | None = None
    judged_at: str | None = None
    judged_why: str | None = None
    judged_when: str | None = None
    put_from: str | None = None
    put_until: str | None = None
    put_forward_at: str | None = None
    put_forward_window: str | None = None
    saved_at: str | None = None
    passed_at: str | None = None
    passed_by: int | None = None
    passed_why: str | None = None
    filled_at: str | None = None  # when a lookup last tried it
    fill_note: str | None = None
    first_seen_at: str
    last_seen_at: str
    gone: bool = False

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Find:
        data = dict(row)
        data["participants"] = from_json(data.get("participants"), []) or []
        return cls(**data)

    @property
    def any_time(self) -> bool:
        return self.starts_at is None


class NewFind(BaseModel):
    """Something a search found, to keep (`keep`): dated or any time."""

    title: str
    url: str
    starts: str | None = None  # "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM", wall time; None any time
    ends: str | None = None
    all_day: bool = False
    venue: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    price_note: str | None = None
    summary: str | None = None
    category: str | None = None
    participants: list[str] = []
    why: str | None = None
    min_age: int | None = None
    max_age: int | None = None


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


# Dated, not passed on, and overlapping the days asked.
_ON = (
    "gone = 0 AND state != 'passed' AND starts_at IS NOT NULL "
    "AND starts_at < ? AND coalesce(ends_at, starts_at) >= ?"
)


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


def keep(
    conn: sqlite3.Connection, source: str, kind: str, found: Iterable[NewFind], *, now: str
) -> tuple[list[Find], int]:
    """Keep what a search found, dated or any time: one already kept from any search (by its
    page) is brought up to date in place, keeping what became of it. Returns the finds kept, in
    the order given, and how many were new."""
    kept: list[Find] = []
    added = 0
    for one in found:
        title = _cut(one.title, TITLE_MAX)
        if title is None or not one.url:
            continue
        row = conn.execute(
            "SELECT id FROM finds WHERE kind IN ('web', 'request') AND lower(url) = lower(?) "
            "ORDER BY id LIMIT 1",
            (one.url,),
        ).fetchone()
        listing = (
            title,
            one.starts,
            one.ends,
            int(one.all_day),
            _cut(one.venue, TITLE_MAX),
            _cut(one.address, TITLE_MAX),
            one.lat,
            one.lon,
            _cut(one.price_note, TITLE_MAX),
            _cut(one.summary, TEXT_MAX),
            _cut(one.category, TITLE_MAX),
        )
        if row is not None:
            conn.execute(
                "UPDATE finds SET title = ?, starts_at = ?, ends_at = ?, all_day = ?, "
                "venue = coalesce(?, venue), address = coalesce(?, address), "
                "lat = coalesce(?, lat), lon = coalesce(?, lon), "
                "price_note = coalesce(?, price_note), summary = coalesce(?, summary), "
                "category = coalesce(?, category), last_seen_at = ?, gone = 0 WHERE id = ?",
                (*listing, now, row["id"]),
            )
            find_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO finds (source, kind, external_id, title, starts_at, ends_at, "
                "all_day, venue, address, lat, lon, price_note, summary, category, url, "
                "participants, why, min_age, max_age, first_seen_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source,
                    kind,
                    one.url[:TEXT_MAX],
                    *listing,
                    one.url,
                    to_json([p for p in one.participants if p.strip()][:6]),
                    _cut(one.why, TEXT_MAX),
                    one.min_age,
                    one.max_age,
                    now,
                    now,
                ),
            )
            find_id = int(cur.lastrowid or 0)
            added += 1
        found_row = get(conn, find_id)
        if found_row is not None:
            kept.append(found_row)
    return kept, added


def anytime(conn: sqlite3.Connection, *, limit: int) -> list[Find]:
    """The places she found to go any time, still hers to offer, newest first."""
    rows = conn.execute(
        "SELECT * FROM finds WHERE starts_at IS NULL AND gone = 0 "
        "AND state IN ('new', 'recommended') ORDER BY first_seen_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def by_url_or_title(conn: sqlite3.Connection, url: str | None, title: str) -> Find | None:
    """A find by its page, else by its exact title (case aside), the newest; any state."""
    if url:
        row = conn.execute(
            "SELECT * FROM finds WHERE lower(url) = lower(?) ORDER BY id DESC LIMIT 1", (url,)
        ).fetchone()
        if row is not None:
            return Find.from_row(row)
    row = conn.execute(
        "SELECT * FROM finds WHERE lower(title) = lower(?) ORDER BY id DESC LIMIT 1",
        (" ".join(title.split()),),
    ).fetchone()
    return Find.from_row(row) if row else None


def recent(conn: sqlite3.Connection, *, since: str, limit: int) -> list[Find]:
    """Finds first seen or seen again at or after `since`, newest first, any state: what a
    person might mean by "that market" in a chat."""
    rows = conn.execute(
        "SELECT * FROM finds WHERE last_seen_at >= ? ORDER BY last_seen_at DESC, id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def passed(conn: sqlite3.Connection, *, since: str) -> list[Find]:
    """What the family passed on at or after `since`, newest first."""
    rows = conn.execute(
        "SELECT * FROM finds WHERE state = 'passed' AND passed_at >= ? ORDER BY passed_at DESC",
        (since,),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def mark_saved(conn: sqlite3.Connection, find_id: int, *, idea_id: int, now: str) -> None:
    """The family saved it: it is this idea now."""
    conn.execute(
        "UPDATE finds SET state = 'saved', idea_id = ?, saved_at = ? WHERE id = ?",
        (idea_id, now, find_id),
    )


def mark_planned(
    conn: sqlite3.Connection, *, find_id: int | None, idea_id: int | None, now: str
) -> None:
    """A plan was made from it: the find named, or the one saved as this idea. One passed on
    stays passed."""
    conn.execute(
        "UPDATE finds SET state = 'planned', saved_at = coalesce(saved_at, ?) "
        "WHERE state != 'passed' AND (id = ? OR (idea_id = ? AND state = 'saved'))",
        (now, find_id, idea_id),
    )


def mark_passed(
    conn: sqlite3.Connection, find_id: int, *, by: int | None, why: str | None, now: str
) -> None:
    """The family said it is not for them."""
    conn.execute(
        "UPDATE finds SET state = 'passed', passed_at = ?, passed_by = ?, passed_why = ? "
        "WHERE id = ?",
        (now, by, _cut(why, NOTE_MAX), find_id),
    )


# What a change to a find's fate touches, kept before it so it can be put back (familydb/undo.py).
FATE = ("state", "idea_id", "saved_at", "passed_at", "passed_by", "passed_why")


def fates_since(conn: sqlite3.Connection, *, since: str) -> dict[str, dict[str, int]]:
    """For each kind of find (where it came from), what was found since a timestamp and what
    became of what was: put forward, saved, planned, passed on (suggest/taken.py)."""
    rows = conn.execute(
        "SELECT kind, "
        "sum(first_seen_at >= ?) AS found, "
        "sum(judged_why IS NOT NULL AND judged_at >= ?) AS recommended, "
        "sum(saved_at IS NOT NULL AND saved_at >= ?) AS saved, "
        "sum(state = 'planned' AND coalesce(saved_at, last_seen_at) >= ?) AS planned, "
        "sum(passed_at IS NOT NULL AND passed_at >= ?) AS passed "
        "FROM finds GROUP BY kind",
        (since,) * 5,
    ).fetchall()
    keys = ("found", "recommended", "saved", "planned", "passed")
    return {row["kind"]: {key: int(row[key] or 0) for key in keys} for row in rows}


def rated_since(conn: sqlite3.Connection, *, since: str) -> dict[str, tuple[int, float]]:
    """For each kind of find, how the outings made of the ideas it became went since a day
    (YYYY-MM-DD): how many were rated, and their average."""
    rows = conn.execute(
        "SELECT f.kind AS kind, count(o.id) AS n, avg(o.rating) AS average FROM finds f "
        "JOIN outcomes o ON o.idea_id = f.idea_id "
        "WHERE f.idea_id IS NOT NULL AND o.rating IS NOT NULL AND o.happened_on >= ? "
        "GROUP BY f.kind",
        (since,),
    ).fetchall()
    return {row["kind"]: (int(row["n"]), round(float(row["average"]), 1)) for row in rows}


def saved_since(conn: sqlite3.Connection, *, since: str, limit: int) -> list[Find]:
    """What the family saved or planned of what she found, newest first: what the next search
    leans towards (scouting/brief.py)."""
    rows = conn.execute(
        "SELECT * FROM finds WHERE state IN ('saved', 'planned') AND saved_at >= ? "
        "ORDER BY saved_at DESC, id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def fate(find: Find) -> dict[str, object]:
    """What became of a find, as `restore` takes it back."""
    return {key: getattr(find, key) for key in FATE}


def restore(conn: sqlite3.Connection, find_id: int, before: dict[str, object]) -> None:
    """Put back what became of a find, as it was before a change now undone."""
    conn.execute(
        "UPDATE finds SET state = ?, idea_id = ?, saved_at = ?, passed_at = ?, passed_by = ?, "
        "passed_why = ? WHERE id = ?",
        (*(before.get(key) for key in FATE), find_id),
    )


# Still hers to offer, on no day past: what the evening's fills and judging look at.
_POCKET = (
    "gone = 0 AND state IN ('new', 'recommended') "
    "AND (starts_at IS NULL OR coalesce(ends_at, starts_at) >= ?)"
)


def pocket(conn: sqlite3.Connection, *, today: date, limit: int) -> list[Find]:
    """Her back pocket: what is still hers to offer, soonest first, places to go any time after."""
    rows = conn.execute(
        f"SELECT * FROM finds WHERE {_POCKET} "
        "ORDER BY starts_at IS NULL, starts_at, first_seen_at DESC, id LIMIT ?",
        (today.isoformat(), limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def to_fill(conn: sqlite3.Connection, *, today: date, limit: int) -> list[Find]:
    """What a lookup has never tried, newest first: what scouting and searches found lately."""
    rows = conn.execute(
        f"SELECT * FROM finds WHERE {_POCKET} AND filled_at IS NULL AND place_id IS NULL "
        "AND url IS NOT NULL ORDER BY first_seen_at DESC, id DESC LIMIT ?",
        (today.isoformat(), limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


# What a lookup may fill in on a find; what the search already said stays.
FACTS = ("setting", "cost_level", "duration_min", "min_age", "max_age", "needs_booking")


def mark_filled(
    conn: sqlite3.Connection,
    find_id: int,
    *,
    place_id: int | None,
    facts: dict[str, object],
    note: str | None,
    now: str,
) -> None:
    """A lookup tried it: its place when it found one, and the facts it found where none were."""
    said = {key: facts.get(key) for key in FACTS}
    conn.execute(
        "UPDATE finds SET place_id = coalesce(?, place_id), filled_at = ?, fill_note = ?, "
        + ", ".join(f"{key} = coalesce({key}, ?)" for key in FACTS)
        + " WHERE id = ?",
        (place_id, now, _cut(note, NOTE_MAX), *said.values(), find_id),
    )


def recommended(conn: sqlite3.Connection, *, today: date, limit: int) -> list[Find]:
    """What the evening's judgement put forward and is still to offer: not past, and not past
    the last day it was to be offered; the latest judged first."""
    rows = conn.execute(
        f"SELECT * FROM finds WHERE {_POCKET} AND state = 'recommended' "
        "AND (put_until IS NULL OR put_until >= ?) ORDER BY judged_at DESC, id LIMIT ?",
        (today.isoformat(), today.isoformat(), limit),
    ).fetchall()
    return [Find.from_row(row) for row in rows]


def put_forward(conn: sqlite3.Connection, find_id: int, *, window: str, now: str) -> None:
    """She put it forward on Now, for this window (familydb/picks.py)."""
    conn.execute(
        "UPDATE finds SET put_forward_at = ?, put_forward_window = ? WHERE id = ?",
        (now, window, find_id),
    )


def judging_due(conn: sqlite3.Connection, *, today: date) -> bool:
    """Whether anything in the pocket is new to the judging, or filled in since it was judged."""
    row = conn.execute(
        f"SELECT 1 FROM finds WHERE {_POCKET} AND (judged_at IS NULL "
        "OR (filled_at IS NOT NULL AND filled_at > judged_at)) LIMIT 1",
        (today.isoformat(),),
    ).fetchone()
    return row is not None


def judged(
    conn: sqlite3.Connection,
    looked_at: list[int],
    chosen: dict[int, dict[str, str | None]],
    *,
    now: str,
) -> None:
    """The evening's judgement of the pocket: each find looked at is judged now; those chosen are
    recommended, with why, when and the days to put them forward; one recommended before and not
    chosen again is hers to offer still, no longer recommended."""
    for find_id in looked_at:
        said = chosen.get(find_id)
        if said is None:
            conn.execute(
                "UPDATE finds SET judged_at = ?, judged_why = NULL, judged_when = NULL, "
                "put_from = NULL, put_until = NULL, "
                "state = CASE WHEN state = 'recommended' THEN 'new' ELSE state END WHERE id = ?",
                (now, find_id),
            )
            continue
        conn.execute(
            "UPDATE finds SET judged_at = ?, judged_why = ?, judged_when = ?, put_from = ?, "
            "put_until = ?, state = 'recommended' WHERE id = ? AND state IN ('new', 'recommended')",
            (
                now,
                _cut(said.get("why"), NOTE_MAX),
                _cut(said.get("when"), TITLE_MAX),
                said.get("put_from"),
                said.get("put_until"),
                find_id,
            ),
        )


def prune(conn: sqlite3.Connection, *, before: date) -> int:
    """Forget what was over before `before` and never became the family's, a place offered any
    time and not seen for `ANYTIME_DAYS`, and the family's word on one after `REMEMBER_DAYS`."""
    gone = 0
    for sql, when in (
        (
            "DELETE FROM finds WHERE state IN ('new', 'recommended') AND starts_at IS NOT NULL "
            "AND coalesce(ends_at, starts_at) < ?",
            before,
        ),
        (
            "DELETE FROM finds WHERE state IN ('new', 'recommended') AND starts_at IS NULL "
            "AND last_seen_at < ?",
            before - timedelta(days=ANYTIME_DAYS),
        ),
        (
            "DELETE FROM finds WHERE state IN ('saved', 'planned', 'passed') "
            "AND coalesce(passed_at, saved_at, last_seen_at) < ?",
            before - timedelta(days=REMEMBER_DAYS),
        ),
    ):
        gone += conn.execute(sql, (when.isoformat(),)).rowcount
    return gone


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
    removed. What the family saved, planned or passed on stays, marked gone. Returns how many
    sources went."""
    names = [row["source"] for row in conn.execute("SELECT source FROM find_sources")]
    names += [row["source"] for row in conn.execute("SELECT DISTINCT source FROM finds")]
    going = sorted({name for name in names if name not in keep})
    for name in going:
        conn.execute(
            "DELETE FROM finds WHERE source = ? AND state IN ('new', 'recommended')", (name,)
        )
        conn.execute("UPDATE finds SET gone = 1 WHERE source = ?", (name,))
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
