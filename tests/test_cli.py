from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from familydb import __version__
from familydb.cli import app
from tests import fakes

runner = CliRunner()


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("FAMILYDB_PATH", str(tmp_path / "cli.sqlite3"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TZ", "America/Vancouver")
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
    assert "schema version: 1" in result.output
    assert "ideas: 1" in result.output


def test_chat_command_uses_the_pipeline(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner.invoke(app, ["members", "add", "Sam", "--role", "admin"])
    monkeypatch.setattr(
        "familydb.app.make_client",
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
