"""A task kept for some Saturday morning comes up when one comes round free (jobs/nudges.py)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta

import pytest

from familydb import buttons, task_service, windows
from familydb.app import App
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.jobs.nudges import run_nudges
from familydb.store import db, messages, tasks
from familydb.tools.registry import ToolContext
from familydb.tools.tasks import (
    AddTaskInput,
    ListTasksInput,
    UpdateTaskInput,
    add_task,
    list_tasks,
    update_task,
)
from tests import fakes
from tests.conftest import TZ

FRIDAY = datetime(2026, 9, 25, 8, 0, tzinfo=TZ)
SATURDAY = datetime(2026, 9, 26, 9, 0, tzinfo=TZ)


class CountingCalendar(fakes.FakeCalendar):
    def __init__(self) -> None:
        super().__init__(TZ)
        self.asked = 0

    def list_events(self, start, end):
        self.asked += 1
        return super().list_events(start, end)


def _app(settings, at: datetime, *, calendar=None, **changes):
    app = App(settings.model_copy(update=changes), FixedClock(at, TZ), calendar=calendar)
    said: list[str] = []
    app.senders["web"] = lambda chat, text: said.append(text)
    return app, said


def _at(app, moment: datetime) -> None:
    app.clock._at = moment


def _task(conn, title="Get the knives sharpened", window="one of these Saturday mornings", **kw):
    """Said on Friday morning, in the page's chat unless another is named."""
    values = {"title": title, "preferred_window": window, "owner_id": kw.pop("owner_id", None)}
    values["window_until"] = kw.pop("window_until", None)
    return task_service.create(
        conn,
        values,
        reminder=kw.pop("reminder", None),
        operation_key=f"{title}:{window}:{kw}",
        channel=kw.pop("channel", "web"),
        chat_id=kw.pop("chat_id", "web"),
        now=utc_iso(kw.pop("said", FRIDAY)),
        repeat=kw.pop("repeat", None),
    )


# -- reading the window


@pytest.mark.parametrize(
    ("said", "days", "parts", "words"),
    [
        ("one of these Saturday mornings", {5}, ("morning",), "a Saturday morning"),
        ("a free weekend", {5, 6}, ("day",), "a weekend day"),
        ("weeknights", set(range(5)), ("evening",), "a weekday evening"),
        ("some evening", set(range(7)), ("evening",), "an evening"),
        ("Monday or Wednesday night", {0, 2}, ("evening",), "a Monday or Wednesday evening"),
        # Free time, said whole: any day the calendar has two hours free.
        ("Next time I have some free time", set(range(7)), ("day",), "a day with two hours free"),
        ("whenever we get a chance", set(range(7)), ("day",), "a day with two hours free"),
        ("in my spare time", set(range(7)), ("day",), "a day with two hours free"),
    ],
)
def test_a_window_is_read_as_days_and_parts_of_the_day(said, days, parts, words) -> None:
    window = windows.read(said)
    assert window is not None
    assert (set(window.days), window.parts, window.words()) == (days, parts, words)


@pytest.mark.parametrize(
    "said",
    [
        "",
        "before Christmas",
        "any day but Sunday",
        "next Saturday morning",
        "tonight",
        "Saturday at 3",
        "Sat morning",
        "sometime",
        "next time I have some free time and the car is fixed",
        "this weekend",  # with no day it was said on to count from
    ],
)
def test_a_window_with_any_word_it_does_not_know_is_not_read(said) -> None:
    assert windows.read(said) is None


def test_this_weekend_ends_on_the_sunday_after_it_was_said() -> None:
    """Read as every weekend it would nag for good; read as nothing it never came up at all."""
    thursday = FRIDAY.date() - timedelta(days=1)
    until = windows.until("sometime this weekend", thursday)
    assert until == SATURDAY.date() + timedelta(days=1)
    assert windows.until("this week, in the evening", until) == until  # said on the Sunday
    assert windows.until("one of these Saturday mornings", thursday) is None
    window = windows.read("this weekend", until=until, today=thursday)
    assert window is not None and set(window.days) == {5, 6}
    assert window.words("free") == "a free weekend day by Sun 27 Sep"
    assert window.open_at(SATURDAY) == "day"
    assert window.open_at(SATURDAY + timedelta(days=7)) is None  # the weekend after
    assert windows.read("this weekend", until=until, today=until + timedelta(days=1)) is None
    morning = windows.read("this weekend morning", until=until, today=thursday)
    assert morning is not None and morning.parts == ("morning",)


def test_a_nudge_goes_from_an_hour_into_the_part_until_an_hour_before_its_end() -> None:
    window = windows.read("some Saturday morning")
    assert window is not None
    opens = [
        window.open_at(SATURDAY.replace(hour=h, minute=m))
        for h, m in [(8, 59), (9, 0), (11, 0), (11, 1)]
    ]
    assert opens == [None, "morning", "morning", None]
    assert window.open_at(SATURDAY + timedelta(days=1)) is None  # a Sunday


# -- the job


def test_it_comes_up_on_a_free_saturday_morning_and_again_a_week_on(settings, conn, family) -> None:
    task = _task(conn, owner_id=family["sam"].id)
    app, said = _app(settings, SATURDAY - timedelta(minutes=15))
    assert run_nudges(app) == 0  # not before nine
    _at(app, SATURDAY)
    assert run_nudges(app) == 1
    assert said == [
        f"It's Saturday morning, a good moment for this one: Get the knives sharpened (Sam). "
        f"Task #{task.id}; tell me when it's done, or I can remind you later."
    ]
    sent = messages.get(conn, conn.execute("SELECT max(id) FROM messages").fetchone()[0])
    assert sent.buttons == buttons.for_reminder(task.id)  # Done, In an hour, Tomorrow
    assert tasks.get(conn, task.id).revision == task.revision  # a nudge is not an edit
    _at(app, SATURDAY + timedelta(minutes=15))
    assert run_nudges(app) == 0  # once
    _at(app, SATURDAY + timedelta(days=1))
    assert run_nudges(app) == 0  # a Sunday
    _at(app, SATURDAY + timedelta(days=7))
    assert run_nudges(app) == 1  # the next Saturday


def test_a_busy_calendar_holds_it_until_an_hour_is_free(settings, conn, family) -> None:
    calendar = CountingCalendar()
    calendar.seed("Swimming", SATURDAY, SATURDAY + timedelta(minutes=30))
    calendar.seed("Haircut", SATURDAY.replace(hour=10, minute=15), SATURDAY.replace(hour=11))
    _task(conn)
    app, said = _app(settings, FRIDAY + timedelta(hours=2), calendar=calendar)
    assert run_nudges(app) == 0
    assert calendar.asked == 0  # nothing could go on a Friday, so Google was not asked
    _at(app, SATURDAY)
    assert run_nudges(app) == 0  # at the pool
    _at(app, SATURDAY.replace(minute=30))
    assert run_nudges(app) == 0  # free, but only for 45 minutes
    _at(app, SATURDAY.replace(hour=11))
    assert run_nudges(app) == 1
    assert said[-1].startswith("It's Saturday morning")


def test_free_time_comes_up_when_the_calendar_has_two_hours_free(settings, conn, family) -> None:
    calendar = CountingCalendar()
    tuesday = SATURDAY + timedelta(days=3)  # 09:00
    calendar.seed("Dentist", tuesday.replace(hour=10), tuesday.replace(hour=11))
    _task(conn, "Schedule my colonoscopy", window="next time I have some free time")
    app, said = _app(settings, tuesday, calendar=calendar)
    assert run_nudges(app) == 0  # an hour free, not two
    _at(app, tuesday.replace(hour=11))
    assert run_nudges(app) == 1
    assert said[-1].startswith(
        "It's Tuesday morning, with two hours free, a good moment for this one: "
        "Schedule my colonoscopy."
    )


def test_this_weekend_comes_up_that_weekend_only(settings, conn, family) -> None:
    sunday = (SATURDAY + timedelta(days=1)).date().isoformat()
    _task(conn, "Clean the garage", window="this weekend", window_until=sunday)
    app, said = _app(settings, SATURDAY + timedelta(days=7))
    assert run_nudges(app) == 0  # the weekend after: over
    _at(app, SATURDAY)
    assert run_nudges(app) == 1 and said[-1].startswith("It's Saturday, a good moment")


def test_a_busy_day_on_the_calendar_brings_nothing_up(settings, conn, family) -> None:
    calendar = CountingCalendar()
    day = SATURDAY.date()
    calendar.seed("Away at the coast", day, day + timedelta(days=1), all_day=True)
    _task(conn)
    app, _ = _app(settings, SATURDAY, calendar=calendar)
    assert run_nudges(app) == 0


def test_a_chat_hears_one_a_day_the_longest_waiting_first(settings, conn, family) -> None:
    first = _task(conn)
    second = _task(conn, "Return the library books")
    elsewhere = _task(conn, "Fix the bike", channel="telegram", chat_id="42")
    app, said = _app(settings, SATURDAY)
    app.senders["telegram"] = lambda chat, text: said.append(f"{chat}: {text}")
    assert run_nudges(app) == 2  # one in each chat
    assert [text.split("this one: ")[1].split(".")[0] for text in said] == [
        "Get the knives sharpened",
        "Fix the bike",
    ]
    _at(app, SATURDAY + timedelta(hours=1))
    assert run_nudges(app) == 0  # the page's chat has had one today
    _at(app, SATURDAY + timedelta(days=7))
    assert run_nudges(app) == 2
    assert f"Task #{second.id}" in said[-2]  # never brought up, so before the knives again
    assert tasks.get(conn, first.id).nudged_at == utc_iso(SATURDAY)
    assert tasks.get(conn, elsewhere.id).nudged_at == utc_iso(SATURDAY + timedelta(days=7))


def test_what_is_never_brought_up(settings, conn, family) -> None:
    done = _task(conn, "Done already")
    cancelled = _task(conn, "Cancelled")
    for task, status in ((done, "done"), (cancelled, "cancelled")):
        task_service.update(conn, task.id, {"status": status}, now=utc_iso(FRIDAY))
    _task(conn, "Has a reminder", reminder=utc_iso(SATURDAY + timedelta(days=3)))
    rule = {"repeat_every": 1, "repeat_unit": "week", "repeat_from": "schedule"}
    _task(conn, "Comes round", reminder=utc_iso(SATURDAY + timedelta(days=3)), repeat=rule)
    _task(conn, "Some time before Christmas", window="before Christmas")
    _task(conn, "Only just said", said=SATURDAY - timedelta(hours=1))
    _task(conn, "Nobody here can send there", channel="telegram", chat_id="42")
    app, said = _app(settings, SATURDAY)
    assert run_nudges(app) == 0
    assert said == []


def test_switched_off_nothing_comes_up(settings, conn, family) -> None:
    _task(conn)
    app, said = _app(settings, SATURDAY, task_nudges=False)
    assert run_nudges(app) == 0
    assert said == []


def test_a_tap_on_in_an_hour_turns_it_into_a_reminder(settings, conn, family) -> None:
    task = _task(conn, channel="telegram", chat_id="42")
    app, _ = _app(settings, SATURDAY)
    app.senders["telegram"] = lambda chat, text: None
    assert run_nudges(app) == 1
    tapped = buttons.tap(
        app,
        conn,
        channel="telegram",
        chat_id="42",
        channel_user_id="1001",
        tap_id="t1",
        data=f"hour:{task.id}",
    )
    assert "10\u00a0am today" in f"{tapped.toast} {tapped.note}"
    assert tasks.get(conn, task.id).reminder is not None


# -- what the model and the page are told


def _ctx(settings, conn, family, **changes) -> ToolContext:
    return ToolContext(
        conn=conn,
        settings=settings.model_copy(update=changes),
        clock=FixedClock(FRIDAY, TZ),
        member=family["sam"],
    )


def test_the_model_is_told_when_a_task_will_come_up(settings, conn, family) -> None:
    ctx = _ctx(settings, conn, family)
    kept = add_task(ctx, AddTaskInput(title="Knives", preferred_window="some Saturday morning"))
    assert kept["nudges"] == "on a free Saturday morning"
    vague = add_task(ctx, AddTaskInput(title="Gutters", preferred_window="before Christmas"))
    assert "nudges" not in vague
    # Only the weekly list of what has waited will bring it up: the model is told, so it offers
    # a reminder for sooner; with that list off, nothing will.
    assert vague["comes_up"] == (
        "in Sunday morning's list once a week old; offer a reminder for sooner"
    )
    assert "comes_up" not in kept
    quiet = _ctx(settings, conn, family, forgotten_roundup=False)
    alone = add_task(quiet, AddTaskInput(title="Shed", preferred_window="before Christmas"))
    assert alone["comes_up"] == "not by itself; offer a reminder"
    due = add_task(ctx, AddTaskInput(title="Water bill", due_at="2026-10-02T17:00"))
    assert due["comes_up"] == "the morning before it is due"
    reminded = add_task(ctx, AddTaskInput(title="Bins", remind_at="2026-09-30T19:00"))
    assert "comes_up" not in reminded
    weekend = add_task(ctx, AddTaskInput(title="Garage", preferred_window="this weekend"))
    assert weekend["nudges"] == "on a free weekend day by Sun 27 Sep"
    assert tasks.get(conn, weekend["task"]["id"]).window_until == "2026-09-27"
    listed = {task["id"]: task for task in list_tasks(ctx, ListTasksInput())["tasks"]}
    assert listed[kept["task"]["id"]]["nudges"] == "on a free Saturday morning"
    assert "nudges" not in listed[vague["task"]["id"]]
    moved = update_task(
        ctx, UpdateTaskInput(task_id=vague["task"]["id"], preferred_window="weekday evenings")
    )
    assert moved["nudges"] == "on a free weekday evening"
    off = _ctx(settings, conn, family, task_nudges=False)
    assert "nudges" not in add_task(off, AddTaskInput(title="Bike", preferred_window="a weekend"))


def test_in_a_group_a_plain_save_is_not_followed_by_an_offer(settings, conn, family) -> None:
    """In the family group a plain save is only ✓ (the family's decision): what will bring it up
    is still said, but not that a reminder should be offered, which everyone would read."""
    with db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="g9",
            chat_id="-100",
            member_id=family["sam"].id,
            text="Don't let me forget to make a dentist appointment.",
            now="2026-09-25T17:00:00Z",
        )
    ctx = _ctx(settings, conn, family)
    in_group = dataclasses.replace(ctx, message_id=asked.id)
    saved = add_task(in_group, AddTaskInput(title="Dentist appointment"))
    assert saved["comes_up"] == "in Sunday morning's list once a week old"
    alone = add_task(ctx, AddTaskInput(title="Dentist appointment, mine"))
    assert alone["comes_up"].endswith("; offer a reminder for sooner")


def test_the_tasks_page_says_when_one_comes_up(settings, conn, family) -> None:
    from tests.test_web_edits import _client

    read = _task(conn)
    _task(conn, "Clear the gutters", window="some time before Christmas")
    _task(conn, "Clean the garage", window="this weekend", window_until="2026-09-20")  # over
    with db.transaction(conn):
        tasks.mark_nudged(conn, read.id, utc_iso(SATURDAY))
    page = _client(settings, FixedClock(SATURDAY, TZ)).get("/tasks").text
    assert "Vera brings it up on a free Saturday morning, last on Sat 26 Sep" in page
    unread = "not a day or part of the day Vera can read, so it comes up only when asked"
    assert page.count(unread) == 2
    quiet = _client(settings.model_copy(update={"task_nudges": False}), FixedClock(SATURDAY, TZ))
    assert "brings it up" not in quiet.get("/tasks").text
