import json
from datetime import date, datetime, timedelta

from familydb.integrations.open_meteo import DayForecast
from familydb.store import db, ideas, places, suggestions
from familydb.suggest.context import build_context
from familydb.suggest.discover import DISCOVER_CACHE_SECONDS
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
    today = thursday_clock.now()
    window, label, _ = resolve_window(SuggestInput(window="this_weekend", question="?"), today)
    assert window == (SAT, SUN) and label.startswith("this weekend (Sat 26 to Sun 27 Sep)")
    window, label, _ = resolve_window(SuggestInput(window="next_weekend", question="?"), today)
    assert window == (date(2026, 10, 3), date(2026, 10, 4)) and label.startswith("next weekend")
    window, label, _ = resolve_window(SuggestInput(window="someday", question="?"), today)
    assert window is None and label == "someday"
    window, _, _ = resolve_window(
        SuggestInput(window="dates", start="2026-10-10", end="2026-10-11", question="?"), today
    )
    assert window == (date(2026, 10, 10), date(2026, 10, 11))


def test_resolve_window_on_a_sunday(clock) -> None:
    now = clock.now()  # Sunday 20 September, 14:03
    today = now.date()
    window, label, bounds = resolve_window(SuggestInput(window="this_weekend", question="?"), now)
    assert window == (today, today) and label == "this weekend (Sun 20 Sep)"
    # Asked at 14:03 on the day itself: the morning has gone.
    assert bounds.for_day(today, today, today) == (14 * 60 + 5, 22 * 60)
    window, label, _ = resolve_window(SuggestInput(window="next_weekend", question="?"), now)
    assert window == (SAT, SUN) and label == "next weekend (Sat 26 to Sun 27 Sep)"


def test_context_reports_missing_services(conn, settings, thursday_clock, family) -> None:
    context = build_context(_ctx(conn, settings, thursday_clock, family), (SAT, SUN))
    assert context.skipped == ["calendar not connected", "weather not configured"]
    assert [d.spans for d in context.days] == [[(8 * 60, 22 * 60)]] * 2
    assert context.days[0].free_known is False and context.season == "autumn"


def test_context_with_calendar_and_forecast(conn, full_settings, thursday_clock, family) -> None:
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family, busy_saturday_morning=True)
    context = build_context(ctx, (SAT, SUN))
    assert context.skipped == []
    assert context.days[0].spans == [(8 * 60, 9 * 60), (11 * 60, 22 * 60)]
    assert context.days[0].free_known
    assert context.days[1].forecast.rain_chance == 80


def test_free_span_and_participants() -> None:
    assert longest_free_span([(480, 1320)]) == 840
    assert longest_free_span([(480, 720), (1020, 1320)]) == 300
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
    assert overlap_minutes(ranges, [(480, 1320)]) == 600
    assert overlap_minutes(ranges, [(480, 720)]) == 120
    assert overlap_minutes([{"open": "21:00", "close": "02:00"}], [(1020, 1320)]) == 60
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
        data["days"][0]["free"] == ["08:00-09:00", "11:00-22:00"]
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
    registry, conn, full_settings, thursday_clock, family, monkeypatch
) -> None:
    from familydb.errors import AgentError

    def unavailable(**kwargs):
        raise AgentError("test worker unavailable", retryable=False)

    monkeypatch.setattr("familydb.suggest.discover.run_worker_turn", unavailable)
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
    assert "web discovery failed: test worker unavailable" in data["skipped_checks"]


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


FIND = {
    "title": "Harvest festival",
    "url": "https://example.com/harvest",
    "dates": "Sat 26 Sep, 10am to 4pm",
    "summary": "Pumpkins, hay rides and food carts.",
}


def _web_ctx(conn, full_settings, thursday_clock, family, api, cache):
    web_on = full_settings.model_copy(update={"web_tools_enabled": True})
    ctx = _ctx(conn, web_on, thursday_clock, family, calendar=fakes.FakeCalendar(TZ))
    ctx.api = api
    ctx.discover_cache = cache
    return ctx


def test_discovery_runs_a_worker_turn_and_caches_the_finds(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    api = fakes.FakeMessagesAPI(*fakes.discover_script([FIND]))
    cache: dict = {}
    ctx = _web_ctx(conn, full_settings, thursday_clock, family, api, cache)
    _idea(conn, "Cafe A", setting="indoor")
    _, data = _suggest(registry, ctx, discover=True)
    assert data["web_finds"] == [{**FIND, "source": "example.com"}]
    assert "web discovery" not in " ".join(data["skipped_checks"])
    request = api.requests[0]
    assert [t["name"] for t in request["tools"]] == ["report_finds", "web_search", "web_fetch"]
    assert request["tools"][1]["max_uses"] == 4
    assert request["tools"][1]["user_location"]["city"] == "Vancouver"
    asked = request["messages"][0]["content"][1]["text"]
    assert "Window: Saturday 26 September to Sunday 27 September 2026." in asked
    # The wording is not sent: the same window and constraints are the same search.
    assert "Home area: Vancouver, WA." in asked and "what should we do" not in asked
    assert len(cache) == 1
    # The suggestions log carries the finds too.
    row = suggestions.list_recent(conn, limit=1)[0]
    assert row.web_finds[0]["url"] == FIND["url"]

    # Asking again inside the cache window makes no request at all.
    _, again = _suggest(registry, ctx, discover=True)
    assert again["web_finds"] == data["web_finds"] and len(api.requests) == 2

    # A different window is a different key; an expired key is searched again.
    api.queue.extend(fakes.discover_script([]))
    _, other = _suggest(registry, ctx, discover=True, window="next_weekend")
    assert other["web_finds"] == [] and len(cache) == 2
    thursday_clock.advance(timedelta(seconds=DISCOVER_CACHE_SECONDS + 1))
    api.queue.extend(fakes.discover_script([FIND]))
    _, refreshed = _suggest(registry, ctx, discover=True)
    assert len(refreshed["web_finds"]) == 1 and len(api.requests) == 6


def test_discovery_failures_become_notes_and_are_not_cached(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    cache: dict = {}
    api = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    ctx = _web_ctx(conn, full_settings, thursday_clock, family, api, cache)
    _, data = _suggest(registry, ctx, discover=True)
    assert data["web_finds"] == [] and cache == {}
    assert any(n.startswith("web discovery failed:") for n in data["skipped_checks"])

    # A worker that never hands back is a failure too, so the next ask tries again.
    api.queue.append(fakes.message([fakes.text("Nothing found.")]))
    _, data = _suggest(registry, ctx, discover=True)
    assert "web discovery failed: worker ended without reporting" in data["skipped_checks"]
    assert cache == {}

    api.queue.extend(fakes.discover_script([FIND]))
    _, data = _suggest(registry, ctx, discover=True)
    assert len(data["web_finds"]) == 1 and len(cache) == 1

    # discover=False never touches the web, even with a warm cache.
    _, data = _suggest(registry, ctx, discover=False)
    assert data["web_finds"] == [] and data["skipped_checks"] == ["weather not configured"]


def test_discovery_request_for_someday(conn, settings, thursday_clock, family) -> None:
    from familydb.suggest.discover import cache_key, render_discover_request

    context = build_context(_ctx(conn, settings, thursday_clock, family), None)
    text = render_discover_request(context, Constraints(), settings)
    assert "Window: no fixed dates; look at the next four weeks or so." in text
    assert "Home area: not set." in text and "asked" not in text
    assert cache_key(None) == "someday" and cache_key((SAT, SAT)) == "2026-09-26:2026-09-26"


def test_discovery_crash_is_a_note_and_not_cached(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    cache: dict = {}
    api = fakes.FakeMessagesAPI(RuntimeError("boom"))
    ctx = _web_ctx(conn, full_settings, thursday_clock, family, api, cache)
    result, data = _suggest(registry, ctx, discover=True)
    assert not result.is_error
    assert "web discovery failed: RuntimeError: boom" in data["skipped_checks"]
    assert data["web_finds"] == [] and cache == {}


class _BrokenCalendar:
    def list_events(self, start, end):
        raise OSError("connection reset")


def test_context_survives_a_calendar_transport_error(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    ctx = _ctx(
        conn,
        full_settings,
        thursday_clock,
        family,
        calendar=_BrokenCalendar(),
        weather=fakes.FakeForecast([DRY_SAT, WET_SUN]),
    )
    _idea(conn, "Cafe A", setting="indoor")
    result, data = _suggest(registry, ctx)
    assert not result.is_error
    assert data["skipped_checks"] == ["calendar check failed: connection reset"]
    assert all(d["free_known"] is False and d["free"] == ["08:00-22:00"] for d in data["days"])


def test_the_result_stays_small_however_long_the_list_gets(
    registry, conn, full_settings, thursday_clock, family
) -> None:
    """The result is sent to the model and then sent again with its reply, and is never cached."""
    from familydb.suggest.compose import MAX_OFFERED, MAX_RULED_OUT

    for number in range(60):
        _idea(conn, f"Idea number {number} with a realistic sort of name", setting="indoor")
    for number in range(10):
        _idea(conn, f"Winter thing {number}", seasons=["winter"])  # ruled out: wrong season
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family)
    result, data = _suggest(registry, ctx)
    offered = [c for c in data["candidates"] if c["verdict"] != "ruled_out"]
    rejected = [c for c in data["candidates"] if c["verdict"] == "ruled_out"]
    assert len(offered) == MAX_OFFERED and len(rejected) == MAX_RULED_OUT
    assert data["not_shown"] == (60 - MAX_OFFERED) + (10 - MAX_RULED_OUT)
    assert len(result.content) < 6000, "the result grew; it is paid for twice per question"
    # Nulls are left out, but anything with something to say survives.
    assert "null" not in result.content
    assert all(c["reasons"] for c in data["candidates"])

    # The log keeps every verdict, whatever the model was shown.
    row = suggestions.list_recent(conn, limit=1)[0]
    assert len(row.candidates) == 70


def test_a_short_list_is_returned_whole(registry, conn, full_settings, thursday_clock, family):
    _idea(conn, "Cafe A", setting="indoor")
    _idea(conn, "Ski day", seasons=["winter"])
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family)
    _, data = _suggest(registry, ctx)
    assert len(data["candidates"]) == 2 and data.get("not_shown", 0) == 0


# -- right now and today ------------------------------------------------------------------------
# The `clock` fixture is Sunday 20 September, 14:03 in Vancouver.


def _now_ctx(conn, full_settings, clock, family, *busy):
    calendar = fakes.FakeCalendar(TZ)
    for start, end in busy:
        calendar.seed(
            "Busy",
            datetime(2026, 9, 20, *start, tzinfo=TZ),
            datetime(2026, 9, 20, *end, tzinfo=TZ),
        )
    return _ctx(conn, full_settings, clock, family, calendar=calendar)


def test_now_is_the_next_hours_around_what_is_on(
    registry, conn, full_settings, clock, family
) -> None:
    ctx = _now_ctx(conn, full_settings, clock, family, ((15, 0), (16, 0)))
    cafe = _idea(conn, "Board game cafe", kind="outing", duration_min=90)
    _seed_place(conn, cafe, hours={"sun": [{"open": "11:00", "close": "21:00"}]}, travel_minutes=10)
    shut = _idea(conn, "Ramen place", kind="restaurant", duration_min=60)
    _seed_place(conn, shut, hours={"sun": []})
    coast = _idea(conn, "Day at the coast", kind="day_trip")
    result, data = _suggest(registry, ctx, window="now", question="I'm bored, what now?")
    assert not result.is_error, data
    assert data["window"]["label"] == "now until 18:05"
    # 14:05, not the morning; the hour at three is taken out.
    assert data["days"][0]["free"] == ["14:05-15:00", "16:00-18:05"]
    verdicts = {c["idea_id"]: c for c in data["candidates"]}
    assert verdicts[cafe.id]["verdict"] == "good"
    # Ten minutes each way: there by 16:10, home by 18:05.
    assert "can go 16:10-17:55 today" in verdicts[cafe.id]["reasons"]
    assert verdicts[shut.id]["verdict"] == "ruled_out"
    assert verdicts[coast.id]["verdict"] == "ruled_out"


def test_tonight_is_today_from_five(registry, conn, full_settings, clock, family) -> None:
    ctx = _now_ctx(conn, full_settings, clock, family)
    bar = _idea(conn, "Cocktail bar", kind="restaurant", duration_min=90)
    _seed_place(conn, bar, hours={"sun": [{"open": "16:00", "close": "23:00"}]}, travel_minutes=15)
    _, data = _suggest(
        registry, ctx, window="today", from_time="17:00", until_time="23:00", question="tonight?"
    )
    assert data["days"][0]["free"] == ["17:00-23:00"]
    bar_verdict = next(c for c in data["candidates"] if c["idea_id"] == bar.id)
    assert "can go 17:15-22:45 today" in bar_verdict["reasons"]


def test_times_that_make_no_sense_are_refused(registry, conn, full_settings, clock, family) -> None:
    ctx = _now_ctx(conn, full_settings, clock, family)
    for overrides in (
        {"window": "now", "hours": 20},
        {"window": "today", "until_time": "12:00"},  # it is already after two
        {
            "window": "dates",
            "start": "2026-09-26",
            "end": "2026-09-26",
            "from_time": "18:00",
            "until_time": "09:00",
        },
        {"window": "today", "from_time": "tea time"},
    ):
        result, _ = _suggest(registry, ctx, **overrides)
        assert result.is_error, overrides


def test_a_later_day_keeps_its_morning(conn, full_settings, clock, family) -> None:
    now = clock.now()
    window, label, bounds = resolve_window(
        SuggestInput(
            window="dates",
            start="2026-09-20",
            end="2026-09-21",
            from_time="09:00",
            question="?",
        ),
        now,
    )
    assert label.endswith("09:00-22:00")
    first, last = window
    assert bounds.for_day(first, first, last) == (14 * 60 + 5, 22 * 60)
    assert bounds.for_day(last, first, last) == (9 * 60, 22 * 60)


def test_open_now_without_a_calendar_still_checks_the_hours(
    registry, conn, full_settings, clock, family
) -> None:
    ctx = _ctx(conn, full_settings, clock, family)  # no calendar connected
    cafe = _idea(conn, "Breakfast cafe", kind="restaurant", duration_min=60)
    _seed_place(conn, cafe, hours={"sun": [{"open": "08:00", "close": "12:00"}]})
    _, data = _suggest(registry, ctx, window="now", question="open now?")
    verdict = next(c for c in data["candidates"] if c["idea_id"] == cafe.id)
    assert verdict["verdict"] == "ruled_out"
    assert "calendar not connected" in data["skipped_checks"]


def test_the_topic_is_folded_so_the_same_subject_is_one_search(
    conn, full_settings, thursday_clock, family, monkeypatch
) -> None:
    from familydb.suggest import engine

    seen: list[str] = []

    def record(ctx, context, constraints):
        seen.append(constraints.topic)
        return [], None

    monkeypatch.setattr(engine, "discover", record)
    ctx = _ctx(conn, full_settings, thursday_clock, family)
    for topic in ("Live  Jazz", "live jazz"):
        engine.run(ctx, SuggestInput(window="this_weekend", question="?", topic=topic))
    assert seen == ["live jazz", "live jazz"]
