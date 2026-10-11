"""The morning message (jobs/morning.py): one a day in each chat that has something for it, none on
an empty day, no model call."""

from __future__ import annotations

from datetime import datetime, timedelta

from familydb import buttons, task_service
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.base.dates import utc_iso
from familydb.jobs.morning import run_morning
from familydb.store import db, ideas, messages, mornings, plans, tasks
from tests.conftest import TZ

TUESDAY = datetime(2026, 10, 6, 7, 0, tzinfo=TZ)
SUNDAY = datetime(2026, 10, 11, 7, 0, tzinfo=TZ)


def _app(settings, at=TUESDAY, **changes):
    app = App(settings.model_copy(update=changes), FixedClock(at, TZ))
    said: list[str] = []
    app.senders["web"] = lambda chat, text: said.append(text)
    return app, said


def _task(conn, title, *, said=TUESDAY - timedelta(days=1), owner=None, chat="web", **values):
    return task_service.create(
        conn,
        {"title": title, "owner_id": owner, **values},
        reminder=values.pop("reminder", None),
        operation_key=title,
        channel="web",
        chat_id=chat,
        now=utc_iso(said),
    )


def _plan(conn, title, start):
    with db.transaction(conn):
        return plans.insert(conn, title=title, start=start, end=None, all_day=False)


def test_an_empty_day_says_nothing(settings, conn, family) -> None:
    app, said = _app(settings)
    assert run_morning(app) == 0 and said == []
    assert conn.execute("SELECT count(*) FROM mornings").fetchone()[0] == 0


def test_the_day_ahead_once_in_the_chat_it_is_for(settings, conn, family) -> None:
    sam = family["sam"].id
    _plan(conn, "Zoo", "2026-10-06T10:00:00-07:00")
    _task(conn, "Bins out", owner=sam, reminder=utc_iso(TUESDAY.replace(hour=18)))
    _task(conn, "Pay the bill", owner=sam, due_at=utc_iso(TUESDAY.replace(hour=17)))
    _task(conn, "Library books", owner=sam, due_at=utc_iso(TUESDAY + timedelta(days=1, hours=9)))
    app, said = _app(settings)
    assert run_morning(app) == 1
    assert said == [
        "Good morning. Here's Tue 6 Oct:\n"
        "10\u00a0am Zoo\n"
        "due 5\u00a0pm: #2 Pay the bill (Sam)\n"
        "6\u00a0pm reminder: #1 Bins out (Sam)\n"
        "\n"
        "Due tomorrow:\n"
        "#3 Library books (Sam), by 4\u00a0pm"
    ]
    assert run_morning(app) == 0  # once a day
    sent = messages.get(conn, conn.execute("SELECT max(id) FROM messages").fetchone()[0])
    assert sent.sent_as == "morning"
    counts = mornings.part_counts(conn, since="2000-01-01")
    assert set(counts) == {"morning:agenda", "morning:deadlines"}


def test_a_reminder_nobody_acted_on_is_chased_once_with_a_button(settings, conn, family) -> None:
    task = _task(conn, "Call the plumber", owner=family["sam"].id, reminder=utc_iso(TUESDAY))
    with db.transaction(conn):
        out = messages.insert_out(
            conn, channel="web", chat_id="web", text="Reminder", now=utc_iso(TUESDAY)
        )
        tasks.attach_message(conn, task.reminder.id, out.id)
        messages.mark_delivered(conn, [out.id], now=utc_iso(TUESDAY - timedelta(hours=14)))
    app, said = _app(settings)
    assert run_morning(app) == 1
    assert said[-1].endswith("Still open from yesterday:\n#1 Call the plumber (Sam)")
    morning = messages.get(conn, conn.execute("SELECT max(id) FROM messages").fetchone()[0])
    assert morning.buttons == buttons.in_row(
        [
            {"label": "✓ Call the plumber", "data": f"done:{task.id}"},
            {"label": "Tomorrow", "data": f"tomorrow:{task.id}"},
        ],
        str(task.id),
    )
    app.clock._at = TUESDAY + timedelta(days=1)
    assert run_morning(app) == 0  # chased once


def test_sundays_list_what_has_waited_with_nothing_to_bring_it_up(settings, conn, family) -> None:
    week_ago = SUNDAY - timedelta(days=8)
    for number in range(7):
        _task(conn, f"Chore {number}", said=week_ago)
    _task(conn, "Knives", said=week_ago, preferred_window="some Saturday morning")
    _task(conn, "Fresh", said=SUNDAY - timedelta(days=2))
    app, said = _app(settings, at=SUNDAY)
    assert run_morning(app) == 1
    listed = said[-1].split("(tell me if any can go):\n")[1].splitlines()
    assert listed == [f"#{n + 1} Chore {n}" for n in range(5)]
    app, said = _app(settings, at=SUNDAY - timedelta(days=1))
    assert run_morning(app) == 0  # not the day for it


def test_an_idea_ending_this_week_with_a_free_day_is_said_once(settings, conn, family) -> None:
    with db.transaction(conn):
        festival = ideas.insert(
            conn,
            title="Lantern festival",
            kind="event",
            setting="indoor",
            happens_from="2026-10-09",
            happens_until="2026-10-11",
            now=utc_iso(TUESDAY),
        )
    app, said = _app(settings)
    assert run_morning(app) == 1
    assert said[-1] == (
        "Good morning. Here's Tue 6 Oct:\n"
        f"#{festival.id} Lantern festival ends Sunday; Friday looks free for it."
    )
    app.clock._at = TUESDAY + timedelta(days=1)
    assert run_morning(app) == 0


def test_where_a_kid_reads_it_is_plain_and_keeps_birthdays_out(settings, conn, family) -> None:
    girls = family["girls"]
    mine = f"member:{girls.id}"
    _task(conn, "Tidy up", owner=girls.id, chat=mine, due_at=utc_iso(TUESDAY.replace(hour=17)))
    _task(
        conn,
        "Mum's birthday",
        owner=girls.id,
        chat=mine,
        gift_for="Alex",
        due_at=utc_iso(TUESDAY.replace(hour=18)),
    )
    app, said = _app(settings)
    assert run_morning(app) == 1
    assert said == ["Good morning. Here's Tue 6 Oct:\ndue 5\u00a0pm: Tidy up (the girls)"]


def test_with_every_part_off_it_reads_nothing(settings, conn, family) -> None:
    _task(conn, "Pay the bill", due_at=utc_iso(TUESDAY.replace(hour=17)))
    app, said = _app(
        settings,
        morning_agenda=False,
        chase_missed=False,
        deadline_heads_up=False,
        forgotten_roundup=False,
    )
    assert run_morning(app) == 0 and said == []
