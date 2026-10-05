"""When the family is free: which days an event touches, and what is left of a day around it.

Plain functions over calendar events, shared by the calendar tools, the suggestion engine and
nudges. Minutes are family clock time, so a stretch reads as on the kitchen wall even on a
clock-change day.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent

BLOCKS: tuple[tuple[str, time, time], ...] = (
    ("morning", time(8, 0), time(12, 0)),
    ("afternoon", time(12, 0), time(17, 0)),
    ("evening", time(17, 0), time(22, 0)),
)


def day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def on_day(event: CalendarEvent, day: date, tz: ZoneInfo) -> bool:
    if event.all_day:
        first = event.start if isinstance(event.start, date) else event.start.date()
        last_exclusive = event.end if isinstance(event.end, date) else event.end.date()
        if last_exclusive <= first:
            last_exclusive = first + timedelta(days=1)
        return first <= day < last_exclusive
    day_start, day_end = day_bounds(day, tz)
    return event.start < day_end and event.end > day_start  # type: ignore[operator]


def free_blocks(events: list[CalendarEvent], day: date, tz: ZoneInfo) -> list[str]:
    """Which of morning, afternoon and evening are free. A busy all-day event takes the whole day;
    one marked free in Google, or a free timed event, takes none.
    """
    free: list[str] = []
    for name, start_t, end_t in BLOCKS:
        block_start = datetime.combine(day, start_t, tzinfo=tz)
        block_end = datetime.combine(day, end_t, tzinfo=tz)
        busy = any(
            event.busy
            and on_day(event, day, tz)
            and (event.all_day or (event.start < block_end and event.end > block_start))  # type: ignore[operator]
            for event in events
        )
        if not busy:
            free.append(name)
    return free


def free_spans(
    events: list[CalendarEvent], day: date, tz: ZoneInfo, start: int, end: int
) -> list[tuple[int, int]]:
    """The free stretches of a day between two minutes after midnight, busy events taken out; same
    rules as `free_blocks`.
    """
    todays = [event for event in events if event.busy and on_day(event, day, tz)]
    if any(event.all_day for event in todays):
        return []

    def minute(moment: datetime) -> int:
        local = moment.astimezone(tz)
        if local.date() < day:
            return 0
        if local.date() > day:
            return 24 * 60
        return local.hour * 60 + local.minute

    busy = sorted((minute(e.start), minute(e.end)) for e in todays)  # type: ignore[arg-type]
    spans: list[tuple[int, int]] = []
    cursor = start
    for left, right in busy:
        if left > cursor:
            spans.append((cursor, min(left, end)))
        cursor = max(cursor, right)
        if cursor >= end:
            break
    if cursor < end:
        spans.append((cursor, end))
    return [(a, b) for a, b in spans if b > a]


def events_by_day(
    calendar: CalendarAPI, start: date, end: date, tz: ZoneInfo
) -> list[tuple[date, list[CalendarEvent]]]:
    window_start, _ = day_bounds(start, tz)
    _, window_end = day_bounds(end, tz)
    events = calendar.list_events(window_start, window_end)
    days = []
    day = start
    while day <= end:
        days.append((day, [event for event in events if on_day(event, day, tz)]))
        day += timedelta(days=1)
    return days
