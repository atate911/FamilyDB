"""Parsing and validating dates in the family timezone."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from familydb.base.clock import Clock
from familydb.base.errors import ToolError


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
    """The next birthday on or after today; from 29 February, 1 March in a year without one."""
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


def clock_time(value: datetime | time | str) -> str:
    """A time of day as the family reads it: "9 am", "1:30 pm", "12 pm". The number is held to
    am or pm by a no-break space. Takes a time, a datetime (its wall time as it is) or an
    "HH:MM" or "YYYY-MM-DDTHH:MM" string. What the model is sent and what is stored stay 24-hour."""
    if isinstance(value, str):
        text = value[11:16] if "T" in value else value  # an offset after the minutes is ignored
        hour, minute = int(text[:2]), int(text[3:5])
    else:
        hour, minute = value.hour, value.minute
    clock = f"{hour % 12 or 12}:{minute:02d}" if minute else str(hour % 12 or 12)
    return f"{clock}\u00a0{'am' if hour < 12 else 'pm'}"


def hour_words(hour: int) -> str:
    """An hour on the dot, as the settings say it: "7 am", "12 pm"."""
    return clock_time(time(hour))


_HH_MM = re.compile(r"\b([01]\d|2[0-4]):([0-5]\d)\b(?:-([01]\d|2[0-4]):([0-5]\d)\b)?")


def spoken_times(text: str) -> str:
    """Every "HH:MM" in text, and "HH:MM-HH:MM" stretch, written as the family reads it ("7:30 pm",
    "3 pm to 5 pm"), for words the engine made for a person; "24:00", the end of a day, is
    "12 am"."""

    def at(hour: str, minute: str) -> str:
        return clock_time(f"{int(hour) % 24:02d}:{minute}")

    def one(found: re.Match[str]) -> str:
        first = at(found[1], found[2])
        return f"{first} to {at(found[3], found[4])}" if found[3] else first

    return _HH_MM.sub(one, text)
