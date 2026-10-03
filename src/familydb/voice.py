"""The voice layer: every message the bot sends of its own accord is worded here.

The chat model speaks for itself, in the persona the prompt gives it. Everything else the bot
says (a reminder, "how was it?", a lookup note, a notice that it cannot answer) is written by
code, and comes through `say`: the line the persona in force has for that event
(`personas.active`: her own, `personas/<key>/lines.toml`, or the family's rewrite of it from the
Personality page), or the plain wording below when she has none. Any line may say {name}, which
is her name as the persona in force gives it: her own, or the one the family call her. No model
call, so it works when the model is down, the key is missing or the day's limit is spent.

A line may have several wordings, kept as a list, and she picks one each time. Code chooses, not
chance: the same event with the same seed (a message's own id), or with no seed the same facts,
always chooses the same wording, so a resend or a retry says the same words, the same reminder
reads the same every time, and another message may say it another way. A line kept as a string
is one wording, line breaks and all, as older installs stored every line. The plain wordings are
one each.

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
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
    fields: tuple[str, ...]  # the {names} of its own a line may use; {name} goes with every one
    # Facts like those it is said with, for the Personality page to show how a line reads, and
    # for nothing else.
    example: Mapping[str, Any] = field(default_factory=dict)


# What any line may use, whatever the event: her name, from the persona in force.
HERS = ("name",)


EVENTS: dict[str, Event] = {
    "reminder": Event(
        "A reminder",
        "Reminder: {title}{who}  -  task #{task}. Tell me when it's done or ask to snooze it.",
        ("title", "who", "task"),
        {"title": "bins out", "who": " (Sam)", "task": 12},
    ),
    "reminder_late": Event(
        "A reminder sent late, after the bot was off",
        "Reminder: {title}{who}  -  task #{task}. This was due {due}; I was offline then. "
        "Tell me when it's done or ask to snooze it.",
        ("title", "who", "task", "due"),
        {"title": "bins out", "who": " (Sam)", "task": 12, "due": "Tue 22 Sep at 07:30"},
    ),
    "gift_ideas": Event(
        "Gift ideas under a birthday's reminder",
        "Gift ideas saved for {who}: {ideas}.",
        ("who", "ideas"),
        {"who": "Grandma", "ideas": "#41 a gardening apron, #52 a pottery class"},
    ),
    "birthday_wishes": Event(
        "A kid's birthday wish list under her birthday's reminder",
        "On {who}'s own birthday list: {wishes}.",
        ("who", "wishes"),
        {"who": "Mia", "wishes": "roller skates, a sushi dinner"},
    ),
    "gift_ideas_none": Event(
        "A birthday's reminder with no gift ideas saved",
        "No gift ideas saved for {who} yet; tell me any and I'll keep them.",
        ("who",),
        {"who": "Grandma"},
    ),
    "nudge": Event(
        "Bringing up a task kept for some Saturday morning",
        "It's {when}: time for {title}{who}? Task #{task}; tell me when it's done.",
        ("when", "title", "who", "task"),
        {
            "when": "Saturday morning",
            "title": "get the knives sharpened",
            "who": " (Sam)",
            "task": 14,
        },
    ),
    # The heading of each command's answer (commands.py), one line, which the facts follow.
    "cmd_today": Event("Answering /today", "Today, {day}:", ("day",), {"day": "Sat 26 Sep"}),
    "cmd_week": Event("Answering /week", "The next seven days:", ()),
    "cmd_tasks": Event("Answering /tasks", "Open tasks in this chat:", ()),
    "cmd_now": Event(
        "Answering /now", "From the list, {window}:", ("window",), {"window": "now until 19:30"}
    ),
    "plan_rain": Event(
        "The evening before an outdoor plan, when rain is likely",
        "A heads-up for tomorrow: {weather} for {plan}, which is outdoors.",
        ("plan", "weather"),
        {"plan": "#4 The falls hike", "weather": "70% chance of rain"},
    ),
    "plan_closed": Event(
        "The evening before a plan, when the place looks closed then",
        "A heads-up for tomorrow's {plan}: {place} is {hours}.",
        ("plan", "place", "hours"),
        {
            "plan": "#1 Ramen night",
            "place": "Ramen Ichiban",
            "hours": "listed as closed on Mondays",
        },
    ),
    "plan_backup": Event(
        "Another idea offered with a heads-up",
        "Instead, maybe #{idea} {title}: {why}.",
        ("idea", "title", "why"),
        {
            "idea": 7,
            "title": "Board game cafe",
            "why": "can go 10:00-12:00 Saturday, about 10 min drive (estimate)",
        },
    ),
    "follow_up": Event(
        "Asking how a plan went",
        "How was {plan} on {day}? Worth doing again?",
        ("plan", "day"),
        {"plan": "#31 Hopscotch", "day": "Saturday"},
    ),
    # A button under one of those tapped (buttons.py). Each is shown to whoever tapped, and the
    # ones that did something are added under the message, for everyone in the chat.
    "tap_done": Event("A reminder's Done tapped", "Done ✓ ({who}).", ("who",), {"who": "Sam"}),
    "tap_done_again": Event(
        "A repeating reminder's Done tapped",
        "Done ✓ ({who}). Next time: {when}.",
        ("who", "when"),
        {"who": "Sam", "when": "19:00 on Sun 04 Oct"},
    ),
    "tap_snoozed": Event(
        "A reminder snoozed with its button",
        "Snoozed until {when} ({who}).",
        ("who", "when"),
        {"who": "Sam", "when": "09:30 tomorrow"},
    ),
    "tap_again": Event(
        "A plan worth doing again, tapped",
        "Noted: worth doing again ({who}).",
        ("who",),
        {"who": "Sam"},
    ),
    "tap_not_again": Event(
        "A plan not to repeat, tapped",
        "Noted: not one to repeat ({who}).",
        ("who",),
        {"who": "Sam"},
    ),
    "tap_missed": Event(
        "A plan that did not happen, tapped",
        "Noted: you didn't go, so it's back on the list ({who}).",
        ("who",),
        {"who": "Sam"},
    ),
    "tap_wish_yes": Event(
        "A kid's ask answered yes with its button",
        "Yes ✓ ({who}). I've told {kid}.",
        ("who", "kid"),
        {"who": "Sam", "kid": "Mia"},
    ),
    "tap_wish_no": Event(
        "A kid's ask answered not this time with its button",
        "Not this time ({who}). I've told {kid}, kindly.",
        ("who", "kid"),
        {"who": "Sam", "kid": "Mia"},
    ),
    "tap_later": Event(
        "A kid's ask left for later with its button",
        "Left for later. It's on the Kids card on Home when you're ready.",
        (),
    ),
    "tap_parents_only": Event(
        "A kid's ask tapped by somebody who may not answer it",
        "Only a parent can answer that.",
        (),
    ),
    "tap_already": Event(
        "A button tapped for something already dealt with", "That's already dealt with.", ()
    ),
    "tap_stale": Event("A button that no longer works", "That button no longer works.", ()),
    "tap_failed": Event(
        "A button tapped that could not be done",
        "That didn't go through. Tell me in words instead?",
        (),
    ),
    "tap_stranger": Event(
        "A button tapped by someone not in the family", "Only the family can use these.", ()
    ),
    "lookup_done": Event(
        "An idea looked up",
        "Filled in #{idea} {place}: {details}.",
        ("idea", "place", "details"),
        {
            "idea": 31,
            "place": "Hopscotch",
            "details": "Indoor play · hours saved for sat, sun · about 20 min away (estimate)",
        },
    ),
    "lookups_done": Event(
        "The evening's lookups, together",
        "Looked up {count} ideas this evening:\n{found}",
        ("count", "found"),
        {
            "count": 2,
            "found": "• #31 Hopscotch: Indoor play · hours saved for sat, sun\n"
            "• #32 Ramen Ryoma: Noodle bar · closed mon",
        },
    ),
    "lookups_asked": Event(
        "Answering /lookup",
        "Looking up {count} now; I'll say here what I find.",
        ("count",),
        {"count": "3 ideas"},
    ),
    "lookups_none": Event(
        "Answering /lookup with nothing waiting",
        "Nothing is waiting to be looked up.",
        (),
    ),
    "lookups_off": Event(
        "Answering /lookup with lookups switched off",
        "Looking ideas up on the web is switched off, on the settings page under Lookups.",
        (),
    ),
    "location_shared": Event(
        "A location shared on Telegram",
        'Got your location{where}. For the next 3 hours, "what\'s near here?" and "open now" '
        "start from there instead of home.",
        ("where",),
        {"where": " (Old Town, Portland)"},
    ),
    "limit_reached": Event(
        "The day's spending limit reached",
        "Today's spending limit (${limit}) is used up, so I can't answer until tomorrow. "
        "Ask again then, or raise the limit on the settings page.",
        ("limit",),
        {"limit": "2.00"},
    ),
    "kid_flagged": Event(
        "To the parents: a kid asked for something inappropriate",
        "{kid} asked me for something that isn't OK, and I said no: {what}.",
        ("kid", "what"),
        {"kid": "Mia", "what": "a video game rated for adults"},
    ),
    "kid_asks_parent": Event(
        "To the parents: a kid would like a parent to decide",
        "{kid} would like you to decide this one: {what}.",
        ("kid", "what"),
        {"kid": "Mia", "what": "more internet time tonight"},
    ),
    "wish_granted": Event(
        "To a kid: a parent said yes to her wish",
        "Good news, {kid}: yes to {wish}!{note}",
        ("kid", "wish", "note"),
        {"kid": "Mia", "wish": "roller skates", "note": " Saturday, at the shop."},
    ),
    "wish_declined": Event(
        "To a kid: a parent said not this time",
        "{kid}, not this time for {wish}.{note} You can ask again after {again}.",
        ("kid", "wish", "note", "again"),
        {"kid": "Mia", "wish": "a cat", "note": " The allergies, love.", "again": "4 October"},
    ),
    "kid_share": Event(
        "A kid's own share of the day used up",
        "That's all our chatting for today, {kid}. Come back tomorrow! Your list is still "
        "there, and you can move things around on it.",
        ("kid",),
        {"kid": "Mia"},
    ),
    "alert_credit": Event(
        "Telling an admin: a company is out of credit",
        "{company} says the account is out of credit, so I can't ask it anything until it is "
        "topped up with {company}. Another company's key on the settings page would let me carry "
        "on meanwhile.",
        ("company",),
        {"company": "OpenAI"},
    ),
    "alert_key": Event(
        "Telling an admin: a company refused the key",
        "{company} refused my key, so I can't ask it anything. A new one can be pasted on the "
        "settings page, under AI model.",
        ("company",),
        {"company": "OpenAI"},
    ),
    "alert_limit": Event(
        "Telling an admin: the day's limit is used up",
        "Today's spending limit (${limit}) is used up, so I'm not answering anyone until "
        "tomorrow. It can be raised on the settings page, under Spending.",
        ("limit",),
        {"limit": "2.00"},
    ),
    "alert_calendar": Event(
        "Telling an admin: Google shut me out",
        "Google Calendar stopped letting me in, so plans aren't reaching the calendar. Check "
        "that the calendar is still shared with my service account (its address is on the "
        "settings page, under Connections) and that the key was not deleted in Google Cloud; "
        "connecting again there puts either right.",
        (),
    ),
    "alert_model": Event(
        "Telling an admin: a model in use is going, or gone",
        "A model I use is going away: {detail}. Another can be chosen on the settings page, "
        "under AI model.",
        ("detail",),
        {"detail": "OpenAI retires gpt-6-luna on 2026-12-01, in 30 days"},
    ),
    "alert_price": Event(
        "Telling an admin: a price changed",
        "A price changed: {detail}. The spending limit counts the new one from now on.",
        ("detail",),
        {
            "detail": "gpt-6-luna (OpenAI) now costs $0.12 in, $0.6 out a million tokens, was "
            "$0.1 in, $0.5 out"
        },
    ),
    "alert_prices": Event(
        "Telling an admin: prices could not be checked",
        "I couldn't check prices properly: {detail}. Costs are counted from the last good "
        "prices meanwhile.",
        ("detail",),
        {"detail": "OpenRouter's price list could not be read for 3 days running"},
    ),
    "alert_new": Event(
        "Telling an admin: new models to choose from",
        "New models to choose from, {detail}. They're on the settings page, under AI model.",
        ("detail",),
        {"detail": "OpenAI: gpt-6-nova ($0.2 in, $1 out)"},
    ),
    "alert_shift": Event(
        "Telling an admin: what the calls cost or do moved",
        "Something changed in how I'm running this week: {detail}. The status page has the "
        "figures.",
        ("detail",),
        {"detail": "answering the family costs 62% more a message ($0.004, was $0.0025)"},
    ),
    "alert_api": Event(
        "Telling an admin: a company stopped taking part of a request",
        "Heads up: {detail}. Everything still works; the status page has it.",
        ("detail",),
        {
            "detail": "Anthropic no longer takes the refusal fallback for claude-opus-5, so it is "
            "now left out and the rest works without it"
        },
    ),
    "alert_refused": Event(
        "Telling an admin: a company keeps refusing requests",
        "{company} keeps refusing what I send it, for a reason I can't read: {detail}. "
        "The status page has it; another model, or a newer FamilyDB, may be needed.",
        ("company", "detail"),
        {"company": "OpenAI", "detail": "API error 400: Unsupported parameter"},
    ),
    "alert_advice": Event(
        "Telling an admin: what a judgement on the models said",
        "I weighed a change in the models: {detail}. The status page has it, with a way to "
        "put it back or put it in.",
        ("detail",),
        {
            "detail": "claude-sonnet-5 put in place of claude-haiku-4-5, at the same cost or "
            "less (Anthropic): the nearest in price that handles tools well"
        },
    ),
    "kid_limit": Event(
        "A kid's messages for the day used up",
        "That's {limit} messages today, which is all for today. Ask me again tomorrow, or ask a "
        "grown-up.",
        ("limit",),
        {"limit": 20},
    ),
    "kid_later": Event(
        "Can't answer now, where a kid reads it",
        "I can't answer that just now. Ask me again in a little while!",
        (),
    ),
    "kid_tomorrow": Event(
        "Can't answer until tomorrow, where a kid reads it",
        "That's all I can do today. Ask me again tomorrow!",
        (),
    ),
    "kid_type_it": Event(
        "Can't hear a voice note, where a kid reads it",
        "I couldn't hear that one. Could you type it for me?",
        (),
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
    "voice_off": Event(
        "A voice note while they are turned off",
        "I don't listen to voice notes here, so I didn't hear that one. Could you type it?",
        (),
    ),
    "voice_no_ears": Event(
        "A voice note with nobody to hear it",
        "I can't hear voice notes yet: that needs an OpenAI or Gemini key, which an admin can "
        "add on the settings page. Could you type it for now?",
        (),
    ),
    "voice_too_long": Event(
        "A voice note too long to hear",
        "That voice note is longer than the {minutes} minutes I listen to. Could you send it "
        "in shorter pieces, or type it?",
        ("minutes",),
        {"minutes": 5},
    ),
    "voice_unheard": Event(
        "A voice note that could not be heard",
        "Sorry, I couldn't make out that voice note. Could you send it again, or type it?",
        (),
    ),
    "cannot_read": Event(
        "A sticker, file or video sent with no words",
        "I can't open that kind of message. Could you tell me in words?",
        (),
    ),
    "photo_off": Event(
        "A photo while they are turned off",
        "I don't look at photos here, so I didn't see that one. Could you tell me in words?",
        (),
    ),
    "photo_too_large": Event(
        "A photo too large to look at",
        "That picture is too large for me to look at. Could you send it as a photo rather than "
        "a file, or tell me in words?",
        (),
    ),
    "photo_unseen": Event(
        "A photo that could not be looked at",
        "Sorry, I couldn't look at that photo. Could you send it again, or tell me in words?",
        (),
    ),
    "done": Event("Nothing to add after doing it", "Done.", ()),
    "stranger": Event(
        "Someone not in the family",
        "Sorry, I only talk to the family. Ask one of them to add you; your id here is {id}.",
        ("id",),
        {"id": "123456789"},
    ),
    "invite_linked": Event(
        "Somebody's Telegram linked by the link made for them",
        "Welcome, {who}! This Telegram is linked to you now, so I'll know it's you. Tell me "
        "ideas and plans, or ask what to do this weekend.",
        ("who",),
        {"who": "Alex"},
    ),
    "invite_stale": Event(
        "A link that no longer works",
        "That link no longer works: it was used already, or it's more than a day old. Ask "
        "whoever sent it for a new one.",
        (),
    ),
    "invite_taken": Event(
        "A link opened by a Telegram already on the list",
        "This Telegram is already {who}'s on the family list, so I left the link for whoever it "
        "was made for.",
        ("who",),
        {"who": "Sam"},
    ),
    "joined_group": Event(
        "Added to a family group where she reads every message",
        "Hi all, I'm {name}, the family's planning assistant. Tell me ideas and plans as they come "
        "up here, or ask what to do this weekend.",
        (),
    ),
    "joined_group_mentioned": Event(
        "Added to a family group where she has to be mentioned",
        "Hi all, I'm {name}, the family's planning assistant. Mention {bot} or reply to me when "
        "something's for me: an idea, a plan, or what to do this weekend.",
        ("bot",),
        {"bot": "@tate_family_bot"},
    ),
    "start": Event(
        "Telegram's /start, and the bot's description there",
        "Hi! I'm {name}, the family's planning assistant. Tell me ideas (\"we should try that "
        'ramen place"), plans ("we\'re going to the symphony next Saturday") or ask "what '
        'should we do this weekend?" Typed or as a voice note, as long and rambling as you '
        "like.",
        (),
    ),
}

# A line that speaks of how the bot works (a key, a model, a limit in dollars, an admin, the
# settings page), and the one said instead where somebody reads who may not see that: a kid
# (audience.plain). The grown-ups who can mend it are told the cause another way (alerts.py).
PLAIN: dict[str, str] = {
    "cannot_reach": "kid_later",
    "no_key": "kid_later",
    "retry_later": "kid_later",
    "gave_up": "kid_later",
    "gave_up_partly": "kid_later",
    "limit_partial": "kid_later",
    "limit_reached": "kid_tomorrow",
    "voice_no_ears": "kid_type_it",
    "reminder_late": "reminder",
}

# Messages the bot sends unasked, which a conversation under way can carry instead.
FOLDABLE = frozenset(
    {"reminder", "reminder_late", "nudge", "follow_up", "plan_rain", "plan_closed", "lookup_done"}
)
# A chat whose family wrote this recently is a conversation under way.
ACTIVE = timedelta(minutes=5)
# How long a held message waits for the next turn before it is sent as written.
HOLD = timedelta(minutes=2)
# How long a turn that took held messages may keep them before they are sent anyway.
IN_TURN = timedelta(minutes=10)


# A line: one wording, whatever rows it has, or a list of several.
Line = str | Sequence[str]


def wording(persona: personas.Persona) -> dict[str, list[str]]:
    """Every event's wordings in this persona's words, and the plain one where she has none."""
    return {name: _wordings_of(persona, name) for name in EVENTS}


def wordings(line: Line) -> list[str]:
    """A line's wordings: a string is one, whatever rows it has; a list is several, with the
    blank ones left out."""
    several = [line] if isinstance(line, str) else list(line)
    return [words.strip() for words in several if words.strip()]


def boxed(line: Line) -> str:
    """A line as its box on the Personality page shows it: its wordings one to a row. A string
    is shown as it is."""
    return line if isinstance(line, str) else "\n".join(wordings(line))


def usable(event: str) -> tuple[str, ...]:
    """The {names} a line for this event may use: hers, then the event's own."""
    return HERS + EVENTS[event].fields


def say(settings: Any, event: str, *, seed: Any = None, plain: bool = False, **facts: Any) -> str:
    """The words for one event: one wording of the line in force, filled in.

    Which wording is chosen from the event and the seed, a message's own id when the caller has
    one, or with no seed from the facts, so the same inputs always say the same words. A wording
    that cannot be filled in falls back to the plain line. A {name} is always hers: the persona
    in force gives it, not the caller. `plain` is for a chat somebody reads who may not see how
    the bot works (audience.plain): a line about the workings says its `PLAIN` one instead."""
    if plain:
        event = PLAIN.get(event, event)
    persona = personas.active(settings)
    said = _wordings_of(persona, event)
    return _filled(event, said[_turn(event, seed, facts) % len(said)], persona.name, facts)


def reads_as(settings: Any, event: str) -> list[str]:
    """How the line in force for this event reads: each of its wordings filled in with the
    event's example facts, as `say` fills them. For the Personality page, and nothing else."""
    persona = personas.active(settings)
    example = EVENTS[event].example
    return [_filled(event, one, persona.name, example) for one in _wordings_of(persona, event)]


def _wordings_of(persona: personas.Persona, event: str) -> list[str]:
    """The wordings of this persona's line for an event, or the plain one when she has none."""
    return wordings(persona.lines.get(event, "")) or [EVENTS[event].plain]


def _turn(event: str, seed: Any, facts: Mapping[str, Any]) -> int:
    """A number that is the same wherever and whenever the same event is said with the same seed,
    or with no seed the same facts. CRC-32, because Python's hash() is salted afresh in every
    process."""
    basis = [str(seed)] if seed is not None else [f"{key}={facts[key]}" for key in sorted(facts)]
    return zlib.crc32("\n".join([event, *basis]).encode("utf-8"))


def _filled(event: str, words: str, name: str, facts: Mapping[str, Any]) -> str:
    """One wording with the facts and her name filled in, or the plain line when it cannot be."""
    known = {**facts, "name": name}
    values = {wanted: known.get(wanted, "") for wanted in usable(event)}
    try:
        return words.format(**values).strip()
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        log.warning("the %s line could not be used; saying it plainly", event)
        return EVENTS[event].plain.format(**values).strip()


def problems(written: Mapping[str, Line]) -> dict[str, str]:
    """What is wrong with lines the family wrote: an unknown event, or a wording with a {…} it
    cannot fill in. In a line of several wordings, which of them is wrong is said too."""
    found: dict[str, str] = {}
    for event, line in written.items():
        if event not in EVENTS:
            found[event] = f"there is no {event!r} message"
            continue
        several = wordings(line)
        for number, words in enumerate(several, start=1):
            if wrong := _wrong(event, words):
                found[event] = f"in wording {number}, {wrong}" if len(several) > 1 else wrong
                break
    return found


def _wrong(event: str, words: str) -> str | None:
    """What is wrong with one wording of a line for this event, if anything."""
    try:
        names = [name for _, name, _, _ in string.Formatter().parse(words) if name is not None]
    except ValueError:
        return "a { or } is not closed; write {{ or }} for a brace itself"
    allowed = usable(event)
    unknown = [name for name in names if name not in allowed]
    if unknown:
        known = ", ".join("{" + name + "}" for name in allowed)
        return f"{{{unknown[0]}}} is not something it knows; it can use {known}"
    return None


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
    from familydb.store.db import transaction

    # Kept with the message, so the Messages page can say what went out unasked, and how often.
    with transaction(conn):
        messages.mark_sent_as(conn, message_id, event)
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
