"""The behaviour checks in evals/ grade what they claim to: a right answer passes, a wrong one fails
with a reason. Run offline here with a scripted model; the real runs are `python -m evals`."""

import functools
import json

import pytest
from evals import __main__ as evals_cli
from evals.cases import by_name
from evals.harness import GROUP, Case, emoji_in, grade, run_case, under_persona

from familydb import personas
from familydb.config import apply_overrides
from familydb.store import messages
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


def test_an_outdoor_idea_after_dark_is_offered_as_one(settings) -> None:
    case = by_name("outdoors_after_dark")
    frame = {"window": "today", "from_time": "17:00", "question": "tonight?", "discover": False}

    def replying(words: str):
        return run_case(
            case,
            settings,
            api=_answer([fakes.tool_use("t1", "suggest", frame)], [fakes.text(words)]),
        )

    careless = replying("After soccer you're free till 22:00: the falls hike fits.")
    assert grade(case, careless) == [
        "offers hike without saying dark or daylight or sunset or dusk"
    ]
    careful = replying("The falls hike needs daylight, and it's dark by 19:04 after soccer.")
    assert grade(case, careful) == []
    assert grade(case, replying("Nothing outdoors fits after soccer tonight.")) == []


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


def test_input_tokens_are_counted_cached_or_not(settings) -> None:
    """New, written to the cache and read from it, each once; a column the vendor left empty
    counts nothing."""
    case = by_name("capture_restaurant")
    cached = {"input_tokens": 40, "cache_creation_input_tokens": 300, "cache_read_input_tokens": 5}
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("t1", "add_idea", {"title": "Ethiopian place", "kind": "restaurant"})],
            usage=cached,
        ),
        fakes.message([fakes.text("Saved #6.")]),  # input_tokens only, the fake's 100
    )
    assert run_case(case, settings, api=api).input_tokens == 40 + 300 + 5 + 100


def _said(request) -> str:
    """Everything a request put before the model: its system blocks, then the conversation."""
    system = " ".join(block["text"] for block in request.get("system") or [])
    return system + " " + json.dumps(request["messages"], ensure_ascii=False)


# -- personas ----------------------------------------------------------------------------------


def test_two_personas_are_compared_side_by_side(settings, monkeypatch, tmp_path, capsys) -> None:
    """Each case runs under each persona, and the summary gives each its own line."""
    api = _answer([fakes.text("Any time.")], [fakes.text("Any time.")])
    monkeypatch.setattr(evals_cli, "Settings", lambda: settings)
    monkeypatch.setattr(evals_cli, "run_case", functools.partial(run_case, api=api))
    out = tmp_path / "results.json"
    argv = ["--case", "thanks", "--persona", "default", "--persona", "none", "--json", str(out)]

    assert evals_cli.main(argv) == 0

    printed = capsys.readouterr().out
    assert printed.splitlines()[0].endswith("personas default, none")
    assert "default  1/1 runs passed, 100 input tokens" in printed
    assert "none     1/1 runs passed, 100 input tokens" in printed
    results = json.loads(out.read_text())
    assert [(r["case"], r["persona"], r["input_tokens"]) for r in results["results"]] == [
        ("thanks", "default", 100),
        ("thanks", "none", 100),
    ]
    assert [p["persona"] for p in results["personas"]] == ["default", "none"]
    assert results["input_tokens"] == 200
    # And each ran as itself: her character under default, none of it under none.
    hers = personas.load("default").prompt.splitlines()[0]
    assert hers in _said(api.requests[0])
    assert hers not in _said(api.requests[1])


def test_the_personas_share_one_budget(settings, monkeypatch, capsys) -> None:
    """What the first spends is gone for the second: here all of it, so the second never asks."""
    api = _answer([fakes.text("Any time.")], [fakes.text("Any time.")])
    monkeypatch.setattr(evals_cli, "Settings", lambda: settings)
    monkeypatch.setattr(evals_cli, "run_case", functools.partial(run_case, api=api))
    argv = ["--case", "thanks", "--persona", "default", "--persona", "none", "--budget", "1e-9"]

    assert evals_cli.main(argv) == 1

    assert len(api.requests) == 1
    printed = capsys.readouterr().out
    assert "Stopped in thanks (default)" in printed
    assert "0/0 runs passed, 100 input tokens" in printed


def test_a_file_persona_is_used_as_the_rewrite(settings, tmp_path) -> None:
    rewrite = tmp_path / "rhyming.md"
    rewrite.write_text("You are {name}, and you answer every question in rhyme.")

    label, chosen = under_persona(settings, str(rewrite))

    assert (label, chosen.persona) == (str(rewrite), personas.DEFAULT)
    api = _answer([fakes.text("Any time.")])
    run_case(by_name("thanks"), chosen, api=api)
    said = _said(api.requests[0])
    assert "You are Vera, and you answer every question in rhyme." in said
    assert personas.load("default").prompt.splitlines()[0] not in said


def test_a_persona_by_key_is_her_as_she_ships(settings, tmp_path) -> None:
    """The family's words already in the settings are not laid over the persona a run names."""
    rewritten = apply_overrides(
        settings,
        {
            "persona_text": {"default": {"text": "You are {name}, and brief."}},
            "persona_notes": "Rhyme everything.",
            "persona_name": "Juno",
        },
    )

    label, chosen = under_persona(rewritten, "Vera")  # her older key, as a setting may hold it

    assert (label, chosen.persona, chosen.persona_text) == ("default", "default", {})
    assert personas.active(chosen) == personas.load(personas.DEFAULT)
    with pytest.raises(ValueError, match="not a persona"):
        under_persona(settings, str(tmp_path / "missing.md"))
    empty = tmp_path / "empty.md"
    empty.write_text("\n")
    with pytest.raises(ValueError, match="empty"):
        under_persona(settings, str(empty))


# -- who is listening --------------------------------------------------------------------------


def test_a_cases_sender_and_chat_reach_the_pipeline(settings, monkeypatch) -> None:
    """The girls, writing in the family group, are who the model hears from, and the message is
    stored as the group's. A case that names neither is Sam in his own chat."""
    stored: list[str] = []
    insert_in = messages.insert_in

    def keep(conn, **fields):
        stored.append(fields["chat_id"])
        return insert_in(conn, **fields)

    monkeypatch.setattr(messages, "insert_in", keep)
    api = _answer([fakes.text("Swim lessons till 11, then Hopscotch?")], [fakes.text("Any time.")])

    run_case(by_name("kid_in_the_group"), settings, api=api)
    run_case(by_name("thanks"), settings, api=api)

    assert stored == [GROUP, "1001"]
    assert "[the girls] can we do something fun tomorrow?" in _said(api.requests[0])
    assert "[Sam] thanks!" in _said(api.requests[1])


MISSED_TOMORROW = "suggest was called, but not for a window taking in tomorrow"


@pytest.mark.parametrize(
    ("frame", "wrong"),
    [
        ({"window": "this_weekend"}, []),
        ({"window": "dates", "start": "2026-09-26", "end": "2026-09-27"}, []),
        ({"window": "today"}, [MISSED_TOMORROW]),
        ({"window": "next_weekend"}, [MISSED_TOMORROW]),
    ],
)
def test_tomorrow_is_asked_about_however_it_is_framed(settings, frame, wrong) -> None:
    case = by_name("kid_in_the_group")
    api = _answer(
        [fakes.tool_use("t1", "suggest", {"question": "fun tomorrow?", **frame})],
        [fakes.text("Swim lessons till 11, then Hopscotch in Portland?")],
    )
    problems = grade(case, run_case(case, settings, api=api))
    assert [problem.split(":")[0] for problem in problems] == wrong


# -- who she is --------------------------------------------------------------------------------


def test_a_cases_settings_are_laid_over_the_run(settings) -> None:
    case = Case("about_us", ("hi",), (), "why", settings={"about_family": "Mia is seven."})
    api = _answer([fakes.text("Hi.")])
    run_case(case, settings, api=api)
    assert "Mia is seven." in _said(api.requests[0])


@pytest.mark.parametrize(
    ("persona", "reply", "wrong"),
    [
        ("default", "I'm Juno.", []),
        ("default", "I'm Vera.", ["reply does not mention Juno"]),
        ("none", "I'm FamilyDB.", []),
        ("none", "I'm Juno.", ["reply does not mention FamilyDB"]),
    ],
)
def test_her_name_is_the_one_she_was_given_and_none_keeps_its_own(
    settings, persona, reply, wrong
) -> None:
    """The case's name for her is laid over whichever persona the run is under, and under none
    the bot is still FamilyDB."""
    case = by_name("her_name_after_a_rename")
    _, chosen = under_persona(settings, persona)
    assert grade(case, run_case(case, chosen, api=_answer([fakes.text(reply)]))) == wrong


# -- style, whoever she is ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("Saved #6 as a restaurant idea.", 0),
        ("21°C and dry, © ™ → ↗", 0),  # symbols, but not from the blocks emoji are drawn from
        ("Done 👍", 1),
        ("🎉🎉", 2),
        ("☀ then ⛅, ⏰ at 9 ✅", 4),  # the blocks below U+1F000 count too
        ("👨\u200d👩\u200d👧\u200d👦", 1),  # a family, joined
        ("👍\U0001f3fd ❤\ufe0f", 2),  # a skin tone and U+FE0F add nothing
        ("🇺🇸 🇬🇧", 2),  # two indicators to a flag
        ("🇺🇸🇬🇧", 2),
    ],
)
def test_emoji_are_counted_once_however_they_are_built(text, count) -> None:
    assert emoji_in(text) == count


@pytest.mark.parametrize(
    ("reply", "problem"),
    [
        ("Any time 🙂🎉", "reply has 2 emoji, over 1"),
        ("As an AI, I don't mind at all.", "says 'As an AI', which is filler"),
        ("as an artificial intelligence I'm glad", "which is filler"),
        ("Happy to help, AS A LANGUAGE MODEL.", "which is filler"),
        ("Any time! Really! Truly!", "reply has 3 exclamation marks, over 2"),
    ],
)
def test_each_style_check_fires_on_a_reply_that_breaks_it(settings, reply, problem) -> None:
    case = by_name("thanks")
    problems = grade(case, run_case(case, settings, api=_answer([fakes.text(reply)])))
    assert any(problem in p for p in problems), problems


def test_a_reply_at_the_limits_of_style_passes(settings) -> None:
    """One emoji, two exclamation marks, and "as an aside", which is not "as an AI"."""
    case = by_name("thanks")
    reply = "Any time! As an aside, swim lessons are at 9 tomorrow! 🙂"
    assert grade(case, run_case(case, settings, api=_answer([fakes.text(reply)]))) == []


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


def test_a_repeat_is_graded_on_how_often_and_from_when(settings) -> None:
    case = by_name("bins_every_sunday")
    weekly = {
        "title": "Bins out",
        "remind_at": "2026-09-27T19:00",
        "repeat_every": 1,
        "repeat_unit": "week",
    }
    api = _answer([fakes.tool_use("t1", "add_task", weekly)], [fakes.text("Every Sunday, 7pm.")])
    assert grade(case, run_case(case, settings, api=api)) == []
    once = {"title": "Bins out", "remind_at": "2026-09-27T19:00"}
    api = _answer([fakes.tool_use("t1", "add_task", once)], [fakes.text("Sunday, 7pm.")])
    assert "add_task was called, but not every week" in " ".join(
        grade(case, run_case(case, settings, api=api))
    )


def test_a_window_nothing_will_bring_up_is_graded_on_what_was_promised(settings) -> None:
    case = by_name("gutters_before_christmas")
    gutters = {"title": "Clean out the gutters", "preferred_window": "before Christmas"}
    kept = [fakes.tool_use("t1", "add_task", gutters)]
    api = _answer(kept, [fakes.text("Saved as task #1, for before Christmas.")])
    assert grade(case, run_case(case, settings, api=api)) == []
    api = _answer(kept, [fakes.text("Saved. I\u2019ll nudge you when you have a free day.")])
    assert "promised: i'll nudge" in " ".join(grade(case, run_case(case, settings, api=api)))


def test_a_birthday_is_graded_on_whose_it_is_and_a_gift_on_its_kind(settings) -> None:
    case = by_name("grandmas_birthday")
    yearly = {
        "title": "Grandma's birthday, 12 Oct",
        "remind_at": "2026-09-28T09:00",
        "repeat_every": 1,
        "repeat_unit": "year",
        "gift_for": "Grandma",
    }
    api = _answer([fakes.tool_use("t1", "add_task", yearly)], [fakes.text("Mon 28 Sep, 9am.")])
    assert grade(case, run_case(case, settings, api=api)) == []
    nobodys = {key: value for key, value in yearly.items() if key != "gift_for"}
    api = _answer([fakes.tool_use("t1", "add_task", nobodys)], [fakes.text("Mon 28 Sep, 9am.")])
    assert "not yearly, for Grandma's gifts" in " ".join(
        grade(case, run_case(case, settings, api=api))
    )
    case = by_name("a_gift_for_grandma")
    apron = {"title": "Gardening apron", "kind": "gift", "participants": ["Grandma"]}
    api = _answer([fakes.tool_use("t1", "add_idea", apron)], [fakes.text("Saved as a gift.")])
    assert grade(case, run_case(case, settings, api=api)) == []
    outing = {**apron, "kind": "home"}
    api = _answer([fakes.tool_use("t1", "add_idea", outing)], [fakes.text("Saved.")])
    assert "not a gift, for Grandma" in " ".join(grade(case, run_case(case, settings, api=api)))
