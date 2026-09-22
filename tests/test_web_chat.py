"""The chat page: talking to the bot from a browser."""

from __future__ import annotations

import re
import threading

import pytest

from familydb.app import App
from familydb.channels.web import BUSY, DEFAULT_CHAT, UNKNOWN_MEMBER
from familydb.store import messages
from familydb.web import create_app
from tests import fakes

PASSWORD = "open sesame please"


def _client(settings, clock, *responses):
    """A signed-in client whose model is a script of replies, so a whole turn runs offline."""
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    api = fakes.FakeMessagesAPI(*responses) if responses else None
    web = create_app(app, api=api)
    client = web.test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.chat = web.config["FAMILYDB_CHAT"]
    return client


def _token(client, path: str = "/chat") -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get(path).text)
    assert found is not None
    return found.group(1)


def _say(client, text: str, who: str = "Sam", **extra):
    form = {"csrf": _token(client), "text": text, "who": who, **extra}
    return client.post("/chat", data=form)


@pytest.fixture
def replies():
    return [fakes.message([fakes.text("Saturday looks dry. The museum?")])]


def test_an_empty_chat_says_so(settings, clock, conn, family) -> None:
    page = _client(settings, clock).get("/chat")
    assert page.status_code == 200
    assert "Nothing said here yet" in page.text
    assert "Sam" in page.text and "the girls" in page.text  # everyone can be spoken for


def test_a_message_goes_through_the_pipeline_and_the_answer_lands_on_the_page(
    settings, clock, conn, family, replies
) -> None:
    client = _client(settings, clock, *replies)
    sent = _say(client, "what should we do this weekend?")
    assert sent.status_code == 302 and sent.headers["Location"] == "/chat"
    assert client.chat.wait(10)

    page = client.get("/chat").text
    assert "what should we do this weekend?" in page
    assert "Saturday looks dry. The museum?" in page
    assert 'http-equiv="refresh"' not in page  # nothing left to wait for

    thread = messages.last_for_chat(conn, DEFAULT_CHAT, limit=10)
    assert [(m.direction, m.status) for m in thread] == [("in", "processed"), ("out", "processed")]
    assert thread[0].member_id == family["sam"].id
    assert thread[0].channel == "web"


def test_the_page_says_it_is_thinking_and_asks_to_be_shown_again(
    settings, clock, conn, family
) -> None:
    """No script can scroll this page, so while a reply is coming it refreshes itself."""
    client = _client(settings, clock)
    asked, release = threading.Event(), threading.Event()

    def slow(**kwargs):
        asked.set()
        assert release.wait(10)
        return fakes.message([fakes.text("done")])

    client.chat._api = type("Slow", (), {"create": staticmethod(slow)})()
    _say(client, "take your time")
    assert asked.wait(10)

    page = client.get("/chat").text
    assert 'http-equiv="refresh"' in page
    assert "Thinking about the last message" in page
    assert "disabled" in page  # and nothing can be sent on top of it

    refused = _say(client, "are you there?")
    assert refused.status_code == 400 and BUSY in refused.text
    release.set()
    assert client.chat.wait(10)


def test_a_message_from_somebody_who_is_not_family_is_refused(settings, clock, conn, family):
    client = _client(settings, clock)
    refused = _say(client, "hello", who="Mallory")
    assert refused.status_code == 400
    assert UNKNOWN_MEMBER.format(name="Mallory") in refused.text
    assert messages.last_for_chat(conn, DEFAULT_CHAT, limit=10) == []


def test_nothing_typed_sends_nothing(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    assert _say(client, "   ").status_code == 400
    assert messages.last_for_chat(conn, DEFAULT_CHAT, limit=10) == []


def test_a_message_longer_than_the_limit_is_refused(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    refused = _say(client, "x" * 4001)
    assert refused.status_code == 400 and "couple of messages" in refused.text
    assert messages.last_for_chat(conn, DEFAULT_CHAT, limit=10) == []


def test_the_page_remembers_who_was_talking(settings, clock, conn, family, replies) -> None:
    client = _client(settings, clock, *replies)
    _say(client, "hello", who="Alex")
    assert client.chat.wait(10)
    assert '<option value="Alex" selected>' in client.get("/chat").text


def test_a_message_from_another_site_is_refused(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    elsewhere = {"Origin": "https://evil.example"}
    refused = client.post(
        "/chat", data={"csrf": _token(client), "text": "hi", "who": "Sam"}, headers=elsewhere
    )
    assert refused.status_code == 400 and "did not come from this page" in refused.text
    assert messages.last_for_chat(conn, DEFAULT_CHAT, limit=10) == []


def test_a_form_without_this_session_s_token_is_refused(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    refused = client.post("/chat", data={"csrf": "not-the-one", "text": "hi", "who": "Sam"})
    assert refused.status_code == 400 and "too old to use" in refused.text
    assert messages.last_for_chat(conn, DEFAULT_CHAT, limit=10) == []


def test_the_chat_is_behind_the_password(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    stranger = create_app(app).test_client()
    assert stranger.get("/chat").headers["Location"] == "/login?next=/chat"
    assert stranger.post("/chat", data={"text": "hi", "who": "Sam"}).status_code == 401


def test_a_message_left_unanswered_by_a_restart_says_so(settings, clock, conn, family) -> None:
    """Nothing is thinking about it any more, so the page stops waiting and offers it back."""
    client = _client(settings, clock)
    with client.application.config["FAMILYDB_APP"].connect() as own:
        from familydb.store.db import transaction

        with transaction(own):
            messages.insert_in(
                own,
                channel="web",
                channel_update_id="gone",
                chat_id=DEFAULT_CHAT,
                member_id=family["sam"].id,
                text="what happened to this?",
            )
    page = client.get("/chat").text
    assert "never answered" in page
    assert 'http-equiv="refresh"' not in page
    assert "what happened to this?" in page  # and it comes back in the box


def test_a_reply_the_turn_failed_to_produce_is_shown_as_trouble(settings, clock, conn, family):
    client = _client(settings, clock, fakes.rate_limit_error())
    _say(client, "this will not go well")
    assert client.chat.wait(10)
    page = client.get("/chat").text
    assert "retry later" in page  # the pipeline's own notice to the family, stored as a reply
    assert "this one did not go through" in page
