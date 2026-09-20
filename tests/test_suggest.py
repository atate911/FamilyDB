import json
from datetime import date, datetime

from familydb.integrations.open_meteo import DayForecast
from familydb.store import db, ideas, places, suggestions
from familydb.suggest.context import build_context
from familydb.suggest.engine import resolve_window
from familydb.suggest.evaluate import overlap_minutes
from familydb.suggest.shortlist import longest_free_span, participants_match, shortlist
from familydb.suggest.types import Constraints, SuggestInput
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO, TZ

SAT = date(2026, 9, 26)
SUN = date(2026, 9, 27)
DRY_SAT = DayForecast(SAT, 1, "mainly clear", 19.0, 9.0, 5, 0.0)
WET_SUN = DayForecast(SUN, 61, "light rain", 14.0, 8.0, 80, 6.5)


def _ctx(conn, settings, clock, family, *, calendar=None, weather=None, member=True) -> ToolContext:
    return ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=family["sam"] if member else None,
        calendar=calendar,
        weather=weather,
    )


def _idea(conn, title, **fields):
    with db.transaction(conn):
        return ideas.insert(
            conn, title=title, kind=fields.pop("kind", "activity"), now=NOW_ISO, **fields
        )


def _weekend_ctx(conn, full_settings, thursday_clock, family, *, busy_saturday_morning=False):
    calendar = fakes.FakeCalendar(TZ)
    if busy_saturday_morning:
        calendar.seed(
            "Dentist", datetime(2026, 9, 26, 9, tzinfo=TZ), datetime(2026, 9, 26, 11, tzinfo=TZ)
        )
    weather = fakes.FakeForecast([DRY_SAT, WET_SUN])
    return _ctx(conn, full_settings, thursday_clock, family, calendar=calendar, weather=weather)


def test_resolve_window(thursday_clock) -> None:
    today = thursday_clock.today()
    window, label = resolve_window(SuggestInput(window="this_weekend", question="?"), today)
    assert window == (SAT, SUN) and label.startswith("this weekend (Sat 26 to Sun 27 Sep)")
    window, label = resolve_window(SuggestInput(window="next_weekend", question="?"), today)
    assert window == (date(2026, 10, 3), date(2026, 10, 4)) and label.startswith("next weekend")
    window, label = resolve_window(SuggestInput(window="someday", question="?"), today)
    assert window is None and label == "someday"
    window, _ = resolve_window(
        SuggestInput(window="dates", start="2026-10-10", end="2026-10-11", question="?"), today
    )
    assert window == (date(2026, 10, 10), date(2026, 10, 11))


def test_context_reports_missing_services(conn, settings, thursday_clock, family) -> None:
    context = build_context(_ctx(conn, settings, thursday_clock, family), (SAT, SUN))
    assert context.skipped == ["calendar not connected", "weather not configured"]
    assert [d.free for d in context.days] == [["morning", "afternoon", "evening"]] * 2
    assert context.days[0].free_known is False and context.season == "autumn"


def test_context_with_calendar_and_forecast(conn, full_settings, thursday_clock, family) -> None:
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family, busy_saturday_morning=True)
    context = build_context(ctx, (SAT, SUN))
    assert context.skipped == []
    assert context.days[0].free == ["afternoon", "evening"] and context.days[0].free_known
    assert context.days[1].forecast.rain_chance == 80


def test_free_span_and_participants() -> None:
    assert longest_free_span(["morning", "afternoon", "evening"]) == 840
    assert longest_free_span(["morning", "evening"]) == 300
    assert longest_free_span([]) == 0
    from familydb.store.ideas import Idea

    def idea(participants):
        return Idea(
            id=1, kind="x", title="t", participants=participants, created_at="", updated_at=""
        )

    assert participants_match(idea([]), ["with the girls"])
    assert participants_match(idea(["whole family"]), ["adults"])
    assert participants_match(idea(["with the girls"]), ["the girls"])
    assert not participants_match(idea(["adults only"]), ["with the girls"])


def test_shortlist_rules(conn, full_settings, thursday_clock, family) -> None:
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family, busy_saturday_morning=True)
    context = build_context(ctx, (SAT, SUN))
    planned = _idea(conn, "Planned thing", status="planned")
    recent = _idea(conn, "Done last week", status="done", duration_min=60)
    with db.transaction(conn):
        ideas.apply_outcome(conn, recent.id, happened_on="2026-09-19", avg_rating=8.0, now=NOW_ISO)
    bad = _idea(conn, "Bad restaurant", kind="restaurant", status="done")
    with db.transaction(conn):
        ideas.apply_outcome(conn, bad.id, happened_on="2026-01-10", avg_rating=3.0, now=NOW_ISO)
    adults = _idea(conn, "Wine bar", participants=["adults only"])
    winter = _idea(conn, "Ski day", seasons=["winter"])
    hike = _idea(conn, "The falls hike", setting="outdoor", duration_min=180)
    long_day = _idea(conn, "Day at the coast", kind="day_trip")
    cafe = _idea(conn, "Board game cafe", setting="indoor", duration_min=120, cost_level=1)
    pricey = _idea(conn, "Fancy dinner", kind="restaurant", cost_level=4)
    kept, ruled_out, extras = shortlist(
        ideas.list_all(conn),
        context,
        Constraints(participants=["with the girls"], max_cost_level=2),
        full_settings,
    )
    reasons = {c.idea_id: c.reasons[0] for c in ruled_out}
    assert reasons[planned.id] == "already planned"
    assert reasons[recent.id] == "done 1 week ago"
    assert reasons[bad.id] == "rated 3/10 last time"
    assert reasons[adults.id] == "for adults only"
    assert reasons[winter.id] == "for winter"
    assert reasons[pricey.id] == "over the budget asked for"
    kept_ids = {s.idea.id: s for s in kept}
    assert set(kept_ids) == {hike.id, cafe.id, long_day.id}
    # Sunday is wet, so the hike only fits Saturday; the day trip needs a whole free day and
    # Saturday morning is busy, so it only fits Sunday (rain only matters outdoors).
    assert kept_ids[hike.id].fits_days == [SAT] and kept_ids[hike.id].weather == "ok"
    assert kept_ids[long_day.id].fits_days == [SUN]
    assert kept_ids[cafe.id].fits_days == [SAT, SUN]
    assert extras == []


def test_shortlist_duration_and_weather_reasons(
    conn, full_settings, thursday_clock, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    for day in (26, 27):
        calendar.seed(
            "Busy", datetime(2026, 9, day, 8, tzinfo=TZ), datetime(2026, 9, day, 17, tzinfo=TZ)
        )
    weather = fakes.FakeForecast([WET_SUN, DayForecast(SAT, 63, "rain", 12.0, 7.0, 90, 12.0)])
    ctx = _ctx(conn, full_settings, thursday_clock, family, calendar=calendar, weather=weather)
    context = build_context(ctx, (SAT, SUN))
    hike = _idea(conn, "The falls hike", setting="outdoor", duration_min=180)
    long_indoor = _idea(conn, "Museum marathon", setting="indoor", duration_min=420)
    kept, ruled_out, _ = shortlist(ideas.list_all(conn), context, Constraints(), full_settings)
    reasons = {c.idea_id: c.reasons[0] for c in ruled_out}
    assert reasons[hike.id].startswith("rain likely Saturday (90%); rain likely Sunday (80%)")
    assert reasons[long_indoor.id] == "needs about 7 h, only 5 h free"
    assert kept == []


def test_someday_skips_window_rules(conn, settings, thursday_clock, family) -> None:
    context = build_context(_ctx(conn, settings, thursday_clock, family), None)
    hike = _idea(conn, "The falls hike", setting="outdoor", duration_min=600)
    kept, ruled_out, _ = shortlist(ideas.list_all(conn), context, Constraints(), settings)
    assert [s.idea.id for s in kept] == [hike.id] and kept[0].fits_days == [] and ruled_out == []


def test_overlap_minutes() -> None:
    ranges = [{"open": "10:00", "close": "20:00"}]
    assert overlap_minutes(ranges, ["morning", "afternoon", "evening"]) == 600
    assert overlap_minutes(ranges, ["morning"]) == 120
    assert overlap_minutes([{"open": "21:00", "close": "02:00"}], ["evening"]) == 60
    assert overlap_minutes(ranges, []) == 0


def _seed_place(conn, idea, **fields):
    with db.transaction(conn):
        place = places.insert(
            conn,
            name=idea.title,
            now=NOW_ISO,
            last_checked_at=NOW_ISO.replace("20T", "24T"),
            **fields,
        )
        ideas.update(conn, idea.id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)
    return place


def _suggest(registry, ctx, **overrides):
    payload = {
        "window": "this_weekend",
        "question": "what should we do this weekend?",
        "discover": False,
        **overrides,
    }
    result = registry.dispatch("suggest", payload, ctx)
    return result, json.loads(result.content)


def test_suggest_end_to_end_with_verdicts(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family, busy_saturday_morning=True)
    hopscotch = _idea(
        conn, "Hopscotch Portland", kind="outing", participants=["with the girls"], duration_min=120
    )
    _seed_place(
        conn,
        hopscotch,
        hours={
            "sat": [{"open": "10:00", "close": "20:00"}],
            "sun": [{"open": "10:00", "close": "18:00"}],
        },
        travel_minutes=40,
        travel_km=45.0,
    )
    ramen = _idea(conn, "Ramen place", kind="restaurant", duration_min=60)
    _seed_place(conn, ramen, hours={"sat": [], "sun": []})
    hike = _idea(conn, "The falls hike", setting="outdoor", duration_min=180)  # no place details
    show = _idea(conn, "Big concert", kind="show", needs_booking=True, lead_time_days=10)
    _seed_place(
        conn,
        show,
        hours={"sat": [{"open": "19:00", "close": "23:00"}]},
        booking_url="https://example.com/tix",
    )
    stale = _idea(conn, "Old museum", setting="indoor", duration_min=90)
    with db.transaction(conn):
        old = places.insert(
            conn,
            name="Old museum",
            now=NOW_ISO,
            hours={"sat": [{"open": "10:00", "close": "17:00"}]},
            last_checked_at="2026-01-01T00:00:00Z",
        )
        ideas.update(conn, stale.id, {"place_id": old.id, "enrichment": "done"}, now=NOW_ISO)
    result, data = _suggest(registry, ctx)
    assert not result.is_error, data
    assert data["window"]["start"] == "2026-09-26" and data["window"]["end"] == "2026-09-27"
    assert (
        data["days"][0]["free"] == ["afternoon", "evening"]
        and data["days"][1]["rain_chance_pct"] == 80
    )
    verdicts = {c["idea_id"]: c for c in data["candidates"]}
    assert verdicts[hopscotch.id]["verdict"] == "good"
    assert (
        verdicts[hopscotch.id]["checks"]["open"] == "open"
        and verdicts[hopscotch.id]["checks"]["travel_minutes"] == 40
    )
    assert "about 40 min drive (estimate)" in verdicts[hopscotch.id]["reasons"]
    assert verdicts[ramen.id]["verdict"] == "ruled_out" and verdicts[ramen.id]["reasons"] == [
        "closed Saturday and Sunday"
    ]
    assert verdicts[hike.id]["verdict"] == "possible" and verdicts[hike.id]["reasons"][
        0
    ].startswith("hours unknown")
    assert verdicts[hike.id]["fits_days"] == ["2026-09-26"]
    assert (
        verdicts[show.id]["verdict"] == "ruled_out"
        and verdicts[show.id]["checks"]["booking"] == "too_late"
    )
    assert (
        verdicts[stale.id]["verdict"] == "possible"
        and verdicts[stale.id]["checks"]["stale"] is True
    )
    assert data["candidates"][0]["idea_id"] == hopscotch.id  # good first
    assert data["skipped_checks"] == []  # discover=False adds nothing; web off note only when asked
    assert data["web_finds"] == []
    row = suggestions.get(conn, data["suggestion"]["id"])
    assert row.window_start == "2026-09-26" and row.asked_by == family["sam"].id
    assert {c["idea_id"] for c in row.candidates} == {
        hopscotch.id,
        ramen.id,
        hike.id,
        show.id,
        stale.id,
    }
    assert result.summary["suggestion_id"] == row.id
    assert ideas.get(conn, stale.id).enrichment == "done"  # web off: no re-queue


def test_suggest_requeues_stale_places_when_web_is_on(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    web_on = full_settings.model_copy(update={"web_tools_enabled": True})
    ctx = _ctx(
        conn,
        web_on,
        thursday_clock,
        family,
        calendar=fakes.FakeCalendar(TZ),
        weather=fakes.FakeForecast([DRY_SAT, WET_SUN]),
    )
    stale = _idea(conn, "Old museum", setting="indoor", duration_min=90)
    with db.transaction(conn):
        old = places.insert(
            conn, name="Old museum", now=NOW_ISO, last_checked_at="2026-01-01T00:00:00Z"
        )
        ideas.update(conn, stale.id, {"place_id": old.id, "enrichment": "done"}, now=NOW_ISO)
    _, data = _suggest(registry, ctx, discover=True)
    assert ideas.get(conn, stale.id).enrichment == "pending"
    assert "stale place details re-queued for a refresh" in data["skipped_checks"]
    assert "web discovery not available yet" in data["skipped_checks"]


def test_suggest_without_services_and_recent_variety(
    registry, conn, settings, thursday_clock, family
) -> None:
    ctx = _ctx(conn, settings, thursday_clock, family)
    first = _idea(conn, "Cafe A", setting="indoor")
    second = _idea(conn, "Cafe B", setting="indoor")
    _, data = _suggest(registry, ctx, discover=True)
    assert data["skipped_checks"] == [
        "calendar not connected",
        "weather not configured",
        "web discovery off",
    ]
    assert all(d["free_known"] is False for d in data["days"])
    assert [c["idea_id"] for c in data["candidates"]] == [first.id, second.id]
    assert all(c["verdict"] == "possible" for c in data["candidates"])  # hours unknown everywhere
    # the second ask sinks what was already suggested as good... both possible, so order holds
    with db.transaction(conn):
        suggestions.insert(
            conn,
            asked_by=None,
            window_start=None,
            window_end=None,
            candidates=[{"idea_id": first.id, "verdict": "good"}],
            web_finds=[],
            now="2026-09-24T00:00:00Z",
        )
    _, data = _suggest(registry, ctx)
    assert [c["idea_id"] for c in data["candidates"]] == [second.id, first.id]


def test_suggest_rejects_bad_dates(registry, conn, settings, thursday_clock, family) -> None:
    ctx = _ctx(conn, settings, thursday_clock, family)
    result, data = _suggest(registry, ctx, window="dates")
    assert result.is_error and "start and end" in data["error"]
    result, data = _suggest(registry, ctx, window="dates", start="2026-10-01", end="2026-11-30")
    assert result.is_error and "two weeks" in data["error"]


def test_pipeline_links_the_suggestion_to_the_reply(settings, thursday_clock, conn, family) -> None:
    from familydb.app import App
    from familydb.channels.console import one_shot

    app = App(settings, thursday_clock)
    _idea(conn, "Cafe A", setting="indoor")
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_s",
                    "suggest",
                    {"window": "this_weekend", "question": "what should we do?", "discover": False},
                )
            ],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("How about Cafe A?")]),
    )
    reply = one_shot(app, "what should we do this weekend?", "Sam", api=api)
    assert reply.status == "ok"
    row = suggestions.list_recent(conn, limit=1)[0]
    assert row.reply_message_id == reply.out_message_id
    assert reply.actions[0]["suggestion_id"] == row.id
