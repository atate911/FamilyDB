"""The voice layer: every message the bot sends of its own accord is worded here.

The chat model speaks for itself, in the persona the prompt gives it. Everything else the bot
says (a reminder, "how was it?", a lookup note, a notice that it cannot answer) is written by
code, and comes through `say`: the persona's line for that event (`personas/<name>.lines.toml`),
the family's own rewrite of it (the Personality page, the `voice_lines` setting), or the plain
wording below when neither has one. No model call, so it works when the model is down, the key is
missing or the day's limit is spent.

A proactive message that lands while the family is talking (`FOLDABLE`) is not sent on its own.
`hand_over` holds it for a moment; the chat turn that comes next takes it (`take`), the model
mentions it in its own reply, and the message is marked delivered with that reply. If no turn
comes within `HOLD`, or the model's reply forgets it, the written line goes after all. Holds are
kept in memory: after a restart a held message is simply sent, the way it would have been.
"""

from __future__ import annotations

import logging
import sqlite3
import string
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from familydb import personas
from familydb.dates import utc_iso
from familydb.store import messages

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    label: str  # what the Personality page calls it
    plain: str  # the wording with no persona, and whenever a line cannot be used
    fields: tuple[str, ...]  # the {names} a line may use


EVENTS: dict[str, Event] = {
    "reminder": Event(
        "A reminder",
        "Reminder: {title}{who}  -  task #{task}. Tell me when it's done or ask to snooze it.",
        ("title", "who", "task"),
    ),
    "reminder_late": Event(
        "A reminder sent late, after the bot was off",
        "Reminder: {title}{who}  -  task #{task}. This was due {due}; I was offline then. "
        "Tell me when it's done or ask to snooze it.",
        ("title", "who", "task", "due"),
    ),
    "follow_up": Event(
        "Asking how a plan went",
        "How was {plan} on {day}? Worth doing again?",
        ("plan", "day"),
    ),
    "lookup_done": Event(
        "An idea looked up",
        "Filled in #{idea} {place}: {details}.",
        ("idea", "place", "details"),
    ),
    "location_shared": Event(
        "A location shared on Telegram",
        'Got your location{where}. For the next 3 hours, "what\'s near here?" and "open now" '
        "start from there instead of home.",
        ("where",),
    ),
    "limit_reached": Event(
        "The day's spending limit reached",
        "Today's spending limit (${limit}) is used up, so I can't answer until tomorrow. "
        "Ask again then, or raise the limit on the settings page.",
        ("limit",),
    ),
    "limit_partial": Event(
        "The limit reached halfway through",
        "That much is saved, but today's spending limit stopped me before I finished. "
        "Check what is saved before asking for the rest, so nothing is done twice.",
        (),
    ),
    "gave_up": Event(
        "Too many steps to answer",
        "I couldn't finish that within the steps I'm allowed, so I've stopped. "
        "Try asking again more simply.",
        (),
    ),
    "gave_up_partly": Event(
        "Too many steps, some of it done",
        "That much is saved, but I ran out of steps before I finished. "
        "Check what is saved before asking for the rest, so nothing is done twice.",
        (),
    ),
    "retry_later": Event(
        "Cannot answer now, will retry",
        "Saved your message, but I couldn't process it right now. I'll retry later.",
        (),
    ),
    "cannot_reach": Event(
        "The model cannot be reached",
        "Saved your message, but I can't reach the model at the moment. "
        "An admin needs to check the logs.",
        (),
    ),
    "no_key": Event(
        "No model key yet",
        "I can't answer yet: no model key has been added. An admin can add one on the settings "
        "page, and then ask me again.",
        (),
    ),
    "done": Event("Nothing to add after doing it", "Done.", ()),
    "stranger": Event(
        "Someone not in the family",
        "Sorry, I only talk to the family. Ask one of them to add you; your id here is {id}.",
        ("id",),
    ),
    "start": Event(
        "Telegram's /start",
        "Hi! I'm {name}, the family's planning assistant. Tell me ideas (\"we should try that "
        'ramen place"), plans ("we\'re going to the symphony next Saturday") or ask "what '
        'should we do this weekend?"',
        ("name",),
    ),
}

# Messages the bot sends unasked, which a conversation under way can carry instead.
FOLDABLE = frozenset({"reminder", "reminder_late", "follow_up", "lookup_done"})
# A chat whose family wrote this recently is a conversation under way.
ACTIVE = timedelta(minutes=5)
# How long a held message waits for the next turn before it is sent as written.
HOLD = timedelta(minutes=2)
# How long a turn that took held messages may keep them before they are sent anyway.
IN_TURN = timedelta(minutes=10)


def lines(settings: Any) -> dict[str, str]:
    """Every event's wording now: the family's rewrite, else the persona's line, else plain."""
    chosen = personas.lines(settings.persona)
    own = settings.voice_lines or {}
    return {
        name: (own.get(name) or chosen.get(name) or event.plain) for name, event in EVENTS.items()
    }


def say(settings: Any, event: str, **facts: Any) -> str:
    """The words for one event. A line that cannot be filled in falls back to the plain one."""
    spec = EVENTS[event]
    values = {name: facts.get(name, "") for name in spec.fields}
    line = lines(settings)[event]
    try:
        return line.format(**values).strip()
    except (KeyError, IndexError, ValueError):
        log.warning("the %s line could not be used; saying it plainly", event)
        return spec.plain.format(**values).strip()


def problems(written: dict[str, str]) -> dict[str, str]:
    """What is wrong with lines the family wrote: an unknown event, or a {name} it cannot use."""
    found: dict[str, str] = {}
    for event, line in written.items():
        if event not in EVENTS:
            found[event] = f"there is no {event!r} message"
            continue
        try:
            names = [name for _, name, _, _ in string.Formatter().parse(line) if name is not None]
        except ValueError:
            found[event] = "a { or } is not closed; write {{ or }} for a brace itself"
            continue
        allowed = EVENTS[event].fields
        unknown = [name for name in names if name not in allowed]
        if unknown:
            usable = ", ".join("{" + name + "}" for name in allowed) or "none"
            found[event] = f"{{{unknown[0]}}} is not something it knows; it can use {usable}"
    return found


# -- folding into a conversation under way -------------------------------------------------------


@dataclass
class Held:
    message_id: int
    chat: tuple[str, str]  # (channel, chat_id)
    text: str  # the written line, sent if the conversation does not carry it
    mention: str  # a word the model's reply must contain to count as having said it
    until: datetime


class Holds:
    """Messages waiting for the conversation under way to carry them. Shared by every thread."""

    def __init__(self) -> None:
        self._held: dict[int, Held] = {}
        self._lock = threading.Lock()

    def hold(self, held: Held) -> None:
        with self._lock:
            self._held[held.message_id] = held

    def is_held(self, message_id: int, now: datetime) -> bool:
        with self._lock:
            held = self._held.get(message_id)
            return held is not None and held.until > now

    def take(self, chat: tuple[str, str], now: datetime) -> list[Held]:
        """The messages a turn in this chat should carry; kept back from delivery while it runs."""
        with self._lock:
            taken = [h for h in self._held.values() if h.chat == chat and h.until > now]
            for held in taken:
                held.until = now + IN_TURN
            return taken

    def done(self, taken: list[Held]) -> None:
        """The turn carried them: nothing is left to send."""
        with self._lock:
            for held in taken:
                self._held.pop(held.message_id, None)

    def let_go(self, taken: list[Held], now: datetime) -> None:
        """The turn failed: send them as written at the next chance."""
        with self._lock:
            for held in taken:
                if held.message_id in self._held:
                    self._held[held.message_id].until = now

    def due(self, now: datetime) -> list[int]:
        """Messages whose wait is over, taken off the list to be sent as written."""
        with self._lock:
            over = [i for i, held in self._held.items() if held.until <= now]
            for message_id in over:
                del self._held[message_id]
            return over


def hand_over(
    app: Any,
    conn: sqlite3.Connection,
    message_id: int,
    *,
    event: str,
    channel: str,
    chat_id: str,
    mention: str,
) -> bool:
    """Send a stored proactive message, or hold it for the conversation under way.

    True when it went (or was held); the caller counts it either way. Anything that is not
    `FOLDABLE`, or a chat nobody is talking in, is delivered at once.
    """
    from familydb.delivery import deliver

    now = app.clock.now()
    if event in FOLDABLE and _talking(conn, channel, chat_id, now):
        stored = messages.get(conn, message_id)
        app.held.hold(
            Held(message_id, (channel, chat_id), stored.text if stored else "", mention, now + HOLD)
        )
        log.info("holding message %s for the conversation in %s", message_id, chat_id)
        return True
    return deliver(app, message_id)


def release(app: Any) -> int:
    """Send, as written, every held message no turn carried in time. For the minute job."""
    from familydb.delivery import deliver

    return sum(deliver(app, message_id) for message_id in app.held.due(app.clock.now()))


def _talking(conn: sqlite3.Connection, channel: str, chat_id: str, now: datetime) -> bool:
    if messages.claimed_in_chat(conn, chat_id, now=utc_iso(now)):
        return True
    last = messages.last_inbound_at(conn, channel, chat_id)
    return last is not None and now - datetime.fromisoformat(last) <= ACTIVE
