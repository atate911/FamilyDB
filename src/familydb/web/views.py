"""Turning stored records into what the templates show. Pure functions, no database, no Flask.

The wording here is for people reading a page. The model's view of an idea lives in
`agent/render.py` and must not change, because it sits in the cached prompt prefix.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from familydb.store.ideas import Idea
from familydb.store.messages import Message
from familydb.store.outcomes import Outcome
from familydb.store.places import Place
from familydb.store.plans import Plan
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
        "all_day": plan.all_day,
        # What a datetime-local box wants: the stored start, with a time when there is none,
        # so re-opening the form shows where the plan is now rather than an empty box.
        "start_value": plan.start if len(plan.start) > 10 else f"{plan.start[:10]}T09:00",
        "location": plan.location,
        "notes": plan.notes,
        "status": plan.status,
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
    message: Message, names: dict[int, str], tz: ZoneInfo, *, did: list[str], waiting: bool
) -> dict[str, Any]:
    """One message in the chat: who said it, when, what the turn ran, and what went wrong.

    `did` is the turn's tool calls, which the log stores against the question rather than the
    answer. They belong under the answer: "used suggest" beneath somebody's own message reads
    as though they had run it. `waiting` is for a message nothing has replied to yet, which is
    a fact about the thread rather than about the row, so the caller works it out.
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
        "who": "FamilyDB" if from_bot else names.get(message.member_id or -1, "someone"),
        "from_bot": from_bot,
        "text": message.text,
        "when": local_moment(message.received_at, tz),
        "trouble": trouble,
        "did": did if from_bot else [],
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


def change_row(line: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    """One line of the settings history. A key's value is never in there to show."""
    return {
        "when": local_moment(line["changed_at"], tz),
        "key": line["key"],
        "secret": bool(line["secret"]),
        "old": setting_text(line["old_value"]),
        "new": setting_text(line["new_value"]),
        "who": line.get("changed_by_name"),
        "source": line["source"],
    }
