from pathlib import Path

import pytest
from pydantic import ValidationError

from familydb.config import Settings


def test_defaults_and_masking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.delenv("FAMILYDB_TZ", raising=False)
    s = Settings(_env_file=None, anthropic_api_key="sk-secret", familydb_path=tmp_path / "x.db")
    assert s.anthropic_model == "claude-opus-5"
    assert s.anthropic_effort == "medium"
    assert s.tz == "UTC"
    assert s.tzinfo.key == "UTC"
    masked = s.masked()
    assert masked["anthropic_api_key"] == "****"
    assert masked["tz"] == "UTC"
    assert "sk-secret" not in str(masked)


def test_env_vars_are_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_EFFORT", "high")
    monkeypatch.setenv("FAMILYDB_TZ", "America/Vancouver")
    monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "db.sqlite3"))
    s = Settings(_env_file=None)
    assert s.anthropic_effort == "high"
    assert s.tzinfo.key == "America/Vancouver"
    assert s.familydb_path == tmp_path / "db.sqlite3"


def test_rejects_unknown_timezone() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, family_tz="Mars/Olympus")


def test_rejects_bad_effort() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, anthropic_effort="ultra")  # type: ignore[arg-type]


def test_os_tz_is_a_fallback_only_when_it_is_a_real_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FAMILYDB_TZ", raising=False)
    monkeypatch.setenv("TZ", "America/Vancouver")
    assert Settings(_env_file=None).tz == "America/Vancouver"
    monkeypatch.setenv("TZ", "UTC0")
    assert Settings(_env_file=None).tz == "UTC"
    monkeypatch.setenv("TZ", ":/etc/localtime")
    assert Settings(_env_file=None).tz == "UTC"
    monkeypatch.setenv("FAMILYDB_TZ", ":Europe/Paris")
    assert Settings(_env_file=None).tz == "Europe/Paris"
    assert Settings(_env_file=None, family_tz="Asia/Tokyo").tz == "Asia/Tokyo"  # explicit wins
    monkeypatch.delenv("FAMILYDB_TZ")
    monkeypatch.setenv("TZ", "UTC0")
    assert Settings(_env_file=None, family_tz="Asia/Tokyo").tz == "Asia/Tokyo"
