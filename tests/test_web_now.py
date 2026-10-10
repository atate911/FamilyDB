"""Now, the first screen (web/now.py, templates/frame.html): the box first, then her questions,
her picks and today's line, and the row of destinations. No model call for a page view."""

from __future__ import annotations

import re
import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from familydb import family as rules
from familydb.app import App
from familydb.store import db, ideas, messages, outcomes, plans, tasks, wishes
from familydb.store import picks as pick_store
from familydb.web import create_app, views
from familydb.web.chat import HOME_PROMPT
from tests import fakes
from tests.conftest import NOW_ISO

TZ = ZoneInfo("America/Vancouver")


def _now(app_settings, clock, calendar=None):
    return create_app(App(app_settings, clock, calendar=calendar)).test_client()


def _box(page: str) -> str:
    found = re.search(r'<form class="bar[^"]*" id="ask".*?</form>', page, re.S)
    assert found is not None
    return found.group(0)


def _say(client, page: str, text: str, who: str = "Sam"):
    fields = dict(re.findall(r'name="(csrf|once|back)" value="([^"]+)"', _box(page)))
    return client.post("/chat", data={**fields, "text": text, "who": who})


def _row(page: str) -> str:
    return re.search(r'<nav class="row".*?</nav>', page, re.S).group(0)


# -- the box, first, always


def test_the_box_is_first_and_posts_to_the_chat_to_come_back_here(settings, clock, conn, family):
    home = _now(settings, clock).get("/").text
    body = home[home.index("<body") :]
    assert body.index('id="ask"') < body.index('class="ctx"') < body.index('class="row"')
    box = _box(home)
    assert 'action="/chat"' in box and 'name="back" value="/"' in box
    assert f'placeholder="{HOME_PROMPT}"' in box and "ask.js" in home
    # What the script and the dictation look for.
    assert 'id="text"' in box and 'data-dictate="ask-mic"' in box and 'id="ask-mic"' in box
    assert 'id="locate"' in box and 'id="where"' in box and 'name="send_where"' in box
    # The family shares one password here, so the box asks who is writing.
    assert '<select id="who" name="who" required>' in box
    assert "data-say" not in home and 'class="starters"' not in home  # no ways to start


def test_a_question_handed_over_by_a_link_waits_in_the_box_unsent(
    settings, thursday_clock, conn, family
) -> None:
    client = _now(settings, thursday_clock)
    waiting = client.get("/?ask=What+should+we+do+this+weekend%3F").text
    assert ">What should we do this weekend?</textarea>" in waiting  # waiting, not sent
    assert messages.last_for_chat(conn, "web", limit=5) == []


def test_the_old_address_of_a_search_still_finds_it(settings, clock, conn) -> None:
    moved = _now(settings, clock).get("/?q=museum&kind=outing")
    assert moved.status_code == 302 and moved.headers["Location"] == "/do?q=museum&kind=outing"


def test_the_context_line_says_the_day_and_the_hour(settings, clock, conn, family) -> None:
    home = _now(settings, clock).get("/").text
    assert '<p class="ctx">Sunday 2:03\u00a0pm</p>' in home


# -- her reply comes back over Now


def test_a_message_sent_from_now_comes_back_to_now_with_her_answer_under_the_box(
    settings, clock, conn, family
) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saturday looks dry. The museum?")]))
    web = create_app(App(settings, clock), api=api)
    client = web.test_client()
    sent = _say(client, client.get("/").text, "what should we do this weekend?")
    where = sent.headers["Location"]
    assert sent.status_code == 302 and re.fullmatch(r"/\?asked=[0-9a-f]{32}#said", where)
    assert web.config["FAMILYDB_CHAT"].wait(10)
    back = client.get(where.split("#")[0]).text
    sheet = re.search(r'<div class="said-sheet".*?Earlier</a>', back, re.S).group(0)
    assert "what should we do this weekend?" in sheet and "Saturday looks dry. The museum?" in sheet
    assert 'href="/chat#latest"' in sheet  # the thread, one tap away
    assert len(api.requests) == 1  # one message, one call; none for the pages around it
    # Opened again without the message named, Now is quiet: the reply lives in the thread.
    assert "Saturday looks dry" not in client.get("/").text
    assert "Saturday looks dry" in client.get("/chat").text


def test_an_instruction_comes_back_as_a_receipt_with_undo(settings, clock, conn, family) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved.")]),
    )
    web = create_app(App(settings, clock), api=api)
    client = web.test_client()
    sent = _say(client, client.get("/").text, "we should try the ramen place")
    assert web.config["FAMILYDB_CHAT"].wait(10)
    back = client.get(sent.headers["Location"].split("#")[0]).text
    receipt = re.search(r'<div class="rcpt" role="status">.*?Earlier</a></div>', back, re.S)
    assert receipt is not None
    assert "Saved." in receipt.group(0) and "Saved an idea." in receipt.group(0)
    assert 'action="/undo"' in receipt.group(0) and "add_idea" not in back
    assert 'class="said-sheet"' not in back  # a receipt, not a sheet


def test_while_she_answers_now_says_so_closes_the_box_and_looks_again(
    settings, clock, conn, family
) -> None:
    asked, release = threading.Event(), threading.Event()

    def slow(**kwargs):
        asked.set()
        assert release.wait(10)
        return fakes.message([fakes.text("done")])

    web = create_app(App(settings, clock), api=type("Slow", (), {"create": staticmethod(slow)})())
    client = web.test_client()
    sent = _say(client, client.get("/").text, "take your time")
    assert asked.wait(10)
    waiting = client.get(sent.headers["Location"].split("#")[0]).text
    assert "Answering a message now." in waiting and "vs--busy" in waiting
    assert "disabled" in _box(waiting)  # closed while she writes back
    refresh = re.search(r'<meta http-equiv="refresh" content="3; url=([^"]+)"', waiting)
    assert refresh is not None and "n=1" in refresh.group(1) and "asked=" in refresh.group(1)
    # Somebody else opening Now meanwhile finds the box closed and nothing of the message.
    other = create_app(App(settings, clock), api=web.config["FAMILYDB_CHAT"]._api).test_client()
    assert "take your time" not in other.get("/").text
    release.set()
    assert web.config["FAMILYDB_CHAT"].wait(10)
    assert 'http-equiv="refresh"' not in client.get(sent.headers["Location"].split("#")[0]).text


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
        "/?asked=u1",
        "/more",
        "/chat",
        "/ideas",
        "/plans",
        "/plans/month",
        "/happening",
        "/tasks",
        "/lists",
        "/restaurants",
        "/memory",
        "/wishes",
        "/wiki",
        "/wiki/_search?q=start",
    ):
        assert client.get(path).status_code == 200, path
    assert api.requests == []
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0


# -- her questions


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
    client = _now(settings, clock)
    home = client.get("/").text
    question = re.search(r'<section class="q".*?</section>', home, re.S).group(0)
    assert "How did Silver Falls hike go?" in question and "Thu 17 Sep" in question
    for face in ("Loved it", "OK", "Not great"):
        assert f"<span>{face}</span>" in question
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', question))
    assert fields["plan_id"] == str(plan.id) and fields["back"] == "home"

    sent = client.post(f"/idea/{idea.id}/outcome", data={**fields, "went": "loved"})
    assert sent.status_code == 302 and sent.headers["Location"] == "/"  # back for the next one
    recorded = outcomes.list_for_idea(conn, idea.id)
    assert [(o.rating, o.plan_id, o.happened_on) for o in recorded] == [(9, plan.id, "2026-09-17")]
    assert "How did Silver Falls hike go?" not in client.get("/").text  # it has been said


def test_a_kids_pitch_is_asked_about_and_later_puts_it_off_on_this_device(
    settings, clock, conn, family
) -> None:
    with db.transaction(conn):
        pitch = ideas.insert(
            conn,
            title="Sky High Trampolines",
            kind="outing",
            suggested_by=family["girls"].id,
            now="2026-09-18T22:00:00Z",
        )
        ideas.insert(
            conn,
            title="Old one",
            kind="outing",
            suggested_by=family["girls"].id,
            now="2026-08-01T22:00:00Z",
        )
        ideas.insert(
            conn, title="Sam\u2019s own", kind="outing", suggested_by=family["sam"].id, now=NOW_ISO
        )
    client = _now(settings, clock)
    home = client.get("/").text
    question = re.search(r'<section class="q".*?</section>', home, re.S).group(0)
    assert "the girls suggested Sky High Trampolines." in question
    assert "the girls, 18 September" in question
    assert f'href="/idea/{pitch.id}"' in question and 'action="/later"' in question
    assert "Old one" not in home and "Sam\u2019s own" not in home  # two weeks old; not a kid's
    csrf = re.search(r'name="csrf" value="([^"]+)"', question).group(1)
    assert client.post("/later", data={"csrf": csrf, "idea": str(pitch.id)}).status_code == 302
    assert "Sky High" not in client.get("/").text
    assert "Sky High" in _now(settings, clock).get("/").text  # another device still asks
    assert client.post("/later", data={"csrf": csrf, "idea": "x"}).status_code == 400


def test_with_nothing_waiting_now_says_so(settings, clock, conn, family) -> None:
    home = _now(settings, clock).get("/").text
    assert "Nothing needs you." in home and 'class="q"' not in home


# -- her picks, made ahead


def _set(conn, picks, *, member_id=None, window="now", made="2026-09-20T20:00:00Z"):
    with db.transaction(conn):
        return pick_store.insert(
            conn,
            member_id=member_id,
            window=window,
            window_start="2026-09-20",
            window_end="2026-09-20",
            header="Dry, free this afternoon",
            picks=picks,
            made_at=made,
            stale_at="2026-09-20T23:00:00Z",
        )


def test_her_picks_are_tiles_with_a_reason_and_a_way_in(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        ramen = ideas.insert(conn, title="Kenji\u2019s Ramen", kind="restaurant", now=NOW_ISO)
    client = _now(settings, clock)
    assert "What about" not in client.get("/").text
    _set(
        conn,
        [
            {
                "kind": "Eat",
                "when": "tonight",
                "title": "Kenji\u2019s Ramen",
                "why": "Open till 9 pm, 12 min",
                "idea_id": ramen.id,
            },
            {
                "kind": "New",
                "when": "Sat 26 Sep",
                "title": "Pumpkin carving",
                "why": "Free. Listed by Tryon Creek",
                "idea_id": None,
            },
        ],
    )
    home = client.get("/").text
    picks = re.search(
        r'<section class="sec" aria-labelledby="h-picks">.*?</section>', home, re.S
    ).group(0)
    assert "What about…" in picks and "chosen 1\u00a0pm" in picks
    tiles = re.findall(r'<a class="pk" href="([^"]+)">(.*?)</a>', picks, re.S)
    assert [href for href, _ in tiles] == [f"/idea/{ramen.id}", "/soon"]
    assert "Eat · tonight" in tiles[0][1] and "Open till 9 pm, 12 min" in tiles[0][1]
    assert "New · Sat 26 Sep" in tiles[1][1]
    assert '<p class="ctx">Sunday 2:03\u00a0pm · Dry, free this afternoon</p>' in home
    # Different ones is a message to her, sent on purpose.
    different = re.search(r'<form class="sec__more".*?</form>', picks, re.S).group(0)
    assert (
        'action="/chat"' in different and 'name="text" value="What else could we do?' in different
    )
    assert "Nothing needs you" not in home


def test_a_present_never_shows_among_a_kids_picks(settings, clock, conn, family) -> None:
    shared = {"web_password": "installer-made-password-1"}
    app = App(settings.model_copy(update=shared), clock)
    rules.choose_password(conn, family["girls"].id, "a kid can choose one too", now=NOW_ISO)
    with db.transaction(conn):
        lego = ideas.insert(
            conn, title="Lego set", kind="gift", participants=["the girls"], now=NOW_ISO
        )
        zoo = ideas.insert(conn, title="The zoo", kind="outing", now=NOW_ISO)
    _set(
        conn,
        [
            {"kind": "Gift", "when": "Sat", "title": "Lego set", "why": "", "idea_id": lego.id},
            {
                "kind": "Go out",
                "when": "Sat",
                "title": "The zoo",
                "why": "You haven\u2019t been",
                "idea_id": zoo.id,
            },
        ],
        member_id=family["girls"].id,
        window="weekend",
    )
    client = create_app(app).test_client()
    assert (
        client.post(
            "/login", data={"name": "the girls", "password": "a kid can choose one too"}
        ).status_code
        == 302
    )
    home = client.get("/").text
    assert "The zoo" in home and "Lego set" not in home


# -- today's line


def test_today_and_tomorrow_are_one_line_each(calendar_settings, clock, conn, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 20, 17, tzinfo=TZ),
        datetime(2026, 9, 20, 18, tzinfo=TZ),
    )
    calendar.seed(
        "Brunch", datetime(2026, 9, 19, 10, tzinfo=TZ), datetime(2026, 9, 19, 11, tzinfo=TZ)
    )
    calendar.seed(
        "Swim", datetime(2026, 9, 21, 16, tzinfo=TZ), datetime(2026, 9, 21, 17, tzinfo=TZ)
    )
    calendar.seed(
        "Dentist", datetime(2026, 9, 21, 9, tzinfo=TZ), datetime(2026, 9, 21, 10, tzinfo=TZ)
    )
    home = _now(calendar_settings, clock, calendar).get("/").text
    lines = [
        (label, re.sub(r"<[^>]+>", "", words))
        for label, words in re.findall(
            r'<p class="today"><b>(\w+)</b><span>(.*?)</span></p>', home, re.S
        )
    ]
    assert 'href="/plans/month#d-2026-09-21"' in home
    assert lines[0][0] == "Today" and "Soccer practice 5\u00a0pm" in lines[0][1]
    assert lines[1][0] == "Tomorrow" and "Dentist 9\u00a0am, then Swim 4\u00a0pm" in lines[1][1]
    assert "Brunch" not in home  # yesterday


def test_a_free_day_says_so(settings, clock, conn, family) -> None:
    home = _now(settings, clock).get("/").text
    assert home.count("<span>Free.</span>") == 2


# -- what waits on a person today


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


def test_a_to_do_that_is_late_or_due_today_is_on_now_and_ticks_off_there(
    settings, clock, conn, family
) -> None:
    towels = _task(conn, family, "Buy paper towels", due="2026-09-18T17:00:00Z")
    _task(conn, family, "Book the dentist", due="2026-09-20T23:00:00Z")
    _task(conn, family, "Someday: clear the garage")
    _task(conn, family, "Next week", due="2026-09-25T17:00:00Z")
    client = _now(settings, clock)
    home = client.get("/").text
    plate = re.search(
        r'<section class="sec" aria-labelledby="h-todo">.*?</section>', home, re.S
    ).group(0)
    assert "On your plate" in plate and "Buy paper towels" in plate and "Book the dentist" in plate
    assert "clear the garage" not in home and "Next week" not in home  # the week's plate has those
    assert "2 days late" in plate and 'href="/tasks"' in plate
    tick = re.search(
        rf'<form class="todo__tick" method="post" action="/task/{towels}/done">.*?</form>',
        home,
        re.S,
    )
    assert tick is not None and 'aria-label="Mark done: Buy paper towels"' in tick.group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', tick.group(0)))
    done = client.post(f"/task/{towels}/done", data=fields)
    assert done.headers["Location"] == "/"
    assert tasks.get(conn, towels).status == "done"
    assert 'aria-label="Mark done: Buy paper towels"' not in client.get("/").text


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


def test_a_wish_waiting_on_a_parent_is_asked_and_answered_from_now(app, conn, family) -> None:
    with db.transaction(conn):
        wish = wishes.insert(
            conn,
            member_id=family["girls"].id,
            title="Roller skates",
            topic="roller skates",
            occasion=None,
            rank=1,
            now="2026-09-19T18:00:00Z",
        )
        wishes.update(
            conn,
            wish.id,
            {"status": "turned_away", "parent_review": "asked"},
            now="2026-09-19T18:05:00Z",
        )
    client = _in_as(app, "Sam", "sam likes long sentences")  # only a parent may answer
    home = client.get("/").text
    question = re.search(r'<section class="q".*?</section>', home, re.S).group(0)
    assert "the girls asked for Roller skates." in question
    assert 'value="granted">Yes</button>' in question and "Not this time" in question
    assert f'href="/kids?who={family["girls"].id}"' in question
    fields = dict(re.findall(r'name="(csrf|once|kid|back)" value="([^"]*)"', question))
    sent = client.post(f"/wish/{wish.id}/answer", data={**fields, "status": "granted"})
    assert sent.status_code == 302 and sent.headers["Location"] == "/"
    assert wishes.get(conn, wish.id).status == "granted"
    assert "asked for Roller skates" not in client.get("/").text


def test_a_grown_up_signed_in_writes_as_themselves(app, conn, family) -> None:
    home = _in_as(app, "Sam", "sam likes long sentences").get("/").text
    assert 'name="who"' not in _box(home)  # signed in as themselves: nobody else to be
    assert "Finish setting up" in home  # an admin's unfinished setup, each step a link
    row = _row(home)
    assert "Kids" in row and "Lists" in row


def test_a_kid_sees_only_what_is_hers_and_nothing_of_how_it_works(app, conn, family) -> None:
    _task(conn, family, "Feed the fish", due="2026-09-22T19:00:00Z", owner="girls")
    _task(conn, family, "Call the dentist", owner="sam")
    with db.transaction(conn):
        plans.insert(
            conn,
            title="Old hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=ideas.insert(conn, title="Hike", kind="outing", now=NOW_ISO).id,
        )
    kid = _in_as(app, "the girls", "a kid can choose one too")
    home = kid.get("/").text
    assert "Feed the fish" in home and "Call the dentist" not in home  # only her own, all of them
    assert (
        "My to-dos" in home
        and 'aria-label="Mark done: Feed the fish"' in home
        and "todo--mine" in home
    )
    assert "How did Old hike go?" not in home  # her questions reach her chat, not her Now
    # No money, no model, no household pages, no pill, nothing late.
    for hidden in ("spent today", "Finish setting up", "pill-health", "Setup:", "On your plate"):
        assert hidden not in home, hidden
    assert not re.search(r"\blate\b", home)
    assert "Sam and Alex can read this" in home and "20 messages left today." in home
    assert re.findall(r"<a [^>]*>([^<]+)(?:<span|</a>)", _row(home)) == [
        "Now",
        "Do",
        "My week",
        "My list",
    ]


# -- what the page says, in words


def test_the_context_line_is_the_moment_and_one_fact() -> None:
    at = datetime(2026, 10, 9, 17, 2, tzinfo=TZ)
    assert views.context_line(at) == "Friday 5:02\u00a0pm"
    assert (
        views.context_line(at, "dry through Sunday") == "Friday 5:02\u00a0pm · dry through Sunday"
    )


def test_a_days_line_names_what_is_on_in_order_and_links_to_the_day() -> None:
    rows = [{"title": "Dentist", "time": "9\u00a0am"}, {"title": "Swim", "time": "4\u00a0pm"}]
    parts = views.day_line(rows, "/week/2026-09-21")
    assert [p["text"] for p in parts] == ["Dentist 9\u00a0am, then Swim 4\u00a0pm", "."]
    assert parts[0]["href"] == "/week/2026-09-21"
    assert (
        views.day_line([{"title": "Fair", "time": None, "status": "tentative"}], "/x")[0]["text"]
        == "Fair (tentative)"
    )
    assert views.day_line([], "/x") == [{"text": "Free.", "href": None}]


def test_when_a_set_was_chosen_is_said_briefly() -> None:
    now = datetime(2026, 9, 20, 21, 3, tzinfo=ZoneInfo("UTC"))
    assert views.made_words("2026-09-20T20:00:00Z", now, TZ) == "chosen 1\u00a0pm"
    assert views.made_words("2026-09-19T23:30:00Z", now, TZ) == "chosen yesterday"
    assert views.made_words("2026-09-17T23:30:00Z", now, TZ) == "chosen Thu"


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


def test_a_face_is_a_rating_on_the_same_scale_as_the_longer_form() -> None:
    from familydb.web import edits

    assert edits.FACES == {"loved": 9, "ok": 6, "not-great": 3}
