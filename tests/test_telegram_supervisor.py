"""A Telegram token changed on the settings page takes effect without a restart."""

from __future__ import annotations

import time
from typing import ClassVar

import pytest
from telegram.error import InvalidToken, NetworkError

from familydb.app import App
from familydb.channels.telegram import TelegramSupervisor
from familydb.store import db
from familydb.store import settings as settings_store


class Channel:
    """Stands in for the real channel: records what was started and stopped."""

    events: ClassVar[list[str]] = []

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


def _until(condition, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f"gave up waiting; events: {Channel.events}")
        time.sleep(0.02)


def _token(conn, value: str | None) -> None:
    with db.transaction(conn):
        settings_store.set_many(conn, {"telegram_bot_token": value}, source="test")


@pytest.fixture
def watched(settings, clock, conn):
    Channel.events = []
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
