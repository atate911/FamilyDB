"""Tasks and their reminders from the tools and the page, a thought saved for later, and a
question narrowed to the ideas it names."""

import json
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
from familydb.tools.tasks import (
    AddTaskInput,
    ListTasksInput,
    UpdateTaskInput,
    add_task,
    list_tasks,
    update_task,
)
from tests.test_web_edits import _client


def add(ctx, **fields):
    return add_task(ctx, AddTaskInput(title="Buy paper towels", **fields))["task"]


def test_a_reminder_is_answered_in_the_family_s_time_never_utc(ctx):
    """Shown its stored UTC ("…T15:00:00Z" for 8am in Vancouver), the model took that for the time
    and set 3pm; the result says the wall time it was asked for, the form it writes in."""
    task = add(ctx, remind_at="2026-09-26T08:00")
    assert task["reminder"]["remind_at"] == "2026-09-26T08:00"
    assert "Z" not in json.dumps(task)


def test_deadlines_and_flexible_windows_do_not_schedule_reminders(ctx):
    task = add(ctx, due_at="2026-09-22T09:00", preferred_window="Some Saturday")
    assert task["due_at"] == "2026-09-22T09:00"  # the family's wall time, as the model writes it
    assert task["reminder"] is None
    assert task["owner"] == "Sam"
    # The tool result is the task's columns, less its idempotency key and who made it (that is for
    # the page's "Set by", not for the model), and the ones kept for code while they are empty,
    # plus owner and reminder.
    from familydb.tools.tasks import UNSAID_WHEN_EMPTY

    columns = {row["name"] for row in ctx.conn.execute("PRAGMA table_info(tasks)")}
    unsaid = {"operation_key", "created_by_member_id", *UNSAID_WHEN_EMPTY}
    assert set(task) == columns - unsaid | {"owner", "reminder"}
    assert not ctx.conn.execute("SELECT * FROM plans").fetchall()


def test_the_task_list_sends_the_model_only_what_it_needs(ctx):
    add(ctx, due_at="2026-09-22T09:00", notes="x" * 4000, remind_at="2026-09-21T08:00")
    for number in range(30):
        add_task(ctx, AddTaskInput(title=f"Chore {number}"))
    listed = list_tasks(ctx, ListTasksInput())
    assert len(listed["tasks"]) == 25 and listed["not_shown"] == 6
    first = listed["tasks"][0]
    # Family time, as the model says it back; no channel, chat or bookkeeping fields.
    assert first["due"] == "2026-09-22T09:00" and first["reminder"] == "2026-09-21T08:00"
    assert first["reminder_sent"] is False and len(first["notes"]) == 201
    assert set(first) == {
        "id",
        "title",
        "status",
        "owner",
        "notes",
        "due",
        "reminder",
        "reminder_sent",
    }


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
    reminder = tasks.get(ctx.conn, task["id"]).reminder
    assert reminder.delivered_at
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
    # Past the minutes in which "Remind me" makes this a conversation under way, which would
    # hold the reminder for the reply instead (tests/test_voice.py).
    ctx.clock.advance(timedelta(minutes=6))
    app = App(ctx.settings, ctx.clock)
    assert run_reminders(app) == 0
    queued = tasks.get(ctx.conn, task["id"]).reminder.message_id
    sent = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    # Not tried again every minute by this job: the retry job has it, on its own interval.
    assert run_reminders(app) == 0 and not sent
    assert run_deliveries(app) == 1
    assert tasks.get(ctx.conn, task["id"]).reminder.message_id == queued
    assert sent[0][0] == "family-group"


def test_a_late_reminder_worded_again_still_says_when_it_was_due(ctx):
    task = add(ctx, remind_at="2026-09-20T15:00")
    ctx.clock.advance(timedelta(days=2))
    app = App(ctx.settings, ctx.clock)
    app.senders.clear()  # the send fails, so it waits for the retry job
    assert run_reminders(app) == 0
    update_task(ctx, UpdateTaskInput(task_id=task["id"], title="Buy kitchen roll"))
    queued = messages.get(ctx.conn, tasks.get(ctx.conn, task["id"]).reminder.message_id).text
    assert "Buy kitchen roll" in queued and "was due Sun 20 Sep at 3\u00a0pm" in queued


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
    message_id = tasks.get(ctx.conn, task["id"]).reminder.message_id
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
    client.post(f"/task/{task.id}/edit", data=edit)
    assert tasks.get(conn, task.id).status == "open"
    for odd in ("", "²", "1e3", "9" * 40):
        bad = dict(form, revision=odd, once=f"odd-{len(odd)}-{odd[:1]}", status="done")
        assert client.post(f"/task/{task.id}/edit", data=bad).status_code == 302
    bad = {k: v for k, v in form.items() if k != "revision"} | {"once": "none", "status": "done"}
    assert client.post(f"/task/{task.id}/edit", data=bad).status_code == 302
    assert tasks.get(conn, task.id).status == "open"
    assert client.get("/tasks?status=invalid").status_code == 400


def test_an_open_task_ticks_off_where_it_is_listed(settings, clock, conn, family):
    """The tick sends only "done" and the revision it was drawn at; the rest stays as it was."""
    client = _client(settings, clock)
    form = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', client.get("/tasks").text))
    form.update(title="Sharpen the knives", notes="At the market", preferred_window="Saturday")
    client.post("/tasks/new", data=form)
    task = tasks.list_all(conn)[0]
    page = client.get("/tasks").text
    tick = re.search(rf'action="/task/{task.id}/done">(.*?)</form>', page, re.S)
    assert tick is not None and "Mark done: Sharpen the knives" in tick.group(1)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', tick.group(1)))
    assert fields["back"] == "tasks"
    ticked = client.post(f"/task/{task.id}/done", data=fields)
    assert ticked.headers["Location"] == "/tasks"
    done = tasks.get(conn, task.id)
    assert done.status == "done" and done.notes == "At the market"
    assert done.preferred_window == "Saturday"
    assert f"/task/{task.id}/done" not in client.get("/tasks?status=done").text  # no tick left


def test_a_reminder_in_the_page_chat_is_ticked_or_snoozed_there(settings, clock, conn, family):
    """On Telegram a reminder carries Done, In an hour and Tomorrow; on the page it carried none,
    so somebody who only uses the page could not act on it where it arrived. The chat draws them
    as forms, through the same update_task, under the newest reminder of each open task."""
    from familydb import buttons

    client = _client(settings, clock)
    form = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', client.get("/tasks").text))
    client.post("/tasks/new", data={**form, "title": "Call the plumber"})
    task = tasks.list_all(conn)[0]
    with db.transaction(conn):
        for _ in range(2):  # reminded twice: the buttons go under the second only
            messages.insert_out(
                conn,
                channel="web",
                chat_id="web",
                text="Reminder: Call the plumber.",
                now="2026-09-20T21:00:00Z",
                buttons=buttons.for_reminder(task.id),
            )
    chat = client.get("/chat").text
    assert chat.count(f'action="/task/{task.id}/done"') == 1
    snooze = re.search(
        rf'action="/task/{task.id}/snooze">((?:(?!</form>).)*?value="tomorrow".*?)</form>',
        chat,
        re.S,
    )
    assert snooze is not None and "Tomorrow" in snooze.group(1)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', snooze.group(1)))
    assert fields["back"] == "chat" and fields["when"] == "tomorrow"
    snoozed = client.post(f"/task/{task.id}/snooze", data=fields, follow_redirects=True)
    assert "#1 Call the plumber comes back at 2:03\u00a0pm tomorrow." in snoozed.text
    assert tasks.get(conn, task.id).reminder.remind_at == "2026-09-21T21:03:00Z"
    chat = client.get("/chat").text
    done = re.search(rf'action="/task/{task.id}/done">(.*?)</form>', chat, re.S)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', done.group(1)))
    assert client.post(f"/task/{task.id}/done", data=fields).headers["Location"] == "/chat"
    assert tasks.get(conn, task.id).status == "done"
    assert f"/task/{task.id}/" not in client.get("/chat").text  # nothing left to press
    wrong = {**fields, "once": "again", "when": "next year"}
    client.post(f"/task/{task.id}/snooze", data=wrong)
    assert tasks.get(conn, task.id).status == "done"


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
            text=messages.CAPTURE_PREFIX + raw,
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
    monkeypatch.setattr(chat, "ask", lambda *args, **more: received.append((*args, more)))
    assert client.post("/chat", data=form).status_code == 302
    assert received == [("Save this idea for later:\n" + raw, "Sam", "web", None, {"photo": None})]


def test_an_idea_number_not_on_the_list_is_reported_not_silently_empty(ctx):
    with db.transaction(ctx.conn):
        sushi = ideas.insert(ctx.conn, title="Sushi with the girls", kind="restaurant")
        walk = ideas.insert(ctx.conn, title="Walk", kind="outing")
    only_wrong = run(
        ctx, SuggestInput(window="someday", question="Sushi?", idea_ids=[9999], discover=False)
    )
    assert {c.idea_id for c in only_wrong.candidates} == {sushi.id, walk.id}
    assert any("#9999" in note and "every idea" in note for note in only_wrong.skipped_checks)
    mixed = run(
        ctx,
        SuggestInput(
            window="someday", question="Sushi?", idea_ids=[sushi.id, 9999], discover=False
        ),
    )
    assert [c.idea_id for c in mixed.candidates] == [sushi.id]
    assert any("#9999" in note for note in mixed.skipped_checks)


def test_a_task_for_everyone_is_nobodys_and_says_where_it_will_go(ctx):
    """ "Remind us all" is a task with no owner, whose reminder goes to the family's chat; one for
    somebody else says so too. The model is told where in words it can say back."""
    for_all = add_task(ctx, AddTaskInput(title="Swim bags", owner="everyone"))
    assert for_all["task"]["owner_id"] is None
    assert for_all["reminder_destination"] == "the chat on the page"
    family_chat = ctx.settings.model_copy(update={"family_chat_id": "-100"})
    ctx.settings = family_chat
    assert add_task(ctx, AddTaskInput(title="Bins", owner="all of us"))["reminder_destination"] == (
        "the Telegram group"
    )
    mine = add_task(ctx, AddTaskInput(title="Call the plumber"))
    assert mine["reminder_destination"] == (
        "the chat on the page (on Telegram once you open your chat with Vera)"
    )
    alex = add_task(ctx, AddTaskInput(title="Pick up the cake", owner="Alex"))
    assert alex["reminder_destination"] == (
        "the chat on the page (on Telegram once Alex opens a chat with Vera)"
    )
    with db.transaction(ctx.conn):
        messages.insert_in(
            ctx.conn,
            channel="telegram",
            channel_update_id="hello",
            chat_id="1002",
            member_id=alex["task"]["owner_id"],
            text="/start",
            now="2026-09-01T00:00:00Z",
        )
    again = add_task(ctx, AddTaskInput(title="Pick up the candles", owner="Alex"))
    assert again["reminder_destination"] == "Alex's own chat on Telegram"
    moved = update_task(ctx, UpdateTaskInput(task_id=again["task"]["id"], owner="everyone"))
    assert moved["task"]["owner_id"] is None


def test_the_page_says_where_a_reminder_will_go(settings, clock, conn, family):
    from familydb.web import views

    saved = {
        "task": {"id": 7, "title": "Call the plumber", "reminder": None},
        "reminder_destination": "the chat on the page",
    }
    assert views.task_saved(saved) == "Added to your to-dos: Call the plumber."
    saved["task"]["reminder"] = {"remind_at": "2026-09-22T16:00:00Z"}
    assert views.task_saved(saved) == (
        "Added to your to-dos: Call the plumber. Its reminder goes to the chat on the page."
    )
