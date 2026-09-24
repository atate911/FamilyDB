"""The home page: what is coming up, what was added lately, and one tap to ask or add."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from familydb.app import App
from familydb.store import db, ideas
from familydb.web import create_app
from tests import fakes

TZ = ZoneInfo("America/Vancouver")


def _home(app_settings, clock, calendar=None):
    return create_app(App(app_settings, clock, calendar=calendar)).test_client()


def test_home_puts_what_is_coming_up_before_everything_else(calendar_settings, clock, conn, family):
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 22, 17, tzinfo=TZ),
        datetime(2026, 9, 22, 18, tzinfo=TZ),
    )
    calendar.seed(  # already over: not coming up
        "Brunch", datetime(2026, 9, 19, 10, tzinfo=TZ), datetime(2026, 9, 19, 11, tzinfo=TZ)
    )
    text = _home(calendar_settings, clock, calendar).get("/").text
    assert "Coming up" in text and "Soccer practice" in text and "Brunch" not in text
    assert text.index("Coming up") < text.index("Lately added")  # first on a phone


def test_home_shows_the_newest_ideas_and_counts_them(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        for number in range(6):
            ideas.insert(
                conn, title=f"Idea {number}", kind="outing", now=f"2026-09-1{number}T12:00:00Z"
            )
        ideas.insert(conn, title="Ramen place", kind="restaurant", now="2026-09-19T12:00:00Z")
    text = _home(settings, clock).get("/").text
    assert "Ramen place" in text and "Idea 5" in text and "Idea 1" not in text  # the four newest
    assert "All 7" in text and "1 restaurant to try" in text


def test_the_old_address_of_a_search_still_finds_it(settings, clock, conn) -> None:
    moved = _home(settings, clock).get("/?q=museum&kind=outing")
    assert moved.status_code == 302 and moved.headers["Location"] == "/ideas?q=museum&kind=outing"


def test_the_weekend_question_is_one_tap_away(settings, clock, conn, family) -> None:
    client = _home(settings, clock)
    text = client.get("/").text
    assert 'href="/chat?ask=What+should+we+do+this+weekend?#latest"' in text
    chat = client.get("/chat?ask=What+should+we+do+this+weekend%3F").text
    assert ">What should we do this weekend?</textarea>" in chat  # waiting, not sent
