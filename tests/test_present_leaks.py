"""A sweep for presents (docs/DESIGN.md section 16): as each kid, and as the grown-up a present is
for, no present, no plan made from one and no to-do about one shows anywhere they can look: a page,
a count, a search, the chat's tools, or a Telegram command."""

from __future__ import annotations

import html
import json
from contextlib import closing

import pytest

from familydb.store import db, ideas, members, plans, tasks
from familydb.tools import ToolContext, build_registry
from tests.conftest import NOW_ISO
from tests.test_web_logins import KIDS, _as, _start, _tokens, alex, app, sam  # noqa: F401

LEGO = "Lego Millennium set"  # for Theo, a kid: kept from every kid
WATCH = "Diver's watch"  # for Alex, a grown-up: kept from the kids and Alex
ORDER_WATCH = "Order the diver's watch"
WRAP_LEGO = "Wrap the Lego Millennium set"
SECRETS = (LEGO, WATCH, ORDER_WATCH, WRAP_LEGO, "Millennium", "diver")

PAGES = (
    "/",
    "/ideas",
    "/ideas?q=Lego",
    "/ideas?kind=gift",
    "/restaurants",
    "/plans",
    "/plans/month?month=2026-10",
    "/tasks",
    "/tasks?status=all",
    "/chat",
    "/more",
    "/wishes",
)


@pytest.fixture
def household(app, sam, alex, family):  # noqa: F811
    """Maya and Theo signed in as themselves; two presents, a plan made from one, and a to-do about
    each, one of them Alex's own to do."""
    with closing(app.connect()) as conn, db.transaction(conn):
        maya = members.add(conn, "Maya", "kid", now=NOW_ISO)
        theo = members.add(conn, "Theo", "kid", now=NOW_ISO)
        conn.execute(
            "UPDATE members SET channel = 'telegram', channel_user_id = '4242' WHERE id = ?",
            (maya.id,),
        )
        lego = ideas.insert(conn, title=LEGO, kind="gift", participants=["Theo"], now=NOW_ISO)
        watch = ideas.insert(conn, title=WATCH, kind="present", participants=["Alex"], now=NOW_ISO)
        plans.insert(
            conn,
            title=WRAP_LEGO,
            start="2026-10-03T10:00-07:00",
            end="2026-10-03T11:00-07:00",
            all_day=False,
            idea_id=lego.id,
            now=NOW_ISO,
        )
        for title, idea, owner in (
            (ORDER_WATCH, watch, family["sam"].id),
            ("Hide the Lego set", lego, family["alex"].id),
        ):
            tasks.insert(
                conn,
                title=title,
                notes="",
                owner_id=owner,
                due_at="2026-09-21T17:00:00Z",
                preferred_window="",
                operation_key=title,
                channel="telegram",
                chat_id="-100",
                now=NOW_ISO,
                idea_id=idea.id,
            )
    browsers = {"sam": sam, "alex": alex}
    for name, kid in (("maya", maya), ("theo", theo)):
        browser = _as(app, kid.display_name, _start(sam, kid.id))
        browser.post("/you", data={**_tokens(browser, "/you"), "new": KIDS, "again": KIDS})
        browsers[name] = browser
    return {
        "browsers": browsers,
        "members": {**family, "maya": maya, "theo": theo},
        "lego": lego,
        "watch": watch,
    }


def _leaks(text: str, secrets=SECRETS) -> list[str]:
    folded = html.unescape(text).casefold()  # an apostrophe on a page is &#39;
    return [secret for secret in secrets if secret.casefold() in folded]


@pytest.mark.parametrize("who", ["maya", "theo"])
def test_no_page_shows_a_kid_any_present(household, who) -> None:
    browser = household["browsers"][who]
    found = {path: _leaks(browser.get(path).text) for path in PAGES}
    assert {path: hit for path, hit in found.items() if hit} == {}
    for idea in (household["lego"], household["watch"]):
        assert browser.get(f"/idea/{idea.id}").status_code == 404


def test_no_page_shows_alex_his_own_present_or_the_to_do_about_it(household) -> None:
    browser = household["browsers"]["alex"]
    mine = (WATCH, ORDER_WATCH, "diver")
    found = {path: _leaks(browser.get(path).text, mine) for path in PAGES}
    assert {path: hit for path, hit in found.items() if hit} == {}
    assert browser.get(f"/idea/{household['watch'].id}").status_code == 404
    # The Lego set is not his: he sees it, and the to-do about it, which is his own to do.
    assert LEGO in browser.get("/ideas").text and "Hide the Lego set" in browser.get("/tasks").text


def test_sam_sees_both_and_is_told_whom_each_is_kept_from(household) -> None:
    page = household["browsers"]["sam"].get("/ideas").text
    assert LEGO in page and WATCH in html.unescape(page)
    assert "hidden from the kids and alex" in page.casefold()


def test_the_counts_do_not_give_a_present_away(household) -> None:
    """Alex has one to-do of his own that he may see (the Lego), and one he may not (the watch's,
    which is Sam's): the menu's late count and To do's open count leave the watch's out."""
    sams = household["browsers"]["sam"].get("/tasks").text
    alexs = household["browsers"]["alex"].get("/tasks").text
    assert "2 open" in sams and "1 open" in alexs


def _ctx(conn, settings, clock, member):
    return ToolContext(conn=conn, settings=settings, clock=clock, member=member)


@pytest.mark.parametrize("who", ["maya", "theo", "alex"])
def test_the_chats_tools_tell_nobody_of_a_present_kept_from_them(
    household,
    app,  # noqa: F811
    settings,
    clock,
    who,
) -> None:
    registry = build_registry()
    member = household["members"][who]
    secrets = (WATCH, ORDER_WATCH, "diver") if who == "alex" else SECRETS
    with closing(app.connect()) as conn:
        ctx = _ctx(conn, settings, clock, member)
        for name, args in (
            ("search_ideas", {}),
            ("search_ideas", {"kind": "gift"}),
            ("search_ideas", {"text": "watch"}),
            ("list_tasks", {"status": "all"}),
            ("search_plans", {}),
            ("suggest", {"window": "this_weekend", "question": "what shall we do"}),
        ):
            result = registry.dispatch(name, args, ctx)
            said = json.dumps(json.loads(result.content))
            assert _leaks(said, secrets) == [], (name, args)


@pytest.mark.parametrize("command", ["/today", "/week", "/tasks", "/now"])
def test_telegram_commands_tell_a_kid_of_no_present(household, app, command) -> None:  # noqa: F811
    """Maya asks in the family's Telegram group, where the present's to-dos were set."""
    from familydb import commands
    from familydb.channels.base import IncomingMessage

    message = IncomingMessage(
        channel="telegram",
        channel_update_id=f"u-{command}",
        chat_id="-100",
        channel_user_id="4242",
        text=command,
        sender_name="Maya",
    )
    out = commands.answer(app, message)
    said = out.text if out is not None else ""
    assert said and _leaks(said) == [], said


def test_the_calendar_tells_a_kid_of_no_plan_made_from_a_present(
    household,
    calendar_settings,
    clock,
    app,  # noqa: F811
) -> None:
    from zoneinfo import ZoneInfo

    from tests import fakes

    registry = build_registry()
    calendar = fakes.FakeCalendar(ZoneInfo("America/Vancouver"))
    with closing(app.connect()) as conn:
        sams = ToolContext(
            conn=conn,
            settings=calendar_settings,
            clock=clock,
            member=household["members"]["sam"],
            calendar=calendar,
        )
        made = registry.dispatch(
            "create_event",
            {
                "title": "Pick up the Millennium box",
                "start": "2026-09-26T10:00",
                "idea_id": household["lego"].id,
            },
            sams,
        )
        assert not made.is_error, made.content
        args = {"start": "2026-09-25", "end": "2026-09-28"}
        for who in ("maya", "theo"):
            ctx = ToolContext(
                conn=conn,
                settings=calendar_settings,
                clock=clock,
                member=household["members"][who],
                calendar=calendar,
            )
            seen = registry.dispatch("get_calendar", args, ctx).content
            assert _leaks(seen) == [], seen
        assert "Millennium" in registry.dispatch("get_calendar", args, sams).content


def test_a_present_s_reminder_in_the_family_group_does_not_name_it(
    household,
    app,  # noqa: F811
    settings,
) -> None:
    """The watch's to-do is Sam's, set in the family's Telegram group, where Alex and the kids
    read. Sam has no chat of his own with the bot, so the reminder stays in the group: it says
    there is one, and nothing of what."""
    from familydb import task_service

    with closing(app.connect()) as conn:
        task = next(t for t in tasks.list_all(conn, status="all") if t.title == ORDER_WATCH)
        said = task_service.reminder_for(
            conn, task, settings, channel="telegram", chat_id="-100", due_when=None
        )
        assert _leaks(said) == [] and "reminder is waiting on your To do" in said
        # In a chat only Sam reads (his own Telegram chat with the bot), it says what it is.
        with db.transaction(conn):
            conn.execute(
                "UPDATE members SET channel = 'telegram', channel_user_id = '777' WHERE id = ?",
                (household["members"]["sam"].id,),
            )
        private = task_service.reminder_for(
            conn, task, settings, channel="telegram", chat_id="777", due_when=None
        )
    assert ORDER_WATCH in private


def test_a_present_kept_from_a_kid_reads_like_any_page_that_is_not_there(household) -> None:
    """One refusal page: the present's address and one that never was say the same, and say who
    is signed in, with two ways on."""
    browser = household["browsers"]["maya"]
    browser.get("/")  # the flash left from choosing her password
    kept = browser.get(f"/idea/{household['lego'].id}")
    never = browser.get("/idea/9999")
    assert kept.status_code == never.status_code == 404
    assert kept.text == never.text
    assert "Signed in as Maya" in kept.text and "Go to Home" in kept.text
    refused = browser.get("/settings")
    assert refused.status_code == 403 and "Signed in as Maya" in refused.text
