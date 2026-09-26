"""Bring up a task kept for some Saturday morning when one comes round free. No model call.

A task with a preferred window and nothing else to bring it back ("one of these Saturday mornings
I need to get my knives sharpened") would wait until somebody asked about it. When its window
can be read (windows.py), this job brings it up in the chat it was asked in, in her words and
with a reminder's buttons: from an hour into that part of the day, while the calendar is free for
the hour ahead. A task is brought up at most once a week, and a chat hears at most one a day, the
task nudged longest ago first; a task said in the last twelve hours waits, since it was only just
said. With nothing to bring up it reads the database and returns: the calendar is asked only
when a nudge could go this minute.
"""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime, time, timedelta
from typing import Any

from familydb import buttons, voice
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.store.tasks import Task
from familydb.tools.gcal import events_by_day, free_spans
from familydb.windows import read

log = logging.getLogger(__name__)

# At most once a week for each task: six days, so the same morning next week still qualifies.
GAP = timedelta(days=6)
# A task said this recently is not brought up; they have only just said it.
SETTLE = timedelta(hours=12)
# How long the calendar must be free from now for a nudge to go.
FREE_MINUTES = 60


def nudge_text(task: Task, settings: Any, *, when: str, today: str) -> str:
    """The nudge as sent, in the assistant's voice: `when` is "Saturday morning"."""
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


def free_minutes(app: App, moment: datetime) -> int | None:
    """How long the family calendar is free from this minute, within the day; None when there
    is no calendar to ask, or it could not be asked (the nudge then goes without it)."""
    calendar = app.calendar
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
    """Bring up each chat's task whose window is here, when it is free. Returns how many."""
    app.refresh()
    if not app.settings.task_nudges:
        return 0
    moment = app.clock.now()
    now = utc_iso(moment)
    midnight = datetime.combine(moment.date(), time.min, tzinfo=app.clock.tz)
    with closing(app.connect()) as conn:
        chosen: dict[tuple[str, str], tuple[Task, str]] = {}
        for task in tasks.nudge_candidates(
            conn,
            said_before=utc_iso(moment - SETTLE),
            nudged_before=utc_iso(moment - GAP),
            chats_quiet_since=utc_iso(midnight),
        ):
            window = read(task.preferred_window)
            part = window.open_at(moment) if window else None
            # A nudge that arrived late would be no nudge: a chat nothing here can send to waits.
            if window and part and app.senders.get(task.channel) is not None:
                when = window.now_words(moment, part)
                chosen.setdefault((task.channel, task.chat_id), (task, when))
        if not chosen:
            return 0
        free = free_minutes(app, moment)
        if free is not None and free < FREE_MINUTES:
            return 0
        nudged = 0
        for (channel, chat_id), (task, when) in chosen.items():
            with transaction(conn):
                # Asked again under the write lock: a run by hand can race the scheduler, and a
                # tap or a reply can finish the task in between.
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
                    buttons=buttons.for_reminder(task.id),
                )
                tasks.mark_nudged(conn, task.id, now)
            # Stored first, sent second: one that cannot go now is the retry job's.
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
