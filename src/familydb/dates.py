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


def ensure_not_past(when: date | datetime, clock: Clock, *, backfill: bool = False) -> None:
    """Refuse a date before today or a time before now, unless the caller flags a backfill."""
    if backfill:
        return
    past = when < clock.now() if isinstance(when, datetime) else when < clock.today()
    if past:
        raise ToolError(
            f"{when.isoformat()} is in the past; set backfill=true to record it anyway."
        )


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
