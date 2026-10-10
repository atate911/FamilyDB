"""The kitchen tablet's board (docs/INTERFACE.md section 8; web/destinations.py `board`): Now as
one surface for the family at the wall. Faces along the box's top that hold for a minute, today
and tomorrow largest, what waits on a person, the shopping list always, her picks, the saved ideas
fading at the bottom. No costs, no back office, no model call."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from familydb.app import App
from familydb.store import db, ideas, lists, plans
from familydb.web import create_app
from tests import fakes
from tests.conftest import NOW_ISO

TZ = ZoneInfo("America/Vancouver")


def _board(settings, clock, calendar=None, api=None):
    return create_app(App(settings, clock, calendar=calendar), api=api).test_client()


def _faces(page: str) -> str:
    found = re.search(r'<fieldset class="bar__faces">.*?</fieldset>', page, re.S)
    assert found is not None
    return found.group(0)


def test_the_board_is_today_and_tomorrow_what_waits_and_the_list(
    calendar_settings, clock, conn, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Swim lesson",
        datetime(2026, 9, 20, 16, 30, tzinfo=TZ),
        datetime(2026, 9, 20, 17, tzinfo=TZ),
    )
    calendar.seed(
        "Night market", datetime(2026, 9, 21, 17, tzinfo=TZ), datetime(2026, 9, 21, 20, tzinfo=TZ)
    )
    with db.transaction(conn):
        hike = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=hike.id,
        )
        ideas.insert(conn, title="Pottery", kind="activity", cost_level=3, now=NOW_ISO)
        ideas.insert(conn, title="Old kite day", kind="outing", now="2026-06-01T12:00:00Z")
        shopping = lists.list_id(conn, "shopping", NOW_ISO)
        lists.add(conn, shopping, "milk", by=None, now=NOW_ISO)
    client = _board(calendar_settings, clock, calendar)
    page = client.get("/board").text
    days = page[page.index('class="bd__days"') :]
    assert days.index("Today") < days.index("Swim lesson") < days.index("Tomorrow")
    assert days.index("Tomorrow") < days.index("Night market")
    assert "bd__day--first" in page  # the nearer day is the largest
    assert "How did Silver Falls hike go?" in page and 'name="back" value="board"' in page
    assert ">milk<" in page
    someday = re.search(r'<section class="bd__someday".*?</section>', page, re.S).group(0)
    assert "Pottery" in someday and "bd__idea--resting" in someday  # the old one fades
    assert "$" not in page.split('class="bd"')[1]  # no costs on the wall
    assert 'aria-current="page">Now<' in page
    # A tick on the board comes back to the board.
    form = re.search(r'<ul class="bd__items">.*?</form>', page, re.S).group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form))
    ticked = client.post("/lists/change", data=fields)
    assert ticked.status_code == 302 and ticked.headers["Location"] == "/board"
    assert ">milk<" not in client.get("/board").text


def test_faces_along_the_top_say_who_is_asking_and_hold_for_a_minute(
    settings, clock, conn, family
) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("On it.")]))
    web = create_app(App(settings, clock), api=api)
    client = web.test_client()
    page = client.get("/board").text
    faces = _faces(page)
    for name in ("Sam", "Alex", "the girls"):
        assert f'name="who" value="{name}" required' in faces
    assert "checked" not in faces and '<select id="who"' not in page  # nobody picked for them
    box = re.search(r'<form class="bar[^"]*" id="ask".*?</form>', page, re.S).group(0)
    fields = dict(re.findall(r'name="(csrf|once|back)" value="([^"]+)"', box))
    sent = client.post("/chat", data={**fields, "text": "what about tonight?", "who": "Alex"})
    assert sent.status_code == 302 and sent.headers["Location"].startswith("/board?asked=")
    assert web.config["FAMILYDB_CHAT"].wait(10)
    assert 'value="Alex" required checked' in _faces(client.get("/board").text)
    clock.advance(timedelta(seconds=61))
    assert "checked" not in _faces(client.get("/board").text)  # the next person is not Alex
    # Elsewhere the box keeps asking From, as before.
    assert '<select id="who"' in client.get("/").text


def test_the_board_asks_no_model(settings, clock, conn, family) -> None:
    api = fakes.FakeMessagesAPI()
    client = _board(settings, clock, api=api)
    assert client.get("/board").status_code == 200
    assert api.requests == []
