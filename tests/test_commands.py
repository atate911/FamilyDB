"""Telegram's /today, /week, /tasks and /now, answered by code with no model call (commands.py)."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from telegram import BotCommand

from familydb import commands, task_service
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.channels.telegram import TelegramChannel
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.store import db, knocks, messages, tasks
from tests import fakes
from tests.conftest import TZ
from tests.test_telegram import TOKEN, _takers, _telegram

FRIDAY = datetime(2026, 9, 25, 15, 30, tzinfo=TZ)


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=TZ)


def _app(settings, *, at=FRIDAY, calendar=None, **changes) -> App:
    return App(settings.model_copy(update=changes), FixedClock(at, TZ), calendar=calendar)


def _ask(app, text, *, update="1", chat="42", user="1001") -> str | None:
    reply = commands.answer(app, IncomingMessage("telegram", update, chat, user, text))
    return reply.text if reply else None


def _task(conn, title, *, chat="42", remind=None, **values):
    return task_service.create(
        conn,
        {"title": title, **values},
        reminder=utc_iso(remind) if remind else None,
        operation_key=f"{title}:{chat}",
        channel="telegram",
        chat_id=chat,
        now=utc_iso(FRIDAY - timedelta(days=1)),
    )


def test_a_command_is_known_by_its_first_word() -> None:
    assert commands.name_of("/today") == "today"
    assert commands.name_of("/Week@familybot") == "week"
    assert commands.name_of("/now please") == "now"
    assert commands.name_of("/start") is None
    assert commands.name_of("what's on today?") is None
    assert commands.name_of("") is None


def test_today_is_the_calendar_and_this_chats_reminders(settings, conn, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed("Soccer practice", _at(25, 17), _at(25, 18))
    calendar.seed("Grandma visiting", date(2026, 9, 24), date(2026, 9, 27), all_day=True)
    calendar.seed("Swim lessons", _at(26, 9), _at(26, 10))  # tomorrow's
    bins = _task(conn, "Bins out", remind=_at(25, 19))
    _task(conn, "Elsewhere", chat="-100", remind=_at(25, 16))  # another chat's
    taxes = _task(conn, "File the taxes", due_at=utc_iso(_at(25, 17, 30)))
    app = _app(settings, calendar=calendar)
    assert _ask(app, "/today") == (
        "Here's today, Fri 25 Sep:\n"
        "All day: Grandma visiting\n"
        "17:00-18:00 Soccer practice\n"
        f"17:30 due: File the taxes (task #{taxes.id})\n"
        f"19:00 reminder: Bins out (task #{bins.id})"
    )


def test_the_week_names_each_day_and_the_month_where_it_turns(settings, conn, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed("Swim lessons", _at(26, 9), _at(26, 10))
    calendar.seed("Sleepover", _at(26, 18), _at(27, 10))
    app = _app(settings, calendar=calendar)
    assert _ask(app, "/week") == (
        "Here's the week ahead:\n"
        "Fri 25 Sep: nothing on\n"
        "Sat 26: 09:00-10:00 Swim lessons; 18:00 Sleepover\n"
        "Sun 27: until 10:00 Sleepover\n"
        "Mon 28: nothing on\n"
        "Tue 29: nothing on\n"
        "Wed 30: nothing on\n"
        "Thu 1 Oct: nothing on"
    )


def test_tasks_are_this_chats_open_ones_and_the_askers_own(settings, conn, family) -> None:
    """This chat's open tasks, and the asker's own wherever they were set: a task Sam set for
    himself elsewhere is on his list here too; somebody else's in another chat is not."""
    rule = {"repeat_every": 1, "repeat_unit": "week", "repeat_from": "schedule"}
    bins = task_service.create(
        conn,
        {"title": "Bins out", "owner_id": family["sam"].id},
        reminder=utc_iso(_at(27, 19)),
        operation_key="bins",
        channel="telegram",
        chat_id="42",
        now=utc_iso(FRIDAY),
        repeat=rule,
    )
    knives = _task(conn, "Get the knives sharpened", preferred_window="some Saturday morning")
    done = _task(conn, "Already done")
    task_service.update(conn, done.id, {"status": "done"}, now=utc_iso(FRIDAY))
    _task(conn, "Somebody else's", chat="-100")
    app = _app(settings)
    assert _ask(app, "/tasks") == (
        "Still to do, here and yours:\n"
        f"#{bins.id} Bins out (Sam): reminder Sun 27 Sep 19:00, every week\n"
        f"#{knives.id} Get the knives sharpened: some Saturday morning"
    )
    for n in range(12):
        _task(conn, f"Chore {n}")
    listed = _ask(app, "/tasks", update="2")
    assert listed is not None
    assert listed.splitlines()[-1] == "…and 2 more on the web page's Tasks."
    assert _ask(app, "/tasks", chat="7", update="3") == (
        "Still to do, here and yours:\n"
        f"#{bins.id} Bins out (Sam): reminder Sun 27 Sep 19:00, every week"
    )
    assert _ask(app, "/tasks", chat="7", update="4", user="1002") == (
        "Still to do, here and yours:\nNone."
    )


def test_tasks_say_a_reminder_was_sent_and_not_acted_on(settings, conn, family) -> None:
    """A reminder that went and was neither done nor snoozed used to vanish from the list's
    words, leaving a task that looked as if nothing would ever bring it up."""
    task = _task(conn, "Call the plumber", remind=_at(25, 9))
    with db.transaction(conn):
        out = messages.insert_out(
            conn, channel="telegram", chat_id="42", text="…", now=utc_iso(FRIDAY)
        )
        reminder = tasks.get(conn, task.id).reminder
        tasks.attach_message(conn, reminder.id, out.id)
        messages.mark_delivered(conn, [out.id], now=utc_iso(_at(25, 9)))
    assert _ask(_app(settings), "/tasks") == (
        f"Still to do, here and yours:\n#{task.id} Call the plumber: reminded Fri 09:00"
    )


def test_now_is_the_engine_without_a_model(settings, conn) -> None:
    from evals.household import NOW, calendar_events, seed

    seed(conn)
    calendar = fakes.FakeCalendar(TZ)
    calendar_events(calendar)
    app = _app(settings, at=NOW.replace(tzinfo=TZ), calendar=calendar)
    said = _ask(app, "/now")
    assert said is not None
    lines = said.splitlines()
    assert lines[0] == "From your list, now until 19:30:"
    assert lines[1].startswith("#1 Ramen place on Main St: can go 15:42-16:48 today, about 12 min")
    assert lines[3].startswith("Not now: #3 Hopscotch Portland (needs about 2 h, only 1.5 h free)")
    assert lines[4:] == ["Not checked: weather not configured."]
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


def test_a_command_is_kept_answered_once_and_never_a_turn(settings, conn, family) -> None:
    from familydb.jobs.retry_failed import run_retries

    app = _app(settings)
    assert _ask(app, "/tasks", update="9") is not None
    assert _ask(app, "/tasks", update="9") is None  # the same update again
    asked, answer = conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
    assert (asked["direction"], asked["text"], asked["status"]) == ("in", "/tasks", "processed")
    assert (answer["direction"], answer["reply_to"]) == ("out", asked["id"])
    assert run_retries(app) == 0  # nothing for the retry job, so nothing for a model


def test_a_stranger_gets_the_strangers_line_and_knocks(settings, conn, family) -> None:
    said = _ask(_app(settings), "/today", user="777")
    assert (
        said == "Sorry, I only talk to the family. Ask one of them to add you; your id here is 777."
    )
    assert [knock.channel_user_id for knock in knocks.recent(conn, channel="telegram")] == ["777"]
    assert messages.get(conn, 1) is None  # nothing of theirs is kept


# -- on Telegram


def _command(text: str):
    return _telegram(
        "message",
        text=text,
        entities=[{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}],
    )


def test_telegram_hands_each_command_to_code(settings, clock) -> None:
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    for name in ("today", "week", "tasks", "now"):
        assert _takers(channel, _command(f"/{name}")) == ["on_command"]
    assert _takers(channel, _command("/today@familybot")) == ["on_command"]
    assert _takers(channel, _command("/today@someotherbot")) == []
    assert _takers(channel, _command("/start")) == ["on_start"]
    edited = _telegram(
        "edited_message",
        text="/today",
        entities=[{"type": "bot_command", "offset": 0, "length": 6}],
    )
    assert _takers(channel, edited) == []  # an edited command is not answered again


def test_telegram_sends_the_answer_as_a_reply(settings, clock, conn, family) -> None:
    channel = TelegramChannel(App(settings, FixedClock(FRIDAY, TZ)), token=TOKEN)
    replies: list[str] = []

    async def reply_text(value: str, **_: object) -> None:
        replies.append(value)

    async def send_chat_action(**_: object) -> None:
        return None

    update = SimpleNamespace(
        update_id=11,
        effective_message=SimpleNamespace(text="/today", reply_text=reply_text),
        effective_user=SimpleNamespace(id=1001, full_name="Sam", username=None),
        effective_chat=SimpleNamespace(id=42, type="private"),
    )
    context = SimpleNamespace(bot=SimpleNamespace(send_chat_action=send_chat_action))
    asyncio.run(channel.on_command(update, context))
    # Drawn with its heading in bold; kept as it was written, for the page and the history.
    assert replies == [
        "<b>Here's today, Fri 25 Sep:</b>\nNothing on.\n"
        "Google Calendar isn't connected, so these are the saved plans only."
    ]
    kept = conn.execute("SELECT text FROM messages WHERE direction='out'").fetchone()["text"]
    assert kept.startswith("Here's today, Fri 25 Sep:\n")
    sent = conn.execute("SELECT delivered_at FROM messages WHERE direction='out'").fetchone()
    assert sent["delivered_at"] is not None  # stored first, marked delivered once it went


def test_the_menu_is_set_only_when_it_differs(settings, clock) -> None:
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    menu = [BotCommand(name, about) for name, about in commands.MENU]

    class Bot:
        def __init__(self, has):
            self.has, self.set = has, []

        async def get_my_commands(self):
            return tuple(self.has)

        async def set_my_commands(self, wanted):
            self.set.append(wanted)

    fresh, current = Bot([]), Bot(menu)
    asyncio.run(channel.offer_commands(fresh))
    asyncio.run(channel.offer_commands(current))
    assert fresh.set == [menu] and current.set == []

    class Broken(Bot):
        async def get_my_commands(self):
            raise RuntimeError("Telegram is down")

    asyncio.run(channel.offer_commands(Broken([])))  # logged, not raised


# -- a link that links somebody's Telegram


def _started(app, text, *, user="1003", chat=None, update="30"):
    msg = IncomingMessage("telegram", update, chat or user, user, text, sender_name="Jo Smith")
    return commands.start(app, msg)


def test_starting_from_a_link_links_and_welcomes_them(settings, conn, family) -> None:
    from familydb import family as rules
    from familydb.store import members

    app = _app(settings)
    jo = rules.add(conn, "Jo", "parent", telegram_id=None, now=utc_iso(FRIDAY))
    code = rules.invite(conn, jo.id, by=None, now=FRIDAY)
    said = _started(app, f"/start {code}")
    assert said.status == "ok" and said.text.startswith("Welcome, Jo! Your Telegram is linked")
    assert members.resolve(conn, "telegram", "1003").id == jo.id
    # Opened again, the link is spent, and Jo is simply greeted as family.
    again = _started(app, f"/start {code}", update="31")
    assert again.text.startswith("Hi, I'm Vera.")


def test_a_link_that_does_nothing_says_why(settings, conn, family) -> None:
    from familydb import family as rules

    app = _app(settings)
    jo = rules.add(conn, "Jo", "parent", telegram_id=None, now=utc_iso(FRIDAY))
    code = rules.invite(conn, jo.id, by=None, now=FRIDAY)
    stale = _started(app, "/start AAAAAAAAAAAAAAAAAAAAAAAA", user="4242")
    assert stale.status == "unknown_sender" and "doesn't work any more" in stale.text
    assert "4242" in [k.channel_user_id for k in knocks.recent(conn, channel="telegram")]
    taken = _started(app, f"/start {code}", user="1001")  # Sam trying it on their own phone
    assert taken.text.startswith("This Telegram is already Sam's")
    # Only in a private chat: a group's Start is never a link.
    grouped = _started(app, f"/start {code}", chat="-100")
    assert grouped.text.startswith("Sorry, I only talk to the family")
    assert _started(app, f"/start {code}", update="32").text.startswith("Welcome, Jo!")


def test_lookup_asks_for_every_idea_waiting_to_be_looked_up_now(settings, conn, family) -> None:
    from familydb.store import db, ideas
    from familydb.voice import say

    looking = _app(settings, web_tools_enabled=True)
    assert _ask(looking, "/lookup", update="l1") == say(looking.settings, "lookups_none", seed=0)
    with db.transaction(conn):
        first = ideas.insert(conn, title="Hopscotch", kind="outing")
        ideas.insert(conn, title="Ramen", kind="restaurant")
    asked = _ask(looking, "/lookup", update="l2")
    assert asked == say(looking.settings, "lookups_asked", seed=0, count="2 ideas")
    assert ideas.get(conn, first.id).lookup_wanted_at is not None
    off = _app(settings, web_tools_enabled=False)
    assert _ask(off, "/lookup", update="l3") == say(off.settings, "lookups_off", seed=0)
