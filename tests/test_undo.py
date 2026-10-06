"""Taking back the last change (familydb/undo.py): said in the chat, /undo, the button under a
reply, and the page's Undo; only what is as that change left it, only once, only whose it is."""

from __future__ import annotations

import json
import re
from datetime import timedelta

import pytest

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
from familydb.store import db, ideas, memories, messages, plans, tasks
from familydb.tools import ToolContext, build_registry
from tests import fakes
from tests.conftest import NOW_ISO, call

REGISTRY = build_registry()


def _said(conn, member, text: str, update: str, chat: str = "42") -> int:
    """A message somebody sent, for the calls a turn makes to belong to."""
    with db.transaction(conn):
        return messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=update,
            chat_id=chat,
            member_id=member.id,
            text=text,
            now=NOW_ISO,
        ).id


def _as(settings, clock, conn, member, message_id=None, **more) -> ToolContext:
    return ToolContext(
        conn=conn, settings=settings, clock=clock, member=member, message_id=message_id, **more
    )


def _run(ctx: ToolContext, name: str, **args):
    result = REGISTRY.dispatch(name, args, ctx)
    return result, json.loads(result.content)


def test_saying_undo_takes_back_the_last_change_in_this_chat_once(settings, clock, conn, family):
    sam = family["sam"]
    asked = _said(conn, sam, "remind me to call the plumber", "u1")
    _run(_as(settings, clock, conn, sam, asked), "add_task", title="Call the plumber")
    elsewhere = _said(conn, sam, "and the gutters", "u2", chat="-100")
    _run(_as(settings, clock, conn, sam, elsewhere), "add_task", title="Gutters")
    undo = _as(settings, clock, conn, sam, _said(conn, sam, "undo that", "u3"))
    result, said = _run(undo, "undo")
    assert not result.is_error and said == {"undone": "added task #1 Call the plumber"}
    assert tasks.get(conn, 1).status == "cancelled"
    assert tasks.get(conn, 2).status == "open"  # said in another chat
    again, said = _run(undo, "undo")
    assert again.is_error and "nothing of yours to undo" in said["error"]
    # A day on, a change is no longer taken back.
    later = _said(conn, sam, "remind me about the car", "u4")
    _run(_as(settings, clock, conn, sam, later), "add_task", title="The car")
    clock.advance(timedelta(hours=25))
    late = _as(settings, clock, conn, sam, _said(conn, sam, "undo", "u5"))
    assert "nothing of yours to undo" in _run(late, "undo")[1]["error"]


def test_an_idea_changed_is_put_back_unless_it_changed_again(settings, clock, conn, family):
    sam = family["sam"]
    first = _said(conn, sam, "ramen place", "u1")
    _run(_as(settings, clock, conn, sam, first), "add_idea", title="Ramen", kind="restaurant")
    fix = _said(conn, sam, "call it Ramen Ichiban, cheap", "u2")
    _run(
        _as(settings, clock, conn, sam, fix),
        "update_idea",
        id=1,
        title="Ramen Ichiban",
        cost_level=1,
    )
    undo = _as(settings, clock, conn, sam, _said(conn, sam, "undo", "u3"))
    assert _run(undo, "undo")[1] == {"undone": "changed idea #1 Ramen Ichiban"}
    back = ideas.get(conn, 1)
    assert back.title == "Ramen" and back.cost_level is None  # unset again, which no tool can do
    # The add before it is next; changed since by somebody else, it is left alone.
    alex = _as(settings, clock, conn, family["alex"], _said(conn, family["alex"], "x", "u4"))
    _run(alex, "update_idea", id=1, status="planned")
    result, said = _run(undo, "undo")
    assert result.is_error and "changed since" in said["error"]
    assert ideas.get(conn, 1).status == "planned"


def test_a_one_off_marked_done_reopens_with_its_reminder(settings, clock, conn, family):
    sam = family["sam"]
    made = _said(conn, sam, "remind me", "u1")
    added = _run(
        _as(settings, clock, conn, sam, made),
        "add_task",
        title="Bins out",
        remind_at="2026-09-21T19:00",
    )[1]
    done = _said(conn, sam, "done with the bins", "u2")
    _run(
        _as(settings, clock, conn, sam, done),
        "update_task",
        task_id=added["task"]["id"],
        status="done",
    )
    assert tasks.get(conn, 1).reminder is None
    undo = _as(settings, clock, conn, sam, _said(conn, sam, "undo", "u3"))
    assert _run(undo, "undo")[1] == {"undone": "marked task #1 Bins out done"}
    task = tasks.get(conn, 1)
    assert task.status == "open" and task.reminder.remind_at == "2026-09-22T02:00:00Z"


def test_a_repeating_round_or_an_outcome_is_not_offered(settings, clock, conn, family):
    sam = family["sam"]
    made = _said(conn, sam, "bins every week", "u1")
    _run(
        _as(settings, clock, conn, sam, made),
        "add_task",
        title="Bins",
        remind_at="2026-09-21T19:00",
        repeat_every=1,
        repeat_unit="week",
    )
    done = _said(conn, sam, "bins done", "u2")
    result = _run(_as(settings, clock, conn, sam, done), "update_task", task_id=1, status="done")[0]
    assert not result.undoable
    rows = conn.execute("SELECT tool_name, undo IS NOT NULL AS can FROM tool_calls ORDER BY id")
    assert [tuple(row) for row in rows] == [("add_task", 1), ("update_task", 0)]


def test_a_kid_may_undo_only_her_own_things_to_do(settings, clock, conn, family):
    sam, girls = family["sam"], family["girls"]
    parent = _said(conn, sam, "remind the girls", "u1", chat="7")
    _run(_as(settings, clock, conn, sam, parent), "add_task", title="Tidy up", owner="the girls")
    kid = _as(settings, clock, conn, girls, _said(conn, girls, "undo", "u2", chat="7"))
    assert "nothing of yours to undo" in _run(kid, "undo")[1]["error"]
    target = conn.execute("SELECT id FROM tool_calls").fetchone()[0]
    pressed = _as(settings, clock, conn, girls, undo_target=target)
    assert "only your own" in _run(pressed, "undo")[1]["error"]
    hers = _said(conn, girls, "done!", "u3", chat="7")
    _run(_as(settings, clock, conn, girls, hers), "update_task", task_id=1, status="done")
    assert _run(kid, "undo")[1] == {"undone": "marked task #1 Tidy up done"}


def test_a_plan_made_or_moved_is_put_back_on_the_calendar_too(env):
    _, made = call(
        env, "create_event", title="Zoo", start="2026-09-26T10:00", remind_before=["1 day"]
    )
    event_id = made["plan"]["google_event_id"]
    plan_id = made["plan"]["id"]
    call(env, "update_event", plan_id=plan_id, start="2026-09-27T10:00")
    env.ctx.undo_target = env.conn.execute("SELECT max(id) FROM tool_calls").fetchone()[0]
    assert call(env, "undo")[1] == {"undone": "changed plan #1 Zoo"}
    assert plans.get(env.conn, plan_id).start.startswith("2026-09-26T10:00")
    assert env.cal.get_event(event_id).start.day == 26
    env.ctx.undo_target = env.conn.execute(
        "SELECT min(id) FROM tool_calls WHERE tool_name = 'create_event'"
    ).fetchone()[0]
    assert call(env, "undo")[1] == {"undone": "put Zoo on the calendar (plan #1)"}
    assert plans.get(env.conn, plan_id).status == "cancelled"
    assert env.cal.get_event(event_id) is None
    assert [task.status for task in tasks.list_all(env.conn, status="all")] == ["cancelled"]


def test_something_remembered_by_mistake_is_forgotten(settings, clock, conn, family):
    sam = family["sam"]
    said = _said(conn, sam, "Alex hates sushi", "u1")
    change = {"action": "add", "about": "Alex", "fact": "hates sushi", "category": "food"}
    _run(_as(settings, clock, conn, sam, said), "remember", changes=[change])
    undo = _as(settings, clock, conn, sam, _said(conn, sam, "no, undo that", "u2"))
    assert _run(undo, "undo")[1] == {"undone": "remembered hates sushi"}
    assert memories.get(conn, 1).status == "forgotten"


def _tg(text: str, update: str) -> IncomingMessage:
    return IncomingMessage("telegram", update, "chat-1", "1001", text)


def test_undo_is_a_command_and_a_button_under_the_reply(settings, clock, conn, family):
    from familydb import buttons, commands

    app = App(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_task", {"title": "Call the plumber"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Added #1 Call the plumber.")]),
    )
    reply = handle_incoming(app, _tg("remind me to call the plumber", "1"), api=api, conn=conn)
    undo_buttons = [b for b in reply.buttons if b["data"].startswith("undo:")]
    assert undo_buttons == buttons.for_undo(int(undo_buttons[0]["data"][5:]))
    tapped = buttons.tap(
        app,
        conn,
        channel="telegram",
        chat_id="chat-1",
        channel_user_id="1001",
        tap_id="t1",
        data=undo_buttons[0]["data"],
    )
    assert tapped.note == "Undone (Sam): added task #1 Call the plumber."
    assert tasks.get(conn, 1).status == "cancelled"
    again = buttons.tap(
        app,
        conn,
        channel="telegram",
        chat_id="chat-1",
        channel_user_id="1001",
        tap_id="t2",
        data=undo_buttons[0]["data"],
    )
    assert again.toast == "That one's already taken care of." and again.finished
    asked = commands.answer(app, _tg("/undo", "2"))
    assert asked.text == "Nothing undone: nothing of yours to undo here from the last day."


def test_a_reply_in_a_group_carries_no_undo(settings, clock, conn, family):
    app = App(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_task", {"title": "Gutters"})], stop_reason="tool_use"
        ),
        fakes.message([fakes.text("Added.")]),
    )
    group = IncomingMessage("telegram", "1", "-100", "1001", "gutters")
    assert handle_incoming(app, group, api=api, conn=conn).buttons == []


@pytest.fixture
def page(settings, clock, conn, family):
    from tests.test_web_edits import _client

    return _client(settings, clock)


def test_the_page_offers_undo_beside_the_notice_and_under_her_reply(
    page, settings, clock, conn, family
):
    from tests.test_web_edits import _idea_form

    added = page.post("/ideas/new", data=_idea_form(page, who="Sam"), follow_redirects=True)
    form = re.search(r'<form class="undo-form"[^>]*>(.*?)</form>', added.text, re.S)
    assert form is not None
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form.group(1)))
    assert fields["back"] == "/idea/1"
    undone = page.post("/undo", data=fields, follow_redirects=True)
    assert "Undone: added idea #1 Ramen place." in undone.text
    assert ideas.get(conn, 1).status == "dropped"
    assert 'class="undo-form"' not in undone.text  # an undo is not undone
    # Under her reply in the chat, for the change its turn made.
    with db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="w1",
            chat_id="web",
            member_id=family["sam"].id,
            text="remind me to call the plumber",
            now=NOW_ISO,
        )
    _run(_as(settings, clock, conn, family["sam"], asked.id), "add_task", title="Call the plumber")
    with db.transaction(conn):
        messages.mark_processed(conn, asked.id, [], now=NOW_ISO)
        messages.insert_out(
            conn, channel="web", chat_id="web", text="Added.", reply_to=asked.id, now=NOW_ISO
        )
    chat = page.get("/chat").text
    form = re.search(r'<form class="undo-form"[^>]*>(.*?)</form>', chat, re.S)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form.group(1)))
    assert fields["back"] == "/chat#latest"
    page.post("/undo", data=fields)
    assert tasks.get(conn, 1).status == "cancelled"
    assert 'class="undo-form"' not in page.get("/chat").text
