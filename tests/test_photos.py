"""Photos: looked at by the lookup model through the gateway, written down, then answered as if
typed. The picture is never kept."""

from __future__ import annotations

import asyncio
import base64
from types import SimpleNamespace

import pytest
from telegram import Bot, Update

from familydb import voice
from familydb.agent import gateway
from familydb.agent.providers import LOOK_TOKENS, Picture, build, lookers
from familydb.agent.spending import SpendingLimitReached
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage, PhotoNote
from familydb.channels.telegram import LONGEST, TelegramChannel, picture
from familydb.pipeline import MAX_PHOTO_BYTES, handle_incoming, retry_message
from familydb.store import messages
from familydb.store.db import transaction
from tests import fakes
from tests.conftest import NOW_ISO
from tests.test_telegram import TOKEN, _context, _takers, _telegram

POSTER = "A poster for the Night Market: Sat 3 Oct, 5-10pm, Zidell Yards. Free entry."
JPEG = b"\xff\xd8\xff\xe0-not-really-a-photo"


def _photo(update_id="p1", *, user_id="1001", caption="", fetched=None, size=None, data=JPEG):
    def fetch() -> bytes:
        if fetched is not None:
            fetched.append(update_id)
        return data

    note = PhotoNote(mime="image/jpeg", fetch=fetch, size=size)
    return IncomingMessage("telegram", update_id, "chat-1", user_id, caption, photo=note)


def _kinds(conn) -> list[str]:
    return [row[0] for row in conn.execute("SELECT kind FROM llm_calls ORDER BY id")]


def _eyes(seen: str = POSTER) -> fakes.FakeMessagesAPI:
    return fakes.FakeMessagesAPI(fakes.message([fakes.text(seen)], model="claude-haiku-4-5"))


# -- the pipeline --------------------------------------------------------------------------------


def test_a_photo_is_looked_at_then_answered_like_words(settings, clock, conn, family) -> None:
    eyes = _eyes()
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1 Night Market, Sat 3 Oct.")]))
    note = _photo(caption="we should go to this")
    reply = handle_incoming(App(settings, clock), note, api=api, conn=conn, seeing=eyes)

    assert reply.status == "ok" and reply.text == "Saved #1 Night Market, Sat 3 Oct."
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.text == f"(photo) {POSTER}\n\nwe should go to this"
    # The lookup model, with a lookup's budget, sent the picture and then what to write down.
    sent = eyes.requests[0]
    assert sent["model"] == "claude-haiku-4-5" and sent["max_tokens"] == LOOK_TOKENS
    image, ask = sent["messages"][0]["content"]
    assert image["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": base64.b64encode(JPEG).decode("ascii"),
    }
    assert ask["text"].startswith("Write down what this picture shows")
    assert ask["text"].endswith("Names: Sam, Alex, the girls, Vera.")  # spelled their way
    assert "tools" not in sent and "system" not in sent
    said = api.requests[0]["messages"][0]["content"][1]["text"]
    assert said == f"[Sam] (photo) {POSTER}\n\nwe should go to this"
    # Looking is a model call like any other: recorded under its own kind, first, and costed.
    assert _kinds(conn) == ["look", "chat"]
    looked = conn.execute("SELECT * FROM llm_calls WHERE kind = 'look'").fetchone()
    assert looked["message_id"] == inbound.id and looked["provider"] == "anthropic"
    assert looked["cost_usd"] > 0 and not looked["cost_estimated"]
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0
    assert gateway.purpose("look") == "reading photos"


def test_a_stranger_s_photo_is_never_even_fetched(settings, clock, conn, family) -> None:
    fetched: list[str] = []
    eyes = _eyes()
    note = _photo(user_id="5555", fetched=fetched)
    reply = handle_incoming(
        App(settings, clock), note, api=fakes.FakeMessagesAPI(), conn=conn, seeing=eyes
    )
    assert reply.status == "unknown_sender"
    assert fetched == [] and eyes.requests == [] and _kinds(conn) == []


def test_with_photos_off_nothing_is_looked_at_and_words_are_still_answered(
    settings, clock, conn, family
) -> None:
    off = settings.model_copy(update={"photos": False})
    fetched: list[str] = []
    bare = handle_incoming(
        App(off, clock), _photo(fetched=fetched), api=fakes.FakeMessagesAPI(), conn=conn
    )
    assert bare.status == "failed" and bare.text == voice.say(off, "photo_off")
    assert messages.get(conn, bare.in_message_id).give_up
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1 Night Market.")]))
    worded = _photo("p2", caption="night market on the 3rd", fetched=fetched)
    reply = handle_incoming(App(off, clock), worded, api=api, conn=conn)
    assert reply.status == "ok" and fetched == [] and _kinds(conn) == ["chat"]
    assert messages.get(conn, reply.in_message_id).text == (
        "(with a photo, not seen) night market on the 3rd"
    )


@pytest.mark.parametrize(
    ("note", "event"),
    [
        (_photo(size=MAX_PHOTO_BYTES + 1), "photo_too_large"),
        (_photo(data=b"x" * (MAX_PHOTO_BYTES + 1)), "photo_too_large"),
    ],
)
def test_a_photo_too_large_is_not_looked_at(settings, clock, conn, family, note, event) -> None:
    eyes = _eyes()
    reply = handle_incoming(
        App(settings, clock), note, api=fakes.FakeMessagesAPI(), conn=conn, seeing=eyes
    )
    assert reply.status == "failed" and reply.text == voice.say(settings, event)
    assert eyes.requests == [] and _kinds(conn) == []
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.give_up and inbound.text == messages.UNLOOKED
    assert messages.pending(conn, max_retries=3, now=NOW_ISO) == []  # nothing left to retry


def test_a_photo_that_could_not_be_looked_at_is_given_up_and_says_so(
    settings, clock, conn, family
) -> None:
    eyes = fakes.FakeMessagesAPI(fakes.bad_request_error())
    reply = handle_incoming(
        App(settings, clock), _photo(), api=fakes.FakeMessagesAPI(), conn=conn, seeing=eyes
    )
    assert reply.status == "failed" and reply.text == voice.say(settings, "photo_unseen")
    assert messages.get(conn, reply.in_message_id).give_up
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0  # given back


def test_the_day_s_limit_spent_stops_a_photo_before_it_is_sent(
    settings, clock, conn, family, monkeypatch
) -> None:
    def spent(*_args, **_kwargs):
        raise SpendingLimitReached(2.1, 2.0)

    monkeypatch.setattr("familydb.agent.spending.admit", spent)
    eyes = _eyes()
    reply = handle_incoming(
        App(settings, clock), _photo(), api=fakes.FakeMessagesAPI(), conn=conn, seeing=eyes
    )
    assert reply.text == voice.say(settings, "limit_reached", limit="2.00")
    assert eyes.requests == []


def test_a_photo_the_process_stopped_before_looking_at_is_given_up_on_retry(
    settings, clock, conn, family
) -> None:
    """Stored, and then the process stopped: the picture is not kept, so there is nothing to look
    at again, and the family are told."""
    app = App(settings, clock)
    app.senders["telegram"] = lambda _chat, _text: None
    with transaction(conn):
        stored = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="p9",
            chat_id="chat-1",
            member_id=family["sam"].id,
            text=messages.UNLOOKED,
            now=NOW_ISO,
        )
    reply = retry_message(app, stored.id, api=fakes.FakeMessagesAPI(), conn=conn)
    assert reply.text == voice.say(settings, "photo_unseen")
    assert messages.get(conn, stored.id).give_up


# -- who looks, and what each is sent ------------------------------------------------------------


def test_the_company_that_looks_things_up_looks(settings, monkeypatch) -> None:
    both = settings.model_copy(
        update={
            "openai_api_key": "sk-test",
            "worker_provider": "openai",
            "provider_fallback": False,
        }
    )
    assert [provider.name for provider in lookers(both)] == ["openai"]
    alone = settings.model_copy(update={"worker_provider": "openai", "provider_fallback": False})
    assert [provider.name for provider in lookers(alone)] == ["anthropic"]  # the one with a key
    spare = both.model_copy(update={"provider_fallback": True})
    assert [provider.name for provider in lookers(spare)] == ["openai", "anthropic"]
    # Claude's SDK also finds credentials the settings never see; with none anywhere, nobody.
    monkeypatch.setattr(
        "familydb.agent.providers.anthropic.AnthropicProvider.configured", lambda self: False
    )
    nobody = settings.model_copy(update={"openai_api_key": "", "gemini_api_key": ""})
    assert lookers(nobody) == [] and not gateway.can_look(nobody)


def test_openai_is_sent_the_photo_as_a_data_url(settings) -> None:
    eyes = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text(POSTER)], model="gpt-6-luna"))
    provider = build("openai", settings.model_copy(update={"openai_api_key": "k"}), api=eyes)
    seen = provider.describe(Picture(data=JPEG, mime="image/jpeg"), "Write it down.")
    assert seen.text == POSTER and seen.usage["output_tokens"] == 10
    sent = eyes.requests[0]
    assert sent["model"] == "gpt-6-luna" and sent["max_output_tokens"] == LOOK_TOKENS
    assert "tools" not in sent and "instructions" not in sent and sent["store"] is False
    image, ask = sent["input"][0]["content"]
    encoded = base64.b64encode(JPEG).decode("ascii")
    assert image == {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"}
    assert ask == {"type": "input_text", "text": "Write it down."}


def test_gemini_is_sent_the_photo_itself(settings) -> None:
    eyes = fakes.FakeGeminiAPI(fakes.gm_response([fakes.gm_text(POSTER)]))
    provider = build("gemini", settings.model_copy(update={"gemini_api_key": "k"}), api=eyes)
    seen = provider.describe(Picture(data=JPEG, mime="image/png"), "Write it down.")
    assert seen.text == POSTER
    sent = eyes.requests[0]
    assert sent["model"] == "gemini-3.1-flash-lite"
    image, ask = sent["contents"][0]["parts"]
    assert image == {"inline_data": {"mime_type": "image/png", "data": JPEG}}
    assert ask == {"text": "Write it down."}
    assert sent["config"]["max_output_tokens"] == LOOK_TOKENS


def test_a_vendor_that_will_not_describe_it_is_not_taken_at_its_word(settings) -> None:
    from familydb.errors import AgentError

    refused = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_refusal()]))
    provider = build("openai", settings.model_copy(update={"openai_api_key": "k"}), api=refused)
    with pytest.raises(AgentError, match="would not describe it"):
        provider.describe(Picture(data=JPEG, mime="image/jpeg"), "Write it down.")


# -- on Telegram ---------------------------------------------------------------------------------


def _sizes(*sides: tuple[int, int]):
    return [
        SimpleNamespace(width=w, height=h, file_size=w * h // 10, file_id=f"{w}x{h}")
        for w, h in sides
    ]


def test_a_photo_is_fetched_at_a_size_enough_for_its_words() -> None:
    sizes = _sizes((90, 67), (320, 240), (800, 600), (1280, 960), (2560, 1920))
    chosen, kind, size = picture(SimpleNamespace(photo=sizes))
    assert (chosen.width, kind, size) == (1280, "image/jpeg", 1280 * 960 // 10)
    assert max(chosen.width, chosen.height) <= LONGEST
    # Only a huge one: the smallest there is, rather than nothing.
    assert picture(SimpleNamespace(photo=_sizes((4000, 3000))))[0].width == 4000
    png = SimpleNamespace(photo=None, document=SimpleNamespace(mime_type="image/png"))
    assert picture(png)[1] == "image/png"
    heic = SimpleNamespace(photo=None, document=SimpleNamespace(mime_type="image/heic"))
    assert picture(heic) is None  # not a kind every vendor reads: a file, as before


def test_photos_and_images_sent_as_files_go_to_the_photo_handler(settings, clock) -> None:
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    photo = {
        "photo": [{"file_id": "a", "file_unique_id": "ua", "width": 800, "height": 600}],
        "caption": "this!",
    }
    image = {"document": {"file_id": "d", "file_unique_id": "ud", "mime_type": "image/png"}}
    heic = {"document": {"file_id": "h", "file_unique_id": "uh", "mime_type": "image/heic"}}
    assert _takers(channel, _telegram("message", **photo)) == ["on_photo"]
    # Of the handlers that could take a picture sent as a file, the first is the one that runs.
    assert _takers(channel, _telegram("message", **image)) == ["on_photo", "on_unread"]
    assert _takers(channel, _telegram("message", **heic)) == ["on_unread"]
    assert _takers(channel, _telegram("edited_message", **photo)) == []


def _sent_photo(caption=None, *, chat_type="private", chat_id=42):
    replies: list[str] = []

    async def reply_text(value, **_):
        replies.append(value)

    message = SimpleNamespace(
        text=None,
        caption=caption,
        photo=_sizes((800, 600)),
        reply_text=reply_text,
        reply_to_message=None,
    )
    update = SimpleNamespace(
        update_id=77,
        effective_message=message,
        effective_user=SimpleNamespace(id=1001),
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
    )
    return update, replies


def test_on_telegram_a_photo_is_handed_over_with_a_way_to_fetch_it(
    settings, clock, monkeypatch
) -> None:
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    seen: list[IncomingMessage] = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: seen.append(msg) or OutgoingMessage(msg.chat_id, "Saved.", "ok"),
    )
    update, replies = _sent_photo("we should go")
    asyncio.run(channel.on_photo(update, _context()[0]))
    assert replies == ["Saved."]
    assert seen[0].text == "we should go" and seen[0].photo.mime == "image/jpeg"
    assert seen[0].photo.size == 800 * 600 // 10
    # In a group, only a photo sent to her is looked at: each one is paid for.
    update, replies = _sent_photo("the kids at the beach", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_photo(update, _context()[0]))
    assert len(seen) == 1 and replies == []
    update, replies = _sent_photo("@familybot what's on here?", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_photo(update, _context()[0]))
    assert seen[1].text == "what's on here?" and replies == ["Saved."]


def test_telegram_asks_for_a_photo_the_way_it_is_sent(settings, clock) -> None:
    """A photo's update, as Telegram sends it, reaches the handler with its sizes."""
    bot = Bot(TOKEN)
    update = Update.de_json(
        {
            "update_id": 5,
            "message": {
                "message_id": 1,
                "date": 1790000000,
                "chat": {"id": 42, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Sam"},
                "photo": [
                    {"file_id": "s", "file_unique_id": "us", "width": 320, "height": 240},
                    {"file_id": "m", "file_unique_id": "um", "width": 1280, "height": 960},
                ],
            },
        },
        bot,
    )
    chosen, kind, _ = picture(update.effective_message)
    assert (chosen.file_id, kind) == ("m", "image/jpeg")
