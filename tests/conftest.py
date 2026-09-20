"""Shared pytest fixtures for FamilyDB."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from familydb.clock import FixedClock
from familydb.config import Settings
from familydb.store import db, members
from familydb.store.members import Member

TZ = ZoneInfo("America/Vancouver")
NOW = datetime(2026, 9, 20, 14, 3)  # a Sunday afternoon, PDT
NOW_ISO = "2026-09-20T21:03:00Z"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        anthropic_api_key="test-key",
        familydb_path=tmp_path / "familydb.sqlite3",
        tz="America/Vancouver",
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
            conn, "Alex", "member", channel="telegram", channel_user_id="1002", now=NOW_ISO
        )
        girls = members.add(conn, "the girls", "kid", now=NOW_ISO)
    return {"sam": sam, "alex": alex, "girls": girls}
