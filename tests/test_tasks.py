"""Task persistence, delivery recovery, capture, and context selection regressions."""

import re
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from familydb.app import App
from familydb.delivery import lease, run_deliveries
from familydb.errors import ToolError
from familydb.jobs.reminders import run_reminders
from familydb.store import db, ideas, messages, tasks
from familydb.suggest.engine import run
from familydb.suggest.types import SuggestInput
from familydb.tools.ideas import DescribeIdeaInput, describe_idea
from familydb.tools.tasks import AddTaskInput, UpdateTaskInput, add_task, update_task
from tests.test_web_edits import _client


def add(ctx, **fields):
    return add_task(ctx, AddTaskInput(title="Buy paper towels", **fields))["task"]


def test_deadlines_and_flexible_windows_do_not_schedule_reminders(ctx):
    task = add(ctx, due_at="2026-09-22T09:00", preferred_window="Some Saturday")
    assert task["due_at"] == "2026-09-22T16:00:00Z"
    assert task["reminder"] is None
    assert task["owner"] == "Sam"
    assert not ctx.conn.execute("SELECT * FROM plans").fetchall()


def test_retry_after_due_time_returns_the_original_task(ctx):
    ctx.operation_id = "durable-form-key"
    task = add(ctx, remind_at="2026-09-20T14:04")
    ctx.clock.advance(timedelta(minutes=5))
    assert add(ctx, remind_at="2026-09-20T14:04")["id"] == task["id"]
    assert ctx.conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1


@pytest.mark.parametrize(
    "moment", ["2026-09-20", "2026-09-20T13:00", "2027-03-14T02:30", "2026-11-01T01:30"]
)
def test_invalid_or_ambiguous_reminder_time_is_refused(ctx, moment):
    ctx.clock.tz = ZoneInfo("America/Los_Angeles")
    with pytest.raises(ToolError):
        add(ctx, remind_at=moment)
    assert tasks.list_all(ctx.conn) == []


def test_overdue_reminder_survives_restart_and_is_queued_once(ctx):
    task = add(ctx, remind_at="2026-09-20T14:04")
    ctx.clock.advance(timedelta(minutes=5))
    app = App(ctx.settings, ctx.clock)
    assert run_reminders(app) == 1
    assert run_reminders(App(ctx.settings, ctx.clock)) == 0
    reminder = tasks.get(ctx.conn, task["id"])["reminder"]
    assert reminder["delivered_at"]
    assert len(messages.last_for_chat(ctx.conn, "web", limit=100)) == 1


def test_failed_send_retries_without_creating_another_message(ctx):
    with db.transaction(ctx.conn):
        origin = messages.insert_in(
            ctx.conn,
            channel="telegram",
            channel_update_id="1",
            chat_id="family-group",
            member_id=ctx.member.id,
            text="Remind me",
            now=ctx.now_iso(),
        )
    ctx.message_id = origin.id
    task = add(ctx, remind_at="2026-09-20T14:04")
    ctx.clock.advance(timedelta(minutes=2))
    app = App(ctx.settings, ctx.clock)
    assert run_reminders(app) == 0
    queued = tasks.get(ctx.conn, task["id"])["reminder"]["message_id"]
    sent = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    assert run_reminders(app) == 1
    assert tasks.get(ctx.conn, task["id"])["reminder"]["message_id"] == queued
    assert sent[0][0] == "family-group"


def test_completion_cancels_queued_delivery_and_reopen_does_not_restore(ctx):
    task = add(ctx, remind_at="2026-09-20T14:04")
    ctx.clock.advance(timedelta(minutes=2))
    app = App(ctx.settings, ctx.clock)
    app.senders.clear()
    assert run_reminders(app) == 0
    update_task(ctx, UpdateTaskInput(task_id=task["id"], status="done"))
    app.senders["web"] = lambda chat, text: pytest.fail("cancelled reminder sent")
    assert run_deliveries(app) == 0
    assert messages.last_for_chat(ctx.conn, "web", limit=100) == []
    update_task(ctx, UpdateTaskInput(task_id=task["id"], status="open"))
    assert run_reminders(app) == 0


def test_snooze_replay_and_stale_revision(ctx):
    task = add(ctx, remind_at="2026-09-20T14:04")
    args = UpdateTaskInput(task_id=task["id"], remind_at="2026-09-21T09:00")
    first = update_task(ctx, args)["task"]["reminder"]["id"]
    assert update_task(ctx, args)["task"]["reminder"]["id"] == first
    ctx.task_revision = 1
    with pytest.raises(ToolError, match="changed"):
        update_task(ctx, UpdateTaskInput(task_id=task["id"], title="Overwrite"))


def test_in_flight_reminder_cannot_be_recalled(ctx):
    task = add(ctx, remind_at="2026-09-20T14:04")
    ctx.clock.advance(timedelta(minutes=2))
    app = App(ctx.settings, ctx.clock)
    app.senders.clear()
    run_reminders(app)
    message_id = tasks.get(ctx.conn, task["id"])["reminder"]["message_id"]
    with lease(app, ctx.conn, message_id) as owned:
        assert owned
        with pytest.raises(ToolError, match="being delivered"):
            update_task(ctx, UpdateTaskInput(task_id=task["id"], status="done"))


def test_browser_task_form_and_revision_guard(settings, clock, conn, family):
    client = _client(settings, clock)
    page = client.get("/tasks")
    assert page.status_code == 200
    form = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', page.text))
    form.update(title="Dentist appointment to arrange", remind_at="2026-09-22T09:00")
    assert client.post("/tasks/new", data=form).status_code == 302
    assert client.post("/tasks/new", data=form).status_code == 302
    task = tasks.list_all(conn)[0]
    assert len(tasks.list_all(conn)) == 1
    page = client.get("/tasks")
    assert "Scheduled" in page.text
    edit = dict(form, revision="0", once="new-edit", status="done")
    client.post(f"/task/{task['id']}/edit", data=edit)
    assert tasks.get(conn, task["id"])["status"] == "open"
    assert client.get("/tasks?status=invalid").status_code == 400


def test_topic_selection_is_applied_before_shortlist_limit(ctx):
    with db.transaction(ctx.conn):
        for n in range(12):
            ideas.insert(ctx.conn, title=f"Walk {n}", kind="outing")
        sushi = ideas.insert(ctx.conn, title="Sushi with the girls", kind="restaurant")
    result = run(
        ctx, SuggestInput(window="someday", question="Sushi?", idea_ids=[sushi.id], discover=False)
    )
    assert [c.idea_id for c in result.candidates] == [sushi.id]


def test_original_free_form_idea_is_recoverable(ctx):
    raw = "Maybe food carts near the river with the girls, sometime sunny?"
    with db.transaction(ctx.conn):
        origin = messages.insert_in(
            ctx.conn,
            channel="web",
            channel_update_id="raw-idea",
            chat_id="web",
            member_id=ctx.member.id,
            text=raw,
        )
        idea = ideas.insert(
            ctx.conn, title="Food cart afternoon", kind="outing", source_message_id=origin.id
        )
    assert describe_idea(ctx, DescribeIdeaInput(id=idea.id))["original_message"] == raw


def test_free_form_capture_hands_the_words_to_chat(settings, clock, conn, family, monkeypatch):
    client = _client(settings, clock)
    page = client.get("/ideas")
    assert "Save a thought for later" in page.text
    form = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', page.text))
    raw = "Maybe a McMenamins passport stop with food carts nearby?"
    form.update(text=raw, who="Sam", intent="save_idea")
    received = []
    chat = client.application.config["FAMILYDB_CHAT"]
    monkeypatch.setattr(chat, "ask", lambda *args: received.append(args))
    assert client.post("/chat", data=form).status_code == 302
    assert received == [("Save this idea for later:\n" + raw, "Sam", "web")]
