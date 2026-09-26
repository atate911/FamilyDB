"""Buttons under a reminder and a follow-up, and what a tap on one does, with no model asked."""

from datetime import datetime, timedelta

import pytest

from familydb import buttons
from familydb.app import App
from familydb.store import db, ideas, messages, outcomes, plans, tasks
from familydb.tools import ToolContext
from familydb.tools.registry import ToolResult
from familydb.tools.tasks import AddTaskInput, add_task
from tests.conftest import NOW_ISO


def _task(settings, clock, conn, family, title="Bins out"):
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    return add_task(ctx, AddTaskInput(title=title, remind_at="2026-09-20T18:00"))["task"]


def _tap(app, conn, data, *, tap_id="q1", who="1001"):
    return buttons.tap(
        app,
        conn,
        channel="telegram",
        chat_id="42",
        channel_user_id=who,
        tap_id=tap_id,
        data=data,
    )


def _plan(conn, family, *, idea_id, start="2026-09-19", title="Hopscotch"):
    with db.transaction(conn):
        return plans.insert(
            conn,
            title=title,
            start=start,
            end=None,
            all_day=True,
            idea_id=idea_id,
            created_by=family["sam"].id,
            channel="telegram",
            chat_id="42",
            now="2026-09-18T00:00:00Z",
        )


def _idea(conn, title="Hopscotch Portland", **fields):
    with db.transaction(conn):
        return ideas.insert(conn, title=title, kind="outing", now=NOW_ISO, **fields)


def test_what_a_reminder_and_a_follow_up_come_with() -> None:
    assert buttons.for_reminder(12) == [
        {"label": "✓ Done", "data": "done:12"},
        {"label": "In an hour", "data": "hour:12"},
        {"label": "Tomorrow", "data": "tomorrow:12"},
    ]
    assert [b["data"] for b in buttons.for_follow_up(31)] == [
        "again:31",
        "not_again:31",
        "missed:31",
    ]
    # Telegram hands back at most 64 bytes of a button, whatever its number.
    longest = buttons.for_follow_up(10**18 - 1) + buttons.for_reminder(10**18 - 1)
    assert max(len(b["data"].encode()) for b in longest) <= 64


def test_done_is_done_once_and_kept_as_a_message(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    task = _task(settings, clock, conn, family)
    tapped = _tap(app, conn, f"done:{task['id']}")
    assert tapped == buttons.Tapped("Ticked off ✓ (Sam).", "Ticked off ✓ (Sam).", finished=True)
    assert tasks.get(conn, task["id"]).status == "done"
    kept = messages.recent_for_chat(conn, "42", limit=5, since="2000-01-01")
    assert [m.text for m in kept] == [f"(tapped) ✓ Done: task #{task['id']} Bins out"]
    assert kept[0].member_id == family["sam"].id and kept[0].status == "processed"
    assert kept[0].actions == [{"tool": "update_task", "ok": True, "task_id": task["id"]}]
    audit = conn.execute("SELECT tool_name FROM tool_calls WHERE message_id = ?", (kept[0].id,))
    assert [row[0] for row in audit] == ["update_task"]
    # The same tap delivered again is done once; a second tap finds nothing left to do.
    assert _tap(app, conn, f"done:{task['id']}") is None
    again = _tap(app, conn, f"done:{task['id']}", tap_id="q2")
    assert again == buttons.Tapped("That one's already taken care of.", finished=True)
    assert len(messages.recent_for_chat(conn, "42", limit=5, since="2000-01-01")) == 1


def test_snoozing_moves_the_reminder(settings, clock, conn, family) -> None:
    app = App(settings, clock)  # Sunday 20 September, 14:03
    task = _task(settings, clock, conn, family)
    tapped = _tap(app, conn, f"hour:{task['id']}")
    assert tapped.note == "I'll bring it up again at 15:03 today (Sam)."
    assert tasks.get(conn, task["id"]).reminder.remind_at == "2026-09-20T22:03:00Z"
    tapped = _tap(app, conn, f"tomorrow:{task['id']}", tap_id="q2")
    assert tapped.note == "I'll bring it up again at 14:03 tomorrow (Sam)."
    reminder = tasks.get(conn, task["id"]).reminder
    assert (
        reminder.remind_at == "2026-09-21T21:03:00Z"
        and tasks.get(conn, task["id"]).status == "open"
    )


def test_when_a_snooze_comes_back_reads_after_until_and_at() -> None:
    now = datetime(2026, 9, 20, 14, 3)
    today = now.date()
    assert buttons.when_text(now + timedelta(hours=1), today) == "15:03 today"
    assert buttons.when_text(now + timedelta(days=1), today) == "14:03 tomorrow"
    assert buttons.when_text(now + timedelta(days=3), today) == "14:03 on Wed 23 Sep"


def test_a_follow_up_is_answered_by_tapping(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    idea = _idea(conn)
    plan = _plan(conn, family, idea_id=idea.id)
    tapped = _tap(app, conn, f"again:{plan.id}")
    assert tapped.note == "Noted, Sam: one to do again." and tapped.finished
    recorded = outcomes.list_for_idea(conn, idea.id)
    assert [(o.plan_id, o.happened_on, o.would_repeat) for o in recorded] == [
        (plan.id, "2026-09-19", True)
    ]
    assert ideas.get(conn, idea.id).status == "done"
    # Said already: another answer changes nothing.
    assert _tap(app, conn, f"not_again:{plan.id}", tap_id="q2").toast == (
        "That one's already taken care of."
    )
    assert len(outcomes.list_for_idea(conn, idea.id)) == 1


def test_not_again_and_didnt_go(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    dud = _idea(conn, "Loud arcade")
    missed = _idea(conn, "Falls hike", status="planned")
    dropped = _idea(conn, "Old idea", status="dropped")
    tapped = _tap(app, conn, f"not_again:{_plan(conn, family, idea_id=dud.id).id}")
    assert tapped.note == "Noted, Sam: not one to repeat."
    assert outcomes.list_for_idea(conn, dud.id)[0].would_repeat is False
    # Didn't go is not an outcome: the idea goes back on the list to come up again.
    tapped = _tap(app, conn, f"missed:{_plan(conn, family, idea_id=missed.id).id}", tap_id="q2")
    assert tapped.note == "No harm done, Sam: it's back on the list."
    assert ideas.get(conn, missed.id).status == "idea"
    assert outcomes.list_for_idea(conn, missed.id) == []
    # A dropped idea is not brought back by it.
    tapped = _tap(app, conn, f"missed:{_plan(conn, family, idea_id=dropped.id).id}", tap_id="q3")
    assert tapped.toast == "That one's already taken care of."
    assert ideas.get(conn, dropped.id).status == "dropped"


@pytest.mark.parametrize(
    "data",
    [
        "done:",
        "done:abc",
        "done:-1",
        "drop:1",
        "done:1:2",
        "",
        "done:" + "9" * 30,
        "done:999",
        "done:\u0661",  # an Arabic-Indic one: a digit to Python, not in what a button sends
    ],
)
def test_nonsense_and_the_gone_do_nothing(settings, clock, conn, family, data) -> None:
    """What a button sends back is checked like anything a client sends."""
    tapped = _tap(App(settings, clock), conn, data)
    assert tapped == buttons.Tapped(
        "That button's gone stale; tell me in words instead.", finished=True
    )
    assert messages.recent_for_chat(conn, "42", limit=5, since="2000-01-01") == []


def test_somebody_not_in_the_family_cannot(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    task = _task(settings, clock, conn, family)
    tapped = _tap(app, conn, f"done:{task['id']}", who="9999")
    assert tapped == buttons.Tapped("Sorry, only the family can use these.")  # buttons stay
    assert tasks.get(conn, task["id"]).status == "open"
    assert messages.recent_for_chat(conn, "42", limit=5, since="2000-01-01") == []


def test_a_tap_that_does_not_go_through_says_so(settings, clock, conn, family, monkeypatch) -> None:
    app = App(settings, clock)
    task = _task(settings, clock, conn, family)
    monkeypatch.setattr(
        app.registry, "dispatch", lambda *_: ToolResult('{"error": "busy"}', is_error=True)
    )
    tapped = _tap(app, conn, f"done:{task['id']}")
    assert tapped == buttons.Tapped("That didn't go through. Could you tell me in words?")
    kept = messages.recent_for_chat(conn, "42", limit=5, since="2000-01-01")
    assert kept[0].status == "processed" and kept[0].actions == []  # never a turn to retry


def test_a_tap_asks_no_model(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"anthropic_api_key": ""}), clock)
    task = _task(settings, clock, conn, family)
    assert _tap(app, conn, f"done:{task['id']}").finished
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


# -- going out with them -------------------------------------------------------------------------


def _telegram_task(clock, conn, title="Bins out", remind_at="2026-09-20T21:05:00Z"):
    from familydb import task_service

    return task_service.create(
        conn,
        {"title": title},
        reminder=remind_at,
        operation_key=f"test:{title}",
        channel="telegram",
        chat_id="42",
        now=NOW_ISO,
    )


def test_a_reminder_goes_with_its_buttons_where_they_can_be_shown(settings, clock, conn, family):
    from familydb.jobs.reminders import run_reminders

    app = App(settings, clock)
    plain, rich = [], []
    app.senders["telegram"] = lambda chat, text: plain.append((chat, text))
    app.button_senders["telegram"] = lambda chat, text, row: rich.append((chat, text, row))
    task = _telegram_task(clock, conn)
    clock.advance(timedelta(minutes=2))
    assert run_reminders(app) == 1
    assert plain == [] and len(rich) == 1
    chat, text, row = rich[0]
    assert chat == "42" and text.startswith("Reminder: Bins out")
    assert row == buttons.for_reminder(task.id)
    assert messages.get(conn, tasks.get(conn, task.id).reminder.message_id).buttons == row


def test_where_they_cannot_be_shown_its_words_go_alone(settings, clock, conn, family):
    from familydb.jobs.reminders import run_reminders

    app = App(settings, clock)  # nothing here can show a button: the manual retry command, say
    plain = []
    app.senders["telegram"] = lambda chat, text: plain.append(text)
    _telegram_task(clock, conn)
    clock.advance(timedelta(minutes=2))
    assert run_reminders(app) == 1
    assert len(plain) == 1 and plain[0].startswith("Reminder: Bins out")


def test_a_follow_up_goes_with_its_answers_when_there_is_an_idea(
    settings, thursday_clock, conn, family
):
    from familydb.jobs.follow_ups import run_follow_ups

    app = App(settings, thursday_clock)  # Thursday 24 September
    rich, plain = [], []
    app.senders["telegram"] = lambda chat, text: plain.append(text)
    app.button_senders["telegram"] = lambda chat, text, row: rich.append(row)
    idea = _idea(conn)
    with_idea = _plan(conn, family, idea_id=idea.id)
    _plan(conn, family, idea_id=None, title="Dentist")  # nothing to record an answer against
    assert run_follow_ups(app) == 2
    assert rich == [buttons.for_follow_up(with_idea.id)]
    assert len(plain) == 1 and "Dentist" in plain[0]
