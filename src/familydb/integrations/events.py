"""The one shape every source of dated things near home hands back: a calendar feed,
Ticketmaster, or a find from the weekly search. No SDK and no store here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class FoundEvent:
    """One dated thing as a source lists it.

    `starts` and `ends` are aware datetimes for a timed thing, dates for an all-day one, whose
    `ends` is exclusive, as Google's and iCal's are. `external_id` is the source's own name for
    it, so the next read of the same source finds the same row.
    """

    external_id: str
    title: str
    starts: datetime | date
    ends: datetime | date | None = None
    all_day: bool = False
    venue: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    url: str | None = None
    price_note: str | None = None
    summary: str | None = None
    category: str | None = None


def stored_when(value: datetime | date | None, tz: ZoneInfo) -> str | None:
    """A start or end as `finds` keeps it: the family's wall time, to the minute, or a day."""
    if value is None:
        return None
    if isinstance(value, datetime):
        local = value.astimezone(tz) if value.tzinfo else value
        return local.strftime("%Y-%m-%dT%H:%M")
    return value.isoformat()


def stored_end(event: FoundEvent, tz: ZoneInfo) -> str | None:
    """The end as kept: an all-day thing's last day (its exclusive end less a day), else the
    end's minute. None when the source gave no end, or one no later than the start."""
    if event.ends is None:
        return None
    if event.all_day and not isinstance(event.ends, datetime):
        last = event.ends - timedelta(days=1)
        start = event.starts if not isinstance(event.starts, datetime) else event.starts.date()
        return last.isoformat() if last > start else None
    end = stored_when(event.ends, tz)
    start = stored_when(event.starts, tz)
    return end if end and start and end > start else None
