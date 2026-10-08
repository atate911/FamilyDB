"""The voice layer: every message the bot sends of its own accord is worded here, by code, with no
model call.

`say` returns the line the persona in force has for an event (`personas.active`: hers, or the
family's rewrite), else the plain wording below. Any line may say {name}.

A line may have several wordings. Code chooses, not chance: the same event with the same seed (a
message's id), or with no seed the same facts, always chooses the same wording, so a resend or
retry says the same words. A string line is one wording, as older installs stored every line.

A proactive message landing while the family is talking (`FOLDABLE`) is held by `hand_over`; the
next chat turn takes it (`take`), the model mentions it, and it is marked delivered with that
reply. If no turn comes within `HOLD`, or the reply forgets it, the written line goes. Holds are
in memory: after a restart a held message is simply sent.
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

from familydb import happening, personas
from familydb.dates import utc_iso
from familydb.store import messages

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    label: str
    plain: str
    fields: tuple[str, ...]
    # Facts like those it is said with, for the Personality page to show how a line reads.
    example: Mapping[str, Any] = field(default_factory=dict)


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
        {"title": "bins out", "who": " (Sam)", "task": 12, "due": "Tue 22 Sep at 7:30 am"},
    ),
    "reminder_from": Event(
        "Under a reminder somebody asked for on another's behalf",
        "{asker} asked me to remind you.",
        ("asker",),
        {"asker": "Sam"},
    ),
    "reminder_plan": Event(
        "Under a reminder set before a plan: when the plan is",
        "It's {when}.",
        ("when",),
        {"when": "on Wed 19 Nov at 19:30"},
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
    "cmd_today": Event("Answering /today", "Today, {day}:", ("day",), {"day": "Sat 26 Sep"}),
    "cmd_week": Event("Answering /week", "The next seven days:", ()),
    "cmd_tasks": Event("Answering /tasks", "Open tasks, this chat's and yours:", ()),
    "cmd_now": Event(
        "Answering /now", "From the list, {window}:", ("window",), {"window": "now until 7:30 pm"}
    ),
    "push_note": Event(
        "The notice on a phone or tablet when she writes on the page (never the words)",
        "{name} has a message",
        (),
        {},
    ),
    "morning": Event(
        "The morning message: its first line",
        "Good morning. Here's {day}:",
        ("day",),
        {"day": "Tue 6 Oct"},
    ),
    "morning_ending": Event(
        "The morning message: a dated idea that ends this week, with a free day for it",
        "{idea} ends {last}; {free} looks free for it.",
        ("idea", "last", "free"),
        {"idea": "The lantern festival", "last": "Sunday", "free": "Saturday"},
    ),
    "morning_chase": Event(
        "The morning message: reminders from yesterday nobody acted on",
        "Still open from yesterday:",
        (),
        {},
    ),
    "morning_deadlines": Event(
        "The morning message: what is due tomorrow",
        "Due tomorrow:",
        (),
        {},
    ),
    "morning_roundup": Event(
        "The morning message, once a week: to-dos that have waited",
        "Waiting a week or more, with nothing to bring them up (tell me if any can go):",
        (),
        {},
    ),
    "plan_rain": Event(
        "The evening before an outdoor plan, when rain is likely",
        "A heads-up for tomorrow: {weather} for {plan}, which is outdoors.",
        ("plan", "weather"),
        {"plan": "#4 The falls hike", "weather": "70% chance of rain"},
    ),
    "plan_rain_today": Event(
        "An outdoor plan later today, when rain is likely and the evening before was missed",
        "A heads-up for today: {weather} for {plan}, which is outdoors.",
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
    "plan_closed_today": Event(
        "A plan later today, when the place looks closed and the evening before was missed",
        "A heads-up for today's {plan}: {place} is {hours}.",
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
            "why": "can go 10 am to 12 pm Saturday, about 10 min drive (estimate)",
        },
    ),
    "follow_up": Event(
        "Asking how a plan went",
        "How was {plan} on {day}? Worth doing again?",
        ("plan", "day"),
        {"plan": "#31 Hopscotch", "day": "Saturday"},
    ),
    # A button tapped (buttons.py): shown to whoever tapped; ones that did something are added under
    # the message for everyone.
    "tap_done": Event("A reminder's Done tapped", "Done ✓ ({who}).", ("who",), {"who": "Sam"}),
    "tap_done_again": Event(
        "A repeating reminder's Done tapped",
        "Done ✓ ({who}). Next time: {when}.",
        ("who", "when"),
        {"who": "Sam", "when": "7 pm on Sun 4 Oct"},
    ),
    "tap_ticked": Event(
        "A thing on the list ticked with its button",
        "Got it ✓ {item} ({who}).",
        ("item", "who"),
        {"item": "milk", "who": "Sam"},
    ),
    "tap_undone": Event(
        "Undo tapped under a reply",
        "Undone ({who}): {what}.",
        ("who", "what"),
        {"who": "Sam", "what": "added task #12 Call the plumber"},
    ),
    "tap_snoozed": Event(
        "A reminder snoozed with its button",
        "Snoozed until {when} ({who}).",
        ("who", "when"),
        {"who": "Sam", "when": "9:30 am tomorrow"},
    ),
    "tap_again": Event(
        "A plan loved, tapped",
        "Noted: loved it, and worth doing again ({who}).",
        ("who",),
        {"who": "Sam"},
    ),
    "tap_ok": Event(
        "A plan that was OK, tapped",
        "Noted: it was OK ({who}).",
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
        "A button tapped by somebody who may not do what it does (a kid's ask, how a plan went)",
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
    "cmd_list": Event("Heading /list", "On the shopping list:", (), {}),
    "cmd_list_empty": Event(
        "Answering /list when it is empty", "Nothing on the shopping list.", (), {}
    ),
    "undo_done": Event(
        "Answering /undo",
        "Undone: {what}.",
        ("what",),
        {"what": "added task #12 Call the plumber"},
    ),
    "undo_not": Event(
        "Answering /undo when nothing was undone",
        "Nothing undone: {why}.",
        ("why",),
        {"why": "nothing of yours to undo here from the last day"},
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
    "lookups_wait": Event(
        "Answering /lookup for a kid, whose lookups wait for the evening",
        "Lookups wait for the evening. Ask a parent if one can't wait!",
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
        "Telling an admin: Google refused my key, or I have none",
        "Google Calendar won't take my key (it was refused, deleted or can't be read), so plans "
        "aren't reaching the calendar. Connecting the calendar again with a new key on the "
        "settings page, under Connections, puts it right.",
        (),
    ),
    "alert_calendar_access": Event(
        "Telling an admin: the calendar is no longer there for me",
        "Google Calendar no longer shows me the calendar, so plans aren't reaching it and I "
        "can't tell a plan moved there from one taken off. Check that it is still shared with "
        "my service account (its address is on the settings page, under Connections) and not "
        "deleted; sharing it again, or connecting another there, puts it right.",
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
    "alert_happening": Event(
        "Telling an admin: a place I read for what is on could not be read",
        "I couldn't read one of the places I check for what's on near home: {detail}. It's in "
        "the settings, on the {page} page.",
        ("detail", "page"),
        {
            "detail": "library.example.org could not be read for 3 days running (HTTP 404)",
            "page": happening.NAME,
        },
    ),
    "alert_calendars": Event(
        "Telling an admin: event calendars found near home",
        "I found {detail} near home. Tick the ones to read in the settings, on the {page} page.",
        ("detail", "page"),
        {
            "detail": "2 new event calendars: Fort Vancouver Regional Library and Vancouver "
            "Parks and Recreation",
            "page": happening.NAME,
        },
    ),
    "alert_backup": Event(
        "Telling an admin: the backups stopped working",
        "The backups need a look: {detail}. Until one works, what the family has told me is on "
        "this server alone. RUNBOOK section 7 has the backup line to check.",
        ("detail",),
        {"detail": "the last good backup was made 2026-10-01 10:15 UTC"},
    ),
    "alert_disk": Event(
        "Telling an admin: the server's disk is nearly full",
        "The server's disk is nearly full ({detail}). When it fills, I can't keep anything, "
        "messages included: old backups and logs are the usual things to clear.",
        ("detail",),
        {"detail": "312 MB free"},
    ),
    "alert_telegram": Event(
        "On the status page: Telegram refused the bot's token",
        "Telegram refused my token, so I can't hear or answer anyone there. A new one from "
        "@BotFather can be pasted on the settings page, under Connections.",
        (),
    ),
    "alert_advice": Event(
        "Telling an admin: what a judgment on the models said",
        "I weighed a change in the models: {detail}. The status page has it, with a way to "
        "put it back or put it in.",
        ("detail",),
        {
            "detail": "claude-sonnet-5 put in place of claude-haiku-4-5, at about the same "
            "cost (Anthropic): the nearest in price that handles tools well"
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

# A line about how the bot works (a key, a model, a dollar limit, an admin, the settings page), and
# the one said instead where a kid reads (audience.plain). Grown-ups who can mend it are told the
# cause another way (alerts.py).
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
    "lookups_off": "lookups_wait",
}

FOLDABLE = frozenset(
    {
        "reminder",
        "reminder_late",
        "nudge",
        "follow_up",
        "plan_rain",
        "plan_rain_today",
        "plan_closed",
        "plan_closed_today",
        "lookup_done",
    }
)
ACTIVE = timedelta(minutes=5)
HOLD = timedelta(minutes=2)
IN_TURN = timedelta(minutes=10)


Line = str | Sequence[str]


def wording(persona: personas.Persona) -> dict[str, list[str]]:
    return {name: _wordings_of(persona, name) for name in EVENTS}


def wordings(line: Line) -> list[str]:
    """A line's wordings: a string is one, a list is several, blanks left out."""
    several = [line] if isinstance(line, str) else list(line)
    return [words.strip() for words in several if words.strip()]


def boxed(line: Line) -> str:
    """A line as its Personality-page box shows it, one wording to a row."""
    return line if isinstance(line, str) else "\n".join(wordings(line))


def usable(event: str) -> tuple[str, ...]:
    return HERS + EVENTS[event].fields


def say(settings: Any, event: str, *, seed: Any = None, plain: bool = False, **facts: Any) -> str:
    """The words for one event: one wording of the line in force, filled in.

    The wording is chosen from the event and the seed (a message's id), or with no seed the
    facts, so the same inputs say the same words. One that cannot be filled in falls back to the
    plain line. {name} is always hers. `plain` is for a chat a kid reads (audience.plain): a line
    about the workings says its `PLAIN` one.
    """
    if plain:
        event = PLAIN.get(event, event)
    persona = personas.active(settings)
    said = _wordings_of(persona, event)
    return _filled(event, said[_turn(event, seed, facts) % len(said)], persona.name, facts)


def reads_as(settings: Any, event: str) -> list[str]:
    """Each wording of the line in force filled in with the event's example facts, for the
    Personality page.
    """
    persona = personas.active(settings)
    example = EVENTS[event].example
    return [_filled(event, one, persona.name, example) for one in _wordings_of(persona, event)]


def _wordings_of(persona: personas.Persona, event: str) -> list[str]:
    return wordings(persona.lines.get(event, "")) or [EVENTS[event].plain]


def _turn(event: str, seed: Any, facts: Mapping[str, Any]) -> int:
    """The same number wherever the same event is said with the same seed (or facts). CRC-32,
    because hash() is salted per process.
    """
    basis = [str(seed)] if seed is not None else [f"{key}={facts[key]}" for key in sorted(facts)]
    return zlib.crc32("\n".join([event, *basis]).encode("utf-8"))


def _filled(event: str, words: str, name: str, facts: Mapping[str, Any]) -> str:
    known = {**facts, "name": name}
    values = {wanted: known.get(wanted, "") for wanted in usable(event)}
    try:
        return words.format(**values).strip()
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        log.warning("the %s line could not be used; saying it plainly", event)
        return EVENTS[event].plain.format(**values).strip()


def problems(written: Mapping[str, Line]) -> dict[str, str]:
    """What is wrong with lines the family wrote: an unknown event, or a wording with a {…} it
    cannot fill in.
    """
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


@dataclass
class Held:
    message_id: int
    chat: tuple[str, str]  # (channel, chat_id)
    text: str  # the written line, sent if the conversation does not carry it
    mention: str  # a word the model's reply must contain to count as having said it
    until: datetime


class Holds:
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
        with self._lock:
            taken = [h for h in self._held.values() if h.chat == chat and h.until > now]
            for held in taken:
                held.until = now + IN_TURN
            return taken

    def done(self, taken: list[Held]) -> None:
        with self._lock:
            for held in taken:
                self._held.pop(held.message_id, None)

    def let_go(self, taken: list[Held], now: datetime) -> None:
        with self._lock:
            for held in taken:
                if held.message_id in self._held:
                    self._held[held.message_id].until = now

    def due(self, now: datetime) -> list[int]:
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
    """Send a stored proactive message, or hold it for the conversation under way. True when it went
    or was held. Anything not `FOLDABLE`, or in a chat nobody is talking in, goes at once.
    """
    from familydb.delivery import deliver
    from familydb.store.db import transaction

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
    from familydb.delivery import deliver

    return sum(deliver(app, message_id) for message_id in app.held.due(app.clock.now()))


def _talking(conn: sqlite3.Connection, channel: str, chat_id: str, now: datetime) -> bool:
    if messages.claimed_in_chat(conn, chat_id, now=utc_iso(now)):
        return True
    last = messages.last_inbound_at(conn, channel, chat_id)
    return last is not None and now - datetime.fromisoformat(last) <= ACTIVE
