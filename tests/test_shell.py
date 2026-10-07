"""The frame around the page (templates/base.html, web/shell.py): who sees which pages in
the menu, the health pill, and the counts by a page's name. Read on `/more`, the phone's menu,
which is the first page built on it."""

from __future__ import annotations

import re
from contextlib import closing

import pytest

from familydb import family as rules
from familydb.app import App
from familydb.store import db, members, tasks
from familydb.web import create_app
from tests.conftest import NOW_ISO

PASSWORDS = {"Sam": "sam likes long sentences", "Alex": "alex chose this one today"}
KID = "a kid can choose one too"


@pytest.fixture
def app(settings, clock, conn, family):
    live = App(settings.model_copy(update={"web_password": "installer-made-password-1"}), clock)
    # Everybody signs in as themselves, kids included.
    for key, word in (("sam", PASSWORDS["Sam"]), ("alex", PASSWORDS["Alex"]), ("girls", KID)):
        rules.choose_password(conn, family[key].id, word, now=NOW_ISO)
    return live


def _in_as(app, name: str, password: str):
    client = create_app(app).test_client()
    assert client.post("/login", data={"name": name, "password": password}).status_code == 302
    return client


@pytest.fixture
def sam(app):
    return _in_as(app, "Sam", PASSWORDS["Sam"])


@pytest.fixture
def alex(app):
    return _in_as(app, "Alex", PASSWORDS["Alex"])


@pytest.fixture
def girl(app):
    return _in_as(app, "the girls", KID)


def _sidebar(client) -> str:
    html = client.get("/more").text
    return re.search(r'<aside class="side".*?</aside>', html, re.S).group(0)


def _tabbar(client) -> str:
    return re.search(r'<nav class="tabbar".*?</nav>', client.get("/more").text, re.S).group(0)


def _late_task(conn, owner_id: int, title: str = "Call the dentist") -> None:
    with db.transaction(conn):
        tasks.insert(
            conn,
            title=title,
            notes="",
            owner_id=owner_id,
            due_at="2026-09-18T19:00:00Z",  # the Friday before the clock's Sunday
            preferred_window="",
            operation_key=f"late-{title}-{owner_id}",
            channel="web",
            chat_id="web",
            now=NOW_ISO,
        )


# -- who is in the menu


def test_an_admin_sees_every_page_and_what_is_behind_the_scenes(sam) -> None:
    side = _sidebar(sam)
    for page in ("Home", "Chat with Vera", "Ideas", "Plans", "To do", "Kids\u2019 lists"):
        assert f"<span>{page}</span>" in side, page
    assert "What Vera knows" in side
    assert 'class="overline nav-group"' in side and "Behind the scenes" in side
    for target in ('href="/status"', 'href="/settings"', 'href="/family"'):
        assert target in side, target
    assert "Signed in" not in side and "<b>Sam</b>" in side and "Admin" in side
    assert 'class="me__acts"' in side and 'href="/look"' in side and 'href="/you"' in side
    assert 'action="/logout"' in side and "Sign out" in side


def test_a_parent_gets_status_but_not_settings_or_the_family_list(alex) -> None:
    side = _sidebar(alex)
    assert "Behind the scenes" in side and 'href="/status"' in side
    assert 'href="/settings"' not in side and 'href="/family"' not in side
    assert "Kids\u2019 lists" in side and "What Vera knows" in side
    page = alex.get("/more").text
    assert 'href="/settings"' not in page and 'href="/family"' not in page
    assert "Status" in page


def test_a_kid_sees_her_own_pages_and_nothing_of_how_it_works(girl) -> None:
    side = _sidebar(girl)
    assert "Behind the scenes" not in side
    for gone in ("/status", "/settings", "/family", "/memory", "What Vera knows"):
        assert gone not in side, gone
    assert "<span>My to-dos</span>" in side and "<span>My list</span>" in side
    assert "pill-health" not in girl.get("/more").text  # never a pill, or money, for a kid
    tabs = _tabbar(girl)
    assert "My list" in tabs and "Ideas" not in tabs  # her list where a grown-up has Ideas
    menu = girl.get("/more").text
    assert 'href="/ideas"' in menu  # and Ideas is in her menu
    assert "Behind the scenes" not in menu and "Settings" not in menu
    # No version number on a kid's footer.
    assert "Version" not in menu.split('<footer class="foot">')[1]


def test_a_grown_up_phone_menu_keeps_the_five_tabs(sam) -> None:
    tabs = _tabbar(sam)
    for page in ("Home", "Chat", "Ideas", "Plans", "To do"):
        assert f"<span>{page}</span>" in tabs, page
    assert tabs.count("<a ") == 5


def test_the_page_can_be_skipped_to_and_names_its_language(sam) -> None:
    html = sam.get("/more").text
    assert '<a class="skip" href="#main">Skip to content</a>' in html
    assert 'id="main"' in html and '<html lang="en-US"' in html
    assert "style.css" in html and "fonts/atkinson-400.woff2" in html


def test_somebody_who_is_not_signed_in_gets_no_menu(app) -> None:
    client = create_app(app).test_client()
    assert client.get("/more").status_code == 302


# -- the pill


def test_a_grown_up_is_told_how_she_is_and_it_says_the_same_in_the_bar_and_the_menu(sam) -> None:
    html = sam.get("/more").text
    assert html.count("Vera is ready") >= 3  # sidebar, phone bar and the menu's Status row
    assert 'class="pill-health"' in html


def test_the_day_s_limit_reached_is_told_as_resting_until_midnight(app, sam, conn) -> None:
    live = app.settings.model_copy(update={"daily_spend_limit": 0.01})
    app.settings = live
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO llm_calls (iteration, model, created_at, cost_usd) VALUES (1, 'm', ?, 1)",
            ("2026-09-20T20:00:00Z",),
        )
    html = sam.get("/more").text
    assert "Vera is resting until midnight" in html and "pill-health--rest" in html


# -- the counts


def test_late_to_dos_are_counted_for_a_grown_up_and_a_kid_counts_only_her_own(
    sam, girl, conn, family
) -> None:
    _late_task(conn, family["sam"].id)
    _late_task(conn, family["alex"].id, "Renew the car")
    _late_task(conn, family["girls"].id, "Feed the fish")
    assert 'badge--late">3 late' in _sidebar(sam)
    assert 'badge--late">1 late' in _sidebar(girl)
    assert '3<span class="sr"> late</span>' in _tabbar(sam)


def test_nothing_is_counted_when_nothing_is_late(sam) -> None:
    assert "badge--late" not in _sidebar(sam)


def test_a_dot_on_the_phone_picture_says_something_is_worth_a_look(sam, conn, family) -> None:
    def things() -> int:
        top = sam.get("/more").text.split('<aside class="side"')[0]
        found = re.search(r"your menu, (\d+) things? to look at", top)
        assert (found is not None) == ('class="dot"' in top)  # the dot and the words agree
        return int(found.group(1)) if found else 0

    before = things()
    _late_task(conn, family["sam"].id)
    assert things() == before + 1


# -- the colours people wear


def test_each_person_has_their_own_colour_and_it_does_not_follow_their_name(conn, family) -> None:
    assert [family[key].slot for key in ("sam", "alex", "girls")] == [1, 2, 3]
    with closing(db.connect(conn.execute("PRAGMA database_list").fetchone()[2])) as other:
        stored = members.get(other, family["alex"].id)
        assert stored is not None and stored.slot == 2
    renamed = members.update_profile(
        conn,
        family["alex"].id,
        display_name="Alexandra",
        role="parent",
        active=True,
        channel="telegram",
        channel_user_id="1002",
    )
    assert renamed is not None and renamed.slot == 2


def test_the_page_you_are_on_is_marked_in_the_menu_and_the_tab_bar(sam, girl) -> None:
    """Home is the first page on the frame; each of its two places for a page's name marks it
    as current, once, for a screen reader as well as the eye."""
    home = sam.get("/").text
    side = re.search(r'<aside class="side".*?</aside>', home, re.S).group(0)
    tabs = re.search(r'<nav class="tabbar".*?</nav>', home, re.S).group(0)
    for where in (side, tabs):
        assert where.count('aria-current="page"') == 1
        assert re.search(r'<a href="/" aria-current="page">', where)
    # The account corner marks Look while you are on it.
    look = sam.get("/more").text  # a page of its own: none of the pages is current there
    assert (
        re.search(r'<aside class="side".*?</aside>', look, re.S).group(0).count("aria-current") == 0
    )
    # A kid's Home marks hers.
    kid = girl.get("/").text
    assert re.search(r'<a href="/" aria-current="page">', kid)
