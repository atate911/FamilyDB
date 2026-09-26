"""The home page: what is on your mind, and around it what is coming, left to do and new."""

from __future__ import annotations

import math
import re
import threading
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from familydb.app import App
from familydb.store import db, ideas, messages, tasks
from familydb.web import create_app, views
from familydb.web.agenda import Entry
from familydb.web.chat import HOME_PROMPT
from tests import fakes
from tests.conftest import NOW_ISO

TZ = ZoneInfo("America/Vancouver")


def _home(app_settings, clock, calendar=None):
    return create_app(App(app_settings, clock, calendar=calendar)).test_client()


def test_home_puts_what_is_coming_up_before_everything_else(calendar_settings, clock, conn, family):
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 22, 17, tzinfo=TZ),
        datetime(2026, 9, 22, 18, tzinfo=TZ),
    )
    calendar.seed(  # already over: not coming up
        "Brunch", datetime(2026, 9, 19, 10, tzinfo=TZ), datetime(2026, 9, 19, 11, tzinfo=TZ)
    )
    text = _home(calendar_settings, clock, calendar).get("/").text
    assert "Coming up" in text and "Soccer practice" in text and "Brunch" not in text
    assert text.index("Coming up") < text.index("Lately added")  # first on a phone


def test_home_shows_the_newest_ideas_and_counts_them(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        for number in range(6):
            ideas.insert(
                conn, title=f"Idea {number}", kind="outing", now=f"2026-09-1{number}T12:00:00Z"
            )
        ideas.insert(conn, title="Ramen place", kind="restaurant", now="2026-09-19T12:00:00Z")
    text = _home(settings, clock).get("/").text
    assert "Ramen place" in text and "Idea 5" in text and "Idea 1" not in text  # the four newest
    assert "All 7" in text and "1 restaurant to try" in text


def test_the_old_address_of_a_search_still_finds_it(settings, clock, conn) -> None:
    moved = _home(settings, clock).get("/?q=museum&kind=outing")
    assert moved.status_code == 302 and moved.headers["Location"] == "/ideas?q=museum&kind=outing"


def test_the_question_of_the_day_is_one_tap_away(
    settings, clock, thursday_clock, conn, family
) -> None:
    """With a script a way to start fills the box; without one, the link brings Home back with
    the words waiting in it. Either way nothing is sent until somebody presses Send."""
    text = _home(settings, thursday_clock).get("/").text
    assert 'data-say="What should we do this weekend?"' in text
    assert 'href="/?ask=What+should+we+do+this+weekend?#ask"' in text
    assert 'data-say="Remind me to "' in text and ">Remind me to…</a>" in text
    # On a weekend day it is today that wants filling. The fixture's clock is a Sunday.
    assert 'data-say="What should we do today?"' in _home(settings, clock).get("/").text

    client = _home(settings, thursday_clock)
    waiting = client.get("/?ask=What+should+we+do+this+weekend%3F").text
    assert ">What should we do this weekend?</textarea>" in waiting  # waiting, not sent
    assert messages.last_for_chat(conn, "web", limit=5) == []
    chat = client.get("/chat?ask=What+should+we+do+this+weekend%3F").text  # the setup's link
    assert ">What should we do this weekend?</textarea>" in chat


def _box(page: str) -> str:
    found = re.search(r'<form class="ask".*?</form>', page, re.S)
    assert found is not None
    return found.group(0)


def _say(client, page: str, text: str, who: str = "Sam"):
    fields = dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', _box(page)))
    return client.post("/chat", data={**fields, "text": text, "who": who})


def test_what_is_on_your_mind_is_asked_on_home_and_answered_in_the_chat(
    settings, clock, conn, family
) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saturday looks dry. The museum?")]))
    web = create_app(App(settings, clock), api=api)
    client = web.test_client()
    home = client.get("/").text
    assert "ask.js" in home
    # Her question is the box's label, and the page's heading: a tap on it is a way in.
    assert '<h1 class="ask-question"><label for="text">What\u2019s on your' in _box(home)
    assert f'placeholder="{HOME_PROMPT}"' in _box(home)
    assert 'action="/chat"' in _box(home)  # the chat's own box, not a second way in

    sent = _say(client, home, "what should we do this weekend?")
    assert sent.status_code == 302 and sent.headers["Location"] == "/chat#latest"
    assert web.config["FAMILYDB_CHAT"].wait(10)
    chat = client.get("/chat").text
    assert chat.index("what should we do this weekend?") < chat.index("Saturday looks dry.")
    assert "<strong>Vera</strong>" in chat and "<h1>Vera</h1>" in chat

    # Back home, what she said is the line under the box, a tap from the rest of it.
    home = client.get("/").text
    assert "Saturday looks dry. The museum?" in home and "Continue with Vera" in home
    assert len(api.requests) == 1  # one message, one call; none for the pages around it


def test_browsing_asks_nothing_of_a_model(settings, clock, conn, family) -> None:
    """Every page reads the database and words things itself: only a message sent is a call."""
    api = fakes.FakeMessagesAPI()  # nothing scripted: a call would fail the test
    with db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="u1",
            chat_id="web",
            member_id=family["sam"].id,
            text="remind me about the dentist",
            now="2026-09-20T20:00:00Z",
        )
        messages.insert_out(
            conn, channel="web", chat_id="web", text="Done.", reply_to=asked.id, now=NOW_ISO
        )
        ideas.insert(conn, title="Ramen place", kind="restaurant", now=NOW_ISO)
    client = create_app(App(settings, clock), api=api).test_client()
    for path in (
        "/",
        "/chat",
        "/ideas",
        "/plans",
        "/plans/month",
        "/tasks",
        "/restaurants",
        "/memory",
    ):
        assert client.get(path).status_code == 200, path
    assert api.requests == []
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


def _exchange(conn, family, *, asked_at: str, answered_at: str, answer: str) -> None:
    with db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="web",
            channel_update_id=f"u-{asked_at}",
            chat_id="web",
            member_id=family["sam"].id,
            text="anything on tonight?",
            now=asked_at,
        )
        messages.mark_processed(conn, asked.id, [], now=answered_at)
        messages.insert_out(
            conn, channel="web", chat_id="web", text=answer, reply_to=asked.id, now=answered_at
        )


def test_what_she_said_last_stays_on_home_for_a_day(settings, clock, conn, family) -> None:
    _exchange(
        conn,
        family,
        asked_at="2026-09-18T19:00:00Z",
        answered_at="2026-09-18T19:00:05Z",
        answer="The market closes at two.",
    )
    home = _home(settings, clock).get("/").text
    assert "The market closes at two." not in home  # two days ago: only in the chat now
    _exchange(
        conn,
        family,
        asked_at="2026-09-20T20:00:00Z",
        answered_at="2026-09-20T20:00:05Z",
        answer="Nothing booked; the park is free till six.",
    )
    home = _home(settings, clock).get("/").text
    assert "Nothing booked; the park is free till six." in home
    assert '<ol class="thread brief">' in home and 'href="/chat#latest"' in home


def test_home_says_when_she_is_answering_and_keeps_its_own_box_open(
    settings, clock, conn, family
) -> None:
    asked, release = threading.Event(), threading.Event()

    def slow(**kwargs):
        asked.set()
        assert release.wait(10)
        return fakes.message([fakes.text("done")])

    web = create_app(App(settings, clock), api=type("Slow", (), {"create": staticmethod(slow)})())
    client = web.test_client()
    _say(client, client.get("/").text, "take your time")
    assert asked.wait(10)
    home = client.get("/").text
    assert "Answering a message now." in home and "Open the conversation" in home
    # Home never looks again by itself, so its box stays open: what is typed there is kept, and
    # a send before she is done is refused with the words handed back.
    assert 'http-equiv="refresh"' not in home and "disabled" not in _box(home)
    assert "disabled" in _box(client.get("/chat").text)  # the chat's is closed meanwhile
    release.set()
    assert web.config["FAMILYDB_CHAT"].wait(10)


def _task(conn, family, title: str, due: str | None = None) -> int:
    with db.transaction(conn):
        return tasks.insert(
            conn,
            title=title,
            notes="",
            owner_id=family["sam"].id,
            due_at=due,
            preferred_window="",
            operation_key=f"test-{title}",
            channel="web",
            chat_id="web",
            now=NOW_ISO,
        )


def test_what_is_left_to_do_is_on_home_and_ticks_off_there(settings, clock, conn, family) -> None:
    towels = _task(conn, family, "Buy paper towels", due="2026-09-21T17:00:00Z")
    _task(conn, family, "Call the dentist")
    client = _home(settings, clock)
    home = client.get("/").text
    assert home.index("Buy paper towels") < home.index("Call the dentist")  # soonest first
    assert "due tomorrow, 10:00" in home and "All 2" in home

    tick = re.search(
        rf'<form class="tick-form" method="post" action="/task/{towels}/done">.*?</form>',
        home,
        re.S,
    )
    assert tick is not None
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', tick.group(0)))
    stale = client.post(f"/task/{towels}/done", data={**fields, "revision": "0", "once": "old"})
    assert stale.headers["Location"] == "/"
    assert tasks.get(conn, towels).status == "open"  # changed since it was drawn: not ticked

    done = client.post(f"/task/{towels}/done", data=fields, follow_redirects=True)
    assert "Done: #1 Buy paper towels." in done.text
    assert tasks.get(conn, towels).status == "done"
    assert tasks.get(conn, towels).title == "Buy paper towels"  # nothing else about it changed
    assert "Buy paper towels" not in done.text.split("Done: #1 Buy paper towels.")[1]
    assert "All 1" in done.text


def test_home_words_a_task_by_when_it_is_due() -> None:
    today = date(2026, 9, 20)
    task = tasks.Task(
        id=3,
        title="Dentist",
        owner="Sam",
        due_at="2026-09-19T16:00:00Z",
        channel="web",
        chat_id="web",
        created_at=NOW_ISO,
        updated_at=NOW_ISO,
    )
    assert views.task_brief(task, TZ, today)["due"] == "was due yesterday"
    assert views.task_brief(task, TZ, today)["late"]
    soon = task.model_copy(update={"due_at": "2026-09-23T16:30:00Z"})
    assert views.task_brief(soon, TZ, today)["due"] == "due in 3 days, 09:30"
    loose = task.model_copy(update={"due_at": None, "preferred_window": "Some Saturday"})
    assert views.task_brief(loose, TZ, today)["window"] == "Some Saturday"
    assert views.task_brief(loose, TZ, today)["due"] is None


def test_the_radar_puts_sooner_plans_nearer_the_middle() -> None:
    assert [views.radar_distance(days) for days in (-2, 0, 7, 14, 28, 60)] == [
        12,
        12,
        33,
        66,
        92,
        92,
    ]
    today = date(2026, 9, 20)
    plans = [
        Entry(
            f"Plan {n}",
            (today + timedelta(days=away)).isoformat(),
            None,
            True,
            None,
            None,
            "confirmed",
            n,
            None,
        )
        for n, away in enumerate((1, 1, 6, 13, 40))  # two on one day
    ]
    blips = views.radar_blips(plans, today)
    assert [blip["next"] for blip in blips] == [True, False, False, False, False]
    assert len({blip["bearing"] for blip in blips}) == len(blips)  # never one on top of another
    reach = [round(math.dist((100, 100), (blip["x"], blip["y"]))) for blip in blips]
    assert reach == sorted(reach) and reach[-1] <= 92  # later is further out, and inside the dial


def test_home_draws_what_is_coming_on_a_radar_beside_the_next(
    calendar_settings, clock, conn, family
):
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 22, 17, tzinfo=TZ),
        datetime(2026, 9, 22, 18, tzinfo=TZ),
    )
    calendar.seed(
        "Pumpkin patch", datetime(2026, 10, 3, 10, tzinfo=TZ), datetime(2026, 10, 3, 13, tzinfo=TZ)
    )
    text = _home(calendar_settings, clock, calendar).get("/").text
    assert '<div class="radar" aria-hidden="true">' in text  # a picture of what the words say
    assert text.count('<g class="blip ') == 2 and '<g class="blip b7 next">' in text
    assert "Soccer practice" in text and "1 more on the radar" in text


def test_an_empty_radar_says_so_in_words(settings, clock, conn, family) -> None:
    text = _home(settings, clock).get("/").text
    assert '<div class="radar" aria-hidden="true">' in text and '<g class="blip' not in text
    assert "Nothing on the radar yet." in text
