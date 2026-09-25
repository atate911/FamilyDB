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


def test_a_case_in_the_group_is_sent_there_and_asking_first_passes(settings) -> None:
    case = by_name("sensitive_reminder_in_the_group")
    api = _answer([fakes.text("Everyone here reads this, the girls too. Set it here anyway?")])
    assert grade(case, run_case(case, settings, api=api)) == []
    turn = [part["text"] for part in api.requests[0]["messages"][-1]["content"]]
    assert "everyone in it reads your reply, kids among them." in turn[1]
    # The same words in Sam's own chat are set at once, and a question there fails.
    private = by_name("sensitive_reminder_in_private")
    api = _answer([fakes.text("Shall I set it for 8am tomorrow?")])
    assert "never called add_task" in grade(private, run_case(private, settings, api=api))
    assert len(api.requests[0]["messages"][-1]["content"]) == 2  # the date, then the message


def test_every_case_has_a_reason_and_a_unique_name() -> None:
    from evals.cases import CASES

    assert len({c.name for c in CASES}) == len(CASES)
    assert all(c.why and c.says and c.checks for c in CASES)


def test_the_budget_stops_a_case_between_its_calls(settings) -> None:
    """What is left of the budget is the run's own limit, so a case cannot run on past it."""
    case = by_name("capture_restaurant")
    api = _answer(
        [fakes.tool_use("t1", "add_idea", {"title": "Ethiopian place", "kind": "restaurant"})],
        [fakes.text("Saved #6.")],
    )
    run = run_case(case, settings, api=api, limit=1e-9)
    assert run.model_calls == 1  # the first call crossed it; the second was never sent
    assert run.counts["ideas"] == 6  # and what it did before stopping is kept
