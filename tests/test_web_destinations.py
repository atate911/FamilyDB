"""The destinations (docs/INTERFACE.md section 4; web/destinations.py, web/routes.py): each one a
question for a title, one line of what to know, chips to narrow, the answer, and the box scoped
to it. No model call for any of them."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from familydb.app import App
from familydb.store import db, ideas, outcomes, plans, tasks
from familydb.store import picks as pick_store
from familydb.web import create_app, views
from tests import fakes
from tests.conftest import NOW_ISO

TZ = ZoneInfo("America/Vancouver")


def _client(app_settings, clock, calendar=None):
    return create_app(App(app_settings, clock, calendar=calendar)).test_client()


def _head(page: str) -> tuple[str, str]:
    """The question and the line under it."""
    found = re.search(
        r'<h1 class="dest__q">(.*?)</h1>\s*(?:<p class="dest__sum">(.*?)</p>)?', page, re.S
    )
    assert found is not None
    return found.group(1), found.group(2) or ""


def _chips(page: str) -> list[str]:
    nav = re.search(r'<nav class="chips".*?</nav>', page, re.S)
    return re.findall(r">([^<]+)(?:<span|</a>)", nav.group(0)) if nav else []


def _scope(page: str) -> str:
    found = re.search(r'name="scope" value="([^"]+)"', page)
    return found.group(1) if found else ""


def _task(conn, family, title: str, due: str | None = None, window: str = "") -> int:
    with db.transaction(conn):
        return tasks.insert(
            conn,
            title=title,
            notes="",
            owner_id=family["sam"].id,
            due_at=due,
            preferred_window=window,
            operation_key=f"test-{title}",
            channel="web",
            chat_id="web",
            now=NOW_ISO,
        )


# -- This week


def test_the_week_is_seven_days_from_today_with_free_time_and_the_plate(
    calendar_settings, clock, conn, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer", datetime(2026, 9, 22, 17, tzinfo=TZ), datetime(2026, 9, 22, 18, tzinfo=TZ)
    )
    calendar.seed(
        "Dentist", datetime(2026, 9, 21, 9, tzinfo=TZ), datetime(2026, 9, 21, 10, tzinfo=TZ)
    )
    calendar.seed("Camping", datetime(2026, 9, 26, tzinfo=TZ), datetime(2026, 9, 28, tzinfo=TZ))
    _task(conn, family, "Call the dentist")  # no day: on the plate
    _task(conn, family, "Pay the bill", due="2026-09-18T17:00:00Z")  # late: on the plate
    _task(conn, family, "Bins out", due="2026-09-22T19:00:00Z")  # a reminder on its day
    page = _client(calendar_settings, clock, calendar).get("/week").text
    question, summary = _head(page)
    assert question == "This week" and summary.startswith("Today: free all day")  # a Sunday
    assert "2 on your plate, 1 late" in summary
    days = re.findall(r'<h2 class="wk__label"[^>]*><a href="(/week/[^"]+)">([^<]+)</a></h2>', page)
    assert [label for _, label in days] == [
        "Today",
        "Tomorrow",
        "Tuesday 22 September",
        "Wednesday 23 September",
        "Thursday 24 September",
        "Friday 25 September",
        "Saturday 26 September",
    ]
    assert days[0][0] == "/week/2026-09-20"
    # Each day: what is on, as a set row with its time, then the free time in words.
    tuesday = page[page.index('id="d-2026-09-22"') : page.index('id="d-2026-09-23"')]
    assert "Soccer" in tuesday and "5\u00a0pm" in tuesday
    assert "Free till 5\u00a0pm, then from 6\u00a0pm" in tuesday
    assert "Bins out" in tuesday  # the reminder, as a small mark on its day
    monday = page[page.index('id="d-2026-09-21"') : page.index('id="d-2026-09-22"')]
    assert "Dentist" in monday and "Free till 9\u00a0am, then from 10\u00a0am" in monday
    saturday = page[page.index('id="d-2026-09-26"') :]
    assert "Camping" in saturday and "All day" in saturday and "Free" not in saturday
    # On your plate, whatever week is showing: what has no day, what is late.
    plate = re.search(r'aria-labelledby="h-plate".*?</section>', page, re.S).group(0)
    assert "Call the dentist" in plate and "Pay the bill" in plate and "Bins out" not in plate
    assert _chips(page) == ["Sam", "Alex", "the girls", "Month", "Past"]
    assert _scope(page) == "About this week:"
    # Earlier and later weeks, and the day's own page.
    assert 'href="/week?from=2026-09-27"' in page and 'href="/week?from=2026-09-13"' in page
    later = _client(calendar_settings, clock, calendar).get("/week?from=2026-09-27").text
    assert "Sunday 27 September" in later and 'href="/week">This week</a>' in later


def test_a_day_of_the_week_has_its_own_page_and_the_week_links_to_it(
    settings, clock, conn, family
) -> None:
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Zoo", kind="outing", now=NOW_ISO)
        plans.insert(
            conn,
            title="Zoo",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=idea.id,
        )
        outcomes.insert(
            conn,
            idea_id=idea.id,
            plan_id=None,
            happened_on="2026-09-17",
            rating=9,
            would_repeat=True,
            notes="the girls loved it",
            recorded_by=None,
            now=NOW_ISO,
        )
    client = _client(settings, clock)
    page = client.get("/week/2026-09-17").text
    question, _ = _head(page)
    assert question == "Thursday 17 September" and 'href="/week"' in page
    assert "Zoo" in page and "Loved it" in page and "the girls loved it" in page
    assert client.get("/week/not-a-day").status_code == 404
    assert client.get("/week?from=1900-01-01").status_code == 404


def test_her_pick_sits_in_pencil_on_a_free_weekend_day(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        kites = ideas.insert(conn, title="Kites on the butte", kind="day_trip", now=NOW_ISO)
        pick_store.insert(
            conn,
            member_id=None,
            window="weekend",
            window_start="2026-09-26",
            window_end="2026-09-27",
            header=None,
            picks=[
                {
                    "kind": "Day trip",
                    "when": "Sat",
                    "title": "Kites on the butte",
                    "why": "Dry",
                    "idea_id": kites.id,
                }
            ],
            made_at=NOW_ISO,
            stale_at="2026-09-21T00:00:00Z",
        )
    page = _client(settings, clock).get("/week").text
    saturday = page[page.index('id="d-2026-09-26"') :]
    assert "Vera\u2019s pick" in saturday and f'href="/idea/{kites.id}"' in saturday
    assert "Kites on the butte" not in page.split('id="d-2026-09-26"')[0]  # only on its day


def test_a_kid_sees_her_week_plainly(settings, clock, conn, family) -> None:
    from familydb import family as rules

    rules.choose_password(conn, family["girls"].id, "a kid can choose one too", now=NOW_ISO)
    with db.transaction(conn):
        for_her = ideas.insert(
            conn, title="Rink", kind="outing", participants=["the girls"], now=NOW_ISO
        )
        for_sam = ideas.insert(
            conn, title="Dinner out", kind="restaurant", participants=["Sam", "Alex"], now=NOW_ISO
        )
        plans.insert(
            conn,
            title="Rink",
            start="2026-09-22T16:00",
            end="2026-09-22T17:00",
            all_day=False,
            idea_id=for_her.id,
        )
        plans.insert(
            conn,
            title="Dinner out",
            start="2026-09-22T19:00",
            end="2026-09-22T21:00",
            all_day=False,
            idea_id=for_sam.id,
        )
    _task(conn, family, "Pay the bill", due="2026-09-18T17:00:00Z")
    app = App(settings.model_copy(update={"web_password": "installer-made-password-1"}), clock)
    kid = create_app(app).test_client()
    assert (
        kid.post(
            "/login", data={"name": "the girls", "password": "a kid can choose one too"}
        ).status_code
        == 302
    )
    page = kid.get("/week").text
    assert "Rink" in page and "Dinner out" not in page  # hers and the family's, not the grown-ups'
    assert "On your plate" not in page and "Pay the bill" not in page and "pick" not in page
    assert _chips(page) == ["Month", "Past"]


# -- What we did


def test_what_we_did_lists_outings_with_their_faces_and_asks_about_the_unrated(
    settings, clock, conn, family
) -> None:
    with db.transaction(conn):
        zoo = ideas.insert(
            conn, title="Zoo", kind="outing", participants=["the girls"], now=NOW_ISO
        )
        ramen = ideas.insert(conn, title="Ramen", kind="restaurant", now=NOW_ISO)
        hike = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        ideas.apply_outcome(conn, zoo.id, happened_on="2026-09-12", avg_rating=9.0, now=NOW_ISO)
        outcomes.insert(
            conn,
            idea_id=zoo.id,
            plan_id=None,
            happened_on="2026-09-12",
            rating=9,
            would_repeat=True,
            notes="loved the otters",
            recorded_by=None,
            now=NOW_ISO,
        )
        outcomes.insert(
            conn,
            idea_id=ramen.id,
            plan_id=None,
            happened_on="2026-09-05",
            rating=4,
            would_repeat=False,
            notes=None,
            recorded_by=None,
            now=NOW_ISO,
        )
        plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=hike.id,
        )
    client = _client(settings, clock)
    page = client.get("/did").text
    question, summary = _head(page)
    assert question == "What we did" and summary == "1 outing to say how it went."
    assert "How did Silver Falls hike go?" in page  # her question, first
    rows = re.split(r'<div class="r r--did"', page)[1:]
    assert len(rows) == 2 and "Zoo" in rows[0] and "Ramen" in rows[1]  # newest first
    assert "Sat 12 Sep · Loved it · loved the otters" in rows[0]
    assert "Not great" in rows[1]
    assert 'name="status" value="idea"' in rows[0]  # Again? puts it back among the things to do
    assert _chips(page) == ["Loved", "Sam", "Alex", "the girls"]
    loved = client.get("/did?loved=1").text
    assert "Zoo" in loved and "Ramen" not in loved.split('class="rows"')[-1]
    assert _scope(page) == "About what we did:"


def test_a_face_on_a_day_comes_back_to_what_we_did(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        hike = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        plan = plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=hike.id,
        )
    client = _client(settings, clock)
    page = client.get("/did").text
    form = re.search(
        r'<form method="post" action="/idea/\d+/outcome">.*?</form>', page, re.S
    ).group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form))
    assert fields["back"] == "did" and fields["plan_id"] == str(plan.id)
    sent = client.post(f"/idea/{hike.id}/outcome", data={**fields, "went": "ok"})
    assert sent.headers["Location"] == "/did"
    assert "How did Silver Falls hike go?" not in client.get("/did").text
    assert "Sat 12" not in client.get("/did").text and "Thu 17 Sep · OK" in client.get("/did").text


# -- Eat, Do, Soon, Lists, Kids: the skeleton


def test_every_destination_answers_a_question_and_scopes_the_box(
    settings, clock, conn, family
) -> None:
    client = _client(settings, clock)
    expected = {
        "/eat": ("Where should we eat?", "About eating out:"),
        "/do": ("What could we do?", "About things to do:"),
        "/week": ("This week", "About this week:"),
        "/soon": (None, "About what is on near home:"),
        "/lists": ("Lists", "About the shopping list:"),
        "/kids": ("The kids", "About the kids:"),
        "/did": ("What we did", "About what we did:"),
    }
    for path, (question, scope) in expected.items():
        page = client.get(path)
        assert page.status_code == 200, path
        if question:
            assert _head(page.text)[0] == question, path
        assert _scope(page.text) == scope, path
        assert 'name="back" value="' + path + '"' in page.text, path
    # The older addresses still find them.
    for old in (
        "/ideas",
        "/restaurants",
        "/happening",
        "/wishes",
    ):
        assert client.get(old).status_code == 200, old
        assert f'name="back" value="{old}"' in client.get(old).text


def test_do_narrows_by_chips_and_leads_with_her_pick(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        free = ideas.insert(
            conn,
            title="Powell Butte kites",
            kind="day_trip",
            cost_level=0,
            participants=["the girls"],
            now=NOW_ISO,
        )
        us = ideas.insert(
            conn,
            title="Jazz night",
            kind="show",
            cost_level=3,
            participants=["Sam", "Alex"],
            now=NOW_ISO,
        )
        ideas.insert(conn, title="Board games", kind="home", cost_level=0, now=NOW_ISO)
        ideas.insert(conn, title="Ramen", kind="restaurant", now=NOW_ISO)  # Eat's, not here
        pick_store.insert(
            conn,
            member_id=None,
            window="weekend",
            window_start="2026-09-26",
            window_end="2026-09-27",
            header=None,
            picks=[
                {
                    "kind": "Day trip",
                    "when": "Sat",
                    "title": "Powell Butte kites",
                    "why": "Dry",
                    "idea_id": free.id,
                }
            ],
            made_at=NOW_ISO,
            stale_at="2026-09-21T00:00:00Z",
        )
    client = _client(settings, clock)
    page = client.get("/do").text
    assert "3 ideas saved · Powell Butte kites fits Sat." in page
    assert '<span class="r__label">Fits Sat</span>' in page and "Ramen" not in page
    assert _chips(page) == [
        "Day trip",
        "Show",
        "Stay in",
        "With the kids",
        "Just us",
        "Free",
        "Close",
        "Sam",
        "Alex",
        "the girls",
        "Dropped",
    ]
    only_free = client.get("/do?free=1").text
    assert (
        "Powell Butte kites" in only_free
        and "Board games" in only_free
        and "Jazz night" not in only_free
    )
    just_us = client.get("/do?us=1").text
    assert "Jazz night" in just_us and "Board games" not in just_us
    with_kids = client.get("/do?kids=1").text
    assert (
        "Powell Butte kites" in with_kids
        and "Board games" in with_kids
        and "Jazz night" not in with_kids
    )
    assert _chips(with_kids)[0] == "Everything"  # a way back
    assert "Show · " in client.get("/do?kind=show").text and f'href="/idea/{us.id}"' in just_us


def test_lists_shows_one_list_at_a_time_with_the_rest_as_chips(
    settings, clock, conn, family
) -> None:
    from familydb.store import lists as list_store

    with db.transaction(conn):
        shopping = list_store.list_id(conn, "shopping", NOW_ISO)
        list_store.add(conn, shopping, "milk", by=None, now=NOW_ISO)
        camping = list_store.list_id(conn, "camping", NOW_ISO)
        list_store.add(conn, camping, "tent", by=None, now=NOW_ISO)
        list_store.add(conn, camping, "torch", by=None, now=NOW_ISO)
    client = _client(settings, clock)
    page = client.get("/lists").text
    assert _head(page) == ("Lists", "Shopping · 1 · Camping · 2 to get")
    assert ">milk<" in page and ">tent<" not in page  # one list at a time
    chips = re.search(r'<nav class="chips".*?</nav>', page, re.S).group(0)
    assert 'href="/lists?list=camping"' in chips and 'class="chip chip--on"' in chips
    camping_page = client.get("/lists?list=camping").text
    assert ">tent<" in camping_page and ">milk<" not in camping_page
    assert _scope(camping_page) == "About the camping list:"
    assert client.get("/lists?list=nothing").status_code == 404
    # A tick comes back to the list it was on.
    fields = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', camping_page))
    ticked = client.post(
        "/lists/change",
        data={**fields, "action": "tick", "name": "camping", "items": "tent", "back": "camping"},
    )
    assert ticked.headers["Location"] == "/lists?list=camping"


def test_the_words_of_the_week_and_the_days() -> None:
    from datetime import date

    today = date(2026, 9, 20)
    assert views.day_label(today, today) == "Today"
    assert views.day_label(date(2026, 9, 21), today) == "Tomorrow"
    assert views.day_label(date(2026, 9, 19), today) == "Yesterday"
    assert views.day_label(date(2026, 10, 3), today) == "Saturday 3 October"
    assert views.free_words([], whole=True) == "Free all day"
    assert views.free_words([(8 * 60, 22 * 60)]) == "Free all day"
    assert views.free_words([(8 * 60, 13 * 60)]) == "Free till 1\u00a0pm"
    assert views.free_words([(15 * 60, 22 * 60)]) == "Free from 3\u00a0pm"
    assert (
        views.free_words([(8 * 60, 10 * 60), (12 * 60, 15 * 60)])
        == "Free till 10\u00a0am, then 12\u00a0pm to 3\u00a0pm"
    )
    assert views.free_words([]) == ""
