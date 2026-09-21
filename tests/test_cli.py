import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from familydb import __version__
from familydb.cli import app
from familydb.errors import AgentError
from familydb.store import db
from tests import fakes

runner = CliRunner()


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "cli.sqlite3"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("FAMILYDB_TZ", "America/Vancouver")
    monkeypatch.delenv("CONSOLE_MEMBER", raising=False)
    return tmp_path


def _fake_client(*responses):
    return SimpleNamespace(beta=SimpleNamespace(messages=fakes.FakeMessagesAPI(*responses)))


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_db_members_and_ideas_commands(env: Path) -> None:
    assert runner.invoke(app, ["db", "migrate"]).exit_code == 0
    result = runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    assert result.exit_code == 0, result.output
    assert "added #1 Sam (admin)" in result.output
    assert runner.invoke(app, ["members", "add", "Sam"]).exit_code != 0  # duplicate name
    result = runner.invoke(app, ["members", "add", "the girls", "--role", "kid"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["members", "list"])
    assert "#2 the girls [kid] no channel" in result.output
    result = runner.invoke(
        app,
        ["tool", "add_idea", "--json", '{"title": "Ramen place on Main St", "kind": "restaurant"}'],
    )
    assert result.exit_code == 0, result.output
    assert '"suggested_by_name": "Sam"' in result.output
    result = runner.invoke(app, ["ideas", "list"])
    assert result.output.startswith("#1 | [restaurant] | Ramen place on Main St")
    result = runner.invoke(
        app, ["tool", "get_forecast", "--json", '{"start": "2026-09-26", "end": "2026-09-27"}']
    )
    assert result.exit_code == 0
    assert '"available": false' in result.output
    result = runner.invoke(app, ["tool", "add_idea", "--json", "{}"])
    assert result.exit_code == 1
    result = runner.invoke(app, ["db", "status"])
    assert f"schema version: {len(db.list_migrations())}" in result.output
    assert "ideas: 1" in result.output


def test_chat_command_uses_the_pipeline(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    monkeypatch.setattr(
        "familydb.agent.providers.anthropic.make_client",
        lambda settings: _fake_client(fakes.message([fakes.text("Hello Sam!")])),
    )
    result = runner.invoke(app, ["chat", "hi there"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "Hello Sam!"
    result = runner.invoke(app, ["db", "status"])
    assert "messages: 2" in result.output


def test_chat_without_members_explains(env: Path) -> None:
    result = runner.invoke(app, ["chat", "hi"])
    assert result.exit_code != 0
    assert "no family members yet" in result.output


def test_debug_prompt_prints_request(env: Path) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    result = runner.invoke(app, ["debug", "prompt", "what should we do?"])
    assert result.exit_code == 0, result.output
    assert '"cache_control"' in result.output
    assert "[Sam] what should we do?" in result.output


def test_run_command_waits_and_stops_on_sigterm(env: Path) -> None:
    proc = subprocess.Popen(
        [sys.executable, "-m", "familydb", "run"],
        env={**os.environ, "LOG_LEVEL": "INFO"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(1.5)
        assert proc.poll() is None, "run exited early"
        proc.send_signal(signal.SIGTERM)
        output, _ = proc.communicate(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 0, output
    assert "waiting" in output
    assert "stopped" in output


def test_validate_tools_reports_missing_credentials(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_client(settings):
        raise AgentError("no Anthropic credentials configured", retryable=False)

    monkeypatch.setattr("familydb.agent.providers.anthropic.make_client", _no_client)
    result = runner.invoke(app, ["debug", "validate-tools"])
    assert result.exit_code == 1
    assert "validation failed: no Anthropic credentials" in result.output


def test_enrich_command_requires_web_tools(env: Path) -> None:
    result = runner.invoke(app, ["enrich"])
    assert result.exit_code == 1
    assert "WEB_TOOLS_ENABLED" in result.output


def test_suggest_command_prints_verdicts(env: Path) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    runner.invoke(
        app, ["tool", "add_idea", "--json", '{"title": "Board game cafe", "kind": "activity"}']
    )
    result = runner.invoke(app, ["suggest", "--window", "this-weekend"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("this weekend (")
    assert "possible  #1 Board game cafe: hours unknown" in result.output
    assert "skipped: calendar not connected; weather not configured" in result.output
    result = runner.invoke(app, ["suggest", "--window", "2026-10-03..2026-10-04", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["window"]["start"] == "2026-10-03" and len(data["candidates"]) == 1
    result = runner.invoke(app, ["suggest", "--window", "tuesday"])
    assert result.exit_code != 0 and "START..END" in result.output
    result = runner.invoke(app, ["suggest", "--discover"])
    assert result.exit_code == 1 and "WEB_TOOLS_ENABLED" in result.output


def test_digest_command_needs_a_chat_id_and_shows_the_schedule(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = runner.invoke(app, ["digest", "--now"])
    assert result.exit_code == 1 and "DIGEST_CHAT_ID" in result.output
    monkeypatch.setenv("DIGEST_CHAT_ID", "-100")
    result = runner.invoke(app, ["digest"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == (
        "digest goes to telegram chat -100 every thu at 18:00 America/Vancouver; "
        "add --now to send it now"
    )
    # --now without a Telegram token has no sender, so nothing is sent.
    result = runner.invoke(app, ["digest", "--now"])
    assert result.exit_code == 1 and "digest not sent" in result.output


def test_follow_ups_command(env: Path) -> None:
    result = runner.invoke(app, ["follow-ups"])
    assert result.exit_code == 0 and result.output.startswith("follow-ups go out daily at 10:00")
    result = runner.invoke(app, ["follow-ups", "--now"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "asked about 0 plan(s)"


def test_web_command_refuses_a_page_open_to_the_network(env: Path, monkeypatch) -> None:
    monkeypatch.setenv("WEB_HOST", "0.0.0.0")
    result = runner.invoke(app, ["web"])
    assert result.exit_code == 1
    assert "WEB_PASSWORD" in result.output and "WEB_ALLOW_NO_PASSWORD" in result.output


def test_web_command_reports_a_port_it_cannot_have(env: Path, monkeypatch) -> None:
    import socket

    monkeypatch.setenv("WEB_PASSWORD", "shared")
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        port = taken.getsockname()[1]
        result = runner.invoke(app, ["web", "--port", str(port)])
    assert result.exit_code == 1 and "could not serve the page" in result.output


def test_config_says_where_each_setting_came_from(env: Path) -> None:
    from contextlib import closing

    from familydb.app import build_app
    from familydb.store import settings as settings_store

    assert runner.invoke(app, ["db", "migrate"]).exit_code == 0
    application = build_app()
    with closing(application.connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, {"effort": "high", "gemini_api_key": "gm-hunter2"})
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0, result.output
    lines = dict(line.split("=", 1) for line in result.output.splitlines())
    assert lines["effort"] == "high  # set on the settings page"
    assert lines["gemini_api_key"] == "****  # set on the settings page"
    assert lines["anthropic_api_key"] == "****  # from the environment"  # the fixture sets it
    assert lines["provider"] == "anthropic"  # nobody set it, so it is just the default
    assert "gm-hunter2" not in result.output


def test_debug_cost_reports_the_prefix_and_what_was_spent(env: Path) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    result = runner.invoke(app, ["debug", "cost"])
    assert result.exit_code == 0, result.output
    assert "Sent with every chat message" in result.output
    assert "tool definitions" in result.output and "in total" in result.output
    assert "No model calls in the last 30 days." in result.output


def test_a_command_reports_the_settings_in_force_not_the_file_s(env: Path) -> None:
    """A stored setting is what the bot is doing, so it is what a command should say."""
    from contextlib import closing

    from familydb.app import build_app
    from familydb.store import settings as settings_store

    runner.invoke(app, ["db", "migrate"])
    assert "via anthropic" in runner.invoke(app, ["debug", "cost"]).output
    application = build_app()
    with closing(application.connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, {"provider": "gemini", "gemini_model": "gemini-2.5-flash"})
    result = runner.invoke(app, ["debug", "cost"])
    assert result.exit_code == 0, result.output
    assert "chat runs on gemini-2.5-flash via gemini" in result.output
