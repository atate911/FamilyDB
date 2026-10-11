"""Checking covers finds (suggest/pocket.py): what she found is held to the same checks as the
family's ideas, by the same code: its time against the free time, rain when it is outdoors, who
it is for, the family's firm rules against its words, and the drive. The ruled out are logged,
never offered, and nothing a find stood in as reaches the log."""

from __future__ import annotations

from datetime import datetime

from familydb.store import db, finds, memories, suggestions
from familydb.suggest.engine import run
from familydb.suggest.types import SuggestInput
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO, TZ
from tests.test_suggest import DRY_SAT, WET_SUN

WEEKEND = {"window": "this_weekend", "question": "what should we do?", "discover": False}


def _ctx(conn, settings, clock, family, *, busy=None, member="sam") -> ToolContext:
    calendar = fakes.FakeCalendar(TZ)
    if busy:
        calendar.seed("Busy", *busy)
    return ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=family[member],
        calendar=calendar,
        weather=fakes.FakeForecast([DRY_SAT, WET_SUN]),
    )


def _found(conn, title, starts, **facts) -> int:
    """Something she found, kept as a search on request keeps it; `facts` as a lookup fills."""
    words = {k: facts.pop(k) for k in ("summary", "participants") if k in facts}
    with db.transaction(conn):
        [kept], _ = finds.keep(
            conn,
            "request",
            "request",
            [finds.NewFind(title=title, url=f"https://x.example/{title}", starts=starts, **words)],
            now=NOW_ISO,
        )
        for key, value in facts.items():
            conn.execute(f"UPDATE finds SET {key} = ? WHERE id = ?", (value, kept.id))
    return kept.id


def _rule(conn, fact, rule) -> int:
    with db.transaction(conn):
        return memories.insert(
            conn,
            member_id=None,
            category="other",
            fact=fact,
            firm=True,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=None,
            now=NOW_ISO,
            rule=rule,
        ).id


def _logged(conn) -> dict[str, dict]:
    row = suggestions.list_recent(conn, limit=1)[0]
    return {find["title"]: find for find in row.web_finds}


def test_an_event_is_held_to_when_it_is_on(conn, full_settings, thursday_clock, family):
    _found(conn, "Late show", "2026-09-26T19:00", ends_at="2026-09-26T21:00")
    _found(conn, "Matinee", "2026-09-26T14:00", ends_at="2026-09-26T16:00")
    busy = (datetime(2026, 9, 26, 18, tzinfo=TZ), datetime(2026, 9, 26, 22, tzinfo=TZ))
    result = run(
        _ctx(conn, full_settings, thursday_clock, family, busy=busy), SuggestInput(**WEEKEND)
    )
    [matinee] = result.web_finds
    assert (matinee.title, matinee.verdict) == ("Matinee", "good")
    assert matinee.reasons[0] == "on Saturday 14:00-16:00" and matinee.fits_days == ["2026-09-26"]
    late = _logged(conn)["Late show"]
    assert late["verdict"] == "ruled_out" and late["reasons"][0].startswith("busy while it is on")


def test_rain_makes_an_outdoor_find_possible(conn, full_settings, thursday_clock, family):
    _found(conn, "Pumpkin patch", "2026-09-27", setting="outdoor")
    result = run(_ctx(conn, full_settings, thursday_clock, family), SuggestInput(**WEEKEND))
    [patch] = result.web_finds
    assert patch.verdict == "possible" and any("rain" in reason for reason in patch.reasons)


def test_who_it_is_for_and_the_familys_rules_hold(conn, full_settings, thursday_clock, family):
    loud = _rule(conn, "No loud places", {"avoid": ["loud"]})
    near = _rule(conn, "Nothing over 30 minutes away", {"max_travel_minutes": 30})
    _found(conn, "Wine walk", "2026-09-26", participants=["grown-ups"])
    _found(conn, "Rock night", "2026-09-26", summary="A loud gig in the park")
    _found(conn, "Far fair", "2026-09-26", lat=47.6, lon=-122.3)  # Seattle, hours away
    _found(conn, "Story time", "2026-09-26", participants=["whole family"])
    asked = SuggestInput(**{**WEEKEND, "participants": ["the girls"]})
    result = run(_ctx(conn, full_settings, thursday_clock, family), asked)
    assert [one.title for one in result.web_finds] == ["Story time"]
    logged = _logged(conn)
    assert logged["Wine walk"]["reasons"] == ["for grown-ups"]
    assert logged["Rock night"]["reasons"] == [f"loud, which m{loud} rules out"]
    assert logged["Far fair"]["reasons"][0] == f"further than m{near} allows"
    # Nothing a find stood in as reaches the log or the result.
    row = suggestions.list_recent(conn, limit=1)[0]
    assert all(candidate["idea_id"] > 0 for candidate in row.candidates)
    assert all("idea_id" not in find for find in row.web_finds)
