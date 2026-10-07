"""Place tools: cached facts about where an idea happens, filled in by the enrichment worker."""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb import roles
from familydb.availability import enrichment_available
from familydb.dates import clock_time, parse_date
from familydb.errors import ToolError
from familydb.integrations.geocode import estimate_travel
from familydb.store import ideas, places
from familydb.store.db import transaction
from familydb.store.places import Place
from familydb.tools.registry import ToolContext, tool
from familydb.tools.urls import clean_url

log = logging.getLogger(__name__)

Day = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class OpeningHours(BaseModel):
    day: Day
    open: str = Field(description="HH:MM, 24-hour.")
    close: str = Field(description="HH:MM, 24-hour.")


class LookupPlaceInput(BaseModel):
    idea_id: int | None = Field(default=None, description="The idea whose place to look up.")
    name: str | None = Field(default=None, description="Or a place name, with an area.")
    area: str | None = None


class CheckOpenInput(BaseModel):
    idea_id: int = Field(description="The idea number.")
    date: str = Field(description="YYYY-MM-DD.")


class SavePlaceInput(BaseModel):
    idea_id: int
    name: str
    summary: str | None = Field(default=None, description="One sentence: what it is.")
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    website: str | None = None
    booking_url: str | None = Field(default=None, description="Tickets or reservations page.")
    phone: str | None = None
    hours: list[OpeningHours] = Field(
        default_factory=list, description="Only hours a page states; two entries for split days."
    )
    closed_days: list[Day] = Field(default_factory=list, description="Days it is closed.")
    price_note: str | None = Field(default=None, description="e.g. 'adults $28, kids free'.")
    source_urls: list[str] = Field(default_factory=list, description="Pages the facts came from.")
    # What the suggestions need, only as a page states it; each fills the idea's only when empty.
    cost_level: Literal[0, 1, 2, 3, 4] | None = Field(
        default=None, description="0 free, 1 cheap, 2 moderate, 3 pricey, 4 expensive."
    )
    setting: Literal["indoor", "outdoor"] | None = None
    visit_minutes: int | None = Field(default=None, description="How long a visit takes.")
    needs_booking: bool | None = Field(default=None, description="Tickets or a table needed.")
    book_days_ahead: int | None = None
    first_day: str | None = Field(default=None, description="An event's first day, YYYY-MM-DD.")
    last_day: str | None = Field(default=None, description="An event's last day, YYYY-MM-DD.")
    min_age: int | None = None
    max_age: int | None = None


class LookUpNowInput(BaseModel):
    idea_ids: list[int] = Field(
        default_factory=list,
        description="Ideas to look up now, again if they were already. Empty: every idea waiting.",
    )


class SkipPlaceInput(BaseModel):
    idea_id: int
    status: Literal["skipped", "failed"] = Field(
        description="skipped: not a specific place or event; failed: could not be identified."
    )
    reason: str = Field(description="One short sentence.")


# Kinds whose dates a page can give: a dated event or show, not a place open all year, nor a
# season that comes round again (a pumpkin patch's "until 31 October" is this year's).
DATED_KINDS = frozenset({"event", "show"})
LONGEST_VISIT = 24 * 60
FURTHEST_AHEAD = 365
OLDEST = 120


def filled_in(idea: ideas.Idea, args: SavePlaceInput, today: date) -> dict[str, Any]:
    """What a lookup adds to the idea, field by field, only where the idea has nothing: what the
    family said always stands. Anything a page could not have meant (a visit of a week, an age of
    200, an event already over) is left out rather than refused, so the place is still kept."""
    found: dict[str, Any] = {}
    if args.cost_level is not None and idea.cost_level is None:
        found["cost_level"] = args.cost_level
    if args.setting and idea.setting == "either":
        found["setting"] = args.setting
    minutes = args.visit_minutes
    empty = idea.duration_min is None and idea.duration_max is None
    if minutes is not None and 0 < minutes <= LONGEST_VISIT and empty:
        found["duration_min"] = minutes
    if args.needs_booking and not idea.needs_booking:
        found["needs_booking"] = True
    ahead = args.book_days_ahead
    if ahead is not None and 0 <= ahead <= FURTHEST_AHEAD and idea.lead_time_days is None:
        found["lead_time_days"] = ahead
    if idea.min_age is None and idea.max_age is None:
        low, high = args.min_age, args.max_age
        if low is not None and not 0 <= low <= OLDEST:
            low = None
        if high is not None and not 0 <= high <= OLDEST:
            high = None
        if low is not None and high is not None and low > high:
            low = high = None
        found |= {k: v for k, v in (("min_age", low), ("max_age", high)) if v is not None}
    dated = idea.happens_from is not None or idea.happens_until is not None
    if args.first_day and idea.kind.casefold() in DATED_KINDS and not dated:
        try:
            first = parse_date(args.first_day.strip()[:10])
            last = parse_date(args.last_day.strip()[:10]) if args.last_day else first
        except ToolError:
            return found
        if first <= last and last >= today:
            found |= {"happens_from": first.isoformat(), "happens_until": last.isoformat()}
    return found


def hours_dict(entries: list[OpeningHours], closed_days: list[str]) -> dict[str, Any] | None:
    """Storage form: weekday -> ranges; empty list is closed, absent is unknown."""
    out: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        for value in (entry.open, entry.close):
            if not TIME_RE.match(value):
                raise ToolError(f"invalid time {value!r}: use HH:MM")
        out.setdefault(entry.day, []).append({"open": entry.open, "close": entry.close})
    for day in closed_days:
        out.setdefault(day, [])
    return out or None


def open_on(place: Place | None, day: date) -> tuple[str, list[dict[str, str]]]:
    """('open' | 'closed' | 'unknown', ranges) for a date, from the cached hours."""
    if place is None or not place.hours:
        return "unknown", []
    key = DAYS[day.weekday()]
    if key not in place.hours:
        return "unknown", []
    ranges = list(place.hours.get(key) or [])
    return ("open" if ranges else "closed"), ranges


def format_ranges(ranges: list[dict[str, str]], *, spoken: bool = False) -> str | None:
    """The hours as stored ("11:30-21:00", for the model) or, `spoken`, as the family reads them
    ("11:30 am to 9 pm")."""
    if not ranges:
        return None
    if spoken:
        return ", ".join(f"{clock_time(r['open'])} to {clock_time(r['close'])}" for r in ranges)
    return ", ".join(f"{r['open']}-{r['close']}" for r in ranges)


def checked_days_ago(place: Place | None, now: datetime) -> int | None:
    if place is None or not place.last_checked_at:
        return None
    try:
        checked = datetime.strptime(place.last_checked_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return max(0, (now.astimezone(UTC) - checked).days)


def is_stale(place: Place | None, now: datetime, stale_days: int) -> bool:
    days = checked_days_ago(place, now)
    return days is None or days > stale_days


def place_summary(place: Place, ctx: ToolContext) -> dict[str, Any]:
    now = ctx.clock.now()
    return {
        "id": place.id,
        "name": place.name,
        "summary": place.summary,
        "address": place.address,
        "website": place.website,
        "booking_url": place.booking_url,
        "phone": place.phone,
        "price_note": place.price_note,
        "hours": place.hours,
        "travel_minutes": place.travel_minutes,
        "travel_km": place.travel_km,
        "travel_is_estimate": place.travel_minutes is not None,
        "checked_days_ago": checked_days_ago(place, now),
        "stale": is_stale(place, now, ctx.settings.place_stale_days),
        "source_urls": place.source_urls,
    }


@tool(
    name="lookup_place",
    description=(
        "Cached facts about an idea's place: what it is, address, hours, booking link, travel "
        "time from home. Says when nothing has been looked up yet."
    ),
)
def lookup_place(ctx: ToolContext, args: LookupPlaceInput) -> dict[str, Any]:
    idea = None
    place = None
    if args.idea_id is not None:
        idea = ideas.get(ctx.conn, args.idea_id)
        if idea is None:
            raise ToolError(f"no idea #{args.idea_id}")
        place = places.get(ctx.conn, idea.place_id) if idea.place_id else None
    elif args.name:
        place = places.find_by_name(ctx.conn, args.name)
    else:
        raise ToolError("give idea_id, or a place name")
    if place is None:
        queued = False
        if idea is not None:
            if idea.enrichment == "pending":
                queued = True
            elif enrichment_available(ctx.settings):
                with transaction(ctx.conn):
                    ideas.requeue_enrichment(ctx.conn, [idea.id], now=ctx.now_iso())
                queued = True
        return {
            "found": False,
            "queued": queued,
            "enrichment": idea.enrichment if idea else None,
            "note": idea.enrichment_note if idea else None,
        }
    return {"found": True, "idea_id": idea.id if idea else None, "place": place_summary(place, ctx)}


@tool(
    name="look_up_now",
    description=(
        "Look ideas up on the web within minutes instead of with the evening's lookups. Only "
        "when someone asks for it now."
    ),
    available=enrichment_available,
    unavailable_reason="looking ideas up on the web is switched off",
    writes=True,
)
def look_up_now(ctx: ToolContext, args: LookUpNowInput) -> dict[str, Any]:
    # A kid's lookups wait for the evening (docs/WISHES.md).
    if ctx.member is not None and not roles.may(ctx.member.role, "change"):
        raise ToolError("lookups wait for the evening; a parent can ask for one now")
    with transaction(ctx.conn):
        asked = ideas.want_lookup(ctx.conn, args.idea_ids or None, now=ctx.now_iso())
    return {
        "asked": asked,
        "unknown": [idea_id for idea_id in args.idea_ids if idea_id not in asked],
        "within_minutes": ctx.settings.enrich_interval_minutes,
    }


@tool(
    name="check_open",
    description="Whether an idea's place is open on a given date, and its hours that day.",
)
def check_open(ctx: ToolContext, args: CheckOpenInput) -> dict[str, Any]:
    idea = ideas.get(ctx.conn, args.idea_id)
    if idea is None:
        raise ToolError(f"no idea #{args.idea_id}")
    place = places.get(ctx.conn, idea.place_id) if idea.place_id else None
    day = parse_date(args.date)
    status, ranges = open_on(place, day)
    now = ctx.clock.now()
    return {
        "idea_id": idea.id,
        "date": day.isoformat(),
        "weekday": day.strftime("%A"),
        "known": status != "unknown",
        "open": status,
        "hours": format_ranges(ranges),
        "stale": is_stale(place, now, ctx.settings.place_stale_days) if place else None,
        "checked_days_ago": checked_days_ago(place, now),
        "enrichment": idea.enrichment,
    }


@tool(
    name="save_place",
    description=(
        "Store looked-up details for an idea's place and mark the idea as filled in. Used by the "
        "enrichment worker; give only facts the pages state."
    ),
    writes=True,
    worker_only=True,
)
def save_place(ctx: ToolContext, args: SavePlaceInput) -> dict[str, Any]:
    idea = ideas.get(ctx.conn, args.idea_id)
    if idea is None:
        raise ToolError(f"no idea #{args.idea_id}")
    hours = hours_dict(args.hours, args.closed_days)
    lat, lon = args.lat, args.lon
    geocoded = False
    note: str | None = None
    if lat is None or lon is None:
        if ctx.geocoder is None:
            note = "no geocoder configured"
        else:
            area = idea.location_name or ctx.settings.home_area
            query = args.address or ", ".join(p for p in (args.name, area) if p)
            point = ctx.geocoder.geocode(query)
            if point is not None:
                lat, lon, geocoded = point.lat, point.lon, True
            else:
                note = "could not geocode"
    travel = (
        estimate_travel(ctx.settings, lat, lon) if lat is not None and lon is not None else None
    )
    # Links come from fetched pages via the model; keep only real web addresses.
    website, booking_url = clean_url(args.website), clean_url(args.booking_url)
    source_urls = [u for u in (clean_url(s) for s in args.source_urls) if u]
    dropped = sum(1 for v in (args.website, args.booking_url) if v) + len(args.source_urls)
    dropped -= sum(1 for v in (website, booking_url) if v) + len(source_urls)
    if dropped:
        log.warning(
            "save_place for idea %s dropped %d link(s) that were not URLs", idea.id, dropped
        )
    now = ctx.now_iso()
    fields: dict[str, Any] = {
        "summary": args.summary,
        "address": args.address,
        "lat": lat,
        "lon": lon,
        "website": website,
        "booking_url": booking_url,
        "phone": args.phone,
        "hours": hours,
        "price_note": args.price_note,
        "travel_minutes": travel[0] if travel else None,
        "travel_km": travel[1] if travel else None,
        "source_urls": source_urls,
        "last_checked_at": now,
    }
    with transaction(ctx.conn):
        existing = places.get(ctx.conn, idea.place_id) if idea.place_id else None
        if existing is None:
            existing = places.find_by_name(ctx.conn, args.name)
        if existing is not None:
            place = places.update(ctx.conn, existing.id, {"name": args.name, **fields}, now=now)
        else:
            place = places.insert(ctx.conn, name=args.name, now=now, **fields)
        assert place is not None
        filled = filled_in(idea, args, ctx.clock.today())
        changes: dict[str, Any] = {
            "place_id": place.id,
            "enrichment": "done",
            "enriched_at": now,
            "enrichment_note": note,
            **filled,
        }
        if not idea.location_name:
            changes["location_name"] = args.name
        updated = ideas.update(ctx.conn, idea.id, changes, now=now)
    return {
        "place": place.model_dump(mode="json"),
        "idea": updated.model_dump(mode="json") if updated else None,
        "filled": sorted(filled),
        "geocoded": geocoded,
        "travel": {"minutes": travel[0], "km": travel[1], "estimate": True} if travel else None,
        "note": note,
    }


@tool(
    name="skip_place",
    description=(
        "Mark an idea as having no place to look up (skipped) or as unidentifiable (failed), "
        "with a one-line reason. Used by the enrichment worker."
    ),
    writes=True,
    worker_only=True,
)
def skip_place(ctx: ToolContext, args: SkipPlaceInput) -> dict[str, Any]:
    idea = ideas.get(ctx.conn, args.idea_id)
    if idea is None:
        raise ToolError(f"no idea #{args.idea_id}")
    now = ctx.now_iso()
    with transaction(ctx.conn):
        updated = ideas.update(
            ctx.conn,
            idea.id,
            {"enrichment": args.status, "enriched_at": now, "enrichment_note": args.reason[:500]},
            now=now,
        )
    return {
        "idea": updated.model_dump(mode="json") if updated else None,
        "status": args.status,
        "reason": args.reason,
    }
