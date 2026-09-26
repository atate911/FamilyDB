"""What the bot writes is readable by the bot alone, and a secret never reaches the log."""

from __future__ import annotations

import io
import logging
import os
import stat

import pytest
from typer.testing import CliRunner

from familydb import privacy
from familydb.app import RedactSecrets
from familydb.cli import app

runner = CliRunner()


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_a_database_the_bot_creates_is_owner_only(tmp_path, monkeypatch) -> None:
    before = os.umask(0o022)  # the usual default, under which files come out 0644
    try:
        monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "data" / "familydb.sqlite3"))
        monkeypatch.setenv("FAMILYDB_TZ", "America/Vancouver")
        assert runner.invoke(app, ["db", "migrate"]).exit_code == 0
        assert _mode(tmp_path / "data" / "familydb.sqlite3") == 0o600
    finally:
        os.umask(before)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_files_an_older_version_left_readable_are_tightened(settings, tmp_path) -> None:
    database = settings.familydb_path
    database.write_bytes(b"")
    token = tmp_path / "google_token.json"
    token.write_text("{}")
    for path in (database, token):
        os.chmod(path, 0o644)
    changed = privacy.tighten(settings.model_copy(update={"google_token_path": token}))
    assert set(changed) == {database, token}
    assert _mode(database) == 0o600 and _mode(token) == 0o600
    assert privacy.tighten(settings) == []  # nothing left to do the second time


def test_privacy_tightening_does_not_require_getuid_on_windows(settings, monkeypatch):
    monkeypatch.setattr(privacy.os, "name", "nt")
    monkeypatch.delattr(privacy.os, "getuid", raising=False)
    assert privacy.tighten(settings) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_the_google_token_is_written_owner_only(tmp_path) -> None:
    from familydb.integrations.google_calendar import save_token

    before = os.umask(0o022)
    try:
        save_token(tmp_path / "google_token.json", '{"token": "t"}')
    finally:
        os.umask(before)
    assert _mode(tmp_path / "google_token.json") == 0o600
    assert not (tmp_path / "google_token.json.new").exists()


def test_a_telegram_token_never_reaches_the_log() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactSecrets())
    logger = logging.getLogger("test.redaction")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        logger.debug(
            "HTTP Request: POST https://api.telegram.org/bot%s/getUpdates",
            "123456789:AAH-abcdefghijklmnopqrstuvwxyz012345",
        )
    finally:
        logger.removeHandler(handler)
    written = stream.getvalue()
    assert "AAH-abcdefghijklmnopqrstuvwxyz012345" not in written
    assert "bot<token>/getUpdates" in written
