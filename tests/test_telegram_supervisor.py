"""The settings page reaches Telegram without a restart: a new token, and her name on the bot."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import ClassVar

import pytest
from telegram import BotDescription, BotName
from telegram.error import BadRequest, InvalidToken, NetworkError, RetryAfter, TimedOut

from familydb import voice
from familydb.app import App
from familydb.channels.telegram import TelegramChannel, TelegramSupervisor
from familydb.store import db
from familydb.store import settings as settings_store


class Channel:
    """Stands in for the real channel: records what was started and stopped, and what its
    contact was asked to say. An error in `refusals` is raised by the next introduction."""

    events: ClassVar[list[str]] = []
    introduced: ClassVar[list[tuple[str, str, str]]] = []
    asked_at: ClassVar[list[float]] = []
    refusals: ClassVar[list[Exception]] = []

    def __init__(self, app: App, token: str) -> None:
        self.token = token
        self.username = f"bot_{token}"

    async def start(self) -> None:
        Channel.events.append(f"start {self.token}")
        if self.token == "refused":
            raise InvalidToken("Unauthorized")
        if self.token == "offline":
            raise NetworkError("no route to host")

    async def stop(self) -> None:
        Channel.events.append(f"stop {self.token}")

    async def introduce(self, name: str, about: str) -> None:
        Channel.introduced.append((self.token, name, about))
        Channel.asked_at.append(time.monotonic())
        if Channel.refusals:
            raise Channel.refusals.pop(0)


def _until(condition, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f"gave up waiting; events: {Channel.events}")
        time.sleep(0.02)


def _token(conn, value: str | None) -> None:
    _store(conn, telegram_bot_token=value)


def _store(conn, **values) -> None:
    with db.transaction(conn):
        settings_store.set_many(conn, values, source="test")


@pytest.fixture
def watched(settings, clock, conn):
    Channel.events, Channel.introduced, Channel.asked_at, Channel.refusals = [], [], [], []
    app = App(settings, clock)
    supervisor = TelegramSupervisor(app, make_channel=Channel, check_seconds=0.02)
    supervisor.start()
    yield app, supervisor
    supervisor.stop(timeout=5)


def test_a_token_saved_on_the_page_connects_and_a_new_one_reconnects(watched, conn) -> None:
    app, supervisor = watched
    time.sleep(0.1)
    assert Channel.events == []  # no token, nothing to connect
    _token(conn, "first")
    _until(lambda: Channel.events == ["start first"])
    assert app.channel_states["telegram"] == "connected as @bot_first"
    _token(conn, "second")
    _until(lambda: Channel.events[-2:] == ["stop first", "start second"])
    _token(conn, None)
    _until(lambda: Channel.events[-1] == "stop second")
    assert supervisor.state == "off"


def test_a_refused_token_is_not_tried_again_until_it_changes(watched, conn) -> None:
    app, _ = watched
    _token(conn, "refused")
    _until(lambda: app.channel_states.get("telegram") == "the token was refused by Telegram")
    time.sleep(0.2)  # ten more checks
    assert Channel.events.count("start refused") == 1
    _token(conn, "fixed")
    _until(lambda: Channel.events[-1] == "start fixed")


def test_telegram_out_of_reach_is_tried_again(watched, conn, monkeypatch) -> None:
    app, supervisor = watched
    monkeypatch.setattr(supervisor, "RETRY_SECONDS", 0.05)
    _token(conn, "offline")
    _until(lambda: Channel.events.count("start offline") >= 2)
    assert app.channel_states["telegram"] == "cannot reach Telegram; trying again"


def test_stopping_closes_the_connection(settings, clock, conn) -> None:
    Channel.events = []
    _token(conn, "only")
    supervisor = TelegramSupervisor(App(settings, clock), make_channel=Channel, check_seconds=0.02)
    supervisor.start()
    _until(lambda: Channel.events == ["start only"])
    supervisor.stop(timeout=5)
    assert Channel.events == ["start only", "stop only"]


def test_connecting_gives_the_bot_her_name_once_and_a_reconnect_again(watched, conn) -> None:
    app, _ = watched
    _token(conn, "first")
    _until(lambda: len(Channel.introduced) == 1)
    time.sleep(0.1)  # five more checks
    assert Channel.introduced == [("first", "Vera", voice.say(app.settings, "start"))]
    assert Channel.introduced[0][2].startswith("Hi, I'm Vera.")
    _token(conn, "second")
    _until(lambda: len(Channel.introduced) == 2)
    time.sleep(0.1)
    assert [said[:2] for said in Channel.introduced] == [("first", "Vera"), ("second", "Vera")]


def test_a_new_introduction_on_the_page_is_given_to_the_bot_once(watched, conn) -> None:
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 1)
    _store(conn, voice_lines={"start": "Hello, {name} here. Ask me anything."})
    _until(lambda: len(Channel.introduced) == 2)
    time.sleep(0.1)
    assert Channel.introduced[1:] == [("only", "Vera", "Hello, Vera here. Ask me anything.")]
    assert Channel.events == ["start only"]


def test_a_setting_that_changes_nothing_she_says_asks_telegram_nothing(watched, conn) -> None:
    app, _ = watched
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 1)
    _store(conn, about_family="Two kids, one dog.")
    _until(lambda: app.settings.about_family == "Two kids, one dog.")
    time.sleep(0.1)
    assert len(Channel.introduced) == 1


def test_under_none_the_contact_says_what_the_bot_calls_itself(watched, conn) -> None:
    """The plain bot is FamilyDB everywhere, so its contact is too; choosing her again gives it
    her name back. A contact still called Vera would say one thing while the bot said another."""
    app, _ = watched
    _store(conn, persona="none")
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 1)
    assert Channel.introduced[0][1] == "FamilyDB"
    assert Channel.introduced[0][2] == voice.say(app.settings, "start")
    assert "Vera" not in Channel.introduced[0][2]
    _store(conn, persona=None)
    _until(lambda: len(Channel.introduced) == 2)
    assert Channel.introduced[1][1] == "Vera"
    _store(conn, persona="none")
    _until(lambda: len(Channel.introduced) == 3)
    assert Channel.introduced[2][1] == "FamilyDB"


def test_an_introduction_that_fails_leaves_the_channel_running(watched, conn, caplog) -> None:
    app, _ = watched
    Channel.refusals = [BadRequest("Bot name is invalid")]
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 1)
    time.sleep(0.1)
    assert Channel.events == ["start only"]  # neither stopped nor started again
    assert app.channel_states["telegram"] == "connected as @bot_only"
    assert len(Channel.introduced) == 1  # and not tried again until something she says changes
    assert "Bot name is invalid" in caplog.text
    _store(conn, voice_lines={"start": "Hello from {name}."})
    _until(lambda: len(Channel.introduced) == 2)
    assert Channel.events == ["start only"]


def test_telegram_out_of_reach_while_naming_her_is_tried_again(watched, conn, monkeypatch) -> None:
    """A running channel is never reconnected by an outage, so a timeout left as it was would
    leave the contact under her old name until a restart."""
    _, supervisor = watched
    monkeypatch.setattr(supervisor, "RETRY_SECONDS", 0.05)
    Channel.refusals = [TimedOut("Timed out"), NetworkError("no route to host")]
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 3)
    time.sleep(0.1)
    assert len(Channel.introduced) == 3  # and once it went, not again
    assert len(set(Channel.introduced)) == 1
    assert Channel.events == ["start only"]


# python-telegram-bot 22 gives `retry_after` in seconds, and warns that it is a timedelta from 23
# (or with PTB_TIMEDELTA set, as the second run does); both are read.
@pytest.mark.filterwarnings("ignore::telegram.warnings.PTBDeprecationWarning")
@pytest.mark.parametrize("as_timedelta", [False, True])
def test_a_wait_telegram_asks_for_is_waited_out(watched, conn, monkeypatch, as_timedelta) -> None:
    if as_timedelta:
        monkeypatch.setenv("PTB_TIMEDELTA", "true")
    Channel.refusals = [RetryAfter(1)]
    _token(conn, "only")
    _until(lambda: len(Channel.introduced) == 1)
    time.sleep(0.2)  # ten more checks
    assert len(Channel.introduced) == 1
    _until(lambda: len(Channel.introduced) == 2)
    assert Channel.asked_at[1] - Channel.asked_at[0] >= 1.0
    assert Channel.events == ["start only"]


class Bot:
    """Stands in for Telegram's bot: the name and description its contact has, and what is set."""

    def __init__(self, name: str, description: str) -> None:
        self.name, self.description = name, description
        self.set: list[tuple[str, str]] = []

    async def get_my_name(self) -> BotName:
        return BotName(self.name)

    async def get_my_description(self) -> BotDescription:
        return BotDescription(self.description)

    async def set_my_name(self, name: str) -> bool:
        self.set.append(("name", name))
        self.name = name
        return True

    async def set_my_description(self, description: str) -> bool:
        self.set.append(("description", description))
        self.description = description
        return True


def test_introducing_sets_only_what_differs_trimmed_to_telegram_limits(settings, clock) -> None:
    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    bot = Bot("Vera", "Made by the Tates in BotFather.")
    channel.application = SimpleNamespace(bot=bot)
    asyncio.run(channel.introduce("Vera", "Hi, I'm Vera."))
    assert bot.set == [("description", "Hi, I'm Vera.")]

    asyncio.run(channel.introduce("J" * 70, "Hi. " + "x" * 600))
    assert bot.set[1:] == [("name", "J" * 64), ("description", ("Hi. " + "x" * 600)[:512])]
    # Telegram already has the trimmed words, so the same long ones set nothing again.
    asyncio.run(channel.introduce("J" * 70, "Hi. " + "x" * 600))
    assert len(bot.set) == 3
