"""The scouting layer (familydb/scouting): every web search to find something new goes through it.
The move into it changed no request: each is byte-identical to what the code sent before
(tests/scouting_requests.json, rendered from fixed inputs by the code as it was). Since, the
search on request opens with its own first line, and the places search is gone into it."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from familydb.base.config import Settings
from familydb.moment import Constraints, Context, DayContext, Origin
from familydb.scouting.fill import render_enrich_request
from familydb.scouting.near_home import render_feeds_request, render_scout_request
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
    assert render_scout_request(settings, SAT, date(2026, 10, 22)) == BEFORE["scout"]
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
