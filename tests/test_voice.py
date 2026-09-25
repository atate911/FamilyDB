"""The voice layer: what she says unasked, and a conversation under way carrying it for her."""

import json
import os
import subprocess
import sys
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


# -- several wordings for a line -----------------------------------------------------------------

# Three wordings of a follow-up, as the family would type them into its box, a blank row and all.
THREE = "One: {plan}.\n\n  Two: {plan}.\nThree: {plan}.\n"
SAID = {"One: Hopscotch.", "Two: Hopscotch.", "Three: Hopscotch."}


def _asked(settings, seed=None, **facts) -> str:
    return voice.say(settings, "follow_up", seed=seed, **{"plan": "Hopscotch", **facts})


def test_a_line_of_several_wordings_takes_turns_the_same_way_every_time(settings) -> None:
    own = settings.model_copy(update={"voice_lines": {"follow_up": THREE}})
    by_seed = {seed: _asked(own, seed, day="Saturday") for seed in range(20)}
    assert set(by_seed.values()) <= SAID and len(set(by_seed.values())) > 1
    # The same seed and facts say the same words, so a resend or a retry reads as it did.
    assert all(_asked(own, seed, day="Saturday") == said for seed, said in by_seed.items())
    # With no seed the facts choose, in whatever order they are given.
    unseeded = _asked(own, day="Saturday")
    assert unseeded in SAID
    assert voice.say(own, "follow_up", day="Saturday", plan="Hopscotch") == unseeded


def test_the_choice_is_the_same_in_every_process(settings) -> None:
    """Python salts hash() afresh in every process, so a choice made with it would change with
    each restart."""
    script = (
        "import json\n"
        "from familydb import voice\n"
        "from familydb.config import Settings\n"
        f"lines = {{'follow_up': {THREE!r}}}\n"
        "own = Settings(_env_file=None, persona='default', voice_lines=lines)\n"
        "said = [voice.say(own, 'follow_up', seed=n, plan='Hopscotch') for n in range(20)]\n"
        "print(json.dumps(said))\n"
    )
    there = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "PYTHONHASHSEED": "random"},
        capture_output=True,
        text=True,
        check=True,
    )
    own = settings.model_copy(update={"voice_lines": {"follow_up": THREE}})
    assert json.loads(there.stdout) == [_asked(own, seed) for seed in range(20)]


def test_a_wording_that_cannot_be_used_is_said_plainly(settings) -> None:
    """The wordings that can be used still are; the one that cannot is the plain line."""
    own = settings.model_copy(update={"voice_lines": {"follow_up": "One: {plan}.\n{venue}?"}})
    said = {_asked(own, seed, day="Saturday") for seed in range(20)}
    assert said == {"One: Hopscotch.", "How was Hopscotch on Saturday? Worth doing again?"}


def test_what_is_wrong_with_one_of_several_wordings_is_named() -> None:
    found = voice.problems(
        {
            "follow_up": "How was {plan}?\n\nHow was {venue}?",
            "reminder": "{title}, #{task}.\n{title",
            "done": "Done.\nAll done.",
        }
    )
    assert found["follow_up"].startswith("in wording 2, {venue} is not something it knows")
    assert found["follow_up"].endswith("it can use {name}, {plan}, {day}")
    assert found["reminder"].startswith("in wording 2, a { or } is not closed")
    assert "done" not in found


def test_every_event_s_example_fills_every_field_it_declares() -> None:
    """The examples are what the Personality page fills a line in with to show how it reads."""
    for name, event in voice.EVENTS.items():
        assert set(event.example) == set(event.fields), name
        filled = voice.EVENTS[name].plain.format(name="Vera", **event.example)
        assert "{" not in filled and "}" not in filled, name


def test_the_brief_persona_takes_turns_and_vera_says_each_thing_one_way(settings) -> None:
    """Vera's lines stay as first written, one wording each. The brief persona's second wording
    of a line is no longer than her first: she is the short one."""
    brief = personas.load("brief")
    for event in ("follow_up", "lookup_done"):
        first, second = voice.wordings(brief.lines[event])
        assert len(second) <= len(first), event
    vera = personas.load(personas.DEFAULT)
    assert all(len(voice.wordings(line)) == 1 for line in vera.lines.values())
    as_brief = settings.model_copy(update={"persona": "brief"})
    assert voice.reads_as(as_brief, "follow_up") == [
        "How was #31 Hopscotch on Saturday? Worth doing again?",
        "How did #31 Hopscotch go on Saturday? Do it again?",
    ]


def test_how_a_line_reads_is_every_wording_in_force_filled_in(settings) -> None:
    own = settings.model_copy(
        update={"voice_lines": {"reminder": "{name}: {title}{who}.\n#{task}"}}
    )
    assert voice.reads_as(own, "reminder") == ["Vera: bins out (Sam).", "#12"]
    assert voice.reads_as(settings, "reminder") == [
        "Reminder: bins out (Sam). Task #12; tell me when it's done, or I can snooze it."
    ]
    # With no persona the line in force is the plain one, whatever the family wrote.
    plain = own.model_copy(update={"persona": "none"})
    assert voice.reads_as(plain, "reminder") == [
        "Reminder: bins out (Sam)  -  task #12. Tell me when it's done or ask to snooze it."
    ]


def test_a_notice_is_worded_by_the_message_it_answers(settings, clock, conn, family) -> None:
    """A notice has no facts of its own, so without the message's id to choose by it would read
    the same every time."""
    lines = {"retry_later": "Not now.\nLater, then.\nGive me a minute."}
    app = App(settings.model_copy(update={"voice_lines": lines}), clock)
    said = set()
    for update in range(8):
        reply = handle_incoming(
            app,
            IncomingMessage("telegram", f"u{update}", "chat-1", "1001", "we should go hiking"),
            api=fakes.FakeMessagesAPI(fakes.rate_limit_error()),
            conn=conn,
        )
        assert reply.text == voice.say(app.settings, "retry_later", seed=reply.in_message_id)
        assert messages.get(conn, reply.out_message_id).text == reply.text
        said.add(reply.text)
    assert len(said) > 1


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


def test_a_held_message_carries_the_wording_chosen_for_it(settings, clock, conn, family) -> None:
    """A reminder is worded once, when it is stored, and whatever carries it carries those
    words: a reply that forgets it takes them as they were chosen, not a new choice."""
    from familydb.task_service import reminder_text

    lines = {"reminder": "Psst: {title}.\nDon't forget: {title}.\n{title}, as promised."}
    app = App(settings.model_copy(update={"voice_lines": lines}), clock)
    app.senders["telegram"] = lambda chat, text: None
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
    task = tasks.list_all(conn)[0]
    held = messages.get(conn, task.reminder.message_id).text
    assert app.held.is_held(task.reminder.message_id, clock.now())
    assert held == reminder_text(task, app.settings) and "Call grandma" in held
    out, _ = _next(app, conn, "Pasta tonight.")
    assert out.text == "Pasta tonight.\n\n" + held
