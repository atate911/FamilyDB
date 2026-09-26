"""Settings the family can change without touching a file, and everything picking them up."""

from __future__ import annotations

import pytest

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.config import apply_overrides
from familydb.store import db
from familydb.store import settings as settings_store
from tests import fakes
from tests.conftest import NOW_ISO


def _store(conn, values, **kwargs) -> list[str]:
    with db.transaction(conn):
        return settings_store.set_many(conn, values, **kwargs)


def test_a_stored_setting_wins_over_the_environment(conn, settings) -> None:
    assert settings.provider == "anthropic"
    assert _store(conn, {"provider": "gemini", "effort": "low"}) == ["provider", "effort"]
    layered = apply_overrides(settings, settings_store.overrides(conn))
    assert layered.provider == "gemini" and layered.effort == "low"
    assert layered.anthropic_api_key == settings.anthropic_api_key  # the rest is untouched
    assert settings.provider == "anthropic"  # and the environment's own object never changes


def test_only_named_settings_can_be_stored(conn) -> None:
    with pytest.raises(ValueError, match="familydb_path is not a setting"):
        _store(conn, {"familydb_path": "/tmp/elsewhere.sqlite3"})
    with pytest.raises(ValueError, match="web_password"):
        _store(conn, {"web_password": "guessed"})
    # A row for something no longer editable is ignored rather than trusted.
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) "
            "VALUES ('web_host', '\"0.0.0.0\"', ?)",
            (NOW_ISO,),
        )
    assert "web_host" not in settings_store.overrides(conn)


def test_the_log_records_every_change_but_never_a_key(conn, family) -> None:
    sam = family["sam"].id
    _store(conn, {"effort": "high"}, changed_by=sam)
    _store(conn, {"anthropic_api_key": "sk-ant-secret"}, changed_by=sam, source="cli")
    lines = settings_store.history(conn)
    assert [line["key"] for line in lines] == ["anthropic_api_key", "effort"]
    key_line, effort_line = lines
    assert key_line["secret"] == 1
    assert key_line["old_value"] is None and key_line["new_value"] is None
    assert key_line["source"] == "cli" and key_line["changed_by_name"] == "Sam"
    assert effort_line["secret"] == 0
    assert effort_line["old_value"] == "null" and effort_line["new_value"] == '"high"'
    assert "sk-ant-secret" not in str(lines)
    assert (
        settings_store.get(conn, "anthropic_api_key") == "sk-ant-secret"
    )  # stored, just not logged


def test_storing_what_is_already_in_force_changes_nothing(conn) -> None:
    assert _store(conn, {"effort": "high"}) == ["effort"]
    assert _store(conn, {"effort": "high"}) == []
    assert len(settings_store.history(conn)) == 1


def test_the_stamp_moves_when_an_override_is_removed(conn) -> None:
    empty = settings_store.stamp(conn)
    _store(conn, {"effort": "high"})
    stored = settings_store.stamp(conn)
    assert stored != empty
    with db.transaction(conn):
        assert settings_store.clear(conn, "effort") is True
    # max(updated_at) alone would have gone back to where it started.
    assert settings_store.stamp(conn) not in (empty, stored)
    assert settings_store.overrides(conn) == {}


def test_the_app_picks_a_change_up_and_forgets_what_it_built(conn, settings, clock) -> None:
    app = App(settings.model_copy(update={"home_lat": 49.2, "home_lon": -123.1}))
    assert app.refresh() is False  # nothing stored yet
    weather = app.weather
    assert weather is not None and app.weather is weather

    _store(conn, {"provider": "gemini", "home_lat": -33.9})
    assert app.refresh() is True
    assert app.settings.provider == "gemini"
    assert app.weather is not weather  # built from the old coordinates
    assert app.clock.southern is True  # and so was the season
    assert app.refresh() is False  # the stamp has not moved, so nothing is read


def test_a_handed_in_client_is_never_replaced(conn, settings, clock) -> None:
    calendar = object()
    app = App(settings, clock, calendar=calendar)
    _store(conn, {"google_calendar_id": "family@group.calendar.google.com"})
    assert app.refresh() is True
    assert app.calendar is calendar
    assert app.clock is clock


def test_a_stored_value_that_will_not_validate_leaves_the_settings_alone(
    conn, settings, caplog
) -> None:
    app = App(settings)
    _store(conn, {"effort": "low"})
    assert app.refresh() is True and app.settings.effort == "low"
    with db.transaction(conn):
        conn.execute(
            "UPDATE app_settings SET value = '\"turbo\"', updated_at = ? WHERE key = 'effort'",
            (NOW_ISO,),
        )
        conn.execute(
            "INSERT INTO settings_log (key, changed_at, source) VALUES ('effort', ?, 'test')",
            (NOW_ISO,),
        )
    assert app.refresh() is False
    assert app.settings.effort == "low"  # what was in force stays in force
    assert "not usable" in caplog.text
    assert app.refresh() is False  # and it is not re-read on every message


def test_turning_the_log_up_from_the_page_turns_the_log_up(conn, settings) -> None:
    """A setting nothing re-reads on its own has to be applied when it moves."""
    import logging

    from familydb.app import configure_logging

    root = logging.getLogger()
    was = root.level
    try:
        configure_logging("INFO")
        app = App(settings)
        _store(conn, {"log_level": "debug"})
        assert app.refresh() is True
        assert root.level == logging.DEBUG
        with db.transaction(conn):
            settings_store.clear(conn, "log_level")
        assert app.refresh() is True
        assert root.level == logging.INFO
    finally:
        root.setLevel(was)


def test_a_message_uses_the_settings_in_force(conn, settings, clock, family) -> None:
    """Nobody calls refresh here: the pipeline does it, so the next message is the new one."""
    from familydb.pipeline import handle_incoming

    app = App(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("ok")]), fakes.message([fakes.text("ok")])
    )
    first = IncomingMessage("telegram", "1", "chat-1", "1001", "hi")
    handle_incoming(app, first, api=api, conn=conn)
    assert api.requests[0]["model"] == settings.anthropic_model
    assert api.requests[0]["max_tokens"] == settings.max_output_tokens

    _store(conn, {"anthropic_model": "claude-haiku-4-5-20251001", "max_output_tokens": 2000})
    second = IncomingMessage("telegram", "2", "chat-1", "1001", "and again")
    handle_incoming(app, second, api=api, conn=conn)
    assert api.requests[1]["model"] == "claude-haiku-4-5-20251001"
    assert api.requests[1]["max_tokens"] == 2000


def test_a_job_uses_the_settings_in_force(conn, settings, clock, family) -> None:
    """Same for the background jobs, which nothing else wakes up to tell."""
    from familydb.jobs.enrich import run_enrichment
    from familydb.jobs.follow_ups import run_follow_ups

    app = App(settings, clock)
    nothing = dict.fromkeys(("done", "skipped", "failed", "deferred"), 0)
    assert run_enrichment(app) == nothing
    assert app.settings.web_tools_enabled is False

    _store(conn, {"web_tools_enabled": True, "enrich_batch": 7})
    assert run_enrichment(app) == nothing  # no pending ideas, so still no model call
    assert app.settings.web_tools_enabled is True and app.settings.enrich_batch == 7

    _store(conn, {"log_level": "DEBUG"})
    assert run_follow_ups(app) == 0
    assert app.settings.log_level == "DEBUG"


def test_the_page_follows_the_title_it_is_given(conn, settings, clock, family) -> None:
    from familydb.web import create_app

    app = App(settings, clock)
    client = create_app(app).test_client()
    assert "FamilyDB" in client.get("/").text
    _store(conn, {"web_title": "The Tate family"})
    assert "The Tate family" in client.get("/").text


def test_the_schedule_follows_the_settings(conn, settings, clock) -> None:
    from datetime import timedelta

    from familydb.jobs.scheduler import apply_settings, build_scheduler

    app = App(settings, clock)
    scheduler = build_scheduler(app)
    assert {job.id for job in scheduler.get_jobs()} == {
        "retry_failed",
        "follow_ups",
        "catch_up",
        "settings_watch",
        "reminders",
        "forget_locations",
        "nudges",
        "plan_checks",
    }
    assert scheduler.get_job("retry_failed").trigger.interval == timedelta(
        minutes=settings.retry_interval_minutes
    )

    _store(conn, {"retry_interval_minutes": 30, "digest_chat_id": "-100", "follow_up_hour": 9})
    assert sorted(apply_settings(app, scheduler)) == [
        "follow_ups",
        "retry_failed",
        "weekend_digest on",
    ]
    assert scheduler.get_job("retry_failed").trigger.interval == timedelta(minutes=30)
    assert str(scheduler.get_job("follow_ups").trigger) == "cron[hour='9']"
    assert apply_settings(app, scheduler) == []  # nothing moved, nothing touched

    _store(conn, {"digest_chat_id": None})
    assert apply_settings(app, scheduler) == ["weekend_digest off"]
    assert scheduler.get_job("weekend_digest") is None

    _store(conn, {"task_nudges": False})
    assert apply_settings(app, scheduler) == ["nudges off"]
    assert scheduler.get_job("nudges") is None

    _store(conn, {"plan_check_hour": 20})
    assert apply_settings(app, scheduler) == ["plan_checks"]
    assert str(scheduler.get_job("plan_checks").trigger) == "cron[hour='20']"
    _store(conn, {"plan_checks": False})
    assert apply_settings(app, scheduler) == ["plan_checks off"]


def test_the_schedule_moves_even_when_the_page_saw_the_change_first(conn, settings, clock) -> None:
    """The form and every page view refresh too, and must not swallow the scheduler's turn."""
    from datetime import timedelta

    from familydb.jobs.scheduler import apply_settings, build_scheduler

    app = App(settings, clock)
    scheduler = build_scheduler(app)

    _store(conn, {"retry_interval_minutes": 42})
    assert app.refresh() is True  # the settings form, or somebody opening a page
    assert app.settings.retry_interval_minutes == 42

    assert apply_settings(app, scheduler) == ["retry_failed"]
    assert scheduler.get_job("retry_failed").trigger.interval == timedelta(minutes=42)
