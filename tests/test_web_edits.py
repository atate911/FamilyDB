"""Changing ideas, outcomes and plans from the page, through the same tools the model calls."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo

import pytest

from familydb.app import App
from familydb.store import ideas, outcomes, plans
from familydb.web import create_app
from tests import fakes

PASSWORD = "open sesame please"
TZ = ZoneInfo("America/Vancouver")


def _client(app_settings, clock, **extra):
    app = App(app_settings.model_copy(update={"web_password": PASSWORD}), clock, **extra)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


@pytest.fixture
def page(settings, clock, conn, family):
    return _client(settings, clock)


@pytest.fixture
def planning(calendar_settings, clock, conn, family):
    """A page with Google Calendar connected, so the plan forms are there to use."""
    return _client(calendar_settings, clock, calendar=fakes.FakeCalendar(TZ))


def _token(client, path: str) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get(path).text)
    assert found is not None
    return found.group(1)


def _said(response) -> str:
    return " ".join(re.findall(r'class="said"[^>]*>\s*([^<]+)', response.text))


def _idea_form(client, path="/ideas/new", **changes) -> dict[str, str]:
    form = {"csrf": _token(client, path), "title": "Ramen place", "kind": "restaurant"}
    if path.endswith("/edit"):
        form["revision"] = re.search(
            r'name="revision" value="([^"]+)"', client.get(path).text
        ).group(1)
    form.update({key: str(value) for key, value in changes.items()})
    return form


def test_an_idea_can_be_added_from_the_page(page, conn) -> None:
    sent = page.post(
        "/ideas/new",
        data=_idea_form(
            page,
            description="the one on Main St",
            participants="whole family, the girls",
            tags="food, cheap",
            cost_level=2,
            duration_min=60,
            needs_booking="yes",
            who="Alex",
        ),
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/idea/1"
    saved = ideas.get(conn, 1)
    assert saved.title == "Ramen place" and saved.kind == "restaurant"
    assert saved.participants == ["whole family", "the girls"]
    assert saved.tags == ["cheap", "food"]  # the store lowercases and sorts them
    assert saved.cost_level == 2 and saved.duration_min == 60 and saved.needs_booking
    assert saved.suggested_by_name == "Alex"  # the form said who, and the tool recorded it
    assert "Saved #1 Ramen place." in _said(page.get("/idea/1"))


def test_an_idea_with_no_title_is_refused_and_nothing_is_written(page, conn) -> None:
    sent = page.post("/ideas/new", data=_idea_form(page, title="  "))
    assert sent.status_code == 302 and sent.headers["Location"] == "/ideas/new"
    assert "An idea needs a title." in _said(page.get("/ideas/new"))
    assert ideas.list_all(conn) == []


def test_the_duplicate_check_is_the_tool_s_own(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    again = page.post("/ideas/new", data=_idea_form(page, title="ramen place"))
    assert again.headers["Location"] == "/idea/1"  # sent to the one that already exists
    assert "already an idea called that: #1" in _said(page.get("/idea/1"))
    assert len(ideas.list_all(conn)) == 1


def test_a_number_that_is_not_a_number_is_refused(page, conn) -> None:
    sent = page.post("/ideas/new", data=_idea_form(page, duration_min="a while"))
    assert sent.headers["Location"] == "/ideas/new"
    assert "The shortest time needs to be a number." in _said(page.get("/ideas/new"))
    assert ideas.list_all(conn) == []


def test_an_idea_can_be_changed_and_a_text_box_emptied(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page, description="the one on Main St"))
    changed = page.post(
        "/idea/1/edit",
        data=_idea_form(
            page, path="/idea/1/edit", title="Ramen place on Main", tags="food", description=""
        ),
    )
    assert changed.status_code == 302 and changed.headers["Location"] == "/idea/1"
    saved = ideas.get(conn, 1)
    assert saved.title == "Ramen place on Main" and saved.tags == ["food"]
    assert not saved.description  # an emptied box clears the field rather than leaving it be


def test_the_edit_form_comes_up_filled_in(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page, tags="food, cheap", cost_level=2))
    form = page.get("/idea/1/edit").text
    assert 'value="Ramen place"' in form
    assert 'value="cheap, food"' in form
    assert '<option value="2" selected>moderate</option>' in form


def test_an_idea_can_be_dropped_and_brought_back(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    page.post("/idea/1/status", data={"csrf": _token(page, "/idea/1"), "status": "dropped"})
    assert ideas.get(conn, 1).status == "dropped"
    assert "Bring it back" in page.get("/idea/1").text
    page.post("/idea/1/status", data={"csrf": _token(page, "/idea/1"), "status": "idea"})
    assert ideas.get(conn, 1).status == "idea"


def test_recording_an_outcome_marks_the_idea_done(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    sent = page.post(
        "/idea/1/outcome",
        data={
            "csrf": _token(page, "/idea/1"),
            "happened_on": "2026-09-19",
            "rating": "8",
            "would_repeat": "yes",
            "notes": "busy but good",
            "who": "Sam",
        },
    )
    assert sent.status_code == 302
    recorded = outcomes.list_for_idea(conn, 1)
    assert len(recorded) == 1
    assert recorded[0].rating == 8 and recorded[0].would_repeat is True
    assert recorded[0].notes == "busy but good"
    saved = ideas.get(conn, 1)
    assert saved.status == "done" and saved.times_done == 1 and saved.avg_rating == 8


def test_an_outcome_in_the_future_is_refused_by_the_tool(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    page.post(
        "/idea/1/outcome",
        data={"csrf": _token(page, "/idea/1"), "happened_on": "2026-12-25", "rating": "9"},
    )
    assert outcomes.list_for_idea(conn, 1) == []
    assert "things that happened" in _said(page.get("/idea/1"))


def test_a_plan_can_be_made_from_an_idea_and_cancelled(planning, conn) -> None:
    planning.post("/ideas/new", data=_idea_form(planning))
    sent = planning.post(
        "/plans/new",
        data={
            "csrf": _token(planning, "/idea/1"),
            "idea_id": "1",
            "title": "Ramen place",
            "start": "2026-09-26T18:30",
            "location": "Main St",
            "who": "Sam",
        },
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/idea/1"
    plan = plans.get(conn, 1)
    assert plan.title == "Ramen place" and plan.start.startswith("2026-09-26T18:30")
    assert plan.google_event_id  # it really went on the calendar, through the same tool
    assert ideas.get(conn, 1).status == "planned"

    planning.post("/plan/1/cancel", data={"csrf": _token(planning, "/plans")})
    assert plans.get(conn, 1).status == "cancelled"
    assert ideas.get(conn, 1).status == "idea"  # and the idea goes back to being one


def test_a_plan_can_be_moved_rather_than_cancelled_and_remade(planning, conn) -> None:
    """Cancelling and adding it again would lose the link to the idea and the notes."""
    planning.post("/ideas/new", data=_idea_form(planning))
    planning.post(
        "/plans/new",
        data={
            "csrf": _token(planning, "/idea/1"),
            "idea_id": "1",
            "title": "Ramen place",
            "start": "2026-09-26T18:30",
        },
    )
    moved = planning.post(
        "/plan/1/move",
        data={"csrf": _token(planning, "/plans"), "start": "2026-09-27T19:00"},
    )
    assert moved.status_code == 302
    plan = plans.get(conn, 1)
    assert plan.start.startswith("2026-09-27T19:00")
    assert plan.idea_id == 1 and plan.google_event_id  # the same event, moved
    assert plan.status == "confirmed"
    assert ideas.get(conn, 1).status == "planned"
    assert "Moved to" in _said(planning.get("/plans"))


def test_moving_a_plan_into_the_past_is_refused_by_the_tool(planning, conn) -> None:
    planning.post(
        "/plans/new",
        data={
            "csrf": _token(planning, "/plans"),
            "title": "Harvest festival",
            "start": "2026-09-26T18:30",
        },
    )
    planning.post(
        "/plan/1/move", data={"csrf": _token(planning, "/plans"), "start": "2020-01-01T10:00"}
    )
    assert plans.get(conn, 1).start.startswith("2026-09-26")  # unmoved


def test_an_all_day_plan_keeps_only_the_date(planning, conn) -> None:
    planning.post(
        "/plans/new",
        data={
            "csrf": _token(planning, "/plans"),
            "title": "Harvest festival",
            "start": "2026-09-26T18:30",
            "all_day": "yes",
        },
    )
    plan = plans.get(conn, 1)
    assert plan.all_day and plan.start == "2026-09-26"


def test_without_a_calendar_the_page_offers_no_plan_form_and_refuses_one_anyway(page, conn):
    assert "not connected" in page.get("/plans").text
    assert "csrf" not in page.get("/plans").text  # there is no form on the page at all
    page.post(
        # A token from another form on the site: being refused for the right reason is the point.
        "/plans/new",
        data={"csrf": _token(page, "/chat"), "title": "Nope", "start": "2026-09-26T18:30"},
    )
    assert plans.get(conn, 1) is None
    assert "Google Calendar" in _said(page.get("/plans"))


@pytest.mark.parametrize(
    ("path", "form"),
    [
        ("/ideas/new", {"title": "Sneaky", "kind": "restaurant"}),
        ("/idea/1/edit", {"title": "Sneaky", "kind": "restaurant"}),
        ("/idea/1/status", {"status": "dropped"}),
        ("/idea/1/outcome", {"rating": "9"}),
        ("/plans/new", {"title": "Sneaky", "start": "2026-09-26T18:30"}),
        ("/plan/1/cancel", {}),
        ("/plan/1/move", {"start": "2026-09-27T19:00"}),
    ],
)
def test_every_form_refuses_a_post_from_another_site(page, conn, path, form) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    before = ideas.get(conn, 1)
    sent = page.post(
        path, data={"csrf": _token(page, "/idea/1"), **form}, headers={"Origin": "https://evil.x"}
    )
    assert sent.status_code == 302  # sent back to the page, having done nothing
    assert "did not come from this page" in _said(page.get("/idea/1"))
    assert ideas.get(conn, 1) == before
    assert len(ideas.list_all(conn, include_dropped=True)) == 1


@pytest.mark.parametrize(
    ("path", "form"),
    [
        ("/ideas/new", {"title": "Sneaky", "kind": "restaurant"}),
        ("/idea/1/edit", {"title": "Sneaky", "kind": "restaurant"}),
        ("/idea/1/status", {"status": "dropped"}),
        ("/idea/1/outcome", {"rating": "9"}),
    ],
)
def test_every_form_refuses_a_stale_token(page, conn, path, form) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    before = ideas.get(conn, 1)
    page.post(path, data={"csrf": "not-this-session", **form})
    assert "too old to use" in _said(page.get("/idea/1"))
    assert ideas.get(conn, 1) == before
    assert len(ideas.list_all(conn, include_dropped=True)) == 1


def test_the_forms_are_behind_the_password(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    stranger = create_app(app).test_client()
    for path in ("/ideas/new", "/idea/1/edit", "/idea/1/status", "/plans/new"):
        assert stranger.post(path, data={"title": "x"}).status_code == 401
    assert stranger.get("/ideas/new").status_code == 302
