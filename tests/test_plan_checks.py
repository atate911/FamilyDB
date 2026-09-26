"""The evening before a plan, its weather and place's hours are checked (plan_checks.py)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from familydb.app import App
from familydb.clock import FixedClock
from familydb.integrations.open_meteo import DayForecast
from familydb.jobs.catch_up import run_catch_up
from familydb.jobs.plan_checks import run_plan_checks
from familydb.store import db, ideas, places, plans
from familydb.tools.places import DAYS
from tests import fakes
from tests.conftest import NOW_ISO, TZ

FRIDAY_EVENING = datetime(2026, 9, 25, 19, 0, tzinfo=TZ)
SATURDAY = date(2026, 9, 26)
WET = DayForecast(SATURDAY, 61, "Light rain", 14.0, 8.0, 80, 6.5)
DRY = DayForecast(SATURDAY, 1, "Mainly clear", 19.0, 9.0, 5, 0.0)
EVERY_DAY = {day: [{"open": "10:00", "close": "22:00"}] for day in DAYS}


def _idea(conn, title, *, hours=None, **fields):
    with db.transaction(conn):
        idea = ideas.insert(conn, title=title, kind="outing", now=NOW_ISO, **fields)
        if hours is not None:
            place = places.insert(
                conn,
                name=title,
                now=NOW_ISO,
                last_checked_at=NOW_ISO,
                hours=hours,
                travel_minutes=10,
                travel_km=8.0,
            )
            ideas.update(conn, idea.id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)
    return ideas.get(conn, idea.id)


def _plan(conn, idea, start="2026-09-26T10:00", end="2026-09-26T12:00", **fields):
    with db.transaction(conn):
        plan = plans.insert(
            conn,
            title=idea.title,
            start=start,
            end=end,
            all_day=len(start) == 10,
            idea_id=idea.id,
            channel=fields.pop("channel", "web"),
            chat_id=fields.pop("chat_id", "web"),
            now=NOW_ISO,
            **fields,
        )
        ideas.update(conn, idea.id, {"status": "planned"}, now=NOW_ISO)
    return plan


def _app(settings, *, weather=(WET,), at=FRIDAY_EVENING, **changes):
    forecast = fakes.FakeForecast(list(weather)) if weather is not None else None
    app = App(settings.model_copy(update=changes), FixedClock(at, TZ), weather=forecast)
    said: list[str] = []
    app.senders["web"] = lambda chat, text: said.append(text)
    return app, said


def test_rain_for_an_outdoor_plan_comes_with_an_indoor_backup(settings, conn, family) -> None:
    hike = _idea(conn, "The falls hike", setting="outdoor", duration_min=120)
    cafe = _idea(conn, "Board game cafe", setting="indoor", duration_min=90, hours=EVERY_DAY)
    _idea(conn, "Kite flying", setting="outdoor", duration_min=60, hours=EVERY_DAY)
    _plan(conn, hike)
    app, said = _app(settings)
    assert run_plan_checks(app) == 1
    heads_up, backup = said[0].split("\n")
    assert heads_up == (
        f"Heads-up for tomorrow: 80% chance of rain for #{hike.id} The falls hike, "
        "and it's an outdoor one."
    )
    assert backup == (
        f"If you'd rather switch: #{cafe.id} Board game cafe, open Saturday 10:00-22:00, "
        "about 10 min drive (estimate)."
    )
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0
    assert run_plan_checks(app) == 0  # once


def test_a_dry_evening_before_says_nothing(settings, conn, family) -> None:
    plan = _plan(conn, _idea(conn, "The falls hike", setting="outdoor"))
    app, said = _app(settings, weather=(DRY,))
    assert run_plan_checks(app) == 0
    assert said == []
    assert plans.get(conn, plan.id).checked_at is not None  # checked, and not again


def test_a_place_listed_as_closed_then(settings, conn, family) -> None:
    evenings = {day: [{"open": "17:00", "close": "22:00"}] for day in ("fri", "sat")}
    ramen = _idea(conn, "Ramen Ichiban", setting="indoor", hours=evenings)
    closed = _idea(conn, "Pottery studio", setting="indoor", hours={"sat": [], "sun": []})
    fine = _idea(conn, "Cinema", setting="indoor", hours=EVERY_DAY)
    bowling = _idea(conn, "Bowling", setting="indoor", duration_min=60, hours=EVERY_DAY)
    _plan(conn, ramen, "2026-09-26T12:00", "2026-09-26T14:00")
    _plan(conn, closed, "2026-09-26T14:00", "2026-09-26T16:00")
    _plan(conn, fine, "2026-09-26T19:00", None)
    app, said = _app(settings, weather=None)
    assert run_plan_checks(app) == 2
    assert said[0].split("\n")[0] == (
        f"Heads-up for tomorrow's #{ramen.id} Ramen Ichiban: Ramen Ichiban is listed as open "
        "17:00-22:00 on Saturdays, as far as I know. Worth a quick check."
    )
    closed_heads_up = said[1].split("\n")[0]
    assert closed_heads_up.endswith(
        "Pottery studio is listed as closed on Saturdays, as far as I know. Worth a quick check."
    )
    assert said[0].split("\n")[1].startswith(f"If you'd rather switch: #{bowling.id} Bowling")
    assert not any("Cinema" in text for text in said)  # open then, and planned, so neither


def test_what_is_not_checked(settings, conn, family) -> None:
    hike = _idea(conn, "The falls hike", setting="outdoor")
    cancelled = _plan(conn, hike)
    with db.transaction(conn):
        conn.execute("UPDATE plans SET status = 'cancelled' WHERE id = ?", (cancelled.id,))
    _plan(conn, _idea(conn, "Beach day", setting="outdoor"), "2026-09-27T10:00")  # Sunday's
    _plan(conn, _idea(conn, "Picnic", setting="outdoor"), channel="telegram", chat_id="42")
    app, said = _app(settings)
    assert run_plan_checks(app) == 0  # nothing here can send to Telegram
    assert said == []
    app, said = _app(settings, plan_checks=False)
    app.senders["telegram"] = lambda chat, text: said.append(text)
    assert run_plan_checks(app) == 0
    assert said == []


def test_after_a_restart_past_the_hour_it_still_checks(settings, conn, family) -> None:
    _plan(conn, _idea(conn, "The falls hike", setting="outdoor"))
    app, said = _app(settings, at=FRIDAY_EVENING - timedelta(hours=3))
    assert "plan_checks" not in run_catch_up(app)  # before the hour: tomorrow waits
    app, said = _app(settings, at=FRIDAY_EVENING + timedelta(hours=2))
    assert run_catch_up(app)["plan_checks"] == 1
    assert said[0].startswith("Heads-up for tomorrow")
