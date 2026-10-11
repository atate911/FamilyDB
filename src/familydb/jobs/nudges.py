"""Bring up a task kept for a preferred window ("one of these Saturday mornings") when it comes
round and the calendar is free. No model call. A readable window (windows.py) is nudged in its
chat from an hour into that part of the day, with a reminder's buttons: a task once a week, a
chat once a day (longest-ago first), none said in the last twelve hours. With nothing to bring up
it reads the database and returns; the calendar is asked only when a nudge could go."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, time, timedelta
from typing import Any

from familydb import buttons, routing, voice
from familydb.app import App
from familydb.availability import calendar_available
from familydb.base.dates import utc_iso
from familydb.free_time import events_by_day, free_spans
from familydb.saved_plans import SavedPlans
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.store.tasks import Task
from familydb.windows import Window, read

log = logging.getLogger(__name__)

# Six days, so the same morning next week still qualifies.
GAP = timedelta(days=6)
SETTLE = timedelta(hours=12)


def nudge_text(task: Task, settings: Any, *, when: str, today: str) -> str:
    """The nudge as sent; `when` is "Saturday morning"."""
    who = f" ({task.owner})" if task.owner else ""
    return voice.say(
        settings,
        "nudge",
        seed=f"{task.id}:{today}",
        when=when,
        title=task.title,
        who=who,
        task=task.id,
    )


def free_minutes(app: App, moment: datetime, conn: sqlite3.Connection | None = None) -> int | None:
    """Minutes the calendar is free from now, within the day; None when it cannot be asked (the
    nudge then goes without it). With no Google calendar the plans kept here are the calendar."""
    calendar = app.calendar
    if calendar is None and conn is not None and not calendar_available(app.settings):
        calendar = SavedPlans(conn, app.clock.tz)
    if calendar is None:
        return None
    day = moment.date()
    minute = moment.hour * 60 + moment.minute
    try:
        [(_, events)] = events_by_day(calendar, day, day, app.clock.tz)
    except Exception:
        log.exception("nudges go without the calendar: it could not be checked")
        return None
    spans = free_spans(events, day, app.clock.tz, minute, 24 * 60)
    return spans[0][1] - minute if spans and spans[0][0] == minute else 0


def run_nudges(app: App) -> int:
    """Bring up each chat's task whose window is here, when free; returns how many."""
    app.refresh()
    if not app.settings.task_nudges:
        return 0
    moment = app.clock.now()
    now = utc_iso(moment)
    midnight = datetime.combine(moment.date(), time.min, tzinfo=app.clock.tz)
    with closing(app.connect()) as conn:
        due: list[tuple[Task, Window, str]] = []
        for task in tasks.nudge_candidates(
            conn,
            said_before=utc_iso(moment - SETTLE),
            nudged_before=utc_iso(moment - GAP),
            chats_quiet_since=utc_iso(midnight),
        ):
            window = read(task.preferred_window, until=task.until, today=moment.date())
            part = window.open_at(moment) if window else None
            # A chat nothing can send to waits.
            if window and part and app.senders.get(task.channel) is not None:
                due.append((task, window, part))
        if not due:
            return 0
        # How long the calendar is free from now: each window says how long it needs (an hour,
        # or two for "some free time").
        free = free_minutes(app, moment, conn)
        chosen: dict[tuple[str, str], tuple[Task, str]] = {}
        for task, window, part in due:
            if free is None or free >= window.min_free:
                chosen.setdefault(
                    (task.channel, task.chat_id), (task, window.now_words(moment, part))
                )
        nudged = 0
        for task, when in chosen.values():
            # The owner's task goes to them; everyone's to the family (routing.py).
            channel, chat_id = routing.for_task(conn, app.settings, task)
            with transaction(conn):
                # Re-read under the write lock: a manual run can race the scheduler, and a tap
                # or reply can finish the task meanwhile.
                current = tasks.get(conn, task.id)
                if current is None or current.status != "open":
                    continue
                if current.nudged_at != task.nudged_at:
                    continue
                out = messages.insert_out(
                    conn,
                    channel=channel,
                    chat_id=chat_id,
                    text=nudge_text(task, app.settings, when=when, today=moment.date().isoformat()),
                    now=now,
                    buttons=buttons.for_reminder(task.id, everyone=task.owner_id is None),
                )
                tasks.mark_nudged(conn, task.id, now)
            voice.hand_over(
                app,
                conn,
                out.id,
                event="nudge",
                channel=channel,
                chat_id=chat_id,
                mention=task.title,
            )
            nudged += 1
    return nudged
