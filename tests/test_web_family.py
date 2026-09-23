"""The Family page: the list, and adding or changing somebody from a browser."""

from __future__ import annotations

import re

import pytest

from familydb.app import App
from familydb.store import members
from familydb.web import create_app

PASSWORD = "open sesame please"


@pytest.fixture
def page(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def _token(client, path: str = "/family") -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get(path).text)
    assert found is not None
    return found.group(1)


def _revision(client, member_id: int) -> str:
    found = re.search(r'name="revision" value="([^"]+)"', client.get(f"/family/{member_id}").text)
    assert found is not None
    return found.group(1)


def _said(response) -> str:
    return " ".join(re.findall(r'class="said">\s*([^<]+)', response.text))


def test_the_list_shows_everybody_and_how_the_bot_knows_them(page, family) -> None:
    text = page.get("/family").text
    assert "Sam" in text and "Alex" in text and "the girls" in text
    assert "Telegram 1001" in text
    assert "named in ideas, does not message the bot" in text  # a kid with no channel
    assert 'href="/family"' in page.get("/plans").text  # and the bar reaches it


def test_somebody_can_be_added_from_the_page(page, conn) -> None:
    sent = page.post(
        "/family",
        data={"csrf": _token(page), "name": "Jo", "role": "member", "telegram_id": "1003"},
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/family"
    jo = members.find_by_name(conn, "Jo")
    assert jo is not None and jo.channel_user_id == "1003"
    assert "Jo is on the family list." in _said(page.get("/family"))


def test_a_name_that_is_taken_is_refused_with_the_reason(page, conn) -> None:
    page.post("/family", data={"csrf": _token(page), "name": "SAM", "role": "member"})
    assert "already somebody called Sam" in _said(page.get("/family"))
    assert len(members.list_all(conn, active_only=False)) == 3


def test_somebody_can_be_changed_from_the_page(page, conn, family) -> None:
    alex = family["alex"]
    sent = page.post(
        f"/family/{alex.id}",
        data={
            "csrf": _token(page),
            "revision": _revision(page, alex.id),
            "name": "Alexandra",
            "role": "admin",
            "active": "yes",
            "telegram_id": "1002",
        },
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/family"
    changed = members.get(conn, alex.id)
    assert changed.display_name == "Alexandra" and changed.role == "admin"


def test_the_last_admin_cannot_be_switched_off_from_the_page(page, conn, family) -> None:
    sam = family["sam"]
    page.post(
        f"/family/{sam.id}",
        data={
            "csrf": _token(page),
            "revision": _revision(page, sam.id),
            "name": "Sam",
            "role": "admin",
            "active": "no",
            "telegram_id": "1001",
        },
    )
    assert "only admin" in _said(page.get(f"/family/{sam.id}"))
    assert members.get(conn, sam.id).active


def test_a_form_drawn_before_somebody_else_saved_is_refused(page, conn, family) -> None:
    alex = family["alex"]
    stale = _revision(page, alex.id)
    form = {"csrf": _token(page), "role": "member", "active": "yes", "telegram_id": "1002"}
    page.post(f"/family/{alex.id}", data={**form, "revision": stale, "name": "Al"})
    page.post(f"/family/{alex.id}", data={**form, "revision": stale, "name": "Lex"})
    assert "changed since you opened" in _said(page.get(f"/family/{alex.id}"))
    assert members.get(conn, alex.id).display_name == "Al"


def test_the_family_forms_refuse_another_site_and_a_stale_token(page, conn, family) -> None:
    elsewhere = {"Origin": "https://evil.example"}
    page.post("/family", data={"csrf": _token(page), "name": "Mallory"}, headers=elsewhere)
    assert "did not come from this page" in _said(page.get("/family"))
    page.post("/family", data={"csrf": "not-this-session", "name": "Mallory"})
    assert "too old to use" in _said(page.get("/family"))
    assert members.find_by_name(conn, "Mallory") is None


def test_the_family_page_is_behind_the_password(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    stranger = create_app(app).test_client()
    assert stranger.get("/family").status_code == 302
    assert stranger.post("/family", data={"name": "Mallory"}).status_code == 401
    assert members.find_by_name(conn, "Mallory") is None
