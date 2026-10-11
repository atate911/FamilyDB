"""The hourly job for what is on near home: each source read when due, failures told to admins
after three days, the weekly search and the calendar lookup held to the month's budget, and
nothing asked of a model when nothing is due."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from familydb import happening
from familydb.agent.prompt import load_prompt
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.integrations.events import FoundEvent
from familydb.integrations.ical import FeedError
from familydb.jobs import happening as job
from familydb.jobs.happening import run_happening
from familydb.store import alerts as alert_store
from familydb.store import finds
from familydb.store.db import transaction
from tests import fakes
from tests.conftest import TZ

LIBRARY = "https://library.example.org/events.ics"
PARKS = "https://parks.example.org/calendar.ics"


def _ics(*events: tuple[str, str, str]) -> bytes:
    """A calendar of (uid, YYYYMMDDTHHMMSS local, title)."""
    body = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:test"]
    for uid, start, title in events:
        body += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;TZID=America/Vancouver:{start}",
            f"SUMMARY:{title}",
            "END:VEVENT",
        ]
    body.append("END:VCALENDAR")
    return "\r\n".join(body).encode()


STORY = ("story", "20260926T103000", "Story time")
CHOIR = ("choir", "20260927T150000", "Choir")


class Feeds:
    """Calendars by address: the bytes it serves, or an error it raises."""

    def __init__(self, served: dict[str, bytes | Exception]) -> None:
        self.served = served
        self.read_urls: list[str] = []

    def read(self, url: str) -> bytes:
        self.read_urls.append(url)
        answer = self.served.get(url, FeedError("404"))
        if isinstance(answer, Exception):
            raise answer
        return answer


class TM:
    def __init__(self, events: list[FoundEvent] | Exception) -> None:
        self.answer = events
        self.calls = 0

    def events(self, lat, lon, radius_km, start, end):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


SHOW = FoundEvent(
    external_id="G1",
    title="Brandi Carlile",
    starts=datetime(2026, 10, 3, 19, 30, tzinfo=TZ),
    venue="Moda Center",
)


def _app(settings, day: int = 20, hour: int = 12, **extra) -> App:
    live = settings.model_copy(
        update={"home_lat": 45.63, "home_lon": -122.67, "home_area": "Vancouver, WA", **extra}
    )
    app = App(live, FixedClock(datetime(2026, 9, 1, hour) + timedelta(days=day - 1), TZ))
    app.senders["telegram"] = lambda *_: None
    return app


def _upcoming(conn):
    return finds.upcoming(conn, start=date(2026, 9, 1), end=date(2026, 12, 31), limit=50)


def test_nothing_to_read_reads_nothing_and_asks_nothing(settings, conn) -> None:
    api = fakes.FakeMessagesAPI()
    assert set(run_happening(_app(settings), api=api).values()) == {0}
    assert api.requests == [] and finds.sources(conn) == []


def test_calendars_and_ticketmaster_are_read_once_a_day(settings, conn) -> None:
    feeds, tm = Feeds({LIBRARY: _ics(STORY, CHOIR)}), TM([SHOW])
    extra = {"event_feeds": LIBRARY, "ticketmaster_api_key": "tm-1"}
    counts = run_happening(_app(settings, **extra), feeds=feeds, ticketmaster=tm)
    assert (counts["read"], counts["added"]) == (2, 3)
    assert {f.title for f in _upcoming(conn)} == {"Story time", "Choir", "Brandi Carlile"}
    assert {(s.source, s.found) for s in finds.sources(conn)} == {
        (happening.feed_source(LIBRARY), 2),
        ("ticketmaster", 1),
    }

    later = run_happening(_app(settings, hour=13, **extra), feeds=feeds, ticketmaster=tm)
    assert later["read"] == 0 and len(feeds.read_urls) == 1 and tm.calls == 1

    feeds.served[LIBRARY] = _ics(STORY)  # the choir was called off
    tomorrow = run_happening(_app(settings, day=21, hour=12, **extra), feeds=feeds, ticketmaster=tm)
    assert (tomorrow["read"], tomorrow["gone"]) == (2, 1)
    assert "Choir" not in {f.title for f in _upcoming(conn)}


def test_a_calendar_that_cannot_be_read_is_told_after_three_days(settings, conn) -> None:
    feeds = Feeds({LIBRARY: FeedError("library.example.org answered HTTP 404")})
    for day in (20, 21):
        run_happening(_app(settings, day=day, event_feeds=LIBRARY), feeds=feeds)
        assert alert_store.current(conn, since="2026-01-01") == []
    run_happening(_app(settings, day=22, event_feeds=LIBRARY), feeds=feeds)
    [told] = alert_store.current(conn, since="2026-01-01")
    assert told.kind == "happening" and "3 days running" in told.detail
    assert "library.example.org" in told.detail

    feeds.served[LIBRARY] = _ics(STORY)
    run_happening(_app(settings, day=23, event_feeds=LIBRARY), feeds=feeds)
    assert alert_store.current(conn, since="2026-01-01") == []


def test_a_calendar_taken_off_the_list_is_forgotten_with_what_it_listed(settings, conn) -> None:
    feeds = Feeds({LIBRARY: _ics(STORY), PARKS: _ics(CHOIR)})
    run_happening(_app(settings, event_feeds=f"{LIBRARY}\n{PARKS}"), feeds=feeds)
    run_happening(_app(settings, hour=13, event_feeds=PARKS), feeds=feeds)
    assert [f.title for f in _upcoming(conn)] == ["Choir"]
    assert [s.source for s in finds.sources(conn)] == [happening.feed_source(PARKS)]


SEARCHING = {"web_tools_enabled": True}
DATED = [
    {
        "title": "Lantern walk",
        "url": "https://parks.example.org/lanterns",
        "dates": "Fri 9 Oct, 7pm",
        "starts_on": "2026-10-09",
        "starts_time": "19:00",
        "summary": "Bring a lantern.",
    },
    {"title": "Undated", "url": "https://example.org/x", "summary": "No day given."},
    {
        "title": "Too far ahead",
        "url": "https://example.org/y",
        "starts_on": "2027-01-01",
        "summary": "Next year.",
    },
]


def _looked(conn, at: str = "2026-09-20T12:00:00Z") -> None:
    """The calendar lookup for this home area has just been made."""
    with transaction(conn):
        source = happening.proposals_source("Vancouver, WA")
        finds.source_answered(conn, source, "proposals", ok=True, note="", found=0, at=at)


def test_the_weekly_search_keeps_what_says_when_it_is_on(settings, conn) -> None:
    _looked(conn)
    api = fakes.FakeMessagesAPI(*fakes.discover_script(DATED))
    counts = run_happening(_app(settings, **SEARCHING), api=api)
    assert counts["searched"] == 1
    [lantern] = _upcoming(conn)
    assert (lantern.title, lantern.starts_at, lantern.kind) == (
        "Lantern walk",
        "2026-10-09T19:00",
        "web",
    )
    asked = api.requests[0]["messages"][0]["content"][1]["text"]
    assert "Home area: Vancouver, WA." in asked and "Window: Sunday 20 September" in asked

    quiet = fakes.FakeMessagesAPI()
    assert run_happening(_app(settings, day=25, **SEARCHING), api=quiet)["searched"] == 0
    assert quiet.requests == []
    _looked(conn, at="2026-09-27T12:00:00Z")
    again = fakes.FakeMessagesAPI(*fakes.discover_script([]))
    assert run_happening(_app(settings, day=27, **SEARCHING), api=again)["searched"] == 1


@pytest.mark.parametrize(
    "held",
    [{"happening_budget": 0}, {"happening_search": False}, {"web_tools_enabled": False}],
)
def test_no_search_without_the_budget_the_setting_or_the_web(settings, conn, held) -> None:
    api = fakes.FakeMessagesAPI()
    feeds = Feeds({LIBRARY: _ics(STORY)})
    counts = run_happening(
        _app(settings, event_feeds=LIBRARY, **{**SEARCHING, **held}), api=api, feeds=feeds
    )
    assert counts["read"] == 1 and counts["searched"] == 0 and api.requests == []


def test_a_month_s_budget_spent_stops_the_search_but_not_the_calendars(
    settings, conn, monkeypatch
) -> None:
    monkeypatch.setattr(happening, "spent_this_month", lambda *_: 0.95)
    api = fakes.FakeMessagesAPI()
    counts = run_happening(
        _app(settings, event_feeds=LIBRARY, **SEARCHING),
        api=api,
        feeds=Feeds({LIBRARY: _ics(STORY)}),
    )
    assert counts["read"] == 1 and api.requests == []


def _feeds_script(*handed: dict) -> list:
    return [
        fakes.message(
            [fakes.tool_use("tu_feeds", "report_feeds", {"feeds": list(handed)})],
            stop_reason="tool_use",
        )
    ]


def test_calendars_found_near_home_are_offered_only_when_they_read(settings, conn) -> None:
    api = fakes.FakeMessagesAPI(
        *_feeds_script(
            {"title": "Library", "url": LIBRARY, "why": "Story time and more."},
            {"title": "Not a calendar", "url": "https://city.example.org/events", "why": "A page."},
        ),
        *fakes.discover_script([]),
    )
    feeds = Feeds(
        {LIBRARY: _ics(STORY), "https://city.example.org/events": FeedError("not a calendar")}
    )
    counts = run_happening(_app(settings, **SEARCHING), api=api, feeds=feeds)
    assert counts["proposed"] == 1 and counts["searched"] == 1
    [offered] = finds.proposals(conn, "Vancouver, WA")
    assert (offered.url, offered.title, offered.events) == (LIBRARY, "Library", 1)
    [news] = [a for a in alert_store.current(conn, since="2026-01-01") if a.kind == "calendars"]
    assert "1 new event calendar: Library" in news.detail

    # Not asked again until the family's days between looks have passed: only the search.
    quiet = fakes.FakeMessagesAPI(*fakes.discover_script([]))
    run_happening(_app(settings, day=28, **SEARCHING), api=quiet, feeds=feeds)
    assert {r["system"][0]["text"] for r in quiet.requests} == {load_prompt("discover")}
    later = fakes.FakeMessagesAPI(*_feeds_script(), *fakes.discover_script([]))
    run_happening(_app(settings, day=50, **SEARCHING), api=later, feeds=feeds)
    asked = later.requests[0]["messages"][0]["content"][1]["text"]
    assert "Already known, do not report:" in asked and LIBRARY in asked


def test_a_new_home_area_looks_for_calendars_at_once(settings, conn) -> None:
    _looked(conn)
    api = fakes.FakeMessagesAPI(*_feeds_script(), *fakes.discover_script([]))
    run_happening(_app(settings, home_area="Portland, OR", **SEARCHING), api=api)
    assert "Home area: Portland, OR." in api.requests[0]["messages"][0]["content"][1]["text"]


def test_a_restart_reads_what_is_due(settings, conn, monkeypatch) -> None:
    from familydb.jobs.catch_up import run_catch_up

    monkeypatch.setattr(job, "IcalFeeds", lambda: Feeds({LIBRARY: _ics(STORY)}))
    result = run_catch_up(_app(settings, event_feeds=LIBRARY))
    assert result["happening"]["read"] == 1


def test_the_status_page_shows_each_source_and_what_is_on(settings, conn, family) -> None:
    from markupsafe import escape

    from familydb.web import create_app

    feeds = Feeds({LIBRARY: _ics(STORY, CHOIR), PARKS: FeedError("parks.example.org: HTTP 500")})
    app = _app(settings, event_feeds=f"{LIBRARY}\n{PARKS}", web_password="open sesame please")
    run_happening(app, feeds=feeds)
    client = create_app(app).test_client()
    client.post("/login", data={"password": "open sesame please"})
    text = client.get("/status").text
    assert 'id="happening"' in text and str(escape(happening.NAME)) in text
    assert "Calendar at library.example.org" in text and "Read " in text
    assert "Calendar at parks.example.org" in text and "HTTP 500" in text
    assert "2 on in the next 28 days." in text
