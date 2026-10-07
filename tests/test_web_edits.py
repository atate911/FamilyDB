"""Changing ideas, outcomes and plans from the page, through the same tools the model calls."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo

import pytest

from familydb.app import App
from familydb.store import db, ideas, outcomes, plans, tasks
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
    """What the last form said: the older pages' line, or the new frame's flash."""
    return " ".join(re.findall(r'class="(?:said|banner__text)"[^>]*>\s*([^<]+)', response.text))


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
    assert "Saved #1 “Ramen place”." in _said(page.get("/idea/1"))


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


def test_the_days_a_thing_is_on_are_set_shown_and_cleared_from_the_page(planning, conn) -> None:
    planning.post(
        "/ideas/new",
        data=_idea_form(
            planning,
            title="Lantern festival",
            kind="event",
            happens_from="2026-10-17",
            happens_time="18:30",
            happens_until="2026-10-18",
        ),
    )
    saved = ideas.get(conn, 1)
    assert (saved.happens_from, saved.happens_until) == ("2026-10-17T18:30", "2026-10-18")
    shown = planning.get("/idea/1").text
    assert "Sat 17 Oct, 6:30\u00a0pm to Sun 18 Oct 2026" in shown
    assert 'value="2026-10-17"' in shown and '<option value="18:30" selected>' in shown
    form = planning.get("/idea/1/edit").text
    assert 'value="2026-10-17"' in form and '<option value="18:30" selected>' in form
    # Emptied boxes clear them, as an emptied text box does.
    planning.post(
        "/idea/1/edit",
        data=_idea_form(
            planning,
            path="/idea/1/edit",
            title="Lantern festival",
            kind="event",
            happens_from="",
            happens_time="",
            happens_until="",
        ),
    )
    cleared = ideas.get(conn, 1)
    assert (cleared.happens_from, cleared.happens_until) == (None, None)


def test_days_that_are_over_are_refused_by_the_tool(page, conn) -> None:
    sent = page.post(
        "/ideas/new",
        data=_idea_form(page, happens_from="2026-09-01", happens_until="2026-09-02"),
    )
    assert "was over on 2026-09-02" in _said(page.get(sent.headers["Location"]))
    assert ideas.list_all(conn) == []


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


def test_without_a_calendar_plans_are_kept_here_by_hand(page, conn):
    """No Google Calendar: the plan forms are there and FamilyDB keeps the plan, saying so."""
    text = page.get("/plans").text
    assert "Add something to the plans" in text and "Add it to the plans" in text
    assert "isn\u2019t connected, so plans are kept here only" in text
    page.post(
        "/plans/new",
        data={"csrf": _token(page, "/plans"), "title": "Picnic", "start": "2026-09-26T13:00"},
    )
    plan = plans.get(conn, 1)
    assert plan.title == "Picnic" and plan.google_event_id is None and plan.calendar_id is None
    assert "Added to the plans: Picnic" in _said(page.get("/plans"))
    page.post("/plan/1/move", data={"csrf": _token(page, "/plans"), "start": "2026-09-27T15:00"})
    assert plans.get(conn, 1).start.startswith("2026-09-27T15:00")
    page.post("/plan/1/cancel", data={"csrf": _token(page, "/plans")})
    assert plans.get(conn, 1).status == "cancelled"


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


def test_an_idea_or_every_one_waiting_can_be_looked_up_now(settings, clock, conn, family):
    looking = _client(settings.model_copy(update={"web_tools_enabled": True}), clock)
    with db.transaction(conn):
        first = ideas.insert(conn, title="Hopscotch", kind="outing")
        second = ideas.insert(conn, title="Ramen", kind="restaurant")
    page = looking.get(f"/idea/{first.id}").text
    assert "Looked up together at 9\u00a0pm each evening." in page and "Look it up now" in page
    sent = looking.post(f"/idea/{first.id}/lookup", data={"csrf": _token(looking, "/")})
    assert sent.headers["Location"] == f"/idea/{first.id}"
    after = looking.get(f"/idea/{first.id}").text
    assert "Looking it up now: within a few minutes." in after
    assert "Asked for now: within a few minutes." in after and "Look it up now" not in after

    status = looking.get("/status").text
    assert (
        'Ideas are looked up together at <span class="fig">9\u00a0pm</span> each evening.' in status
    )
    looking.post("/lookups/now", data={"csrf": _token(looking, "/status")})
    assert "Looking 2 ideas up now" in _said(looking.get("/status"))
    assert ideas.get(conn, second.id).lookup_wanted_at is not None
    # Without lookups on, neither button is there.
    plain = _client(settings, clock).get("/status").text
    assert "Look them up now" not in plain


def test_a_to_do_flash_names_it_in_words_with_no_numbers(page, conn) -> None:
    """The family says "to-do", never "task", and a number is how it works, not what is said."""
    form = {"csrf": _token(page, "/tasks"), "once": "o1", "title": "Buy paper towels"}
    saved = page.post("/tasks/new", data=form, follow_redirects=True)
    assert "Added to your to-dos: Buy paper towels." in _said(saved)
    assert "task" not in _said(saved).lower() and "#" not in _said(saved)


def test_a_done_to_do_can_be_put_back_from_the_done_list(page, conn) -> None:
    page.post(
        "/tasks/new", data={"csrf": _token(page, "/tasks"), "once": "o9", "title": "Pay the bill"}
    )
    page.post("/task/1/done", data={"csrf": _token(page, "/tasks"), "once": "o10", "revision": "1"})
    done = page.get("/tasks?status=done").text
    assert 'action="/task/1/reopen"' in done and ">Undo<" in done.replace("\n", "")
    page.post("/task/1/reopen", data={"csrf": _token(page, "/tasks"), "once": "o11"})
    assert 'id="t-1"' in page.get("/tasks").text  # open again (this also shows the flash)
    assert 'id="t-1"' not in page.get("/tasks?status=done").text


def test_a_tick_and_a_cancel_each_say_so_with_an_undo(page, conn) -> None:
    page.post("/tasks/new", data={"csrf": _token(page, "/tasks"), "once": "u1", "title": "Mow"})
    ticked = page.post(
        "/task/1/done",
        data={"csrf": _token(page, "/tasks"), "once": "u2", "revision": "1"},
        follow_redirects=True,
    ).text
    assert "Done: Mow." in ticked and 'action="/task/1/reopen"' in ticked and ">Undo<" in ticked
    undo = re.search(
        r'action="/task/1/reopen"><input type="hidden" name="csrf" value="([^"]+)"', ticked
    )
    page.post("/task/1/reopen", data={"csrf": undo.group(1), "once": "u3"})
    assert tasks.get(conn, 1).status == "open"
    edit = page.get("/task/1/edit").text
    assert "Mark done" in edit and "Cancel this to-do" in edit and "actions--sticky" in edit
    cancelled = page.post(
        "/task/1/cancel", data={"csrf": _token(page, "/tasks"), "once": "u4"}, follow_redirects=True
    ).text
    assert tasks.get(conn, 1).status == "cancelled" and "Canceled: Mow." in cancelled
    assert "Open it again" in page.get("/task/1/edit").text


def test_an_idea_with_a_plan_ahead_leads_with_it_and_is_rated_with_faces(page, conn) -> None:
    page.post("/ideas/new", data=_idea_form(page))
    plain = page.get("/idea/1").text
    assert 'href="#h-plan"' not in plain and "Plan it another time" not in plain
    assert (
        "Out of ten" not in plain and 'name="went" value="loved"' in plain and "Add more" in plain
    )
    with db.transaction(conn):
        plans.insert(
            conn, title="Ramen", start="2026-09-26T18:00-07:00", end=None, all_day=False, idea_id=1
        )
    ahead = page.get("/idea/1").text
    assert 'href="#h-plan"' in ahead and "Plan it another time" in ahead
    rated = page.post(
        "/idea/1/outcome", data={"csrf": _token(page, "/idea/1"), "once": "o1", "went": "loved"}
    )
    assert rated.status_code == 302
