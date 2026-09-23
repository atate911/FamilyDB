"""Failures found during the PR #4 review, exercised through application boundaries."""

import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta

from familydb import privacy
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
    assert "do not repeat" in first.text
    assert messages.get(conn, first.in_message_id).status == "processed"
    assert len(api.requests) == 1


def test_privacy_tightening_does_not_require_getuid_on_windows(settings, monkeypatch):
    monkeypatch.setattr(privacy.os, "name", "nt")
    monkeypatch.delattr(privacy.os, "getuid", raising=False)
    assert privacy.tighten(settings) == []


def test_admission_blocks_other_process_and_recovers_after_crash(settings, conn, tmp_path):
    # File signals avoid terminating a process while it owns a multiprocessing Event mutex.
    script = """
import sys, time
from pathlib import Path
from familydb.store import db
from familydb.agent import admission
conn = db.connect(sys.argv[1])
Path(sys.argv[2]).touch()
with admission.locked(conn):
    Path(sys.argv[3]).touch()
    time.sleep(30)
"""
    workers = []

    def start(index):
        ready, acquired = tmp_path / f"ready{index}", tmp_path / f"acquired{index}"
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(settings.familydb_path), str(ready), str(acquired)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        workers.append(process)
        return ready, acquired

    def wait_for(path):
        deadline = time.monotonic() + 10
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert path.exists()

    try:
        _, acquired = start(0)
        wait_for(acquired)
        ready, acquired = start(1)
        wait_for(ready)
        time.sleep(0.2)
        assert not acquired.exists()
        workers[0].terminate()
        workers[0].wait(timeout=10)
        wait_for(acquired)
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.terminate()
            worker.communicate(timeout=10)
