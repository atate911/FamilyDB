"""The settings for what is on near home: the calendars to read (ticked or pasted), the search,
the budget, the Ticketmaster key, and the one place the family's name for it is written."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from markupsafe import escape
from pydantic import ValidationError

from familydb import happening
from familydb.app import App
from familydb.base.config import Settings
from familydb.store import finds
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.web import create_app

PASSWORD = "open sesame please"
LIBRARY = "https://library.example.org/events.ics"
PARKS = "https://parks.example.org/calendar.ics"
MINE = "https://school.example.org/term.ics"


@pytest.fixture
def page(settings, clock, conn, family):
    live = settings.model_copy(update={"web_password": PASSWORD, "home_area": "Vancouver, WA"})
    app = App(live, clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def _token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/general").text)
    assert found is not None
    return found.group(1)


def test_the_family_name_for_it_is_written_in_one_place() -> None:
    """A rename is one line: nothing else in the code, templates or her lines spells it."""
    root = Path(happening.__file__).parent
    spelled = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.suffix in {".py", ".html", ".md", ".toml"}
        and path.name != "happening.py"
        and "going down" in path.read_text(encoding="utf-8").casefold()
    ]
    assert spelled == []


def test_calendar_lines_are_tidied_and_a_line_that_is_no_address_is_refused() -> None:
    tidy = Settings(_env_file=None, event_feeds=f"  {LIBRARY}\n\nwebcal://parks.example.org/c\n")
    assert tidy.event_feeds == f"{LIBRARY}\nhttps://parks.example.org/c"
    assert Settings(_env_file=None, event_feeds=f"{LIBRARY}\n{LIBRARY}").event_feeds == LIBRARY
    with pytest.raises(ValidationError, match="starting with https://"):
        Settings(_env_file=None, event_feeds="the library's calendar")


def test_the_page_is_among_the_settings_under_its_name(page) -> None:
    listed = page.get("/settings").text
    assert 'href="/settings/happening"' in listed and str(escape(happening.NAME)) in listed
    text = page.get("/settings/happening").text
    assert "<textarea" in text and 'name="event_feeds"' in text
    assert 'name="happening_budget"' in text and 'name="ticketmaster_api_key"' in text
    assert "Nothing proposed yet" in text


def test_a_pasted_line_that_is_no_address_is_said_beside_its_box(page, conn) -> None:
    sent = {"csrf": _token(page), "section": "happening", "event_feeds": "library calendar"}
    refused = page.post("/settings", data=sent)
    assert refused.status_code == 400 and "starting with https://" in refused.text
    assert settings_store.overrides(conn) == {}


def _propose(conn, *urls: str) -> None:
    readable = [
        finds.Readable(url=u, title=f"Calendar {i}", note="", events=4) for i, u in enumerate(urls)
    ]
    with transaction(conn):
        finds.merge_proposals(conn, "Vancouver, WA", readable, now="2026-09-20T05:00:00Z")
        finds.source_answered(
            conn,
            happening.proposals_source("Vancouver, WA"),
            "proposals",
            ok=True,
            note="",
            found=len(urls),
            at="2026-09-20T05:00:00Z",
        )


def test_a_proposed_calendar_is_a_tick_and_a_pasted_one_a_line(page, conn) -> None:
    _propose(conn, LIBRARY, PARKS)
    text = page.get("/settings/happening").text
    assert text.count('name="proposed"') == 2 and "Calendar 0" in text
    assert text.count(">new</span>") == 2  # found on the last look, not ticked yet

    sent = {
        "csrf": _token(page),
        "section": "happening",
        "proposed": [LIBRARY, PARKS],
        "feed": [LIBRARY],
        "event_feeds": MINE,
    }
    assert page.post("/settings", data=sent).status_code == 302
    assert settings_store.get(conn, "event_feeds") == f"{LIBRARY}\n{MINE}"

    again = page.get("/settings/happening").text
    assert re.search(rf'value="{re.escape(LIBRARY)}" checked', again)
    box = re.search(r'<textarea[^>]*name="event_feeds"[^>]*>([^<]*)</textarea>', again)
    assert box is not None and box.group(1) == MINE  # the ticked one is not a line too

    untick = {**sent, "feed": [PARKS], "csrf": _token(page)}
    page.post("/settings", data=untick)
    assert settings_store.get(conn, "event_feeds") == f"{PARKS}\n{MINE}"


def test_the_ticketmaster_key_is_kept_on_its_own_page_and_never_shown(page, conn) -> None:
    sent = {"csrf": _token(page), "section": "happening", "ticketmaster_api_key": "tm-secret-1"}
    answered = page.post("/settings/keys", data=sent)
    assert answered.headers["Location"] == "/settings/happening"
    assert settings_store.get(conn, "ticketmaster_api_key") == "tm-secret-1"
    assert "tm-secret-1" not in page.get("/settings/happening").text
    assert "saved here" in page.get("/settings/happening").text
    assert "k-ticketmaster_api_key" not in page.get("/settings/model").text
    refused = page.post(
        "/settings/keys", data={"csrf": _token(page), "ticketmaster_api_key": "tm secret"}
    )
    assert refused.status_code == 400 and f"<h1>{escape(happening.NAME)}</h1>" in refused.text


def test_status_says_whether_there_is_a_ticketmaster_key(page) -> None:
    assert "Ticketmaster key" in page.get("/status").text
