"""The scouting layer (familydb/scouting): every web search to find something new goes through it.
The move into it changed no request: each is byte-identical to what the code sent before
(tests/scouting_requests.json, rendered from fixed inputs by the code as it was). Since, the
search on request opens with its own first line, the places search is gone into it, and the
scouting near home is told the night's theme and the family's brief."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from familydb.base.config import Settings
from familydb.moment import Constraints, Context, DayContext, Origin
from familydb.scouting.fill import render_enrich_request
from familydb.scouting.near_home import render_feeds_request, render_scout_request, theme_for
from familydb.scouting.reach import Reach
from familydb.scouting.search import cache_key, render_discover_request
from familydb.store.ideas import Idea
from familydb.store.places import Place
from familydb.tools import ToolContext

BEFORE = json.loads((Path(__file__).parent / "scouting_requests.json").read_text())
SAT, SUN = date(2026, 9, 26), date(2026, 9, 27)
TODAY = date(2026, 9, 24)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        provider="anthropic",
        home_area="Vancouver, WA",
        family_tz="America/Vancouver",
        home_lat=45.63,
        home_lon=-122.67,
    )


def _contexts() -> dict[str, Context]:
    whole = [DayContext(SAT, [(480, 1320)], True, None), DayContext(SUN, [(480, 1320)], True, None)]
    return {
        "plain": Context((SAT, SUN), whole, "autumn", TODAY),
        "evening": Context(
            (SAT, SAT),
            [DayContext(SAT, [(1020, 1320)], True, None, bounds=(1020, 1320))],
            "autumn",
            TODAY,
            origin=Origin(45.6201, -122.6702, "the Pearl", "the Pearl"),
        ),
        "mixed": Context(
            (SAT, SUN),
            [
                DayContext(SAT, [], True, None, bounds=(1020, 1320)),
                DayContext(SUN, [], True, None, bounds=(480, 720)),
            ],
            "autumn",
            TODAY,
        ),
        "someday": Context(None, [], "autumn", TODAY),
    }


HELD = Constraints(
    participants=["the girls"],
    max_cost_level=1,
    setting="indoor",
    max_travel_minutes=30,
    max_duration_minutes=90,
    topic="live jazz",
    avoid=["loud"],
)


@pytest.mark.parametrize("name", ["plain", "evening", "mixed", "someday"])
@pytest.mark.parametrize("held", ["none", "held"])
def test_the_searches_while_answering_ask_what_they_asked_before(name, held) -> None:
    settings, context = _settings(), _contexts()[name]
    constraints = HELD if held == "held" else Constraints()
    assert (
        render_discover_request(context, constraints, settings) == BEFORE[f"discover/{name}/{held}"]
    )


def test_the_searches_near_home_and_the_lookups_ask_what_they_asked_before() -> None:
    settings = _settings()
    assert [cache_key(None), cache_key((SAT, SUN))] == BEFORE["cache_key"]
    known, stopped = ["https://a.example/ics"], ["https://b.example/ics"]
    assert render_feeds_request(settings, known, stopped) == BEFORE["feeds"]
    assert render_feeds_request(settings, [], []) == BEFORE["feeds/none"]
    bare = Idea(id=9, kind="outing", title="Zoo", created_at="x", updated_at="x")
    assert render_enrich_request(bare, None, settings) == BEFORE["enrich/bare"]
    idea = Idea(
        id=7,
        kind="restaurant",
        title="Kenji's Ramen",
        description="the girls loved it",
        participants=["whole family"],
        location_name="SE Larkspur St",
        url="https://kenji.example",
        created_at="x",
        updated_at="x",
    )
    place = Place(
        id=3,
        name="Kenji's Ramen",
        address="1 Main St",
        website="https://kenji.example",
        hours={"sat": [{"open": "11:00", "close": "21:00"}]},
        created_at="x",
        updated_at="x",
    )
    assert render_enrich_request(idea, place, settings) == BEFORE["enrich/full"]


def test_a_search_made_while_answering_shares_the_app_s_cache(conn, settings, clock) -> None:
    cache: dict = {}
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, message_id=None)
    ctx.discover_cache = cache
    reach = Reach.of(ctx)
    assert reach.cache is cache and reach.conn is conn and reach.message_id is None


def test_scouting_is_told_the_night_s_theme_and_the_family() -> None:
    asked = render_scout_request(
        _settings(), SAT, date(2026, 10, 22), theme=theme_for(SAT), about_family="Who they are:"
    )
    assert asked.splitlines() == [
        "Tonight's theme: classes and clubs: lessons, workshops, sports, groups to join.",
        "Window: Saturday 26 September to Thursday 22 October 2026.",
        "Home area: Vancouver, WA.",
        "",
        "About the family:",
        "Who they are:",
    ]
    # A theme for each day of the week, none twice.
    assert len({theme_for(date(2026, 9, 21 + n)) for n in range(7)}) == 7


def test_what_scouting_hands_back_is_sorted_by_code(conn, settings) -> None:
    from familydb.scouting.near_home import sort
    from familydb.scouting.types import Found
    from familydb.store import db, finds, ideas, memories
    from tests.conftest import NOW_ISO

    with db.transaction(conn):
        ideas.insert(conn, title="Corn maze", kind="outing", now=NOW_ISO)
        [passed], _ = finds.keep(
            conn,
            "request",
            "request",
            [finds.NewFind(title="Old", url="https://a.example/o")],
            now="1",
        )
        finds.mark_passed(conn, passed.id, by=None, why=None, now="1")
        memories.insert(
            conn,
            member_id=None,
            category="other",
            fact="Nothing loud",
            firm=True,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=None,
            now=NOW_ISO,
            rule={"avoid": ["loud"]},
        )

    def found(title: str, **more) -> Found:
        return Found(**{"title": title, "url": f"https://x.example/{title}", **more})

    handed = [
        found("Lantern walk", starts="2026-10-01T19:00"),
        found("Rose garden", any_time=True),
        found("Corn maze", starts="2026-10-02"),  # already an idea
        found("Old", url="https://a.example/o", any_time=True),  # passed on
        found("Rock night", starts="2026-10-03", summary="A loud gig"),  # a firm rule avoids it
        found("Some day", dates="next spring"),  # no day code can read
        found("Gone by", starts="2026-09-01"),  # past
    ]
    kept = sort(conn, handed, today=SAT, end=date(2026, 10, 24))
    assert [one.title for one in kept] == ["Lantern walk", "Rose garden"]
