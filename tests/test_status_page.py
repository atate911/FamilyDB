"""The status page: is it working, and what is it costing us?"""

from __future__ import annotations

import pytest

from familydb.agent.providers import owner
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import calls, db, ideas, messages
from familydb.store import settings as settings_store
from familydb.web import create_app
from tests.conftest import NOW_ISO

PASSWORD = "open sesame please"


@pytest.fixture
def status(settings, clock, conn, family):
    app = App(settings, clock)
    return create_app(app).test_client()


def _flat(response) -> str:
    """The page as one line, so an assertion never depends on where the template wrapped."""
    return " ".join(response.text.split())


def _call(conn, *, model: str, stop: str = "end", usage=None, duration=1000) -> None:
    with db.transaction(conn):
        calls.log_llm_call(
            conn,
            message_id=None,
            iteration=1,
            model=model,
            served_model=model,
            request_id="r",
            stop_reason=stop,
            usage=usage or {"input_tokens": 100, "output_tokens": 10},
            duration_ms=duration,
            now=NOW_ISO,
        )


def test_a_model_name_says_whose_it_is() -> None:
    assert owner("claude-opus-5") == "anthropic"
    assert owner("gpt-5-mini") == "openai" and owner("o3-mini") == "openai"
    assert owner("gemini-2.5-flash") == "gemini"
    assert owner("something-else") is None and owner(None) is None


def test_it_says_who_answers_and_where_each_key_came_from(status, conn, settings) -> None:
    with db.transaction(conn):
        settings_store.set_many(conn, {"gemini_api_key": "gm-never-shown", "provider": "gemini"})
    text = _flat(status.get("/status"))
    assert "Google Gemini, gemini-2.5-pro" in text  # chat, from the page's own setting
    assert "Google Gemini, gemini-2.5-flash" in text  # the lookup turns
    assert "Claude (Anthropic) answers instead" in text  # the environment's key is the spare
    assert "set on this page" in text and "set in the environment" in text
    assert "no key" in text  # OpenAI
    assert "gm-never-shown" not in text and settings.anthropic_api_key not in text


def test_a_quiet_month_says_so(status) -> None:
    assert "Nothing has been asked of a model in the last 30 days." in _flat(status.get("/status"))


def test_it_adds_up_what_the_models_cost(status, conn) -> None:
    _call(
        conn,
        model="claude-opus-5",
        usage={
            "input_tokens": 900,
            "cache_read_input_tokens": 4800,
            "cache_creation_input_tokens": 5000,
            "output_tokens": 120,
        },
        duration=3400,
    )
    _call(conn, model="gemini-2.5-flash", usage={"input_tokens": 300, "output_tokens": 50})
    text = _flat(status.get("/status"))
    assert "2 model calls in the last 30 days" in text
    assert "44% of what was sent came back from the cache" in text
    assert "4,800" in text and "claude-opus-5" in text
    assert "gemini-2.5-flash (Google Gemini)" in text  # the last one, and who served it


def test_it_shows_what_is_waiting(status, conn, family) -> None:
    with db.transaction(conn):
        for number in range(3):
            ideas.insert(conn, title=f"Idea {number}", kind="activity", now=NOW_ISO)
        ideas.update(conn, 2, {"enrichment": "done", "enriched_at": NOW_ISO}, now=NOW_ISO)
        stuck = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="9",
            chat_id="c",
            member_id=family["sam"].id,
            text="book us a table somewhere",
            now=NOW_ISO,
        )
        messages.mark_failed(conn, stuck.id, "AgentError: overloaded", now=NOW_ISO)
        assert messages.claim_retry(conn, stuck.id, 0) is True
    text = _flat(status.get("/status"))
    assert "2 waiting to be looked up" in text and "1 looked up" in text
    assert 'href="/idea/1"' in text and "#1 Idea 0" in text
    assert "book us a table somewhere" in text
    assert "AgentError: overloaded" in text and "1 try, will try again" in text


def test_it_shows_what_went_wrong(status, conn, family) -> None:
    with db.transaction(conn):
        ideas.insert(conn, title="Ramen place", kind="restaurant", now=NOW_ISO)
        ideas.update(
            conn,
            1,
            {
                "enrichment": "failed",
                "enrichment_note": "worker: no website found",
                "enriched_at": NOW_ISO,
            },
            now=NOW_ISO,
        )
    _call(conn, model="gemini-2.5-flash", stop="max_tokens")
    _call(conn, model="claude-opus-5", stop="end")  # an ordinary one is not worth a look
    text = _flat(status.get("/status"))
    assert "Worth a look" in text
    assert "gemini-2.5-flash — max_tokens" in text
    assert "worker: no website found" in text and "#1 Ramen place" in text
    assert "claude-opus-5 — end" not in text


def test_a_calm_page_says_nothing_is_wrong(status, conn) -> None:
    _call(conn, model="claude-opus-5")
    assert "Worth a look" not in _flat(status.get("/status"))


def test_the_status_page_is_behind_the_password(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.get("/status").headers["Location"] == "/login?next=/status"
    client.post("/login", data={"password": PASSWORD})
    assert client.get("/status").status_code == 200


def test_a_calendar_named_but_not_signed_into_is_not_connected(settings, clock, conn, family):
    app = App(settings.model_copy(update={"google_calendar_id": "family@group.calendar"}), clock)
    text = _flat(create_app(app).test_client().get("/status"))
    assert "nobody has signed in" in text
    assert "no home coordinates" in text


def test_the_status_page_asks_nothing_of_a_model(status, conn, monkeypatch) -> None:
    """It is a page someone refreshes; it must never be the thing that spends the budget."""
    from familydb.agent.providers.anthropic import AnthropicProvider

    def _boom(*_args, **_kwargs):
        raise AssertionError("the status page called a model")

    monkeypatch.setattr(AnthropicProvider, "send", _boom)
    assert status.get("/status").status_code == 200
    assert calls.recent_llm_calls(conn) == []


def test_the_page_after_a_failed_message_was_given_up_on(status, conn, family) -> None:
    with db.transaction(conn):
        stuck = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="1",
            chat_id="c",
            member_id=family["sam"].id,
            text="never mind",
            now=NOW_ISO,
        )
        messages.mark_failed(conn, stuck.id, "ConfigError: no credentials", now=NOW_ISO)
        messages.give_up(conn, stuck.id)
    text = _flat(status.get("/status"))
    assert "given up on" in text and "will try again" not in text


def test_the_dates_are_the_family_s(status, conn, clock) -> None:
    _call(conn, model="claude-opus-5")
    assert "20 Sep, 14:03" in _flat(status.get("/status"))  # NOW_ISO is 21:03 UTC
    assert utc_iso(clock.now()) == NOW_ISO
