"""A fresh install has no model key yet, and nothing may break or be lost for want of one.

Everything that would ask a model checks first: chat says plainly that a key is missing, lookups
wait with the ideas still pending, the digest is skipped, and discovery says why it did not run.
"""

from __future__ import annotations

from datetime import date

import pytest

from familydb import voice
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.integrations.geocode import GeoPoint
from familydb.jobs.enrich import run_enrichment
from familydb.jobs.weekend_digest import run_digest
from familydb.pipeline import handle_incoming
from familydb.store import db, ideas, messages
from familydb.suggest.context import build_context
from familydb.suggest.discover import NOTE_NO_KEY, discover
from familydb.suggest.types import Constraints
from familydb.tools import ToolContext
from familydb.web import create_app

NO_KEYS = {"anthropic_api_key": None, "openai_api_key": None, "gemini_api_key": None}


@pytest.fixture
def keyless(settings, monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return settings.model_copy(
        update={
            **NO_KEYS,
            "web_tools_enabled": True,
            "home_lat": 45.63,
            "home_lon": -122.67,
            "digest_chat_id": "web",
        }
    )


def test_a_message_is_saved_and_the_reply_says_a_key_is_missing(keyless, clock, conn, family):
    reply = handle_incoming(
        App(keyless, clock),
        IncomingMessage("telegram", "1", "chat-1", "1001", "we should try the ramen place"),
        conn=conn,
    )
    assert reply is not None and reply.text == voice.say(keyless, "no_key")
    stored = messages.get(conn, reply.in_message_id)
    assert stored.text == "we should try the ramen place"  # nothing the family said is lost
    assert stored.give_up  # and the retry job does not keep trying without a key


def test_ideas_wait_for_a_key_rather_than_fail(keyless, clock, conn, family) -> None:
    point = GeoPoint(45.5, -122.6, "Hopscotch", "nominatim")
    from tests.fakes import FakeGeocoder

    app = App(keyless, clock, geocoder=FakeGeocoder(default=point))
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch, Portland", kind="outing")
    assert run_enrichment(app) == {"done": 0, "skipped": 0, "failed": 0, "deferred": 0}
    assert ideas.get(conn, idea.id).enrichment == "pending"


def test_no_digest_is_attempted_without_a_key(keyless, clock, conn, family) -> None:
    app = App(keyless, clock)
    assert run_digest(app) is None
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0


def test_discovery_says_it_is_waiting_for_a_key(keyless, clock, conn, family) -> None:
    ctx = ToolContext(conn=conn, settings=keyless, clock=clock, member=family["sam"])
    context = build_context(ctx, (date(2026, 9, 26), date(2026, 9, 27)))
    assert discover(ctx, context, Constraints()) == ([], NOTE_NO_KEY)


def test_the_status_page_says_what_waits_for_a_key(keyless, clock, conn, family) -> None:
    page = create_app(App(keyless, clock)).test_client()
    text = page.get("/status").text
    assert "waiting for a model key" in text
    assert "once there is a model key to write it" in text
    # With no model it cannot answer anyone, so the home page is the setup page until there is.
    assert page.get("/").headers["Location"] == "/setup"
    setup = page.get("/setup").text
    assert "Connect an AI model" in setup and "No AI key yet, so it cannot answer." in setup
