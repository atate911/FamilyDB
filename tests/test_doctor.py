"""What `familydb doctor` reports, and what `--fix` puts right.

The point of these is that the verdicts mean what the script that reads them thinks they mean:
a failure is something that stops the bot working, and a warning is something not set up yet.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from familydb import doctor
from familydb.app import App


def _report(settings, clock, **overrides):
    app = App(settings.model_copy(update=overrides), clock)
    return app, doctor.run(app)


def _verdict_of(report: doctor.Report, name: str) -> str:
    for check in report.checks:
        if check.name == name:
            return check.verdict
    raise AssertionError(f"no check called {name!r} in {[c.name for c in report.checks]}")


def test_a_fresh_install_fails_only_on_what_stops_it_working(settings, clock, conn, family) -> None:
    _app, report = _report(settings, clock)
    # The database is there and migrated, and there is a key and a family.
    assert _verdict_of(report, "schema") == doctor.OK
    assert _verdict_of(report, "database writable") == doctor.OK
    assert _verdict_of(report, "family") == doctor.OK
    assert _verdict_of(report, "model key") == doctor.OK
    # Nothing optional has been set up, and none of that is a failure.
    assert _verdict_of(report, "google calendar") == doctor.WARN
    assert _verdict_of(report, "weather") == doctor.WARN
    assert _verdict_of(report, "weekend digest") == doctor.WARN
    assert report.healthy
    assert "It will run." in doctor.verdict(report)


def test_no_database_is_a_failure_that_names_the_command(settings, clock) -> None:
    _app, report = _report(settings, clock)  # no conn fixture, so nothing was ever created
    failures = {c.name: c for c in report.failures}
    assert "database" in failures
    assert "db migrate" in failures["database"].fix
    assert not report.healthy
    assert "must be fixed" in doctor.verdict(report)


def test_no_key_at_all_is_a_failure(settings, clock, conn, family) -> None:
    _app, report = _report(
        settings, clock, anthropic_api_key=None, openai_api_key=None, gemini_api_key=None
    )
    assert _verdict_of(report, "model key") == doctor.FAIL


def test_a_key_for_another_provider_is_only_a_warning(settings, clock, conn, family) -> None:
    """It still answers, on the spare. That is a surprise worth flagging, not a failure."""
    _app, report = _report(
        settings, clock, provider="openai", anthropic_api_key="k", openai_api_key=None
    )
    assert _verdict_of(report, "model key") == doctor.WARN
    assert report.healthy


def test_an_empty_family_is_a_failure(settings, clock, conn) -> None:
    _app, report = _report(settings, clock)
    assert _verdict_of(report, "family") == doctor.FAIL


def test_a_page_that_would_not_serve_is_a_failure(settings, clock, conn, family) -> None:
    _app, report = _report(settings, clock, web_enabled=True, web_host="0.0.0.0", web_password=None)
    assert _verdict_of(report, "web page") == doctor.FAIL


def test_the_report_is_json_a_script_can_read(settings, clock, conn, family) -> None:
    _app, report = _report(settings, clock)
    as_dict = report.as_dict()
    assert as_dict["healthy"] is True
    assert as_dict["failures"] == 0
    assert {"check", "verdict", "detail"} <= set(as_dict["checks"][0])


@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX idea")
def test_fix_tightens_a_readable_env_file(settings, clock, conn, family, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=secret\n")
    env.chmod(0o644)

    app, report = _report(settings, clock)
    assert _verdict_of(report, "env file") == doctor.WARN

    doctor.correct(app, report)
    assert Path(env).stat().st_mode & 0o777 == 0o600
    assert _verdict_of(doctor.run(app), "env file") == doctor.OK


def test_fix_applies_a_migration_that_has_not_been_run(settings, clock, tmp_path) -> None:
    """A database from an older version is the one failure a script can safely put right."""
    from familydb.store import db

    path = settings.familydb_path
    db.connect(path).close()  # exists, but at migration 0
    app = App(settings, clock)
    report = doctor.run(app)
    assert _verdict_of(report, "schema") == doctor.FAIL

    doctor.correct(app, report)
    assert _verdict_of(doctor.run(app), "schema") == doctor.OK


def test_online_checks_are_skipped_unless_asked(settings, clock, conn, family) -> None:
    """A first install has no key yet, and a check that hangs is worse than no check."""
    _app, report = _report(settings, clock)
    assert _verdict_of(report, "model reachable") == doctor.SKIP


def test_at_the_end_of_an_install_the_pages_first_steps_are_not_faults(
    settings, clock, conn
) -> None:
    """Nobody on the list and no model key is what the page's setup does next, so the installer's
    last check says so instead of printing two red crosses at somebody who did nothing wrong."""
    keyless = {"anthropic_api_key": "", "openai_api_key": "", "gemini_api_key": ""}
    _app, report = _report(settings, clock, provider="openai", provider_fallback=False, **keyless)
    assert _verdict_of(report, "family") == doctor.FAIL  # on its own, still a fault
    doctor.as_new_install(report)
    assert _verdict_of(report, "family") == doctor.TODO
    assert _verdict_of(report, "model key") == doctor.TODO
    assert report.healthy
    assert doctor.verdict(report).startswith("It is running. The rest is set up on the web page")
    family = next(check for check in report.checks if check.name == "family")
    assert family.fix == "next, on the web page: Add yourself"
