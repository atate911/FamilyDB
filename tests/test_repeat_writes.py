"""A write repeated for the same message changes nothing (CLAUDE.md, nothing lost or done twice).

A retry tells the model what already ran (`render_retry_note`), but that note is read from the
tool-call log, which is written after the tool's own transaction; and a model may call a tool
twice in one turn anyway. So each writing tool holds the outcome itself: the same call, for the
same message, a second time leaves the household as the first left it. A new writing tool is a
line in CASES, or in EXEMPT with its reason.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from familydb.store import db, messages
from familydb.tools import ToolContext, build_registry
from tests.conftest import NOW_ISO

# Bookkeeping, not the household: the log of calls, what they cost, and the full-text indexes
# (rebuilt by triggers whatever was written).
NOT_STATE = ("tool_calls", "llm_calls", "ai_texts", "problems", "spend_holds", "schema_checksums")

# Tools that may rightly do something twice in one message, each with why.
EXEMPT = {
    # "Undo that, and the one before" is two undos in one message; each takes back its own change
    # (`undo.take_back` claims the call it undoes, so the same change is never undone twice).
    "undo",
}


def _state(conn) -> dict[str, list[tuple]]:
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        if row[0] not in NOT_STATE and "_fts" not in row[0] and not row[0].startswith("sqlite_")
    ]
    return {
        t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY rowid")] for t in tables
    }


def _ctx(env, member, message_id: int | None) -> ToolContext:
    return ToolContext(
        conn=env.conn,
        settings=env.settings,
        clock=env.app.clock,
        member=member,
        calendar=env.cal,
        message_id=message_id,
    )


def _made(env, name: str, args: dict[str, Any], member=None) -> dict[str, Any]:
    """Something to act on, made under no message of its own."""
    result = env.registry.dispatch(name, args, _ctx(env, member or env.member, None))
    assert not result.is_error, result.content
    return json.loads(result.content)


def _idea(env) -> int:
    return _made(env, "add_idea", {"title": "Oregon Zoo", "kind": "outing"})["id"]


def _plan(env) -> int:
    made = _made(
        env,
        "create_event",
        {"title": "Zoo", "start": "2026-09-26T10:00:00-07:00", "end": "2026-09-26T13:00:00-07:00"},
    )
    return made["plan"]["id"]


def _task(env, **more) -> int:
    return _made(env, "add_task", {"title": "Water the plants", **more})["task"]["id"]


def _wish(env) -> int:
    kid = env.family["girls"]
    return _made(env, "add_wish", {"title": "A telescope", "topic": "space"}, kid)["wish"]["id"]


def _find(env) -> int:
    from familydb.scouting.search import SOURCE
    from familydb.store import finds

    with db.transaction(env.conn):
        kept, _ = finds.keep(
            env.conn,
            SOURCE,
            SOURCE,
            [finds.NewFind(title="Harvest fair", url="https://example.org/fair")],
            now=NOW_ISO,
        )
    return kept[0].id


# label -> (who calls it, the call's input given what was set up); a label is the tool's name,
# or the tool's name and what is special about this call after a colon.
CASES: dict[str, tuple[str, Callable[[SimpleNamespace], dict[str, Any]]]] = {
    "add_idea": ("sam", lambda env: {"title": "Ramen place", "kind": "restaurant"}),
    "update_idea": ("sam", lambda env: {"id": _idea(env), "title": "The Oregon Zoo"}),
    "look_up_now": ("sam", lambda env: {"idea_ids": [_idea(env)]}),
    "record_outcome": ("sam", lambda env: {"idea_id": _idea(env), "rating": 8}),
    "create_event": (
        "sam",
        lambda env: {
            "title": "Pumpkin patch",
            "start": "2026-09-27T10:00:00-07:00",
            "end": "2026-09-27T12:00:00-07:00",
        },
    ),
    "update_event": ("sam", lambda env: {"plan_id": _plan(env), "title": "Zoo with Grandma"}),
    "delete_event": ("sam", lambda env: {"plan_id": _plan(env)}),
    "add_task": ("sam", lambda env: {"title": "Call the plumber"}),
    "update_task": ("sam", lambda env: {"task_id": _task(env), "status": "done"}),
    "update_task:a repeating one, done": (
        "sam",
        lambda env: {
            "task_id": _task(env, remind_at="2026-09-25T09:00", repeat_every=1, repeat_unit="week"),
            "status": "done",
        },
    ),
    "update_task:a repeating one, done, counted from done": (
        "sam",
        lambda env: {
            "task_id": _task(
                env,
                remind_at="2026-09-25T09:00",
                repeat_every=2,
                repeat_unit="week",
                repeat_from="done",
            ),
            "status": "done",
        },
    ),
    "shopping_list": ("sam", lambda env: {"action": "add", "items": ["milk"]}),
    "remember": (
        "sam",
        lambda env: {"changes": [{"action": "add", "category": "food", "fact": "loves noodles"}]},
    ),
    "recipe": ("sam", lambda env: {"action": "save", "title": "Tacos", "total_minutes": 30}),
    "add_wish": ("girls", lambda env: {"title": "A puppy", "topic": "pet"}),
    "update_wish": ("girls", lambda env: {"wish_id": _wish(env), "status": "withdrawn"}),
    "turn_away": (
        "girls",
        lambda env: {"summary": "Asked for a phone", "concern": "rule", "parent_may_review": True},
    ),
    "pass_find": ("sam", lambda env: {"find_id": _find(env)}),
}


@pytest.fixture
def home(env, family):
    env.family = family
    with db.transaction(env.conn):
        asked = messages.insert_in(
            env.conn,
            channel="telegram",
            channel_update_id="u1",
            chat_id="1001",
            member_id=family["sam"].id,
            text="the message being answered",
            now=NOW_ISO,
        )
    env.message_id = asked.id
    return env


def test_every_writing_tool_is_held_to_it() -> None:
    writing = {s.name for s in build_registry().specs() if s.writes and not s.worker_only}
    assert writing == {label.split(":")[0] for label in CASES} | EXEMPT


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_same_write_twice_for_one_message_changes_nothing(home, name) -> None:
    who, make = CASES[name]
    args = make(home)
    member = home.family[who]
    name = name.split(":")[0]
    first = home.registry.dispatch(name, args, _ctx(home, member, home.message_id))
    assert not first.is_error, first.content
    once = _state(home.conn)
    again = home.registry.dispatch(name, args, _ctx(home, member, home.message_id))
    twice = _state(home.conn)
    changed = {t: (once[t], twice[t]) for t in once if once[t] != twice[t]}
    assert not changed, f"{name} again changed {sorted(changed)}: {again.content}"
