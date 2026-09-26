"""What the family tells the bot about itself: kept by `remember`, chosen for each message by code,
and forgotten for good when the family says so (docs/MEMORY.md)."""

from __future__ import annotations

import json
import re

import pytest

from familydb import memory
from familydb.agent.render import render_memories
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
from familydb.store import db, memories, messages
from familydb.tools import ToolContext, ToolRegistry
from tests import fakes
from tests.conftest import NOW_ISO

VEGETARIAN = {"action": "add", "about": "the girls", "category": "food", "fact": "vegetarian"}


def _call(registry: ToolRegistry, ctx: ToolContext, **payload):
    result = registry.dispatch("remember", payload, ctx)
    return result, json.loads(result.content)


@pytest.fixture
def said(ctx) -> ToolContext:
    """A tool context for a turn answering a message, as the chat's is."""
    with db.transaction(ctx.conn):
        inbound = messages.insert_in(
            ctx.conn,
            channel="telegram",
            channel_update_id="m1",
            chat_id="chat-1",
            member_id=ctx.member.id,
            text="the girls are vegetarian now",
            now=NOW_ISO,
        )
    ctx.message_id = inbound.id
    return ctx


# -- the tool ------------------------------------------------------------------------------------


def test_a_memory_is_kept_with_where_it_came_from(registry, said, family) -> None:
    result, data = _call(registry, said, changes=[{**VEGETARIAN, "firm": True}])
    assert not result.is_error
    done = data["remembered"][0]
    assert done["result"] == "saved" and done["about"] == "the girls"
    kept = memories.get(said.conn, done["id"])
    assert kept.member_id == family["girls"].id and kept.category == "food" and kept.firm
    assert kept.source_message_id == said.message_id and kept.said_by_name == "Sam"
    assert kept.source_text == "the girls are vegetarian now"


def test_said_again_is_not_kept_twice_and_a_guess_said_outright_stops_being_one(
    registry, said
) -> None:
    _, first = _call(registry, said, changes=[{**VEGETARIAN, "inferred": True, "firm": True}])
    guess = memories.get(said.conn, first["remembered"][0]["id"])
    assert guess.inferred and not guess.firm  # a guess never rules anything out
    _, again = _call(registry, said, changes=[{**VEGETARIAN, "fact": "Vegetarian!", "firm": True}])
    assert again["remembered"][0] == {**first["remembered"][0], "result": "already remembered"}
    now = memories.get(said.conn, guess.id)
    assert not now.inferred and now.firm
    assert len(memories.active(said.conn, today=said.clock.today())) == 1


def test_the_same_thing_about_two_people_is_two_memories(registry, said) -> None:
    _call(registry, said, changes=[VEGETARIAN, {**VEGETARIAN, "about": "Alex"}])
    _call(registry, said, changes=[{**VEGETARIAN, "about": "family"}])
    about = sorted(
        m.about_name or "family" for m in memories.active(said.conn, today=said.clock.today())
    )
    assert about == ["Alex", "family", "the girls"]


@pytest.mark.parametrize(
    ("change", "complaint"),
    [
        ({**VEGETARIAN, "about": "Grandpa"}, "no family member called 'Grandpa'"),
        ({**VEGETARIAN, "fact": "   "}, "needs the fact itself"),
        ({**VEGETARIAN, "fact": "x" * 201}, "under 200 characters"),
        ({**VEGETARIAN, "until": "2026-09-01"}, "has already passed"),
        ({"action": "forget"}, "needs the m number"),
        ({"action": "replace", "id": 99, "fact": "pescatarian"}, "no memory m99"),
    ],
)
def test_changes_that_cannot_be_are_refused_and_nothing_is_kept(
    registry, said, change, complaint
) -> None:
    result, data = _call(registry, said, changes=[VEGETARIAN, change])
    assert result.is_error and complaint in data["error"]
    assert memories.list_all(said.conn) == []  # all of a call, or none of it


def test_at_most_five_changes_at_once(registry, said) -> None:
    result, data = _call(registry, said, changes=[VEGETARIAN] * 6)
    assert result.is_error and "at most 5" in data["error"]


def test_a_correction_replaces_rather_than_piles_up(registry, said) -> None:
    _, first = _call(registry, said, changes=[VEGETARIAN])
    old = first["remembered"][0]["id"]
    _, data = _call(
        registry,
        said,
        changes=[{**VEGETARIAN, "action": "replace", "id": old, "fact": "eats fish again"}],
    )
    new = data["remembered"][0]
    assert new["result"] == "replaced" and new["was"] == "vegetarian"
    assert memories.get(said.conn, old).status == "replaced"
    assert memories.get(said.conn, old).replaced_by == new["id"]
    live = memories.active(said.conn, today=said.clock.today())
    assert [m.fact for m in live] == ["eats fish again"]
    result, data = _call(registry, said, changes=[{"action": "replace", "id": old, "fact": "x"}])
    assert result.is_error and "is replaced" in data["error"]


def test_what_was_forgotten_does_not_come_back_from_a_conversation(registry, said) -> None:
    _, first = _call(registry, said, changes=[VEGETARIAN])
    kept = first["remembered"][0]["id"]
    _, data = _call(registry, said, changes=[{"action": "forget", "id": kept}])
    assert data["remembered"][0]["result"] == "forgotten"
    gone = memories.get(said.conn, kept)
    assert gone.status == "forgotten" and gone.forgotten_by_name == "Sam"
    # Said again in a later turn, or drawn from the history: not saved, and the model is told.
    result, data = _call(registry, said, changes=[VEGETARIAN], reply="Noted!")
    assert not result.is_error
    refused = data["remembered"][0]
    assert refused["result"] == "not saved" and "asked to forget" in refused["why"]
    assert said.take_reply() is None  # a reply that says "noted" would not be true
    assert memories.active(said.conn, today=said.clock.today()) == []


def test_a_person_on_the_page_can_have_it_remembered_again(registry, said) -> None:
    _, first = _call(registry, said, changes=[VEGETARIAN])
    _call(registry, said, changes=[{"action": "forget", "id": first["remembered"][0]["id"]}])
    said.message_id = None  # typed on the memory page: a person, with no message behind it
    _, data = _call(registry, said, changes=[VEGETARIAN])
    assert data["remembered"][0]["result"] == "saved"


def test_a_reply_is_offered_only_when_everything_was_kept(registry, said) -> None:
    _call(registry, said, changes=[VEGETARIAN], reply="  Noted: the girls are vegetarian.  ")
    assert said.take_reply() == "Noted: the girls are vegetarian."
    assert said.take_reply() is None  # taken once


# -- the turn ------------------------------------------------------------------------------------


def _telegram(text: str, update_id: str) -> IncomingMessage:
    return IncomingMessage("telegram", update_id, "chat-1", "1001", text)


def _remember(reply: str | None = "Noted: the girls are vegetarian now. 🥦", **extra):
    return fakes.tool_use("tu_r", "remember", {"changes": [VEGETARIAN], "reply": reply, **extra})


def test_remembering_alone_costs_one_call(settings, clock, conn, family) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([_remember()], stop_reason="tool_use"))
    reply = handle_incoming(
        App(settings, clock), _telegram("fyi the girls are vegetarian now", "1"), api=api, conn=conn
    )
    assert reply.status == "ok" and reply.text == "Noted: the girls are vegetarian now. 🥦"
    assert len(api.requests) == 1  # no second call just to say "noted"
    assert reply.actions == [{"tool": "remember", "ok": True}]
    assert [m.fact for m in memories.active(conn, today=clock.today())] == ["vegetarian"]
    assert messages.get(conn, reply.out_message_id).text == reply.text


def test_remembering_beside_anything_else_lets_the_model_answer(settings, clock, conn, family):
    idea = fakes.tool_use("tu_i", "add_idea", {"title": "Veggie Grill", "kind": "restaurant"})
    api = fakes.FakeMessagesAPI(
        fakes.message([_remember(), idea], stop_reason="tool_use"),
        fakes.message([fakes.text("Noted, and saved #1 Veggie Grill.")]),
    )
    reply = handle_incoming(
        App(settings, clock),
        _telegram("the girls are vegetarian now, let's try Veggie Grill", "2"),
        api=api,
        conn=conn,
    )
    assert reply.text == "Noted, and saved #1 Veggie Grill." and len(api.requests) == 2


def test_a_memory_that_was_not_kept_goes_back_to_the_model(settings, clock, conn, family):
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_r", "remember", {"changes": [{**VEGETARIAN, "about": "Zed"}]})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Who is Zed?")]),
    )
    reply = handle_incoming(
        App(settings, clock), _telegram("Zed is vegetarian", "3"), api=api, conn=conn
    )
    assert reply.text == "Who is Zed?" and len(api.requests) == 2


def test_what_is_remembered_goes_with_the_message_never_in_the_cached_part(
    settings, clock, conn, family
) -> None:
    with db.transaction(conn):
        memories.insert(
            conn,
            member_id=family["girls"].id,
            category="food",
            fact="allergic to kiwi",
            firm=True,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=family["sam"].id,
            now=NOW_ISO,
        )
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sushi Hana, then: no kiwi there.")]))
    handle_incoming(
        App(settings, clock), _telegram("where should we eat?", "4"), api=api, conn=conn
    )
    sent = api.requests[0]
    assert "kiwi" not in json.dumps(sent["system"])
    parts = [part["text"] for part in sent["messages"][-1]["content"]]
    assert parts[-1] == (
        "What the family has told you about itself (m numbers are for remember):\n"
        "- m1 the girls: allergic to kiwi (must)"
    )


# -- choosing what a message needs ---------------------------------------------------------------


def _keep(conn, fact, *, member_id=None, category="other", firm=False, until=None, inferred=False):
    with db.transaction(conn):
        return memories.insert(
            conn,
            member_id=member_id,
            category=category,
            fact=fact,
            firm=firm,
            inferred=inferred,
            until=until,
            source_message_id=None,
            said_by=None,
            now=NOW_ISO,
        )


def test_every_firm_one_goes_however_little_room_there_is(conn, clock, family) -> None:
    allergy = _keep(conn, "allergic to peanuts", member_id=family["alex"].id, firm=True)
    sushi = _keep(conn, "loves sushi", member_id=family["sam"].id, category="food")
    chosen = memory.choose(
        conn, "anything on tonight?", sender_id=None, today=clock.today(), budget=0
    )
    assert [m.id for m in chosen.memories] == [allergy.id] and chosen.left_out == 1
    everything = memory.choose(conn, "anything on tonight?", sender_id=None, today=clock.today())
    assert [m.id for m in everything.memories] == [allergy.id, sushi.id]


def test_with_too_many_to_send_the_ones_that_bear_on_the_message_go(conn, clock, family) -> None:
    sam, alex = family["sam"].id, family["alex"].id
    jazz = _keep(conn, "likes live jazz", member_id=alex, category="activities")
    sushi = _keep(conn, "loves sushi", member_id=sam, category="food")
    early = _keep(conn, "early riser", member_id=alex, category="routine")
    room = max(len(memory.line_of(m)) for m in (jazz, sushi, early))  # room for one

    def chosen(text, sender=sam):
        found = memory.choose(conn, text, sender_id=sender, today=clock.today(), budget=room)
        assert found.left_out == 2
        return [m.id for m in found.memories]

    assert chosen("any good sushi places?") == [sushi.id]  # a word in common
    assert chosen("somewhere with live jazz tonight") == [jazz.id]
    assert chosen("what's for dinner?") == [sushi.id]  # food, though it names none
    assert chosen("are we up early on friday?", sender=alex) == [early.id]
    # Nothing bears on it: about whoever is asking, then the newest.
    assert chosen("hello", sender=alex) == [early.id]


def test_what_has_run_its_course_is_not_sent(conn, clock, family) -> None:
    _keep(conn, "no long drives", until="2026-09-19", firm=True)  # yesterday
    still = _keep(conn, "no stairs", until="2026-09-20", firm=True)  # today is its last day
    chosen = memory.choose(conn, "hi", sender_id=None, today=clock.today())
    assert [m.id for m in chosen.memories] == [still.id] and chosen.left_out == 0


def test_how_a_memory_is_told(conn, clock, family) -> None:
    _keep(conn, "vegetarian", member_id=family["girls"].id, firm=True)
    _keep(conn, "might like opera", member_id=family["alex"].id, inferred=True)
    _keep(conn, "no hiking", until="2026-10-31")
    shown = render_memories(memory.choose(conn, "hi", sender_id=None, today=clock.today()))
    assert shown.splitlines()[1:] == [
        "- m1 the girls: vegetarian (must)",
        "- m2 Alex: might like opera (a guess)",
        "- m3 family: no hiking (until 2026-10-31)",
    ]
    assert render_memories(memory.Chosen([], 0)) is None
    one = memory.choose(conn, "hi", sender_id=None, today=clock.today(), budget=0)
    assert render_memories(one).endswith("(2 more, on other things.)")


# -- the page ------------------------------------------------------------------------------------

PASSWORD = "open sesame please"


def _page(settings, clock):
    from familydb.web import create_app

    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def _form(client) -> dict[str, str]:
    page = client.get("/memory").text
    csrf = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
    once = re.search(r'name="once" value="([^"]+)"', page).group(1)
    return {"csrf": csrf, "once": once}


def test_the_page_shows_what_is_remembered_and_where_it_came_from(
    settings, clock, conn, family, registry
) -> None:
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    with db.transaction(conn):
        inbound = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="m9",
            chat_id="chat-1",
            member_id=family["sam"].id,
            text="(voice note) so the girls are vegetarian now, no more burger places",
            now=NOW_ISO,
        )
    ctx.message_id = inbound.id
    _call(registry, ctx, changes=[{**VEGETARIAN, "firm": True}])
    page = _page(settings, clock).get("/memory")
    assert page.status_code == 200
    text = page.text
    assert "What Vera remembers" in text and "the girls" in text
    assert "<strong>vegetarian</strong>" in text and ">must<" in text
    assert "Sam, Sunday 20 September, in a voice note" in text
    assert "so the girls are vegetarian now" in text and "(voice note)" not in text
    assert 'href="/memory"' in text  # in the bar, for everybody signed in


def test_remembering_and_forgetting_from_the_page(settings, clock, conn, family) -> None:
    client = _page(settings, clock)
    empty = client.get("/memory").text
    assert "Nothing yet." in empty
    sent = client.post(
        "/memory/new",
        data={
            **_form(client),
            "fact": "allergic to peanuts",
            "about": "Alex",
            "category": "health",
            "firm": "yes",
        },
    )
    assert sent.status_code == 302 and sent.headers["Location"] == "/memory"
    kept = memories.active(conn, today=clock.today())
    assert [(m.fact, m.about_name, m.category, m.firm) for m in kept] == [
        ("allergic to peanuts", "Alex", "health", True)
    ]
    assert kept[0].source_message_id is None
    shown = client.get("/memory").text
    assert "Remembered: allergic to peanuts." in shown
    assert "Added on this page, Sunday 20 September" in shown  # the family's shared password
    client.post(f"/memory/{kept[0].id}/forget", data=_form(client))
    after = client.get("/memory").text
    assert "Forgotten: allergic to peanuts." in after
    assert memories.get(conn, kept[0].id).status == "forgotten"
    assert "Forgotten</span>" in after  # listed under Forgotten, not remembered


def test_the_page_refuses_a_fact_left_empty_and_a_post_from_elsewhere(
    settings, clock, conn, family
) -> None:
    client = _page(settings, clock)
    client.post("/memory/new", data={**_form(client), "fact": "  "})
    assert "Say what to remember." in client.get("/memory").text
    client.post("/memory/new", data={"fact": "likes jazz"})  # no token
    assert memories.list_all(conn) == []


def test_a_long_message_is_quoted_where_the_memory_is() -> None:
    from familydb.web.views import excerpt

    said = (
        "ok so a couple of things, first the soccer schedule changed again and practice is "
        "on Thursdays now, and the dentist moved, and oh Alex is allergic to shellfish "
        "apparently, so we need to watch that at restaurants, and the lantern festival is on "
        "the seventeenth"
    )
    quoted = excerpt(said, "allergic to shellfish", room=80)
    assert "allergic to shellfish" in quoted and len(quoted) <= 82
    assert quoted.startswith("…") and quoted.endswith("…")
    assert excerpt("short and sweet", "sweet") == "short and sweet"
