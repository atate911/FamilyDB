"""What a long, rambling or spoken message needs underneath: ideas tied to dates, and events
somebody put on the calendar by hand that the bot can still move or take off."""

from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from familydb.agent.render import render_idea_line
from familydb.store import db, ideas, plans
from familydb.suggest.context import build_context
from familydb.suggest.shortlist import shortlist
from familydb.suggest.types import Constraints
from familydb.tools import ToolContext, ToolRegistry
from tests import fakes
from tests.conftest import NOW_ISO, TZ
from tests.test_suggest import SAT, SUN, _ctx, _idea, _weekend_ctx


def _call(registry: ToolRegistry, ctx: ToolContext, name: str, **payload):
    result = registry.dispatch(name, payload, ctx)
    return result, json.loads(result.content)


# -- ideas tied to dates -------------------------------------------------------------------------


def test_an_idea_keeps_the_days_it_is_on(registry, ctx) -> None:
    _, festival = _call(
        registry,
        ctx,
        "add_idea",
        title="Lantern festival",
        kind="event",
        participants=["with the girls"],
        happens_from="2026-10-17",
        happens_until="2026-10-18",
    )
    assert (festival["happens_from"], festival["happens_until"]) == ("2026-10-17", "2026-10-18")
    # A start time said with it makes it one evening, not an open run.
    _, concert = _call(
        registry, ctx, "add_idea", title="Beck", kind="show", happens_from="2026-11-18T20:00"
    )
    assert (concert["happens_from"], concert["happens_until"]) == ("2026-11-18T20:00", "2026-11-18")
    # With no end, it is on from that day, like a pumpkin patch that opens on the first.
    _, patch = _call(
        registry, ctx, "add_idea", title="Pumpkin patch", kind="seasonal", happens_from="2026-10-01"
    )
    assert (patch["happens_from"], patch["happens_until"]) == ("2026-10-01", None)
    line = render_idea_line(ideas.get(ctx.conn, festival["id"]))
    assert "| on 2026-10-17 to 2026-10-18 |" in line
    assert "| on 2026-11-18T20:00 |" in render_idea_line(ideas.get(ctx.conn, concert["id"]))
    assert "| from 2026-10-01 |" in render_idea_line(ideas.get(ctx.conn, patch["id"]))


@pytest.mark.parametrize(
    ("given", "complaint"),
    [
        ({"happens_from": "next Saturday"}, "Invalid date"),
        ({"happens_from": "2026-10-18", "happens_until": "2026-10-17"}, "is before"),
        ({"happens_until": "2026-10-17"}, "give happens_from"),
        ({"happens_from": "2026-09-01", "happens_until": "2026-09-02"}, "was over on 2026-09-02"),
    ],
)
def test_dates_that_cannot_be_are_refused(registry, ctx, given, complaint) -> None:
    result, data = _call(registry, ctx, "add_idea", title="Something", kind="event", **given)
    assert result.is_error and complaint in data["error"]
    assert ideas.list_all(ctx.conn) == []


def test_changing_or_clearing_the_days(registry, ctx) -> None:
    _, fair = _call(registry, ctx, "add_idea", title="County fair", kind="event")
    _, fair = _call(registry, ctx, "update_idea", id=fair["id"], happens_from="2026-10-02T10:30")
    assert (fair["happens_from"], fair["happens_until"]) == ("2026-10-02T10:30", "2026-10-02")
    _, fair = _call(registry, ctx, "update_idea", id=fair["id"], happens_until="2026-10-04T22:00")
    assert (fair["happens_from"], fair["happens_until"]) == ("2026-10-02T10:30", "2026-10-04")
    # Clearing the first day clears both: it is no longer tied to dates at all.
    _, fair = _call(registry, ctx, "update_idea", id=fair["id"], happens_from="")
    assert (fair["happens_from"], fair["happens_until"]) == (None, None)


def test_an_idea_whose_days_are_over_can_still_be_changed(registry, ctx) -> None:
    """A form sends the days back as they were drawn; that is no change, and not refused."""
    with db.transaction(ctx.conn):
        old = ideas.insert(
            ctx.conn,
            title="Summer fair",
            kind="event",
            happens_from="2026-08-01",
            happens_until="2026-08-02",
            now=NOW_ISO,
        )
    result, data = _call(
        registry,
        ctx,
        "update_idea",
        id=old.id,
        title="Summer fair (next year?)",
        happens_from="2026-08-01",
        happens_until="2026-08-02",
    )
    assert not result.is_error and data["title"] == "Summer fair (next year?)"


def test_a_dated_idea_is_only_suggested_on_its_own_days(
    conn, full_settings, thursday_clock, family
) -> None:
    ctx = _weekend_ctx(conn, full_settings, thursday_clock, family)
    context = build_context(ctx, (SAT, SUN))
    sunday_only = _idea(conn, "Market", setting="indoor", happens_from="2026-09-27")
    ideas.update(conn, sunday_only.id, {"happens_until": "2026-09-27"}, now=NOW_ISO)
    later = _idea(conn, "Lantern festival", happens_from="2026-10-17", happens_until="2026-10-18")
    over = _idea(conn, "Summer fair", happens_from="2026-08-01", happens_until="2026-08-02")
    running = _idea(conn, "Corn maze", setting="indoor", happens_from="2026-09-01")
    kept, ruled_out, _ = shortlist(ideas.list_all(conn), context, Constraints(), full_settings)
    reasons = {c.idea_id: c.reasons[0] for c in ruled_out}
    assert reasons[later.id] == "on Sat 17 Oct to Sun 18 Oct"
    assert reasons[over.id] == "was over on Sun 2 Aug"
    fits = {s.idea.id: s.fits_days for s in kept}
    assert fits[sunday_only.id] == [SUN]  # never offered for the Saturday
    assert fits[running.id] == [SAT, SUN]


def test_someday_still_leaves_out_what_is_over(conn, settings, thursday_clock, family) -> None:
    context = build_context(_ctx(conn, settings, thursday_clock, family), None)
    later = _idea(conn, "Lantern festival", happens_from="2026-10-17", happens_until="2026-10-18")
    over = _idea(conn, "Summer fair", happens_from="2026-08-01", happens_until="2026-08-02")
    kept, ruled_out, _ = shortlist(ideas.list_all(conn), context, Constraints(), settings)
    assert [s.idea.id for s in kept] == [later.id]
    assert [(c.idea_id, c.reasons) for c in ruled_out] == [(over.id, ["was over on Sun 2 Aug"])]


def test_the_page_says_when_a_dated_idea_is_on(conn, family) -> None:
    from familydb.web.views import idea_row

    concert = _idea(conn, "Beck", happens_from="2026-11-18T20:00", happens_until="2026-11-18")
    run = _idea(conn, "Nutcracker", happens_from="2026-12-05", happens_until="2027-01-02")
    assert idea_row(concert, TZ)["on"] == "Wed 18 Nov 2026, 20:00"
    assert idea_row(run, TZ)["on"] == "Sat 5 Dec 2026 to Sat 2 Jan 2027"
    assert idea_row(_idea(conn, "Plain"), TZ)["on"] is None


# -- events somebody put on the calendar by hand -------------------------------------------------


@pytest.fixture
def cal_ctx(conn, calendar_settings, clock, family):
    calendar = fakes.FakeCalendar(TZ)
    return ToolContext(
        conn=conn, settings=calendar_settings, clock=clock, member=family["sam"], calendar=calendar
    )


def _by_hand(ctx, title="Swim lessons", day=26, start=9, end=11):
    return ctx.calendar.seed(
        title, datetime(2026, 9, day, start, tzinfo=TZ), datetime(2026, 9, day, end, tzinfo=TZ)
    )


def test_an_event_put_on_by_hand_can_be_taken_off(registry, cal_ctx) -> None:
    swim = _by_hand(cal_ctx)
    _, days = _call(registry, cal_ctx, "get_calendar", start="2026-09-26", end="2026-09-26")
    listed = days["days"][0]["events"][0]
    assert listed["google_event_id"] == swim.id and listed["plan_id"] is None
    result, data = _call(registry, cal_ctx, "delete_event", event_id=swim.id)
    assert not result.is_error
    assert data["plan"] is None and data["removed"]["title"] == "Swim lessons"
    assert cal_ctx.calendar.deleted == [swim.id]
    assert plans.list_between(cal_ctx.conn, "2026-01-01", "2027-01-01") == []  # none made up


def test_cancelling_one_by_hand_through_update_event(registry, cal_ctx) -> None:
    swim = _by_hand(cal_ctx)
    result, data = _call(registry, cal_ctx, "update_event", event_id=swim.id, status="cancelled")
    assert not result.is_error and data["removed"]["id"] == swim.id
    result, data = _call(registry, cal_ctx, "delete_event", event_id=swim.id)
    assert result.is_error and "no event" in data["error"]


def test_moving_one_by_hand_keeps_its_length(registry, cal_ctx) -> None:
    dentist = _by_hand(cal_ctx, "Dentist", day=29, start=10, end=11)
    result, data = _call(
        registry, cal_ctx, "update_event", event_id=dentist.id, start="2026-10-02T14:00"
    )
    assert not result.is_error
    assert data["event"]["start"] == "2026-10-02T14:00:00-07:00"
    assert data["event"]["end"] == "2026-10-02T15:00:00-07:00"
    assert data["was"]["start"].startswith("2026-09-29T10:00")


def test_an_event_the_bot_made_is_changed_as_its_plan(registry, cal_ctx) -> None:
    with db.transaction(cal_ctx.conn):
        hike = ideas.insert(cal_ctx.conn, title="The falls hike", kind="outing", now=NOW_ISO)
    _, made = _call(
        registry,
        cal_ctx,
        "create_event",
        title="The falls hike",
        start="2026-10-03T13:00",
        idea_id=hike.id,
    )
    event_id = made["event"]["id"]
    result, data = _call(registry, cal_ctx, "delete_event", event_id=event_id)
    assert not result.is_error and data["plan"]["status"] == "cancelled"
    assert ideas.get(cal_ctx.conn, hike.id).status == "idea"  # back on the list


@pytest.mark.parametrize("given", [{}, {"plan_id": 1, "event_id": "evt1"}])
def test_exactly_one_of_plan_and_event(registry, cal_ctx, given) -> None:
    result, data = _call(registry, cal_ctx, "delete_event", **given)
    assert result.is_error and "give plan_id, or event_id" in data["error"]


def test_the_days_a_dated_idea_is_on() -> None:
    idea = ideas.Idea(
        id=1,
        kind="event",
        title="Fair",
        happens_from="2026-10-02T10:30",
        happens_until="2026-10-04",
        created_at=NOW_ISO,
        updated_at=NOW_ISO,
    )
    assert (idea.first_day, idea.last_day) == (date(2026, 10, 2), date(2026, 10, 4))
    assert [idea.on(date(2026, 10, d)) for d in (1, 2, 4, 5)] == [False, True, True, False]
    undated = idea.model_copy(update={"happens_from": None, "happens_until": None})
    assert undated.on(date(2020, 1, 1))
