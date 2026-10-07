"""Choosing what to suggest: a stronger call inside `suggest` picks from the dossier, the picks
lead the result the chat model words, and whenever it should not or cannot, nothing changes."""

from __future__ import annotations

import json

import pytest

from familydb.agent.prompt import load_prompt
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
from familydb.store import calls, ideas, outcomes, suggestions
from familydb.store.db import transaction
from familydb.suggest import choose as choosing
from familydb.suggest.types import SuggestInput
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO

WEEKEND = {
    "window": "this_weekend",
    "question": "what should we do this weekend?",
    "discover": False,
}


def _ideas(conn):
    with transaction(conn):
        ramen = ideas.insert(
            conn, title="Ramen at Menya", kind="restaurant", setting="indoor", now=NOW_ISO
        )
        museum = ideas.insert(
            conn, title="Science museum", kind="outing", setting="indoor", now=NOW_ISO
        )
        outcome = outcomes.insert(
            conn,
            idea_id=ramen.id,
            plan_id=None,
            happened_on="2026-06-13",
            rating=9,
            would_repeat=True,
            notes="the girls loved it",
            recorded_by=None,
            now=NOW_ISO,
        )
        ideas.apply_outcome(
            conn, ramen.id, happened_on=outcome.happened_on, avg_rating=9.0, now=NOW_ISO
        )
    return ramen, museum


def _app(settings, clock, **extra) -> App:
    return App(settings.model_copy(update={"choosing": True, **extra}), clock)


def _asks(suggest=WEEKEND, tu="tu_s"):
    return fakes.message([fakes.tool_use(tu, "suggest", suggest)], stop_reason="tool_use")


def _picks(*picks, framing=None):
    return fakes.message(
        [fakes.tool_use("tu_p", "give_picks", {"picks": list(picks), "framing": framing})],
        stop_reason="tool_use",
    )


def _says(words="Ramen, then the museum."):
    return fakes.message([fakes.text(words)])


def _ask(app, api, conn, text="what should we do this weekend?", update="7"):
    message = IncomingMessage("telegram", update, "chat-1", "1001", text)
    return handle_incoming(app, message, api=api, conn=conn)


def _suggest_result(request) -> dict:
    result = request["messages"][-1]["content"][0]
    assert result["type"] == "tool_result"
    return json.loads(result["content"])


def _kinds(conn) -> list[str]:
    return [row[0] for row in conn.execute("SELECT kind FROM llm_calls ORDER BY id")]


def test_the_picks_lead_what_the_chat_model_is_given(settings, thursday_clock, conn, family):
    ramen, museum = _ideas(conn)
    api = fakes.FakeMessagesAPI(
        _asks(),
        _picks(
            {
                "ref": f"idea:{ramen.id}",
                "slot": "favourite",
                "reason": "The girls loved it.",
                "cites": [f"idea:{ramen.id}"],
            },
            {"ref": f"idea:{museum.id}", "slot": "new", "reason": "Never tried, and indoors."},
            framing="An easy weekend.",
        ),
        _says(),
    )
    reply = _ask(_app(settings, thursday_clock), api, conn)
    assert reply.status == "ok" and reply.text == "Ramen, then the museum."
    chooser = api.requests[1]
    assert chooser["system"][0]["text"] == load_prompt("choose")
    assert [t["name"] for t in chooser["tools"]] == ["give_picks"]
    assert chooser["model"] == "claude-opus-5"  # the chat company, at the best level
    asked = chooser["messages"][0]["content"][1]["text"]
    assert '"the girls loved it"' in asked and "## What may be picked" in asked
    data = _suggest_result(api.requests[2])
    assert [p["ref"] for p in data["picks"]] == [f"idea:{ramen.id}", f"idea:{museum.id}"]
    assert data["framing"] == "An easy weekend."
    assert data["candidates"][0]["idea_id"] == ramen.id
    assert _kinds(conn) == ["chat", "choose", "chat"]
    logged = [t["tool_name"] for t in calls.tool_calls_for_message(conn, reply.in_message_id)]
    assert logged == ["give_picks", "suggest"]
    [kept] = suggestions.picked_since(conn, since="2026-01-01T00:00:00Z")
    assert [p["title"] for p in kept.picks["picks"]] == ["Ramen at Menya", "Science museum"]


def test_a_question_about_right_now_is_not_chosen(settings, thursday_clock, conn, family):
    _ideas(conn)
    now = {"window": "now", "question": "anything open right now?", "discover": False}
    api = fakes.FakeMessagesAPI(_asks(now), _says("The museum is open."))
    reply = _ask(_app(settings, thursday_clock), api, conn, text="anything open right now?")
    assert reply.status == "ok" and _kinds(conn) == ["chat", "chat"]
    assert "picks" not in _suggest_result(api.requests[1])


def test_a_choice_that_fails_leaves_the_engine_s_order(settings, thursday_clock, conn, family):
    _ideas(conn)
    wrong = {"ref": "idea:999", "slot": "new", "reason": "Not an option."}
    api = fakes.FakeMessagesAPI(_asks(), _picks(wrong), _picks(wrong), _says())
    reply = _ask(_app(settings, thursday_clock), api, conn)
    assert reply.status == "ok"
    assert _kinds(conn) == ["chat", "choose", "choose", "chat"]  # two calls at most
    data = _suggest_result(api.requests[3])
    assert "picks" not in data and data["candidates"]
    assert suggestions.picked_since(conn, since="2026-01-01T00:00:00Z") == []


def test_one_choice_a_message_however_often_suggest_is_called(
    settings, thursday_clock, conn, family
):
    ramen, museum = _ideas(conn)
    api = fakes.FakeMessagesAPI(
        _asks(),
        _picks(
            {"ref": f"idea:{ramen.id}", "slot": "favourite", "reason": "Loved it."},
            {"ref": f"idea:{museum.id}", "slot": "new", "reason": "Indoors."},
        ),
        _asks(tu="tu_s2"),
        _says(),
    )
    _ask(_app(settings, thursday_clock), api, conn)
    assert _kinds(conn) == ["chat", "choose", "chat", "chat"]
    again = _suggest_result(api.requests[3])
    assert [p["ref"] for p in again["picks"]] == [f"idea:{ramen.id}", f"idea:{museum.id}"]


def test_a_month_s_budget_spent_makes_no_call(settings, thursday_clock, conn, family):
    _ideas(conn)
    with transaction(conn):
        calls.log_llm_call(
            conn,
            message_id=None,
            iteration=1,
            model="claude-opus-5",
            served_model=None,
            request_id=None,
            stop_reason="end",
            usage={},
            duration_ms=1,
            now="2026-09-02T20:00:00Z",
            provider="anthropic",
            cost_usd=4.99,
            kind="choose",
        )
    api = fakes.FakeMessagesAPI(_asks(), _says())
    _ask(_app(settings, thursday_clock), api, conn)
    assert _kinds(conn) == ["choose", "chat", "chat"]  # the seeded row, then no choice


def _ctx(conn, settings, clock, member, message_id=1) -> ToolContext:
    return ToolContext(
        conn=conn, settings=settings, clock=clock, member=member, message_id=message_id
    )


@pytest.mark.parametrize(
    "change, who, message_id, window, why",
    [
        ({"choosing": False}, "sam", 1, "this_weekend", "off"),
        ({}, "sam", 1, "now", "a question about right now"),
        ({}, "sam", None, "this_weekend", "not a chat message"),
        ({}, "girls", 1, "this_weekend", "a kid's question"),
        ({"choose_budget": 0}, "sam", 1, "this_weekend", "no budget"),
    ],
)
def test_who_and_what_is_never_chosen_for(
    settings, clock, conn, family, change, who, message_id, window, why
):
    live = settings.model_copy(update={"choosing": True, **change})
    ctx = _ctx(conn, live, clock, family[who], message_id)
    args = SuggestInput(window=window, question="?")
    assert choosing.reason_not_to(ctx, args) == why
