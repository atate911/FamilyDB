"""Tasks that come round again: on a schedule, or counted from when they were last done."""

from datetime import date, datetime, timedelta

import pytest

from familydb import buttons, task_service
from familydb.app import App
from familydb.jobs.reminders import run_reminders
from familydb.store import tasks
from familydb.tools import ToolContext
from familydb.tools.tasks import (
    AddTaskInput,
    ListTasksInput,
    UpdateTaskInput,
    add_task,
    list_tasks,
    update_task,
)
from tests.conftest import TZ

# The clock fixture: Sunday 20 September 2026, 14:03 in Vancouver.


def _ctx(settings, clock, conn, family) -> ToolContext:
    return ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])


def _add(ctx, **fields) -> dict:
    return add_task(ctx, AddTaskInput(title="Bins out", **fields))["task"]


def _update(ctx, task_id, **fields) -> dict:
    return update_task(ctx, UpdateTaskInput(task_id=task_id, **fields))["task"]


def _local(value: str) -> str:
    return datetime.fromisoformat(value).astimezone(TZ).strftime("%a %Y-%m-%d %H:%M")


def _sent(app) -> list[str]:
    said: list[str] = []
    app.senders["web"] = lambda chat, text: said.append(text)
    return said


# -- the arithmetic ------------------------------------------------------------------------------


def test_a_schedule_keeps_its_hour_on_the_wall_when_the_clocks_change() -> None:
    first = datetime(2026, 10, 25, 19, 0, tzinfo=TZ)  # PDT; the clocks go back on 1 November
    after = datetime(2026, 10, 26, 9, 0, tzinfo=TZ)
    later = task_service.next_time(first, 1, "week", after)
    assert later == datetime(2026, 11, 1, 19, 0, tzinfo=TZ)  # still 19:00, now PST
    assert later.utcoffset() == timedelta(hours=-8)


def test_the_end_of_a_month_does_not_drift() -> None:
    first = datetime(2026, 1, 31, 9, 0, tzinfo=TZ)
    times = []
    after = first
    for _ in range(3):
        after = task_service.next_time(first, 1, "month", after)
        times.append(after.date())
    assert times == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]
    assert task_service.shifted(date(2028, 2, 29), 1, "year") == date(2029, 2, 28)


def test_the_next_time_is_found_however_long_ago_the_first_was() -> None:
    first = datetime(2020, 1, 1, 8, 0, tzinfo=TZ)
    after = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)
    assert task_service.next_time(first, 1, "day", after) == datetime(2026, 9, 21, 8, 0, tzinfo=TZ)
    assert task_service.next_time(first, 3, "month", after) == datetime(
        2026, 10, 1, 8, 0, tzinfo=TZ
    )
    soon = datetime(2026, 9, 27, 19, 0, tzinfo=TZ)
    assert task_service.next_time(soon, 1, "week", after) == soon  # the first is still to come


# -- on a schedule -------------------------------------------------------------------------------


def test_a_weekly_reminder_comes_round_again(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    said = _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="week")
    assert (task["repeat_every"], task["repeat_unit"], task["repeat_from"]) == (
        1,
        "week",
        "schedule",
    )
    clock.advance(timedelta(hours=5))  # 19:03
    assert run_reminders(app) == 1 and said[-1].startswith("Reminder: Bins out")
    after = tasks.get(conn, task["id"])
    assert after.status == "open"
    assert _local(after.reminder.remind_at) == "Sun 2026-09-27 19:00"
    brief = list_tasks(ctx, ListTasksInput())["tasks"][0]
    assert brief["repeats"] == "every week" and brief["reminder"] == "2026-09-27T19:00"


def test_a_long_stretch_offline_sends_one_late_reminder_not_a_flood(settings, clock, conn, family):
    app = App(settings, clock)
    said = _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="day")
    clock.advance(timedelta(days=3))  # the bot was off: Wednesday 23rd, 14:03
    assert run_reminders(app) == 1 and "was due" in said[-1]
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Wed 2026-09-23 19:00"
    assert run_reminders(app) == 0  # and nothing more until then


def test_done_on_a_schedule_records_it_and_keeps_going(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="week")
    clock.advance(timedelta(hours=5))
    run_reminders(app)
    done = _update(ctx, task["id"], status="done")
    assert done["status"] == "open" and done["last_done_at"] == "2026-09-21T02:03:00Z"
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Sun 2026-09-27 19:00"
    # With nothing waiting (its reminder taken off), done starts it again from the schedule.
    _update(ctx, task["id"], clear_reminder=True)
    assert tasks.get(conn, task["id"]).reminder is None
    _update(ctx, task["id"], status="done")
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Sun 2026-09-27 19:00"


def test_a_snooze_moves_this_time_not_the_schedule(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="week")
    clock.advance(timedelta(hours=5))
    run_reminders(app)
    _update(ctx, task["id"], remind_at="2026-09-21T08:00")  # "tomorrow morning"
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Mon 2026-09-21 08:00"
    assert tasks.get(conn, task["id"]).repeat_anchor == task["repeat_anchor"]
    clock.advance(timedelta(hours=13))  # Monday 08:03
    assert run_reminders(app) == 1
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Sun 2026-09-27 19:00"


# -- counted from when it was done ---------------------------------------------------------------


def test_counted_from_done_comes_round_that_long_after(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    said = _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(
        ctx,
        remind_at="2026-09-20T15:00",
        repeat_every=6,
        repeat_unit="month",
        repeat_from="done",
    )
    clock.advance(timedelta(hours=1))
    assert run_reminders(app) == 1 and said
    assert tasks.get(conn, task["id"]).reminder.message_id is not None  # nothing more waits
    clock.advance(timedelta(days=4))  # done on Thursday 24th
    done = _update(ctx, task["id"], status="done")
    assert done["status"] == "open"
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Wed 2027-03-24 15:00"


# -- ending it, and what is refused ---------------------------------------------------------------


def test_stopping_or_cancelling_ends_it(settings, clock, conn, family) -> None:
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="week")
    one_off = _update(ctx, task["id"], stop_repeating=True)
    assert one_off["repeat_every"] is None and one_off["repeat_anchor"] is None
    assert _update(ctx, task["id"], status="done")["status"] == "done"  # now done is done
    again = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=2, repeat_unit="week")
    cancelled = _update(ctx, again["id"], status="cancelled")
    assert cancelled["status"] == "cancelled" and tasks.get(conn, again["id"]).reminder is None


@pytest.mark.parametrize(
    "fields",
    [
        {"repeat_every": 1, "repeat_unit": "week"},  # no first time
        {"remind_at": "2026-09-20T19:00", "repeat_unit": "week"},
        {"remind_at": "2026-09-20T19:00", "repeat_every": 0, "repeat_unit": "week"},
        {"remind_at": "2026-09-20T19:00", "repeat_every": 500, "repeat_unit": "day"},
    ],
)
def test_a_repeat_needs_a_first_time_and_a_sensible_interval(
    registry, settings, clock, conn, family, fields
) -> None:
    ctx = _ctx(settings, clock, conn, family)
    result = registry.dispatch("add_task", {"title": "Bins out", **fields}, ctx)
    assert result.is_error, fields
    assert tasks.list_all(conn) == []


def test_a_tap_on_done_says_when_it_comes_round_next(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-20T19:00", repeat_every=1, repeat_unit="week")
    clock.advance(timedelta(hours=5))
    run_reminders(app)
    tapped = buttons.tap(
        app,
        conn,
        channel="telegram",
        chat_id="42",
        channel_user_id="1001",
        tap_id="q1",
        data=f"done:{task['id']}",
    )
    assert tapped.note == "Ticked off ✓ (Sam). It comes round again at 19:00 on Sun 27 Sep."


# -- the tasks page --------------------------------------------------------------------------------


def test_the_page_sets_changes_and_stops_a_repeat(settings, clock, conn, family) -> None:
    import re

    from tests.test_web_edits import _client

    client = _client(settings, clock)
    tokens = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', client.get("/tasks").text))
    new = dict(tokens, title="Bins out", remind_at="2026-09-20T19:00", repeat="1:week")
    assert client.post("/tasks/new", data=new).status_code == 302
    task = tasks.list_all(conn)[0]
    assert (task.repeat_every, task.repeat_unit, task.repeat_from) == (1, "week", "schedule")
    page = client.get("/tasks").text
    assert "Every week" in page and 'name="repeat_was" value="1:week:schedule"' in page

    def edit(once, **changes):
        form = dict(
            tokens,
            once=once,
            revision=str(tasks.get(conn, task.id).revision),
            title="Bins out",
            status="open",
            repeat_was="1:week:schedule",
            repeat="1:week",
        )
        form.update(changes)
        return client.post(f"/task/{task.id}/edit", data=form)

    # Saved as it was drawn, the repeat is not sent again, so its first time stays put.
    edit("e1", notes="Green bin too")
    kept = tasks.get(conn, task.id)
    assert kept.notes == "Green bin too" and kept.repeat_anchor == task.repeat_anchor
    edit("e2", repeat="2:week", repeat_after_done="on")
    changed = tasks.get(conn, task.id)
    assert (changed.repeat_every, changed.repeat_from) == (2, "done")
    edit("e3", repeat_was="2:week:done", repeat="")
    assert tasks.get(conn, task.id).repeat_every is None  # doesn't repeat any more
    # A choice the page never offered is refused, and changes nothing.
    edit("e4", repeat_was="", repeat="7:fortnight")
    assert tasks.get(conn, task.id).repeat_every is None


# -- birthdays and the gifts saved for them --------------------------------------------------------


def _gift(conn, title, *, who="Grandma", kind="gift", status="idea"):
    from familydb.store import db, ideas

    with db.transaction(conn):
        return ideas.insert(
            conn,
            title=title,
            kind=kind,
            participants=[who],
            status=status,
            now="2026-09-01T00:00:00Z",
        )


def test_a_birthday_reminder_lists_the_gifts_saved_for_them(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    said = _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    apron = _gift(conn, "a gardening apron")
    pottery = _gift(conn, "a pottery class", who="for Grandma")
    _gift(conn, "a fishing rod", who="Grandpa")
    _gift(conn, "an old idea", status="dropped")
    _gift(conn, "Grandma's favourite cafe", kind="restaurant")  # somewhere to go, not a gift
    task = add_task(
        ctx,
        AddTaskInput(
            title="Grandma's birthday, 12 Oct",
            remind_at="2026-09-20T15:00",
            repeat_every=1,
            repeat_unit="year",
            gift_for="Grandma",
        ),
    )["task"]
    assert task["gift_for"] == "Grandma"
    clock.advance(timedelta(hours=1))
    assert run_reminders(app) == 1
    assert said[-1].endswith(
        f"Gift ideas you've saved for Grandma: #{pottery.id} a pottery class, "
        f"#{apron.id} a gardening apron."
    )
    assert _local(tasks.get(conn, task["id"]).reminder.remind_at) == "Mon 2027-09-20 15:00"


def test_with_no_gifts_saved_it_asks_for_some(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    said = _sent(app)
    ctx = _ctx(settings, clock, conn, family)
    _add(ctx, remind_at="2026-09-20T15:00", gift_for="Sam")
    _gift(conn, "a kite", who="Samantha")  # a whole name, not part of one
    clock.advance(timedelta(hours=1))
    run_reminders(app)
    assert said[-1].endswith(
        "Nothing saved yet as a gift for Sam; tell me any ideas and I'll keep them."
    )


def test_a_gift_is_never_offered_as_something_to_do(settings, clock, conn, family) -> None:
    from familydb.suggest.engine import run
    from familydb.suggest.types import SuggestInput

    gift = _gift(conn, "a gardening apron")
    ctx = _ctx(settings, clock, conn, family)
    result = run(ctx, SuggestInput(window="this_weekend", question="?", discover=False))
    assert gift.id not in {c.idea_id for c in result.candidates}


def test_whose_occasion_it_is_can_be_set_and_cleared(settings, clock, conn, family) -> None:
    ctx = _ctx(settings, clock, conn, family)
    task = _add(ctx, remind_at="2026-09-28T09:00", repeat_every=1, repeat_unit="year")
    assert _update(ctx, task["id"], gift_for="Alex")["gift_for"] == "Alex"
    assert list_tasks(ctx, ListTasksInput())["tasks"][0]["gift_for"] == "Alex"
    assert _update(ctx, task["id"], gift_for="")["gift_for"] is None
