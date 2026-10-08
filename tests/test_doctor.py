"""What `familydb doctor` reports, and what `--fix` puts right.

A failure is something that stops the bot working; a warning is something not set up yet.
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


def test_a_page_that_would_not_serve_is_a_failure(settings, clock, conn, family) -> None:
    _app, report = _report(settings, clock, web_enabled=True, web_host="0.0.0.0", web_password=None)
    assert _verdict_of(report, "web page") == doctor.FAIL


def test_a_page_whose_family_sign_in_as_themselves_needs_no_shared_password(
    settings, clock, conn, family
) -> None:
    """The page serves without WEB_PASSWORD once an admin has their own, and doctor agrees."""
    from familydb import family as family_rules

    family_rules.claim(conn, family["sam"].id, "a long enough password", now="2026-09-20T21:03:00Z")
    _app, report = _report(settings, clock, web_enabled=True, web_host="0.0.0.0", web_password=None)
    assert _verdict_of(report, "web page") == doctor.OK


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


@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX idea")
def test_fix_reports_what_it_put_right(settings, clock, conn, family, tmp_path, monkeypatch):
    """The second look is clean, so the note of what was done rides over to the check it was for."""
    monkeypatch.chdir(tmp_path)
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=secret\n")
    env.chmod(0o644)

    report = doctor.fix(App(settings, clock))
    check = next(c for c in report.checks if c.name == "env file")
    assert check.verdict == doctor.OK
    assert check.corrected == "made .env readable only by its owner"
    assert {c["check"]: c for c in report.as_dict()["checks"]}["env file"]["corrected"]


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
    last check says so instead of printing two red crosses.
    """
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


def test_a_link_that_is_gone_or_has_moved_is_said(settings) -> None:
    """The consoles move now and then: `doctor --online` asks each page the setup steps link
    to, and says which to change in web/links.py."""
    from familydb import doctor
    from familydb.web.links import LINKS

    def fetch(url):
        if url == LINKS["anthropic_keys"]:
            return 200, "https://platform.claude.com/settings/keys"
        if url == LINKS["google_service_accounts"]:
            return 404, url
        if url == LINKS["openai_keys"]:
            return 403, url  # behind a sign-in: still there
        return 200, url

    report = doctor.Report()
    doctor.check_links(report, fetch)
    (check,) = report.checks
    assert check.verdict == doctor.WARN
    assert "no answer from google_service_accounts (404)" in check.detail
    assert "anthropic_keys now at https://platform.claude.com/settings/keys" in check.detail
    assert "openai_keys" not in check.detail

    fine = doctor.Report()
    doctor.check_links(fine, lambda url: (200, url))
    assert fine.checks[0].verdict == doctor.OK


# --- what only a look at the running bot and its data can say ------------------------------------


def _later(settings, clock, minutes: int) -> App:
    from datetime import timedelta

    from familydb.clock import FixedClock

    return App(settings, FixedClock(clock.now() + timedelta(minutes=minutes), clock.tz))


def _detail_of(report: doctor.Report, name: str) -> str:
    return next(check.detail for check in report.checks if check.name == name)


def test_the_report_is_filed_under_headings_a_page_of_it_can_be_read_by(
    settings, clock, conn, family
) -> None:
    _app, report = _report(settings, clock)
    assert all(check.group for check in report.checks)
    groups = list(dict.fromkeys(check.group for check in report.checks))
    assert groups[:3] == ["Settings", "Database", "Family"]
    lines = doctor.text(report)
    assert lines[0] == "▸ Settings"
    assert "▸ Running" in lines
    assert lines[-1] == doctor.verdict(report)
    assert report.as_dict()["checks"][0]["group"] == "Settings"


def test_a_family_that_never_chose_a_time_zone_is_told_the_servers_is_utc(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.config import Settings

    monkeypatch.delenv("TZ", raising=False)
    bare = Settings(
        _env_file=None,
        provider="anthropic",
        anthropic_api_key="k",
        familydb_path=settings.familydb_path,
        family_tz=None,
        model_watch=False,
    )
    report = doctor.run(App(bare, clock))
    assert _verdict_of(report, "time zone") == doctor.WARN
    chosen = _report(settings, clock)[1]
    assert _verdict_of(chosen, "time zone") == doctor.OK
    assert "America/Vancouver" in _detail_of(chosen, "time zone")
    assert "14:03" in _detail_of(chosen, "time zone")


def test_the_database_file_is_checked_by_sqlite_itself(settings, clock, conn, family) -> None:
    _app, report = _report(settings, clock)
    assert _verdict_of(report, "integrity") == doctor.OK

    class Damaged:
        def execute(self, _sql):
            rows = [("*** in database main ***",), ("Page 3: btreeInitPage() returns error 11",)]
            return type("Rows", (), {"fetchall": lambda self: rows})()

    broken = doctor.Report()
    doctor.check_integrity(App(settings, clock), Damaged(), broken)  # type: ignore[arg-type]
    only = broken.checks[0]
    assert only.verdict == doctor.FAIL
    assert "2 problem(s)" in only.detail
    assert "maintain.sh restore" in only.fix


def test_a_file_sqlite_opens_but_cannot_read_is_a_finding_not_a_crash(settings, clock) -> None:
    settings.familydb_path.write_bytes(b"this is not a database" * 400)
    report = doctor.run(App(settings, clock))
    assert _verdict_of(report, "database") == doctor.FAIL
    assert "restore" in next(c for c in report.checks if c.name == "database").fix
    assert not report.healthy


@pytest.mark.skipif(os.name != "posix", reason="file modes are a POSIX idea")
def test_a_database_other_users_can_read_is_said_and_fix_closes_it(
    settings, clock, conn, family
) -> None:
    Path(settings.familydb_path).chmod(0o644)
    app, report = _report(settings, clock)
    assert _verdict_of(report, "data files") == doctor.WARN
    assert settings.familydb_path.name in _detail_of(report, "data files")
    doctor.correct(app, report)
    assert Path(settings.familydb_path).stat().st_mode & 0o077 == 0
    assert _verdict_of(doctor.run(app), "data files") == doctor.OK


def test_what_has_been_spent_today_is_set_against_the_limit(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.agent import spending

    monkeypatch.setattr(spending, "spent_today", lambda *_a: 0.5)
    report = _report(settings, clock, daily_spend_limit=2.0)[1]
    assert _verdict_of(report, "spending today") == doctor.OK
    assert "$0.50 of $2.00" in _detail_of(report, "spending today")
    assert "25%" in _detail_of(report, "spending today")

    monkeypatch.setattr(spending, "spent_today", lambda *_a: 2.0)
    used = _report(settings, clock, daily_spend_limit=2.0)[1]
    assert _verdict_of(used, "spending today") == doctor.WARN
    assert "until midnight" in _detail_of(used, "spending today")
    assert used.healthy  # a limit the family set is not a fault

    free = _report(settings, clock, daily_spend_limit=0)[1]
    assert "no daily limit" in _detail_of(free, "spending today")


def test_a_scheduler_that_is_up_but_quiet_is_a_failure_with_the_command(
    settings, clock, conn, family
) -> None:
    from familydb import health

    app = App(settings, clock)
    assert _verdict_of(doctor.run(app), "scheduled jobs") == doctor.SKIP  # never started
    health.ticked(app)
    ticking = doctor.run(_later(settings, clock, 3))
    assert _verdict_of(ticking, "scheduled jobs") == doctor.OK
    assert "3 min ago" in _detail_of(ticking, "scheduled jobs")

    quiet = doctor.run(_later(settings, clock, 40))
    assert _verdict_of(quiet, "scheduled jobs") == doctor.FAIL
    assert "40 min" in _detail_of(quiet, "scheduled jobs")
    assert not quiet.healthy

    health.stopped(_later(settings, clock, 41))
    on_purpose = doctor.run(_later(settings, clock, 90))
    assert _verdict_of(on_purpose, "scheduled jobs") == doctor.SKIP
    assert on_purpose.healthy


def _stuck(conn, family, update_id: str, *, minutes_ago: int, state: str = "received", **more):
    from datetime import UTC, datetime, timedelta

    from familydb.dates import utc_iso
    from familydb.store import messages

    when = utc_iso(datetime(2026, 9, 20, 21, 3, tzinfo=UTC) - timedelta(minutes=minutes_ago))
    message = messages.insert_in(
        conn,
        channel="telegram",
        channel_update_id=update_id,
        chat_id="1001",
        member_id=family["sam"].id,
        text="hello",
        now=when,
    )
    conn.execute(
        "UPDATE messages SET status = ?, error = ?, give_up = ?, processed_at = ? WHERE id = ?",
        (
            state,
            more.get("error"),
            int(more.get("give_up", False)),
            when if state == "failed" else None,
            message.id,
        ),
    )
    conn.commit()
    return message


def test_a_message_nobody_answered_is_said_with_how_to_retry_it(
    settings, clock, conn, family
) -> None:
    _stuck(conn, family, "u1", minutes_ago=2)  # being answered right now: no trouble
    assert _verdict_of(_report(settings, clock)[1], "messages") == doctor.OK

    _stuck(conn, family, "u2", minutes_ago=30, state="failed", error="boom")
    report = _report(settings, clock)[1]
    assert _verdict_of(report, "waiting messages") == doctor.WARN
    assert "1 message(s)" in _detail_of(report, "waiting messages")
    assert "retry-failed" in next(c for c in report.checks if c.name == "waiting messages").fix
    assert report.healthy


def test_a_message_given_up_on_names_why_but_a_removed_member_is_no_trouble(
    settings, clock, conn, family
) -> None:
    _stuck(
        conn, family, "u3", minutes_ago=45, state="failed", give_up=True, error="member_inactive"
    )
    assert _verdict_of(_report(settings, clock)[1], "messages") == doctor.OK

    _stuck(
        conn,
        family,
        "u4",
        minutes_ago=45,
        state="failed",
        give_up=True,
        error="AgentError: credit balance is too low\nmore",
    )
    report = _report(settings, clock)[1]
    assert _verdict_of(report, "given-up messages") == doctor.WARN
    assert "credit balance is too low" in _detail_of(report, "given-up messages")
    assert "more" not in _detail_of(report, "given-up messages")


def test_a_reply_that_was_never_sent_is_said(settings, clock, conn, family) -> None:
    from familydb.store import messages

    messages.insert_out(
        conn, channel="telegram", chat_id="1001", text="hi", now="2026-09-20T20:00:00Z"
    )
    conn.commit()
    report = _report(settings, clock)[1]
    assert _verdict_of(report, "unsent replies") == doctor.WARN
    assert "never delivered" in _detail_of(report, "unsent replies")


def test_trouble_the_admins_were_told_of_and_errors_logged_are_listed(
    settings, clock, conn, family
) -> None:
    from datetime import UTC, datetime

    from familydb.store import alerts as alert_store
    from familydb.store import problems

    clean = _report(settings, clock)[1]
    assert _verdict_of(clean, "alerts") == doctor.OK
    assert _verdict_of(clean, "logged errors") == doctor.OK

    alert_store.note(
        conn,
        "credit",
        "anthropic",
        "out of credit",
        now="2026-09-20T20:00:00Z",
        keep_after="2026-09-01T00:00:00Z",
    )
    alert_store.note(  # news, not trouble; and backups have their own row
        conn,
        "new",
        "gpt-9",
        "a new model",
        now="2026-09-20T20:00:00Z",
        keep_after="2026-09-01T00:00:00Z",
    )
    problems.record(
        conn,
        level="ERROR",
        source="familydb.jobs",
        message="digest failed",
        now=datetime(2026, 9, 20, 20, 0, tzinfo=UTC),
    )
    conn.commit()
    report = _report(settings, clock)[1]
    assert _verdict_of(report, "alerts") == doctor.WARN
    assert "credit (anthropic): out of credit" in _detail_of(report, "alerts")
    assert "gpt-9" not in _detail_of(report, "alerts")
    assert _verdict_of(report, "logged errors") == doctor.WARN
    assert "familydb.jobs: digest failed" in _detail_of(report, "logged errors")
    assert report.healthy  # told and logged is worth a look, not a stop


def test_a_name_in_env_that_nothing_reads_is_said_with_the_one_it_is_close_to(
    settings, clock, conn, family, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "WEB_ENABLED=true\nWEB_PROT=8080\nanthropic_api_key=k\nTZ=UTC\nCOMPOSE_PROFILES=tls\n"
        "export DAILY_SPEND_LIMT=3\n"
    )
    (tmp_path / ".env").chmod(0o600)
    _app, report = _report(settings, clock)
    check = next(c for c in report.checks if c.name == "env options")
    assert check.verdict == doctor.WARN
    assert "WEB_PROT (did you mean WEB_PORT?)" in check.detail
    assert "DAILY_SPEND_LIMT (did you mean DAILY_SPEND_LIMIT?)" in check.detail
    assert "TZ" not in check.detail and "anthropic_api_key" not in check.detail
    assert "COMPOSE_PROFILES" not in check.detail
    assert report.healthy  # worth a look, not a stop

    (tmp_path / ".env").write_text("WEB_ENABLED=true\nWEB_PORT=8080\n")
    (tmp_path / ".env").chmod(0o600)
    _app, clean = _report(settings, clock)
    assert "env options" not in [c.name for c in clean.checks]


# -- a company the settings define


def _with_company(settings, *, key="sk-or-1", **more):
    from familydb.config import CompanyDef

    one = CompanyDef(
        slug="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        model="vendor/chat",
        **more,
    )
    return {"companies": [one], "company_keys": {"openrouter": key} if key else {}}


def test_a_company_with_no_key_is_a_warning_that_says_what_is_missing(settings, clock) -> None:
    _app, report = _report(settings, clock, **_with_company(settings, key=""))
    check = next(c for c in report.checks if c.name == "company openrouter")
    assert check.verdict == doctor.WARN and "its key is not set" in check.detail


def test_an_unpriced_model_is_said_to_be_counted_dear(settings, clock) -> None:
    _app, report = _report(settings, clock, **_with_company(settings))
    assert _verdict_of(report, "company openrouter") == doctor.OK
    prices = next(c for c in report.checks if c.name == "company openrouter prices")
    assert prices.verdict == doctor.WARN and "vendor/chat" in prices.detail


def test_online_the_company_is_asked_about_its_key_and_its_models(
    settings, clock, monkeypatch
) -> None:
    from familydb.agent.providers.chat import ChatProvider

    for verdict, expected in (
        ("works", doctor.OK),
        ("refused", doctor.FAIL),
        ("unchecked", doctor.WARN),
    ):
        monkeypatch.setattr(ChatProvider, "check_key", lambda self, v=verdict: v)
        monkeypatch.setattr(ChatProvider, "listed_models", lambda self: ["vendor/chat"])
        app = App(settings.model_copy(update=_with_company(settings)), clock)
        report = doctor.Report()
        doctor.check_added_companies(app, report, online=True)
        assert _verdict_of(report, "company openrouter") == expected, verdict
    monkeypatch.setattr(ChatProvider, "check_key", lambda self: "works")
    monkeypatch.setattr(ChatProvider, "listed_models", lambda self: ["vendor/other"])
    report = doctor.Report()
    doctor.check_added_companies(app, report, online=True)
    gone = next(c for c in report.checks if c.name == "company openrouter")
    assert gone.verdict == doctor.WARN and "not listed: vendor/chat" in gone.detail


def test_an_added_company_does_not_answer_instead_unless_it_may_stand_in(settings, clock) -> None:
    only_added = {
        **_with_company(settings),
        "provider": "openai",
        "openai_api_key": None,
        "anthropic_api_key": None,
        "gemini_api_key": None,
    }
    _app, report = _report(settings, clock, **only_added)
    check = next(c for c in report.checks if c.name == "model key")
    assert check.verdict == doctor.FAIL and "no company with a key may stand in" in check.detail
    allowed = {**only_added, **_with_company(settings, stand_in=True)}
    _app, report = _report(settings, clock, **allowed)
    check = next(c for c in report.checks if c.name == "model key")
    assert check.verdict == doctor.WARN and "openrouter will answer instead" in check.detail


def test_a_company_that_answers_with_a_key_is_ok_not_a_crash(settings, clock) -> None:
    _app, report = _report(settings, clock, **_with_company(settings), provider="openrouter")
    assert _verdict_of(report, "model key") == doctor.OK
