"""The morning message, no model call: at `morning_hour`, at most one message in each chat that has
something for it, and none on an empty day.

Its parts, each with its own switch, in this order:

- the day ahead (`morning_agenda`): today's plans and a dated idea that ends this week when a free
  day could fit it, in the family's chat; today's reminders and deadlines where each task's
  reminders go;
- yesterday's reminders nobody acted on (`chase_missed`), each once, with a button to tick it off;
- what is due tomorrow (`deadline_heads_up`), so a deadline is not missed for want of a reminder;
- once a week (`forgotten_roundup`, on `roundup_day`), to-dos a week old or more with nothing to
  bring them up, five at most.

Each thing goes where that task's reminders go (routing.for_task), so a person's things reach them
and a page's shared conversation gets one message with all of it. Where a kid reads it is said
plainly, without numbers, and never names a birthday's task or a present's plan. Sent once a day in
a chat (`mornings`), and never held to ride a reply.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from familydb import agenda, audience, buttons, routing, voice, windows
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import ideas, messages, mornings, tasks
from familydb.store.db import transaction
from familydb.store.ideas import GIFT, Idea
from familydb.store.tasks import Task
from familydb.suggest.engine import run as suggest
from familydb.suggest.types import SuggestInput
from familydb.tools.registry import ToolContext

log = logging.getLogger(__name__)

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Said a week ago or more, and not brought up by anything: the round-up's to-dos.
WAITED = timedelta(days=7)
MOST_IN_ROUNDUP = 5
# After a restart the morning message still goes, until noon.
CATCH_UP_UNTIL = 12
# A chased task's own Done, its title cut to fit a button.
BUTTON_TITLE = 24


@dataclass
class Morning:
    """What one chat's morning message holds."""

    plans: list[agenda.Entry] = field(default_factory=list)
    today: list[tuple[str, Task, str]] = field(default_factory=list)  # (sort key, task, what)
    ending: list[tuple[Idea, date]] = field(default_factory=list)
    chase: list[tuple[int, Task]] = field(default_factory=list)
    tomorrow: list[Task] = field(default_factory=list)
    roundup: list[Task] = field(default_factory=list)

    def parts(self) -> list[str]:
        """Which parts it has, as the Messages page counts them."""
        named = {
            "agenda": self.plans or self.today or self.ending,
            "chase": self.chase,
            "deadlines": self.tomorrow,
            "roundup": self.roundup,
        }
        return [name for name, held in named.items() if held]


def any_on(settings: Any) -> bool:
    return bool(
        settings.morning_agenda
        or settings.chase_missed
        or settings.deadline_heads_up
        or settings.forgotten_roundup
    )


def due(app: App) -> bool:
    """Whether this morning's message should have gone by now (the catch-up after a restart)."""
    hour = app.clock.now().hour
    return any_on(app.settings) and app.settings.morning_hour <= hour < CATCH_UP_UNTIL


def run_morning(app: App) -> int:
    """Each chat's morning message, once today; returns how many went."""
    app.refresh()
    settings = app.settings
    if not any_on(settings):
        return 0
    moment = app.clock.now()
    today = moment.date()
    with closing(app.connect()) as conn:
        chats = gather(app, conn, moment)
        sent = 0
        for (channel, chat_id), morning in chats.items():
            if app.senders.get(channel) is None:
                log.info("the morning message for %s waits: nothing can send there", channel)
                continue
            sent += _send(app, conn, channel, chat_id, morning, today)
    return sent


def gather(app: App, conn: sqlite3.Connection, moment: datetime) -> dict[tuple[str, str], Morning]:
    """Every chat's morning, by where each thing goes. Reads only."""
    settings = app.settings
    tz = app.clock.tz
    today = moment.date()
    chats: dict[tuple[str, str], Morning] = {}

    def at(where: tuple[str, str]) -> Morning:
        return chats.setdefault(where, Morning())

    def to(task: Task) -> Morning:
        return at(routing.for_task(conn, settings, task))

    def bounds(day: date) -> tuple[str, str]:
        start = datetime.combine(day, time.min, tzinfo=tz)
        return utc_iso(start), utc_iso(start + timedelta(days=1))

    family = routing.family_chat(settings) or ("web", "web")
    if settings.morning_agenda:
        seen = agenda.read(app, conn, today, today)
        on = sorted(agenda.on(seen, today), key=lambda entry: agenda.entry_key(entry, today))
        live = [entry for entry in on if entry.status != "cancelled"]
        if live:
            at(family).plans = live
        rest_of_today = (utc_iso(moment), bounds(today)[1])
        for task in tasks.reminded_between(conn, *rest_of_today):
            assert task.reminder is not None
            at_time = datetime.fromisoformat(task.reminder.remind_at).astimezone(tz)
            to(task).today.append((f"{at_time:%H:%M}", task, f"{at_time:%H:%M} reminder"))
        for task in tasks.due_between(conn, *bounds(today)):
            assert task.due_at is not None
            by = datetime.fromisoformat(task.due_at).astimezone(tz)
            to(task).today.append((f"{by:%H:%M}", task, f"due {by:%H:%M}"))
        ending = _ending(app, conn, today)
        if ending:
            at(family).ending = ending
    if settings.chase_missed:
        for reminder_id, task in tasks.unchased(
            conn,
            delivered_from=bounds(today - timedelta(days=1))[0],
            delivered_until=bounds(today)[0],
        ):
            to(task).chase.append((reminder_id, task))
    if settings.deadline_heads_up:
        for task in tasks.due_between(conn, *bounds(today + timedelta(days=1))):
            to(task).tomorrow.append(task)
    if settings.forgotten_roundup and WEEKDAYS[today.weekday()] == settings.roundup_day:
        for task in tasks.waiting(conn, said_before=utc_iso(moment - WAITED)):
            if windows.read(task.preferred_window, until=task.until, today=today) is not None:
                continue  # its window will bring it up
            held = to(task).roundup
            if len(held) < MOST_IN_ROUNDUP:
                held.append(task)
    return chats


def _ending(app: App, conn: sqlite3.Connection, today: date) -> list[tuple[Idea, date]]:
    """Ideas whose last day is this week, with the first free day the engine finds for them (no
    model call, no lookup queued); each is brought up once."""
    sunday = today + timedelta(days=6 - today.weekday())
    dated = [
        idea
        for idea in ideas.ending_between(conn, today.isoformat(), sunday.isoformat())
        if idea.kind.casefold() != GIFT
    ]
    if not dated:
        return []
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        calendar=app.calendar,
        weather=app.weather,
        source="job",
    )
    asked = SuggestInput(
        window="dates",
        start=today.isoformat(),
        end=sunday.isoformat(),
        idea_ids=[idea.id for idea in dated],
        discover=False,
        question="which ideas ending this week have a free day",
    )
    result = suggest(ctx, asked, refresh_stale=False)
    by_id = {idea.id: idea for idea in dated}
    return [
        (by_id[candidate.idea_id], date.fromisoformat(candidate.fits_days[0]))
        for candidate in result.candidates
        # Not ruled out, and a day it fits: "looks free" is all that is said, so an unknown
        # opening time does not keep it back.
        if candidate.verdict != "ruled_out" and candidate.fits_days and candidate.idea_id in by_id
    ]


def _send(
    app: App, conn: sqlite3.Connection, channel: str, chat_id: str, morning: Morning, today: date
) -> int:
    """Word one chat's morning, keep it and send it; 0 when there is nothing to say there or it
    went already today."""
    plain = audience.plain(conn, channel, chat_id)
    presents = audience.everyone_may(conn, channel, chat_id, "decide")
    if not presents:
        # A birthday's to-do and a present's plan are never said where a kid reads.
        _keep_from_kids(conn, morning)
    parts = morning.parts()
    if not parts:
        return 0
    now = utc_iso(app.clock.now())
    with transaction(conn):
        if mornings.sent(conn, channel, chat_id, today.isoformat()):
            return 0
        out = messages.insert_out(
            conn,
            channel=channel,
            chat_id=chat_id,
            text=words(app.settings, morning, today, seed=f"{chat_id}:{today}", plain=plain),
            now=now,
            buttons=_chase_buttons(morning) or None,
        )
        mornings.record(
            conn,
            channel=channel,
            chat_id=chat_id,
            day=today.isoformat(),
            message_id=out.id,
            parts=parts,
            now=now,
        )
        tasks.mark_chased(conn, [reminder_id for reminder_id, _ in morning.chase], now)
        ideas.mark_nudged(conn, [idea.id for idea, _ in morning.ending], now)
    voice.hand_over(
        app, conn, out.id, event="morning", channel=channel, chat_id=chat_id, mention=""
    )
    return 1


def _keep_from_kids(conn: sqlite3.Connection, morning: Morning) -> None:
    def fine(task: Task) -> bool:
        return not task.gift_for

    gifts = {
        entry.idea_id
        for entry in morning.plans
        if entry.idea_id is not None
        and (idea := ideas.get(conn, entry.idea_id)) is not None
        and idea.kind.casefold() == GIFT
    }
    morning.plans = [entry for entry in morning.plans if entry.idea_id not in gifts]
    morning.today = [item for item in morning.today if fine(item[1])]
    morning.chase = [item for item in morning.chase if fine(item[1])]
    morning.tomorrow = [task for task in morning.tomorrow if fine(task)]
    morning.roundup = [task for task in morning.roundup if fine(task)]


def words(settings: Any, morning: Morning, today: date, *, seed: str, plain: bool) -> str:
    """The morning message as sent: her lines for each part, the things under them by code."""

    def named(task: Task) -> str:
        who = f" ({task.owner})" if task.owner else ""
        return f"{task.title}{who}" if plain else f"#{task.id} {task.title}{who}"

    tz = settings.tzinfo
    lines = [voice.say(settings, "morning", seed=seed, day=f"{today:%a} {today.day} {today:%b}")]
    day_lines = [
        (agenda.entry_key(entry, today), agenda.entry_text(entry, today, numbers=not plain))
        for entry in morning.plans
    ]
    day_lines += [(key, f"{what}: {named(task)}") for key, task, what in morning.today]
    lines += [text for _, text in sorted(day_lines)]
    for idea, free in morning.ending:
        last = idea.last_day
        assert last is not None
        lines.append(
            voice.say(
                settings,
                "morning_ending",
                seed=seed,
                idea=idea.title if plain else f"#{idea.id} {idea.title}",
                last="today" if last == today else f"{last:%A}",
                free="today" if free == today else f"{free:%A}",
            )
        )
    if morning.chase:
        lines += ["", voice.say(settings, "morning_chase", seed=seed)]
        lines += [named(task) for _, task in morning.chase]
    if morning.tomorrow:
        lines += ["", voice.say(settings, "morning_deadlines", seed=seed)]
        for task in morning.tomorrow:
            assert task.due_at is not None
            by = datetime.fromisoformat(task.due_at).astimezone(tz)
            lines.append(f"{named(task)}, by {by:%H:%M}")
    if morning.roundup:
        lines += ["", voice.say(settings, "morning_roundup", seed=seed)]
        lines += [named(task) for task in morning.roundup]
    return "\n".join(lines)


def _chase_buttons(morning: Morning) -> list[buttons.Button]:
    """A row for each chased to-do: tick it off by its name, or bring it back tomorrow."""
    rows: list[buttons.Button] = []
    for _, task in morning.chase:
        title = task.title if len(task.title) <= BUTTON_TITLE else task.title[: BUTTON_TITLE - 1]
        title += "" if len(task.title) <= BUTTON_TITLE else "…"
        row = [
            {"label": f"✓ {title}", "data": f"done:{task.id}"},
            {"label": buttons.LABELS["tomorrow"], "data": f"tomorrow:{task.id}"},
        ]
        rows += buttons.in_row(row, str(task.id))
    return rows
