"""What follows a plan stays in step with it (plan_service.py): a plan made on the page is checked
the evening before and asked about after, like one made in a chat, and a plan that moves, through
the tools or in Google, is checked and asked about again for its new day."""

from datetime import datetime

from familydb.store import db, plans
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
