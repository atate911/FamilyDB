"""A place nothing saved fits, found on the web (suggest/places.py): only when the family has it
on, for a topic nothing framed for it fits, for now or the next days; said as found, never
checked, and marked when it is already on the list."""

from __future__ import annotations

from familydb.store import db, ideas
from familydb.suggest.engine import run
from familydb.suggest.places import render_places_request
from familydb.suggest.types import SuggestInput
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO

THAI = {
    "title": "Thai Bloom",
    "url": "https://thaibloom.example.com/",
    "summary": "Family-run Thai kitchen.",
    "kind": "restaurant",
    "hours": "Daily 11am-9pm",
    "address": "1200 Main St, Vancouver, WA",
}
ASKED = {"window": "now", "topic": "thai food", "discover": False, "question": "Thai open now?"}


def _ctx(conn, full_settings, clock, family, api, cache, **changes) -> ToolContext:
    settings = full_settings.model_copy(
        update={"web_tools_enabled": True, "find_places": True, **changes}
    )
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    ctx.api, ctx.discover_cache = api, cache
    return ctx


def test_nothing_saved_fits_so_a_place_is_looked_for(conn, full_settings, clock, family):
    api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI]))
    cache: dict = {}
    ctx = _ctx(conn, full_settings, clock, family, api, cache)
    result = run(ctx, SuggestInput(**ASKED))
    assert [f.model_dump(exclude_none=True) for f in result.web_finds] == [
        {**THAI, "source": "thaibloom.example.com"}
    ]
    request = api.requests[0]
    assert [t["name"] for t in request["tools"]] == ["report_finds", "web_search", "web_fetch"]
    asked = str(request["messages"])
    assert (
        "Find places for: thai food." in asked
        and "Open: Sunday 20 September 2026, 14:00-19:00." in asked
    )
    kind = conn.execute("SELECT kind FROM llm_calls").fetchall()
    assert [row[0] for row in kind] == ["places", "places"]  # the search, then the hand-back
    # Asked again within the hour: the same search, from the cache.
    run(ctx, SuggestInput(**{**ASKED, "question": "anything Thai?"}))
    assert len(api.requests) == 2


def test_one_already_saved_is_marked_with_its_number(conn, full_settings, clock, family):
    with db.transaction(conn):
        kept = ideas.insert(conn, title="Thai Bloom", kind="restaurant", now=NOW_ISO)
    ctx = _ctx(conn, full_settings, clock, family, fakes.FakeMessagesAPI(), {})
    framed = {**ASKED, "idea_ids": [kept.id]}
    # Framed for the topic and possible now: nothing is searched for.
    result = run(ctx, SuggestInput(**framed))
    assert result.web_finds == [] and ctx.api.requests == []
    with db.transaction(conn):
        ideas.update(conn, kept.id, {"status": "dropped"}, now=NOW_ISO)
        other = ideas.insert(
            conn,
            title="Bloom",
            kind="restaurant",
            url="https://www.thaibloom.example.com/menu",
            now=NOW_ISO,
        )
    ctx.api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI]))
    found = run(ctx, SuggestInput(**ASKED)).web_finds
    assert found[0].saved_as == other.id  # by its site, the one by its name being dropped


def test_it_is_the_familys_to_turn_on_and_only_for_near_days(conn, full_settings, clock, family):
    api = fakes.FakeMessagesAPI()  # nothing scripted: a call would fail the test
    off = _ctx(conn, full_settings, clock, family, api, {}, find_places=False)
    assert run(off, SuggestInput(**ASKED)).web_finds == []
    on = _ctx(conn, full_settings, clock, family, api, {})
    later = {**ASKED, "window": "dates", "start": "2026-09-25", "end": "2026-09-25"}
    assert run(on, SuggestInput(**later)).web_finds == []
    assert run(on, SuggestInput(**{**ASKED, "topic": ""})).web_finds == []
    assert api.requests == []


def test_the_request_is_the_framing_with_the_familys_limits(conn, full_settings, clock, family):
    from familydb.suggest.context import build_context
    from familydb.suggest.engine import resolve_window
    from familydb.suggest.types import Constraints

    ctx = _ctx(conn, full_settings, clock, family, None, {})
    window, _, bounds = resolve_window(SuggestInput(**ASKED), clock.now())
    context = build_context(ctx, window, bounds)
    limits = Constraints(topic="thai food", max_travel_minutes=30, avoid=["loud"])
    text = render_places_request(context, limits, ctx.settings)
    assert "Keep to: max_travel_minutes 30; avoid loud." in text
    assert "Home area: " in text and "the question" not in text
