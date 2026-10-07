import json
from datetime import datetime

import pytest

from familydb.app import App
from familydb.channels.console import one_shot
from familydb.clock import FixedClock
from familydb.jobs.retry_failed import run_retries
from familydb.jobs.scheduler import build_scheduler
from familydb.pipeline import retry_message
from familydb.store import calls, finds, ideas, messages
from tests import fakes
from tests.conftest import TZ


def _failed_message(app: App, conn, api_error):
    reply = one_shot(
        app, "we should try the ramen place", "Sam", api=fakes.FakeMessagesAPI(api_error)
    )
    assert reply.status == "failed"
    return reply.in_message_id


def test_retry_recovers_and_delivers(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    message_id = _failed_message(app, conn, fakes.rate_limit_error())
    delivered: list[tuple[str, str]] = []
    app.senders["console"] = lambda chat_id, text: delivered.append((chat_id, text))
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved #1 (sorry for the wait).")]),
    )
    reply = retry_message(app, message_id, api=api, conn=conn)
    assert reply.status == "ok"
    stored = messages.get(conn, message_id)
    assert stored.status == "processed" and stored.retries == 1
    assert stored.actions[0]["tool"] == "add_idea"
    assert ideas.get(conn, 1).title == "Ramen place"
    assert delivered == [("console", "Saved #1 (sorry for the wait).")]
    assert retry_message(app, message_id, api=api, conn=conn) is None  # no longer failed


def test_only_one_process_can_take_a_retry(settings, clock, conn, family) -> None:
    """The bot's retry job and `familydb db retry-failed` can both see the same failed row."""
    app = App(settings, clock)
    message_id = _failed_message(app, conn, fakes.rate_limit_error())
    app.senders["console"] = lambda chat_id, text: None

    # Whoever holds the message's lease has it. The other stops there, without paying for a
    # model call: an API with no replies scripted would raise if it were asked for one.
    lost = fakes.FakeMessagesAPI()
    from familydb.delivery import lease

    with lease(app, conn, message_id) as owned:
        assert owned
        assert retry_message(app, message_id, api=lost, conn=conn) is None
    assert lost.requests == []


def test_retries_are_bounded(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"retry_max_attempts": 2}), clock)
    message_id = _failed_message(app, conn, fakes.rate_limit_error())
    assert (
        retry_message(
            app, message_id, api=fakes.FakeMessagesAPI(fakes.server_error()), conn=conn
        ).status
        == "failed"
    )
    assert (
        retry_message(
            app, message_id, api=fakes.FakeMessagesAPI(fakes.server_error()), conn=conn
        ).status
        == "failed"
    )
    assert messages.get(conn, message_id).retries == 2
    assert retry_message(app, message_id, api=fakes.FakeMessagesAPI(), conn=conn) is None
    assert messages.failed(conn, max_retries=2) == []
    assert len(messages.failed(conn)) == 1
    # a retry failure stores no extra notice for the family
    outbound = [
        m
        for m in messages.recent_for_chat(conn, "console", limit=20, since="2026-01-01")
        if m.direction == "out"
    ]
    assert len(outbound) == 1


def test_configuration_errors_are_not_retried(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    message_id = _failed_message(app, conn, fakes.bad_request_error())
    stored = messages.get(conn, message_id)
    assert stored.give_up is True and stored.retries == 0
    assert messages.failed(conn, max_retries=settings.retry_max_attempts) == []
    assert retry_message(app, message_id, api=fakes.FakeMessagesAPI(), conn=conn) is None
    assert messages.reset_retries(conn) == 1
    assert messages.get(conn, message_id).give_up is False
    assert messages.failed(conn, max_retries=settings.retry_max_attempts)[0].id == message_id


def test_run_retries_processes_eligible_messages(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    first = _failed_message(app, conn, fakes.rate_limit_error())
    second = _failed_message(app, conn, fakes.rate_limit_error())
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("one")]), fakes.message([fakes.text("two")])
    )
    assert run_retries(app, api=api) == 2
    assert messages.get(conn, first).status == "processed"
    assert messages.get(conn, second).status == "processed"
    assert run_retries(app, api=fakes.FakeMessagesAPI()) == 0


def test_retry_needs_a_sender_for_chat_channels(settings, clock, conn, family) -> None:
    from familydb.channels.base import IncomingMessage
    from familydb.pipeline import handle_incoming

    app = App(settings, clock)
    inbound = IncomingMessage("telegram", "u1", "chat-1", "1001", "we should go hiking")
    reply = handle_incoming(
        app, inbound, api=fakes.FakeMessagesAPI(fakes.rate_limit_error()), conn=conn
    )
    assert reply.status == "failed"
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved.")]))
    assert retry_message(app, reply.in_message_id, api=api, conn=conn) is None  # no sender here
    assert messages.get(conn, reply.in_message_id).status == "failed"
    assert messages.get(conn, reply.in_message_id).retries == 0
    delivered = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append((chat_id, text))
    assert retry_message(app, reply.in_message_id, api=api, conn=conn).status == "ok"
    assert delivered == [("chat-1", "Saved.")]


def test_retry_tells_the_model_what_already_ran(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    first_attempt = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.rate_limit_error(),  # the reply never came, but the idea was saved
    )
    reply = one_shot(app, "we should try the ramen place", "Sam", api=first_attempt)
    assert reply.status == "failed"
    assert ideas.get(conn, 1).title == "Ramen place"
    retry_api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1.")]))
    assert retry_message(app, reply.in_message_id, api=retry_api, conn=conn).status == "ok"
    request = retry_api.requests[0]["messages"]
    assert [m["role"] for m in request] == ["user"]  # the failure notice is not replayed
    blocks = request[0]["content"]
    assert blocks[1]["text"] == "[Sam] we should try the ramen place"
    assert "add_idea (#1)" in blocks[-1]["text"]
    assert "must not be repeated" in blocks[-1]["text"]


# --- enrichment

from familydb.integrations.geocode import GeoPoint  # noqa: E402
from familydb.jobs.enrich import render_place_note, run_enrichment  # noqa: E402
from familydb.store import db, places  # noqa: E402

POINT = GeoPoint(45.5, -122.6, "Hopscotch", "nominatim")


def _web_app(settings, clock, **extra) -> App:
    configured = settings.model_copy(
        update={
            "web_tools_enabled": True,
            "lookups_when": "asap",
            "home_lat": 45.63,
            "home_lon": -122.67,
            **extra,
        }
    )
    return App(configured, clock, geocoder=fakes.FakeGeocoder(default=POINT))


def _captured_idea(conn, family, title="Hopscotch, Portland", chat_id="-100"):
    with db.transaction(conn):
        inbound = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=f"cap-{title}",
            chat_id=chat_id,
            member_id=family["sam"].id,
            text=f"idea: {title}",
            now="2026-09-20T20:00:00Z",
        )
        return ideas.insert(
            conn,
            title=title,
            kind="outing",
            source_message_id=inbound.id,
            now="2026-09-20T20:00:01Z",
        ), inbound


def test_enrichment_fills_in_an_idea_and_notes_the_chat(settings, clock, conn, family) -> None:
    app = _web_app(settings, clock)
    idea, inbound = _captured_idea(conn, family)
    delivered: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append((chat_id, text))
    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script(
            {
                "idea_id": idea.id,
                "name": "Hopscotch Portland",
                "summary": "Immersive art experience.",
                "hours": [{"day": "sat", "open": "10:00", "close": "20:00"}],
                "closed_days": ["mon"],
                "booking_url": "https://example.com/tickets",
            }
        )
    )
    counts = run_enrichment(app, api=api)
    assert counts == {"done": 1, "skipped": 0, "failed": 0, "deferred": 0}
    stored = ideas.get(conn, idea.id)
    assert stored.enrichment == "done" and stored.place_id is not None
    place = places.get(conn, stored.place_id)
    assert place.travel_minutes is not None and place.hours["mon"] == []
    assert api.requests[0]["messages"][0]["content"][1]["text"].startswith(
        "Idea #1: Hopscotch, Portland"
    )
    assert len(delivered) == 1 and delivered[0][0] == "-100"
    note = delivered[0][1]
    assert note.startswith("Looked up #1 Hopscotch Portland:") and "hours saved for sat" in note
    assert "closed mon" in note and "tickets: https://example.com/tickets" in note
    outbound = [
        m
        for m in messages.recent_for_chat(conn, "-100", limit=10, since="2026-09-01")
        if m.direction == "out"
    ]
    assert outbound[0].reply_to == inbound.id and outbound[0].text == note
    assert run_enrichment(app, api=fakes.FakeMessagesAPI()) == {
        "done": 0,
        "skipped": 0,
        "failed": 0,
        "deferred": 0,
    }


def test_enrichment_skipped_failed_and_deferred(settings, clock, conn, family) -> None:
    app = _web_app(settings, clock)
    picnic, _ = _captured_idea(conn, family, title="A picnic somewhere")
    vague, _ = _captured_idea(conn, family, title="That place")
    third, _ = _captured_idea(conn, family, title="Third idea")
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_skip",
                    "skip_place",
                    {"idea_id": picnic.id, "status": "skipped", "reason": "not a specific place"},
                )
            ],
            stop_reason="tool_use",
        ),  # the hand-back ends the turn: no further call to say "skipped"
        fakes.message([fakes.text("I could not find it, sorry.")]),  # no hand-back
        fakes.rate_limit_error(),
    )
    counts = run_enrichment(app, api=api)
    assert counts == {"done": 0, "skipped": 1, "failed": 1, "deferred": 1}
    assert ideas.get(conn, picnic.id).enrichment == "skipped"
    failed = ideas.get(conn, vague.id)
    assert failed.enrichment == "failed" and failed.enrichment_note == "worker ended without saving"
    assert ideas.get(conn, third.id).enrichment == "pending"  # deferred, still queued
    assert [i.id for i in ideas.pending_enrichment(conn, limit=10)] == [third.id]


def test_enrichment_crash_marks_the_idea_failed_and_continues(settings, clock, conn, family):
    app = _web_app(settings, clock)
    first, _ = _captured_idea(conn, family, title="Crashes")
    second, _ = _captured_idea(conn, family, title="Works")
    api = fakes.FakeMessagesAPI(
        RuntimeError("boom"),
        *fakes.enrich_script({"idea_id": second.id, "name": "Works"}),
    )
    counts = run_enrichment(app, api=api)
    assert counts == {"done": 1, "skipped": 0, "failed": 1, "deferred": 0}
    failed = ideas.get(conn, first.id)
    assert failed.enrichment == "failed" and failed.enrichment_note == "error: RuntimeError: boom"
    assert ideas.get(conn, second.id).enrichment == "done"
    assert ideas.pending_enrichment(conn, limit=10) == []  # nothing left to retry forever


def test_enrichment_note_can_be_turned_off(settings, clock, conn, family) -> None:
    app = _web_app(settings, clock, enrichment_notes=False)
    idea, _ = _captured_idea(conn, family)
    delivered = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append(text)
    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch Portland"})
    )
    assert run_enrichment(app, api=api)["done"] == 1
    assert delivered == []


def test_render_place_note_without_details(settings) -> None:
    from familydb.store.ideas import Idea
    from familydb.store.places import Place

    idea = Idea(
        id=7,
        kind="outing",
        title="X",
        created_at="2026-09-20T00:00:00Z",
        updated_at="2026-09-20T00:00:00Z",
    )
    place = Place(
        id=1, name="Somewhere", created_at="2026-09-20T00:00:00Z", updated_at="2026-09-20T00:00:00Z"
    )
    plain = settings.model_copy(update={"persona": "none"})
    assert render_place_note(idea, place, plain) == "Filled in #7 Somewhere: hours unknown."
    assert render_place_note(idea, place, settings) == "Looked up #7 Somewhere: hours unknown."


def test_home_ideas_with_nothing_to_look_up_are_skipped_without_a_call(
    settings, clock, conn, family
) -> None:
    from familydb.jobs.enrich import NO_LOOKUP_NOTE, needs_lookup

    app = _web_app(settings, clock)
    chores, _ = _captured_idea(conn, family, title="Paint the fence")
    shop, _ = _captured_idea(conn, family, title="New shelves")
    with db.transaction(conn):
        ideas.update(conn, chores.id, {"kind": "home"})
        ideas.update(conn, shop.id, {"kind": "home", "location_name": "IKEA Portland"})
    assert not needs_lookup(ideas.get(conn, chores.id))
    assert needs_lookup(ideas.get(conn, shop.id))  # a named place is still looked up
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("nothing")]))
    counts = run_enrichment(app, api=api, idea_id=chores.id)
    assert counts["skipped"] == 1 and api.requests == []
    skipped = ideas.get(conn, chores.id)
    assert skipped.enrichment == "skipped"
    assert skipped.enrichment_note == NO_LOOKUP_NOTE.format(kind="home")


def test_a_gift_is_looked_up_only_when_it_names_a_place(conn, family) -> None:
    from familydb.jobs.enrich import needs_lookup

    apron, _ = _captured_idea(conn, family, title="A gardening apron")
    pottery, _ = _captured_idea(conn, family, title="A pottery class")
    with db.transaction(conn):
        ideas.update(conn, apron.id, {"kind": "gift", "url": "https://shop.example/apron"})
        ideas.update(conn, pottery.id, {"kind": "gift", "location_name": "Clay Space"})
    assert not needs_lookup(ideas.get(conn, apron.id))  # its link is to the thing, not a place
    assert needs_lookup(ideas.get(conn, pottery.id))


def _openai_app(settings, clock, **extra):
    """An app pointed at another provider, with lookups on."""
    configured = settings.model_copy(
        update={
            "web_tools_enabled": True,
            "lookups_when": "asap",
            "home_lat": 45.63,
            "home_lon": -122.67,
            "provider": "openai",
            "openai_api_key": "sk-test",
            **extra,
        }
    )
    return App(configured, clock, geocoder=fakes.FakeGeocoder(default=POINT))


def test_lookups_work_on_openai_too(settings, clock, conn, family) -> None:
    app = _openai_app(settings, clock)
    idea, _ = _captured_idea(conn, family)
    api = fakes.FakeResponsesAPI(
        *fakes.oa_enrich_script(
            {
                "idea_id": idea.id,
                "name": "Hopscotch Portland",
                "summary": "Immersive art experience.",
                "hours": [{"day": "sat", "open": "10:00", "close": "20:00"}],
                "booking_url": "https://example.com/tickets",
            }
        )
    )
    counts = run_enrichment(app, api=api)
    assert counts == {"done": 1, "skipped": 0, "failed": 0, "deferred": 0}
    stored = ideas.get(conn, idea.id)
    assert stored.enrichment == "done" and stored.place_id is not None
    assert places.get(conn, stored.place_id).booking_url == "https://example.com/tickets"
    # It was asked with the worker model, the hosted search and the two hand-back tools.
    request = api.requests[0]
    assert request["model"] == "gpt-6-luna"
    assert sorted(t.get("name", t["type"]) for t in request["tools"]) == [
        "save_place",
        "skip_place",
        "web_search",
    ]
    assert request["instructions"].startswith("You are the lookup worker")
    assert "Home area" in request["instructions"]  # both system blocks, joined into one string
    assert calls.recent_llm_calls(conn)[0]["served_model"] == "gpt-5"


def test_a_mixed_setup_sends_each_surface_to_its_own_provider(settings, clock, conn, family):
    """Chat on Claude for the writing, the mechanical lookups on OpenAI."""
    app = _openai_app(settings, clock, provider="anthropic", worker_provider="openai")
    idea, _ = _captured_idea(conn, family)
    api = fakes.FakeResponsesAPI(*fakes.oa_enrich_script({"idea_id": idea.id, "name": "Hopscotch"}))
    assert run_enrichment(app, api=api)["done"] == 1
    assert api.requests[0]["model"] == "gpt-6-luna"
    assert app.provider("chat").name == "anthropic"
    assert app.provider("worker").name == "openai"


def test_lookups_work_on_gemini_too(settings, clock, conn, family) -> None:
    app = _openai_app(
        settings, clock, provider="gemini", gemini_api_key="gm-test", openai_api_key=None
    )
    idea, _ = _captured_idea(conn, family)
    api = fakes.FakeGeminiAPI(*fakes.gm_enrich_script({"idea_id": idea.id, "name": "Hopscotch"}))
    assert run_enrichment(app, api=api)["done"] == 1
    assert ideas.get(conn, idea.id).enrichment == "done"
    request = api.requests[0]
    assert request["model"] == "gemini-3.1-flash-lite"
    groups = request["config"]["tools"]
    assert sorted(d["name"] for d in groups[0]["function_declarations"]) == [
        "save_place",
        "skip_place",
    ]
    assert "google_search" in groups[1]  # it can search and hand back in the same turn


def test_scheduler_registers_enrichment_only_with_web_tools(settings, clock) -> None:
    assert build_scheduler(App(settings, clock)).get_job("enrich") is None
    on = settings.model_copy(
        update={"web_tools_enabled": True, "lookups_when": "asap", "enrich_interval_minutes": 4}
    )
    job = build_scheduler(App(on, clock)).get_job("enrich")
    assert job is not None and job.trigger.interval.total_seconds() == 4 * 60


# --- weekend digest

from datetime import timedelta  # noqa: E402

from familydb.channels.web import WebChat  # noqa: E402
from familydb.jobs.weekend_digest import DIGEST_TEXT, digest_channel, run_digest  # noqa: E402
from familydb.store import members, suggestions  # noqa: E402


def _digest_app(settings, clock, chat_id="-100", **extra) -> App:
    return App(settings.model_copy(update={"digest_chat_id": chat_id, **extra}), clock)


def _digest_script(text="Here is what I found."):
    return [
        fakes.message(
            [
                fakes.tool_use(
                    "tu_s",
                    "suggest",
                    {"window": "this_weekend", "question": DIGEST_TEXT, "discover": False},
                )
            ],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text(text)]),
    ]


def test_digest_asks_as_the_first_admin_and_delivers(settings, thursday_clock, conn, family):
    app = _digest_app(settings, thursday_clock)
    delivered: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append((chat_id, text))
    api = fakes.FakeMessagesAPI(*_digest_script())
    reply = run_digest(app, api=api)
    assert reply.status == "ok" and delivered == [("-100", "Here is what I found.")]
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.channel == "telegram" and inbound.chat_id == "-100"
    assert inbound.channel_update_id == "digest:2026-09-24"
    assert inbound.member_id == family["sam"].id and inbound.text == DIGEST_TEXT
    assert inbound.status == "processed"
    # Sent to the family's group, so the turn says who reads it before the question.
    asked = [part["text"] for part in api.requests[0]["messages"][0]["content"]]
    assert asked[1:] == [
        "This is the family's group chat: everyone in it reads your reply, kids among them. "
        "When you have only saved what was asked and have nothing to add, reply with just ✓.",
        f"[Sam] {DIGEST_TEXT}",
    ]
    row = suggestions.list_recent(conn, limit=1)[0]
    assert row.reply_message_id == reply.out_message_id and row.window_start == "2026-09-26"
    # The same day again asks and sends nothing.
    assert run_digest(app, api=api) is None
    assert len(api.requests) == 2 and len(delivered) == 1
    # A week later is a new digest.
    thursday_clock.advance(timedelta(days=7))
    api.queue.extend(_digest_script("Next week's."))
    assert run_digest(app, api=api).status == "ok"
    assert delivered[-1] == ("-100", "Next week's.")


def test_digest_needs_a_chat_id_a_sender_and_an_admin(settings, thursday_clock, conn) -> None:
    api = fakes.FakeMessagesAPI()  # any request would fail the test
    assert run_digest(App(settings, thursday_clock), api=api) is None  # no chat id
    app = _digest_app(settings, thursday_clock)
    assert run_digest(app, api=api) is None  # nothing registered to send to Telegram here
    app.senders["telegram"] = lambda *_: None
    with db.transaction(conn):
        members.add(conn, display_name="Kid", role="kid", now="2026-09-20T00:00:00Z")
    assert run_digest(app, api=api) is None  # no admin to ask as
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0


def test_digest_failure_is_left_for_the_retry_job(settings, thursday_clock, conn, family):
    app = _digest_app(settings, thursday_clock, chat_id="console")
    printed: list[str] = []
    app.senders["console"] = lambda _chat_id, text: printed.append(text)
    reply = run_digest(app, api=fakes.FakeMessagesAPI(fakes.rate_limit_error()))
    assert reply.status == "failed" and printed == []
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.channel == "console" and inbound.status == "failed"
    assert reply.out_message_id is None  # no failure notice for the family
    assert run_retries(app, api=fakes.FakeMessagesAPI(*_digest_script("Late digest."))) == 1
    assert printed == ["Late digest."]
    assert messages.get(conn, inbound.id).status == "processed"
    assert run_digest(app, api=fakes.FakeMessagesAPI()) is None  # still one per day


def test_the_digest_can_go_to_the_web_page(settings, thursday_clock, conn, family) -> None:
    """A Telegram chat id cannot be known before somebody writes in the group; "web" can."""
    assert digest_channel("web") == "web"
    assert digest_channel("console") == "console"
    assert digest_channel("-100") == "telegram"

    app = _digest_app(settings, thursday_clock, chat_id="web")
    chat = WebChat(app)  # registering it is what gives the channel a sender
    assert app.senders["web"] is not None
    reply = run_digest(app, api=fakes.FakeMessagesAPI(*_digest_script()))
    assert reply.status == "ok"
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.channel == "web" and inbound.chat_id == "web"
    # Delivering to the page is storing it, which is where the page reads from.
    thread = messages.last_for_chat(conn, "web", limit=10)
    assert [line.text for line in thread] == [DIGEST_TEXT, "Here is what I found."]
    assert chat.busy("web") is False  # the digest is not a turn the page is waiting on


def test_scheduler_registers_the_digest_only_with_a_chat_id(settings, clock) -> None:
    assert build_scheduler(App(settings, clock)).get_job("weekend_digest") is None
    on = settings.model_copy(
        update={"digest_chat_id": "-100", "digest_day": "fri", "digest_hour": 17}
    )
    job = build_scheduler(App(on, clock)).get_job("weekend_digest")
    assert job is not None and job.misfire_grace_time == 3600
    assert str(job.trigger) == "cron[day_of_week='fri', hour='17']"


# --- follow-ups

from familydb.agent.history import load_history  # noqa: E402
from familydb.jobs.follow_ups import run_follow_ups  # noqa: E402
from familydb.store import outcomes, plans  # noqa: E402
from tests.conftest import NOW_ISO, call  # noqa: E402


def _plan(
    conn, family, *, start, title="Hopscotch", idea_id=None, chat_id="-100", channel="telegram"
):
    with db.transaction(conn):
        return plans.insert(
            conn,
            title=title,
            start=start,
            end=None,
            all_day=True,
            idea_id=idea_id,
            created_by=family["sam"].id,
            channel=channel,
            chat_id=chat_id,
            now="2026-09-18T00:00:00Z",
        )


def test_follow_ups_ask_once_in_the_plans_chat(settings, thursday_clock, conn, family) -> None:
    app = App(settings, thursday_clock)  # Thursday 24 September
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch Portland", kind="outing", now=NOW_ISO)
    done = _plan(conn, family, start="2026-09-19", title="Hopscotch Portland", idea_id=idea.id)
    _plan(conn, family, start="2026-09-26", title="Still to come")
    _plan(conn, family, start="2026-09-10", title="Too long ago")
    _plan(conn, family, start="2026-09-20", title="No chat known", chat_id=None, channel=None)
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: sent.append((chat_id, text))
    assert run_follow_ups(app) == 1
    question = f"How was #{idea.id} Hopscotch Portland on Saturday? Worth doing again?"
    assert sent == [("-100", question)]
    assert plans.get(conn, done.id).followed_up_at is not None
    rows = conn.execute(
        "SELECT channel, chat_id, direction, text, reply_to FROM messages"
    ).fetchall()
    assert [tuple(r) for r in rows] == [("telegram", "-100", "out", question, None)]
    assert run_follow_ups(app) == 0  # asked once
    # The question sits in the chat history, so the family's answer reads as feedback.
    history = load_history(conn, "-100", clock=thursday_clock, limit=10, since_hours=24)
    assert [(h.role, h.text) for h in history] == [("assistant", question)]


def test_follow_ups_skip_answered_plans_and_wait_for_a_sender(
    settings, thursday_clock, conn, family
) -> None:
    app = App(settings, thursday_clock)
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Ramen", kind="restaurant", now=NOW_ISO)
    answered = _plan(conn, family, start="2026-09-19", title="Ramen", idea_id=idea.id)
    waiting = _plan(conn, family, start="2026-09-20", title="Zoo")
    with db.transaction(conn):
        outcomes.insert(
            conn,
            idea_id=idea.id,
            plan_id=None,
            happened_on="2026-09-19",
            rating=9,
            would_repeat=True,
            notes="great",
            recorded_by=family["sam"].id,
            now=NOW_ISO,
        )
    assert run_follow_ups(app) == 0  # no Telegram sender here: the zoo waits
    assert plans.get(conn, answered.id).followed_up_at is not None  # answered: marked silently
    assert plans.get(conn, waiting.id).followed_up_at is None
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0
    app.senders["telegram"] = lambda *_: None
    assert run_follow_ups(app) == 1
    assert plans.get(conn, waiting.id).followed_up_at is not None


def test_external_cancellation_suppresses_followup(env):
    _, created = call(env, "create_event", title="Museum", start="2026-09-26T10:00")
    plans.update(env.conn, created["plan"]["id"], {"channel": "telegram", "chat_id": "100"})
    env.cal.delete_event(created["event"]["id"])
    env.app.clock.advance(timedelta(days=4))
    env.app.senders["telegram"] = lambda *_: pytest.fail("cancelled event must not prompt")
    assert run_follow_ups(env.app) == 0
    assert plans.get(env.conn, created["plan"]["id"]).status == "cancelled"


# --- catch-up after a restart

from familydb.jobs.catch_up import run_catch_up  # noqa: E402


def test_catch_up_sends_a_digest_that_was_due_today(settings, thursday_clock, conn, family):
    app = _digest_app(settings, thursday_clock)  # Thursday 18:00, digest at 18
    delivered: list[str] = []
    app.senders["telegram"] = lambda _chat_id, text: delivered.append(text)
    api = fakes.FakeMessagesAPI(*_digest_script("Catch-up digest."))
    assert run_catch_up(app, api=api) == {"follow_ups": 0, "digest": "ok"}
    assert delivered == ["Catch-up digest."]
    # Already sent today: the next catch-up sends nothing.
    assert run_catch_up(app, api=api) == {"follow_ups": 0, "digest": "skipped"}
    assert len(api.requests) == 2


def test_catch_up_leaves_a_digest_that_is_not_due(settings, thursday_clock, clock, conn, family):
    api = fakes.FakeMessagesAPI()  # any request would fail the test
    later = _digest_app(settings, thursday_clock, digest_hour=19)  # not yet 19:00
    later.senders["telegram"] = lambda *_: None
    assert run_catch_up(later, api=api)["digest"] == "not due"
    sunday = _digest_app(settings, clock)  # the shared clock is a Sunday
    sunday.senders["telegram"] = lambda *_: None
    assert run_catch_up(sunday, api=api)["digest"] == "not due"
    assert run_catch_up(App(settings, thursday_clock), api=api)["digest"] == "not due"  # no id


def test_catch_up_runs_the_follow_ups(settings, thursday_clock, conn, family) -> None:
    app = App(settings, thursday_clock)
    asked: list[str] = []
    app.senders["telegram"] = lambda _chat_id, text: asked.append(text)
    _plan(conn, family, start="2026-09-19", title="Hopscotch")
    assert run_catch_up(app)["follow_ups"] == 1
    assert asked == ["How was Hopscotch on Saturday? Worth doing again?"]


# --- every job


def test_no_job_calls_the_model_when_there_is_nothing_to_do(settings, clock, conn, family) -> None:
    """Every scheduled job must be free when the family is quiet. The API is billed per call."""
    from familydb.jobs.catch_up import run_catch_up
    from familydb.jobs.follow_ups import run_follow_ups
    from familydb.jobs.happening import run_happening

    api = fakes.FakeMessagesAPI()  # any request at all raises "no scripted response left"
    # The weekly search near home is a call the family chose, made when it is due; here it is
    # off, and below it has just run, so nothing is due.
    quiet = _web_app(settings, clock, digest_chat_id="-100", happening_search=False)
    quiet.senders["telegram"] = lambda *_: None

    assert run_retries(quiet, api=api) == 0
    assert run_enrichment(quiet, api=api) == {"done": 0, "skipped": 0, "failed": 0, "deferred": 0}
    assert run_follow_ups(quiet) == 0
    assert run_catch_up(quiet, api=api) == {"follow_ups": 0, "digest": "not due"}
    assert set(run_happening(quiet, api=api).values()) == {0}
    assert api.requests == []

    searched = _web_app(settings, clock, home_area="Vancouver, WA")
    with db.transaction(conn):
        for source, kind in (("web:near-home", "web"), ("proposals:vancouver, wa", "proposals")):
            finds.source_answered(conn, source, kind, ok=True, note="", found=0, at=NOW_ISO)
    assert set(run_happening(searched, api=api).values()) == {0}
    assert api.requests == []

    # An enrichment run with the web off must not even reach for a client.
    off = App(settings, clock)
    assert run_enrichment(off, api=api)["done"] == 0
    assert api.requests == []


def test_a_schedule_on_another_clock_is_a_different_schedule() -> None:
    from zoneinfo import ZoneInfo

    from apscheduler.triggers.cron import CronTrigger

    from familydb.jobs.scheduler import same_schedule

    here = CronTrigger(hour=18, timezone=ZoneInfo("America/Vancouver"))
    again = CronTrigger(hour=18, timezone=ZoneInfo("America/Vancouver"))
    there = CronTrigger(hour=18, timezone=ZoneInfo("Europe/London"))
    assert same_schedule(here, again)
    assert not same_schedule(here, there)


# --- the evening's lookups, and asking for one now


def _evening(app, hour=21, minute=5) -> App:
    """The same app a little after the evening's lookup hour, the same Sunday."""
    later = App(
        app.settings,
        FixedClock(datetime(2026, 9, 20, hour, minute), TZ),
        geocoder=fakes.FakeGeocoder(default=POINT),
    )
    later.senders.update(app.senders)
    return later


def test_lookups_wait_for_the_evening_hour_in_the_family_s_time(settings) -> None:
    from familydb.jobs.enrich import lookups_due_before

    evening = settings.model_copy(update={"lookups_when": "evening", "lookup_hour": 21})
    afternoon = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)
    assert lookups_due_before(evening, afternoon) == "2026-09-20T04:00:00Z"  # last night's, PDT
    assert lookups_due_before(evening, afternoon.replace(hour=21, minute=1)) == (
        "2026-09-21T04:00:00Z"
    )
    assert (
        lookups_due_before(evening.model_copy(update={"lookups_when": "asap"}), afternoon) is None
    )


def test_the_evening_s_lookups_run_together_with_one_note_in_each_chat(
    settings, clock, conn, family
) -> None:
    app = _web_app(settings, clock, lookups_when="evening")
    hopscotch, _ = _captured_idea(conn, family, title="Hopscotch, Portland")
    ramen, _ = _captured_idea(conn, family, title="Ramen Ryoma")
    delivered: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append((chat_id, text))
    # The afternoon they were added: nothing is looked up, nothing asked of a model.
    assert run_enrichment(app, api=fakes.FakeMessagesAPI())["done"] == 0

    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script({"idea_id": hopscotch.id, "name": "Hopscotch", "summary": "Art."}),
        *fakes.enrich_script({"idea_id": ramen.id, "name": "Ramen Ryoma", "closed_days": ["mon"]}),
    )
    assert run_enrichment(_evening(app), api=api)["done"] == 2
    assert len(delivered) == 1 and delivered[0][0] == "-100"
    note = delivered[0][1]
    assert note.startswith("Looked up 2 ideas this evening:")
    assert "• #1 Hopscotch: Art" in note and "• #2 Ramen Ryoma:" in note and "closed mon" in note

    # One added after the hour waits for tomorrow evening's.
    late, _ = _captured_idea(conn, family, title="Late idea")
    with db.transaction(conn):
        conn.execute(
            "UPDATE ideas SET updated_at = '2026-09-21T04:30:00Z' WHERE id = ?", (late.id,)
        )
    assert run_enrichment(_evening(app, 21, 40), api=fakes.FakeMessagesAPI())["done"] == 0


def test_an_idea_asked_for_now_is_looked_up_on_the_next_run_with_a_note_of_its_own(
    settings, clock, conn, family
) -> None:
    from familydb.tools import ToolContext

    app = _web_app(settings, clock, lookups_when="evening")
    idea, _ = _captured_idea(conn, family)
    other, _ = _captured_idea(conn, family, title="Another")
    delivered: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: delivered.append((chat_id, text))
    ctx = ToolContext(conn=conn, settings=app.settings, clock=clock, member=family["sam"])
    asked = app.registry.dispatch("look_up_now", {"idea_ids": [idea.id]}, ctx)
    assert json.loads(asked.content)["asked"] == [idea.id]

    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch", "summary": "Art."})
    )
    assert run_enrichment(app, api=api)["done"] == 1  # the afternoon, before the evening
    assert [text for _, text in delivered] == [delivered[0][1]]
    assert delivered[0][1].startswith("Looked up #1 Hopscotch:")
    assert ideas.get(conn, idea.id).lookup_wanted_at is None
    assert ideas.get(conn, other.id).enrichment == "pending"  # the rest still wait


def test_look_up_now_takes_every_idea_waiting_or_those_named(settings, clock, conn, family):
    from familydb.tools import ToolContext

    app = _web_app(settings, clock)
    waiting, _ = _captured_idea(conn, family, title="Waiting")
    done, _ = _captured_idea(conn, family, title="Done already")
    dropped, _ = _captured_idea(conn, family, title="Dropped")
    with db.transaction(conn):
        ideas.update(conn, done.id, {"enrichment": "done"})
        ideas.update(conn, dropped.id, {"status": "dropped"})
    ctx = ToolContext(conn=conn, settings=app.settings, clock=clock, member=family["sam"])

    every = json.loads(app.registry.dispatch("look_up_now", {}, ctx).content)
    assert every["asked"] == [waiting.id]
    again = json.loads(
        app.registry.dispatch("look_up_now", {"idea_ids": [done.id, 99]}, ctx).content
    )
    assert again == {"asked": [done.id], "unknown": [99], "within_minutes": 2}
    assert ideas.get(conn, done.id).enrichment == "pending"
    off = _web_app(settings, clock, web_tools_enabled=False)
    ctx_off = ToolContext(conn=conn, settings=off.settings, clock=clock, member=family["sam"])
    assert (
        json.loads(off.registry.dispatch("look_up_now", {}, ctx_off).content)["available"] is False
    )


def test_what_she_sends_unasked_is_kept_as_such_and_follow_ups_can_be_switched_off(
    settings, thursday_clock, conn, family
) -> None:
    app = App(settings, thursday_clock)
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch Portland", kind="outing", now=NOW_ISO)
    first = _plan(conn, family, start="2026-09-19", title="Hopscotch Portland", idea_id=idea.id)
    app.senders["telegram"] = lambda chat_id, text: None
    assert run_follow_ups(app) == 1
    assert [row["sent_as"] for row in conn.execute("SELECT sent_as FROM messages")] == ["follow_up"]
    assert plans.get(conn, first.id).followed_up_at is not None

    _plan(conn, family, start="2026-09-20", title="Zoo")
    off = App(settings.model_copy(update={"follow_ups": False}), thursday_clock)
    off.senders["telegram"] = app.senders["telegram"]
    assert run_follow_ups(off) == 0  # nobody is asked


def test_how_a_plan_went_is_asked_of_whoever_made_it(settings, thursday_clock, conn, family):
    """A plan made in the family group: how it went is asked in its maker's own chat, once they
    have written there, so one answer is enough and the rest of the group is not buzzed."""
    app = App(settings, thursday_clock)
    with db.transaction(conn):
        messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="dm",
            chat_id="1001",
            member_id=family["sam"].id,
            text="/start",
            now="2026-09-01T00:00:00Z",
        )
    _plan(conn, family, start="2026-09-19", title="Hopscotch Portland")
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat_id, text: sent.append((chat_id, text))
    assert run_follow_ups(app) == 1
    assert [chat for chat, _ in sent] == ["1001"]
