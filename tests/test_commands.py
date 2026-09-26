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
from familydb.store import knocks, messages
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


def test_without_google_it_says_the_plans_are_its_own(settings, conn, family) -> None:
    said = _ask(_app(settings), "/today")
    assert said == (
        "Here's today, Fri 25 Sep:\nNothing on.\n"
        "Google Calendar isn't connected, so these are the saved plans only."
    )


def test_tasks_are_this_chats_open_ones(settings, conn, family) -> None:
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
        "Still to do here:\n"
        f"#{bins.id} Bins out (Sam): reminder Sun 27 Sep 19:00, every week\n"
        f"#{knives.id} Get the knives sharpened: some Saturday morning"
    )
    for n in range(12):
        _task(conn, f"Chore {n}")
    listed = _ask(app, "/tasks", update="2")
    assert listed is not None
    assert listed.splitlines()[-1] == "…and 2 more on the web page's Tasks."
    assert _ask(app, "/tasks", chat="7", update="3") == "Still to do here:\nNone."


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


# -- on Telegram ---------------------------------------------------------------------------------


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

    async def reply_text(value: str) -> None:
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
    assert replies == [
        "Here's today, Fri 25 Sep:\nNothing on.\n"
        "Google Calendar isn't connected, so these are the saved plans only."
    ]
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
