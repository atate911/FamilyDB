"""Voice notes: heard by a speech model through the gateway, then answered as if typed."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from familydb import voice
from familydb.agent import gateway, spending
from familydb.agent.providers import Audio, build, hearers, prices
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage, VoiceNote
from familydb.channels.telegram import TelegramChannel, incoming_voice
from familydb.errors import AgentError
from familydb.pipeline import handle_incoming, retry_message
from familydb.store import calls, messages
from familydb.store.db import transaction
from tests import fakes
from tests.conftest import NOW_ISO

SPOKEN = "um so we should try that ramen place on Main, the girls would love it"
OGG = b"OggS-not-really-a-recording"


def _voice(update_id="v1", *, seconds=42, user_id="1001", caption="", fetched=None, data=OGG):
    def fetch() -> bytes:
        if fetched is not None:
            fetched.append(update_id)
        return data

    note = VoiceNote(seconds=seconds, mime="audio/ogg", fetch=fetch)
    return IncomingMessage("telegram", update_id, "chat-1", user_id, caption, voice=note)


def _kinds(conn) -> list[str]:
    return [row[0] for row in conn.execute("SELECT kind FROM llm_calls ORDER BY id")]


# -- the pipeline --------------------------------------------------------------------------------


def test_a_voice_note_is_heard_then_answered_like_words(settings, clock, conn, family) -> None:
    ears = fakes.FakeTranscriptionsAPI(fakes.oa_transcription(SPOKEN))
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1 Ramen place on Main.")]))
    reply = handle_incoming(App(settings, clock), _voice(), api=api, conn=conn, hearing=ears)

    assert reply.status == "ok" and reply.text == "Saved #1 Ramen place on Main."
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.text == f"(voice note) {SPOKEN}" and inbound.status == "processed"
    sent = ears.requests[0]
    assert sent["model"] == "gpt-4o-mini-transcribe"
    assert sent["file"] == ("voice.ogg", OGG, "audio/ogg")
    # Who might be named, so the words come back spelled the family's way.
    assert sent["prompt"] == "Names: Sam, Alex, the girls, Vera."
    said = api.requests[0]["messages"][0]["content"][1]["text"]
    assert said == f"[Sam] (voice note) {SPOKEN}"
    # Hearing is a model call like any other: recorded under its own kind, first, and costed.
    assert _kinds(conn) == ["transcribe", "chat"]
    heard = conn.execute("SELECT * FROM llm_calls WHERE kind = 'transcribe'").fetchone()
    assert heard["message_id"] == inbound.id and heard["provider"] == "openai"
    assert heard["cost_usd"] == pytest.approx((250 * 1.25 + 40 * 5.0) / 1_000_000)
    assert not heard["cost_estimated"]
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0


def test_a_caption_goes_with_the_words(settings, clock, conn, family) -> None:
    ears = fakes.FakeTranscriptionsAPI(fakes.oa_transcription("the zoo on Saturday"))
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Noted.")]))
    note = _voice(caption="and bring the stroller")
    reply = handle_incoming(App(settings, clock), note, api=api, conn=conn, hearing=ears)
    text = messages.get(conn, reply.in_message_id).text
    assert text == "(voice note) the zoo on Saturday\n\nand bring the stroller"


def test_a_stranger_s_voice_note_is_never_even_fetched(settings, clock, conn, family) -> None:
    fetched: list[str] = []
    ears = fakes.FakeTranscriptionsAPI()
    note = _voice(user_id="5555", fetched=fetched)
    reply = handle_incoming(
        App(settings, clock), note, api=fakes.FakeMessagesAPI(), conn=conn, hearing=ears
    )
    assert reply.status == "unknown_sender"
    assert fetched == [] and ears.requests == [] and _kinds(conn) == []


@pytest.mark.parametrize(
    ("overrides", "seconds", "event", "facts", "injected"),
    [
        ({"voice_notes": False}, 42, "voice_off", {}, True),
        ({}, 42, "voice_no_ears", {}, False),  # Claude alone, and nothing that can hear
        ({"voice_max_minutes": 1}, 61, "voice_too_long", {"minutes": 1}, True),
    ],
)
def test_a_voice_note_that_will_not_be_heard_costs_nothing_and_says_why(
    settings, clock, conn, family, overrides, seconds, event, facts, injected
) -> None:
    fetched: list[str] = []
    changed = settings.model_copy(update=overrides)
    ears = fakes.FakeTranscriptionsAPI() if injected else None
    api = fakes.FakeMessagesAPI()
    note = _voice(seconds=seconds, fetched=fetched)
    reply = handle_incoming(App(changed, clock), note, api=api, conn=conn, hearing=ears)
    assert reply.status == "failed"
    assert reply.text == voice.say(changed, event, **facts)
    assert fetched == [] and api.requests == [] and _kinds(conn) == []
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.give_up and inbound.text == messages.unheard(seconds)
    assert messages.pending(conn, max_retries=3, now=NOW_ISO) == []  # nothing left to retry


@pytest.mark.parametrize(
    "answer", [fakes.openai_rate_limit(), fakes.oa_transcription("   ")], ids=["fails", "empty"]
)
def test_a_voice_note_that_could_not_be_heard_is_given_up_with_a_notice(
    settings, clock, conn, family, answer
) -> None:
    ears = fakes.FakeTranscriptionsAPI(answer)
    api = fakes.FakeMessagesAPI()
    reply = handle_incoming(App(settings, clock), _voice(), api=api, conn=conn, hearing=ears)
    assert reply.text == voice.say(settings, "voice_unheard")
    assert api.requests == []  # the chat model is never asked about words nobody heard
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.give_up and inbound.status == "failed"
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0


def test_the_spending_limit_is_checked_before_hearing(settings, clock, conn, family) -> None:
    with transaction(conn):
        calls.log_llm_call(
            conn,
            message_id=None,
            iteration=1,
            model="gpt-6-luna",
            served_model=None,
            request_id=None,
            stop_reason="end",
            usage={},
            duration_ms=1,
            now=NOW_ISO,
            cost_usd=5.0,
        )
    ears = fakes.FakeTranscriptionsAPI()
    reply = handle_incoming(App(settings, clock), _voice(), conn=conn, hearing=ears)
    assert reply.text == voice.say(settings, "limit_reached", limit="2.00")
    assert ears.requests == []


def test_a_voice_note_left_unheard_by_a_restart_is_given_up_not_answered(
    settings, clock, conn, family
) -> None:
    with transaction(conn):
        left = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="v7",
            chat_id="chat-1",
            member_id=family["sam"].id,
            text=messages.unheard(75),
            now=NOW_ISO,
        )
    assert left.text == "(voice note, 1:15, not heard)"
    app = App(settings, clock)
    sent: list[str] = []
    app.senders["telegram"] = lambda _chat, text: sent.append(text)
    api = fakes.FakeMessagesAPI()
    reply = retry_message(app, left.id, api=api, conn=conn)
    assert reply.text == voice.say(settings, "voice_unheard") and sent == [reply.text]
    assert api.requests == [] and messages.get(conn, left.id).give_up


def test_a_heard_voice_note_retried_later_is_not_heard_again(settings, clock, conn, family):
    """Its words were stored, so a turn that failed afterwards is retried from them."""
    ears = fakes.FakeTranscriptionsAPI(fakes.oa_transcription(SPOKEN))
    app = App(settings, clock)
    failed = handle_incoming(
        app,
        _voice(),
        api=fakes.FakeMessagesAPI(fakes.rate_limit_error()),
        conn=conn,
        hearing=ears,
    )
    assert failed.status == "failed" and not messages.get(conn, failed.in_message_id).give_up
    app.senders["telegram"] = lambda _chat, _text: None
    later = fakes.FakeMessagesAPI(fakes.message([fakes.text("Saved #1.")]))
    reply = retry_message(app, failed.in_message_id, api=later, conn=conn)
    assert reply.status == "ok" and len(ears.requests) == 1
    assert later.requests[0]["messages"][0]["content"][1]["text"].startswith("[Sam] (voice note)")


# -- the gateway and who hears -------------------------------------------------------------------


def _keys(settings, **overrides):
    return settings.model_copy(update=overrides)


def test_who_hears_a_voice_note(settings) -> None:
    def names(**overrides):
        return [p.name for p in hearers(_keys(settings, **overrides))]

    # Claude alone cannot hear, and nobody else has a key.
    assert names() == []
    # With the chat on Claude, whoever else can hear and has a key does.
    assert names(openai_api_key="sk") == ["openai"]
    assert names(openai_api_key="sk", gemini_api_key="g") == ["openai", "gemini"]
    assert names(openai_api_key="sk", gemini_api_key="g", provider_fallback=False) == ["openai"]
    # Chosen by name, it comes first; without its key, somebody else only with the fallback on.
    assert names(openai_api_key="sk", gemini_api_key="g", transcribe_provider="gemini") == [
        "gemini",
        "openai",
    ]
    assert names(openai_api_key="sk", transcribe_provider="gemini") == ["openai"]
    assert names(openai_api_key="sk", transcribe_provider="gemini", provider_fallback=False) == []
    assert not gateway.can_listen(_keys(settings))


def test_listen_hands_over_when_the_first_cannot(settings, clock, conn, monkeypatch) -> None:
    both = _keys(settings, openai_api_key="sk", gemini_api_key="g")
    busy = build("openai", both, audio=fakes.FakeTranscriptionsAPI(fakes.openai_rate_limit()))
    spare_api = fakes.FakeGeminiAPI(fakes.gm_response([fakes.gm_text("see you at the zoo")]))
    spare = build("gemini", both, api=spare_api)
    monkeypatch.setattr(gateway, "hearers", lambda _settings, audio=None: [busy, spare])
    heard = gateway.listen(
        settings=both, conn=conn, clock=clock, audio=Audio(OGG, "audio/ogg", 12), hints=""
    )
    assert heard.text == "see you at the zoo"
    row = conn.execute("SELECT provider, kind FROM llm_calls").fetchall()
    assert [tuple(r) for r in row] == [("gemini", "transcribe")]  # the failed ask cost nothing
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0


def test_listen_with_nobody_to_ask_says_so(settings, clock, conn) -> None:
    with pytest.raises(AgentError, match="no model that can hear"):
        gateway.listen(settings=settings, conn=conn, clock=clock, audio=Audio(OGG, "audio/ogg", 3))


def test_hearing_is_purposed_and_priced(settings) -> None:
    assert gateway.purpose("transcribe") == "listening to voice notes"
    # Priced, but never offered as a chat model.
    assert "gpt-4o-mini-transcribe" in prices.hearing_suggestions("openai")
    assert "gpt-4o-mini-transcribe" not in prices.suggestions("openai")
    assert prices.cost("openai", "whisper-1", {"audio_seconds": 90}) == (
        pytest.approx(0.009),
        True,
    )
    # The hold is never less than a minute's hearing costs.
    held = spending.estimate_hearing("openai", "gpt-4o-mini-transcribe", 60)
    heard = prices.cost(
        "openai", "gpt-4o-mini-transcribe", {"input_tokens": 600, "output_tokens": 300}
    )
    assert held > heard[0]
    assert spending.estimate_hearing("openai", "brand-new-ear", 60) > held  # unlisted: dearer


# -- the providers -------------------------------------------------------------------------------


def test_openai_hears_through_its_speech_endpoint(settings) -> None:
    ears = fakes.FakeTranscriptionsAPI(fakes.oa_transcription(" hello there "))
    provider = build("openai", _keys(settings, openai_api_key="sk"), audio=ears)
    heard = provider.transcribe(Audio(OGG, "audio/ogg", 5, "voice.ogg"), "Names: Sam.")
    assert heard.text == "hello there" and heard.model == "gpt-4o-mini-transcribe"
    assert heard.usage == {"input_tokens": 250, "output_tokens": 40}
    assert ears.requests == [
        {
            "model": "gpt-4o-mini-transcribe",
            "file": ("voice.ogg", OGG, "audio/ogg"),
            "response_format": "json",
            "prompt": "Names: Sam.",
        }
    ]


def test_openai_hearing_by_the_minute_and_its_failures(settings) -> None:
    from openai.types.audio import Transcription

    by_minute = Transcription.model_validate(
        {"text": "hi", "usage": {"type": "duration", "seconds": 61.4}}
    )
    ears = fakes.FakeTranscriptionsAPI(by_minute, fakes.openai_rate_limit())
    keyed = _keys(settings, openai_api_key="sk", openai_transcribe_model="whisper-1")
    provider = build("openai", keyed, audio=ears)
    assert provider.transcribe(Audio(OGG, "audio/ogg", 61), "").usage == {"audio_seconds": 61}
    assert "prompt" not in ears.requests[0]  # no names to give, none sent
    with pytest.raises(AgentError) as failed:
        provider.transcribe(Audio(OGG, "audio/ogg", 61), "")
    assert failed.value.retryable


def test_gemini_hears_the_recording_sent_with_one_line(settings) -> None:
    api = fakes.FakeGeminiAPI(fakes.gm_response([fakes.gm_text("pick up the cake")]))
    provider = build("gemini", _keys(settings, gemini_api_key="g"), api=api)
    assert provider.listener() == "gemini-3.8-flash"  # the lookup model, unless one is named
    heard = provider.transcribe(Audio(OGG, "audio/ogg", 10), "Names: Sam.")
    assert heard.text == "pick up the cake"
    assert heard.usage["input_tokens"] == 100 and heard.usage["output_tokens"] == 10
    sent = api.requests[0]
    assert sent["model"] == "gemini-3.8-flash"
    parts = sent["contents"][0]["parts"]
    assert parts[0] == {"inline_data": {"mime_type": "audio/ogg", "data": OGG}}
    assert (
        parts[1]["text"].startswith("Write down what is said") and "Names: Sam." in parts[1]["text"]
    )
    assert sent["config"]["max_output_tokens"] == 400 + 8 * 10
    assert "tools" not in sent["config"] and "system_instruction" not in sent["config"]


def test_gemini_refusing_to_hear_is_not_retried(settings) -> None:
    refused = fakes.gm_response([], finish_reason="SAFETY")
    provider = build(
        "gemini", _keys(settings, gemini_api_key="g"), api=fakes.FakeGeminiAPI(refused)
    )
    with pytest.raises(AgentError) as failed:
        provider.transcribe(Audio(OGG, "audio/ogg", 10), "")
    assert not failed.value.retryable


def test_claude_hears_nothing(settings) -> None:
    provider = build("anthropic", settings, api=object())
    assert provider.listener() is None
    with pytest.raises(AgentError):
        provider.transcribe(Audio(OGG, "audio/ogg", 1), "")


# -- Telegram ------------------------------------------------------------------------------------


def _voice_update(*, duration=12, caption=None, chat_type="private", reply_from=None, audio=None):
    replies: list[str] = []

    async def reply_text(value: str) -> None:
        replies.append(value)

    async def download_as_bytearray() -> bytearray:
        return bytearray(OGG)

    async def get_file():
        return SimpleNamespace(download_as_bytearray=download_as_bytearray)

    note = SimpleNamespace(
        duration=duration, mime_type="audio/ogg", file_size=len(OGG), get_file=get_file
    )
    message = SimpleNamespace(
        text=None,
        caption=caption,
        voice=None if audio else note,
        audio=audio,
        reply_text=reply_text,
        reply_to_message=SimpleNamespace(from_user=SimpleNamespace(id=reply_from))
        if reply_from
        else None,
    )
    update = SimpleNamespace(
        update_id=31,
        effective_message=message,
        effective_user=SimpleNamespace(id=1001, full_name="Sam", username=None),
        effective_chat=SimpleNamespace(id=42, type=chat_type),
    )
    return update, replies


def _context():
    async def send_chat_action(chat_id: int, action: str) -> None:
        return None

    bot = SimpleNamespace(username="familybot", id=999, send_chat_action=send_chat_action)
    return SimpleNamespace(bot=bot)


def test_a_telegram_voice_note_becomes_one_the_pipeline_can_fetch(settings, clock, monkeypatch):
    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    seen: list[IncomingMessage] = []
    fetched: list[bytes] = []

    def fake_handle(application, msg):
        seen.append(msg)
        fetched.append(msg.voice.fetch())  # from the pipeline's thread, through the bot's loop
        return OutgoingMessage(msg.chat_id, "Heard you.", "ok")

    monkeypatch.setattr("familydb.channels.telegram.handle_incoming", fake_handle)
    update, replies = _voice_update(caption="for Saturday")
    asyncio.run(channel.on_voice(update, _context()))
    assert replies == ["Heard you."]
    note = seen[0].voice
    assert (note.seconds, note.mime, note.name, note.size) == (
        12,
        "audio/ogg",
        "voice.ogg",
        len(OGG),
    )
    assert seen[0].text == "for Saturday" and seen[0].channel_update_id == "31"
    assert fetched == [OGG]


def test_an_audio_file_is_named_for_what_it_is() -> None:
    audio = SimpleNamespace(duration=30, mime_type="audio/mpeg", file_size=10, get_file=None)
    update, _ = _voice_update(audio=audio)
    msg = incoming_voice(update, lambda: b"")
    assert msg.voice.name == "voice.mp3" and msg.voice.seconds == 30


def test_in_a_group_that_needs_a_mention_a_voice_note_must_answer_the_bot(
    settings, clock, monkeypatch
) -> None:
    app = App(settings.model_copy(update={"telegram_require_mention": True}), clock)
    channel = TelegramChannel(app, token="123456:TEST-TOKEN")
    seen: list[IncomingMessage] = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: seen.append(msg) or OutgoingMessage(msg.chat_id, "ok", "ok"),
    )
    update, _ = _voice_update(chat_type="group")
    asyncio.run(channel.on_voice(update, _context()))
    assert seen == []
    update, _ = _voice_update(chat_type="group", reply_from=999)
    asyncio.run(channel.on_voice(update, _context()))
    update, _ = _voice_update(chat_type="group", caption="@familybot this one")
    asyncio.run(channel.on_voice(update, _context()))
    assert [m.text for m in seen] == ["", "this one"]
