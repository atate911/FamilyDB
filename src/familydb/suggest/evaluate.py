"""Stage: check each shortlisted idea against the places cache and the day's free time."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from familydb.clock import Clock
from familydb.config import Settings
from familydb.store import places
from familydb.store.places import Place
from familydb.suggest.shortlist import longest_free_span
from familydb.suggest.types import Candidate, Checks, Constraints, Context, Shortlisted
from familydb.tools.gcal import BLOCKS
from familydb.tools.places import checked_days_ago, format_ranges, is_stale, open_on

MIN_VISIT_MINUTES = 60


def _minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def overlap_minutes(ranges: list[dict[str, str]], free: list[str]) -> int:
    """How many minutes of the open ranges fall inside the free blocks."""
    total = 0
    for entry in ranges:
        open_at = _minutes(entry["open"])
        close_at = _minutes(entry["close"])
        if close_at <= open_at:
            close_at = 24 * 60
        for name, start, end in BLOCKS:
            if name not in free:
                continue
            block_start = start.hour * 60 + start.minute
            block_end = end.hour * 60 + end.minute
            total += max(0, min(close_at, block_end) - max(open_at, block_start))
    return total


def _hours_check(
    item: Shortlisted, place: Place | None, context: Context, checks: Checks, reasons: list[str]
) -> tuple[list, bool, bool]:
    """Returns (fitting days after the hours check, hard_fail, soft)."""
    fits = list(item.fits_days)
    if place is None or not place.hours:
        checks.open = "unknown"
        reasons.append(f"hours unknown (details {item.idea.enrichment})")
        return fits, False, True
    open_days = []
    partial = False
    soft = False
    hours_text = None
    for day in fits:
        status, ranges = open_on(place, day)
        if status == "closed":
            continue
        if status == "unknown":
            open_days.append(day)
            soft = True
            continue
        day_context = context.day(day)
        free = day_context.free if day_context else []
        if day_context is None or not day_context.free_known:
            open_days.append(day)
        else:
            overlap = overlap_minutes(ranges, free)
            need = min(MIN_VISIT_MINUTES, item.idea.duration_min or MIN_VISIT_MINUTES)
            if overlap >= need:
                open_days.append(day)
            elif overlap > 0:
                open_days.append(day)
                partial = True
            else:
                continue
        if hours_text is None:
            hours_text = format_ranges(ranges)
    if not open_days:
        checks.open = "closed"
        reasons.append("closed " + " and ".join(f"{d:%A}" for d in fits))
        return [], True, False
    checks.open = "open"
    checks.hours = hours_text
    if hours_text:
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

        if context.window is not None:
            fits, hard, soft_hours = _hours_check(item, place, context, checks, reasons)
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

        if place is not None and place.travel_minutes is not None:
            minutes = place.travel_minutes
            checks.travel_minutes = minutes
            reasons.append(f"about {minutes} min drive (estimate)")
            if (
                constraints.max_travel_minutes is not None
                and minutes > constraints.max_travel_minutes
            ):
                hard_fail = True
                reasons.append("further than asked for")
            elif fits and context.window is not None:
                spans = [
                    longest_free_span(d.free)
                    for d in (context.day(f) for f in fits)
                    if d is not None and d.free_known
                ]
                if spans:
                    need = 2 * minutes + (idea.duration_min or MIN_VISIT_MINUTES)
                    checks.travel_fits = need <= max(spans)
                    if not checks.travel_fits:
                        soft = True
                        reasons.append("tight: the drive plus the visit barely fit the free time")

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
