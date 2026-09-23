"""Opt-in checks against the real Anthropic API.

Run with `FAMILYDB_LIVE=1 uv run pytest -m live` and ANTHROPIC_API_KEY set. Skipped otherwise.
"""

from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path

import pytest

from familydb.app import App
from familydb.channels.console import one_shot
from familydb.config import Settings
from familydb.store import calls, db, members

pytestmark = pytest.mark.live

LIVE = os.environ.get("FAMILYDB_LIVE") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))
skip_unless_live = pytest.mark.skipif(not LIVE, reason="set FAMILYDB_LIVE=1 and ANTHROPIC_API_KEY")


def _live_app(tmp_path: Path) -> App:
    settings = Settings(
        _env_file=None,
        provider="anthropic",
        familydb_path=tmp_path / "live.sqlite3",
        family_tz="America/Vancouver",
    )
    app = App(settings)
    app.migrate()
    with closing(app.connect()) as conn, db.transaction(conn):
        members.add(conn, "Sam", "admin")
    return app


@skip_unless_live
def test_two_turns_save_an_idea_and_hit_the_cache(tmp_path: Path) -> None:
    app = _live_app(tmp_path)
    first = one_shot(app, "we should try that new ramen place on Main St sometime", "Sam")
    assert first is not None and first.status == "ok", first
    assert any(a["tool"] == "add_idea" and a["ok"] for a in first.actions), first.actions
    second = one_shot(app, "tell me about #1", "Sam")
    assert second is not None and second.status == "ok", second
    with closing(app.connect()) as conn:
        rows = calls.recent_llm_calls(conn, limit=10)
    later_calls = rows[:-1]  # every call after the very first can read the cache
    assert any((row["cache_read_input_tokens"] or 0) > 0 for row in later_calls), rows


@skip_unless_live
def test_tool_schemas_are_accepted_by_the_api(tmp_path: Path) -> None:
    from familydb.agent.providers.base import Message, TurnRequest

    app = _live_app(tmp_path)
    provider = app.provider("chat")
    request = TurnRequest(
        system=[],
        messages=[Message("user", ["hello"])],
        tools=app.registry.tool_defs(app.registry.names()),
    )
    assert provider.count_tokens(request) > 0
