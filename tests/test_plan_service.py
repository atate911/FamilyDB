"""What follows a plan stays in step with it (plan_service.py): a plan made on the page is checked
the evening before and asked about after, like one made in a chat, and a plan that moves, through
the tools or in Google, is checked and asked about again for its new day. A reminder set before a
plan moves with it, goes when it is cancelled, says when the plan is, and is done once it is over.
"""

from datetime import datetime, timedelta

import pytest

from familydb import plan_service
from familydb.errors import ToolError
from familydb.jobs.reminders import run_reminders
from familydb.store import db, ideas, places, plans, tasks
from tests.conftest import NOW_ISO, TZ, call


def test_a_plan_made_on_the_page_has_a_chat_to_be_checked_in(env):
    """A form has no message behind it: the plan gets the family's chat, so the evening-before
    check and the day-after question (which need a chat) reach it. It used to get none."""
    _, made = call(env, "create_event", title="Zoo", start="2026-09-26T10:00")
    assert (made["plan"]["channel"], made["plan"]["chat_id"]) == ("web", "web")
    env.ctx.settings = env.settings.model_copy(update={"family_chat_id": "-100"})
    _, made = call(env, "create_event", title="Museum", start="2026-09-27T10:00")
    assert (made["plan"]["channel"], made["plan"]["chat_id"]) == ("telegram", "-100")


def _checked_and_asked(env, plan_id: int) -> None:
    with db.transaction(env.conn):
        plans.mark_checked(env.conn, plan_id, now=NOW_ISO)
        plans.mark_followed_up(env.conn, plan_id, now=NOW_ISO)


def test_a_plan_moved_by_the_tools_is_checked_again_for_its_new_day(env):
    _, made = call(env, "create_event", title="Zoo", start="2026-09-26T10:00")
    plan_id = made["plan"]["id"]
    _checked_and_asked(env, plan_id)
    call(env, "update_event", plan_id=plan_id, title="The zoo")
    kept = plans.get(env.conn, plan_id)
    assert kept.checked_at is not None and kept.followed_up_at is not None  # not moved
    call(env, "update_event", plan_id=plan_id, start="2026-09-27T10:00")
    moved = plans.get(env.conn, plan_id)
    assert moved.checked_at is None and moved.followed_up_at is None


def test_a_plan_moved_in_google_is_checked_again_for_its_new_day(env):
    _, made = call(env, "create_event", title="Zoo", start="2026-09-26T10:00")
    plan_id = made["plan"]["id"]
    call(env, "search_plans", query="")  # the whole calendar, once
    with db.transaction(env.conn):
        plans.mark_checked(env.conn, plan_id, now=NOW_ISO)
    env.cal.patch_event(
        plans.get(env.conn, plan_id).google_event_id,
        start=datetime(2026, 9, 27, 10, tzinfo=TZ),
        end=datetime(2026, 9, 27, 12, tzinfo=TZ),
    )
    call(env, "search_plans", query="")
    moved = plans.get(env.conn, plan_id)
    assert moved.start.startswith("2026-09-27") and moved.checked_at is None


# -- reminders set before a plan (the clock: Thursday 24 September 2026, 18:00)


def _local(value: str) -> str:
    return datetime.fromisoformat(value).astimezone(TZ).strftime("%Y-%m-%dT%H:%M")


def _reminders(env, plan_id: int) -> dict[str, str]:
    """The live reminders tied to a plan: which, and when, on the family's clock."""
    return {
        task.plan_remind: _local(task.reminder.remind_at)
        for task in tasks.linked_to(env.conn, plan_id)
        if task.reminder is not None and task.reminder.cancelled_at is None
    }


def _beck(env, **more) -> dict:
    _, made = call(
        env,
        "create_event",
        title="Beck",
        start="2026-11-18T20:00",
        remind_before=["1 week"],
        **more,
    )
    return made


def test_a_reminder_before_a_plan_is_tied_to_it(env):
    made = _beck(env, idea_id=None)
    assert made["reminders"] == [{"task": 1, "before": "1 week", "at": "2026-11-11T09:00"}]
    task = tasks.get(env.conn, 1)
    assert (task.title, task.plan_id, task.owner_id) == ("Beck", made["plan"]["id"], env.member.id)
    again = _beck(env)  # the same request again: nothing more is made
    assert again["reminders"] == made["reminders"] and len(tasks.list_all(env.conn)) == 1


def test_a_reminder_moves_with_its_plan(env):
    plan_id = _beck(env)["plan"]["id"]
    call(env, "update_event", plan_id=plan_id, remind_before=["1 week", "2 hours"])
    call(env, "update_event", plan_id=plan_id, start="2026-11-19T20:00")
    assert _reminders(env, plan_id) == {"1 week": "2026-11-12T09:00", "2 hours": "2026-11-19T18:00"}


def test_a_reminder_moves_with_its_plan_in_google(env):
    plan_id = _beck(env)["plan"]["id"]
    call(env, "search_plans", query="")  # the whole calendar, once
    env.cal.patch_event(
        plans.get(env.conn, plan_id).google_event_id,
        start=datetime(2026, 11, 25, 20, tzinfo=TZ),
        end=datetime(2026, 11, 25, 22, tzinfo=TZ),
    )
    call(env, "search_plans", query="")
    assert _reminders(env, plan_id) == {"1 week": "2026-11-18T09:00"}


def test_a_plan_moved_too_soon_for_its_reminder_ends_it(env):
    """A week before is past once the plan moves to the day after tomorrow: nothing is sent late
    for it, and nothing is left on the old day."""
    plan_id = _beck(env)["plan"]["id"]
    call(env, "update_event", plan_id=plan_id, start="2026-09-26T20:00")
    (task,) = tasks.list_all(env.conn, status="cancelled")
    assert task.plan_id == plan_id and task.reminder is None


def test_a_cancelled_plan_takes_its_reminders_with_it(env):
    plan_id = _beck(env)["plan"]["id"]
    call(env, "update_event", plan_id=plan_id, status="cancelled")
    assert tasks.list_all(env.conn) == [] and len(tasks.list_all(env.conn, status="cancelled")) == 1


def test_naming_its_reminders_again_replaces_them(env):
    plan_id = _beck(env)["plan"]["id"]
    _, said = call(env, "update_event", plan_id=plan_id, remind_before=["1 day"])
    assert [r["before"] for r in said["reminders"]] == ["1 day"]
    assert _reminders(env, plan_id) == {"1 day": "2026-11-17T09:00"}
    call(env, "update_event", plan_id=plan_id, remind_before=["1 week", "1 day"])
    call(env, "update_event", plan_id=plan_id, remind_before=["1 day"])
    call(env, "update_event", plan_id=plan_id, remind_before=["1 week", "1 day"])  # and back
    assert set(_reminders(env, plan_id)) == {"1 week", "1 day"}
    call(env, "update_event", plan_id=plan_id, remind_before=[])
    assert _reminders(env, plan_id) == {}


def test_a_reminder_that_cannot_be_set_says_why(env):
    _, made = call(
        env,
        "create_event",
        title="Zoo",
        start="2026-09-26T10:00",
        remind_before=["1 week", "1 hour"],
    )
    assert made["reminders"] == [{"task": 1, "before": "1 hour", "at": "2026-09-26T09:00"}]
    assert made["reminders_not_set"] == ["1 week: that time has passed"]
    result, _ = call(
        env,
        "create_event",
        title="Fair",
        start="2026-10-10",
        remind_before=["1 week", "1 day", "morning of"],
    )
    assert result.is_error  # at most two


def test_an_event_put_on_by_hand_takes_no_reminder_of_the_bot_s(env):
    event = env.cal.seed(
        "Dentist", datetime(2026, 10, 1, 9, tzinfo=TZ), datetime(2026, 10, 1, 10, tzinfo=TZ)
    )
    result, said = call(env, "update_event", event_id=event.id, remind_before=["1 day"])
    assert result.is_error and "add_task" in said["error"]


def _plan(conn, start: str, *, all_day: bool = False, idea_id: int | None = None) -> plans.Plan:
    with db.transaction(conn):
        return plans.insert(
            conn, title="Hike", start=start, end=None, all_day=all_day, idea_id=idea_id
        )


def test_when_a_reminder_before_a_plan_goes(conn):
    evening = _plan(conn, "2026-10-10T19:00:00-07:00")
    early = _plan(conn, "2026-10-10T07:00:00-07:00")
    day = _plan(conn, "2026-10-10", all_day=True)

    def at(plan: plans.Plan, word: str) -> str:
        return f"{plan_service.remind_at(conn, plan, word, TZ):%Y-%m-%dT%H:%M}"

    assert at(evening, "1 week") == "2026-10-03T09:00"
    assert at(day, "3 days") == "2026-10-07T09:00"
    assert at(evening, "morning of") == at(day, "morning of") == "2026-10-10T08:00"
    assert at(early, "morning of") == "2026-10-10T06:00"  # before eight: an hour before
    assert at(evening, "2 hours") == "2026-10-10T17:00"
    with pytest.raises(ToolError, match="all day"):
        at(day, "1 hour")
    with pytest.raises(ToolError, match="travel time"):
        at(evening, "time to leave")
    with db.transaction(conn):
        place = places.insert(conn, name="Silver Falls", travel_minutes=50)
        idea = ideas.insert(conn, title="Silver Falls", kind="outing", place_id=place.id)
    hike = _plan(conn, "2026-10-10T10:00:00-07:00", idea_id=idea.id)
    assert at(hike, "time to leave") == "2026-10-10T09:00"  # the drive, and ten to spare


def test_the_reminder_says_when_its_plan_is_and_is_done_once_it_is_over(env):
    said: list[str] = []
    env.app.senders["web"] = lambda chat, text: said.append(text)
    _, made = call(
        env, "create_event", title="Beck", start="2026-09-25T20:00", remind_before=["2 hours"]
    )
    env.app.clock.advance(timedelta(hours=24, minutes=1))  # Friday, 18:01
    assert run_reminders(env.app) == 1
    assert said[-1].startswith("Reminder: Beck") and said[-1].endswith("It's today at 20:00.")
    assert tasks.get(env.conn, 1).status == "open"  # until the plan is over
    env.app.clock.advance(timedelta(hours=6))  # Saturday, past midnight
    run_reminders(env.app)
    assert tasks.get(env.conn, 1).status == "done"


def test_the_plan_s_day_is_said_from_when_the_reminder_goes():
    plan = plans.Plan(
        id=1, title="Beck", start="2026-11-18T20:00:00-07:00", created_at="", updated_at=""
    )
    fair = plans.Plan(
        id=2, title="Fair", start="2026-11-19", all_day=True, created_at="", updated_at=""
    )
    words = plan_service.when_words
    assert words(plan, datetime(2026, 11, 11, 9, tzinfo=TZ), TZ) == "on Wed 18 Nov at 20:00"
    assert words(plan, datetime(2026, 11, 17, 9, tzinfo=TZ), TZ) == "tomorrow at 20:00"
    assert words(fair, datetime(2026, 11, 19, 8, tzinfo=TZ), TZ) == "today"
