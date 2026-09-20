from pathlib import Path

import pytest
from pydantic import ValidationError

from familydb.config import Settings


def test_defaults_and_masking(tmp_path: Path) -> None:
    s = Settings(_env_file=None, anthropic_api_key="sk-secret", familydb_path=tmp_path / "x.db")
    assert s.anthropic_model == "claude-opus-5"
    assert s.anthropic_effort == "medium"
    assert s.tz == "UTC"
    assert s.tzinfo.key == "UTC"
    masked = s.masked()
    assert masked["anthropic_api_key"] == "****"
    assert "sk-secret" not in str(masked)


def test_env_vars_are_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_EFFORT", "high")
    monkeypatch.setenv("TZ", "America/Vancouver")
    monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "db.sqlite3"))
    s = Settings(_env_file=None)
    assert s.anthropic_effort == "high"
    assert s.tzinfo.key == "America/Vancouver"
    assert s.familydb_path == tmp_path / "db.sqlite3"


def test_rejects_unknown_timezone() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, tz="Mars/Olympus")


def test_rejects_bad_effort() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, anthropic_effort="ultra")  # type: ignore[arg-type]
