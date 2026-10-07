"""The home page: what is on your mind, and around it what is coming, left to do and new."""

from __future__ import annotations

import re
import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from familydb import family as rules
from familydb.app import App
from familydb.store import db, ideas, messages, outcomes, plans, tasks
from familydb.web import create_app, views
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
    assert "Next up" in text and "Soccer practice" in text and "Brunch" not in text
    assert text.index("Next up") < text.index("Just added to Ideas")  # first on a phone


def test_home_shows_the_newest_ideas_and_counts_them(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        for number in range(6):
            ideas.insert(
                conn, title=f"Idea {number}", kind="outing", now=f"2026-09-1{number}T12:00:00Z"
            )
        ideas.insert(conn, title="Ramen place", kind="restaurant", now="2026-09-19T12:00:00Z")
    text = _home(settings, clock).get("/").text
    assert "Ramen place" in text and "Idea 5" in text and "Idea 1" not in text  # the four newest
    assert "All 7 ideas" in text and "1 restaurant to try" in text


def test_the_old_address_of_a_search_still_finds_it(settings, clock, conn) -> None:
    moved = _home(settings, clock).get("/?q=museum&kind=outing")
    assert moved.status_code == 302 and moved.headers["Location"] == "/ideas?q=museum&kind=outing"


def test_a_question_handed_over_by_a_link_waits_in_the_box_unsent(
    settings, clock, thursday_clock, conn, family
) -> None:
    """The box has no ways to start under it (the family found them taking up room), but a link
    that carries a question, as setup's does, still brings the words, and nothing is sent until
    somebody presses Send."""
    text = _home(settings, thursday_clock).get("/").text
    assert "data-say" not in text and 'class="starters"' not in text

    client = _home(settings, thursday_clock)
    waiting = client.get("/?ask=What+should+we+do+this+weekend%3F").text
    assert ">What should we do this weekend?</textarea>" in waiting  # waiting, not sent
    assert messages.last_for_chat(conn, "web", limit=5) == []
    chat = client.get("/chat?ask=What+should+we+do+this+weekend%3F").text
    assert ">What should we do this weekend?</textarea>" in chat


def _box(page: str) -> str:
    found = re.search(r'<form class="composer" id="ask".*?</form>', page, re.S)
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
    assert '<h1 id="h-ask" class="ask__q"><label for="text">What\u2019s on your' in home
    assert f'placeholder="{HOME_PROMPT}"' in _box(home)
    assert 'action="/chat"' in _box(home)  # the chat's own box, not a second way in
    # What the script and the dictation look for.
    assert 'id="text"' in _box(home) and 'data-dictate="ask-mic"' in _box(home)
    assert (
        'id="ask-mic"' in _box(home) and 'id="locate"' in _box(home) and 'id="where"' in _box(home)
    )
    assert 'name="send_where"' in _box(home) and "Share where I am with this message" in home
    assert "Goes to the family chat." in home  # the family shares one password here

    sent = _say(client, home, "what should we do this weekend?")
    assert sent.status_code == 302 and sent.headers["Location"] == "/chat#latest"
    assert web.config["FAMILYDB_CHAT"].wait(10)
    chat = client.get("/chat").text
    room = chat[chat.index('class="scroller"') :]
    assert room.index("what should we do this weekend?") < room.index("Saturday looks dry.")
    assert '<div class="msg__by">Vera <time>' in chat and "<h1>Chat with Vera</h1>" in chat

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
        "/more",
        "/chat",
        "/ideas",
        "/plans",
        "/plans/month",
        "/tasks",
        "/restaurants",
        "/memory",
        "/wishes",
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
    assert 'class="ask__last"' in home and 'href="/chat#latest"' in home


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
    assert "Answering a message now." in home and "Continue with Vera" in home
    assert "vs--busy" in home  # her sign types while she writes back
    # Home never looks again by itself, so its box stays open: what is typed there is kept, and
    # a send before she is done is refused with the words handed back.
    assert 'http-equiv="refresh"' not in home and "disabled" not in _box(home)
    assert "disabled" in _box(client.get("/chat").text)  # the chat's is closed meanwhile
    release.set()
    assert web.config["FAMILYDB_CHAT"].wait(10)


def _task(conn, family, title: str, due: str | None = None, owner: str = "sam") -> int:
    with db.transaction(conn):
        return tasks.insert(
            conn,
            title=title,
            notes="",
            owner_id=family[owner].id,
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
    assert (
        'Mon 21 Sep, <span class="fig">10\u00a0am</span>' in home
        and "No date" in home
        and "All 2 to-dos" in home
    )

    tick = re.search(rf'<form method="post" action="/task/{towels}/done">.*?</form>', home, re.S)
    assert tick is not None and 'aria-label="Mark done: Buy paper towels"' in tick.group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', tick.group(0)))
    stale = client.post(f"/task/{towels}/done", data={**fields, "revision": "0", "once": "old"})
    assert stale.headers["Location"] == "/"
    assert tasks.get(conn, towels).status == "open"  # changed since it was drawn: not ticked

    done = client.post(f"/task/{towels}/done", data=fields, follow_redirects=True)
    assert "Done: Buy paper towels." in done.text
    assert tasks.get(conn, towels).status == "done"
    assert tasks.get(conn, towels).title == "Buy paper towels"  # nothing else about it changed
    assert "Buy paper towels" not in done.text.split("Done: Buy paper towels.")[1]
    assert "All 1 to-do" in done.text


# -- what the page says, in words


def test_the_greeting_follows_the_hour_and_the_name() -> None:
    assert views.greeting(7, "Sam") == "Good morning, Sam"
    assert views.greeting(12, "Sam") == "Good afternoon, Sam"
    assert views.greeting(19, None) == "Good evening"  # the family shares one password


def _plan(title: str, relative: str | None = "tomorrow") -> dict:
    return {"title": title, "relative": relative}


def test_the_one_line_under_the_greeting_says_what_is_coming_and_what_is_late() -> None:
    def said(*args, **kwargs) -> str:
        parts = views.home_line(*args, plans_href="/plans", todo_href="/tasks", **kwargs)
        return "".join(part["text"] for part in parts)

    assert said([_plan("Roller rink")], 3) == "Roller rink tomorrow, and three to-dos are late."
    assert said([_plan("Roller rink")], 1) == "Roller rink tomorrow, and one to-do is late."
    assert said([_plan("Roller rink", None)], 0) == "Roller rink."
    assert said([], 2) == "Two to-dos are late."
    assert said([], 0) == "Nothing is planned yet, and nothing is late."
    assert said([], 12) == "12 to-dos are late."  # a big number stays digits
    parts = views.home_line([_plan("Roller rink")], 3, plans_href="/plans", todo_href="/tasks")
    assert [p["href"] for p in parts if p["href"]] == ["/plans", "/tasks"]  # both are links
    # A kid is told of her plan and a yes, never of what is late.
    kid = views.home_line(
        [_plan("Roller rink")],
        5,
        plans_href="/plans",
        todo_href="/wishes",
        kid=True,
        others="Theo",
        yes=("Sam", "your sketchbook"),
    )
    assert "".join(p["text"] for p in kid) == (
        "Roller rink tomorrow with Theo, and Sam said yes to your sketchbook!"
    )


def test_a_to_do_is_worded_by_how_late_it_is() -> None:
    today = date(2026, 9, 20)
    assert views.late_words(date(2026, 9, 14), today) == "6 days late"
    assert views.late_words(date(2026, 9, 19), today) == "1 day late"
    assert views.late_words(date(2026, 9, 14), today, kid=True) == "Was due Mon 14 Sep"
    assert views.late_words(date(2026, 9, 20), today) is None  # due today is not late

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
    row = views.todo_row(task, TZ, today, {"sam": 1})
    assert row["late"] == "1 day late" and row["when"] == "Sat 19 Sep, 9\u00a0am"
    assert row["person"] == {"name": "Sam", "slot": 1, "initial": "S"}
    soon = task.model_copy(update={"due_at": "2026-09-23T16:30:00Z"})
    assert (
        views.todo_row(soon, TZ, today, {}, kid=True)["when"]
        == "Wed 23 Sep, 9:30\u00a0am, in 3 days"
    )
    loose = task.model_copy(update={"due_at": None, "owner": None})
    assert views.todo_row(loose, TZ, today, {})["when"] == "No date"
    assert views.todo_row(loose, TZ, today, {})["person"]["name"] == "Everyone"


def test_who_a_plan_is_for_is_told_with_their_colours() -> None:
    slots = {"maya": 3, "theo": 4}
    idea = ideas.Idea(
        id=1,
        title="Rink",
        kind="outing",
        participants=["Maya", "Theo"],
        created_at=NOW_ISO,
        updated_at=NOW_ISO,
    )
    people = views.people_for(idea, slots)
    assert [(p["name"], p["slot"]) for p in people] == [("Maya", 3), ("Theo", 4)]
    assert views.names_text(people) == "Maya and Theo"
    everyone = views.people_for(None, slots)
    assert everyone == [{"name": "Everyone", "slot": 0, "initial": ""}]
    # Somebody not on the family list has a letter and no colour; nobody is mistaken for a house.
    guest = views.people_for(idea.model_copy(update={"participants": ["Grandma"]}), slots)
    assert guest == [{"name": "Grandma", "slot": 0, "initial": "G"}]
    assert views.names_text([{"name": n} for n in ("Maya", "Theo", "Sam")]) == "Maya, Theo and Sam"


def test_money_is_told_as_a_person_would() -> None:
    assert views.money_text(0) == "$0.00" and views.money_text(2) == "$2.00"
    assert views.money_text(0.04) == "4¢" and views.money_text(0.0004) == "1¢"
    assert views.money_text(0.1) == "$0.10"


# -- who sees what


@pytest.fixture
def app(settings, clock, conn, family):
    shared = {"web_password": "installer-made-password-1", "kid_daily_messages": 20}
    live = App(settings.model_copy(update=shared), clock)
    for key, word in (("sam", "sam likes long sentences"), ("girls", "a kid can choose one too")):
        rules.choose_password(conn, family[key].id, word, now=NOW_ISO)
    return live


def _in_as(app, name: str, password: str):
    client = create_app(app).test_client()
    assert client.post("/login", data={"name": name, "password": password}).status_code == 302
    return client


def test_a_grown_up_is_greeted_by_name_and_sees_the_household(app, conn, family) -> None:
    _task(conn, family, "Call the dentist", due="2026-09-18T19:00:00Z")
    home = _in_as(app, "Sam", "sam likes long sentences").get("/").text
    assert "Good afternoon, Sam" in home and "Sunday 20 September" in home
    assert ">One to-do</a> is late." in home and "2 days late" in home
    assert "Goes to the family chat as Sam." in home
    assert "Vera today" in home and "spent today" in home  # what she costs: for grown-ups
    assert "Just added to Ideas" in home


def test_a_kid_sees_only_what_is_hers_and_nothing_of_how_it_works(app, conn, family) -> None:
    _task(conn, family, "Feed the fish", due="2026-09-22T19:00:00Z", owner="girls")
    _task(conn, family, "Call the dentist", owner="sam")
    kid = _in_as(app, "the girls", "a kid can choose one too")
    home = kid.get("/").text
    assert "Good afternoon, the girls" in home
    assert "Feed the fish" in home and "Call the dentist" not in home  # only her own
    assert "My to-dos" in home and "Next up for you" in home
    # No money, no model, no household pages, no pill.
    for hidden in ("spent today", "Vera today", "Just added to Ideas", "pill-health"):
        assert hidden not in home, hidden
    assert not re.search(r"\blate\b", home)  # nothing is late to a kid
    assert "Goes to your own chat with Vera; Sam and Alex can read it." in home
    assert "20 messages left today." in home
    # She ticks her own off herself, from Home.
    assert 'aria-label="Mark done: Feed the fish"' in home and "todo--mine" in home


def test_a_present_is_not_on_a_kids_home(app, conn, family) -> None:
    with db.transaction(conn):
        ideas.insert(
            conn,
            title="Lego set",
            kind="gift",
            participants=["the girls"],
            tags=["gift"],
            now=NOW_ISO,
        )
    assert "Lego set" in _in_as(app, "Sam", "sam likes long sentences").get("/").text
    assert "Lego set" not in _in_as(app, "the girls", "a kid can choose one too").get("/").text


# -- how did it go


def test_a_plan_nobody_has_rated_asks_three_faces_and_the_answer_is_kept(
    settings, clock, conn, family
) -> None:
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        plan = plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=idea.id,
        )
    client = _home(settings, clock)
    home = client.get("/").text
    assert "How did Silver Falls hike go?" in home
    for face in ("Loved it", "OK", "Not great"):
        assert f"<span>{face}</span>" in home
    form = re.search(r'<form class="rate-line".*?</form>', home, re.S).group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form))
    assert fields["plan_id"] == str(plan.id) and fields["back"] == "home"

    sent = client.post(f"/idea/{idea.id}/outcome", data={**fields, "went": "loved"})
    assert sent.status_code == 302 and sent.headers["Location"] == "/"  # back for the next one
    recorded = outcomes.list_for_idea(conn, idea.id)
    assert [(o.rating, o.plan_id, o.happened_on) for o in recorded] == [(9, plan.id, "2026-09-17")]
    assert "How did Silver Falls hike go?" not in client.get("/").text  # it has been said


def test_a_face_is_a_rating_on_the_same_scale_as_the_longer_form() -> None:
    from familydb.web import edits

    assert edits.FACES == {"loved": 9, "ok": 6, "not-great": 3}
