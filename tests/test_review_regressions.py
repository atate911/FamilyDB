"""Failures found during the PR #4 review, exercised through application boundaries."""

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta

import pytest

from familydb import privacy
from familydb.agent import spending
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.errors import ToolError
from familydb.pipeline import handle_incoming
from familydb.store import db, ideas, messages, plans
from familydb.store import settings as settings_store
from familydb.tools import ToolContext
from familydb.web import create_app
from familydb.web.once import Once
from tests import fakes
from tests.test_web_once import _form
from tests.test_web_once import page as page
from tests.test_web_once import planning as planning


def test_restart_replay_keeps_one_calendar_event(planning, conn):
    form = {**_form(planning, "/plans"), "title": "Festival", "start": "2026-09-26T10:00"}
    planning.post("/plans/new", data=form)
    old = planning.application.config["FAMILYDB_APP"]
    restarted = create_app(App(old.settings, old.clock, calendar=planning.calendar)).test_client()
    restarted.set_cookie("session", planning.get_cookie("session").value)
    replay = restarted.post("/plans/new", data=form)
    assert replay.status_code == 302
    assert len(planning.calendar.events) == 1
    assert plans.get(conn, 1) is not None and plans.get(conn, 2) is None


def test_lost_google_response_recovers_same_operation(planning, conn):
    original = planning.calendar.insert_event

    def lose_response(**kwargs):
        original(**kwargs)
        raise ToolError("connection lost after insert")

    planning.calendar.insert_event = lose_response
    form = {**_form(planning, "/plans"), "title": "Festival", "start": "2026-09-26T10:00"}
    planning.post("/plans/new", data=form)
    assert plans.get(conn, 1) is None
    planning.application.config["FAMILYDB_ONCE"] = Once()
    planning.calendar.insert_event = original
    planning.post("/plans/new", data=form)
    assert len(planning.calendar.events) == 1
    assert plans.get(conn, 1) is not None and plans.get(conn, 2) is None


def test_lost_google_response_then_a_fresh_form_keeps_one_event(planning, conn):
    original = planning.calendar.insert_event

    def lose_response(**kwargs):
        original(**kwargs)
        raise ToolError("connection lost after insert")

    planning.calendar.insert_event = lose_response
    fields = {"title": "Festival", "start": "2026-09-26T10:00"}
    planning.post("/plans/new", data={**_form(planning, "/plans"), **fields})
    assert plans.get(conn, 1) is None and len(planning.calendar.events) == 1
    planning.calendar.insert_event = original
    # The family opens the form again: a new drawing, a new token, the same event asked for.
    second = {**_form(planning, "/plans"), **fields}
    planning.post("/plans/new", data=second)
    assert len(planning.calendar.events) == 1
    assert plans.get(conn, 1) is not None and plans.get(conn, 2) is None
    # That second form sent again after a restart, when nothing in memory remembers it: it
    # took over the first attempt for good, so it finds the plan rather than asking Google.
    old = planning.application.config["FAMILYDB_APP"]
    restarted = create_app(App(old.settings, old.clock, calendar=planning.calendar)).test_client()
    restarted.set_cookie("session", planning.get_cookie("session").value)
    assert restarted.post("/plans/new", data=second).status_code == 302
    assert len(planning.calendar.events) == 1 and plans.get(conn, 2) is None
    # Asking for it once more afterwards is a new plan, as it would be for anything finished.
    planning.post("/plans/new", data={**_form(planning, "/plans"), **fields})
    assert len(planning.calendar.events) == 2


def test_stale_edit_in_same_second_preserves_newer_save(page, conn):
    page.post("/ideas/new", data={**_form(page, "/ideas/new"), "title": "Museum", "kind": "outing"})
    revision = re.search(r'name="revision" value="([^"]+)"', page.get("/idea/1/edit").text).group(1)
    first = {
        **_form(page, "/idea/1/edit"),
        "revision": revision,
        "title": "Art museum",
        "kind": "outing",
    }
    second = {
        **_form(page, "/idea/1/edit"),
        "revision": revision,
        "title": "Museum",
        "kind": "outing",
        "tags": "art",
    }
    page.post("/idea/1/edit", data=first)
    rejected = page.post("/idea/1/edit", data=second)
    assert rejected.headers["Location"] == "/idea/1/edit"
    assert ideas.get(conn, 1).title == "Art museum"


def test_simultaneous_edits_only_commit_one_revision(settings, conn, clock, family):
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Museum", kind="outing")
    seen = ideas.revision(idea)
    barrier = threading.Barrier(2)
    app = App(settings, clock)

    def edit(title):
        with closing(app.connect()) as own:
            ctx = ToolContext(own, settings, clock, idea_revision=seen)
            barrier.wait(timeout=10)
            return app.registry.dispatch("update_idea", {"id": idea.id, "title": title}, ctx)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["First edit", "Second edit"]))
    assert sum(not result.is_error for result in results) == 1


def test_timezone_change_updates_planning_without_restart(settings, conn, family):
    app = App(settings, calendar=fakes.FakeCalendar(settings.tzinfo))
    with db.transaction(conn):
        settings_store.set_many(conn, {"family_tz": "America/New_York"}, source="review")
    app.refresh(conn)
    assert app.clock.tz.key == app.settings.tzinfo.key == "America/New_York"
    # Exercise the calendar tool's interpretation of a wall-clock time after the reload.
    future = (app.clock.today() + timedelta(days=2)).isoformat() + "T10:00"
    ctx = ToolContext(conn, app.settings, app.clock, calendar=app.calendar)
    # Calendar availability also checks the presence of a token.
    app.settings.google_token_path.write_text("{}")
    ctx.settings = app.settings.model_copy(update={"google_calendar_id": "family"})
    result = app.registry.dispatch("create_event", {"title": "Morning", "start": future}, ctx)
    assert not result.is_error
    expected = datetime.fromisoformat(future).replace(tzinfo=app.settings.tzinfo)
    assert plans.get(conn, 1).start == expected.isoformat(timespec="minutes")


def test_concurrent_model_calls_cannot_spend_same_remaining_allowance(
    settings, conn, clock, family
):
    limited = settings.model_copy(update={"daily_spend_limit": 0.001})
    app = App(limited, clock)
    entered, release = threading.Event(), threading.Event()

    class SlowAPI:
        requests = 0

        def create(self, **kwargs):
            self.requests += 1
            entered.set()
            assert release.wait(10)
            return fakes.message(
                [fakes.text("Answered.")], usage={"input_tokens": 1000, "output_tokens": 100}
            )

    api = SlowAPI()

    def ask(number):
        return handle_incoming(
            app, IncomingMessage("telegram", str(number), "chat", "1001", "hello"), api=api
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(ask, 1)
        assert entered.wait(10)
        others = [pool.submit(ask, number) for number in (2, 3)]
        release.set()
        results = [first.result(), *(future.result() for future in others)]
    assert api.requests == 1
    assert sum(result.status == "ok" for result in results) == 1
    assert sum("spending limit" in result.text for result in results) == 2


def test_spending_limit_after_write_reports_saved_idea(settings, conn, clock, family):
    limited = settings.model_copy(update={"daily_spend_limit": 0.001})
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tool_review", "add_idea", {"title": "Budget crossing idea", "kind": "outing"}
                )
            ],
            usage={"input_tokens": 1000, "output_tokens": 100},
        )
    )
    reply = handle_incoming(
        App(limited, clock),
        IncomingMessage("telegram", "budget", "chat", "1001", "save an idea"),
        api=api,
        conn=conn,
    )
    assert ideas.list_all(conn)[0].title == "Budget crossing idea"
    assert "Saved idea #1" in reply.text and "Ask again" not in reply.text
    assert messages.get(conn, reply.in_message_id).status == "processed"
    assert reply.actions[0]["tool"] == "add_idea"


def test_budget_interruption_reports_calendar_success(calendar_settings, conn, clock, family):
    limited = calendar_settings.model_copy(update={"daily_spend_limit": 0.001})
    calendar = fakes.FakeCalendar(clock.tz)
    app = App(limited, clock, calendar=calendar)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "calendar_review",
                    "create_event",
                    {"title": "Festival", "start": "2026-09-26T10:00"},
                )
            ],
            usage={"input_tokens": 1000, "output_tokens": 100},
        )
    )
    first = handle_incoming(
        app,
        IncomingMessage("telegram", "first", "chat", "1001", "schedule festival"),
        api=api,
        conn=conn,
    )
    assert "Created calendar plan #1" in first.text and len(calendar.events) == 1
    assert "nothing happens twice" in first.text  # Vera's line for it (personas/vera.lines.toml)
    assert messages.get(conn, first.in_message_id).status == "processed"
    assert len(api.requests) == 1


def test_privacy_tightening_does_not_require_getuid_on_windows(settings, monkeypatch):
    monkeypatch.setattr(privacy.os, "name", "nt")
    monkeypatch.delattr(privacy.os, "getuid", raising=False)
    assert privacy.tighten(settings) == []


def test_a_slow_call_does_not_hold_up_the_others(settings, conn, clock, family):
    app = App(settings, clock)
    first_in, second_done = threading.Event(), threading.Event()

    class SlowFirst:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                first_in.set()
                # The second call must finish while this one is still waiting on the network.
                assert second_done.wait(10)
            return fakes.message([fakes.text("Answered.")])

    api = SlowFirst()

    def ask(number):
        reply = handle_incoming(
            app, IncomingMessage("telegram", str(number), "chat", "1001", "hello"), api=api
        )
        if number == 2:
            second_done.set()
        return reply

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(ask, 1)
        assert first_in.wait(10)
        second = pool.submit(ask, 2)
        assert second.result(timeout=10).status == "ok"
        assert first.result(timeout=10).status == "ok"
    with closing(db.connect(settings.familydb_path)) as check:
        assert check.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0


def test_holds_are_given_back_and_a_crashed_one_expires(settings, conn, clock):
    limited = settings.model_copy(update={"daily_spend_limit": 1.0})
    now = clock.now()
    crashed = spending.admit(conn, limited, now - timedelta(minutes=40), 5.0)
    assert crashed
    # Forty minutes old: longer than any call runs, so it no longer counts.
    held = spending.admit(conn, limited, now, 5.0)
    # This one is in flight and holds more than the limit, so the next is refused.
    with pytest.raises(spending.SpendingLimitReached):
        spending.admit(conn, limited, now, 0.01)
    with db.transaction(conn):
        spending.settle(conn, held, now)
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0
    assert spending.admit(conn, limited, now, 0.01)


def test_a_failed_call_gives_its_hold_back(settings, conn, clock, family):
    class Down:
        def create(self, **kwargs):
            raise fakes.server_error()

    app = App(settings, clock)
    reply = handle_incoming(
        app, IncomingMessage("telegram", "down", "chat", "1001", "hello"), api=Down(), conn=conn
    )
    assert reply.status != "ok"
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0
