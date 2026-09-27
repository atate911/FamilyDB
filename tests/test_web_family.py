"""The Family page: the list, and adding or changing somebody from a browser."""

from __future__ import annotations

import re

import pytest

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
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
    return " ".join(re.findall(r'class="said"[^>]*>\s*([^<]+)', response.text))


def test_the_list_shows_everybody_and_how_the_bot_knows_them(page, family) -> None:
    text = page.get("/family").text
    assert "Sam" in text and "Alex" in text and "the girls" in text
    assert "Telegram 1001" in text
    assert "named in ideas and plans" in text  # a kid with no channel and no password
    assert 'href="/family"' in page.get("/plans").text  # and the bar reaches it


def test_somebody_can_be_added_from_the_page(page, conn) -> None:
    sent = page.post(
        "/family",
        data={"csrf": _token(page), "name": "Jo", "role": "parent", "telegram_id": "1003"},
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/family"
    jo = members.find_by_name(conn, "Jo")
    assert jo is not None and jo.channel_user_id == "1003"
    assert "Jo is on the family list." in _said(page.get("/family"))


def test_a_name_that_is_taken_is_refused_with_the_reason(page, conn) -> None:
    page.post("/family", data={"csrf": _token(page), "name": "SAM", "role": "parent"})
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
    form = {"csrf": _token(page), "role": "parent", "active": "yes", "telegram_id": "1002"}
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


def test_a_stranger_who_messaged_the_bot_can_be_added_from_the_page(
    page, settings, clock, conn
) -> None:
    stranger = IncomingMessage(
        "telegram", "77", "5555", "5555", "open the pod bay doors", sender_name="Robin Lee @robin"
    )
    reply = handle_incoming(App(settings, clock), stranger, conn=conn)
    assert reply.status == "unknown_sender" and "5555" in reply.text

    text = page.get("/family").text
    assert "Asked to talk to the bot" in text
    assert 'value="Robin Lee"' in text and "@robin" in text and "Telegram 5555" in text
    assert (
        "pod bay" not in re.findall(r'id="knocking".*?</section>', text, re.S)[0].split("</h2>")[1]
    )

    sent = page.post(
        "/family",
        data={"csrf": _token(page), "name": "Robin", "role": "parent", "telegram_id": "5555"},
    )
    assert sent.status_code == 302
    assert members.find_by_name(conn, "Robin").channel_user_id == "5555"
    assert "Asked to talk to the bot" not in page.get("/family").text  # gone once added


def test_a_link_is_made_for_somebody_and_shown_once(page, conn, family) -> None:
    from familydb.store import invites

    app = page.application.config["FAMILYDB_APP"]
    alex = family["alex"]
    unconnected = page.get(f"/family/{alex.id}").text
    assert "Once the Telegram bot is connected" in unconnected
    refused = page.post(
        f"/family/{alex.id}/invite", data={"csrf": _token(page)}, follow_redirects=True
    )
    assert "Connect the Telegram bot first" in refused.text  # the link would name no bot
    assert conn.execute("SELECT count(*) FROM telegram_invites").fetchone()[0] == 0
    app.channel_states["telegram"] = "connected as @tate_family_bot"
    offered = page.get(f"/family/{alex.id}").text
    assert "Make a link for Alex" in offered
    made = page.post(f"/family/{alex.id}/invite", data={"csrf": _token(page)})
    assert made.status_code == 302 and made.headers["Location"] == f"/family/{alex.id}"
    shown = page.get(f"/family/{alex.id}").text
    link = re.search(r"https://t\.me/tate_family_bot\?start=([A-Za-z0-9_-]+)", shown)
    assert link is not None and "Shown this once" in shown
    assert invites.find(conn, invites.digest(link.group(1))).member_id == alex.id
    assert "t.me/tate_family_bot?start=" not in page.get(f"/family/{alex.id}").text  # once


def test_the_list_says_how_many_messages_each_kid_has_had_today(settings, clock, conn, family):
    from familydb.store import db
    from tests import fakes
    from tests.conftest import NOW_ISO

    with db.transaction(conn):
        members.add(conn, "Mia", "kid", channel="telegram", channel_user_id="1003", now=NOW_ISO)
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("ok")]))
    handle_incoming(app, IncomingMessage("telegram", "u1", "c", "1003", "hi"), api=api, conn=conn)
    client = create_app(app).test_client()
    client.post("/login", data={"password": PASSWORD})
    assert "messages today" not in client.get("/family").text  # no number set, nothing counted

    with db.transaction(conn):
        from familydb.store import settings as settings_store

        settings_store.set_many(conn, {"kid_daily_messages": 10})
    text = client.get("/family").text
    assert "1 of 10 messages today" in text
    assert text.count("messages today") == 2  # Mia, and the girls; never a grown-up


def test_somebody_can_be_taken_off_for_good_once_the_box_is_ticked(page, conn, family) -> None:
    alex = family["alex"]
    drawn = page.get(f"/family/{alex.id}").text
    assert f'action="/family/{alex.id}/remove"' in drawn and 'name="sure"' in drawn
    form = {"csrf": _token(page), "revision": _revision(page, alex.id)}
    unsure = page.post(f"/family/{alex.id}/remove", data=form)
    assert unsure.headers["Location"] == f"/family/{alex.id}"
    assert "Tick the box" in _said(page.get(f"/family/{alex.id}"))
    assert members.get(conn, alex.id) is not None

    sure = page.post(f"/family/{alex.id}/remove", data={**form, "sure": "yes"})
    assert sure.headers["Location"] == "/family"
    assert "Alex is off the family list for good" in _said(page.get("/family"))
    assert members.get(conn, alex.id) is None
    listed = re.search(r'<ul class="panel plain people">.*?</ul>', page.get("/family").text, re.S)
    assert "Alex" not in listed.group(0) and "Sam" in listed.group(0)
    assert page.get(f"/family/{alex.id}").status_code == 404
