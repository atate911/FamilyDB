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
    assert messages.get(conn, message_id).retries == settings.retry_max_attempts
    assert retry_message(app, message_id, api=fakes.FakeMessagesAPI(), conn=conn) is None
    assert messages.reset_retries(conn) == 1
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
