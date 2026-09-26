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
    monkeypatch.setenv("PROVIDER", "anthropic")  # the scripted fake speaks Claude's API
    monkeypatch.setenv("FAMILYDB_TZ", "America/Vancouver")
    monkeypatch.delenv("CONSOLE_MEMBER", raising=False)
    return tmp_path


def _fake_client(*responses):
    return SimpleNamespace(
        beta=SimpleNamespace(messages=fakes.FakeMessagesAPI(*responses)),
        close=lambda: None,  # the provider closes the one it builds to check for a key
    )


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
    assert f"schema version: {db.list_migrations()[-1][0]}" in result.output
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
    assert "This is the family's" not in result.output  # the console is the sender's alone


def test_debug_prompt_says_who_reads_the_chat_it_names(env: Path) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    runner.invoke(app, ["members", "add", "Mia", "--role", "kid"])
    group = runner.invoke(app, ["debug", "prompt", "--chat=-100123", "hi all"])
    assert group.exit_code == 0, group.output
    assert "everyone in it reads your reply, kids among them." in group.output
    page = runner.invoke(app, ["debug", "prompt", "--chat", "web", "hi all"])
    assert "everyone who signs in reads it, kids among them." in page.output


def test_debug_prompt_is_built_from_what_the_page_stored(env: Path) -> None:
    """Her name and the chat's level as the page set them, as the pipeline would send them."""
    from contextlib import closing

    from familydb.app import build_app
    from familydb.store import settings as settings_store

    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    with closing(build_app().connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, {"persona_name": "Juno", "chat_level": "best"})
    result = runner.invoke(app, ["debug", "prompt", "hi"])
    assert result.exit_code == 0, result.output
    assert '"model": "claude-opus-5"' in result.output
    assert "You are Juno" in result.output and "You are Vera" not in result.output


@pytest.mark.skipif(os.name == "nt", reason="Windows terminate does not deliver POSIX SIGTERM")
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


def test_validate_tools_asks_about_the_model_that_answers_the_chat(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At the level the page stored, which a command that did not read the page would miss."""
    from contextlib import closing

    from familydb.agent.providers.anthropic import AnthropicProvider
    from familydb.app import build_app
    from familydb.store import settings as settings_store

    runner.invoke(app, ["db", "migrate"])
    with closing(build_app().connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, {"chat_level": "best"})
    asked: list[str | None] = []

    def count(self, request):
        asked.append(request.model)
        return 1234

    monkeypatch.setattr(AnthropicProvider, "count_tokens", count)
    result = runner.invoke(app, ["debug", "validate-tools"])
    assert result.exit_code == 0, result.output
    assert asked == ["claude-opus-5"]
    assert "accepted by claude-opus-5 via anthropic" in result.output


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
    assert lines["weather_units"] == "metric"  # nobody set it, so it is just the default
    assert "gm-hunter2" not in result.output


def test_config_prints_a_rewrite_of_her_on_one_line(env: Path) -> None:
    """Kept per persona, a rewrite prints as what it is stored as, its line breaks escaped, even
    when it was stored as one string before."""
    from contextlib import closing

    from familydb.app import build_app
    from familydb.store import settings as settings_store

    assert runner.invoke(app, ["db", "migrate"]).exit_code == 0
    application = build_app()
    with closing(application.connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, {"persona_text": "You are {name}.\nDry."})
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0, result.output
    lines = dict(line.split("=", 1) for line in result.output.splitlines())
    assert lines["persona_text"] == (
        "{'default': {'text': 'You are {name}.\\nDry.', 'of': ''}}  # set on the settings page"
    )


def test_config_shortens_a_long_text_and_says_how_long_it_is(env: Path) -> None:
    """A rewrite keeps her whole character as it shipped, a page of prose: the printout gives the
    start of each long text on the Personality page and its real length, one setting to a line,
    and the settings themselves keep all of it."""
    from contextlib import closing

    from familydb import personas
    from familydb.app import build_app
    from familydb.cli import SHOWN_CHARACTERS
    from familydb.config import apply_overrides, load_settings
    from familydb.store import settings as settings_store

    hers = personas.load(personas.DEFAULT).character
    about = "We are the Tates.\n" + "Mia is eight and climbs anything. " * 10
    reminder = "Reminder: {title}{who}, task #{task}. Tell me when it's done.\nBins, {who}!"
    stored = {
        "persona_text": {"default": {"text": "You are {name}.\nDry.", "of": hers}},
        "about_family": about,
        "voice_lines": {"reminder": reminder},
        "google_calendar_id": "c_" + "0123456789abcdef" * 4 + "@group.calendar.google.com",
    }
    assert runner.invoke(app, ["db", "migrate"]).exit_code == 0
    application = build_app()
    with closing(application.connect()) as conn, db.transaction(conn):
        settings_store.set_many(conn, stored)
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0, result.output
    # One setting to a line: a text's own line breaks would leave a line with no "=" in it.
    lines = dict(line.split("=", 1) for line in result.output.splitlines())

    page = "  # set on the settings page"

    def cut(text: str) -> str:
        return f"{text[:SHOWN_CHARACTERS].rstrip()}… ({len(text):,} characters)"

    # A short text is as it was, and a long one its start and its length.
    rewrite = {"default": {"text": "You are {name}.\nDry.", "of": cut(hers)}}
    assert lines["persona_text"] == str(rewrite) + page
    assert lines["about_family"] == cut(about).replace("\n", "\\n") + page
    assert lines["voice_lines"] == str({"reminder": cut(reminder)}) + page
    # A setting that is not a text of hers or the family's prints whole, however long.
    assert lines["google_calendar_id"] == stored["google_calendar_id"] + page

    # Anything else that reads the settings still has all of it.
    masked = apply_overrides(load_settings(), stored).masked()
    assert masked["persona_text"]["default"]["of"] == hers
    assert masked["about_family"] == about
    assert masked["voice_lines"] == {"reminder": reminder}


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
