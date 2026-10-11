"""Judgement calls: questions filed by code when a change needs weighing, asked of a stronger model
together once a day (a refusal at once), checked, and acted on only within what the family set."""

from __future__ import annotations

import re
from datetime import datetime

import anthropic
import pytest

from familydb import judgement, model_watch
from familydb.agent.providers import parts, prices
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.base.errors import AgentError
from familydb.store import calls
from familydb.store import judgements as store
from familydb.store.db import transaction
from tests import fakes
from tests.conftest import TZ
from tests.test_alerts import _found
from tests.test_fallback import _turn
from tests.test_model_watch import CLAUDE, _both, _claude, _listed

GOING = {**CLAUDE, "claude-haiku-4-5": _listed(1.0, 5.0, retires_on="2026-10-15")}
# A newer small model at Haiku's price, besides Sonnet and Opus.
WITH_HAIKU_5 = {**GOING, "claude-haiku-5": _listed(1.0, 5.0)}
LISTED = ("claude-haiku-4-5", "claude-haiku-5", "claude-sonnet-5", "claude-opus-5")


def _app(settings, day=20, hour=5, **extra):
    judging = settings.model_copy(update={"model_watch": True, "judgements": True, **extra})
    return App(judging, FixedClock(datetime(2026, 9, day, hour, 17), TZ))


def _check(settings, day=20, hour=5, table=None, **extra):
    """The daily check of models, with Haiku 4.5 (the lookups' model) going on 15 October."""
    app = _app(settings, day, hour, **extra)
    model_watch.check(app, lists=_both(anthropic=table or WITH_HAIKU_5), listers=_claude(*LISTED))
    return app


def _answer(picks):
    return fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "give_judgement", {"picks": picks})], stop_reason="tool_use"
        )
    )


def _pick(question, choice, reason="the same work at the same price"):
    return {"question": f"q{question.id}", "choice": choice, "reason": reason}


def test_nothing_is_filed_or_asked_while_judgements_are_off(settings, conn) -> None:
    app = _check(settings, judgements=False)
    assert store.open_questions(conn) == []
    assert judgement.run_judgements(app, api=fakes.FakeMessagesAPI()) == {
        "asked": 0,
        "answered": 0,
    }


def test_a_going_model_s_place_is_weighed_with_the_evening_lookups_and_put_in_at_its_cost(
    settings, conn
) -> None:
    _check(settings)
    (question,) = store.open_questions(conn)
    assert question.kind == "replacement" and question.subject == "anthropic:claude-haiku-4-5"
    options = [option["model"] for option in question.facts["options"]]
    assert options[:2] == ["claude-haiku-5", "claude-sonnet-5"]  # nearest in price first
    assert "looking ideas up" in question.facts["used_for"]

    # Filed at 05:17: it waits for the evening, and a run before then asks nothing.
    none_yet = fakes.FakeMessagesAPI()
    assert judgement.run_judgements(_app(settings, hour=12), api=none_yet)["asked"] == 0
    assert none_yet.requests == []

    evening = _app(settings, hour=21)
    api = _answer([_pick(question, "claude-haiku-5")])
    assert judgement.run_judgements(evening, api=api) == {"asked": 1, "answered": 1}
    sent = api.requests[0]
    assert sent["model"] == "claude-opus-5"  # the best level, as judgement_level says
    assert [tool["name"] for tool in sent["tools"]] == ["give_judgement"]  # and no web
    assert "we should" not in str(sent["messages"])  # facts about models, not the family's words

    # The same price as the one it replaces: put in by itself, and said, with the way back.
    evening.refresh()
    assert evening.settings.worker_model == "claude-haiku-5"
    (answered,) = store.recent(conn, since="2000")
    assert answered.outcome.startswith("claude-haiku-5 put in place of claude-haiku-4-5")
    assert answered.answer["undo"] == {"worker_model": ""}
    assert ("advice", "replacement:anthropic:claude-haiku-4-5") in _found(conn)
    assert calls.recent_llm_calls(conn)[0]["kind"] == "judge"


def test_a_dearer_choice_waits_for_an_admin_with_a_button(settings, conn, family) -> None:
    from familydb.web import create_app

    _check(settings)
    (question,) = store.open_questions(conn)
    evening = _app(settings, hour=21)
    judgement.run_judgements(evening, api=_answer([_pick(question, "claude-sonnet-5")]))
    evening.refresh()
    assert evening.settings.worker_model == "claude-haiku-4-5"  # twice the price: not by itself
    page = create_app(evening).test_client().get("/status").text
    form = re.search(r'<form[^>]*class="inline-action">(?:(?!</form>).)*Put these in', page, re.S)
    assert form is not None
    assert 'name="worker_model" value="claude-sonnet-5"' in form.group(0)


def test_only_suggest_changes_nothing_by_itself(settings, conn) -> None:
    _check(settings, judgement_acts="suggest")
    (question,) = store.open_questions(conn)
    evening = _app(settings, hour=21, judgement_acts="suggest")
    judgement.run_judgements(evening, api=_answer([_pick(question, "claude-haiku-5")]))
    evening.refresh()
    assert evening.settings.worker_model == "claude-haiku-4-5"
    assert store.recent(conn, since="2000")[0].answer["waiting"] == {
        "worker_model": "claude-haiku-5"
    }


def test_the_day_s_questions_go_in_one_call(settings, conn) -> None:
    """New models and a going one on the same day: one call answers both."""
    _check(settings, day=19, table=GOING)  # a first check: nothing is new yet
    _check(settings, day=20)  # Haiku 5 is new, and Haiku 4.5 is going
    questions = store.open_questions(conn)
    # Filed on the 19th, the question of Haiku 4.5's place now has Haiku 5 among its options.
    assert sorted(q.kind for q in questions) == ["lineup", "replacement"]
    lineup = next(q for q in questions if q.kind == "lineup")
    going = next(q for q in questions if q.kind == "replacement")
    assert lineup.facts["now"] == {
        "everyday": "claude-opus-5",  # the chat's own model is Opus in these settings
        "better": "claude-opus-5",
        "best": "claude-opus-5",
    }
    api = _answer(
        [
            _pick(going, "claude-haiku-5"),
            *(
                {"question": f"q{lineup.id}.{level}", "choice": "claude-opus-5", "reason": "fine"}
                for level in ("everyday", "better", "best")
            ),
        ]
    )
    counts = judgement.run_judgements(_app(settings, hour=22), api=api)
    assert counts["answered"] == 2
    assert len(api.requests) == 1
    outcomes = {q.kind: q.outcome for q in store.recent(conn, since="2000")}
    assert outcomes["lineup"] == "the models at each level stay as they are"


def test_an_answer_that_is_not_an_option_goes_back_to_be_put_right(settings, conn) -> None:
    _check(settings)
    (question,) = store.open_questions(conn)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "give_judgement", {"picks": [_pick(question, "gpt-7")]})],
            stop_reason="tool_use",
        ),
        fakes.message(
            [
                fakes.tool_use(
                    "tu_2", "give_judgement", {"picks": [_pick(question, "claude-haiku-5")]}
                )
            ],
            stop_reason="tool_use",
        ),
    )
    assert judgement.run_judgements(_app(settings, hour=21), api=api)["answered"] == 1
    assert "is not an option" in str(api.requests[1]["messages"][-1])


def test_the_month_s_budget_is_kept(settings, conn) -> None:
    _check(settings)
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
            cost_usd=0.99,
            kind="judge",
        )
    api = fakes.FakeMessagesAPI()
    assert judgement.run_judgements(_app(settings, hour=21), api=api)["asked"] == 0
    assert api.requests == []
    # A new month, and there is room again.
    october = _app(settings, hour=21).settings
    assert judgement.spent_this_month(
        conn, october, datetime(2026, 10, 1, 9, tzinfo=TZ)
    ) == pytest.approx(0)


def test_no_answer_is_asked_again_the_next_evening_and_then_let_go(settings, conn) -> None:
    _check(settings)
    silent = fakes.FakeMessagesAPI(fakes.message([fakes.text("I think Haiku 5.")]))
    judgement.run_judgements(_app(settings, hour=21), api=silent)
    (question,) = store.open_questions(conn)
    assert question.tries == 1
    later = fakes.FakeMessagesAPI()
    assert judgement.run_judgements(_app(settings, hour=23), api=later)["asked"] == 0
    silent.queue.append(fakes.message([fakes.text("Still Haiku 5.")]))
    judgement.run_judgements(_app(settings, day=21, hour=21), api=silent)
    assert store.open_questions(conn) == []
    assert "no answer came back" in store.recent(conn, since="2000")[0].outcome


def test_a_refusal_nobody_can_read_is_asked_at_once(settings, registry, ctx) -> None:
    def refusing():
        said = anthropic.BadRequestError(
            "anthropic-version: this version no longer takes that header",
            response=fakes._response(400),
            body=None,
        )
        from familydb.agent.providers import build

        return build("anthropic", settings, api=fakes.FakeMessagesAPI(said))

    for _ in range(2):
        with pytest.raises(AgentError):
            _turn(settings, registry, ctx, refusing(), None)
    (question,) = store.open_questions(ctx.conn)
    assert question.kind == "refused" and question.urgent
    assert "the refusal fallback" in question.facts["parts"]

    morning = _app(settings, hour=9)  # no waiting for the evening
    api = _answer([_pick(question, "part:the refusal fallback", "the error names a header")])
    assert judgement.run_judgements(morning, api=api)["answered"] == 1
    assert "the refusal fallback" in parts.left_out("anthropic", "claude-opus-5")

    # Another process learns it too, from the store.
    parts.forget()
    model_watch.load(ctx.conn)
    assert "the refusal fallback" in parts.left_out("anthropic", "claude-opus-5")


def test_a_disputed_price_is_read_from_the_company_s_page_and_taken_only_if_it_matches(
    settings, conn
) -> None:
    from tests.test_model_watch import Lists

    listers = _claude("claude-haiku-4-5", "claude-opus-5")
    first = _app(settings, day=20)
    model_watch.check(first, lists=_both(), listers=listers)
    odd = Lists(
        litellm={"anthropic": {**CLAUDE, "claude-opus-5": _listed(5.0, 26.0)}},
        openrouter={"anthropic": {**CLAUDE, "claude-opus-5": _listed(5.0, 40.0)}},
    )
    model_watch.check(_app(settings, day=21), lists=odd, listers=listers)
    (question,) = store.open_questions(conn)
    assert question.kind == "price"

    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_1",
                    "report_price",
                    {
                        "model": "claude-opus-5",
                        "found": True,
                        "input": 5.0,
                        "output": 26.0,
                        "source_url": "https://claude.com/pricing",
                    },
                )
            ],
            stop_reason="tool_use",
        )
    )
    assert judgement.run_judgements(_app(settings, day=21, hour=21), api=api)["answered"] == 1
    assert any(t.get("type", "").startswith("web_search") for t in api.requests[0]["tools"])
    assert prices.price("anthropic", "claude-opus-5").output == 26.0
    assert ("prices", "anthropic:claude-opus-5") not in _found(conn)
    assert "from https://claude.com/pricing" in store.recent(conn, since="2000")[0].outcome
