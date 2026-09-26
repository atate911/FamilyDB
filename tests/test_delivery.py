"""A message is answered once and a reply sent once, whatever crashes or fails in between."""

from contextlib import closing

from familydb.channels.base import IncomingMessage
from familydb.delivery import deliver, lease, run_deliveries
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.retry_failed import run_retries
from familydb.pipeline import handle_incoming
from familydb.store import db, messages, plans
from tests.fakes import FakeMessagesAPI, message, text


def test_crashed_received_message_recovers_once_and_preserves_original_date(env):
    with db.transaction(env.conn):
        row = messages.insert_in(
            env.conn,
            channel="telegram",
            channel_update_id="crash",
            chat_id="100",
            member_id=env.member.id,
            text="Tomorrow, save a picnic idea",
            now="2026-09-23T19:00:00Z",
        )
    sent = []
    env.app.senders["telegram"] = lambda *args: sent.append(args)
    api = FakeMessagesAPI(message([text("Saved")]))
    assert run_retries(env.app, api=api) == 1
    assert messages.get(env.conn, row.id).status == "processed"
    assert run_retries(env.app, api=api) == 0
    assert (
        handle_incoming(
            env.app, IncomingMessage("telegram", "crash", "100", "1001", "same"), api=api
        )
        is None
    )
    assert len(sent) == 1
    assert "23 September" in api.requests[0]["messages"][-1]["content"][0]["text"]


def test_active_message_claim_blocks_second_connection_and_expired_claim_recovers(env):
    row = messages.insert_in(
        env.conn,
        channel="console",
        channel_update_id="claim",
        chat_id="c",
        member_id=env.member.id,
        text="hello",
    )
    with lease(env.app, env.conn, row.id) as owned:
        assert owned
        with closing(env.app.connect()) as other, lease(env.app, other, row.id) as second:
            assert not second
        assert run_retries(env.app, api=FakeMessagesAPI()) == 0
    env.conn.execute(
        "UPDATE messages SET claim_token='dead', claim_until='2026-01-01T00:00:00Z' WHERE id=?",
        (row.id,),
    )
    assert run_retries(env.app, api=FakeMessagesAPI(message([text("Recovered")]))) == 1


def test_failed_followup_delivery_retries_without_repeating_job_or_model(env):
    plans.insert(
        env.conn,
        title="Museum",
        start="2026-09-23T10:00:00-07:00",
        end="2026-09-23T12:00:00-07:00",
        all_day=False,
        channel="telegram",
        chat_id="100",
    )
    attempts = []

    def fail(*args):
        attempts.append(args)
        raise ConnectionError("Telegram unavailable")

    env.app.senders["telegram"] = fail
    assert run_follow_ups(env.app) == 1
    assert run_follow_ups(env.app) == 0
    assert len(attempts) == 2
    delivered = []
    env.app.senders["telegram"] = lambda *args: delivered.append(args)
    assert run_deliveries(env.app) == 1
    assert run_deliveries(env.app) == 0
    assert len(delivered) == 1
    assert (
        env.conn.execute("SELECT count(*) FROM messages WHERE direction='out'").fetchone()[0] == 1
    )


def test_normal_reply_uses_same_outbox_and_is_not_sent_twice(env):
    api = FakeMessagesAPI(message([text("Saved")]))
    reply = handle_incoming(
        env.app, IncomingMessage("telegram", "normal", "100", "1001", "hello"), api=api
    )
    assert messages.get(env.conn, reply.out_message_id).delivered_at is None
    sent = []
    env.app.senders["telegram"] = lambda *args: sent.append(args)
    assert deliver(env.app, reply.out_message_id)
    assert not deliver(env.app, reply.out_message_id)
    assert len(sent) == len(api.requests) == 1
