"""Whether FamilyDB is well (familydb/health.py): the database answers, and a scheduler that should
be running is ticking. A page served alone, or a scheduler stopped on purpose, is not trouble."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from familydb import health
from familydb.app import App
from familydb.clock import FixedClock
from familydb.store import heartbeat


def _later(settings, clock, minutes: int) -> App:
    return App(settings, FixedClock(clock.now() + timedelta(minutes=minutes), clock.tz))


def test_a_scheduler_that_went_quiet_is_not_well(settings, clock, conn) -> None:
    app = App(settings, clock)
    assert health.check(app) == (True, "ok")  # no scheduler has run: the database answers
    health.ticked(app)
    assert heartbeat.read(conn).jobs_at == "2026-09-20T21:03:00Z"
    assert health.check(_later(settings, clock, 14)) == (True, "ok")
    later = _later(settings, clock, 16)
    assert health.check(later) == (False, "the scheduled jobs have not run for 16 minutes")
    health.stopped(later)  # stopped on purpose: its silence is not trouble
    assert health.check(_later(settings, clock, 60)) == (True, "ok")
    health.ticked(app)  # started again
    assert heartbeat.read(conn).stopped_at is None


def test_healthz_says_what_is_wrong(settings, clock, conn) -> None:
    from familydb.web import create_app

    health.ticked(App(settings, clock))
    quiet = create_app(_later(settings, clock, 30)).test_client().get("/healthz")
    assert quiet.status_code == 503
    assert quiet.text == "the scheduled jobs have not run for 30 minutes\n"


def test_the_settings_watch_is_the_heartbeat(settings, clock, conn) -> None:
    from familydb.jobs.scheduler import apply_settings, build_scheduler

    app = App(settings, clock)
    apply_settings(app, build_scheduler(app))
    assert heartbeat.read(conn).jobs_at == "2026-09-20T21:03:00Z"


def test_familydb_health_exits_one_when_not_well(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from familydb.cli import app

    monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "health.sqlite3"))
    runner = CliRunner()
    answered = runner.invoke(app, ["health"])
    assert answered.exit_code == 0 and answered.output == "ok\n"
    monkeypatch.setattr(health, "check", lambda _app: (False, "the database does not answer"))
    answered = runner.invoke(app, ["health"])
    assert answered.exit_code == 1 and answered.output == "the database does not answer\n"
