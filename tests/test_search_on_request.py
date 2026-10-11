"""Searching on request (docs/FINDS.md; scouting/search.py `search_for`): every planning question
searches the web once, for events and places alike, told the question in their words and the
family's brief; what it finds is kept in the back pocket and offered with the answer, marked when
already saved, never when passed on, and never the grown-ups' alone where a kid reads."""

from __future__ import annotations

import dataclasses

from familydb.scouting import search
from familydb.store import db, finds, ideas, memories, messages
from familydb.suggest.engine import run
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
    "any_time": True,
    "for_whom": ["whole family"],
    "why": "They love noodles.",
}
JAZZ = {
    "title": "Late jazz set",
    "url": "https://club.example.com/jazz",
    "summary": "A trio at ten.",
    "starts_on": "2026-09-20",
    "starts_time": "20:00",
    "for_whom": ["grown-ups"],
    "why": "A night out for two.",
}
ASKED = {"window": "today", "topic": "thai food", "question": "Anything Thai for us today?"}


def _ctx(conn, full_settings, clock, family, api, cache, message_id=None, **changes):
    settings = full_settings.model_copy(update={"web_tools_enabled": True, **changes})
    ctx = ToolContext(
        conn=conn, settings=settings, clock=clock, member=family["sam"], message_id=message_id
    )
    ctx.api, ctx.discover_cache = api, cache
    return ctx


def _message(conn, family, update: str) -> int:
    with db.transaction(conn):
        return messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=update,
            chat_id="42",
            member_id=family["sam"].id,
            text="…",
            now=NOW_ISO,
        ).id


def test_a_planning_question_searches_with_everything_known_and_keeps_it(
    conn, full_settings, clock, family
):
    with db.transaction(conn):
        memories.insert(
            conn,
            member_id=family["alex"].id,
            category="food",
            fact="Alex is allergic to peanuts",
            firm=True,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=None,
            now=NOW_ISO,
        )
    api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI, JAZZ]))
    ctx = _ctx(conn, full_settings, clock, family, api, {})
    result = run(ctx, SuggestInput(**ASKED))
    jazz, thai = result.web_finds  # on in the free time, before a place whose hours are unknown
    assert (jazz.verdict, thai.verdict) == ("good", "possible")
    # The one to mention after what is theirs: none was put forward by an evening, so the first
    # checked good.
    assert result.new_find == "Late jazz set"
    assert (thai.title, thai.any_time, thai.for_whom, thai.why) == (
        "Thai Bloom",
        True,
        ["whole family"],
        "They love noodles.",
    )
    assert jazz.starts == "2026-09-20T20:00" and jazz.find_id is not None
    asked = str(api.requests[0]["messages"])
    assert "They asked: Anything Thai for us today?" in asked
    assert "Looking for: thai food." in asked and "Musts (keep to these)" in asked
    # Names never leave the house: a person is who they are.
    assert "a grown-up: a grown-up is allergic to peanuts" in asked and "Alex" not in asked
    assert [row[0] for row in conn.execute("SELECT kind FROM llm_calls")] == ["discover"] * 2
    # Kept in the back pocket, by its page, as found on request.
    kept = finds.get(conn, thai.find_id)
    assert (kept.kind, kept.any_time, kept.participants) == ("request", True, ["whole family"])
    # The same ask in other words is the same search.
    run(ctx, SuggestInput(**{**ASKED, "question": "thai, anywhere?"}))
    assert len(api.requests) == 2


def test_one_search_a_message(conn, full_settings, clock, family):
    api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI]))
    ctx = _ctx(conn, full_settings, clock, family, api, {}, _message(conn, family, "u1"))
    run(ctx, SuggestInput(**ASKED))
    other = run(ctx, SuggestInput(**{**ASKED, "window": "next_weekend"}))
    assert len(api.requests) == 2 and search.NOTE_ONCE in other.skipped_checks
    # What the first search kept is still offered: a place any time is in the pocket.
    assert [one.title for one in other.web_finds] == ["Thai Bloom"]


def test_saved_is_marked_and_passed_on_is_not_offered(conn, full_settings, clock, family):
    with db.transaction(conn):
        kept = ideas.insert(conn, title="Thai Bloom", kind="restaurant", now=NOW_ISO)
        [passed], _ = finds.keep(
            conn, "request", "request", [finds.NewFind(title="Jazz", url=JAZZ["url"])], now="1"
        )
        finds.mark_passed(conn, passed.id, by=None, why=None, now="1")
    api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI, JAZZ]))
    found = run(_ctx(conn, full_settings, clock, family, api, {}), SuggestInput(**ASKED))
    assert [(one.title, one.saved_as) for one in found.web_finds] == [("Thai Bloom", kept.id)]


def test_where_a_kid_reads_the_grown_ups_finds_are_left_out(conn, full_settings, clock, family):
    api = fakes.FakeMessagesAPI(*fakes.discover_script([THAI, JAZZ]))
    ctx = _ctx(conn, full_settings, clock, family, api, {})
    kid = dataclasses.replace(ctx, member=family["girls"])
    assert [one.title for one in run(kid, SuggestInput(**ASKED)).web_finds] == ["Thai Bloom"]


def test_no_search_with_web_lookups_off_or_when_not_asked(conn, full_settings, clock, family):
    api = fakes.FakeMessagesAPI()  # nothing scripted: a call would fail the test
    off = _ctx(conn, full_settings, clock, family, api, {}, web_tools_enabled=False)
    assert search.NOTE_OFF in run(off, SuggestInput(**ASKED)).skipped_checks
    on = _ctx(conn, full_settings, clock, family, api, {})
    run(on, SuggestInput(**{**ASKED, "discover": False}))
    assert api.requests == []
