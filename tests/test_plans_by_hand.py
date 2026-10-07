"""Plans with or without Google Calendar: FamilyDB keeps its own, and copies them across when
there is a calendar."""

from __future__ import annotations

import json
from zoneinfo import ZoneInfo

import pytest

from familydb.store import db, ideas, plans
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO

TZ = ZoneInfo("America/Vancouver")


def _run(registry, name, ctx, **args):
    result = registry.dispatch(name, args, ctx)
    return result, json.loads(result.content)


@pytest.fixture
def here(conn, settings, clock, family) -> ToolContext:
    """No calendar connected."""
    return ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])


@pytest.fixture
def on_google(conn, calendar_settings, clock, family) -> ToolContext:
    return ToolContext(
        conn=conn,
        settings=calendar_settings,
        clock=clock,
        member=family["sam"],
        calendar=fakes.FakeCalendar(TZ),
    )


def test_a_plan_is_made_moved_and_cancelled_with_no_calendar(registry, conn, here) -> None:
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Ramen", kind="restaurant", now=NOW_ISO)
    made, data = _run(
        registry, "create_event", here, title="Ramen", start="2026-09-26T18:30", idea_id=idea.id
    )
    assert not made.is_error and data["event"] is None and "FamilyDB only" in data["note"]
    plan = plans.get(conn, data["plan"]["id"])
    assert plan.google_event_id is None and plan.calendar_id is None
    assert ideas.get(conn, idea.id).status == "planned"
    # Asking again for the same plan finds it, instead of making a second.
    _, again = _run(
        registry, "create_event", here, title="ramen", start="2026-09-26T18:30", idea_id=idea.id
    )
    assert again["plan"]["id"] == plan.id
    moved, data = _run(registry, "update_event", here, plan_id=plan.id, start="2026-09-27T19:00")
    assert not moved.is_error and plans.get(conn, plan.id).start.startswith("2026-09-27T19:00")
    assert plans.get(conn, plan.id).end.startswith("2026-09-27T21:00")  # it kept its length
    cancelled, _ = _run(registry, "delete_event", here, plan_id=plan.id)
    assert not cancelled.is_error and plans.get(conn, plan.id).status == "cancelled"
    assert ideas.get(conn, idea.id).status == "idea"  # back on the list


def test_a_plan_in_the_past_is_still_refused(registry, here) -> None:
    result, data = _run(registry, "create_event", here, title="Then", start="2020-01-01T10:00")
    assert result.is_error and "past" in data["error"]


def test_without_a_calendar_only_get_calendar_and_hand_made_events_are_unavailable(
    registry, here
) -> None:
    _, data = _run(registry, "get_calendar", here, start="2026-09-26", end="2026-09-27")
    assert data["available"] is False
    _, data = _run(registry, "update_event", here, event_id="abc", title="x")
    assert data["available"] is False  # an event somebody added by hand lives only in Google


def test_a_plan_that_is_on_google_cannot_be_changed_while_google_is_not_connected(
    registry, conn, on_google, here
) -> None:
    _, data = _run(registry, "create_event", on_google, title="Dinner", start="2026-09-26T18:30")
    plan_id = data["plan"]["id"]
    assert plans.get(conn, plan_id).google_event_id
    result, data = _run(registry, "delete_event", here, plan_id=plan_id)
    assert result.is_error and "not connected" in data["error"]
    assert plans.get(conn, plan_id).status == "confirmed"


def test_a_plan_kept_here_is_copied_to_google_once_there_is_a_calendar(
    registry, conn, here, on_google
) -> None:
    _, data = _run(registry, "create_event", here, title="Picnic", start="2026-09-26T13:00")
    plan_id = data["plan"]["id"]
    calendar = on_google.calendar
    assert calendar.get_event("anything") is None
    # Looking at the calendar copies it.
    _run(registry, "get_calendar", on_google, start="2026-09-26", end="2026-09-27")
    plan = plans.get(conn, plan_id)
    assert plan.google_event_id and plan.calendar_id == on_google.settings.google_calendar_id
    assert calendar.get_event(plan.google_event_id).title == "Picnic"
    # Copying twice makes one event.
    _run(registry, "search_plans", on_google, query="picnic")
    assert plans.get(conn, plan_id).google_event_id == plan.google_event_id


def test_changing_a_plan_kept_here_copies_it_and_then_moves_it_on_google(
    registry, conn, here, on_google
) -> None:
    _, data = _run(registry, "create_event", here, title="Picnic", start="2026-09-26T13:00")
    plan_id = data["plan"]["id"]
    moved, _ = _run(registry, "update_event", on_google, plan_id=plan_id, start="2026-09-27T15:00")
    assert not moved.is_error
    plan = plans.get(conn, plan_id)
    event = on_google.calendar.get_event(plan.google_event_id)
    assert plan.start.startswith("2026-09-27T15:00") and event.start.hour == 15
