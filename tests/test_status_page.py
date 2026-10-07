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
    assert owner("gemini-3.8-flash") == "gemini"
    assert owner("something-else") is None and owner(None) is None


def test_it_says_who_answers_and_where_each_key_came_from(status, conn, settings) -> None:
    with db.transaction(conn):
        settings_store.set_many(
            conn,
            {
                "gemini_api_key": "gm-never-shown",
                "provider": "gemini",
                "gemini_worker_model": "gemini-3.8-flash",
                "digest_level": "best",
            },
        )
    text = _flat(status.get("/status"))
    # Chat on Google's cheapest, from the page's own setting; the digest a level up; the lookups
    # on the model typed for them.
    assert "Google Gemini, gemini-3.1-flash-lite" in text
    assert "The weekend digest" in text and "Google Gemini, gemini-3.1-pro-preview (best)" in text
    assert "Google Gemini, gemini-3.8-flash" in text
    assert "Claude (Anthropic) answers instead" in text  # the environment's key is the spare
    assert "set on this page" in text and "set in the environment" in text
    assert "no key" in text  # OpenAI
    assert "gm-never-shown" not in text and settings.anthropic_api_key not in text


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
    _call(conn, model="gemini-3.8-flash", usage={"input_tokens": 300, "output_tokens": 50})
    text = _flat(status.get("/status"))
    assert "2 calls in 30 days" in text
    assert "44% of what was sent came back from the cache" in text
    assert "4,800" in text and "claude-opus-5" in text
    assert "gemini-3.8-flash (Google Gemini)" in text  # the last one, and who served it


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
        conn.execute("UPDATE messages SET retries = 1 WHERE id = ?", (stuck.id,))  # one try
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
    _call(conn, model="gemini-3.8-flash", stop="max_tokens")
    _call(conn, model="claude-opus-5", stop="end")  # an ordinary one is not worth a look
    text = _flat(status.get("/status"))
    assert "Worth checking" in text
    assert "gemini-3.8-flash — max_tokens" in text
    assert "worker: no website found" in text and "#1 Ramen place" in text
    assert "claude-opus-5 — end" not in text


def test_the_page_warns_near_the_limit_and_rests_past_it(status, conn) -> None:
    def spend(dollars: float) -> None:
        with db.transaction(conn):
            calls.log_llm_call(
                conn,
                message_id=None,
                iteration=1,
                model="claude-opus-5",
                served_model="claude-opus-5",
                request_id="r",
                stop_reason="end",
                usage={"input_tokens": 100, "output_tokens": 10},
                duration_ms=1000,
                now=NOW_ISO,
                cost_usd=dollars,
            )

    spend(1.6)  # of the $2.00 limit
    text = _flat(status.get("/status"))
    assert "Near the limit" in text and 'class="meter__fill"' in text
    assert "is ready." in text and "well under budget" not in text
    spend(0.5)
    text = _flat(status.get("/status"))
    assert "Limit reached" in text and "is resting until midnight." in text
    assert "nothing more is asked of a model until midnight" in text


def test_the_status_page_is_behind_the_password(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.get("/status").headers["Location"] == "/login?next=/status"
    client.post("/login", data={"password": PASSWORD})
    assert client.get("/status").status_code == 200


def test_a_connected_calendar_says_who_it_is_shared_with(settings, clock, conn, family):
    key = settings.google_key_path
    key.write_text('{"type": "service_account", "client_email": "bot@p.iam.gserviceaccount.com"}')
    app = App(settings.model_copy(update={"google_calendar_id": "family@group.calendar"}), clock)
    text = _flat(create_app(app).test_client().get("/status"))
    assert "reached as bot@p.iam.gserviceaccount.com" in text


def test_a_calendar_named_but_not_signed_into_is_not_connected(settings, clock, conn, family):
    app = App(settings.model_copy(update={"google_calendar_id": "family@group.calendar"}), clock)
    text = _flat(create_app(app).test_client().get("/status"))
    assert "not connected yet: connect it on the settings page" in text
    assert "No home coordinates" in text


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
    assert '20 Sep, <span class="fig">2:03 pm</span>' in _flat(
        status.get("/status")
    )  # NOW_ISO is 21:03 UTC
    assert utc_iso(clock.now()) == NOW_ISO


def test_a_new_install_starts_by_adding_yourself(settings, clock, conn) -> None:
    """The installer asks for no name: the first setup step on the page is adding yourself."""
    from familydb import family
    from familydb.web.status import services, setup_steps

    app = App(settings, clock)
    first = setup_steps(app, conn)[0]
    assert first == {
        "text": "Add yourself, as an admin, then the rest of the family.",
        "link": "/setup/you",
        "need": "needed",
    }
    family.add(conn, "Sam", "admin", telegram_id=None, now=NOW_ISO)
    assert all(step["link"] != "/setup/you" for step in setup_steps(app, conn))
    named = settings.model_copy(update={"google_calendar_id": "family@example.com"})
    calendar = next(s for s in services(App(named, clock), conn) if "calendar" in str(s).lower())
    assert "familydb auth google" not in str(calendar) and "settings page" in str(calendar)


def test_each_part_says_how_it_stands_and_the_verdict_agrees(status) -> None:
    text = _flat(status.get("/status"))
    assert "How each part is doing" in text
    for area in (
        "Spending",
        "Sign-in",
        "Backup",
        "Telegram",
        "Google Calendar",
        "Looking things up",
    ):
        assert f'<span class="item__title">{area}</span>' in text, area
    # A part that is not connected yet is a choice, said in words and not as a fault.
    assert (
        "Not connected" in text
        and "Telegram and Google Calendar aren\u2019t connected yet." in text
    )


def test_the_verdict_is_built_from_the_parts_it_sits_over() -> None:
    from familydb.web.status import Pill, verdict

    parts = [
        {"area": "Spending", "state": "ok"},
        {"area": "Sign-in", "state": "look"},
        {"area": "Telegram", "state": "better"},
    ]
    ready = Pill("ready", "Vera is ready", "Ready")
    said = verdict(parts, name="Vera", standing=ready, spent=0.0, thirty=1.26)
    assert said["tone"] == "ok" and said["heading"] == "Vera is ready, and well under budget."
    assert "Nothing spent today; the last 30 days cost $1.26." in said["text"]
    assert (
        "Sign-in needs a look." in said["text"]
        and "Telegram isn\u2019t connected yet." in said["text"]
    )
    down = verdict(parts, name="Vera", standing=Pill("down", "", ""), spent=0.0, thirty=0.0)
    assert down["tone"] == "alert" and down["heading"] == "Vera can\u2019t answer right now."
    rest = verdict(parts, name="Vera", standing=Pill("rest", "", ""), spent=2.0, thirty=3.0)
    assert rest["tone"] == "warn" and "About $2.00 spent today" in rest["text"]
