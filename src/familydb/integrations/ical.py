"""Calendar feeds: the iCal (.ics) addresses a library, a school, a venue or the city publishes
for subscribing, read by this server once a day (jobs/happening.py).

Reading is plain HTTPS, with nothing of the family sent. Parsing is `icalendar`, and repeats are
expanded by `recurring-ical-events`, which follows RRULE, EXDATE, RDATE and moved occurrences
(RECURRENCE-ID) across daylight-saving changes: what community calendars are made of, and what a
hand-written parser would quietly get wrong.

An address may come from the family or from a page the proposal lookup read, so it is treated as
untrusted: only http and https, never a host that resolves to this machine or the home network,
followed through redirects, and no more than a calendar could be.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

from familydb.integrations import address
from familydb.integrations.events import FoundEvent

TIMEOUT = 30
# A city's whole calendar for a year is well under a megabyte.
MAX_BYTES = 5 * 1024 * 1024
# The most kept from one calendar for the days read: a busy city calendar lists a few hundred.
MAX_EVENTS = 500
USER_AGENT = "familydb/0.1 (self-hosted family planning bot)"


class FeedError(Exception):
    """A calendar could not be fetched or read."""


class FeedAPI(Protocol):
    def read(self, url: str) -> bytes: ...


def _public(host: str) -> bool:
    """Whether a host name is out on the internet; a calendar has no business anywhere else."""
    return address.is_public(host)


def check_address(url: str) -> None:
    """Refuse an address this server should not read. Raises FeedError saying why."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedError(f"{url} is not a web address")
    if not _public(parts.hostname):
        raise FeedError(f"{parts.hostname} is not a public address")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect is followed only to an address that passes the same check."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        check_address(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class IcalFeeds:
    """Calendars read over HTTP(S). Each call fetches afresh; each is read once a day."""

    @staticmethod
    def _fetch(url: str) -> bytes:
        check_address(url)
        opener = urllib.request.build_opener(_CheckedRedirects)
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "text/calendar, */*;q=0.5"}
        )
        try:
            with opener.open(request, timeout=TIMEOUT) as response:
                body = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise FeedError(f"{urlsplit(url).hostname} answered HTTP {exc.code}") from exc
        except FeedError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FeedError(f"{urlsplit(url).hostname} could not be reached: {exc}") from exc
        if len(body) > MAX_BYTES:
            raise FeedError(f"{urlsplit(url).hostname} sent more than a calendar could be")
        return body

    def read(self, url: str) -> bytes:
        return self._fetch(url)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = ", ".join(str(one) for one in value)
    text = " ".join(str(value).split())
    return text or None


def _categories(value: Any) -> str | None:
    """CATEGORIES may come as one property or several, each holding a list."""
    if value is None:
        return None
    found: list[str] = []
    for one in value if isinstance(value, list) else [value]:
        cats = getattr(one, "cats", None)
        found.extend(str(cat) for cat in (cats if cats is not None else [one]))
    return ", ".join(dict.fromkeys(cat.strip() for cat in found if cat.strip())) or None


def _web(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    parts = urlsplit(text)
    return text if parts.scheme in ("http", "https") and parts.netloc else None


def _moment(value: Any, tz: ZoneInfo) -> datetime | date:
    """A start or end as an aware datetime in the family's zone, or a day. A time with no zone
    (iCal's floating time) is the time where the family is, which is what it means."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=tz) if value.tzinfo is None else value.astimezone(tz)
    if isinstance(value, date):
        return value
    raise FeedError(f"a start or end that is not a time: {value!r}")


def _event(component: Any, tz: ZoneInfo) -> FoundEvent | None:
    if str(component.get("STATUS", "")).upper() == "CANCELLED":
        return None
    title = _text(component.get("SUMMARY"))
    start_prop = component.get("DTSTART")
    if not title or start_prop is None:
        return None
    starts = _moment(start_prop.dt, tz)
    all_day = not isinstance(starts, datetime)
    ends: datetime | date | None = None
    if component.get("DTEND") is not None:
        ends = _moment(component.get("DTEND").dt, tz)
    elif component.get("DURATION") is not None:
        ends = starts + component.get("DURATION").dt
    elif all_day:
        ends = starts + timedelta(days=1)
    if isinstance(ends, datetime) != isinstance(starts, datetime):
        ends = None  # a timed start with a day for an end, or the other way: trust neither
    uid = _text(component.get("UID"))
    occurrence = component.get("RECURRENCE-ID")
    when = (occurrence.dt if occurrence is not None else start_prop.dt).isoformat()
    if not uid:
        uid = hashlib.sha256(f"{title}|{when}".encode()).hexdigest()[:16]
    geo = component.get("GEO")
    return FoundEvent(
        external_id=f"{uid}|{when}",
        title=title,
        starts=starts,
        ends=ends,
        all_day=all_day,
        venue=_text(component.get("LOCATION")),
        lat=getattr(geo, "latitude", None),
        lon=getattr(geo, "longitude", None),
        url=_web(component.get("URL")),
        summary=_text(component.get("DESCRIPTION")),
        category=_categories(component.get("CATEGORIES")),
    )


def parse_feed(body: bytes | str, *, tz: ZoneInfo, start: date, end: date) -> list[FoundEvent]:
    """Every occurrence on from `start` to `end` (both days included), repeats expanded,
    cancelled ones left out, soonest first. Raises FeedError when it is not a calendar."""
    try:
        calendar = icalendar.Calendar.from_ical(body)
    except Exception as exc:  # icalendar raises ValueError and friends on anything malformed
        raise FeedError(f"not a calendar: {exc}") from exc
    if getattr(calendar, "name", "") != "VCALENDAR":
        raise FeedError("not a calendar")
    try:
        occurrences = recurring_ical_events.of(calendar).between(start, end + timedelta(days=1))
    except Exception as exc:  # a repeat rule the library cannot follow
        raise FeedError(f"its repeats could not be read: {exc}") from exc
    found: list[FoundEvent] = []
    for component in occurrences:
        try:
            event = _event(component, tz)
        except FeedError:
            continue
        if event is not None:
            found.append(event)

    def soonest(event: FoundEvent) -> tuple[str, str]:
        starts = event.starts
        key = starts.isoformat() if isinstance(starts, datetime) else f"{starts.isoformat()}T"
        return key, event.title

    return sorted(found, key=soonest)[:MAX_EVENTS]
