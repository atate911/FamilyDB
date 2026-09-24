import json
from datetime import timedelta

from familydb.agent.history import HistoryTurn
from familydb.agent.prompt import build_messages, build_system_blocks, load_system_prompt
from familydb.agent.render import render_user_turn
from familydb.store import db, ideas
from tests.conftest import NOW_ISO


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def test_system_blocks_are_stable_and_cached(conn, settings, family, registry, clock) -> None:
    first = build_system_blocks(conn, settings)
    tools_first = registry.tool_defs()
    clock.advance(timedelta(days=3))
    second = build_system_blocks(conn, settings)
    assert _dump(first) == _dump(second)
    assert _dump(tools_first) == _dump(registry.tool_defs())
    assert len(first) == 2
    assert all(block.cacheable for block in first)
    assert "Today is" not in _dump(first)
    assert "Sam (admin)" in first[1].text
    assert "the girls (kid" in first[1].text
    assert "Calendar: not connected" in first[1].text


def test_adding_an_idea_changes_only_the_context_block(conn, settings, family) -> None:
    before = build_system_blocks(conn, settings)
    with db.transaction(conn):
        ideas.insert(conn, title="Ramen place on Main St", kind="restaurant", now=NOW_ISO)
    after = build_system_blocks(conn, settings)
    assert before[0] == after[0]
    assert before[1] != after[1]
    assert "#1 | [restaurant] | Ramen place on Main St" in after[1].text


def test_cache_ttl_is_the_provider_s_business(settings) -> None:
    from familydb.agent.providers import build

    marker = build("anthropic", settings, api=object()).cache_marker()
    assert marker == {"type": "ephemeral", "ttl": "1h"}
    brief = settings.model_copy(update={"anthropic_cache_ttl": "5m"})
    assert build("anthropic", brief, api=object()).cache_marker() == {"type": "ephemeral"}


def test_user_turn_carries_the_date_and_sender(clock) -> None:
    parts = render_user_turn("Sam", "what should we do?", clock)
    assert parts[0] == "Today is Sunday 20 September 2026, 14:03 (America/Vancouver), autumn."
    assert parts[1] == "[Sam] what should we do?"


def test_build_messages_merges_and_orders_turns(clock) -> None:
    history = [
        HistoryTurn("assistant", "stray reply first"),
        HistoryTurn("user", "[Sam] hello"),
        HistoryTurn("user", "[Alex] me too"),
        HistoryTurn("assistant", "Hi both."),
    ]
    current = render_user_turn("Sam", "what now?", clock)
    messages = build_messages(history, current)
    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert messages[0].text == "[Sam] hello\n\n[Alex] me too"
    assert messages[-1].parts == current
    assert _dump(messages).count("Today is") == 1


def test_build_messages_appends_to_a_trailing_user_turn(clock) -> None:
    history = [HistoryTurn("user", "[Sam] unanswered")]
    current = render_user_turn("Sam", "hello?", clock)
    messages = build_messages(history, current)
    assert len(messages) == 1
    assert messages[0].parts[0] == "[Sam] unanswered"
    assert messages[0].parts[1:] == current


def test_family_context_matches_tool_availability(conn, settings, family, tmp_path) -> None:
    half = settings.model_copy(
        update={"google_calendar_id": "family@group.calendar.google.com", "home_lat": 45.6}
    )
    text = build_system_blocks(conn, half)[1].text
    assert "Calendar: not connected" in text  # id set, but no token file
    assert "Weather: not configured" in text  # latitude without longitude
    token = tmp_path / "token.json"
    token.write_text("{}")
    full = half.model_copy(update={"google_token_path": token, "home_lon": -122.5})
    text = build_system_blocks(conn, full)[1].text
    assert "Calendar: connected" in text
    assert "Weather: configured" in text


def test_worker_tools_are_declared_to_the_chat_agent_too(registry, settings) -> None:
    names = registry.names()
    assert "report_finds" in names and "save_place" in names and "skip_place" in names
    assert "suggest" in names


def test_system_prompt_routes_questions_through_suggest() -> None:
    text = load_system_prompt()
    assert "Call suggest once" in text
    assert "Weekend digest:" in text and "How was #57" in text
    assert "describe_idea or lookup_place" in text


def test_the_chat_list_leaves_out_the_worker_hand_back_tools(registry, settings) -> None:

    chat = registry.tool_defs()
    names = [tool.name for tool in chat]
    assert "save_place" not in names and "skip_place" not in names
    assert "report_finds" not in names
    assert "suggest" in names and "add_idea" in names
    # They are still registered, still dispatchable, and still declared to their own worker.
    assert {"save_place", "skip_place", "report_finds"} <= set(registry.names())
    worker = registry.tool_defs(["save_place", "skip_place"])
    assert [t.name for t in worker] == ["save_place", "skip_place"]
    # Dropping them is worth real money on every message.
    everything = registry.tool_defs(registry.names())
    saved = len(_dump(everything)) - len(_dump(chat))
    assert saved > 2500


def test_the_ideas_block_stops_growing(conn, settings, family) -> None:
    from familydb.agent.prompt import trim_ideas

    small = settings.model_copy(update={"prompt_idea_limit": 3})
    with db.transaction(conn):
        for number in range(5):
            ideas.insert(conn, title=f"Idea {number}", kind="activity", now=NOW_ISO)
    block = build_system_blocks(conn, small)[1].text
    assert "Idea 4" in block and "Idea 2" in block
    assert "Idea 0" not in block and "Idea 1" not in block
    assert "(2 older ideas not listed here; use search_ideas to find them.)" in block
    # Under the limit nothing is dropped and nothing is said.
    roomy = build_system_blocks(conn, settings)[1].text
    assert "Idea 0" in roomy and "not listed here" not in roomy
    assert trim_ideas([1, 2, 3], 0) == ([1, 2, 3], 0)  # a limit of zero means no limit
    assert trim_ideas([1, 2, 3], 2) == ([2, 3], 1)


def test_the_request_is_the_same_one_this_api_always_received(conn, settings, family, clock):
    """Only the newest turn is blocks; the history behind it is one piece of text, as before."""
    from familydb.agent.providers import build
    from familydb.agent.providers.base import TurnRequest

    history = [
        HistoryTurn("user", "[Sam] hello"),
        HistoryTurn("user", "[Alex] me too"),
        HistoryTurn("assistant", "Hi both."),
    ]
    messages = build_messages(history, render_user_turn("Sam", "what now?", clock))
    request = TurnRequest(system=build_system_blocks(conn, settings), messages=messages)
    turns = build("anthropic", settings, api=object()).payload(request)["messages"]
    assert turns[0] == {"role": "user", "content": "[Sam] hello\n\n[Alex] me too"}
    assert turns[1] == {"role": "assistant", "content": "Hi both."}
    assert [part["text"] for part in turns[2]["content"]] == [
        "Today is Sunday 20 September 2026, 14:03 (America/Vancouver), autumn.",
        "[Sam] what now?",
    ]


def test_the_ideas_header_names_the_columns_the_lines_have(conn, settings, family) -> None:
    from familydb.agent.prompt import IDEAS_HEADER

    # A header naming a column the lines no longer carry tells the model about data it lacks.
    assert "details" not in IDEAS_HEADER


def test_the_discovery_worker_is_told_to_use_what_its_request_carries() -> None:
    from familydb.agent.prompt import load_prompt

    # suggest/discover.py writes these lines into the request; the prompt must say what they mean.
    text = load_prompt("discover")
    assert "Looking for:" in text and "its hours" in text


def test_vera_speaks_first_and_the_job_follows(conn, settings, family) -> None:
    from familydb.agent.prompt import build_system_blocks

    first = build_system_blocks(conn, settings)[0].text
    assert first.startswith("# Who you are\n\nYou are Vera")
    assert first.index("You are Vera") < first.index("# The job") < first.index("private planning")


def test_no_persona_leaves_only_the_job(conn, settings, family) -> None:
    from familydb.agent.prompt import build_system_blocks

    plain = settings.model_copy(update={"persona": "none"})
    first = build_system_blocks(conn, plain)[0].text
    assert first.startswith("You are the private planning assistant") and "Vera" not in first


def test_an_unknown_persona_is_refused_when_it_is_saved(settings) -> None:
    import pytest
    from pydantic import ValidationError

    from familydb.config import Settings

    with pytest.raises(ValidationError, match="no persona called 'HAL'"):
        Settings(_env_file=None, persona="HAL")
    assert Settings(_env_file=None, persona=" Vera ").persona == "vera"


def test_the_workers_never_carry_the_persona(conn, settings) -> None:
    from familydb.agent.compose import prefix
    from familydb.agent.gateway import KINDS

    for name, call in KINDS.items():
        blocks, sizes = prefix(call, conn, settings)
        worker = call.prompt != "system"
        assert ("personality" in sizes) is not worker, name
        assert ("Vera" in blocks[0].text) is not worker, name
