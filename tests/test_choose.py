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
from familydb.suggest import choosing
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
                "slot": "favorite",
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
    assert [t["name"] for t in chooser["tools"]] == ["give_picks", "reframe"]
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
            {"ref": f"idea:{ramen.id}", "slot": "favorite", "reason": "Loved it."},
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
        ({"choose_now": True}, "sam", 1, "now", None),
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


def _reframes(**changes):
    return fakes.message([fakes.tool_use("tu_r", "reframe", changes)], stop_reason="tool_use")


SATURDAY_MORNING = {
    "window": "dates",
    "start": "2026-09-26",
    "end": "2026-09-26",
    "until_time": "12:00",
    "why": "They asked about Saturday morning, not the whole weekend.",
}


def test_a_question_about_right_now_is_chosen_for_when_the_family_turned_it_on(
    settings, thursday_clock, conn, family
):
    ramen, museum = _ideas(conn)
    now = {"window": "now", "question": "anything to do right now?", "discover": False}
    api = fakes.FakeMessagesAPI(
        _asks(now),
        _picks(
            {"ref": f"idea:{ramen.id}", "slot": "favorite", "reason": "Loved it."},
            {"ref": f"idea:{museum.id}", "slot": "new", "reason": "Indoors."},
        ),
        _says("Ramen now."),
    )
    reply = _ask(_app(settings, thursday_clock, choose_now=True), api, conn, text="now?")
    assert reply.status == "ok" and _kinds(conn) == ["chat", "choose", "chat"]
    assert _suggest_result(api.requests[2])["picks"][0]["ref"] == f"idea:{ramen.id}"


def test_the_chooser_may_correct_the_framing_once_and_code_checks_it_again(
    settings, thursday_clock, conn, family
):
    """Asked as the whole weekend, the chooser reads "Saturday morning": code runs the engine on
    Saturday until noon with no search, the suggestion's row says so, the picks are checked
    against the new options, and the chat model is told what was looked at."""
    _, museum = _ideas(conn)
    api = fakes.FakeMessagesAPI(
        _asks(),
        _reframes(**SATURDAY_MORNING),
        _picks({"ref": f"idea:{museum.id}", "slot": "new", "reason": "A morning indoors."}),
        _says("The museum on Saturday morning."),
    )
    reply = _ask(_app(settings, thursday_clock), api, conn, text="what about Saturday morning?")
    assert reply.status == "ok" and _kinds(conn) == ["chat", "choose", "choose", "chat"]
    handed = api.requests[2]["messages"][-1]["content"][0]
    assert handed["type"] == "tool_result" and "## What may be picked" in handed["content"]
    data = _suggest_result(api.requests[3])
    assert data["window"]["start"] == data["window"]["end"] == "2026-09-26"
    assert data["window"]["label"].endswith("08:00-12:00")
    assert data["reframed"] == SATURDAY_MORNING["why"]
    assert [p["ref"] for p in data["picks"]] == [f"idea:{museum.id}"]
    [row] = suggestions.list_recent(conn, limit=5)
    assert (row.window_start, row.window_end) == ("2026-09-26", "2026-09-26")
    logged = [t["tool_name"] for t in calls.tool_calls_for_message(conn, reply.in_message_id)]
    assert logged == ["reframe", "give_picks", "suggest"]


def test_a_retry_replays_the_corrected_framing_with_no_call(settings, thursday_clock, conn, family):
    _, museum = _ideas(conn)
    api = fakes.FakeMessagesAPI(
        _asks(),
        _reframes(**SATURDAY_MORNING),
        _picks({"ref": f"idea:{museum.id}", "slot": "new", "reason": "A morning indoors."}),
        _asks(tu="tu_s2"),
        _says(),
    )
    _ask(_app(settings, thursday_clock), api, conn)
    assert _kinds(conn) == ["chat", "choose", "choose", "chat", "chat"]
    again = _suggest_result(api.requests[4])
    assert again["window"]["start"] == "2026-09-26" and again["reframed"]
    assert [p["ref"] for p in again["picks"]] == [f"idea:{museum.id}"]


def test_the_framing_is_corrected_once_and_only_the_framing(settings, clock, conn, family):
    from familydb.suggest.dossier import Dossier
    from familydb.tools import build_registry

    ctx = _ctx(conn, settings, clock, family["sam"], message_id=None)
    asked: list[dict] = []

    def again(changes):
        asked.append(changes)
        return Dossier("## What may be picked\nidea:1 good", {}, frozenset())

    ctx.scratch["reframe"] = again
    registry = build_registry()
    empty = registry.dispatch("reframe", {"why": "no change"}, ctx)
    assert empty.is_error and "say what to change" in empty.content
    first = registry.dispatch("reframe", {"prefer": "favorites", "why": "Our usual."}, ctx)
    assert not first.is_error and "What may be picked" in first.content
    second = registry.dispatch("reframe", {"prefer": "new", "why": "Changed my mind."}, ctx)
    assert second.is_error and "once already" in second.content
    assert asked == [{"prefer": "favorites"}]
    budget = registry.dispatch(
        "reframe", {"max_cost_level": 4, "why": "x"}, ToolContext(conn, settings, clock)
    )
    assert budget.is_error  # a limit the family set is never the chooser's to change
