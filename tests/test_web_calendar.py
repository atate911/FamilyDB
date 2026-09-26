"""The Plans page's list and month: the family calendar as Google has it, or as the bot saved it."""

from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from familydb.app import App
from familydb.store import plans
from familydb.tools import ToolContext, build_registry
from familydb.web import create_app
from tests import fakes

TZ = ZoneInfo("America/Vancouver")


def _page(app_settings, clock, calendar=None):
    app = App(app_settings, clock, calendar=calendar)
    return app, create_app(app).test_client()


def _make_plan(app, conn, family, **args) -> dict:
    """A plan made the way the bot makes them, through the tool."""
    ctx = ToolContext(conn, app.settings, app.clock, member=family["sam"], calendar=app.calendar)
    result = build_registry().dispatch("create_event", args, ctx)
    assert not result.is_error, result.content
    return json.loads(result.content)


@pytest.fixture
def google(calendar_settings, clock, conn, family):
    calendar = fakes.FakeCalendar(TZ)
    app, client = _page(calendar_settings, clock, calendar)
    return app, client, calendar


def test_the_list_is_google_s_calendar_with_the_bot_s_own_plans_marked(google, conn, family):
    app, client, calendar = google
    made = _make_plan(app, conn, family, title="Museum", start="2026-09-26T10:00")
    calendar.patch_event(  # somebody moves it in Google, on their phone
        made["event"]["id"],
        start=datetime(2026, 9, 27, 14, tzinfo=TZ),
        end=datetime(2026, 9, 27, 16, tzinfo=TZ),
    )
    calendar.seed(
        "Dentist", datetime(2026, 9, 25, 9, tzinfo=TZ), datetime(2026, 9, 25, 10, tzinfo=TZ)
    )
    text = client.get("/plans").text
    assert "From Google Calendar" in text
    assert "Sunday 27 September, 14:00" in text  # where Google has it, not where it was made
    assert "Dentist" in text and "added in Google" in text
    assert text.count("<summary>Move it</summary>") == 1  # only the bot's own can be moved
    # Looking is not a write: the stored plan catches up when the bot next acts on it.
    assert plans.get(conn, made["plan"]["id"]).start == "2026-09-26T10:00-07:00"


def test_when_google_does_not_answer_the_page_says_so(google, conn, family) -> None:
    app, client, calendar = google
    _make_plan(app, conn, family, title="Museum", start="2026-09-26T10:00")

    def down(*_args, **_kwargs):
        raise TimeoutError("Google is having a bad day")

    calendar.list_events = down
    text = client.get("/plans").text
    assert "did not answer" in text and "Museum" in text


def test_without_google_the_list_is_the_saved_plans(settings, clock, conn, family) -> None:
    with conn:
        plans.insert(
            conn, title="Picnic", start="2026-09-26", end="2026-09-26", all_day=True, now="x"
        )
    _, client = _page(settings, clock)
    text = client.get("/plans").text
    assert "not connected" in text and "Picnic" in text


def test_a_weekend_away_is_on_each_of_its_days_in_the_month(google, conn, family) -> None:
    app, client, _ = google
    _make_plan(app, conn, family, title="Camping", start="2026-10-02", end="2026-10-04")
    _make_plan(app, conn, family, title="Dinner", start="2026-10-02T18:30")
    text = client.get("/plans/month?month=2026-10").text
    assert "October 2026" in text
    assert text.count("Camping") == 6  # three days in the grid, and the same three as a list
    assert '<time datetime="2026-10-02">' in text and "18:30" in text
    assert "month=2026-09" in text and "month=2026-11" in text  # earlier and later


def test_the_month_is_this_one_by_default_and_marks_today(google) -> None:
    _, client, _ = google
    text = client.get("/plans/month").text
    assert "September 2026" in text and 'class=" today"' in text  # the 20th, in the grid
    assert "This month" not in text  # already on it


@pytest.mark.parametrize("asked", ["2026-13", "soon", "1900-01", "2026-9-1"])
def test_a_month_that_is_not_one_is_not_found(google, asked) -> None:
    _, client, _ = google
    assert client.get(f"/plans/month?month={asked}").status_code == 404


def test_the_phone_list_says_when_a_month_is_empty(google) -> None:
    _, client, _ = google
    assert "Nothing on in March 2027." in client.get("/plans/month?month=2027-03").text


def test_an_entry_knows_its_days() -> None:
    from familydb.agenda import Entry

    def entry(start, end, all_day):
        return Entry("x", start, end, all_day, None, None, "confirmed", None, None)

    assert entry("2026-10-02", "2026-10-04", True).days() == [
        date(2026, 10, 2),
        date(2026, 10, 3),
        date(2026, 10, 4),
    ]
    late = entry("2026-10-02T22:00-07:00", "2026-10-03T00:00-07:00", False)
    assert late.days() == [date(2026, 10, 2)]  # ending at midnight is not a day of its own
    assert entry("2026-10-02T09:00-07:00", None, False).days() == [date(2026, 10, 2)]
