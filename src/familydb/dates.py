"""Parsing and validating dates in the family timezone."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from familydb.clock import Clock
from familydb.errors import ToolError


def parse_date(value: str) -> date:
    """Parse YYYY-MM-DD."""
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ToolError(f"Invalid date {value!r}: use YYYY-MM-DD.") from exc


def parse_datetime(value: str, tz: ZoneInfo) -> datetime:
    """Parse an ISO datetime. Naive values are family-zone wall time; aware ones are converted."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ToolError(f"Invalid datetime {value!r}: use YYYY-MM-DDTHH:MM.") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def ensure_not_past(when: date | datetime, clock: Clock) -> None:
    """Refuse a date before today or a time before now."""
    past = when < clock.now() if isinstance(when, datetime) else when < clock.today()
    if past:
        raise ToolError(f"{when.isoformat()} is in the past.")


def parse_date_range(start_text: str, end_text: str) -> tuple[date, date]:
    """Two YYYY-MM-DD strings, end not before start."""
    start = parse_date(start_text)
    end = parse_date(end_text)
    if end < start:
        raise ToolError("end is before start")
    return start, end


def iso_date(day: date) -> str:
    return day.isoformat()


def iso_datetime(moment: datetime) -> str:
    """ISO with offset, minute precision, for calendar events."""
    return moment.isoformat(timespec="minutes")


def utc_iso(moment: datetime) -> str:
    """Storage form for instants: UTC with a Z suffix, second precision."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def weekend_window(today: date) -> tuple[date, date]:
    """The weekend a question asked on `today` refers to; never a day before today."""
    weekday = today.weekday()  # Monday is 0
    if weekday == 5:
        return today, today + timedelta(days=1)
    if weekday == 6:
        return today, today
    saturday = today + timedelta(days=5 - weekday)
    return saturday, saturday + timedelta(days=1)


def age_on(birth_date: str | None, today: date) -> int | None:
    """How old somebody born on this day is today, in whole years; None with no birthday."""
    if not birth_date:
        return None
    born = date.fromisoformat(birth_date)
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def next_birthday(birth_date: str | None, today: date) -> date | None:
    """The next birthday on or after today. Born on 29 February, it falls on 1 March in a year
    without one."""
    if not birth_date:
        return None
    born = date.fromisoformat(birth_date)
    for year in (today.year, today.year + 1):
        try:
            day = born.replace(year=year)
        except ValueError:
            day = date(year, 3, 1)
        if day >= today:
            return day
    raise AssertionError("a birthday comes round within a year")
