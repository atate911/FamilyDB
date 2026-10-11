"""Her picks for Now, made ahead by code (familydb/picks.py, store/picks.py, jobs/picks.py): one
a kind for the moment, each with its reason; made when due and never by a page view; never a
model call, never logged as a suggestion."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from familydb import picks
from familydb.app import App
from familydb.integrations.open_meteo import DayForecast
from familydb.jobs.catch_up import run_catch_up
from familydb.jobs.picks import run_picks
from familydb.store import db, ideas, places, suggestions
from familydb.store import picks as pick_store
from tests import fakes
from tests.conftest import NOW_ISO


@pytest.fixture
def app(env):
    """Thursday evening with a dry weekend forecast and the fake calendar, no network."""
    dry = [
        DayForecast(date(2026, 9, 24 + n), 1, "Mainly clear", 20.0, 9.0, 5, 0.0) for n in range(5)
    ]
    return App(env.settings, clock=env.app.clock, calendar=env.cal, weather=fakes.FakeForecast(dry))


def _seed(conn) -> dict[str, int]:
    with db.transaction(conn):
        ramen = ideas.insert(conn, title="Kenji\u2019s Ramen", kind="restaurant", now=NOW_ISO)
        spot = places.insert(
            conn,
            name="Kenji\u2019s Ramen",
            now=NOW_ISO,
            lat=45.52,
            lon=-122.68,
            hours={day: [{"open": "11:00", "close": "21:00"}] for day in ("fri", "sat", "sun")},
        )
        ideas.update(conn, ramen.id, {"place_id": spot.id, "enrichment": "done"}, now=NOW_ISO)
        park = ideas.insert(
            conn, title="Sky High Trampolines", kind="outing", setting="indoor", now=NOW_ISO
        )
        kites = ideas.insert(
            conn, title="Kites on the butte", kind="day_trip", setting="outdoor", now=NOW_ISO
        )
        games = ideas.insert(conn, title="Board game night", kind="home", now=NOW_ISO)
        ideas.insert(conn, title="Another ramen", kind="restaurant", now=NOW_ISO)
    return {"ramen": ramen.id, "park": park.id, "kites": kites.id, "games": games.id}


def test_a_set_is_one_pick_a_kind_with_its_reason_and_the_days_line(env, app) -> None:
    seeded = _seed(env.conn)
    made = picks.make(app, env.conn, "weekend")
    assert made is not None and made.window == "weekend" and made.member_id is None
    assert (made.window_start, made.window_end) == ("2026-09-26", "2026-09-27")
    kinds = [tile["kind"] for tile in made.picks]
    # One a kind, in the engine's order: the board game night is good (nothing to look up), the
    # rest possible until their lookups (suggest/evaluate.py).
    assert kinds == ["Stay in", "Eat", "Go out", "Day trip"]
    assert len({tile["title"] for tile in made.picks}) == 4
    ramen = next(tile for tile in made.picks if tile["idea_id"] == seeded["ramen"])
    assert ramen["when"] in ("Sat", "Sun", "Sat or Sun")
    assert (
        ramen["why"].startswith("Open till 9\u00a0pm") and "you haven\u2019t been" in ramen["why"]
    )
    assert "details" not in ramen["why"]  # the engine's own words never reach a tile
    assert (
        made.header == "Saturday: mainly clear, free all day · Sunday: mainly clear, free all day"
    )
    kites = next(tile for tile in made.picks if tile["idea_id"] == seeded["kites"])
    assert kites["why"].endswith("and it\u2019s dry")
    assert pick_store.current(env.conn, today="2026-09-24") == made
    assert suggestions.list_recent(env.conn, limit=5) == []  # never logged as suggested


def test_a_set_for_now_looks_at_the_next_hours(env, app) -> None:
    _seed(env.conn)
    made = picks.make(app, env.conn, "now")
    assert made is not None and made.window_start == made.window_end == "2026-09-24"
    assert all(tile["when"] == "tonight" for tile in made.picks)  # asked at 6 pm
    assert len(made.picks) <= picks.MOST["now"]


def test_the_job_makes_what_is_due_and_then_sits_idle(env, app, family) -> None:
    _seed(env.conn)
    assert run_picks(app) == {"now": 1, "weekend": 2}  # the family's, and the girls' own
    assert pick_store.latest(env.conn, window="weekend", member_id=family["girls"].id) is not None
    assert run_picks(app) == {"now": 0, "weekend": 0}  # all fresh
    app.clock.advance(timedelta(hours=3, minutes=1))
    assert run_picks(app) == {"now": 1, "weekend": 0}  # the next hours have moved on
    assert env.conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


def test_the_now_set_is_left_alone_at_night_and_off_makes_none(env, app) -> None:
    app.clock.advance(timedelta(hours=6))  # midnight
    assert picks.due(app, env.conn, "now") is False
    assert picks.due(app, env.conn, "weekend") is True
    quiet = App(env.settings.model_copy(update={"picks": False}), app.clock)
    assert run_picks(quiet) == {"now": 0, "weekend": 0}


def test_the_catch_up_on_start_makes_the_picks(env, app) -> None:
    _seed(env.conn)
    result = run_catch_up(app)
    assert result["picks"]["weekend"] >= 1
    assert env.conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


def test_the_stronger_calls_picks_lead_the_weekend_while_fresh(env, app) -> None:
    seeded = _seed(env.conn)
    with db.transaction(env.conn):
        row = suggestions.insert(
            conn=env.conn,
            asked_by=None,
            window_start="2026-09-26",
            window_end="2026-09-27",
            candidates=[],
            web_finds=[],
            now="2026-09-24T01:00:00Z",
        )
        suggestions.set_picks(
            env.conn,
            row.id,
            {
                "picks": [
                    {
                        "ref": f"idea:{seeded['games']}",
                        "idea_id": seeded["games"],
                        "title": "Board game night",
                        "slot": "favorite",
                        "reason": "rain is forecast, and you loved it",
                    }
                ]
            },
        )
    made = picks.make(app, env.conn, "weekend")
    assert made is not None and made.source == "chosen"
    assert made.picks[0]["title"] == "Board game night"
    assert made.picks[0]["why"] == "Rain is forecast, and you loved it"


def test_old_sets_are_pruned_but_the_newest_of_each_stays(env, app) -> None:
    with db.transaction(env.conn):
        for day in ("2026-09-10", "2026-09-12"):
            pick_store.insert(
                env.conn,
                member_id=None,
                window="now",
                window_start=day,
                window_end=day,
                header=None,
                picks=[],
                made_at=f"{day}T10:00:00Z",
                stale_at=f"{day}T13:00:00Z",
            )
    run_picks(app)
    kept = [
        row[0]
        for row in env.conn.execute(
            "SELECT made_at FROM pick_sets WHERE window = 'now' ORDER BY id"
        )
    ]
    assert kept[0].startswith("2026-09-25T01")  # tonight, in UTC; the two old ones are gone
    assert len(kept) == 1


def test_a_listed_find_fills_a_spare_tile_and_leads_to_its_page(env, app) -> None:
    """With fewer kinds of idea than tiles, one of what the sources list for the weekend goes on
    the last tile, carrying the stored find's id for Now to link to (web/now.py); the rest are on
    Happening soon."""
    from datetime import datetime

    from familydb.integrations.events import FoundEvent
    from familydb.store import finds
    from tests.conftest import TZ

    _seed(env.conn)
    with db.transaction(env.conn):
        finds.upsert_many(
            env.conn,
            "feed:https://library.example.org/events.ics",
            "feed",
            [
                FoundEvent(
                    external_id=f"e{n}",
                    title=title,
                    starts=datetime(2026, 9, 26, 10 + n, tzinfo=TZ),
                    ends=None,
                    all_day=False,
                    venue="Main library",
                    url=f"https://library.example.org/e{n}",
                )
                for n, title in enumerate(("Puppet show", "Lego club"))
            ],
            tz=TZ,
            now=NOW_ISO,
        )
    made = picks.make(app, env.conn, "weekend")
    assert made is not None
    (tile,) = [tile for tile in made.picks if tile["kind"] == picks.FOUND]
    (puppets,) = [
        f
        for f in finds.upcoming(env.conn, start=date(2026, 9, 26), end=date(2026, 9, 27), limit=9)
        if f.title == "Puppet show"
    ]
    assert tile["title"] == "Puppet show" and tile["find_id"] == puppets.id
    assert tile["idea_id"] is None and tile["url"] == "https://library.example.org/e0"


def test_what_was_done_lately_is_never_on_a_tile(env, app) -> None:
    """Resting is said in a chat answer and left to the family; a pick made ahead is a nudge, so
    it never offers what they did last weekend."""
    with db.transaction(env.conn):
        show = ideas.insert(conn=env.conn, title="Puppet theatre", kind="show", now=NOW_ISO)
        ideas.apply_outcome(
            env.conn, show.id, happened_on="2026-09-21", avg_rating=9.0, now=NOW_ISO
        )
    made = picks.make(app, env.conn, "weekend")
    assert made is not None
    assert all(tile["idea_id"] != show.id for tile in made.picks)


def _listed(conn, *titles):
    """What a library calendar lists for Saturday, as stored finds, by title."""
    from datetime import datetime

    from familydb.integrations.events import FoundEvent
    from familydb.store import finds
    from tests.conftest import TZ

    with db.transaction(conn):
        finds.upsert_many(
            conn,
            "feed:https://library.example.org/events.ics",
            "feed",
            [
                FoundEvent(
                    external_id=f"e{n}",
                    title=title,
                    starts=datetime(2026, 9, 26, 10 + n, tzinfo=TZ),
                    ends=None,
                    all_day=False,
                    venue="Main library",
                    url=f"https://library.example.org/e{n}",
                )
                for n, title in enumerate(titles)
            ],
            tz=TZ,
            now=NOW_ISO,
        )
    found = finds.upcoming(conn, start=date(2026, 9, 26), end=date(2026, 9, 27), limit=9)
    return {f.title: f.id for f in found}


def test_a_find_already_saved_is_never_the_new_tile(env, app) -> None:
    """Saved as an idea, a find is theirs: it is not offered as new again, even while that idea
    is ruled out (here, already planned)."""
    _seed(env.conn)
    _listed(env.conn, "Puppet show", "Lego club")
    with db.transaction(env.conn):
        ideas.insert(env.conn, title="Puppet show", kind="show", status="planned", now=NOW_ISO)
    made = picks.make(app, env.conn, "weekend")
    found = [tile["title"] for tile in made.picks if tile["kind"] == picks.FOUND]
    assert found == ["Lego club"]


def test_a_find_the_stronger_call_picked_is_the_find_tile(env, app) -> None:
    _seed(env.conn)
    ids = _listed(env.conn, "Puppet show", "Lego club")
    with db.transaction(env.conn):
        row = suggestions.insert(
            conn=env.conn,
            asked_by=None,
            window_start="2026-09-26",
            window_end="2026-09-27",
            candidates=[],
            web_finds=[],
            now="2026-09-24T01:00:00Z",
        )
        suggestions.set_picks(
            env.conn,
            row.id,
            {
                "picks": [
                    {
                        "ref": "find:2",
                        "find_id": ids["Lego club"],
                        "title": "Lego club",
                        "slot": "new",
                        "reason": "Theo has been building all week",
                    }
                ]
            },
        )
    made = picks.make(app, env.conn, "weekend")
    (tile,) = [tile for tile in made.picks if tile["kind"] == picks.FOUND]
    assert tile["title"] == "Lego club" and tile["find_id"] == ids["Lego club"]
    assert tile["why"] == "Theo has been building all week"


def test_a_kid_s_set_holds_two_and_nothing_for_grown_ups_only(env, app, family) -> None:
    """docs/INTERFACE.md section 9: a kid's Now holds at most two picks, and never a date
    night."""
    _seed(env.conn)
    with db.transaction(env.conn):
        bar = ideas.insert(
            env.conn,
            title="Wine tasting",
            kind="activity",
            participants=["Sam", "Alex"],
            setting="indoor",
            now=NOW_ISO,
        )
    made = picks.make(app, env.conn, "weekend", member=family["girls"])
    assert made is not None and 1 <= len(made.picks) <= picks.KID_MOST
    family_set = picks.make(app, env.conn, "weekend")
    assert bar.id in [tile["idea_id"] for tile in family_set.picks]  # the grown-ups see it
    assert all(tile["idea_id"] != bar.id for tile in made.picks)
