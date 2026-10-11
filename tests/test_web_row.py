"""The row of destinations, less the places the family took out on Settings, General
(`Settings.row_hidden`): a tick for each place; a place taken out leaves the row, its pages still
open, and with Now taken out the page opens on the first place left."""

from __future__ import annotations

import re

import pytest

from familydb import family as rules
from familydb.app import App
from familydb.base.config import ROW_PLACES, Settings
from familydb.store import ideas
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.web import create_app, fields
from tests.conftest import NOW_ISO

SAM = ("Sam", "sam likes long sentences")
KID = ("the girls", "a kid can choose one too")


@pytest.fixture
def app(settings, clock, conn, family):
    live = App(settings.model_copy(update={"web_password": "installer-made-password-1"}), clock)
    for key, (_, word) in (("sam", SAM), ("girls", KID)):
        rules.choose_password(conn, family[key].id, word, now=NOW_ISO)
    with transaction(conn):
        ideas.insert(conn, title="Zoo", kind="outing", now=NOW_ISO)  # not the first day
    return live


def _in_as(app, who: tuple[str, str]):
    client = create_app(app).test_client()
    name, password = who
    assert client.post("/login", data={"name": name, "password": password}).status_code == 302
    return client


def _row(page: str) -> list[str]:
    """The words of the row, in its order."""
    nav = re.search(r'<nav class="row".*?</nav>', page, re.S)
    assert nav is not None
    return re.findall(r"<a [^>]*>([^<]+)(?:<span|</a>)", nav.group(0))


def _menu(page: str) -> list[str]:
    """The words of the menu down the left, in its order."""
    side = re.search(r'<aside class="side".*?</aside>', page, re.S)
    assert side is not None
    return re.findall(r"<span>([^<]+)</span>", side.group(0))


def test_every_page_has_the_one_menu_with_the_back_office_in_it(app) -> None:
    """The family's pages and the back office draw the same menu down the left (_side.html), so
    opening Now from Settings keeps the way back; an admin's has Status, Guide, Settings and
    Family, a kid's none of them."""
    sam = _in_as(app, SAM)
    for page in ("/", "/eat", "/kids", "/chat", "/settings", "/status"):
        menu = _menu(sam.get(page).text)
        assert {"Now", "Status", "Guide", "Settings", "Family"} <= set(menu), page
    assert (
        'aria-current="page">'
        in sam.get("/eat").text.split('<aside class="side"')[1].split("</aside>")[0]
    )
    kid = _in_as(app, KID)
    assert _menu(kid.get("/").text)[:5] == ["Now", "Chat with Vera", "Do", "My week", "My list"]
    assert not {"Status", "Settings", "Family"} & set(_menu(kid.get("/").text))


def _take_out(conn, places: str) -> None:
    with transaction(conn):
        settings_store.set_many(conn, {"row_hidden": places}, changed_by=None)


def _ticks(page: str) -> dict[str, bool]:
    """Each tick on the settings page, by place, and whether it is ticked."""
    found = re.findall(
        r'<input type="checkbox" name="row_hidden_shown" value="(\w+)"( checked)?', page
    )
    return {place: bool(on) for place, on in found}


def test_a_tick_for_each_place_and_unticking_takes_it_out_of_the_row(app, conn) -> None:
    sam = _in_as(app, SAM)
    page = sam.get("/settings/general").text
    assert _ticks(page) == dict.fromkeys(ROW_PLACES, True)  # every one in the row to begin with
    assert 'name="row_hidden" value="ticked"' in page and 'role="group"' in page
    token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
    shown = [place for place in ROW_PLACES if place not in ("soon", "did")]
    saved = sam.post(
        "/settings",
        data={
            "csrf": token,
            "section": "general",
            "row_hidden": "ticked",
            "row_hidden_shown": shown,
        },
    )
    assert saved.status_code == 302
    assert app.settings.row_hidden == "soon,did"
    assert _ticks(sam.get("/settings/general").text) == {
        place: place not in ("soon", "did") for place in ROW_PLACES
    }
    assert _row(sam.get("/").text) == ["Now", "Eat", "Do", "Week", "Kids", "Lists"]
    assert _menu(sam.get("/").text)[:7] == [
        "Now",
        "Chat with Vera",
        "Eat",
        "Do",
        "Week",
        "Kids",
        "Lists",
    ]
    assert _menu(sam.get("/settings").text) == _menu(sam.get("/").text)  # one menu everywhere
    # Nothing is gone: a place taken out still opens from a link.
    assert sam.get("/soon").status_code == 200 and sam.get("/did").status_code == 200
    # Every tick again is no setting at all, and the row is whole.
    sam.post(
        "/settings",
        data={
            "csrf": token,
            "section": "general",
            "row_hidden": "ticked",
            "row_hidden_shown": list(ROW_PLACES),
        },
    )
    assert "row_hidden" not in settings_store.overrides(conn)
    assert _row(sam.get("/").text)[-1] == "Did"


def test_a_form_without_the_ticks_leaves_the_row_alone(app, conn) -> None:
    """Any other form posting to the settings (Setup's, an older page's) carries no ticks."""
    _take_out(conn, "soon")
    sam = _in_as(app, SAM)
    token = re.search(r'name="csrf" value="([^"]+)"', sam.get("/settings/general").text).group(1)
    sam.post("/settings", data={"csrf": token, "section": "general", "web_title": "The Lees"})
    assert app.settings.row_hidden == "soon" and app.settings.web_title == "The Lees"


def test_with_now_taken_out_the_page_opens_on_the_first_place_left(app, conn) -> None:
    _take_out(conn, "now,eat")
    sam = _in_as(app, SAM)
    opened = sam.get("/")
    assert opened.status_code == 302 and opened.headers["Location"] == "/do"
    assert _row(sam.get("/do").text)[0] == "Do"
    # A kid's row is her own four, less what the family took out.
    kid = _in_as(app, KID)
    assert _row(kid.get("/do").text) == ["Do", "My week", "My list"]
    assert kid.get("/").headers["Location"] == "/do"


def test_with_every_place_taken_out_now_stays(app, conn) -> None:
    _take_out(conn, ",".join(ROW_PLACES))
    sam = _in_as(app, SAM)
    page = sam.get("/")
    assert page.status_code == 200 and _row(page.text) == ["Now"]


def test_the_setting_keeps_known_places_in_the_rows_order() -> None:
    """A place this version does not know is dropped, never refused: a value another version
    stored must not stop the app."""
    said = Settings(_env_file=None, row_hidden="did, banana NOW  soon,did")
    assert said.row_hidden == "now,soon,did"
    assert said.row_hidden_places == {"now", "soon", "did"}
    assert [value for value, _ in fields.BY_KEY["row_hidden"].ticks] == list(ROW_PLACES)
