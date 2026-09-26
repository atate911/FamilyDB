"""Turning stored records into what the templates show. Pure functions, no database, no Flask.

The wording here is for people reading a page. The model's view of an idea lives in
`agent/render.py` and must not change, because it sits in the cached prompt prefix.
"""

from __future__ import annotations

import calendar as months
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from familydb.config import Settings
from familydb.integrations.geocode import estimate_travel
from familydb.store.ideas import Idea
from familydb.store.messages import Message
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
        "who": participants_text(idea),
        "tags": idea.tags,
        "duration": duration_text(idea),
        "cost": cost_text(idea.cost_level),
        "rating": rating_text(idea),
        "details": details_text(idea),
        "pending": idea.enrichment == "pending",
    }


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
    """A stored JSON value as the page shows it. Nothing stored reads as the fallback."""
    if value is None:
        return "—"
    try:
        loaded = json.loads(value)
    except ValueError:
        return value
    if loaded is None:
        return "from the environment"
    if isinstance(loaded, bool):
        return "yes" if loaded else "no"
    return str(loaded)


LONG_SETTINGS = frozenset({"persona_text", "about_family", "voice_lines"})


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
