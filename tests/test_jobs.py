from familydb.app import App
from familydb.channels.console import one_shot
from familydb.jobs.retry_failed import run_retries
from familydb.jobs.scheduler import build_scheduler
from familydb.pipeline import retry_message
from familydb.store import ideas, messages
from tests import fakes


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


def test_scheduler_registers_the_retry_job(settings, clock) -> None:
    app = App(settings.model_copy(update={"retry_interval_minutes": 7}), clock)
    scheduler = build_scheduler(app)
    job = scheduler.get_job("retry_failed")
    assert job is not None
    assert job.trigger.interval.total_seconds() == 7 * 60


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
    assert "add_idea (#1)" in blocks[2]["text"]
    assert "must not be repeated" in blocks[2]["text"]


# --- enrichment ---------------------------------------------------------------------------------

from familydb.integrations.geocode import GeoPoint  # noqa: E402
from familydb.jobs.enrich import render_place_note, run_enrichment  # noqa: E402
from familydb.store import db, places  # noqa: E402

POINT = GeoPoint(45.5, -122.6, "Hopscotch", "nominatim")


def _web_app(settings, clock, **extra) -> App:
    configured = settings.model_copy(
        update={"web_tools_enabled": True, "home_lat": 45.63, "home_lon": -122.67, **extra}
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
    assert note.startswith("Filled in #1 Hopscotch Portland:") and "hours saved for sat" in note
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
        ),
        fakes.message([fakes.text("Skipped.")]),
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


def test_enrichment_is_a_noop_without_web_tools(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    _captured_idea(conn, family)
    api = fakes.FakeMessagesAPI()
    assert run_enrichment(app, api=api)["done"] == 0
    assert api.requests == []


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


def test_render_place_note_without_details() -> None:
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
    assert render_place_note(idea, place) == "Filled in #7 Somewhere: · hours unknown"


def test_scheduler_registers_enrichment_only_with_web_tools(settings, clock) -> None:
    assert build_scheduler(App(settings, clock)).get_job("enrich") is None
    on = settings.model_copy(update={"web_tools_enabled": True, "enrich_interval_minutes": 4})
    job = build_scheduler(App(on, clock)).get_job("enrich")
    assert job is not None and job.trigger.interval.total_seconds() == 4 * 60
