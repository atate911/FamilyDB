"""Telling an admin what only an admin can fix: what counts, where it is noted, who is told."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from familydb import alerts, voice
from familydb.agent import spending
from familydb.agent.providers import build
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.base.errors import AgentError, ToolUnavailable
from familydb.store import alerts as alert_store
from familydb.store import messages
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.web import create_app
from tests import fakes
from tests.conftest import NOW, TZ
from tests.test_fallback import _both, _turn


def _found(conn) -> set[tuple[str, str]]:
    return {(row["kind"], row["subject"]) for row in conn.execute("SELECT * FROM alerts")}


# -- what counts


def test_each_company_s_empty_account_and_refused_key_are_read_as_such() -> None:
    import openai
    from google.genai import errors

    from familydb.agent.loop import worth_switching
    from familydb.agent.providers import anthropic as claude
    from familydb.agent.providers import gemini
    from familydb.agent.providers import openai as oa

    empty = openai.RateLimitError(
        "You exceeded your current quota",
        response=fakes._response(429),
        body={"code": "insufficient_quota", "message": "You exceeded your current quota"},
    )
    assert oa._failure(empty).trouble == "credit" and not oa._failure(empty).retryable
    assert oa._failure(fakes.openai_rate_limit()).trouble is None  # only slow down
    refused = openai.AuthenticationError("bad key", response=fakes._response(401), body=None)
    assert oa._failure(refused).trouble == "key"

    assert claude.trouble(400, "Your credit balance is too low to access the Anthropic API") == (
        "credit"
    )
    assert claude.trouble(401, "invalid x-api-key") == "key"
    # A refusal nothing here can read is still worth telling of, once it happens again.
    assert claude.trouble(400, "tools.0: bad schema") == "refused"
    assert claude.trouble(404, "Not found: /v1/messages/count") == "refused"  # not a model
    assert claude.trouble(429, "slow down") is None

    prepaid = errors.ClientError(
        429, {"error": {"message": "Your prepayment credits are depleted. Check billing."}}
    )
    assert gemini._failure(prepaid).trouble == "credit"
    assert gemini._failure(fakes.gemini_rate_limit()).trouble is None
    bad_key = errors.ClientError(400, {"error": {"message": "API key not valid."}})
    assert gemini._failure(bad_key).trouble == "key"

    # Both are worth asking the other company instead.
    assert worth_switching(AgentError("out of credit", retryable=False, trouble="credit"))
    assert worth_switching(AgentError("API error 401", retryable=False, trouble="key"))


# -- where it is noted


def test_an_empty_account_is_noted_even_when_the_other_company_answers(
    settings, registry, ctx
) -> None:
    import anthropic

    paired = _both(settings)
    empty = anthropic.BadRequestError(
        "Your credit balance is too low to access the Anthropic API",
        response=fakes._response(400),
        body=None,
    )
    primary = build("anthropic", paired, api=fakes.FakeMessagesAPI(empty))
    spare = build(
        "openai", paired, api=fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hi")]))
    )
    assert _turn(paired, registry, ctx, primary, spare).text == "Hi"
    assert _found(ctx.conn) == {("credit", "anthropic")}

    # Topped up: the next answer from Claude forgets it.
    topped = build(
        "anthropic", paired, api=fakes.FakeMessagesAPI(fakes.message([fakes.text("ok")]))
    )
    assert _turn(paired, registry, ctx, topped, None).text == "ok"
    assert _found(ctx.conn) == set()


def test_a_model_the_company_has_no_more_is_noted_and_forgotten_once_it_answers(
    settings, registry, ctx
) -> None:
    """A 404 for the model fails every call to it until an admin chooses another: noted by name, and
    the other company answers.
    """
    import anthropic

    paired = _both(settings)
    missing = anthropic.NotFoundError(
        "model: claude-opus-5", response=fakes._response(404), body=None
    )
    primary = build("anthropic", paired, api=fakes.FakeMessagesAPI(missing))
    spare = build(
        "openai", paired, api=fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hi")]))
    )
    assert _turn(paired, registry, ctx, primary, spare).text == "Hi"
    asked = primary.model_for("chat")
    assert _found(ctx.conn) == {("model", f"anthropic:{asked}")}
    detail = ctx.conn.execute("SELECT detail FROM alerts").fetchone()[0]
    assert f"no model called {asked}" in detail

    # Answered by that name again (a served snapshot may carry a date): the notice is forgotten.
    back = build(
        "anthropic",
        paired,
        api=fakes.FakeMessagesAPI(fakes.message([fakes.text("ok")], model=f"{asked}-20261001")),
    )
    assert _turn(paired, registry, ctx, back, None).text == "ok"
    assert _found(ctx.conn) == set()


def test_the_day_s_limit_is_noted_and_forgotten_once_a_call_is_let_through(conn, settings) -> None:
    now = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)
    tight = settings.model_copy(update={"daily_spend_limit": 0.01})
    with transaction(conn):
        conn.execute(
            "INSERT INTO llm_calls (iteration, model, created_at, cost_usd) VALUES (1, 'm', ?, 1)",
            ("2026-09-20T20:00:00Z",),
        )
    with pytest.raises(spending.SpendingLimitReached):
        spending.admit(conn, tight, now, 0.001)
    assert _found(conn) == {("limit", "2026-09-20")}
    spending.admit(conn, tight.model_copy(update={"daily_spend_limit": 50}), now, 0.001)
    assert _found(conn) == set()


def test_yesterday_s_limit_note_is_not_today_s_trouble(settings, clock, conn) -> None:
    from familydb.web import status

    app = App(settings, clock)
    yesterday = (clock.now() - timedelta(days=1)).date().isoformat()
    today = clock.now().date().isoformat()
    alerts.note(conn, "limit", yesterday, "used up", clock.now() - timedelta(days=1))
    assert status.light(app, conn) is None
    alerts.note(conn, "limit", today, "used up", clock.now())
    assert status.light(app, conn) == "bad"


def test_a_call_let_through_forgets_every_day_s_limit_note(conn, settings) -> None:
    now = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)
    alerts.note(conn, "limit", "2026-09-17", "used up", now - timedelta(days=3))
    alerts.note(conn, "limit", "2026-09-19", "used up", now - timedelta(days=1))
    spending.admit(conn, settings.model_copy(update={"daily_spend_limit": 50}), now, 0.001)
    assert _found(conn) == set()


def test_a_calendar_out_of_reach_is_its_own_note_and_forgotten_when_google_answers(
    calendar_settings, clock, conn
) -> None:
    app = App(calendar_settings, clock)
    app._calendar_said("not shared", True)
    assert _found(conn) == {("calendar_access", "")}
    assert "still shared" in alerts.wording(
        calendar_settings, alert_store.current(conn, since="2000-01-01")[0]
    )
    app._calendar_said(None, False)
    assert _found(conn) == set()


def test_each_calendar_trouble_is_worded_for_what_it_is(calendar_settings, clock, conn) -> None:
    app = App(calendar_settings, clock)
    app._calendar_said("Google no longer accepts the saved key", False)
    key = alerts.wording(calendar_settings, alert_store.current(conn, since="2000-01-01")[0])
    assert "key" in key and "shared" not in key  # the key, not the sharing, is what failed
    app._calendar_said(None, False)
    app._calendar_said("not shared", True)
    shared = alerts.wording(calendar_settings, alert_store.current(conn, since="2000-01-01")[0])
    assert "shared" in shared and "key" not in shared


def test_google_shutting_the_bot_out_is_noted_and_forgotten_when_it_answers(
    calendar_settings, clock, conn
) -> None:
    from google.auth.exceptions import RefreshError

    app = App(calendar_settings, clock)
    client = app.calendar
    assert client.report is not None

    class Refused:
        def execute(self):
            raise RefreshError("invalid_grant")

    class Fine:
        def execute(self):
            return {"items": []}

    with pytest.raises(ToolUnavailable):
        client._execute(Refused())
    assert _found(conn) == {("calendar", "")}
    client._execute(Fine())
    assert _found(conn) == set()


# -- who is told


def test_admins_on_telegram_are_told_once_and_again_while_it_lasts(settings, conn, family) -> None:
    sent: list[tuple[str, str]] = []
    clock = FixedClock(NOW, TZ)
    app = App(settings, clock)
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    alerts.note(conn, "credit", "openai", "insufficient_quota", clock.now())

    assert alerts.run_alerts(app) == 1
    wording = voice.say(settings, "alert_credit", company="OpenAI", limit="2.00")
    assert sent == [("1001", wording)]  # Sam, the admin; never Alex, a parent
    stored = messages.last_for_chat(conn, "1001", limit=1)[0]
    assert stored.text == wording and stored.delivered_at is not None
    assert alerts.run_alerts(app) == 0  # told already

    # Still going half a day later: told again. Gone quiet: not.
    later = App(settings, FixedClock(NOW + timedelta(hours=13), TZ))
    later.senders["telegram"] = app.senders["telegram"]
    assert alerts.run_alerts(later) == 0
    alerts.note(conn, "credit", "openai", "insufficient_quota", later.clock.now())
    assert alerts.run_alerts(later) == 1 and len(sent) == 2

    # Switched off on the settings page: nobody is told.
    alerts.note(conn, "key", "gemini", "API key not valid", later.clock.now())
    with transaction(conn):
        settings_store.set_many(conn, {"admin_alerts": False})
    assert alerts.run_alerts(later) == 0 and len(sent) == 2


def test_a_refusal_nothing_can_read_is_told_once_it_happens_again(
    settings, registry, ctx, family
) -> None:
    """One odd request is not news; the same company refusing twice with no answer between may be a
    change only an admin can look into.
    """
    import anthropic

    def refusing():
        said = anthropic.BadRequestError(
            "messages: an unexpected field", response=fakes._response(400), body=None
        )
        return build("anthropic", settings, api=fakes.FakeMessagesAPI(said))

    sent: list[tuple[str, str]] = []
    app = App(settings, ctx.clock)
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    with pytest.raises(AgentError):
        _turn(settings, registry, ctx, refusing(), None)
    assert _found(ctx.conn) == {("refused", "anthropic")}
    assert alerts.run_alerts(app) == 0 and sent == []  # once: not yet
    with pytest.raises(AgentError):
        _turn(settings, registry, ctx, refusing(), None)
    assert alerts.run_alerts(app) == 1
    assert sent[0][1].startswith("Anthropic keeps refusing what I send it")
    assert "an unexpected field" in sent[0][1]

    # It answers again: forgotten.
    fine = build(
        "anthropic", settings, api=fakes.FakeMessagesAPI(fakes.message([fakes.text("ok")]))
    )
    assert _turn(settings, registry, ctx, fine, None).text == "ok"
    assert _found(ctx.conn) == set()


def test_nothing_is_read_twice_or_asked_of_a_model_when_nothing_is_wrong(settings, clock, conn):
    app = App(settings, clock)
    app.senders["telegram"] = lambda chat, text: pytest.fail("nothing to say")
    assert alerts.run_alerts(app) == 0


def test_the_status_page_says_what_needs_attention_and_who_was_told(
    settings, clock, conn, family
) -> None:
    alerts.note(conn, "credit", "openai", "insufficient_quota", clock.now())
    text = create_app(App(settings, clock)).test_client().get("/status").text
    assert "Needs a look" in text and "OpenAI is out of credit" in text
    assert "admins are told on Telegram within a minute" in text
    with transaction(conn):
        alert_store.mark_told(conn, "credit", "openai", now="2026-09-20T21:04:00Z")
    text = create_app(App(settings, clock)).test_client().get("/status").text
    assert "admins told on Telegram 20 Sep, 2:04\u00a0pm" in text
