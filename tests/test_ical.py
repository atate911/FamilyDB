"""Reading a calendar feed: repeats, moved and cancelled occurrences, all-day things, floating
times, and addresses this server must not read."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from familydb.integrations import ical
from familydb.integrations.ical import FeedError, IcalFeeds, parse_feed
from tests.conftest import TZ

SAMPLE = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Library//Events//EN
BEGIN:VEVENT
UID:story
DTSTART;TZID=America/Los_Angeles:20260905T100000
DTEND;TZID=America/Los_Angeles:20260905T110000
RRULE:FREQ=WEEKLY;COUNT=10
EXDATE;TZID=America/Los_Angeles:20260926T100000
SUMMARY:Story time
LOCATION:Main library\\, Room 2
CATEGORIES:Kids,Reading
URL:https://library.example.org/story
END:VEVENT
BEGIN:VEVENT
UID:story
RECURRENCE-ID;TZID=America/Los_Angeles:20261003T100000
DTSTART;TZID=America/Los_Angeles:20261003T130000
DTEND;TZID=America/Los_Angeles:20261003T140000
SUMMARY:Story time (moved to the afternoon)
END:VEVENT
BEGIN:VEVENT
UID:fair
DTSTART;VALUE=DATE:20260926
DTEND;VALUE=DATE:20260928
SUMMARY:Harvest fair
GEO:45.63;-122.67
DESCRIPTION:Pumpkins\\, a hay maze and   music.
END:VEVENT
BEGIN:VEVENT
UID:gone
DTSTART:20260927T180000Z
DURATION:PT2H
SUMMARY:Choir
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:float
DTSTART:20260927T190000
DURATION:PT90M
SUMMARY:Stargazing
URL:javascript:alert(1)
END:VEVENT
END:VCALENDAR
"""


def _found(start=date(2026, 9, 20), end=date(2026, 10, 10)):
    return parse_feed(SAMPLE, tz=TZ, start=start, end=end)


def test_repeats_are_expanded_with_their_exceptions_and_moves() -> None:
    stories = [e for e in _found() if e.external_id.startswith("story|")]
    starts = [e.starts for e in stories]
    assert starts == [
        datetime(2026, 10, 3, 13, 0, tzinfo=TZ),  # moved to the afternoon
        datetime(2026, 10, 10, 10, 0, tzinfo=TZ),
    ]  # the 26th was skipped, and nothing before the 20th is read
    moved = stories[0]
    assert moved.title == "Story time (moved to the afternoon)"
    assert moved.external_id == "story|2026-10-03T10:00:00-07:00"  # named by where it was


def test_what_each_thing_says_is_kept() -> None:
    by_title = {e.title: e for e in _found()}
    fair = by_title["Harvest fair"]
    assert (fair.starts, fair.ends, fair.all_day) == (date(2026, 9, 26), date(2026, 9, 28), True)
    assert (fair.lat, fair.lon) == (45.63, -122.67)
    assert fair.summary == "Pumpkins, a hay maze and music."
    story = by_title["Story time"]
    assert story.venue == "Main library, Room 2" and story.category == "Kids, Reading"
    assert story.url == "https://library.example.org/story"


def test_a_cancelled_one_is_left_out_and_a_floating_time_is_the_family_s() -> None:
    by_title = {e.title: e for e in _found()}
    assert "Choir" not in by_title
    stars = by_title["Stargazing"]
    assert stars.starts == datetime(2026, 9, 27, 19, 0, tzinfo=TZ)
    assert stars.ends == datetime(2026, 9, 27, 20, 30, tzinfo=TZ)
    assert stars.url is None  # only a web address is kept as a link


def test_only_the_days_asked_are_read_soonest_first() -> None:
    titles = [e.title for e in _found(end=date(2026, 9, 27))]
    assert titles == ["Harvest fair", "Stargazing"]


def test_something_that_is_not_a_calendar_says_so() -> None:
    with pytest.raises(FeedError, match="not a calendar"):
        parse_feed(b"<html>Events</html>", tz=TZ, start=date(2026, 9, 20), end=date(2026, 9, 27))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1:8099/status",
        "http://192.168.1.10/cal.ics",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/cal.ics",
    ],
)
def test_an_address_this_server_must_not_read_is_refused(url) -> None:
    with pytest.raises(FeedError):
        ical.check_address(url)


def test_a_public_address_is_read(monkeypatch) -> None:
    monkeypatch.setattr(ical, "_public", lambda host: host == "library.example.org")
    ical.check_address("https://library.example.org/events.ics")
    fetched = []
    monkeypatch.setattr(
        IcalFeeds, "_fetch", staticmethod(lambda url: fetched.append(url) or SAMPLE)
    )
    assert IcalFeeds().read("https://library.example.org/events.ics") == SAMPLE
    assert fetched == ["https://library.example.org/events.ics"]
