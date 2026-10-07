"""The repository of what is on near home: finds, their sources, and proposed calendars."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from familydb.integrations.events import FoundEvent
from familydb.store import finds
from familydb.store.db import transaction
from tests.conftest import TZ

SAT = date(2026, 9, 26)
SUN = date(2026, 9, 27)


def _show(external_id: str = "a", **fields) -> FoundEvent:
    values = {
        "external_id": external_id,
        "title": "Puppet show",
        "starts": datetime(2026, 9, 26, 10, 30, tzinfo=TZ),
        "ends": datetime(2026, 9, 26, 11, 30, tzinfo=TZ),
    }
    values.update(fields)
    return FoundEvent(**values)


def _keep(conn: sqlite3.Connection, *events: FoundEvent, source: str = "feed:x", now: str = "1"):
    with transaction(conn):
        return finds.upsert_many(conn, source, "feed", events, tz=TZ, now=now)


def test_a_find_is_kept_in_wall_time_and_updated_in_place(conn: sqlite3.Connection) -> None:
    assert _keep(conn, _show(), now="t1") == (1, 0)
    assert _keep(conn, _show(title="Puppet show, sold out"), now="t2") == (0, 1)
    [found] = finds.upcoming(conn, start=SAT, end=SUN, limit=10)
    assert found.starts_at == "2026-09-26T10:30"
    assert found.ends_at == "2026-09-26T11:30"
    assert found.title == "Puppet show, sold out"
    assert (found.first_seen_at, found.last_seen_at) == ("t1", "t2")


def test_an_all_day_thing_ends_on_its_last_day(conn: sqlite3.Connection) -> None:
    fair = _show("fair", title="Harvest fair", starts=SAT, ends=date(2026, 9, 28), all_day=True)
    one_day = _show("one", title="Market", starts=SAT, ends=SUN, all_day=True)
    _keep(conn, fair, one_day)
    rows = {f.external_id: f for f in finds.upcoming(conn, start=SAT, end=SUN, limit=10)}
    assert (rows["fair"].starts_at, rows["fair"].ends_at) == ("2026-09-26", "2026-09-27")
    assert rows["one"].ends_at is None  # one day: no end worth keeping
    assert rows["fair"].all_day


def test_what_is_on_takes_in_a_thing_that_began_before_the_days_asked(
    conn: sqlite3.Connection,
) -> None:
    run = _show("run", title="Exhibit", starts=date(2026, 9, 1), ends=date(2026, 10, 2))
    later = _show("later", title="Concert", starts=datetime(2026, 10, 3, 19, tzinfo=TZ))
    _keep(conn, _show(), run, later)
    titles = [f.title for f in finds.upcoming(conn, start=SAT, end=SUN, limit=10)]
    assert titles == ["Exhibit", "Puppet show"]  # soonest first; the concert is after Sunday
    assert finds.count_upcoming(conn, start=SAT, end=SUN) == 2


def test_what_drops_off_a_list_is_gone_and_comes_back_when_listed_again(
    conn: sqlite3.Connection,
) -> None:
    other = _show("b", title="Choir", starts=datetime(2026, 9, 27, 15, tzinfo=TZ))
    _keep(conn, _show(), other)
    with transaction(conn):
        assert finds.mark_gone(conn, "feed:x", seen={"a"}, start=SAT, end=SUN, now="t") == 1
    assert [f.title for f in finds.upcoming(conn, start=SAT, end=SUN, limit=10)] == ["Puppet show"]
    _keep(conn, other)
    assert finds.count_upcoming(conn, start=SAT, end=SUN) == 2


def test_gone_is_only_said_of_the_days_that_were_read(conn: sqlite3.Connection) -> None:
    _keep(conn, _show(), _show("next", starts=datetime(2026, 10, 10, 9, tzinfo=TZ)))
    with transaction(conn):
        assert finds.mark_gone(conn, "feed:x", seen=set(), start=SAT, end=SUN, now="t") == 1
    assert finds.count_upcoming(conn, start=SAT, end=date(2026, 10, 31)) == 1


def test_what_is_over_is_pruned(conn: sqlite3.Connection) -> None:
    _keep(conn, _show(), _show("old", starts=datetime(2026, 9, 1, 9, tzinfo=TZ), ends=None))
    with transaction(conn):
        assert finds.prune(conn, before=date(2026, 9, 20)) == 1
    assert finds.count_upcoming(conn, start=date(2026, 1, 1), end=date(2026, 12, 31)) == 1


def test_long_words_from_a_source_are_cut(conn: sqlite3.Connection) -> None:
    _keep(conn, _show(title="x" * 500, summary="  many   spaces " + "y" * 500))
    [found] = finds.upcoming(conn, start=SAT, end=SUN, limit=1)
    assert len(found.title) == finds.TITLE_MAX and found.title.endswith("…")
    assert found.summary.startswith("many spaces y") and len(found.summary) == finds.TEXT_MAX


def test_a_source_counts_failures_in_a_row_and_keeps_what_it_last_found(
    conn: sqlite3.Connection,
) -> None:
    with transaction(conn):
        assert finds.source_answered(conn, "feed:x", "feed", ok=True, note="", found=4, at="1") == 0
        assert finds.source_answered(conn, "feed:x", "feed", ok=False, note="404", found=0, at="2")
        assert (
            finds.source_answered(conn, "feed:x", "feed", ok=False, note="404", found=0, at="3")
            == 2
        )
    [answered] = finds.sources(conn)
    assert (answered.ok, answered.failures, answered.found, answered.note) == (False, 2, 4, "404")
    with transaction(conn):
        assert finds.source_answered(conn, "feed:x", "feed", ok=True, note="", found=5, at="4") == 0


def test_a_source_no_longer_listed_is_forgotten_with_what_it_found(
    conn: sqlite3.Connection,
) -> None:
    _keep(conn, _show(), source="feed:x")
    _keep(conn, _show(), source="feed:y")
    with transaction(conn):
        finds.source_answered(conn, "feed:x", "feed", ok=True, note="", found=1, at="1")
        finds.source_answered(conn, "feed:y", "feed", ok=True, note="", found=1, at="1")
        assert finds.forget_sources(conn, {"feed:y"}) == 1
    assert [s.source for s in finds.sources(conn)] == ["feed:y"]
    assert {f.source for f in finds.upcoming(conn, start=SAT, end=SUN, limit=10)} == {"feed:y"}


def _propose(conn, area: str, *urls: str, now: str = "1"):
    readable = [finds.Readable(url=u, title=u.upper(), note="why", events=3) for u in urls]
    with transaction(conn):
        return finds.merge_proposals(conn, area, readable, now=now)


def test_proposals_are_kept_while_they_read_and_let_go_after_three_misses(
    conn: sqlite3.Connection,
) -> None:
    assert _propose(conn, "Vancouver, WA", "a", "b") == (2, 0, 0)
    assert _propose(conn, "Vancouver, WA", "a", "c", now="2") == (1, 1, 0)
    by_url = {p.url: p for p in finds.proposals(conn, "Vancouver, WA")}
    assert by_url["b"].misses == 1 and by_url["a"].last_seen_at == "2"
    assert by_url["a"].found_at == "1"
    _propose(conn, "Vancouver, WA", "a", "c")
    assert _propose(conn, "Vancouver, WA", "a", "c") == (0, 2, 1)
    assert finds.known_feed_urls(conn) == {"a", "c"}


def test_a_new_home_area_starts_the_proposals_again(conn: sqlite3.Connection) -> None:
    _propose(conn, "Vancouver, WA", "a")
    assert _propose(conn, "Portland, OR", "z") == (1, 0, 1)
    assert [p.url for p in finds.proposals(conn, "Portland, OR")] == ["z"]
    assert finds.proposals(conn, "Vancouver, WA") == []
