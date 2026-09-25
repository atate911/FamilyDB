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


def test_a_swap_is_graded_on_its_order_and_on_what_it_leaves(settings) -> None:
    case = by_name("ramble_swap")
    hike = {"title": "Falls hike", "start": "2026-10-03T13:00", "idea_id": 4}
    swap = {"title": "Hopscotch", "start": "2026-10-03T13:00", "idea_id": 3}
    right = _answer(
        [fakes.tool_use("t1", "create_event", hike)],
        [fakes.text("On the calendar: the falls hike, Sat 3 Oct at 1pm.")],
        [
            fakes.tool_use("t2", "create_event", swap),
            fakes.tool_use("t3", "update_event", {"plan_id": 1, "status": "cancelled"}),
        ],
        [fakes.text("Swapped: Hopscotch Sat 3 Oct at 1pm; the hike is back on the list (#4).")],
    )
    assert grade(case, run_case(case, settings, api=right)) == []

    backwards = _answer(
        [fakes.tool_use("t1", "create_event", hike)],
        [fakes.text("On the calendar.")],
        [fakes.tool_use("t3", "update_event", {"plan_id": 1, "status": "cancelled"})],
        [fakes.tool_use("t2", "create_event", swap)],
        [fakes.text("Swapped.")],
    )
    assert "update_event ran before create_event" in grade(
        case, run_case(case, settings, api=backwards)
    )


def test_an_event_put_on_by_hand_is_taken_off_by_its_id(settings) -> None:
    case = by_name("ramble_cancel_by_hand")
    api = _answer(
        [fakes.tool_use("t1", "get_calendar", {"start": "2026-09-26", "end": "2026-09-26"})],
        [fakes.tool_use("t2", "delete_event", {"event_id": "evt2"})],
        [fakes.text("Took swim lessons on Saturday off the calendar.")],
    )
    run = run_case(case, settings, api=api)
    assert grade(case, run) == []
    assert [c.name for c in run.calls] == ["get_calendar", "delete_event"]


def test_remembering_alone_is_graded_on_what_it_cost(settings) -> None:
    case = by_name("remember_alone")
    change = {"action": "add", "about": "the girls", "category": "food", "fact": "vegetarian"}
    once = _answer(
        [fakes.tool_use("t1", "remember", {"changes": [change], "reply": "Noted: vegetarian."})]
    )
    run = run_case(case, settings, api=once)
    assert grade(case, run) == [] and run.reply == "Noted: vegetarian."
    twice = _answer(
        [fakes.tool_use("t1", "remember", {"changes": [change]})],
        [fakes.text("Noted: vegetarian.")],
    )
    assert "2 model calls, over 1" in grade(case, run_case(case, settings, api=twice))
