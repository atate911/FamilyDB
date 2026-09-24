"""The home page: what is coming up, what was added lately, and one tap to ask or add."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from familydb.app import App
from familydb.store import db, ideas
from familydb.web import create_app, views
from familydb.web.agenda import Entry
from tests import fakes

TZ = ZoneInfo("America/Vancouver")


def _home(app_settings, clock, calendar=None):
    return create_app(App(app_settings, clock, calendar=calendar)).test_client()


def test_home_puts_what_is_coming_up_before_everything_else(calendar_settings, clock, conn):
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


def test_home_shows_the_newest_ideas_and_counts_them(settings, clock, conn) -> None:
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


def test_the_radar_puts_sooner_plans_nearer_the_middle() -> None:
    assert [views.radar_distance(days) for days in (-2, 0, 7, 14, 28, 60)] == [
        12,
        12,
        33,
        66,
        92,
        92,
    ]
    today = date(2026, 9, 20)
    plans = [
        Entry(
            f"Plan {n}",
            (today + timedelta(days=away)).isoformat(),
            None,
            True,
            None,
            None,
            "confirmed",
            n,
            None,
        )
        for n, away in enumerate((1, 1, 6, 13, 40))  # two on one day
    ]
    blips = views.radar_blips(plans, today)
    assert [blip["next"] for blip in blips] == [True, False, False, False, False]
    assert len({blip["bearing"] for blip in blips}) == len(blips)  # never one on top of another
    reach = [round(math.dist((100, 100), (blip["x"], blip["y"]))) for blip in blips]
    assert reach == sorted(reach) and reach[-1] <= 92  # later is further out, and inside the dial


def test_home_draws_what_is_coming_on_a_radar_beside_the_next(calendar_settings, clock, conn):
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 22, 17, tzinfo=TZ),
        datetime(2026, 9, 22, 18, tzinfo=TZ),
    )
    calendar.seed(
        "Pumpkin patch", datetime(2026, 10, 3, 10, tzinfo=TZ), datetime(2026, 10, 3, 13, tzinfo=TZ)
    )
    text = _home(calendar_settings, clock, calendar).get("/").text
    assert '<div class="radar" aria-hidden="true">' in text  # a picture of what the words say
    assert text.count('<g class="blip ') == 2 and '<g class="blip b7 next">' in text
    assert "Soccer practice" in text and "1 more on the radar" in text


def test_an_empty_radar_says_so_in_words(settings, clock, conn) -> None:
    text = _home(settings, clock).get("/").text
    assert '<div class="radar" aria-hidden="true">' in text and '<g class="blip' not in text
    assert "Nothing on the radar yet." in text
