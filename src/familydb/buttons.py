"""Buttons under what the bot says unasked, and what a tap on one does.

A reminder comes with Done, In an hour and Tomorrow; "how was it?" with Yes, again, Not again
and Didn't go. A tap does what saying so in the chat would, without asking a model: code calls
the tool the model would have called, as the member who tapped, and says what it did in her
words (`voice.say`). So it costs nothing, answers at once, and works when the model is down or
the day's limit is spent.

What a button sends back is untrusted, like anything a client sends: an action from a closed list
and the number of what it is about, both checked, and whoever tapped checked against the family
list, before anything is done. Nothing a tap does is new; each can be said in the chat instead. A
tap is kept as a message from whoever tapped, so its tool call has a message to belong to in the
audit and the conversation shows it. The same tap delivered twice is done once, and a tap on
something already dealt with does nothing and says so.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from familydb import voice
from familydb.dates import utc_iso
from familydb.store import calls, ideas, members, messages, outcomes, plans, tasks
from familydb.store.db import transaction
from familydb.tools.registry import ToolContext

log = logging.getLogger(__name__)

# (action, label): what each kind of message is sent with. The label is what the button says;
# what it does is the action's, in `_task_job` and `_plan_job`.
REMINDER = (("done", "✓ Done"), ("hour", "In an hour"), ("tomorrow", "Tomorrow"))
FOLLOW_UP = (("again", "Yes, again"), ("not_again", "Not again"), ("missed", "Didn't go"))
LABELS = dict(REMINDER + FOLLOW_UP)
SNOOZES = {"hour": timedelta(hours=1), "tomorrow": timedelta(days=1)}
# Telegram hands back at most 64 bytes of a button; the longest here is well inside that.
MAX_NUMBER_DIGITS = 18

Button = dict[str, str]


def for_reminder(task_id: int) -> list[Button]:
    return _row(REMINDER, task_id)


def for_follow_up(plan_id: int) -> list[Button]:
    return _row(FOLLOW_UP, plan_id)


def _row(choices: tuple[tuple[str, str], ...], number: int) -> list[Button]:
    return [{"label": label, "data": f"{action}:{number}"} for action, label in choices]


@dataclass(frozen=True)
class Tapped:
    """What a tap did, for the channel to show.

    `toast` goes to whoever tapped. `note`, when there is one, is added under the message for
    everyone in the chat, saying who did what. `finished` takes the buttons off: they have done
    their job, or there is nothing left for them to do.
    """

    toast: str
    note: str | None = None
    finished: bool = False


@dataclass(frozen=True)
class _Job:
    tool: str
    values: dict[str, Any]
    about: str  # what was tapped on, in words, for the message kept of the tap
    event: str  # her line for having done it
    facts: dict[str, Any] = field(default_factory=dict)


def tap(
    app: Any,
    conn: sqlite3.Connection,
    *,
    channel: str,
    chat_id: str,
    channel_user_id: str,
    tap_id: str,
    data: str,
) -> Tapped | None:
    """Do what a tapped button says, as whoever tapped it. None for a tap already handled.

    `tap_id` is the channel's own id for this tap, so the same one delivered again is seen as
    such; `data` is what the button sends back, as `for_reminder` and `for_follow_up` made it.
    """
    settings = app.settings
    member = members.resolve(conn, channel, channel_user_id)
    if member is None:
        return Tapped(voice.say(settings, "tap_stranger", seed=tap_id))
    action, _, number = data.partition(":")
    digits = number.isascii() and number.isdigit()
    if action not in LABELS or not digits or len(number) > MAX_NUMBER_DIGITS:
        return Tapped(voice.say(settings, "tap_stale", seed=tap_id), finished=True)
    update_id = f"tap:{tap_id}"
    if messages.exists_update(conn, channel, update_id):
        return None
    planned = _task_job if action in SNOOZES or action == "done" else _plan_job
    job = planned(app, conn, action, int(number))
    if isinstance(job, str):
        return Tapped(voice.say(settings, job, seed=tap_id), finished=True)
    now = utc_iso(app.clock.now())
    try:
        with transaction(conn):
            kept = messages.insert_in(
                conn,
                channel=channel,
                channel_update_id=update_id,
                chat_id=chat_id,
                member_id=member.id,
                text=f"{messages.TAP_PREFIX}{LABELS[action]}: {job.about}",
                now=now,
            )
            # Done by code, never a turn: nothing for the retry job to pick up.
            messages.mark_processed(conn, kept.id, [], now=now)
    except sqlite3.IntegrityError:
        log.info("tap %s arrived twice at once", tap_id)
        return None
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=app.clock,
        member=member,
        message_id=kept.id,
        calendar=app.calendar,
        weather=app.weather,
        geocoder=app.geocoder,
    )
    started = time.monotonic()
    result = app.registry.dispatch(job.tool, job.values, ctx)
    with transaction(conn):
        calls.log_tool_call(
            conn,
            message_id=kept.id,
            iteration=0,
            tool_use_id=update_id,
            tool_name=job.tool,
            input=job.values,
            output=result.content,
            is_error=result.is_error,
            duration_ms=int((time.monotonic() - started) * 1000),
            now=now,
        )
        messages.mark_processed(conn, kept.id, [] if result.is_error else [result.summary], now=now)
    if result.is_error:
        log.warning("tap %s on #%s did not go through: %s", action, number, result.content)
        return Tapped(voice.say(settings, "tap_failed", seed=kept.id))
    line = voice.say(settings, job.event, seed=kept.id, who=member.display_name, **job.facts)
    return Tapped(line, line, finished=True)


def _task_job(app: Any, conn: sqlite3.Connection, action: str, task_id: int) -> _Job | str:
    """What a reminder's button does to its task, or the line for why it does nothing."""
    task = tasks.get(conn, task_id)
    if task is None:
        return "tap_stale"
    if task.status != "open":
        return "tap_already"
    about = f"task #{task.id} {task.title}"
    if action == "done":
        return _Job("update_task", {"task_id": task.id, "status": "done"}, about, "tap_done")
    now = app.clock.now()
    moment = now + SNOOZES[action]
    return _Job(
        "update_task",
        # With its offset, so a clock change in between cannot make the time ambiguous.
        {"task_id": task.id, "remind_at": moment.isoformat(timespec="minutes")},
        about,
        "tap_snoozed",
        {"when": when_text(moment, now.date())},
    )


def _plan_job(app: Any, conn: sqlite3.Connection, action: str, plan_id: int) -> _Job | str:
    """What a follow-up's button records about its plan, or the line for why it does nothing."""
    plan = plans.get(conn, plan_id)
    idea = ideas.get(conn, plan.idea_id) if plan is not None and plan.idea_id else None
    if plan is None or idea is None:
        return "tap_stale"
    day = plan.start[:10]
    if outcomes.exists_since(conn, idea_id=idea.id, plan_id=plan.id, since=day):
        return "tap_already"
    about = f"#{idea.id} {plan.title} on {date.fromisoformat(day):%A}"
    if action == "missed":
        # Back on the list, so it can come up again; not an outcome. A dropped idea stays so.
        if idea.status == "dropped":
            return "tap_already"
        return _Job("update_idea", {"id": idea.id, "status": "idea"}, about, "tap_missed")
    return _Job(
        "record_outcome",
        {"plan_id": plan.id, "happened_on": day, "would_repeat": action == "again"},
        about,
        "tap_again" if action == "again" else "tap_not_again",
    )


def when_text(moment: datetime, today: date) -> str:
    """When a snoozed reminder comes back, time first, so it reads after "until" and after
    "at" alike: "20:05 today", "09:30 tomorrow", "09:30 on Mon 28 Sep"."""
    if moment.date() == today:
        return f"{moment:%H:%M} today"
    if moment.date() == today + timedelta(days=1):
        return f"{moment:%H:%M} tomorrow"
    return f"{moment:%H:%M} on {moment:%a %d %b}"
