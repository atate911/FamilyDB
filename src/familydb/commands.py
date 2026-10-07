"""Telegram's commands, answered by code with no model call: /today, /week, /tasks, /now, /lookup,
/start, and a message with nothing to read.

What is on, what is left and what could start now are asked often and code knows the answers
(agenda.py, the task list, the engine without the web), so they are answered for nothing, even
when the model is down or the limit spent. A command is stored as a message marked processed, so
no turn takes it, and the answer as her reply, stored before sent; a later turn reads both. Only
the family may ask: anyone else gets the stranger's line and a knock.

The heading of each answer is one of her lines (`voice.EVENTS` `cmd_*`), rewritable on the
Personality page; the facts under it are worded here. A chat sees only the tasks asked for in it,
as only it gets their reminders.

/lookup is code calling `look_up_now` as the member, as a button's tap does. /start is her
introduction, or a stranger's line with a knock so Start shows on the Family and setup pages;
from an admin's link (family.py `invite`) it links the sender's Telegram first. A wordless
sticker, file or video gets `cannot_read`, kept as nothing. Added to a group by somebody on the
family list, she introduces herself (`joined_group`); that is kept like anything unasked.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta

from familydb import agenda, family, task_service, voice
from familydb.agenda import Agenda, Entry
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.dates import clock_time, spoken_times, utc_iso
from familydb.store import knocks, members, messages, tasks
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.store.tasks import Task
from familydb.suggest.engine import run as suggest
from familydb.suggest.types import Candidate, SuggestInput
from familydb.tools.registry import ToolContext

log = logging.getLogger(__name__)

MENU = (
    ("today", "What's on today"),
    ("week", "The next seven days"),
    ("tasks", "Open tasks in this chat"),
    ("now", "What could start right now"),
    ("lookup", "Look up the ideas waiting, now"),
)
NAMES = frozenset(name for name, _ in MENU)
MAX_TASKS = 12
MAX_NOW = 5
MAX_NOT_NOW = 3
SOURCE_NOTES = {
    "saved": "Google Calendar isn't connected, so these are the saved plans only.",
    "unavailable": "Google Calendar didn't answer, so these are the saved plans; times may "
    "have moved.",
}


def name_of(text: str) -> str | None:
    words = text.split(maxsplit=1)
    if not words or not words[0].startswith("/"):
        return None
    name = words[0][1:].split("@", 1)[0].lower()
    return name if name in NAMES else None


def answer(app: App, msg: IncomingMessage) -> OutgoingMessage | None:
    with closing(app.connect()) as conn:
        return _answer(app, conn, msg)


def start(app: App, msg: IncomingMessage) -> OutgoingMessage:
    """/start: her introduction, or to a stranger their line with a knock. Not kept.

    With a link's code (made on the Family page) in a private chat, first links the sender's
    Telegram to whoever the link was made for.
    """
    words = msg.text.split()
    private = msg.chat_id == msg.channel_user_id
    if private and len(words) == 2:
        linked = _linked_by(app, msg, words[1])
        if linked is not None:
            return linked
    return _said_by_code(app, msg, "start")


def _linked_by(app: App, msg: IncomingMessage, code: str) -> OutgoingMessage | None:
    """What a link's Start says: welcome, or why it did nothing. None for somebody already on the
    list whose link is spent: greeted as anybody on the list.
    """
    seed = msg.channel_update_id
    with closing(app.connect()) as conn:
        app.refresh(conn)
        try:
            person = family.accept_invite(
                conn, code, telegram_id=msg.channel_user_id, now=app.clock.now()
            )
        except family.InviteRefused as refused:
            if refused.why == "taken":
                owner = refused.owner or "somebody else"
                said = voice.say(app.settings, "invite_taken", seed=seed, who=owner)
                return OutgoingMessage(msg.chat_id, said, "ok")
            if members.resolve(conn, msg.channel, msg.channel_user_id) is not None:
                return None
            _stranger(app, conn, msg)
            said = voice.say(app.settings, "invite_stale", seed=seed)
            return OutgoingMessage(msg.chat_id, said, "unknown_sender")
    log.warning("Telegram %s linked to member %s by a link", msg.channel_user_id, person.id)
    said = voice.say(app.settings, "invite_linked", seed=seed, who=person.display_name)
    return OutgoingMessage(msg.chat_id, said, "ok")


def cannot_read(app: App, msg: IncomingMessage) -> OutgoingMessage:
    """A wordless sticker, file or video: her line saying so, or a stranger's. Not kept."""
    return _said_by_code(app, msg, "cannot_read")


def joined_group(
    app: App,
    *,
    channel: str,
    chat_id: str,
    added_by: str,
    mentioned: bool,
    bot: str | None,
) -> int | None:
    """Her introduction to a group somebody on the family list added her to, stored to be sent; None
    when whoever added her is not family. `mentioned`: she has to be mentioned there (setting or
    Telegram's privacy mode).
    """
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if members.resolve(conn, channel, added_by) is None:
            log.info("added to %s by %s, who is not family; saying nothing", chat_id, added_by)
            return None
        settings = app.settings
        if mentioned and bot:
            said = voice.say(settings, "joined_group_mentioned", seed=chat_id, bot=f"@{bot}")
        else:
            said = voice.say(settings, "joined_group", seed=chat_id)
        with transaction(conn):
            out = messages.insert_out(
                conn, channel=channel, chat_id=chat_id, text=said, now=utc_iso(app.clock.now())
            )
        return out.id


def _said_by_code(app: App, msg: IncomingMessage, event: str) -> OutgoingMessage:
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if members.resolve(conn, msg.channel, msg.channel_user_id) is None:
            return _stranger(app, conn, msg)
    said = voice.say(app.settings, event, seed=msg.channel_update_id)
    return OutgoingMessage(msg.chat_id, said, "ok")


def _stranger(app: App, conn: sqlite3.Connection, msg: IncomingMessage) -> OutgoingMessage:
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


def _answer(app: App, conn: sqlite3.Connection, msg: IncomingMessage) -> OutgoingMessage | None:
    name = name_of(msg.text)
    if name is None:
        return None
    if msg.channel_update_id and messages.exists_update(conn, msg.channel, msg.channel_update_id):
        return None
    app.refresh(conn)
    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
        return _stranger(app, conn, msg)
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
        month = f" {day:%b}" if offset == 0 or day.day == 1 else ""
        lines.append(f"{day:%a} {day.day}{month}: {things}")
    said = voice.say(app.settings, "cmd_week", seed=seed)
    return _with_source(_under(said, lines), seen)


def _on(seen: Agenda, day: date) -> list[Entry]:
    return [entry for entry in seen.entries if day in entry.days()]


def _entry_key(entry: Entry, day: date) -> str:
    return "" if entry.all_day or entry.start[:10] < day.isoformat() else entry.start[11:16]


def _entry_text(entry: Entry, day: date) -> str:
    title = entry.title + (f" (#{entry.idea_id})" if entry.idea_id else "")
    if entry.status == "tentative":
        title += ", tentative"
    if entry.all_day:
        return f"All day: {title}"
    started_before = entry.start[:10] < day.isoformat()
    ends_today = entry.end is not None and entry.end[:10] == day.isoformat()
    if started_before:
        return (
            f"until {clock_time(entry.end)} {title}"
            if ends_today and entry.end
            else f"All day: {title}"
        )
    if ends_today and entry.end:
        return f"{clock_time(entry.start)} to {clock_time(entry.end)} {title}"
    return f"{clock_time(entry.start)} {title}"


def _tasks_today(
    conn: sqlite3.Connection, msg: IncomingMessage, today: date, app: App
) -> list[tuple[str, str]]:
    found = []
    for task in tasks.in_chat(conn, msg.channel, msg.chat_id):
        if task.reminder is not None:
            at = _local(task.reminder.remind_at, app)
            if at.date() == today:
                found.append(
                    (f"{at:%H:%M}", f"{clock_time(at)} reminder: {task.title} (task #{task.id})")
                )
        if task.due_at:
            due = _local(task.due_at, app)
            if due.date() == today:
                found.append(
                    (f"{due:%H:%M}", f"{clock_time(due)} due: {task.title} (task #{task.id})")
                )
    return found


def _with_source(said: str, seen: Agenda) -> str:
    note = SOURCE_NOTES.get(seen.source)
    return f"{said}\n{note}" if note else said


def _tasks(app: App, conn: sqlite3.Connection, msg: IncomingMessage, _: Member, seed: int) -> str:
    kept = tasks.in_chat(conn, msg.channel, msg.chat_id)
    lines = [_task_text(task, app) for task in kept[:MAX_TASKS]]
    if len(kept) > MAX_TASKS:
        lines.append(f"…and {len(kept) - MAX_TASKS} more on the web page's Tasks.")
    return _under(voice.say(app.settings, "cmd_tasks", seed=seed), lines or ["None."])


def _task_text(task: Task, app: App) -> str:
    facts = []
    if task.reminder is not None and task.reminder.delivered_at is None:
        facts.append(f"reminder {_local_when(task.reminder.remind_at, app)}")
    if task.due_at:
        facts.append(f"due {_local_when(task.due_at, app)}")
    facts.append(task_service.repeat_words(task) or "")
    facts.append(task.preferred_window)
    owner = f" ({task.owner})" if task.owner else ""
    said = ", ".join(fact for fact in facts if fact)
    return f"#{task.id} {task.title}{owner}" + (f": {said}" if said else "")


def _local(value: str, app: App) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(app.clock.tz)


def _local_when(value: str, app: App) -> str:
    """ "Thu 1 Oct 8 pm": a stored instant in the family's time, the way they read it."""
    moment = _local(value, app)
    return f"{moment:%a %d %b} {clock_time(moment)}"


def _now(
    app: App, conn: sqlite3.Connection, _msg: IncomingMessage, member: Member, seed: int
) -> str:
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
        skipped = dict.fromkeys(note.split(":", 1)[0] for note in result.skipped_checks)
        lines.append("Not checked: " + "; ".join(skipped) + ".")
    said = voice.say(app.settings, "cmd_now", seed=seed, window=spoken_times(result.window.label))
    return spoken_times(_under(said, lines))


def _option_text(candidate: Candidate) -> str:
    maybe = " (maybe)" if candidate.verdict == "possible" else ""
    reasons = ", ".join(candidate.reasons)
    return f"#{candidate.idea_id} {candidate.title}{maybe}" + (f": {reasons}" if reasons else "")


def _ruled_out_text(candidate: Candidate) -> str:
    why = candidate.reasons[0] if candidate.reasons else "does not fit"
    return f"#{candidate.idea_id} {candidate.title} ({why})"


def _under(heading: str, lines: list[str]) -> str:
    return "\n".join([heading, *lines])


def _lookup(
    app: App, conn: sqlite3.Connection, _msg: IncomingMessage, member: Member, seed: int
) -> str:
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        member=member,
        message_id=seed,
    )
    result = app.registry.dispatch("look_up_now", {}, ctx)
    answered = json.loads(result.content)
    if answered.get("available") is False:
        return voice.say(app.settings, "lookups_off", seed=seed)
    asked = len(answered.get("asked") or [])
    if not asked:
        return voice.say(app.settings, "lookups_none", seed=seed)
    count = "1 idea" if asked == 1 else f"{asked} ideas"
    return voice.say(app.settings, "lookups_asked", seed=seed, count=count)


ANSWERS: dict[str, Callable[[App, sqlite3.Connection, IncomingMessage, Member, int], str]] = {
    "today": _today,
    "week": _week,
    "tasks": _tasks,
    "now": _now,
    "lookup": _lookup,
}
