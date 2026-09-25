"""The voice layer: what she says unasked, and a conversation under way carrying it for her."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from familydb import personas, voice
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.jobs.reminders import run_reminders
from familydb.pipeline import handle_incoming
from familydb.store import messages, tasks
from tests import fakes

# -- the lines -----------------------------------------------------------------------------------


def test_plain_then_hers_then_the_family_s(settings) -> None:
    facts = {"title": "Buy paper towels", "who": " (Sam)", "task": 4}
    plain = settings.model_copy(update={"persona": "none"})
    assert voice.say(plain, "reminder", **facts).startswith("Reminder: Buy paper towels (Sam)  -")
    assert voice.say(settings, "reminder", **facts) == (
        "Reminder: Buy paper towels (Sam). Task #4; tell me when it's done, or I can snooze it."
    )
    own = settings.model_copy(update={"voice_lines": {"reminder": "Psst: {title}, #{task}."}})
    assert voice.say(own, "reminder", **facts) == "Psst: Buy paper towels, #4."
    # no persona is plain throughout, the family's own lines included, which are kept for later
    own_but_plain = own.model_copy(update={"persona": "none"})
    assert voice.say(own_but_plain, "reminder", **facts) == voice.say(plain, "reminder", **facts)


def test_a_line_that_cannot_be_used_is_said_plainly(settings) -> None:
    broken = settings.model_copy(update={"voice_lines": {"follow_up": "How was {venue}?"}})
    assert voice.say(broken, "follow_up", plan="Hopscotch", day="Saturday") == (
        "How was Hopscotch on Saturday? Worth doing again?"
    )


def test_every_line_a_persona_ships_with_is_usable() -> None:
    for key in personas.available():
        shipped = dict(personas.load(key).lines)
        assert voice.problems(shipped) == {}, key
        assert set(shipped) <= set(voice.EVENTS), key


def test_her_name_is_the_persona_s_to_give(settings, monkeypatch) -> None:
    assert voice.say(settings, "start").startswith("Hi, I'm Vera.")
    plain = settings.model_copy(update={"persona": "none"})
    assert voice.say(plain, "start").startswith("Hi! I'm FamilyDB, the family's")
    # Named otherwise, she introduces herself by that name, whatever a caller passes.
    juno = replace(personas.load(personas.DEFAULT), name="Juno")
    monkeypatch.setattr(personas, "active", lambda _settings: juno)
    assert voice.say(settings, "start", name="Hal").startswith("Hi, I'm Juno.")


def test_any_line_can_say_her_name(settings) -> None:
    own = settings.model_copy(update={"voice_lines": {"follow_up": "{name} here: how was {plan}?"}})
    assert voice.say(own, "follow_up", plan="Hopscotch", day="Saturday") == (
        "Vera here: how was Hopscotch?"
    )
    assert voice.problems({"done": "{name} did it."}) == {}
    refused = voice.problems({"follow_up": "How was {venue}?"})["follow_up"]
    assert refused.endswith("it can use {name}, {plan}, {day}")


def test_what_is_wrong_with_a_written_line_is_named() -> None:
    found = voice.problems(
        {"reminder": "Do {thing} now", "follow_up": "How was {plan", "nonsense": "x"}
    )
    assert "{thing} is not something it knows" in found["reminder"]
    assert "{title}" in found["reminder"]  # and it says what it could use
    assert "not closed" in found["follow_up"]
    assert "no 'nonsense' message" in found["nonsense"]


# -- a conversation under way carries what comes due ---------------------------------------------


@pytest.fixture
def talking(settings, clock, conn, family):
    """Sam asked for a reminder at 14:05 at 14:03, in chat-1; the job runs at 14:05."""
    app = App(settings, clock)
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    handle_incoming(
        app,
        IncomingMessage("telegram", "u1", "chat-1", "1001", "remind me at 14:05 to call grandma"),
        api=fakes.FakeMessagesAPI(
            fakes.message(
                [
                    fakes.tool_use(
                        "t1", "add_task", {"title": "Call grandma", "remind_at": "2026-09-20T14:05"}
                    )
                ]
            ),
            fakes.message([fakes.text("Set for 14:05.")]),
        ),
        conn=conn,
    )
    clock.advance(timedelta(minutes=2))
    assert run_reminders(app) == 1
    reminder = tasks.list_all(conn)[0].reminder
    assert sent == [] and app.held.is_held(reminder.message_id, clock.now())
    return app, sent, reminder.message_id


def _next(app, conn, reply_text):
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text(reply_text)]))
    out = handle_incoming(
        app,
        IncomingMessage("telegram", "u2", "chat-1", "1001", "thanks, what's for dinner?"),
        api=api,
        conn=conn,
    )
    return out, json.dumps(api.requests[0]["messages"][-1])


def test_the_next_reply_carries_it(talking, conn, clock) -> None:
    app, sent, held_id = talking
    out, asked = _next(app, conn, "Pasta tonight. And it's time to call grandma (task #1).")
    assert "Also due in this chat just now" in asked and "Call grandma" in asked
    assert out.text == "Pasta tonight. And it's time to call grandma (task #1)."
    assert messages.get(conn, held_id).delivered_at is not None  # sent with the reply
    clock.advance(timedelta(minutes=5))
    assert run_reminders(app) == 0 and sent == []  # and never on its own as well


def test_a_reply_that_forgets_it_takes_the_written_line(talking, conn) -> None:
    app, _, held_id = talking
    out, _ = _next(app, conn, "Pasta tonight.")
    assert out.text.startswith("Pasta tonight.\n\nReminder: Call grandma")
    assert messages.get(conn, held_id).delivered_at is not None


def test_no_conversation_in_time_sends_it_as_written(talking, clock) -> None:
    app, sent, _ = talking
    clock.advance(timedelta(minutes=3))
    assert run_reminders(app) == 1
    assert sent == [("chat-1", sent[0][1])] and sent[0][1].startswith("Reminder: Call grandma")


def test_a_failed_turn_lets_it_go_at_once(talking, conn, clock) -> None:
    app, sent, _ = talking
    handle_incoming(
        app,
        IncomingMessage("telegram", "u3", "chat-1", "1001", "hello?"),
        api=fakes.FakeMessagesAPI(fakes.server_error(), fakes.server_error(), fakes.server_error()),
        conn=conn,
    )
    assert run_reminders(app) == 1  # released without waiting out the hold
    assert any(text.startswith("Reminder: Call grandma") for _, text in sent)


def test_a_quiet_chat_gets_it_straight_away(settings, clock, conn, family) -> None:
    from familydb.tools import ToolContext
    from familydb.tools.tasks import AddTaskInput, add_task

    app = App(settings, clock)
    sent = []
    app.senders["web"] = lambda chat, text: sent.append(text)
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    add_task(ctx, AddTaskInput(title="Water the plants", remind_at="2026-09-20T14:05"))
    clock.advance(timedelta(minutes=2))
    assert run_reminders(app) == 1 and sent[0].startswith("Reminder: Water the plants")
