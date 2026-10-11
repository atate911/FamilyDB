"""A place's opening hours as its record keeps them (`places.hours`: weekday to ranges, an empty
list closed, a day absent unknown), read for a date and worded, and how long ago they were
looked up. The lookup tools write them (`tools/places.py`); the engine, the evening check and
the page read them here."""

from __future__ import annotations

from datetime import UTC, date, datetime

from familydb.base.dates import clock_time
from familydb.store.places import Place

DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


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
