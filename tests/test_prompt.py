import json
from datetime import timedelta

from familydb.agent.history import HistoryTurn
from familydb.agent.prompt import build_messages, build_system_blocks, cache_control
from familydb.agent.render import render_user_turn
from familydb.store import db, ideas
from tests.conftest import NOW_ISO


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def test_system_blocks_are_stable_and_cached(conn, settings, family, registry, clock) -> None:
    first = build_system_blocks(conn, settings)
    tools_first = registry.api_tools(settings)
    clock.advance(timedelta(days=3))
    second = build_system_blocks(conn, settings)
    assert _dump(first) == _dump(second)
    assert _dump(tools_first) == _dump(registry.api_tools(settings))
    assert len(first) == 2
    assert all(block["cache_control"] == {"type": "ephemeral"} for block in first)
    assert "Today is" not in _dump(first)
    assert "Sam (admin)" in first[1]["text"]
    assert "the girls (kid" in first[1]["text"]
    assert "Calendar: not connected" in first[1]["text"]


def test_adding_an_idea_changes_only_the_context_block(conn, settings, family) -> None:
    before = build_system_blocks(conn, settings)
    with db.transaction(conn):
        ideas.insert(conn, title="Ramen place on Main St", kind="restaurant", now=NOW_ISO)
    after = build_system_blocks(conn, settings)
    assert before[0] == after[0]
    assert before[1] != after[1]
    assert "#1 | [restaurant] | Ramen place on Main St" in after[1]["text"]


def test_cache_ttl_setting(settings) -> None:
    assert cache_control(settings) == {"type": "ephemeral"}
    hourly = settings.model_copy(update={"anthropic_cache_ttl": "1h"})
    assert cache_control(hourly) == {"type": "ephemeral", "ttl": "1h"}


def test_user_turn_carries_the_date_and_sender(clock) -> None:
    blocks = render_user_turn("Sam", "what should we do?", clock)
    assert (
        blocks[0]["text"] == "Today is Sunday 20 September 2026, 14:03 (America/Vancouver), autumn."
    )
    assert blocks[1]["text"] == "[Sam] what should we do?"


def test_build_messages_merges_and_orders_turns(clock) -> None:
    history = [
        HistoryTurn("assistant", "stray reply first"),
        HistoryTurn("user", "[Sam] hello"),
        HistoryTurn("user", "[Alex] me too"),
        HistoryTurn("assistant", "Hi both."),
    ]
    current = render_user_turn("Sam", "what now?", clock)
    messages = build_messages(history, current)
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "[Sam] hello\n\n[Alex] me too"
    assert messages[-1]["content"] == current
    assert _dump(messages).count("Today is") == 1


def test_build_messages_appends_to_a_trailing_user_turn(clock) -> None:
    history = [HistoryTurn("user", "[Sam] unanswered")]
    current = render_user_turn("Sam", "hello?", clock)
    messages = build_messages(history, current)
    assert len(messages) == 1
    assert messages[0]["content"][0] == {"type": "text", "text": "[Sam] unanswered"}
    assert messages[0]["content"][1:] == current
