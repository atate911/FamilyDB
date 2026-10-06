"""Buttons under what the bot says unasked, and what a tap on one does.

A tap does what saying so in the chat would, without a model: code calls the tool the model would
have called, as the member who tapped, and says what it did in her words (`voice.say`). It costs
nothing and works when the model is down or the limit spent.

What a button sends back is untrusted: an action from a closed list and the number of what it is
about, both checked, and whoever tapped checked against the family list, before anything is done.
A tap is kept as a message so its tool call has one to belong to. The same tap delivered twice is
done once; a tap on something already dealt with does nothing and says so.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from datetime import time as clock_time
from typing import Any

from familydb import roles, voice
from familydb.dates import utc_iso
from familydb.store import (
    calls,
    ideas,
    lists,
    members,
    messages,
    outcomes,
    plans,
    tasks,
    wishes,
)
from familydb.store.db import from_json, transaction
from familydb.tools.registry import ToolContext

log = logging.getLogger(__name__)

# (action, label) per kind of message; what each does is in `_task_job` and `_plan_job`.
REMINDER = (("done", "✓ Done"), ("hour", "In an hour"), ("tomorrow", "Tomorrow"))
FOLLOW_UP = (("again", "Yes, again"), ("not_again", "Not again"), ("missed", "Didn't go"))
WISH = (("wish_yes", "Yes!"), ("wish_no", "Not this time"), ("wish_later", "Later"))
UNDO = (("undo", "↩ Undo"),)
# A thing on a list, ticked as bought (/list); its label is the thing's own.
TICK = (("tick", "✓"),)
LABELS = dict(REMINDER + FOLLOW_UP + WISH + UNDO + TICK)
SNOOZES = ("hour", "tomorrow")
# "Tomorrow" is the same time of day, on the wall clock, between these; else nine.
TOMORROW_FROM, TOMORROW_UNTIL = clock_time(8, 0), clock_time(20, 0)
TOMORROW_AT = clock_time(9, 0)
MAX_NUMBER_DIGITS = 18

Button = dict[str, str]


def for_reminder(task_id: int) -> list[Button]:
    return _row(REMINDER, task_id)


def for_follow_up(plan_id: int) -> list[Button]:
    return _row(FOLLOW_UP, plan_id)


def for_wish(wish_id: int) -> list[Button]:
    return _row(WISH, wish_id)


def for_undo(call_id: int) -> list[Button]:
    """Under a reply that changed something: take it back (familydb/undo.py), on a row of its
    own beside any a reminder it carries brought."""
    return in_row(_row(UNDO, call_id), "undo")


def _row(choices: tuple[tuple[str, str], ...], number: int) -> list[Button]:
    return [{"label": label, "data": f"{action}:{number}"} for action, label in choices]


def in_row(row: list[Button], key: str) -> list[Button]:
    """These buttons as one of several rows under a message, drawn one row per `key` in the order
    they come: a tap takes off its own row and leaves the others (a message about more than one
    thing, each with its own buttons)."""
    return [{**button, "row": key} for button in row]


@dataclass(frozen=True)
class Tapped:
    """What a tap did: `toast` to whoever tapped; `note` under the message for everyone, saying who
    did what; `finished` takes the buttons off.
    """

    toast: str
    note: str | None = None
    finished: bool = False


@dataclass(frozen=True)
class _Job:
    tool: str
    values: dict[str, Any]
    about: str
    event: str
    facts: dict[str, Any] = field(default_factory=dict)
    # The call an Undo names (ToolContext.undo_target).
    target: int | None = None


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

    `tap_id` is the channel's id for this tap, so a redelivery is seen as such; `data` is what
    the button sent back.
    """
    settings = app.settings
    member = members.resolve(conn, channel, channel_user_id)
    if member is None:
        return Tapped(voice.say(settings, "tap_stranger", seed=tap_id))
    action, _, number = data.partition(":")
    digits = number.isascii() and number.isdigit()
    if action not in LABELS or not digits or len(number) > MAX_NUMBER_DIGITS:
        return Tapped(voice.say(settings, "tap_stale", seed=tap_id), finished=True)
    if action.startswith("wish_"):
        early = _wish_check(conn, member, action, int(number))
        if early is not None:
            return Tapped(voice.say(settings, early, seed=tap_id), finished=early != "tap_later")
    update_id = f"tap:{tap_id}"
    if messages.exists_update(conn, channel, update_id):
        return None
    if action.startswith("wish_"):
        planned: Any = _wish_job
    elif action in SNOOZES or action == "done":
        planned = _task_job
    elif action == "undo":
        planned = _undo_job
    elif action == "tick":
        planned = _list_job
    else:
        planned = _plan_job
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
        source="tap",
        undo_target=job.target,
    )
    result = app.registry.dispatch(job.tool, job.values, ctx, call_id=update_id)
    with transaction(conn):
        messages.mark_processed(conn, kept.id, [] if result.is_error else [result.summary], now=now)
    if result.is_error:
        log.warning("tap %s on #%s did not go through: %s", action, number, result.content)
        return Tapped(voice.say(settings, "tap_failed", seed=kept.id))
    event, facts = job.event, job.facts
    after = tasks.get(conn, job.values["task_id"]) if job.event == "tap_done" else None
    if after is not None and after.status == "open" and after.reminder is not None:
        moment = datetime.fromisoformat(after.reminder.remind_at).astimezone(app.clock.tz)
        event, facts = "tap_done_again", {"when": when_text(moment, app.clock.today())}
    line = voice.say(settings, event, seed=kept.id, who=member.display_name, **facts)
    return Tapped(line, line, finished=True)


def _wish_check(
    conn: sqlite3.Connection, member: members.Member, action: str, wish_id: int
) -> str | None:
    """Why a tap on a kid's ask does nothing: only a parent answers, Later is only a note, an
    answered ask is answered.
    """
    if not roles.may(member.role, "decide"):
        return "tap_parents_only"
    wish = wishes.get(conn, wish_id)
    if wish is None:
        return "tap_stale"
    if wish.status not in ("open", "turned_away"):
        return "tap_already"
    return "tap_later" if action == "wish_later" else None


def _wish_job(app: Any, conn: sqlite3.Connection, action: str, wish_id: int) -> _Job | str:
    wish = wishes.get(conn, wish_id)
    owner = members.get(conn, wish.member_id) if wish is not None else None
    if wish is None or owner is None:
        return "tap_stale"
    yes = action == "wish_yes"
    return _Job(
        "update_wish",
        {"wish_id": wish.id, "status": "granted" if yes else "declined"},
        f"{owner.display_name}'s ask #{wish.id} {wish.title}",
        "tap_wish_yes" if yes else "tap_wish_no",
        {"kid": owner.display_name},
    )


def _task_job(app: Any, conn: sqlite3.Connection, action: str, task_id: int) -> _Job | str:
    task = tasks.get(conn, task_id)
    if task is None:
        return "tap_stale"
    if task.status != "open":
        return "tap_already"
    about = f"task #{task.id} {task.title}"
    if action == "done":
        return _Job("update_task", {"task_id": task.id, "status": "done"}, about, "tap_done")
    now = app.clock.now()
    moment = snoozed_until(action, now)
    return _Job(
        "update_task",
        {"task_id": task.id, "remind_at": moment.isoformat(timespec="minutes")},
        about,
        "tap_snoozed",
        {"when": when_text(moment, now.date())},
    )


def _undo_job(app: Any, conn: sqlite3.Connection, action: str, call_id: int) -> _Job | str:
    row = calls.get(conn, call_id)
    if row is None or row["undo"] is None:
        return "tap_stale"
    if row["undone_at"] is not None:
        return "tap_already"
    what = (from_json(row["undo"]) or {}).get("about", "")
    return _Job("undo", {}, f"undo {what}", "tap_undone", {"what": what}, target=call_id)


def _list_job(app: Any, conn: sqlite3.Connection, action: str, item_id: int) -> _Job | str:
    item = lists.item(conn, item_id)
    name = lists.name_by_id(conn, item.list_id) if item is not None else None
    if item is None or name is None:
        return "tap_stale"
    if item.ticked_at is not None:
        return "tap_already"
    values = {"action": "tick", "items": [item.text], "name": name}
    about = f"{item.text} on the {name} list"
    return _Job("shopping_list", values, about, "tap_ticked", {"item": item.text})


def _plan_job(app: Any, conn: sqlite3.Connection, action: str, plan_id: int) -> _Job | str:
    plan = plans.get(conn, plan_id)
    idea = ideas.get(conn, plan.idea_id) if plan is not None and plan.idea_id else None
    if plan is None or idea is None:
        return "tap_stale"
    day = plan.start[:10]
    if outcomes.exists_since(conn, idea_id=idea.id, plan_id=plan.id, since=day):
        return "tap_already"
    about = f"#{idea.id} {plan.title} on {date.fromisoformat(day):%A}"
    if action == "missed":
        if idea.status == "dropped":
            return "tap_already"
        return _Job("update_idea", {"id": idea.id, "status": "idea"}, about, "tap_missed")
    return _Job(
        "record_outcome",
        {"plan_id": plan.id, "happened_on": day, "would_repeat": action == "again"},
        about,
        "tap_again" if action == "again" else "tap_not_again",
    )


def snoozed_until(action: str, now: datetime) -> datetime:
    """When a snoozed reminder comes back: an hour on, or tomorrow at this time of day on the
    wall clock (so a clock change does not move it), unless that is before eight or after eight
    in the evening, when it is nine. A tap at half eleven at night is not answered at half
    eleven the next night."""
    if action == "hour":
        return now + timedelta(hours=1)
    at = now.time().replace(second=0, microsecond=0)
    if not TOMORROW_FROM <= at <= TOMORROW_UNTIL:
        at = TOMORROW_AT
    return datetime.combine(now.date() + timedelta(days=1), at, tzinfo=now.tzinfo)


def when_text(moment: datetime, today: date) -> str:
    """When a snoozed reminder comes back, time first so it reads after "until" and "at": "20:05
    today", "09:30 on Mon 28 Sep".
    """
    if moment.date() == today:
        return f"{moment:%H:%M} today"
    if moment.date() == today + timedelta(days=1):
        return f"{moment:%H:%M} tomorrow"
    return f"{moment:%H:%M} on {moment:%a %d %b}"
