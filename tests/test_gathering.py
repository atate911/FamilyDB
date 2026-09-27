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


def test_when_the_turn_fails_the_earlier_ones_are_left_for_the_retry_job(
    settings, clock, conn, family
) -> None:
    app = App(settings, clock)
    first = receive(app, _said("one", "1"), conn=conn)
    second = receive(app, _said("two", "2"), conn=conn)
    api = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    assert answer_gathered(app, _said("two", "2"), second, api=api, conn=conn).status == "failed"
    waiting = messages.get(conn, first)
    assert waiting.status == "received" and waiting.claim_token is None  # the retry job's now
    assert {m.id for m in messages.pending(conn, max_retries=3, now=utc_iso(clock.now()))} == {
        first,
        second,
    }


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
