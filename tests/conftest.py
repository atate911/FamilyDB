"""Shared pytest fixtures for FamilyDB."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from familydb.clock import FixedClock
from familydb.config import Settings

TZ = ZoneInfo("America/Vancouver")
NOW = datetime(2026, 9, 20, 14, 3)  # a Sunday afternoon, PDT


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
