"""Forms that do their thing once, however many times the browser sends them."""

from __future__ import annotations

import re
import threading
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from familydb.app import App
from familydb.store import ideas, messages, outcomes, plans
from familydb.web import create_app
from tests import fakes

PASSWORD = "open sesame please"
TZ = ZoneInfo("America/Vancouver")


def _client(app_settings, clock, **extra):
    app = App(app_settings.model_copy(update={"web_password": PASSWORD}), clock, **extra)
    web = create_app(app, api=fakes.FakeMessagesAPI(fakes.message([fakes.text("Hello.")])))
    client = web.test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


@pytest.fixture
def page(settings, clock, conn, family):
    return _client(settings, clock)


@pytest.fixture
def planning(calendar_settings, clock, conn, family):
    calendar = fakes.FakeCalendar(TZ)
    client = _client(calendar_settings, clock, calendar=calendar)
    client.calendar = calendar
    return client


def _form(client, path: str) -> dict[str, str]:
    """The csrf and once fields exactly as a browser would send them back from this page."""
    text = client.get(path).text
    csrf = re.search(r'name="csrf" value="([^"]+)"', text)
    token = re.search(r'name="once" value="([^"]+)"', text)
    assert csrf and token, path
    return {"csrf": csrf.group(1), "once": token.group(1)}


def test_an_idea_sent_twice_is_saved_once(page, conn) -> None:
    form = {**_form(page, "/ideas/new"), "title": "Ramen place", "kind": "restaurant"}
    first = page.post("/ideas/new", data=form)
    second = page.post("/ideas/new", data=form)  # a double click, or a refresh that resends
    assert len(ideas.list_all(conn)) == 1
    assert second.status_code == 302 and second.headers["Location"] == first.headers["Location"]


def test_a_visit_recorded_twice_is_counted_once(page, conn) -> None:
    page.post("/ideas/new", data={**_form(page, "/ideas/new"), "title": "Museum", "kind": "outing"})
    form = {**_form(page, "/idea/1"), "rating": "8"}
    page.post("/idea/1/outcome", data=form)
    page.post("/idea/1/outcome", data=form)
    assert len(outcomes.list_for_idea(conn, 1)) == 1
    assert ideas.get(conn, 1).times_done == 1


def test_a_plan_sent_twice_is_one_event_on_the_calendar(planning, conn) -> None:
    form = {**_form(planning, "/plans"), "title": "Harvest festival", "start": "2026-09-26T10:00"}
    planning.post("/plans/new", data=form)
    planning.post("/plans/new", data=form)
    assert len(planning.calendar.events) == 1
    assert plans.get(conn, 2) is None


def test_a_second_send_while_the_first_is_at_google_waits_for_it(planning, conn) -> None:
    """The case a double click really is: both arrive before the first has finished."""
    calendar = planning.calendar
    inside, release = threading.Event(), threading.Event()
    original = calendar.insert_event

    def slow(**kwargs):
        inside.set()
        assert release.wait(10)
        return original(**kwargs)

    calendar.insert_event = slow
    form = {**_form(planning, "/plans"), "title": "Harvest festival", "start": "2026-09-26T10:00"}
    other = planning.application.test_client()  # a second connection from the same browser
    other.set_cookie("session", planning.get_cookie("session").value)
    answers: dict[str, object] = {}
    first = threading.Thread(
        target=lambda: answers.setdefault("a", planning.post("/plans/new", data=form))
    )
    first.start()
    assert inside.wait(10)
    second = threading.Thread(
        target=lambda: answers.setdefault("b", other.post("/plans/new", data=form))
    )
    second.start()
    release.set()
    first.join(10)
    second.join(10)
    assert len(calendar.events) == 1
    assert answers["a"].headers["Location"] == answers["b"].headers["Location"] == "/plans"


def test_a_token_only_counts_for_the_browser_it_was_drawn_for(settings, clock, conn, family):
    one = _client(settings, clock)
    two = one.application.test_client()
    assert two.post("/login", data={"password": PASSWORD}).status_code == 302
    token = _form(one, "/ideas/new")["once"]
    one.post(
        "/ideas/new", data={**_form(one, "/ideas/new"), "once": token, "title": "A", "kind": "x"}
    )
    two.post(
        "/ideas/new", data={**_form(two, "/ideas/new"), "once": token, "title": "B", "kind": "x"}
    )
    assert sorted(i.title for i in ideas.list_all(conn)) == ["A", "B"]


def test_a_message_sent_twice_is_asked_once(page, conn) -> None:
    form = {**_form(page, "/chat"), "text": "hello", "who": "Sam"}
    first = page.post("/chat", data=form)
    page.application.config["FAMILYDB_CHAT"].wait(10)
    second = page.post("/chat", data=form)
    page.application.config["FAMILYDB_CHAT"].wait(10)  # had it started a turn, it has finished
    assert second.status_code == 302 and second.headers["Location"] == first.headers["Location"]
    thread = messages.last_for_chat(conn, "web", limit=10)
    assert [m.direction for m in thread] == ["in", "out"]


def test_an_edit_on_top_of_somebody_else_s_is_refused(page, conn) -> None:
    page.post("/ideas/new", data={**_form(page, "/ideas/new"), "title": "Museum", "kind": "outing"})
    mine = page.get("/idea/1/edit").text  # opened, and left open
    drawn = re.search(r'name="revision" value="([^"]+)"', mine).group(1)
    page.application.config["FAMILYDB_APP"].clock.advance(timedelta(minutes=1))
    theirs = {**_form(page, "/idea/1/edit"), "title": "Art museum", "kind": "outing"}
    page.post("/idea/1/edit", data={**theirs, "revision": drawn})  # somebody else saves first
    refused = page.post(
        "/idea/1/edit",
        data={
            **_form(page, "/idea/1/edit"),
            "revision": drawn,
            "title": "Museum",
            "kind": "outing",
            "tags": "art",
        },
    )
    assert refused.headers["Location"] == "/idea/1/edit"
    assert "was changed since you opened it" in page.get("/idea/1/edit").text
    assert ideas.get(conn, 1).title == "Art museum" and ideas.get(conn, 1).tags == []


def test_the_move_form_shows_where_the_plan_is_now(planning, conn) -> None:
    planning.post(
        "/plans/new",
        data={**_form(planning, "/plans"), "title": "Dinner", "start": "2026-09-26T18:30"},
    )
    assert plans.get(conn, 1).start == "2026-09-26T18:30-07:00"
    # A datetime-local box given the offset as well shows nothing; it wants the wall time.
    assert 'value="2026-09-26T18:30"' in planning.get("/plans").text
