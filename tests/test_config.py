from pathlib import Path

import pytest
from pydantic import ValidationError

from familydb.config import Settings


def test_defaults_and_masking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.delenv("FAMILYDB_TZ", raising=False)
    s = Settings(_env_file=None, anthropic_api_key="sk-secret", familydb_path=tmp_path / "x.db")
    assert s.anthropic_model == "claude-opus-5"
    assert s.effort == "medium"
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
    assert s.effort == "high"
    assert s.tzinfo.key == "America/Vancouver"
    assert s.familydb_path == tmp_path / "db.sqlite3"


def test_rejects_unknown_timezone() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, family_tz="Mars/Olympus")


def test_rejects_bad_effort() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, effort="ultra")  # type: ignore[arg-type]


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


def test_web_settings_default_to_a_private_page(tmp_path: Path) -> None:
    s = Settings(_env_file=None, familydb_path=tmp_path / "x.db", web_password="hunter2")
    assert s.web_enabled is False and s.web_host == "127.0.0.1" and s.web_port == 8080
    assert s.web_session_days == 30 and s.web_title == "FamilyDB"
    assert s.web_allow_no_password is False and s.web_trust_proxy is False
    masked = s.masked()
    assert masked["web_password"] == "****" and "hunter2" not in str(masked)


def test_web_secret_key_is_generated_once_and_kept(tmp_path: Path) -> None:
    from familydb.web.keys import secret_path, session_secret

    s = Settings(_env_file=None, familydb_path=tmp_path / "data" / "x.db")
    first = session_secret(s)
    assert len(first) > 20 and session_secret(s) == first  # stable across calls
    path = secret_path(s)
    assert path.read_text() == first and path.stat().st_mode & 0o777 == 0o600
    pinned = s.model_copy(update={"web_secret_key": "pinned"})
    assert session_secret(pinned) == "pinned"  # the setting wins over the file


def test_web_secret_key_falls_back_when_it_cannot_be_written(tmp_path: Path) -> None:
    from familydb.web.keys import session_secret

    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory")
    s = Settings(_env_file=None, familydb_path=blocked / "x.db")
    key = session_secret(s)
    assert len(key) > 20 and session_secret(s) != key  # ephemeral, so a new one each time


def test_web_password_is_required_off_the_loopback(tmp_path: Path) -> None:
    from familydb.availability import web_available, web_is_public, web_password_required

    private = Settings(_env_file=None, familydb_path=tmp_path / "x.db", web_enabled=True)
    assert web_available(private) and not web_is_public(private)
    assert not web_password_required(private)
    for host in ("localhost", "::1", "[::1]", "127.0.0.1"):
        assert not web_is_public(private.model_copy(update={"web_host": host})), host
    public = private.model_copy(update={"web_host": "0.0.0.0"})
    assert web_is_public(public) and web_password_required(public)
    waived = public.model_copy(update={"web_allow_no_password": True})
    assert web_is_public(waived) and not web_password_required(waived)
    assert not web_available(private.model_copy(update={"web_enabled": False}))


def test_the_answer_cap_is_not_named_for_one_vendor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_MAX_TOKENS", raising=False)
    monkeypatch.delenv("MAX_OUTPUT_TOKENS", raising=False)
    assert Settings(_env_file=None).max_output_tokens == 16000
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "4321")  # anyone's existing .env keeps working
    assert Settings(_env_file=None).max_output_tokens == 4321
    monkeypatch.setenv("MAX_OUTPUT_TOKENS", "1234")
    assert Settings(_env_file=None).max_output_tokens == 1234


def test_both_providers_cap_the_answer_the_same_way(settings) -> None:
    from familydb.agent.providers import build
    from familydb.agent.providers.base import Message, TurnRequest

    capped = settings.model_copy(update={"max_output_tokens": 999, "openai_api_key": "sk-t"})
    request = TurnRequest(system=[], messages=[Message("user", ["hi"])])
    assert build("anthropic", capped, api=object()).payload(request)["max_tokens"] == 999
    assert build("openai", capped, api=object()).payload(request)["max_output_tokens"] == 999
