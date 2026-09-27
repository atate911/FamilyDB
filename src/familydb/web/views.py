"""Turning stored records into what the templates show. Pure functions, no database, no Flask.

The wording here is for people reading a page. The model's view of an idea lives in
`agent/render.py` and must not change, because it sits in the cached prompt prefix.
"""

from __future__ import annotations

import calendar as months
import difflib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from itertools import islice, pairwise
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from familydb import windows
from familydb.agenda import Entry
from familydb.agent.providers import catalog, prices
from familydb.config import Settings
from familydb.integrations.geocode import estimate_travel
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
    "kid": "is in the plans; with a password, may do whatever a parent may, within the number of "
    "messages a day set under Spending.",
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


# How often a task may come round, as the tasks page offers it: "every:unit" and its words.
REPEATS = (
    ("", "Doesn't repeat"),
    ("1:day", "Every day"),
    ("1:week", "Every week"),
    ("2:week", "Every 2 weeks"),
    ("1:month", "Every month"),
    ("3:month", "Every 3 months"),
    ("6:month", "Every 6 months"),
    ("1:year", "Every year"),
)


def repeat_text(task: Task, tz: ZoneInfo) -> str | None:
    """How often a task comes round, in words: "Every 2 weeks · last done Sun 20 Sep"."""
    if not task.repeats:
        return None
    unit = (
        task.repeat_unit if task.repeat_every == 1 else f"{task.repeat_every} {task.repeat_unit}s"
    )
    words = f"Every {unit}"
    if task.repeat_from == "done":
        words += ", counted from when it is done"
    if task.last_done_at:
        done = datetime.fromisoformat(task.last_done_at).astimezone(tz)
        words += f" · last done {done:%a %d %b}"
    return words


def nudge_words(task: Task, tz: ZoneInfo) -> dict[str, str] | None:
    """Whether an open task kept for a window is brought up by itself (jobs/nudges.py), for the
    tasks page: `on`, "a free Saturday morning", and `last`, when it last was; or `unread` when
    its window is not a day or part of the day that can be read, so the family can say it
    again. None for a task that is not waiting on a window."""
    if task.status != "open" or task.repeats or not task.preferred_window:
        return None
    window = windows.read(task.preferred_window)
    if window is None:
        return {"unread": "yes"}
    said = {"on": window.words("free")}
    if task.nudged_at:
        last = datetime.fromisoformat(task.nudged_at).astimezone(tz)
        said["last"] = f"{last:%a %d %b}"
    return said


def task_row(task: Task, tz: ZoneInfo, *, nudging: bool = False) -> dict[str, Any]:
    """One task on the tasks page, with its times as the family's clock shows them. `nudging`
    is whether tasks kept for a window are being brought up at all (the `task_nudges` setting)."""
    choice = f"{task.repeat_every}:{task.repeat_unit}" if task.repeats else ""
    options = list(REPEATS)
    if choice and choice not in dict(REPEATS):  # set in the chat to something the list lacks
        options.insert(1, (choice, f"Every {task.repeat_every} {task.repeat_unit}s (as it is)"))
    return {
        "task": task,
        "due_input": (
            datetime.fromisoformat(task.due_at).astimezone(tz).strftime("%Y-%m-%dT%H:%M")
            if task.due_at
            else ""
        ),
        "reminder_time": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
        "repeats": repeat_text(task, tz),
        "repeat_choice": choice,
        "repeat_options": options,
        # What the form was drawn with, so saving it changes the repeat only when that did.
        "repeat_was": f"{choice}:{task.repeat_from}" if choice else "",
        "nudge": nudge_words(task, tz) if nudging else None,
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
# the moment the sweep passes that bearing (the `.b1` to `.b11` rules in style.css; bearing 0,
# at twelve o'clock, needs no delay).
RADAR_BEARINGS = 12
RADAR_START = 210  # degrees clockwise from twelve o'clock, where the first plan goes


def radar_distance(away: float, rings: tuple[tuple[int, float], ...] = RADAR_RINGS) -> float:
    """How far from the middle something `away` shows (days for a plan, minutes for a place):
    along the rings, never past the last."""
    away = max(0, away)
    for (near_away, near), (far_away, far) in pairwise(rings):
        if away <= far_away:
            return near + (far - near) * (away - near_away) / (far_away - near_away)
    return rings[-1][1]


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


# The ideas page's radar is a map: home at the middle, north at the top, and each saved place as
# far out as it is by road, its rings a quarter of an hour, three quarters and two hours away.
# Each pair is (minutes away, distance from the middle), as in RADAR_RINGS.
PLACE_RINGS = ((0, 8.0), (15, 33.0), (45, 66.0), (120, 92.0))
PLACE_RING_LABELS = ("15m", "45m", "2h")
COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")
POINTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Which way the second point lies from the first, in degrees clockwise from north."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    east = math.sin(dlmb) * math.cos(phi2)
    north = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
    return math.degrees(math.atan2(east, north)) % 360


def drive_text(minutes: int) -> str:
    """A drive's length as people say it: "25 min", "1 h 35 min", to five minutes past an hour."""
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(5 * round(minutes / 5), 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


@dataclass(frozen=True)
class Away:
    """Where a saved place lies from home: the drive, as the lookups estimate it, and which way."""

    minutes: int
    degrees: float

    @property
    def near(self) -> bool:
        return self.minutes < 5

    @property
    def text(self) -> str:
        """For a card: "about 25 min north-east of home (estimate)"."""
        if self.near:
            return "under 5 min from home (estimate)"
        way = COMPASS[round(self.degrees / 45) % 8]
        return f"about {drive_text(self.minutes)} {way} of home (estimate)"

    @property
    def short(self) -> str:
        """For the green screen beside the radar: "25 min NE"."""
        if self.near:
            return "under 5 min"
        return f"{drive_text(self.minutes)} {POINTS[round(self.degrees / 45) % 8]}"


def away_from_home(place: Place | None, settings: Settings) -> Away | None:
    """How far and which way a place is from home; None unless both are on the map."""
    if place is None or place.lat is None or place.lon is None:
        return None
    if settings.home_lat is None or settings.home_lon is None:
        return None
    estimate = estimate_travel(settings, place.lat, place.lon)
    if estimate is None:
        return None
    return Away(estimate[0], bearing(settings.home_lat, settings.home_lon, place.lat, place.lon))


def places_radar(placed: list[tuple[Idea, Away]]) -> dict[str, Any] | None:
    """The ideas page's radar and the words beside it; None when nothing listed is on the map.

    Each place shows where it is from home, the further by road the further out, never past
    the last ring. It flares as the sweep passes its bearing, the nearest one brightest and
    pinging, since the words beside the radar name it.
    """
    if not placed:
        return None
    ordered = sorted(placed, key=lambda pair: (pair[1].minutes, pair[0].id))
    blips = []
    for index, (_, away) in enumerate(ordered):
        distance = radar_distance(away.minutes, PLACE_RINGS)
        angle = math.radians(away.degrees)
        blips.append(
            {
                "x": round(100 + distance * math.sin(angle), 1),
                "y": round(100 - distance * math.cos(angle), 1),
                "bearing": round(away.degrees / 30) % RADAR_BEARINGS,
                "next": index == 0,
            }
        )

    def named(pair: tuple[Idea, Away]) -> dict[str, Any]:
        idea, away = pair
        return {"id": idea.id, "title": idea.title, "away": away.short}

    return {
        "blips": blips,
        "rings": PLACE_RING_LABELS,
        "count": len(ordered),
        "nearest": named(ordered[0]),
        "furthest": named(ordered[-1]) if len(ordered) > 1 else None,
    }


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


# What needs an admin, by kind (familydb/alerts.py), as the status page heads it.
ALERT_TITLES = {
    "credit": "{company} is out of credit",
    "key": "{company} refused its key",
    "limit": "The day's spending limit was used up",
    "calendar": "Google Calendar stopped letting the bot in",
    "model": "A model in use is going, or has gone",
    "price": "The price of a model in use changed",
    "prices": "The price lists need a look",
    "new": "New models to choose from",
    "shift": "What the calls cost or do moved",
}
# Kinds whose subject is not a company: what the notice says is the detail, shown with it.
SAID_IN_DETAIL = frozenset({"model", "price", "prices", "new", "shift"})
COMPANY_WORDS = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google Gemini"}


def alert_row(alert: Any, tz: ZoneInfo, *, telling: bool, admins: int) -> dict[str, Any]:
    """One trouble as a light on the status page: what it is, since when, and who was told."""
    title = ALERT_TITLES.get(alert.kind, alert.kind).format(
        company=COMPANY_WORDS.get(alert.subject, alert.subject)
    )
    seen = f"since {local_moment(alert.first_at, tz)}"
    if alert.times > 1:
        seen += f", {alert.times} times, last {local_moment(alert.last_at, tz)}"
    if alert.told_at:
        told = f"admins told on Telegram {local_moment(alert.told_at, tz)}"
    elif not telling:
        told = "telling admins is switched off (Settings, Messages)"
    elif not admins:
        told = "no admin has a Telegram id to be told on"
    else:
        told = "admins are told on Telegram within a minute"
    detail = f"{seen}; {told}."
    if alert.kind in SAID_IN_DETAIL and alert.detail:
        detail = f"{alert.detail}. {detail[:1].upper()}{detail[1:]}"
    return {"label": title, "detail": detail, "on": False}


SOURCE_WORDS = {
    "litellm": "LiteLLM's price list",
    "openrouter": "OpenRouter's price list",
}
CHANGE_WORDS = {
    "new": "new, {after}",
    "gone": "no longer offered to the key",
    "back": "offered to the key again",
    "price": "{before} → {after} a million tokens",
    "retiring": "goes on {after}",
}


def source_row(source: Any, tz: ZoneInfo) -> dict[str, Any]:
    """Where the daily check of models and prices reads, as a light: when, and how it went."""
    company = COMPANY_WORDS.get(source.source)
    label = SOURCE_WORDS.get(source.source) or f"{company or source.source}'s list for the key"
    when = local_moment(source.checked_at, tz)
    if source.ok:
        return {"label": label, "detail": f"Read {when}: {source.note}.", "on": True}
    running = f", {source.failures} checks running" if source.failures > 1 else ""
    detail = f"Could not be read {when}{running}: {source.note}."
    return {"label": label, "detail": detail, "on": False}


def model_change_row(change: Any, tz: ZoneInfo) -> dict[str, str]:
    """One thing the daily check found changed, for the status page's table."""
    what = CHANGE_WORDS.get(change.what, change.what)
    return {
        "when": local_moment(change.at, tz),
        "company": COMPANY_WORDS.get(change.provider, change.provider),
        "model": change.model,
        "what": what.format(before=change.before or "?", after=change.after or "?"),
    }


# Each kind of message she sends of her own accord, as the Messages page lists them: the group
# on that page where it is switched (none for reminders, which somebody asked for), what sending
# it costs, and which of her lines (voice.EVENTS, or "digest") are its messages.
AUTOMATIC = (
    ("weekend", "weekend", "Weekend ideas", "one model call a week", ("digest",)),
    ("reminders", "", "Reminders", "free", ("reminder", "reminder_late")),
    ("follow_ups", "others", "How did it go?", "free", ("follow_up",)),
    (
        "checks",
        "others",
        "Tomorrow's plans, checked",
        "free",
        ("plan_rain", "plan_closed", "plan_backup"),
    ),
    ("nudges", "others", "A task brought up", "free", ("nudge",)),
    (
        "lookups",
        "others",
        "What a lookup found",
        "free to send; each lookup is a small model call",
        ("lookup_done", "lookups_done"),
    ),
    (
        "alerts",
        "admins",
        "What needs fixing, to admins",
        "free",
        ("alert_credit", "alert_key", "alert_limit", "alert_calendar"),
    ),
)
AUTOMATIC_BY_EVENT = {event: title for _, _, title, _, events in AUTOMATIC for event in events}


def chat_words(conn_chat: str, member_name: str | None) -> str:
    """Which chat a message went to, as the page says it."""
    if conn_chat == "web":
        return "the chat on this page"
    if conn_chat.startswith("-"):
        return "a Telegram group"
    return f"Telegram, {member_name}" if member_name else "Telegram"


# A tool's input or answer is cut here on the history page; the log keeps it whole.
MAX_SHOWN = 4000
ASKED_WORDS = 90


def pretty_json(text: str | None) -> str:
    """A tool's input or answer, laid out to be read."""
    if not text:
        return ""
    try:
        shown = json.dumps(json.loads(text), indent=2, ensure_ascii=False, sort_keys=True)
    except ValueError:
        shown = text
    return shown if len(shown) <= MAX_SHOWN else shown[:MAX_SHOWN] + "\n…"


def asked_line(text: str, who: str) -> str:
    """A message as a line of the status page's history: who, and the start of what they said."""
    words = " ".join(as_said(text).split())
    if len(words) > ASKED_WORDS:
        words = words[: ASKED_WORDS - 1].rstrip() + "…"
    return f"{who}: {words}"


def found_by_lookup(tool: dict[str, Any]) -> dict[str, Any] | None:
    """What a lookup saved (save_place) or why it gave up (skip_place), as the page shows it."""
    try:
        given = json.loads(tool.get("input") or "{}")
    except ValueError:
        return None
    if tool.get("tool_name") == "skip_place":
        return {"idea_id": given.get("idea_id"), "skipped": given.get("reason") or "no reason"}
    if tool.get("tool_name") != "save_place":
        return None
    hours = [
        f"{row.get('day')} {row.get('open')}-{row.get('close')}"
        for row in given.get("hours") or []
        if isinstance(row, dict)
    ]
    return {
        "idea_id": given.get("idea_id"),
        "name": given.get("name"),
        "summary": given.get("summary"),
        "address": given.get("address"),
        "website": clean_url(given.get("website")),
        "booking_url": clean_url(given.get("booking_url")),
        "phone": given.get("phone"),
        "hours": hours,
        "closed": given.get("closed_days") or [],
        "price_note": given.get("price_note"),
        "sources": [url for url in (clean_url(s) for s in given.get("source_urls") or []) if url],
        "saved": not tool.get("is_error"),
    }


def lookups_when(settings: Any) -> str:
    """When ideas waiting are looked up, as the page says it."""
    if settings.lookups_when == "asap":
        return "as soon as each is added"
    return f"together at {settings.lookup_hour:02d}:00 each evening"


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
    """What a model costs, in US dollars per million tokens read and written, or for a minute of
    recording when that is how it is billed (a hearing model, prices.HEARING)."""
    if price is None:
        return None
    if price.minute and not (price.input or price.output):
        return f"${price.minute:.3f} a minute"
    return f"${price.input:.2f} in, ${price.output:.2f} out"


def model_offer(provider: str, name: str) -> str:
    """A model name as a box offers it: what it is called, where it stands in its company's
    lineup, what it costs, and whether it is new or going (the daily check's word on it)."""
    known = catalog.known(provider, name)
    said = f"{known.label}, {known.level}" if known else ""
    cost = price_text(prices.price(provider, name))
    return " · ".join(part for part in (said, cost, prices.note(provider, name)) if part)


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


# The regions time zones are named for, as the time zone dropdown heads them, in its order. A zone
# named for no region (UTC) goes last, on its own.
ZONE_REGIONS = {
    "Africa": "Africa",
    "America": "Americas",
    "Antarctica": "Antarctica",
    "Asia": "Asia",
    "Atlantic": "Atlantic",
    "Australia": "Australia",
    "Europe": "Europe",
    "Indian": "Indian Ocean",
    "Pacific": "Pacific",
}
ZONE_OTHERS = "Other"


def utc_offset(zone: str, now: datetime) -> str:
    """How far a zone is from UTC at this moment, daylight saving and all: "UTC-07:00"."""
    offset = now.astimezone(ZoneInfo(zone)).utcoffset() or timedelta(0)
    total = round(offset.total_seconds() / 60)
    hours, minutes = divmod(abs(total), 60)
    return f"UTC{'-' if total < 0 else '+'}{hours:02d}:{minutes:02d}"


def zone_label(zone: str, now: datetime) -> str:
    """A time zone as the dropdown offers it: the place it is named for first, so typing a city
    finds it, then its offset now. "Vancouver · UTC-07:00", "Buenos Aires, Argentina ·
    UTC-03:00", and "UTC" as itself."""
    rest = zone.partition("/")[2]
    if not rest:
        return zone
    place = ", ".join(reversed(rest.replace("_", " ").split("/")))
    return f"{place} · {utc_offset(zone, now)}"


ZoneGroups = tuple[tuple[str, tuple[tuple[str, str], ...]], ...]


def zone_groups(zones: Sequence[str], now: datetime) -> ZoneGroups:
    """Time zones for a dropdown: under the region each is named for, the places in alphabetical
    order, each as (zone, how it reads). Worked out for the hour, since the offsets move only as
    clocks change, and there are nearly five hundred of them to work out."""
    hour = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    return _zone_groups(tuple(zones), hour)


@lru_cache(maxsize=2)
def _zone_groups(zones: tuple[str, ...], hour: datetime) -> ZoneGroups:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for zone in zones:
        region, _, rest = zone.partition("/")
        heading = ZONE_REGIONS.get(region, ZONE_OTHERS) if rest else ZONE_OTHERS
        grouped.setdefault(heading, []).append((zone, zone_label(zone, hour)))
    order = [*ZONE_REGIONS.values(), ZONE_OTHERS]
    return tuple(
        (heading, tuple(sorted(grouped[heading], key=lambda row: row[1].casefold())))
        for heading in order
        if heading in grouped
    )


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
