"""The behaviour checks in evals/ grade what they claim to: a right answer passes, a wrong one fails
with a reason. Run offline here with a scripted model; the real runs are `python -m evals`."""

from evals.cases import by_name
from evals.harness import grade, run_case

from tests import fakes


def _answer(*blocks_per_call):
    return fakes.FakeMessagesAPI(*(fakes.message(list(blocks)) for blocks in blocks_per_call))


def test_a_right_answer_passes(settings) -> None:
    case = by_name("capture_restaurant")
    api = _answer(
        [
            fakes.tool_use(
                "t1",
                "add_idea",
                {"title": "Ethiopian place on Mississippi Ave", "kind": "restaurant"},
            )
        ],
        [fakes.text("Saved #6 Ethiopian place on Mississippi Ave as a restaurant idea.")],
    )
    run = run_case(case, settings, api=api)
    assert grade(case, run) == []
    assert run.counts["ideas"] == 6 and run.model_calls == 2


def test_a_wrong_answer_fails_and_says_why(settings) -> None:
    case = by_name("arrange_not_book")
    api = _answer(
        [fakes.tool_use("t1", "create_event", {"title": "Dentist", "start": "2026-10-01T09:00"})],
        [fakes.text("Booked the dentist for #9.")],
    )
    problems = grade(case, run_case(case, settings, api=api))
    assert "never called add_task" in problems
    assert "wrote with create_event" in problems
    assert "names #9, which does not exist" in problems


def test_either_accepts_a_question_instead(settings) -> None:
    case = by_name("reminder_tuesday")
    api = _answer([fakes.text("What time on Tuesday the 29th should I remind you?")])
    assert grade(case, run_case(case, settings, api=api)) == []


def test_every_case_has_a_reason_and_a_unique_name() -> None:
    from evals.cases import CASES

    assert len({c.name for c in CASES}) == len(CASES)
    assert all(c.why and c.says and c.checks for c in CASES)
