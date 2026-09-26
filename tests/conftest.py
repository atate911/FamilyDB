"""Shared pytest fixtures for FamilyDB."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from familydb.clock import FixedClock
from familydb.config import Settings
from familydb.integrations.geocode import Geocoder
from familydb.integrations.open_meteo import OpenMeteo
from familydb.store import db, members
from familydb.store.members import Member
from familydb.tools import ToolContext, ToolRegistry, build_registry

TZ = ZoneInfo("America/Vancouver")
NOW = datetime(2026, 9, 20, 14, 3)  # a Sunday afternoon, PDT
NOW_ISO = "2026-09-20T21:03:00Z"


@pytest.fixture(autouse=True)
def keep_umask() -> Iterator[None]:
    """The CLI makes its process owner-only; the tests run it in-process, so put that back."""
    before = os.umask(0o022)
    os.umask(before)
    yield
    os.umask(before)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Pinned to Claude because the scripted fake in tests/fakes.py speaks its API; the default
    # provider is OpenAI and has tests of its own. On Opus, whose requests carry thinking, effort
    # and the refusal fallback, rather than on Claude's cheapest, which carries none of them.
    return Settings(
        _env_file=None,
        provider="anthropic",
        anthropic_model="claude-opus-5",
        anthropic_api_key="test-key",
        familydb_path=tmp_path / "familydb.sqlite3",
        # Relative by default, which would be the checkout's own data/ folder.
        google_token_path=tmp_path / "google_token.json",
        family_tz="America/Vancouver",
    )


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW, TZ)


@pytest.fixture
def conn(settings: Settings) -> Iterator[sqlite3.Connection]:
    connection = db.connect(settings.familydb_path)
    db.migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def family(conn: sqlite3.Connection) -> dict[str, Member]:
    with db.transaction(conn):
        sam = members.add(
            conn, "Sam", "admin", channel="telegram", channel_user_id="1001", now=NOW_ISO
        )
        alex = members.add(
            conn, "Alex", "parent", channel="telegram", channel_user_id="1002", now=NOW_ISO
        )
        girls = members.add(conn, "the girls", "kid", now=NOW_ISO)
    return {"sam": sam, "alex": alex, "girls": girls}


@pytest.fixture
def registry() -> ToolRegistry:
    return build_registry()


@pytest.fixture
def ctx(
    conn: sqlite3.Connection, settings: Settings, clock: FixedClock, family: dict[str, Member]
) -> ToolContext:
    return ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])


@pytest.fixture
def calendar_settings(settings: Settings, tmp_path: Path) -> Settings:
    """Settings under which the calendar tools count as available."""
    token = tmp_path / "google_token.json"
    token.write_text("{}")
    return settings.model_copy(
        update={
            "google_calendar_id": "family@group.calendar.google.com",
            "google_token_path": token,
        }
    )


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch, request) -> None:
    """Tests never reach the network: the raw fetchers raise unless a test patches them."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("network access is disabled in tests")

    if request.node.get_closest_marker("live") is None:
        import socket

        original_connect = socket.socket.connect

        def local_only(sock, address):
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
                _boom()
            return original_connect(sock, address)

        monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(Geocoder, "_fetch", staticmethod(_boom))
    monkeypatch.setattr(OpenMeteo, "_fetch", staticmethod(_boom))


@pytest.fixture
def full_settings(calendar_settings: Settings) -> Settings:
    """Calendar configured and home coordinates set (weather and travel estimates on)."""
    return calendar_settings.model_copy(
        update={"home_lat": 45.63, "home_lon": -122.67, "home_area": "Vancouver, WA"}
    )


THURSDAY = datetime(2026, 9, 24, 18, 0)  # the evening before the weekend of Sat 26 / Sun 27


@pytest.fixture
def thursday_clock() -> FixedClock:
    return FixedClock(THURSDAY, TZ)
