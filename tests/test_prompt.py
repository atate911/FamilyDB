import json
from datetime import timedelta

from familydb.agent.history import HistoryTurn
from familydb.agent.prompt import build_messages, build_system_blocks, load_system_prompt
from familydb.agent.render import render_audience_line, render_user_turn
from familydb.store import db, ideas
from familydb.store.members import Member
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
    assert Settings(_env_file=None, persona=" Default ").persona == "default"


def test_the_workers_never_carry_the_persona(conn, settings) -> None:
    from familydb.agent.compose import prefix
    from familydb.agent.gateway import KINDS

    for name, call in KINDS.items():
        blocks, sizes = prefix(call, conn, settings)
        worker = call.prompt != "system"
        assert ("personality" in sizes) is not worker, name
        assert ("Vera" in blocks[0].text) is not worker, name


PRECEDENCE = "Where who you are and the job disagree, the job wins."


def test_the_product_says_the_job_wins_whoever_she_is(conn, settings, family) -> None:
    first = build_system_blocks(conn, settings)[0].text
    assert first.count(PRECEDENCE) == 1
    assert first.index("You are Vera") < first.index(PRECEDENCE) < first.index("private planning")
    plain = settings.model_copy(update={"persona": "none"})
    assert PRECEDENCE not in build_system_blocks(conn, plain)[0].text


def test_a_rewrite_of_her_that_leaves_the_rule_out_still_gets_it(conn, settings, family) -> None:
    """Her own character says the job wins; a family's rewrite of her need not."""
    rewritten = settings.model_copy(
        update={"persona_text": "You are {name}. Be very brief, and a little dry."}
    )
    first = build_system_blocks(conn, rewritten)[0].text
    assert first.startswith(
        "# Who you are\n\nYou are Vera. Be very brief, and a little dry.\n\n# The job\n\n"
        f"{PRECEDENCE}\n\nYou are the private planning assistant"
    )


def test_the_spec_keeps_it_suitable_for_kids_whoever_she_is() -> None:
    """The rule is the product's, where no rewrite of her reaches it, and it is written once."""
    text = load_system_prompt()
    assert "a line before the message says who reads it" in text
    listening = text.index("## Who is listening")
    assert listening < text.index("## Reply style")
    assert "whoever you are told you are" in text[listening:]
    assert text.count("sensitive reminder") == 1
    assert text.index("sensitive reminder") > listening


def _member(name: str, role: str, *, active: bool = True) -> Member:
    return Member(id=len(name), display_name=name, role=role, active=active, created_at=NOW_ISO)


GROWN_UPS = [_member("Sam", "admin"), _member("Alex", "parent")]
WITH_A_KID = [*GROWN_UPS, _member("Mia", "kid")]
GROUP = "This is the family's group chat: everyone in it reads your reply"
PAGE = "This is the family's conversation on the page: everyone who signs in reads it"


def test_a_private_chat_has_no_audience_line() -> None:
    assert render_audience_line("telegram", "1001", WITH_A_KID) is None
    assert render_audience_line("console", "console", WITH_A_KID) is None


def test_a_group_says_everyone_in_it_reads_the_reply() -> None:
    assert render_audience_line("telegram", "-100123", GROWN_UPS) == f"{GROUP}."


def test_a_group_says_kids_read_it_when_the_family_has_one() -> None:
    assert render_audience_line("telegram", "-100123", WITH_A_KID) == f"{GROUP}, kids among them."


def test_the_page_s_chat_is_read_by_everyone_who_signs_in() -> None:
    assert render_audience_line("web", "web", GROWN_UPS) == f"{PAGE}."
    assert render_audience_line("web", "web", WITH_A_KID) == f"{PAGE}, kids among them."


def test_a_kid_who_is_switched_off_is_not_counted() -> None:
    family = [*GROWN_UPS, _member("Mia", "kid", active=False)]
    assert render_audience_line("telegram", "-100123", family) == f"{GROUP}."
    assert render_audience_line("web", "web", family) == f"{PAGE}."


def test_the_audience_line_goes_between_the_date_and_the_message(clock) -> None:
    today = "Today is Sunday 20 September 2026, 14:03 (America/Vancouver), autumn."
    assert render_user_turn("Sam", "hi all", clock, f"{GROUP}.") == [
        today,
        f"{GROUP}.",
        "[Sam] hi all",
    ]
    # A private chat's turn is what it always was: the date, then the message.
    assert render_user_turn("Sam", "hi", clock, None) == [today, "[Sam] hi"]
