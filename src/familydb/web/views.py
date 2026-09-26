"""Turning stored records into what the templates show. Pure functions, no database, no Flask.

The wording here is for people reading a page. The model's view of an idea lives in
`agent/render.py` and must not change, because it sits in the cached prompt prefix.
"""

from __future__ import annotations

import calendar as months
import difflib
import json
import math
from datetime import UTC, date, datetime
from itertools import islice, pairwise
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from familydb.agent.providers import catalog, prices
from familydb.memory import words
from familydb.store.ideas import Idea
from familydb.store.members import Member
from familydb.store.memories import Memory
from familydb.store.messages import VOICE_PREFIX, Message, as_said
from familydb.store.outcomes import Outcome
from familydb.store.places import Place
from familydb.store.plans import Plan
from familydb.store.tasks import Task
from familydb.suggest.shortlist import fmt_minutes
from familydb.tools.places import DAYS, checked_days_ago, format_ranges, is_stale, open_on
from familydb.tools.urls import clean_url
from familydb.web.agenda import Entry

DAY_NAMES = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}
SETTINGS = {"indoor": "indoor", "outdoor": "outdoor", "either": "indoor or outdoor"}
WEATHER = {"dry": "needs a dry day", "warm": "needs a warm day", "snow": "needs snow"}
DETAILS = {
    "pending": "details not looked up yet",
    "done": "details filled in",
    "failed": "details could not be found",
    "skipped": "not one place to look up",
}
# The last line of every page. The product's name, not the page's title, which the family may
# change: the copyright is in the software, not in what they call it.
FOOTER = "FamilyDB © 2026 by Andrew Tate. Version v{version}. All rights reserved."
# Each role in the page's words, for the Family page and setup. What each may do is decided in
# familydb/roles.py; this is only how the page says it.
ROLE_WORDS = {
    "admin": "looks after it: the settings, setup, and who is on the family list. There is "
    "always at least one.",
    "parent": "uses all the rest: chat, ideas, plans and things to do.",
    "kid": "is in the plans; for now, with a password, may do whatever a parent may.",
}
# What somebody is told when their role may not go somewhere, by the permission it needs. The
# conversation is hers, so it goes by her name: {name} is the persona in force.
REFUSALS = {
    "manage": (
        "For an admin",
        "Settings, setting up and the family list are changed by an admin. Ask one if "
        "something here needs to change.",
    ),
    "chat": ("Not yet", "Talking to {name} here is not part of your role yet. Ask an admin."),
    "change": (
        "Not yet",
        "Changing ideas, plans and things to do is not part of your role yet. Ask an admin.",
    ),
}
MAP_URL = "https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
MAP_SEARCH = "https://www.openstreetmap.org/search?query={query}"


def duration_text(idea: Idea) -> str | None:
    if idea.duration_min and idea.duration_max and idea.duration_max != idea.duration_min:
        return f"{fmt_minutes(idea.duration_min)} to {fmt_minutes(idea.duration_max)}"
    span = idea.duration_min or idea.duration_max
    return f"about {fmt_minutes(span)}" if span else None


def cost_text(level: int | None) -> str | None:
    if level is None:
        return None
    return "free" if level == 0 else "$" * level


def participants_text(idea: Idea) -> str:
    return ", ".join(idea.participants) if idea.participants else "anyone"


def on_text(idea: Idea) -> str | None:
    """When a dated idea is on, in the page's words: "Wed 18 Nov 2026, 20:00", "Thu 1 Oct to
    Sat 31 Oct 2026", "from Thu 1 Oct 2026". None for an idea tied to no date."""
    first, last = idea.first_day, idea.last_day
    if first is None:
        return None
    time = f", {idea.happens_from[11:16]}" if idea.happens_from and "T" in idea.happens_from else ""
    if last is None:
        return f"from {first:%a} {first.day} {first:%b %Y}{time}"
    if last == first:
        return f"{first:%a} {first.day} {first:%b %Y}{time}"
    year = "" if first.year == last.year else f" {first.year}"
    return f"{first:%a} {first.day} {first:%b}{year}{time} to {last:%a} {last.day} {last:%b %Y}"


def rating_text(idea: Idea) -> str | None:
    if not idea.times_done:
        return None
    times = "once" if idea.times_done == 1 else f"{idea.times_done} times"
    if idea.avg_rating is None:
        return f"done {times}"
    return f"done {times}, rated {idea.avg_rating:g}/10"


def kind_text(kind: str) -> str:
    """`day_trip` is how it is stored and how the model says it; nobody wants to read it."""
    return kind.replace("_", " ")


def details_text(idea: Idea) -> str:
    return DETAILS.get(idea.enrichment, idea.enrichment)


def local_day(value: str, tz: ZoneInfo) -> str:
    """A stored UTC instant as the date it was in the family's timezone."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:10]
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(tz).date().isoformat()


def idea_row(idea: Idea, tz: ZoneInfo) -> dict[str, Any]:
    """One line in a list of ideas."""
    return {
        "id": idea.id,
        "title": idea.title,
        "added": local_day(idea.created_at, tz),
        # Links reach the page from chat and from pages the lookup worker read. Anything that is
        # not an ordinary web address is dropped here rather than put in an href.
        "url": clean_url(idea.url),
        "kind": kind_text(idea.kind),
        "status": idea.status,
        "where": idea.location_name,
        "on": on_text(idea),
        "who": participants_text(idea),
        "tags": idea.tags,
        "duration": duration_text(idea),
        "cost": cost_text(idea.cost_level),
        "rating": rating_text(idea),
        "details": details_text(idea),
        "pending": idea.enrichment == "pending",
    }


# Each kind of memory in the page's words, in the order the add form offers them.
MEMORY_KINDS = {
    "food": "food and drink",
    "activities": "things to do",
    "places": "places",
    "health": "health and needs",
    "routine": "routines",
    "other": "anything else",
}
# How much of the message a memory came from the page shows.
SOURCE_CHARS = 140


def excerpt(text: str, fact: str, room: int = SOURCE_CHARS) -> str:
    """The part of a message a memory came from: around the first of its words found in it, so
    a long voice note shows the line that mattered rather than how it began."""
    text = " ".join(text.split())
    if len(text) <= room:
        return text
    lowered = text.casefold()
    found = [lowered.find(word) for word in words(fact)]
    at = min((index for index in found if index >= 0), default=0)
    start = max(0, min(at - room // 3, len(text) - room))
    piece = text[start : start + room]
    if start > 0 and " " in piece:
        piece = "…" + piece.split(" ", 1)[1]
    if start + room < len(text) and " " in piece:
        piece = piece.rsplit(" ", 1)[0] + "…"
    return piece


def memory_row(memory: Memory, today: date, tz: ZoneInfo) -> dict[str, Any]:
    """One memory as the page shows it, with where it came from in the family's own words."""
    when = day_text(local_day(memory.created_at, tz))
    who = memory.said_by_name
    if memory.source_message_id is None:
        source = f"Added on this page{f' by {who}' if who else ''}, {when}"
        said = None
    else:
        text = as_said(memory.source_text or "")
        voiced = text.startswith(VOICE_PREFIX)
        source = f"{who or 'Somebody'}, {when}{', in a voice note' if voiced else ''}"
        said = excerpt(text.removeprefix(VOICE_PREFIX), memory.fact) or None
    return {
        "id": memory.id,
        "fact": memory.fact,
        "about": memory.about_name or "The family",
        "kind": MEMORY_KINDS.get(memory.category, memory.category),
        "firm": memory.firm,
        "guess": memory.inferred,
        "until": day_text(memory.until) if memory.until else None,
        "ended": bool(memory.until and memory.until < today.isoformat()),
        "source": source,
        "said": said,
        "gone": (
            f"forgotten {day_text(local_day(memory.forgotten_at, tz))}"
            + (f" by {memory.forgotten_by_name}" if memory.forgotten_by_name else "")
            if memory.forgotten_at
            else None
        ),
    }


def memory_page(
    memories: list[Memory], people: list[Member], today: date, tz: ZoneInfo
) -> dict[str, Any]:
    """What the page lists: what is remembered, by whom it is about (the family first, then each
    person in the family's order), and what was forgotten. Replaced ones are history."""
    kept = [m for m in memories if m.status == "active"]
    order = [None, *(person.id for person in people)]
    names = {person.id: person.display_name for person in people}
    groups = []
    for member_id in order:
        rows = [memory_row(m, today, tz) for m in kept if m.member_id == member_id]
        if rows:
            groups.append(
                {
                    "who": names.get(member_id, "The family"),
                    "family": member_id is None,
                    "rows": rows,
                }
            )
    strays = [m for m in kept if m.member_id is not None and m.member_id not in names]
    if strays:  # about somebody since switched off the family list
        groups.append(
            {"who": "Others", "family": False, "rows": [memory_row(m, today, tz) for m in strays]}
        )
    forgotten = [memory_row(m, today, tz) for m in memories if m.status == "forgotten"]
    return {"groups": groups, "forgotten": forgotten}


def task_brief(task: Task, tz: ZoneInfo, today: date) -> dict[str, Any]:
    """An open task as Home lists it: what, whose, and when it is due, in words."""
    due = None
    late = False
    if task.due_at:
        moment = datetime.fromisoformat(task.due_at.replace("Z", "+00:00")).astimezone(tz)
        late = moment.date() < today
        day = relative_text(moment.date().isoformat(), today)
        due = f"was due {day}" if late else f"due {day}, {moment:%H:%M}"
    return {
        "id": task.id,
        "title": task.title,
        "owner": task.owner,
        "due": due,
        "late": late,
        "window": task.preferred_window or None,
        "reminder": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
        "revision": task.revision,
    }


# Ways to start, under the box on Home and in an empty chat. The first is the question most
# people open the page to ask, put the way the day puts it; the other two start an instruction
# and leave the rest to whoever is typing. Written here, never asked of a model.
WEEKEND_QUESTION = "What should we do this weekend?"
TODAY_QUESTION = "What should we do today?"
STARTERS = ("Remind me to ", "We should try ")


def starters(today: date) -> list[dict[str, str]]:
    """The suggestions under the box: what each puts in it, and how it reads as a link."""
    question = TODAY_QUESTION if today.weekday() >= 5 else WEEKEND_QUESTION
    return [
        {"say": text, "label": text.rstrip() + ("…" if text.endswith(" ") else "")}
        for text in (question, *STARTERS)
    ]


def task_row(task: Task, tz: ZoneInfo) -> dict[str, Any]:
    """One task on the tasks page, with its times as the family's clock shows them."""
    return {
        "task": task,
        "due_input": (
            datetime.fromisoformat(task.due_at).astimezone(tz).strftime("%Y-%m-%dT%H:%M")
            if task.due_at
            else ""
        ),
        "reminder_time": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
    }


def hours_rows(place: Place | None) -> list[dict[str, str]]:
    """Monday to Sunday, saying plainly which days are closed and which are unknown."""
    hours = (place.hours if place else None) or {}
    rows = []
    for key in DAYS:
        ranges = hours.get(key)
        if ranges is None:
            text = "not known"
        elif not ranges:
            text = "closed"
        else:
            text = format_ranges(ranges) or "closed"
        rows.append({"day": DAY_NAMES[key], "hours": text})
    return rows


def travel_text(place: Place | None) -> str | None:
    if place is None or place.travel_minutes is None:
        return None
    distance = f", {place.travel_km:g} km" if place.travel_km is not None else ""
    return f"about {place.travel_minutes} min away{distance} (estimate)"


def map_url(place: Place | None) -> str | None:
    if place is None:
        return None
    if place.lat is not None and place.lon is not None:
        return MAP_URL.format(lat=place.lat, lon=place.lon)
    if place.address:
        return MAP_SEARCH.format(query=quote(place.address))
    return None


def freshness_text(place: Place | None, now: datetime, stale_days: int) -> str | None:
    if place is None:
        return None
    days = checked_days_ago(place, now)
    if days is None:
        return "never checked"
    when = "checked today" if days == 0 else f"checked {days} day{'s' if days != 1 else ''} ago"
    return f"{when}, may be out of date" if is_stale(place, now, stale_days) else when


def place_panel(place: Place | None, now: datetime, stale_days: int) -> dict[str, Any] | None:
    if place is None:
        return None
    return {
        "name": place.name,
        "summary": place.summary,
        "address": place.address,
        "phone": place.phone,
        "website": clean_url(place.website),
        "booking_url": clean_url(place.booking_url),
        "price_note": place.price_note,
        "travel": travel_text(place),
        "map_url": map_url(place),
        "hours": hours_rows(place),
        "has_hours": bool(place.hours),
        "sources": [url for url in (clean_url(s) for s in place.source_urls) if url],
        "freshness": freshness_text(place, now, stale_days),
        "stale": is_stale(place, now, stale_days),
    }


TODAY_HOURS = {"open": "open today {ranges}", "closed": "closed today", "unknown": None}


def restaurant_card(
    idea: Idea, place: Place | None, today: date, now: datetime, stale_days: int
) -> dict[str, Any]:
    """A restaurant as the page shows it: where, what it costs, and where to read more."""
    state, ranges = open_on(place, today)
    hours_today = TODAY_HOURS[state]
    if hours_today:
        hours_today = hours_today.format(ranges=format_ranges(ranges) or "").strip()
    return {
        "id": idea.id,
        "title": idea.title,
        "summary": (place.summary if place else None) or idea.description,
        "where": (place.address if place else None) or idea.location_name,
        "who": participants_text(idea),
        "cost": cost_text(idea.cost_level) or (place.price_note if place else None),
        "tags": idea.tags,
        "rating": rating_text(idea),
        "today": hours_today,
        "travel": travel_text(place),
        "website": clean_url(place.website if place else idea.url),
        "booking_url": clean_url(place.booking_url) if place else None,
        "map_url": map_url(place),
        "pending": idea.enrichment == "pending",
        "details": details_text(idea),
        "stale": is_stale(place, now, stale_days) if place else False,
    }


def day_text(value: str) -> str:
    """A stored date or datetime as 'Saturday 26 September', with the time when there is one."""
    stamp = value.strip()
    try:
        if len(stamp) <= 10:
            day = date.fromisoformat(stamp)
            return f"{day:%A} {day.day} {day:%B}"
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        return stamp
    return f"{moment:%A} {moment.day} {moment:%B}, {moment:%H:%M}"


def date_chip(value: str) -> dict[str, Any] | None:
    """The day something starts in three parts, for the tear-off date beside it: Sat, 26, Sep."""
    try:
        day = date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    return {"weekday": f"{day:%a}", "day": day.day, "month": f"{day:%b}"}


def relative_text(value: str, today: date) -> str | None:
    """'today', 'tomorrow', 'in 3 days', '2 weeks ago'. None when the date will not parse."""
    try:
        when = date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    days = (when - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    ahead = days > 0
    count = abs(days)
    unit = f"{count} days" if count < 14 else f"{count // 7} weeks"
    return f"in {unit}" if ahead else f"{unit} ago"


def plan_row(plan: Plan, today: date) -> dict[str, Any]:
    return {
        "id": plan.id,
        "idea_id": plan.idea_id,
        "title": plan.title,
        "when": day_text(plan.start) if not plan.all_day else day_text(plan.start[:10]),
        "relative": relative_text(plan.start, today),
        "chip": date_chip(plan.start),
        "all_day": plan.all_day,
        # What a datetime-local box wants, "2026-09-26T18:30": the stored start without its
        # offset — plans are stored in the family's own time, so the wall time is the first
        # sixteen characters — or a morning on the day of an all-day plan. A box handed the
        # offset as well shows nothing at all.
        "start_value": plan.start[:16] if len(plan.start) > 10 else f"{plan.start[:10]}T09:00",
        "location": plan.location,
        "notes": plan.notes,
        "status": plan.status,
    }


def entry_row(entry: Entry, today: date) -> dict[str, Any]:
    """One line of the calendar: what, when, and whether the bot can move it."""
    days = entry.days()
    when = day_text(entry.start[:10] if entry.all_day else entry.start)
    if entry.all_day and len(days) > 1:
        first, last = days[0], days[-1]
        if (first.year, first.month) == (last.year, last.month):
            # "Saturday 3 to Sunday 4 October": the month once, where it cannot be mistaken.
            when = f"{first:%A} {first.day} to {day_text(last.isoformat())}"
        else:
            when = f"{day_text(first.isoformat())} to {day_text(last.isoformat())}"
    return {
        "id": entry.plan_id,
        "idea_id": entry.idea_id,
        "title": entry.title,
        "when": when,
        "time": None if entry.all_day else entry.start[11:16],
        "relative": "now" if days[0] < today <= days[-1] else relative_text(entry.start, today),
        "chip": date_chip(entry.start),
        "on_today": days[0] <= today <= days[-1],
        "all_day": entry.all_day,
        "location": entry.location,
        "notes": entry.notes,
        "status": entry.status,
        # Made somewhere other than here, so this page can show it but not move it.
        "from_google": entry.plan_id is None,
        "start_value": entry.start[:16] if not entry.all_day else f"{entry.start[:10]}T09:00",
    }


def month_weeks(entries: list[Entry], first: date, today: date) -> list[list[dict[str, Any]]]:
    """A month as weeks of days, Monday first, each day with what is on it.

    `first` is any day in the month. The weeks run from the Monday on or before the 1st to the
    Sunday on or after the last day, so the grid is always whole weeks.
    """
    grid = months.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    by_day: dict[date, list[dict[str, Any]]] = {}
    for entry in entries:
        row = entry_row(entry, today)
        for day in entry.days():
            by_day.setdefault(day, []).append(row)
    return [
        [
            {
                "date": day,
                "day": day.day,
                "name": f"{day:%A} {day.day} {day:%B}",
                "current": day.month == first.month,
                "today": day == today,
                "entries": by_day.get(day, []),
            }
            for day in week
        ]
        for week in grid
    ]


# The home page's radar: a dial 200 units across, its range rings a week, two weeks and four weeks
# out. Each pair is (days away, distance from the middle).
RADAR_RINGS = ((0, 12.0), (7, 33.0), (14, 66.0), (28, 92.0))
# Blips sit on one of twelve bearings, one every 30 degrees: the page times each blip's flare to
# the moment the sweep passes that bearing (the `.b0` to `.b11` rules in style.css).
RADAR_BEARINGS = 12
RADAR_START = 210  # degrees clockwise from twelve o'clock, where the first plan goes


def radar_distance(days: int) -> float:
    """How far from the middle a plan `days` away shows: along the rings, never past the last."""
    days = max(0, days)
    for (near_days, near), (far_days, far) in pairwise(RADAR_RINGS):
        if days <= far_days:
            return near + (far - near) * (days - near_days) / (far_days - near_days)
    return RADAR_RINGS[-1][1]


def radar_blips(entries: list[Entry], today: date) -> list[dict[str, Any]]:
    """Where each coming plan shows on the home page's radar.

    The nearer the day, the nearer the middle. Plans are spread round the dial by the golden
    angle so none sits on another, each on one of the twelve bearings, and the first, the next
    thing on, is marked so the page can make it the brightest.
    """
    blips: list[dict[str, Any]] = []
    taken: set[int] = set()
    for index, entry in enumerate(entries):
        bearing = round((RADAR_START + index * 137.5) % 360 / 30) % RADAR_BEARINGS
        while bearing in taken and len(taken) < RADAR_BEARINGS:
            bearing = (bearing + 1) % RADAR_BEARINGS
        taken.add(bearing)
        distance = radar_distance((entry.days()[0] - today).days)
        angle = math.radians(bearing * 360 / RADAR_BEARINGS)
        blips.append(
            {
                "x": round(100 + distance * math.sin(angle), 1),
                "y": round(100 - distance * math.cos(angle), 1),
                "bearing": bearing,
                "next": index == 0,
            }
        )
    return blips


AGENDA_NOTES = {
    "google": "From Google Calendar, including anything added there directly.",
    "saved": "Google Calendar is not connected, so these are the plans the bot made.",
    "unavailable": (
        "Google Calendar did not answer, so these are the plans as the bot last saw them. "
        "Times may have moved since."
    ),
}


def outcome_row(outcome: Outcome) -> dict[str, Any]:
    repeat = None
    if outcome.would_repeat is not None:
        repeat = "would go again" if outcome.would_repeat else "would not go again"
    return {
        "when": day_text(outcome.happened_on),
        "rating": f"{outcome.rating}/10" if outcome.rating is not None else None,
        "repeat": repeat,
        "notes": outcome.notes,
    }


def chat_line(
    message: Message,
    names: dict[int, str],
    tz: ZoneInfo,
    *,
    did: list[str],
    waiting: bool,
    assistant: str,
) -> dict[str, Any]:
    """One message in the chat: who said it, when, what the turn ran, and what went wrong.

    `did` is the turn's tool calls, which the log stores against the question rather than the
    answer. They belong under the answer: "used suggest" beneath somebody's own message reads
    as though they had run it. `waiting` is for a message nothing has replied to yet, which is
    a fact about the thread rather than about the row, so the caller works it out. `assistant`
    is what the persona in force is called: every line she sends, a reply, a reminder or a
    plain "Done.", is hers alike.
    """
    from_bot = message.direction == "out"
    trouble = None
    if not from_bot:
        if message.status == "failed":
            trouble = "this one did not go through"
        elif waiting:
            trouble = "waiting for an answer"
    return {
        "id": message.id,
        "who": assistant if from_bot else names.get(message.member_id or -1, "someone"),
        "from_bot": from_bot,
        "text": message.text,
        "when": local_moment(message.received_at, tz),
        "trouble": trouble,
        "did": did if from_bot else [],
    }


def handed_line(who: str, text: str, now: datetime, tz: ZoneInfo) -> dict[str, Any]:
    """A message just sent from the page that the log does not hold yet, drawn as it will be."""
    return {
        "id": None,
        "who": who,
        "from_bot": False,
        "text": text,
        "when": local_moment(now.astimezone(UTC).isoformat(), tz),
        "trouble": "waiting for an answer",
        "did": [],
    }


def tools_used(actions: Any) -> list[str]:
    """The tools a turn ran, in order, named once each. Failures included: those are the ones
    worth seeing."""
    seen: list[str] = []
    for action in actions or []:
        name = action.get("tool") if isinstance(action, dict) else None
        if name and name not in seen:
            seen.append(name)
    return seen


def local_moment(value: str, tz: ZoneInfo) -> str:
    """A stored UTC instant as the day and time it was where the family lives."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    here = moment.astimezone(tz)
    return f"{here.day} {here:%b}, {here:%H:%M}"


def setting_text(value: str | None) -> str:
    """A stored JSON value as the page shows it. Nothing stored reads as the default."""
    if value is None:
        return "—"
    try:
        loaded = json.loads(value)
    except ValueError:
        return value
    if loaded is None:
        return "default"
    if isinstance(loaded, bool):
        return "yes" if loaded else "no"
    return str(loaded)


def price_text(price: prices.Price | None) -> str | None:
    """What a model costs, in US dollars per million tokens read and written."""
    if price is None:
        return None
    return f"${price.input:.2f} in, ${price.output:.2f} out"


def model_offer(provider: str, name: str) -> str:
    """A model name as a box offers it: what it is called, where it stands in its company's
    lineup, and what it costs. Only the price, for one the lineup does not list."""
    known = catalog.known(provider, name)
    said = f"{known.label}, {known.level}" if known else ""
    cost = price_text(prices.price(provider, name))
    return " · ".join(part for part in (said, cost) if part)


def level_choice(level: str, provider: str, name: str) -> str:
    """A level as the settings page offers it: the model it means for the company answering."""
    known = catalog.known(provider, name)
    cost = price_text(prices.price(provider, name))
    said = f"{level}: {known.label if known else name}"
    return f"{said} ({cost})" if cost else said


def model_text(provider: str, name: str, level: str) -> str:
    """Which model answers, as the status page and setup say it: its name, and its level when
    that is not the everyday one, or when the model does not think before answering."""
    known = catalog.known(provider, name)
    notes = [] if level == catalog.EVERYDAY else [level]
    if known is not None and not known.thinks:
        notes.append("without thinking first")
    return f"{name} ({', '.join(notes)})" if notes else name


LONG_SETTINGS = frozenset({"persona_text", "persona_notes", "about_family", "voice_lines"})
# How many unchanged lines are shown either side of a change. A persona's character is written in
# paragraphs, one to a line with a blank line between them, so with one either side the only
# context would be the blank.
CHANGE_CONTEXT = 2


def line_changes(before: str, now: str) -> list[dict[str, str]]:
    """What changed from one text to the other, line by line, as a unified diff shows it.

    Each line keeps the mark the diff gives it (+ for one that is new, - for one that has gone, a
    space for one either side that has not changed) and a kind the stylesheet colours, so a
    change never rests on colour alone. The diff's headers and line numbers say nothing to a
    family, so they are left out and its parts are parted by an ellipsis."""
    shown: list[dict[str, str]] = []
    diff = difflib.unified_diff(
        before.splitlines(), now.splitlines(), lineterm="", n=CHANGE_CONTEXT
    )
    for line in islice(diff, 2, None):  # past the two headers naming what was compared
        if line.startswith("@@"):
            if shown:
                shown.append({"kind": "same", "text": "…"})
            continue
        shown.append({"kind": {"+": "added", "-": "removed"}.get(line[:1], "same"), "text": line})
    return shown


def change_row(line: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    """One line of the settings history. A key's value is never in there to show."""
    return {
        "when": local_moment(line["changed_at"], tz),
        "key": line["key"],
        "secret": bool(line["secret"]),
        # A description is too long to show twice in a list; saying it changed is enough.
        "long": line["key"] in LONG_SETTINGS,
        "old": setting_text(line["old_value"]),
        "new": setting_text(line["new_value"]),
        "who": line.get("changed_by_name"),
        "source": line["source"],
    }


def knock_row(knock: Any, tz: Any) -> dict[str, Any]:
    """Somebody who messaged the bot and is not on the family list, as the Family page shows it."""
    words = (knock.name or "").split()
    name = " ".join(word for word in words if not word.startswith("@"))
    handle = next((word for word in words if word.startswith("@")), "")
    group = (knock.chat_id or "").startswith("-")
    return {
        "telegram_id": knock.channel_user_id,
        "name": name,
        "handle": handle,
        "when": local_moment(knock.last_at, tz),
        "times": knock.times,
        "where": "in a group" if group else "in a private chat",
    }


def footer(version: str) -> str:
    """The copyright and version line at the foot of every page."""
    return FOOTER.format(version=version)
