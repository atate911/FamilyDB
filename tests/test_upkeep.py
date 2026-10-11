"""Backups checked and told of, and a disk nearly full (familydb/upkeep.py), with no model call;
a refused Telegram token is shown on the Status page, since Telegram cannot carry it."""

from __future__ import annotations

from collections import namedtuple
from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from familydb import alerts, upkeep
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.store import alerts as alert_store
from familydb.store import backups, db
from familydb.upkeep import run_upkeep

Usage = namedtuple("Usage", "total used free")


def _kinds(conn) -> set[str]:
    return {one.kind for one in alert_store.current(conn, since="2000-01-01T00:00:00Z")}


def _backed_up(conn, made_at: str, ok: bool = True) -> None:
    with db.transaction(conn):
        backups.record(conn, path="/b.sqlite3", size=2048, ok=ok, detail=None, now=made_at)


def test_backups_that_stopped_are_told_once_there_were_any(settings, clock, conn) -> None:
    app = App(settings, clock)  # Sunday 20 September, 21:03 UTC
    assert run_upkeep(app) == 0 and "backup" not in _kinds(conn)  # none ever: no habit to miss
    _backed_up(conn, "2026-09-19T03:15:00Z")  # 42 hours ago
    assert run_upkeep(app) == 1 and "backup" in _kinds(conn)
    _backed_up(conn, "2026-09-20T03:15:00Z", ok=False)  # written, but failed its check
    assert upkeep.backup_trouble(conn, clock.now()).startswith("the last good backup was made")
    _backed_up(conn, "2026-09-20T10:15:00Z")
    assert run_upkeep(app) == 0 and "backup" not in _kinds(conn)  # forgotten once it works


def test_a_disk_nearly_full_is_told(settings, clock, conn, monkeypatch) -> None:
    monkeypatch.setattr(upkeep.shutil, "disk_usage", lambda _path: Usage(1, 1, 300 * 1024 * 1024))
    app = App(settings, clock)
    assert run_upkeep(app) == 1
    (alert,) = [one for one in alert_store.current(conn, since="2000") if one.kind == "disk"]
    assert alert.detail == "300 MB free"
    monkeypatch.setattr(upkeep.shutil, "disk_usage", lambda _path: Usage(1, 1, 5 * 1024**3))
    assert run_upkeep(App(settings, FixedClock(clock.now() + timedelta(hours=1), clock.tz))) == 0
    assert "disk" not in _kinds(conn)


def test_a_refused_telegram_token_is_shown_and_never_sent_on_telegram(settings, clock, conn):
    app = App(settings.model_copy(update={"admin_alerts": True}), clock)
    sent: list[str] = []
    app.senders["telegram"] = lambda chat, text: sent.append(text)
    alerts.note(conn, "telegram", "", "the token was refused", clock.now())
    assert alerts.run_alerts(app) == 0 and sent == []
    assert "telegram" in _kinds(conn)


def test_a_backup_is_checked_and_recorded(settings, conn, tmp_path: Path, monkeypatch) -> None:
    from familydb.cli import app as cli

    monkeypatch.setenv("FAMILYDB_PATH", str(settings.familydb_path))
    done = CliRunner().invoke(cli, ["db", "backup", str(tmp_path / "copy.sqlite3")])
    assert done.exit_code == 0 and "and checked" in done.output
    kept = backups.latest(conn, good=True)
    assert kept is not None and kept.path.endswith("copy.sqlite3") and kept.bytes > 0


def test_status_and_doctor_say_when_the_last_good_one_was(settings, clock, conn) -> None:
    from familydb import doctor
    from familydb.web import status as status_page

    app = App(settings, clock)
    row = next(r for r in status_page.services(app, conn) if r["label"] == "Backups")
    assert row["on"] is None and row["detail"].startswith("none recorded")
    _backed_up(conn, "2026-09-20T10:15:00Z")
    row = next(r for r in status_page.services(app, conn) if r["label"] == "Backups")
    assert row["on"] is True and row["detail"].startswith("the last good one")
    report = doctor.Report()
    doctor.check_backups(app, report, conn)
    assert report.checks[-1].verdict == doctor.OK


@pytest.mark.parametrize("refused", [True, False])
def test_the_channel_notes_its_refused_token(settings, clock, conn, refused) -> None:
    from familydb.channels.telegram import TelegramSupervisor

    supervisor = TelegramSupervisor(App(settings, clock))
    supervisor._token_refused(True)
    supervisor._token_refused(refused)
    assert ("telegram" in _kinds(conn)) is refused
