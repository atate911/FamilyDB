"""The family's lists (tools/lists.py): "we're out of milk" goes on the shopping list, kept once
however it is written, ticked from Telegram or the page, and taken back with undo."""

from __future__ import annotations

import json
import re

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.store import db, messages
from familydb.tools import ToolContext, build_registry
from tests.conftest import NOW_ISO
from tests.test_web_logins import KIDS, _start, _tokens, app, sam  # noqa: F401
from tests.test_web_logins import _as as _browser_as

REGISTRY = build_registry()


def _as(conn, settings, clock, member, message_id=None):
    return ToolContext(
        conn=conn, settings=settings, clock=clock, member=member, message_id=message_id
    )


def _list(ctx, **args):
    result = REGISTRY.dispatch("shopping_list", args, ctx)
    return result, json.loads(result.content)


def test_a_thing_goes_on_the_list_once_however_it_is_written(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _, said = _list(us, action="add", items=["Milk", "eggs", "bin bags"])
    assert said == {"list": "shopping", "add": ["Milk", "eggs", "bin bags"], "open": 3}
    _, said = _list(us, action="add", items=["some milk", "Eggs."])
    assert said["already"] == ["some milk", "Eggs."] and said["open"] == 3
    _list(us, action="tick", items=["milk"])
    _, shown = _list(us, action="show")
    assert shown == {"list": "shopping", "to_get": ["eggs", "bin bags"], "ticked": ["Milk"]}
    _, said = _list(us, action="add", items=["milk"])  # wanted again
    assert said["add"] == ["Milk"] and said["open"] == 3
    _list(us, action="add", items=["screws"], name="Hardware")
    assert _list(us, action="show", name="hardware")[1]["to_get"] == ["screws"]
    _list(us, action="tick", items=["eggs"])
    assert _list(us, action="clear_ticked")[1] == {"list": "shopping", "cleared": 1, "open": 2}
    _, said = _list(us, action="remove", items=["avocados"])
    assert said["not_on_it"] == ["avocados"]


def test_a_kid_reads_the_list_and_asks_a_grown_up_to_add(settings, clock, conn, family):
    _list(_as(conn, settings, clock, family["sam"]), action="add", items=["milk"])
    kid = _as(conn, settings, clock, family["girls"])
    assert _list(kid, action="show")[1]["to_get"] == ["milk"]
    refused, said = _list(kid, action="add", items=["candy"])
    assert refused.is_error and "ask a parent" in said["error"]


def test_a_list_change_is_taken_back_with_undo(settings, clock, conn, family):
    with db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="u1",
            chat_id="42",
            member_id=family["sam"].id,
            text="we're out of milk",
            now=NOW_ISO,
        )
        again = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="u2",
            chat_id="42",
            member_id=family["sam"].id,
            text="undo that",
            now=NOW_ISO,
        )
    _list(_as(conn, settings, clock, family["sam"], asked.id), action="add", items=["milk"])
    undone = REGISTRY.dispatch("undo", {}, _as(conn, settings, clock, family["sam"], again.id))
    assert json.loads(undone.content) == {"undone": "added milk on the shopping list"}
    assert _list(_as(conn, settings, clock, family["sam"]), action="show")[1]["to_get"] == []


def test_slash_list_shows_it_with_a_tick_for_each(settings, clock, conn, family):
    from familydb import buttons, commands

    running = App(settings, clock)
    asked = commands.answer(running, IncomingMessage("telegram", "1", "42", "1001", "/list"))
    assert asked.text == "Nothing on the shopping list."
    _list(_as(conn, settings, clock, family["sam"]), action="add", items=["milk", "eggs"])
    asked = commands.answer(running, IncomingMessage("telegram", "2", "42", "1001", "/list"))
    assert asked.text == "On the shopping list:\nmilk\neggs"
    assert [b["data"] for b in asked.buttons] == ["tick:1", "tick:2"]
    assert asked.buttons[0]["label"] == "✓ milk" and asked.buttons[0]["row"] == "1"
    tapped = buttons.tap(
        running,
        conn,
        channel="telegram",
        chat_id="42",
        channel_user_id="1001",
        tap_id="t1",
        data="tick:1",
    )
    assert tapped.note == "Got it ✓ milk (Sam)."
    assert _list(_as(conn, settings, clock, family["sam"]), action="show")[1]["to_get"] == ["eggs"]


def test_the_lists_page_adds_and_ticks_through_the_same_tool(settings, clock, conn, family):
    from tests.test_web_edits import _client, _said

    page = _client(settings, clock)
    shown = page.get("/lists").text
    assert "Shopping list" in shown and "Nothing on it." in shown
    token = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', shown))
    added = page.post(
        "/lists/change",
        data={**token, "action": "add", "name": "shopping", "items": "milk\neggs\n\nmilk"},
        follow_redirects=True,
    )
    assert "Added to the shopping list: milk, eggs." in _said(added)
    form = re.search(r'name="action" value="tick" />.*?name="items" value="milk"', added.text, re.S)
    assert form is not None
    ticked = page.post(
        "/lists/change",
        data={
            "csrf": token["csrf"],
            "once": "t",
            "action": "tick",
            "name": "shopping",
            "items": "milk",
        },
        follow_redirects=True,
    )
    assert "Got: milk." in _said(ticked) and "<s>milk</s>" in ticked.text


def test_a_grown_up_finds_the_lists_on_a_phone_and_a_kid_does_not(app, sam, family):  # noqa: F811
    assert 'href="/lists"' in sam.get("/more").text  # the phone's menu: the list at the shop
    kid = _browser_as(app, "the girls", _start(sam, family["girls"].id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    assert 'href="/lists"' not in kid.get("/more").text
    assert 'href="/lists"' not in kid.get("/").text
    assert kid.get("/lists").status_code == 403
