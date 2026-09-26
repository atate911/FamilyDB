"""Telegram's commands, answered by code with no model call: /today, /week, /tasks and /now.

What is on, what is left to do and what could start right now are asked often, and code knows
the answers exactly: the calendar (agenda.py), the task list, and the suggestion engine run for
the next few hours without the web. So they are answered at once, for nothing, and still when
the model is down or the day's limit is spent. A command is kept as a message from whoever sent
it, marked processed as it is stored so that no turn ever picks it up, and the answer as her
reply to it, stored before it is sent like any reply; a later turn reads both in the history.
Only the family may ask: anyone else gets the stranger's line and a knock, as with a message.

The heading of each answer is one of her lines (`voice.EVENTS` `cmd_*`), one line so that the
family can rewrite it on the Personality page; the facts under it are worded here. A chat sees
only the tasks asked for in it, as only it gets their reminders.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta

from familydb import agenda, task_service, voice
from familydb.agenda import Agenda, Entry
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.dates import utc_iso
from familydb.store import knocks, members, messages, tasks
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.store.tasks import Task
from familydb.suggest.engine import run as suggest
from familydb.suggest.types import Candidate, SuggestInput
from familydb.tools.registry import ToolContext

log = logging.getLogger(__name__)

# Each command and what Telegram's menu says of it, in the order the menu lists them.
MENU = (
    ("today", "What's on today"),
    ("week", "The next seven days"),
    ("tasks", "Open tasks in this chat"),
    ("now", "What could start right now"),
)
NAMES = frozenset(name for name, _ in MENU)
MAX_TASKS = 12
MAX_NOW = 5  # options offered, the good ones first, as the chat model is asked to
MAX_NOT_NOW = 3  # ideas named as ruled out, with why
# Where the calendar came from, when it was not Google's own.
SOURCE_NOTES = {
    "saved": "Google Calendar isn't connected, so these are the saved plans only.",
    "unavailable": "Google Calendar didn't answer, so these are the saved plans; times may "
    "have moved.",
}


def name_of(text: str) -> str | None:
    """The command a message is, "/today@familybot" as "today"; None for anything else."""
    words = text.split(maxsplit=1)
    if not words or not words[0].startswith("/"):
        return None
    name = words[0][1:].split("@", 1)[0].lower()
    return name if name in NAMES else None


def answer(app: App, msg: IncomingMessage) -> OutgoingMessage | None:
    """The answer to a command, stored as her reply to it. None for one answered already."""
    with closing(app.connect()) as conn:
        return _answer(app, conn, msg)


def _answer(app: App, conn: sqlite3.Connection, msg: IncomingMessage) -> OutgoingMessage | None:
    name = name_of(msg.text)
    if name is None:
        return None
    if msg.channel_update_id and messages.exists_update(conn, msg.channel, msg.channel_update_id):
        return None
    app.refresh(conn)
    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
        with transaction(conn):
            knocks.record(
                conn,
                channel=msg.channel,
                channel_user_id=msg.channel_user_id,
                name=msg.sender_name,
                chat_id=msg.chat_id,
                now=app.clock.now(),
            )
        stranger = voice.say(
            app.settings, "stranger", seed=msg.channel_update_id, id=msg.channel_user_id
        )
        return OutgoingMessage(msg.chat_id, stranger, "unknown_sender")
    now = utc_iso(app.clock.now())
    try:
        with transaction(conn):
            asked = messages.insert_in(
                conn,
                channel=msg.channel,
                channel_update_id=msg.channel_update_id,
                chat_id=msg.chat_id,
                member_id=member.id,
                text=msg.text,
                now=now,
            )
            # Answered by code, never a turn: nothing for the retry job to pick up.
            messages.mark_processed(conn, asked.id, [], now=now)
    except sqlite3.IntegrityError:
        log.info("command %s/%s arrived twice at once", msg.channel, msg.channel_update_id)
        return None
    text = ANSWERS[name](app, conn, msg, member, asked.id)
    with transaction(conn):
        out = messages.insert_out(
            conn, channel=msg.channel, chat_id=msg.chat_id, text=text, reply_to=asked.id, now=now
        )
    return OutgoingMessage(msg.chat_id, text, "ok", in_message_id=asked.id, out_message_id=out.id)


# -- what is on ----------------------------------------------------------------------------------


def _today(app: App, conn: sqlite3.Connection, msg: IncomingMessage, _: Member, seed: int) -> str:
    today = app.clock.today()
    seen = agenda.read(app, conn, today, today)
    timed = [(_entry_key(entry, today), _entry_text(entry, today)) for entry in _on(seen, today)]
    timed += _tasks_today(conn, msg, today, app)
    lines = [text for _, text in sorted(timed)] or ["Nothing on."]
    said = voice.say(app.settings, "cmd_today", seed=seed, day=f"{today:%a %d %b}")
    return _with_source(_under(said, lines), seen)


def _week(app: App, conn: sqlite3.Connection, _msg: IncomingMessage, _: Member, seed: int) -> str:
    today = app.clock.today()
    last = today + timedelta(days=6)
    seen = agenda.read(app, conn, today, last)
    lines = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        on = sorted(_on(seen, day), key=lambda entry: _entry_key(entry, day))
        things = "; ".join(_entry_text(entry, day) for entry in on) or "nothing on"
        # The month where the week starts and where it turns: "Fri 25 Sep", "Sat 26", "Thu 1 Oct".
        month = f" {day:%b}" if offset == 0 or day.day == 1 else ""
        lines.append(f"{day:%a} {day.day}{month}: {things}")
    said = voice.say(app.settings, "cmd_week", seed=seed)
    return _with_source(_under(said, lines), seen)


def _on(seen: Agenda, day: date) -> list[Entry]:
    return [entry for entry in seen.entries if day in entry.days()]


def _entry_key(entry: Entry, day: date) -> str:
    """Sorts a day: all-day things first, then by the time they start that day."""
    return "" if entry.all_day or entry.start[:10] < day.isoformat() else entry.start[11:16]


def _entry_text(entry: Entry, day: date) -> str:
    """One thing on a day, with its idea: "10:00-11:00 Soccer (#12)", "All day: Camping"."""
    title = entry.title + (f" (#{entry.idea_id})" if entry.idea_id else "")
    if entry.status == "tentative":
        title += ", tentative"
    if entry.all_day:
        return f"All day: {title}"
    started_before = entry.start[:10] < day.isoformat()
    ends_today = entry.end is not None and entry.end[:10] == day.isoformat()
    if started_before:
        return (
            f"until {entry.end[11:16]} {title}" if ends_today and entry.end else f"All day: {title}"
        )
    if ends_today and entry.end:
        return f"{entry.start[11:16]}-{entry.end[11:16]} {title}"
    return f"{entry.start[11:16]} {title}"


def _tasks_today(
    conn: sqlite3.Connection, msg: IncomingMessage, today: date, app: App
) -> list[tuple[str, str]]:
    """This chat's reminders and deadlines that fall today, as (time, words)."""
    found = []
    for task in tasks.in_chat(conn, msg.channel, msg.chat_id):
        if task.reminder is not None:
            at = _local(task.reminder.remind_at, app)
            if at.date() == today:
                found.append(
                    (f"{at:%H:%M}", f"{at:%H:%M} reminder: {task.title} (task #{task.id})")
                )
        if task.due_at:
            due = _local(task.due_at, app)
            if due.date() == today:
                found.append((f"{due:%H:%M}", f"{due:%H:%M} due: {task.title} (task #{task.id})"))
    return found


def _with_source(said: str, seen: Agenda) -> str:
    note = SOURCE_NOTES.get(seen.source)
    return f"{said}\n{note}" if note else said


# -- what is left to do --------------------------------------------------------------------------


def _tasks(app: App, conn: sqlite3.Connection, msg: IncomingMessage, _: Member, seed: int) -> str:
    kept = tasks.in_chat(conn, msg.channel, msg.chat_id)
    lines = [_task_text(task, app) for task in kept[:MAX_TASKS]]
    if len(kept) > MAX_TASKS:
        lines.append(f"…and {len(kept) - MAX_TASKS} more on the web page's Tasks.")
    return _under(voice.say(app.settings, "cmd_tasks", seed=seed), lines or ["None."])


def _task_text(task: Task, app: App) -> str:
    """One task and what brings it up: "#12 Bins out (Sam): reminder Sun 27 Sep 19:00, every
    week"."""
    facts = []
    if task.reminder is not None and task.reminder.delivered_at is None:
        facts.append(f"reminder {_local(task.reminder.remind_at, app):%a %d %b %H:%M}")
    if task.due_at:
        facts.append(f"due {_local(task.due_at, app):%a %d %b %H:%M}")
    facts.append(task_service.repeat_words(task) or "")
    facts.append(task.preferred_window)
    owner = f" ({task.owner})" if task.owner else ""
    said = ", ".join(fact for fact in facts if fact)
    return f"#{task.id} {task.title}{owner}" + (f": {said}" if said else "")


def _local(value: str, app: App) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(app.clock.tz)


# -- what could start now ------------------------------------------------------------------------


def _now(
    app: App, conn: sqlite3.Connection, _msg: IncomingMessage, member: Member, seed: int
) -> str:
    """The engine's answer for the next hours, from the saved ideas: no web, no model."""
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        member=member,
        message_id=seed,
        calendar=app.calendar,
        weather=app.weather,
        geocoder=app.geocoder,
    )
    asked = SuggestInput(window="now", question="/now", discover=False)
    result = suggest(ctx, asked, refresh_stale=False)
    offered = [c for c in result.candidates if c.verdict in ("good", "possible")]
    lines = [_option_text(c) for c in offered[:MAX_NOW]]
    more = len(offered) - MAX_NOW + result.not_shown
    if more > 0:
        lines.append(f"…and {more} more.")
    if not lines:
        lines.append("Nothing on the list fits.")
    ruled_out = [c for c in result.candidates if c.verdict == "ruled_out"][:MAX_NOT_NOW]
    if ruled_out:
        lines.append("Not now: " + "; ".join(_ruled_out_text(c) for c in ruled_out) + ".")
    if result.travel_from != "home":
        lines.append(f"Travel from {result.travel_from}.")
    if result.skipped_checks:
        # What was not checked, without the why a log wants: "forecast failed", not the error.
        skipped = dict.fromkeys(note.split(":", 1)[0] for note in result.skipped_checks)
        lines.append("Not checked: " + "; ".join(skipped) + ".")
    return _under(voice.say(app.settings, "cmd_now", seed=seed, window=result.window.label), lines)


def _option_text(candidate: Candidate) -> str:
    maybe = " (maybe)" if candidate.verdict == "possible" else ""
    reasons = ", ".join(candidate.reasons)
    return f"#{candidate.idea_id} {candidate.title}{maybe}" + (f": {reasons}" if reasons else "")


def _ruled_out_text(candidate: Candidate) -> str:
    why = candidate.reasons[0] if candidate.reasons else "does not fit"
    return f"#{candidate.idea_id} {candidate.title} ({why})"


def _under(heading: str, lines: list[str]) -> str:
    return "\n".join([heading, *lines])


ANSWERS: dict[str, Callable[[App, sqlite3.Connection, IncomingMessage, Member, int], str]] = {
    "today": _today,
    "week": _week,
    "tasks": _tasks,
    "now": _now,
}
