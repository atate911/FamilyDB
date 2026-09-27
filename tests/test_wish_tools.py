"""The wish tools, the line a kid's message carries, and the nudge towards "I want"."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from familydb import wording
from familydb.agent.render import render_kid_line
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.dates import utc_iso
from familydb.pipeline import handle_incoming
from familydb.store import db, members, wishes
from familydb.tools.registry import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO, TZ

NOW = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)


def _run(registry, name, values, ctx):
    result = registry.dispatch(name, values, ctx)
    output = json.loads(result.content)
    return {"error": output} if result.is_error else output


@pytest.fixture
def mia(conn, family):
    with db.transaction(conn):
        conn.execute(
            "UPDATE members SET display_name = 'Mia', birth_date = '2017-03-14', "
            "gender = 'female', channel = 'telegram', channel_user_id = '1003' WHERE id = ?",
            (family["girls"].id,),
        )
    return members.get(conn, family["girls"].id)


def _as(conn, settings, clock, who) -> ToolContext:
    return ToolContext(conn=conn, settings=settings, clock=clock, member=who)


# -- the tools ------------------------------------------------------------------------------------


def test_a_kid_puts_a_wish_on_her_own_list(conn, settings, clock, family, mia, registry) -> None:
    kid = _as(conn, settings, clock, mia)
    added = _run(registry, "add_wish", {"title": "An iPhone", "topic": "phone"}, kid)
    assert added["result"] == "added" and added["wish"]["occasion"] is None
    for_birthday = _run(
        registry, "add_wish", {"title": "Sushi", "topic": "sushi", "list": "birthday"}, kid
    )
    assert for_birthday["wish"]["occasion"] == "birthday"
    # Not on anybody else's list.
    other = _run(registry, "add_wish", {"title": "Slime", "topic": "slime", "for_whom": "Sam"}, kid)
    assert "error" in other and "her own list" in other["error"]["error"]


def test_a_parent_adds_for_a_kid_and_answers(conn, settings, clock, family, mia, registry) -> None:
    parent = _as(conn, settings, clock, family["alex"])
    kid = _as(conn, settings, clock, mia)
    added = _run(
        registry, "add_wish", {"title": "A cat", "topic": "pet", "for_whom": "Mia"}, parent
    )
    wish_id = added["wish"]["id"]
    assert wishes.get(conn, wish_id).member_id == mia.id
    refused = _run(registry, "update_wish", {"wish_id": wish_id, "status": "declined"}, kid)
    assert "error" in refused and "only a parent" in refused["error"]["error"]
    declined = _run(
        registry,
        "update_wish",
        {"wish_id": wish_id, "status": "declined", "answer_note": "Not with the allergies."},
        parent,
    )
    assert declined["wish"]["status"] == "declined" and declined["locked_until"] == "2026-10-04"
    again = _run(registry, "add_wish", {"title": "A dog", "topic": "pet"}, kid)
    assert again == {
        "result": "locked",
        "wish": {"id": wish_id, "title": "A cat", "occasion": None},
        "locked_until": "2026-10-04",
        "times_declined": 1,
    }


def test_she_moves_and_withdraws_her_own(conn, settings, clock, family, mia, registry) -> None:
    kid = _as(conn, settings, clock, mia)
    first = _run(registry, "add_wish", {"title": "Lego", "topic": "lego"}, kid)["wish"]["id"]
    second = _run(registry, "add_wish", {"title": "Kite", "topic": "kite"}, kid)["wish"]["id"]
    moved = _run(registry, "update_wish", {"wish_id": second, "position": 1}, kid)
    assert moved["wish"]["rank"] == 1
    flagged = _run(registry, "update_wish", {"wish_id": first, "list": "christmas"}, kid)
    assert wishes.get(conn, flagged["wish"]["id"]).occasion == "christmas"
    gone = _run(registry, "update_wish", {"wish_id": first, "status": "withdrawn"}, kid)
    assert gone["wish"]["status"] == "withdrawn"
    nothing = _run(registry, "update_wish", {"wish_id": second}, kid)
    assert "error" in nothing


def test_turning_away_is_for_a_kid_s_ask_and_kept_once(
    conn, settings, clock, family, mia, registry
) -> None:
    kid = ToolContext(conn=conn, settings=settings, clock=clock, member=mia, message_id=None)
    ask = {"summary": "more internet time", "concern": "rule", "parent_may_review": True}
    assert _run(registry, "turn_away", ask, kid) == {
        "ask_a_parent_offered": True,
        "parents_told": False,
    }
    parent = _as(conn, settings, clock, family["alex"])
    assert "error" in _run(registry, "turn_away", ask, parent)


# -- the nudge towards "I want" -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "we", "want"),
    [
        ("we should get a puppy", True, False),
        ("We could go to Disneyland!", True, False),
        ("can we have pizza tonight", True, False),
        ("let's get slime", True, False),
        ("I want a puppy", False, True),
        ("I'd like a puppy please", False, True),
        ("I\u2019d like a puppy", False, True),  # an iPad's apostrophe
        ("let\u2019s get slime", True, False),
        ("what's for dinner", False, False),
        ("do you think we should?", False, False),  # a question about "we", not an opener
    ],
)
def test_code_reads_how_she_asked(text, we, want) -> None:
    assert wording.says_we_should(text) is we
    assert wording.says_i_want(text) is want


def _said(conn, member_id, text, at: datetime) -> None:
    with db.transaction(conn):
        messages_ = conn.execute(
            "INSERT INTO messages (channel, chat_id, member_id, direction, text, received_at) "
            "VALUES ('web', 'web', ?, 'in', ?, ?)",
            (member_id, text, utc_iso(at)),
        )
        assert messages_.rowcount == 1


def test_a_nudge_at_most_once_a_day_and_rarer_as_she_improves(conn, settings, mia) -> None:
    now = NOW
    assert wording.choose(conn, settings, mia.id, "we should get a puppy", now) == "nudge"
    assert wording.choose(conn, settings, mia.id, "we should get slime", now) is None  # today
    # Said rarely: the next day is too soon, three days on is not.
    assert wording.choose(conn, settings, mia.id, "we should", now + timedelta(days=1)) is None
    assert wording.choose(conn, settings, mia.id, "we could", now + timedelta(days=3)) == "nudge"
    # Said often this week: every day.
    later = now + timedelta(days=10)
    for hours in (1, 2, 3):
        _said(conn, mia.id, "we should get a pony", later - timedelta(hours=hours + 20))
    assert wording.choose(conn, settings, mia.id, "we should", later) == "nudge"
    assert wording.choose(conn, settings, mia.id, "we should", later + timedelta(days=1)) == (
        "nudge"
    )


def test_asking_plainly_is_praised_now_and_then(conn, settings, mia) -> None:
    assert wording.choose(conn, settings, mia.id, "I want a puppy", NOW) == "praise"
    assert wording.choose(conn, settings, mia.id, "I want slime", NOW + timedelta(days=1)) is None
    assert wording.choose(conn, settings, mia.id, "I'd like it", NOW + timedelta(days=3)) == (
        "praise"
    )
    assert wording.choose(conn, settings, mia.id, "what's up", NOW + timedelta(days=9)) is None


# -- her line -------------------------------------------------------------------------------------


def test_her_line_is_short_and_says_only_what_code_chose() -> None:
    line = render_kid_line(
        "Mia", 9, "female", [("pet", "2026-10-04T07:00:00Z"), ("phone", None)], "nudge"
    )
    assert line == (
        "Mia is a girl, 9. Her wish topics: pet (locked to 2026-10-04), phone. Wording: nudge."
    )
    assert render_kid_line("Leo", None, "male", None, None) == "Leo is a boy."
    assert render_kid_line("Sky", 7, None, [("kite", None)], None) == (
        "Sky is a kid, 7. Their wish topics: kite."
    )


def test_a_kid_s_message_carries_her_line_and_a_grown_up_s_does_not(
    settings, clock, conn, family, mia
) -> None:
    app = App(settings, clock)
    with db.transaction(conn):
        wishes.insert(
            conn, member_id=mia.id, title="A cat", topic="pet", occasion=None, rank=1, now=NOW_ISO
        )
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("On your list!")]))
    handle_incoming(
        app,
        IncomingMessage("telegram", "k1", "1003", "1003", "we should get a puppy"),
        api=api,
        conn=conn,
    )
    sent = json.dumps(api.requests[0]["messages"][-1])
    assert "Mia is a girl, 9. Her wish topics: pet. Wording: nudge." in sent
    assert "2017" not in sent  # her age, never her birthday

    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sure.")]))
    handle_incoming(
        app,
        IncomingMessage("telegram", "s1", "1001", "1001", "we should get a puppy"),
        api=api,
        conn=conn,
    )
    assert "Wording" not in json.dumps(api.requests[0]["messages"][-1])


def test_in_a_shared_chat_her_topics_stay_hers(settings, clock, conn, family, mia) -> None:
    app = App(settings, clock)
    with db.transaction(conn):
        wishes.insert(
            conn, member_id=mia.id, title="A cat", topic="pet", occasion=None, rank=1, now=NOW_ISO
        )
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi Mia!")]))
    handle_incoming(
        app, IncomingMessage("telegram", "g1", "-500", "1003", "hello"), api=api, conn=conn
    )
    sent = json.dumps(api.requests[0]["messages"][-1])
    assert "Mia is a girl, 9." in sent and "pet" not in sent


def test_a_kid_s_own_conversation_on_the_page_is_private(conn, family) -> None:
    from familydb.agent.render import render_audience_line

    everyone = members.list_all(conn)
    assert render_audience_line("web", f"member:{family['girls'].id}", everyone) is None
    assert "everyone who signs in" in render_audience_line("web", "web", everyone)


# -- her share of the day, and her lookups ---------------------------------------------------------


def test_a_kid_past_her_share_is_told_by_code_and_nothing_is_asked(
    settings, clock, conn, family, mia
) -> None:
    app = App(settings.model_copy(update={"kid_daily_spend": 0.10}), clock)
    with db.transaction(conn):
        earlier = conn.execute(
            "INSERT INTO messages (channel, chat_id, member_id, direction, text, received_at) "
            "VALUES ('telegram', '1003', ?, 'in', 'hi', ?)",
            (mia.id, NOW_ISO),
        ).lastrowid
        conn.execute(
            "INSERT INTO llm_calls (message_id, iteration, model, created_at, cost_usd) "
            "VALUES (?, 0, 'm', ?, 0.12)",
            (earlier, NOW_ISO),
        )
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("never sent")]))
    reply = handle_incoming(
        app, IncomingMessage("telegram", "k9", "1003", "1003", "I want slime"), api=api, conn=conn
    )
    assert api.requests == []
    assert "That's all our chatting for today, Mia" in reply.text
    # A grown-up's messages are held only by the family's limit.
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sure.")]))
    handle_incoming(
        app, IncomingMessage("telegram", "s9", "1001", "1001", "hello"), api=api, conn=conn
    )
    assert len(api.requests) == 1


def test_a_kid_s_lookups_wait_for_the_hour_and_go_together(settings, conn, family, mia) -> None:
    from familydb.clock import FixedClock
    from familydb.jobs.enrich import _held_back
    from familydb.store import ideas

    with db.transaction(conn):
        hers = ideas.insert(conn, title="Thai place", kind="restaurant", suggested_by=mia.id)
        ours = ideas.insert(conn, title="Ramen", kind="restaurant", suggested_by=family["sam"].id)
    daytime = App(settings, FixedClock(datetime(2026, 9, 20, 14, 3), TZ))
    held = _held_back(daytime, conn)
    assert mia.id in held and family["sam"].id not in held
    waiting = ideas.pending_enrichment(conn, limit=10, holding=held)
    assert [i.id for i in waiting] == [ours.id]
    evening = App(settings, FixedClock(datetime(2026, 9, 20, settings.kid_lookup_hour, 5), TZ))
    assert _held_back(evening, conn) == ()
    assert {i.id for i in ideas.pending_enrichment(conn, limit=10)} == {hers.id, ours.id}
