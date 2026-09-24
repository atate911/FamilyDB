"""Stage: check each shortlisted idea against the places cache and the day's free time."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from familydb.clock import Clock
from familydb.config import Settings
from familydb.integrations.geocode import estimate_travel
from familydb.store import places
from familydb.store.places import Place
from familydb.suggest.types import (
    Candidate,
    Checks,
    Constraints,
    Context,
    Shortlisted,
    clock,
)
from familydb.tools.places import checked_days_ago, format_ranges, is_stale, open_on

MIN_VISIT_MINUTES = 60


def _minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def doable(
    ranges: list[dict[str, str]], spans: list[tuple[int, int]], travel: int = 0
) -> list[tuple[int, int]]:
    """When a place is open and the family is free to be there, allowing travel at both ends."""
    intervals = []
    for entry in ranges:
        open_at = _minutes(entry["open"])
        close_at = _minutes(entry["close"])
        if close_at <= open_at:
            close_at = 24 * 60
        for left, right in spans:
            a, b = max(open_at, left + travel), min(close_at, right - travel)
            if a < b:
                intervals.append((a, b))
    merged: list[tuple[int, int]] = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def overlap_minutes(
    ranges: list[dict[str, str]], spans: list[tuple[int, int]], travel: int = 0
) -> int:
    """Longest continuous opening within free time, allowing travel at both ends."""
    return max((b - a for a, b in doable(ranges, spans, travel)), default=0)


def travel_minutes(place: Place | None, context: Context, settings: Settings) -> int | None:
    """The drive there: from home as the lookup saved it, or from where the family is now."""
    if place is None:
        return None
    if context.origin is None:
        return place.travel_minutes
    if place.lat is None or place.lon is None:
        return None  # only the distance from home is known
    start = (context.origin.lat, context.origin.lon)
    estimate = estimate_travel(settings, place.lat, place.lon, start=start)
    return estimate[0] if estimate else None


def _hours_check(
    item: Shortlisted,
    place: Place | None,
    context: Context,
    checks: Checks,
    reasons: list[str],
    travel: int | None,
) -> tuple[list, bool, bool]:
    """Returns (fitting days after the hours check, hard_fail, soft)."""
    fits = list(item.fits_days)
    if place is None or not place.hours:
        checks.open = "unknown"
        if item.idea.enrichment == "done":
            reasons.append("hours not listed")
        else:
            reasons.append(f"hours unknown (details {item.idea.enrichment})")
        return fits, False, True
    open_days = []
    partial = False
    soft = False
    hours_text = None
    today_text = None
    for day in fits:
        status, ranges = open_on(place, day)
        if status == "closed":
            continue
        if status == "unknown":
            open_days.append(day)
            soft = True
            continue
        day_context = context.day(day)
        spans = day_context.spans if day_context else []
        need = item.idea.duration_min or item.idea.duration_max or MIN_VISIT_MINUTES
        stretches = doable(ranges, spans, travel or 0)
        # Without a calendar the day's free time is all of the time asked about, so the hours
        # are still held to it: "open now" must not offer a café that closed at noon.
        if day_context is None:
            open_days.append(day)
        else:
            overlap = max((b - a for a, b in stretches), default=0)
            if overlap >= need:
                open_days.append(day)
            elif overlap > 0:
                partial = True
            else:
                continue
        if hours_text is None:
            hours_text = format_ranges(ranges)
        if day == context.today and today_text is None:
            # Asked about today: say when they could actually be there, not the posted hours.
            usable = [(a, b) for a, b in stretches if b - a >= need]
            if usable:
                a, b = usable[0]
                today_text = f"can go {clock(a)}-{clock(b)} today"
    if not open_days:
        checks.open = "closed"
        reasons.append(
            "not enough continuous opening and free time"
            if partial
            else "closed " + " and ".join(f"{d:%A}" for d in fits)
        )
        return [], True, False
    checks.open = "open"
    checks.hours = hours_text
    if today_text and open_days[0] == context.today:
        reasons.append(today_text)
    elif hours_text:
        reasons.append(f"open {open_days[0]:%A} {hours_text}")
    if partial:
        soft = True
        reasons.append("open only part of the free time")
    return open_days, False, soft


def evaluate(
    conn: sqlite3.Connection,
    kept: list[Shortlisted],
    context: Context,
    constraints: Constraints,
    settings: Settings,
    clock: Clock,
) -> tuple[list[Candidate], list[int]]:
    """Verdicts for the shortlist, and the ideas whose place details are stale."""
    now: datetime = clock.now()
    candidates: list[Candidate] = []
    stale_ids: list[int] = []
    for item in kept:
        idea = item.idea
        place = places.get(conn, idea.place_id) if idea.place_id else None
        checks = Checks(weather=item.weather)
        reasons: list[str] = []
        hard_fail = False
        soft = False
        fits = list(item.fits_days)
        travel = travel_minutes(place, context, settings)

        if context.window is not None:
            fits, hard, soft_hours = _hours_check(item, place, context, checks, reasons, travel)
            hard_fail = hard_fail or hard
            soft = soft or soft_hours

        if place is not None and is_stale(place, now, settings.place_stale_days):
            checks.stale = True
            soft = True
            days = checked_days_ago(place, now)
            reasons.append(
                "details never checked" if days is None else f"details last checked {days} days ago"
            )
            stale_ids.append(idea.id)

        if idea.needs_booking:
            checks.booking_url = place.booking_url if place else None
            if idea.lead_time_days is not None and fits and context.window is not None:
                days_left = (min(fits) - context.today).days
                if idea.lead_time_days > days_left:
                    hard_fail = True
                    checks.booking = "too_late"
                    reasons.append(
                        f"needs booking {idea.lead_time_days} days ahead, only {days_left} left"
                    )
                else:
                    checks.booking = "ok"
                    reasons.append("needs booking")
            else:
                checks.booking = "unknown"
                soft = True
                reasons.append("needs booking")

        if place is not None and context.origin is not None and travel is None:
            soft = True
            reasons.append(f"distance from {context.origin.label} unknown")
        if travel is not None:
            minutes = travel
            checks.travel_minutes = minutes
            start = f" from {context.origin.label}" if context.origin else ""
            near = "under 5 min" if minutes < 5 else f"about {minutes} min drive"
            reasons.append(f"{near}{start} (estimate)")
            if (
                constraints.max_travel_minutes is not None
                and minutes > constraints.max_travel_minutes
            ):
                hard_fail = True
                reasons.append("further than asked for")
            elif fits and context.window is not None:
                spans = [
                    d.longest
                    for d in (context.day(f) for f in fits)
                    if d is not None and d.free_known
                ]
                if spans:
                    need = 2 * minutes + (idea.duration_min or MIN_VISIT_MINUTES)
                    checks.travel_fits = need <= max(spans)
                    if not checks.travel_fits:
                        hard_fail = True
                        reasons.append("the drive plus the visit do not fit the free time")

        if item.weather == "ok" and (idea.setting == "outdoor" or idea.weather != "any"):
            reasons.append("weather looks fine")

        verdict = "ruled_out" if hard_fail else ("possible" if soft else "good")
        candidates.append(
            Candidate(
                idea_id=idea.id,
                title=idea.title,
                verdict=verdict,
                reasons=reasons,
                fits_days=[d.isoformat() for d in fits],
                checks=checks,
            )
        )
    return candidates, stale_ids
