"""Several messages sent one after another, answered together in one turn and one reply."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.pipeline import GATHER_HOLD_SECONDS, answer_gathered, receive, retry_message
from familydb.store import messages
from tests import fakes
from tests.conftest import TZ


def _said(text: str, update: str, user: str = "1001") -> IncomingMessage:
    return IncomingMessage("telegram", update, "chat-1", user, text)


def _user_text(request: dict) -> str:
    """What the person said, as the turn carries it: the block after the date and the rest."""
    blocks = request["messages"][-1]["content"]
    return next(block["text"] for block in blocks if block.get("text", "").startswith("["))


def test_several_messages_in_a_row_are_answered_together(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    burst = [_said("we should go to the coast", "1"), _said("maybe saturday", "2")]
    burst.append(_said("with the girls", "3"))
    kept = [receive(app, one, conn=conn) for one in burst]
    alex = _said("and I'm in", "4", user="1002")  # somebody else in the same chat
    alex_kept = receive(app, alex, conn=conn)
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("The coast on Saturday with the girls: noted.")]),
        fakes.message([fakes.text("Noted, Alex.")]),
    )

    # The first two see a newer one waiting, and leave it to answer them.
    assert answer_gathered(app, burst[0], kept[0], api=api, conn=conn) is None
    assert answer_gathered(app, burst[1], kept[1], api=api, conn=conn) is None
    reply = answer_gathered(app, burst[2], kept[2], api=api, conn=conn)
    assert reply.text == "The coast on Saturday with the girls: noted."
    assert _user_text(api.requests[0]) == (
        "[Sam] we should go to the coast\nmaybe saturday\nwith the girls"
    )
    for message_id in kept:
        assert messages.get(conn, message_id).status == "processed"
    assert messages.get(conn, reply.out_message_id).reply_to == kept[2]

    # Alex's is Alex's own.
    alone = answer_gathered(app, alex, alex_kept, api=api, conn=conn)
    assert alone.text == "Noted, Alex." and _user_text(api.requests[1]) == "[Alex] and I'm in"
    assert len(api.requests) == 2  # one turn for the burst, one for Alex


def test_a_message_waiting_is_kept_from_the_retry_job_until_its_hold_lapses(
    settings, clock, conn, family
) -> None:
    app = App(settings, clock)
    kept = receive(app, _said("hello there", "1"), conn=conn)
    now = utc_iso(clock.now())
    assert messages.pending(conn, max_retries=3, now=now) == []
    # The process that was to answer it stopped: once the hold lapses, the retry job answers it.
    lapsed = clock.now() + timedelta(seconds=settings.gather_seconds + GATHER_HOLD_SECONDS + 1)
    assert [m.id for m in messages.pending(conn, max_retries=3, now=utc_iso(lapsed))] == [kept]
    later = App(settings, FixedClock(lapsed.astimezone(TZ).replace(tzinfo=None), TZ))
    later.senders["telegram"] = lambda chat, text: None
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hello!")]))
    assert retry_message(later, kept, api=api, conn=conn).text == "Hello!"


def test_a_burst_that_fails_is_retried_whole_knowing_what_it_already_did(
    settings, clock, conn, family
) -> None:
    """Folded into the last message as its turn takes them, the earlier ones go with it: one
    retry answers the whole burst, told what its first try already saved."""
    app = App(settings, clock)
    first = receive(app, _said("we should try the ramen place", "1"), conn=conn)
    second = receive(app, _said("the one on Alberta", "2"), conn=conn)
    saved_then_busy = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_1", "add_idea", {"title": "Ramen on Alberta", "kind": "restaurant"}
                )
            ],
            stop_reason="tool_use",
        ),
        fakes.rate_limit_error(),
    )
    failed = answer_gathered(
        app, _said("the one on Alberta", "2"), second, api=saved_then_busy, conn=conn
    )
    assert failed.status == "failed"
    folded = messages.get(conn, first)
    assert folded.status == "processed" and folded.reply_to == second
    pending = messages.pending(conn, max_retries=3, now=utc_iso(clock.now()))
    assert [m.id for m in pending] == [second]  # one message to retry, not two

    app.senders["telegram"] = lambda chat, text: None
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1 Ramen on Alberta.")]))
    assert retry_message(app, second, api=api, conn=conn).text == "Saved #1 Ramen on Alberta."
    sent = api.requests[0]["messages"][-1]["content"]
    said = " ".join(block.get("text", "") for block in sent)
    assert "we should try the ramen place\nthe one on Alberta" in said
    assert "add_idea" in said  # what the first try already did


def test_turns_in_one_chat_wait_for_each_other(settings, clock, conn, family) -> None:
    """A burst answered while the one before it is still being answered would read that one as
    not yet answered, and might do it again: it waits, and reads the reply instead."""
    import threading

    app = App(settings, clock)
    started, go_on = threading.Event(), threading.Event()
    asked: list[str] = []

    class Slow:
        def create(self, **kwargs):
            asked.append(" ".join(b.get("text", "") for b in kwargs["messages"][-1]["content"]))
            if len(asked) == 1:
                started.set()
                assert go_on.wait(10)
                return fakes.message([fakes.text("Booked Luigi's for Friday at 7.")])
            return fakes.message([fakes.text("Told Alex.")])

    api = Slow()
    first = receive(app, _said("book Luigi's Friday 7pm", "1"), conn=conn)
    answering = threading.Thread(
        target=answer_gathered,
        args=(app, _said("book Luigi's Friday 7pm", "1"), first),
        kwargs={"api": api},
    )
    answering.start()
    assert started.wait(10)
    second = receive(app, _said("and tell Alex", "2"), conn=conn)
    later = threading.Thread(
        target=answer_gathered, args=(app, _said("and tell Alex", "2"), second), kwargs={"api": api}
    )
    later.start()
    later.join(timeout=0.5)
    assert later.is_alive() and len(asked) == 1  # waiting for the first turn to finish
    go_on.set()
    answering.join(timeout=10)
    later.join(timeout=10)
    assert len(asked) == 2 and "and tell Alex" in asked[1]
    assert messages.get(conn, second).status == "processed"


def test_a_kid_s_burst_past_the_limit_is_not_answered_by_the_retry_job(
    settings, clock, conn, family
) -> None:
    from familydb.store import db, members
    from tests.conftest import NOW_ISO

    with db.transaction(conn):
        members.add(conn, "Mia", "kid", channel="telegram", channel_user_id="1003", now=NOW_ISO)
    app = App(settings.model_copy(update={"kid_daily_messages": 1}), clock)
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sure.")]))
    one = receive(app, _said("q1", "1", user="1003"), conn=conn)
    assert (
        answer_gathered(app, _said("q1", "1", user="1003"), one, api=api, conn=conn).text == "Sure."
    )
    two = receive(app, _said("q2", "2", user="1003"), conn=conn)
    three = receive(app, _said("q3", "3", user="1003"), conn=conn)
    refused = answer_gathered(app, _said("q3", "3", user="1003"), three, api=api, conn=conn)
    assert refused.status == "failed" and len(api.requests) == 1
    assert messages.get(conn, two).status == "processed"  # folded, with the refusal
    assert messages.pending(conn, max_retries=3, now=utc_iso(clock.now())) == []


def test_a_message_whose_hold_lapsed_is_not_swept_into_a_later_burst(
    settings, clock, conn, family
) -> None:
    app = App(settings, clock)
    old = receive(app, _said("from this morning", "1"), conn=conn)
    from familydb.store import db

    with db.transaction(conn):
        conn.execute(
            "UPDATE messages SET claim_until = '2000-01-01T00:00:00Z' WHERE id = ?", (old,)
        )
    new = receive(app, _said("hello", "2"), conn=conn)
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi.")]))
    answer_gathered(app, _said("hello", "2"), new, api=api, conn=conn)
    sent = " ".join(b.get("text", "") for b in api.requests[0]["messages"][-1]["content"])
    assert "from this morning\nhello" not in sent  # not part of this burst
    assert messages.get(conn, old).status == "received"  # the retry job's


def test_telegram_keeps_each_message_at_once_and_answers_after_the_pause(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.channels.telegram import TelegramChannel
    from tests.test_telegram import _context, _update

    app = App(settings.model_copy(update={"gather_seconds": 1}), clock)
    channel = TelegramChannel(app, token="123456:TEST-TOKEN")
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Both, got it.")]))
    real = answer_gathered
    monkeypatch.setattr(
        "familydb.channels.telegram.answer_gathered",
        lambda application, msg, kept: real(application, msg, kept, api=api),
    )

    async def two_in_a_row() -> list[str]:
        first, first_replies = _update("pizza tonight?", update_id=11)
        second, second_replies = _update("or tacos", update_id=12)
        context, _ = _context()
        await channel.on_message(first, context)  # returns before any answer
        assert first_replies == [] and len(channel._gathering) == 1
        await channel.on_message(second, context)
        await asyncio.gather(*channel._gathering)
        return first_replies + second_replies

    assert asyncio.run(two_in_a_row()) == ["Both, got it."]
    assert _user_text(api.requests[0]) == "[Sam] pizza tonight?\nor tacos"
