"""Ticketmaster's Discovery API: shows, concerts, games and family events within a radius of
home, read once a day with the family's free key (jobs/happening.py).

What leaves the house: the key, home's position rounded to two decimals (about a kilometer) and
sent as a geohash (`geoPoint`, which replaced the older `latlong`), the radius and the dates.
Nothing else about the family. The key rides in the address, as the API asks, so no error this
module raises ever repeats the address.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

from familydb.base.config import Settings
from familydb.integrations.events import FoundEvent

EVENTS_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
TIMEOUT = 30
MAX_BYTES = 4 * 1024 * 1024
PAGE_SIZE = 100
# Two pages of the soonest a hundred each: far more than a family reads, well within the free
# quota (5,000 calls a day), and a day's read is at most two calls.
MAX_PAGES = 2
GONE = frozenset({"cancelled", "canceled", "offsale"})
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


class TicketmasterError(Exception):
    """Ticketmaster could not be asked, or did not answer in its own shape."""


class TicketmasterAPI(Protocol):
    def events(
        self, lat: float, lon: float, radius_km: int, start: date, end: date
    ) -> list[FoundEvent]: ...


def geohash(lat: float, lon: float, precision: int = 9) -> str:
    """A position as a geohash, the form `geoPoint` takes."""
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    bits, bit, even, out = 0, 0, True, []
    while len(out) < precision:
        span, value = (lon_range, lon) if even else (lat_range, lat)
        middle = (span[0] + span[1]) / 2
        if value >= middle:
            bits = bits * 2 + 1
            span[0] = middle
        else:
            bits *= 2
            span[1] = middle
        even = not even
        bit += 1
        if bit == 5:
            out.append(_BASE32[bits])
            bits, bit = 0, 0
    return "".join(out)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _web(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    parts = urlsplit(text)
    return text if parts.scheme in ("http", "https") and parts.netloc else None


def _when(start: dict[str, Any], tz: ZoneInfo) -> tuple[datetime | date, bool] | None:
    """When it starts: the exact moment when Ticketmaster gives one, else its day."""
    local_day = start.get("localDate")
    if start.get("dateTBD") or start.get("dateTBA") or not isinstance(local_day, str):
        return None
    try:
        day = date.fromisoformat(local_day)
    except ValueError:
        return None
    if start.get("timeTBA") or start.get("noSpecificTime"):
        return day, True
    moment = start.get("dateTime")
    if isinstance(moment, str):
        try:
            return datetime.fromisoformat(moment.replace("Z", "+00:00")).astimezone(tz), False
        except ValueError:
            pass
    local_time = start.get("localTime")
    if isinstance(local_time, str):
        try:
            # Near home, the venue's clock is the family's.
            return datetime.combine(day, time.fromisoformat(local_time), tzinfo=tz), False
        except ValueError:
            pass
    return day, True


def _price(ranges: Any) -> str | None:
    if not isinstance(ranges, list) or not ranges or not isinstance(ranges[0], dict):
        return None
    low, high = _number(ranges[0].get("min")), _number(ranges[0].get("max"))
    currency = _text(ranges[0].get("currency")) or ""
    if low is None:
        return None
    sign = "$" if currency in ("USD", "CAD", "AUD", "NZD", "") else f"{currency} "
    if high is None or high <= low:
        return f"from {sign}{low:.0f}"
    return f"{sign}{low:.0f} to {high:.0f}"


def _category(classifications: Any) -> str | None:
    if not isinstance(classifications, list) or not classifications:
        return None
    first = classifications[0] if isinstance(classifications[0], dict) else {}
    names = []
    for part in ("segment", "genre", "subGenre"):
        name = _text((first.get(part) or {}).get("name"))
        if name and name.casefold() != "undefined" and name not in names:
            names.append(name)
    return ", ".join(names) or None


def parse_events(payload: Any, *, tz: ZoneInfo) -> list[FoundEvent]:
    """The events in one page of an event search. A page with none has no `_embedded`."""
    if not isinstance(payload, dict):
        raise TicketmasterError("Ticketmaster did not answer with an event list")
    embedded = payload.get("_embedded") or {}
    events = embedded.get("events") if isinstance(embedded, dict) else None
    if events is None:
        return []
    if not isinstance(events, list):
        raise TicketmasterError("Ticketmaster's event list is not what it used to be")
    found: list[FoundEvent] = []
    for one in events:
        if not isinstance(one, dict):
            continue
        dates = one.get("dates") if isinstance(one.get("dates"), dict) else {}
        status = str(((dates.get("status") or {}).get("code")) or "").casefold()
        when = _when(dates.get("start") or {}, tz)
        title = _text(one.get("name"))
        event_id = _text(one.get("id"))
        if status in GONE or when is None or not title or not event_id:
            continue
        starts, all_day = when
        venues = (one.get("_embedded") or {}).get("venues") or [{}]
        venue = venues[0] if isinstance(venues[0], dict) else {}
        location = venue.get("location") or {}
        line = _text((venue.get("address") or {}).get("line1"))
        city = _text((venue.get("city") or {}).get("name"))
        found.append(
            FoundEvent(
                external_id=event_id,
                title=title,
                starts=starts,
                ends=starts + timedelta(days=1) if all_day else None,
                all_day=all_day,
                venue=_text(venue.get("name")),
                address=", ".join(part for part in (line, city) if part) or None,
                lat=_number(location.get("latitude")),
                lon=_number(location.get("longitude")),
                url=_web(one.get("url")),
                price_note=_price(one.get("priceRanges")),
                summary=_text(one.get("info")) or _text(one.get("pleaseNote")),
                category=_category(one.get("classifications")),
            )
        )
    return found


def total_pages(payload: Any) -> int:
    page = payload.get("page") if isinstance(payload, dict) else None
    try:
        return int((page or {}).get("totalPages") or 0)
    except (TypeError, ValueError):
        return 0


class Ticketmaster:
    """The event search, with the key from the settings. Each call reads afresh."""

    def __init__(self, settings: Settings) -> None:
        self.key = settings.ticketmaster_api_key or ""
        self.tz = settings.tzinfo

    @staticmethod
    def _fetch(url: str) -> Any:
        request = urllib.request.Request(
            url, headers={"User-Agent": "familydb/0.1", "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                body = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # 401: the key was refused. 429: the day's quota. The address carries the key, so it
            # is never repeated, nor is the exception that holds it.
            raise TicketmasterError(f"Ticketmaster answered HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TicketmasterError("Ticketmaster could not be reached") from None
        if len(body) > MAX_BYTES:
            raise TicketmasterError("Ticketmaster sent more than an event list could be")
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            raise TicketmasterError("Ticketmaster did not answer with JSON") from None

    def _url(
        self, lat: float, lon: float, radius_km: int, start: date, end: date, page: int
    ) -> str:
        first = datetime.combine(start, time(), tzinfo=self.tz).astimezone(UTC)
        last = datetime.combine(end + timedelta(days=1), time(), tzinfo=self.tz).astimezone(UTC)
        query = {
            "apikey": self.key,
            "geoPoint": geohash(round(lat, 2), round(lon, 2)),
            "radius": str(radius_km),
            "unit": "km",
            "startDateTime": first.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": last.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "size": str(PAGE_SIZE),
            "page": str(page),
            "sort": "date,asc",
        }
        return f"{EVENTS_URL}?{urlencode(query)}"

    def events(
        self, lat: float, lon: float, radius_km: int, start: date, end: date
    ) -> list[FoundEvent]:
        found: list[FoundEvent] = []
        for page in range(MAX_PAGES):
            payload = self._fetch(self._url(lat, lon, radius_km, start, end, page))
            found.extend(parse_events(payload, tz=self.tz))
            if page + 1 >= total_pages(payload):
                break
        return found
