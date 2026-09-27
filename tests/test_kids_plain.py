"""Kids never see how the bot works (audience.py, voice.PLAIN): where a kid reads, a line about
a key, a model, a limit in dollars, an admin or the settings page is said plainly instead."""

import pytest

from familydb import audience, personas, voice
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
from familydb.store import db, members
from tests import fakes
from tests.conftest import NOW_ISO

# What a kid is never told: how the bot works, or who mends it.
MACHINERY = (
    "admin",
    "settings",
    "model",
    "key",
    "logs",
    "limit",
    "$",
    "offline",
    "restart",
    "openai",
    "gemini",
    "anthropic",
)


@pytest.fixture
def mia(conn):
    with db.transaction(conn):
        return members.add(
            conn, "Mia", "kid", channel="telegram", channel_user_id="3001", now=NOW_ISO
        )


def test_every_plain_line_is_a_line_and_says_nothing_of_the_workings(settings) -> None:
    for machinery, plain in voice.PLAIN.items():
        assert machinery in voice.EVENTS and plain in voice.EVENTS
    kid_lines = set(voice.PLAIN.values()) - {"reminder"}
    for key in (*personas.available(), personas.NONE):
        spoken = settings.model_copy(update={"persona": key})
        for event in kid_lines:
            for words in voice.reads_as(spoken, event):
                said = words.casefold()
                assert not [w for w in MACHINERY if w in said], (key, event, words)


def test_say_plainly_swaps_only_the_lines_about_the_workings(settings) -> None:
    assert voice.say(settings, "cannot_reach", plain=True) == voice.say(settings, "kid_later")
    assert voice.say(settings, "limit_reached", plain=True, limit="2.00") == voice.say(
        settings, "kid_tomorrow"
    )
    assert voice.say(settings, "cannot_reach") != voice.say(settings, "kid_later")
    # A line with nothing of the workings in it is the same either way.
    assert voice.say(settings, "kid_limit", plain=True, limit=10) == voice.say(
        settings, "kid_limit", limit=10
    )


def test_who_reads_a_chat(conn, family, mia) -> None:
    sam = family["sam"]
    # A kid's own chat, on Telegram or the page, and any group while there is a kid.
    assert audience.plain(conn, "telegram", "3001")
    assert audience.plain(conn, "web", f"member:{mia.id}")
    assert audience.plain(conn, "telegram", "-100")
    # A grown-up's own chat, and the page's shared conversation, which kids do not talk in.
    assert not audience.plain(conn, "telegram", "1001", sam)
    assert not audience.plain(conn, "web", "web", sam)
    # With no kid on the list, a group is grown-ups only.
    with db.transaction(conn):
        members.set_active(conn, mia.id, False)
        members.set_active(conn, family["girls"].id, False)
    assert not audience.plain(conn, "telegram", "-100", sam)


def _kid(text: str, update_id: str) -> IncomingMessage:
    return IncomingMessage("telegram", update_id, "3001", "3001", text)


def test_a_kid_is_told_plainly_when_it_cannot_answer(settings, clock, conn, family, mia) -> None:
    app = App(settings, clock)
    broken = fakes.FakeMessagesAPI(fakes.bad_request_error())
    reply = handle_incoming(app, _kid("can we get a kitten", "1"), api=broken, conn=conn)
    assert reply.status == "failed" and reply.text == voice.say(settings, "kid_later")
    busy = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    reply = handle_incoming(app, _kid("pleeease", "2"), api=busy, conn=conn)
    assert reply.text == voice.say(settings, "kid_later")


def test_in_a_group_with_a_kid_it_is_said_plainly_too(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    broken = fakes.FakeMessagesAPI(fakes.bad_request_error())
    group = IncomingMessage("telegram", "3", "-100", "1001", "hi all")
    reply = handle_incoming(app, group, api=broken, conn=conn)
    assert reply.text == voice.say(settings, "kid_later")


def test_a_grown_up_on_their_own_is_told_what_is_wrong(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    broken = fakes.FakeMessagesAPI(fakes.bad_request_error())
    alone = IncomingMessage("telegram", "4", "1001", "1001", "hi")
    reply = handle_incoming(app, alone, api=broken, conn=conn)
    assert reply.text == voice.say(settings, "cannot_reach")
