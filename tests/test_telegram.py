import asyncio
from types import SimpleNamespace
from typing import Any

from telegram import Bot, Update, User
from telegram.ext import Application, Updater

from familydb.channels.base import OutgoingMessage
from familydb.channels.telegram import (
    UPDATES,
    TelegramChannel,
    addressed_to_bot,
    incoming_from_update,
    keyboard,
    location_from_update,
    record_location,
    split_text,
    strip_mention,
)
from familydb.store import locations

TOKEN = "123456:TEST-TOKEN"


def _update(
    text="hello", *, chat_type="private", chat_id=42, user_id=1001, update_id=7, reply_from=None
):
    replies: list[str] = []

    async def reply_text(value: str) -> None:
        replies.append(value)

    message = SimpleNamespace(
        text=text,
        reply_text=reply_text,
        reply_to_message=SimpleNamespace(from_user=SimpleNamespace(id=reply_from))
        if reply_from
        else None,
    )
    update = SimpleNamespace(
        update_id=update_id,
        effective_message=message,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
    )
    return update, replies


def _telegram(kind: str, **fields: Any) -> Update:
    """An update as Telegram sends it: a new "message", or an "edited_message"."""
    message = {
        "message_id": 5,
        "date": 1790000000,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 1001, "is_bot": False, "first_name": "Sam"},
        **fields,
    }
    if kind == "edited_message":
        message["edit_date"] = 1790000060
    bot = Bot(TOKEN)
    # Who the bot is, which a command is checked against, as polling would have learnt it.
    bot._bot_user = User(999, "Vera", True, username="familybot")
    return Update.de_json({"update_id": 7, kind: message}, bot)


def _takers(channel: TelegramChannel, update: Update) -> list[str]:
    """Which of the channel's handlers would answer this update."""
    handlers = channel.application.handlers[0]
    return [h.callback.__name__ for h in handlers if h.check_update(update)]


def _context(username="familybot", bot_id=999):
    actions: list[tuple[int, str]] = []

    async def send_chat_action(chat_id: int, action: str) -> None:
        actions.append((chat_id, action))

    bot = SimpleNamespace(username=username, id=bot_id, send_chat_action=send_chat_action)
    return SimpleNamespace(bot=bot), actions


def test_incoming_from_update() -> None:
    update, _ = _update("we should try the ramen place")
    msg = incoming_from_update(update)
    assert msg.channel == "telegram" and msg.channel_update_id == "7"
    assert msg.chat_id == "42" and msg.channel_user_id == "1001"
    update.effective_message.text = None
    assert incoming_from_update(update) is None


def test_addressed_to_bot_and_strip_mention() -> None:
    update, _ = _update("@FamilyBot what should we do?", chat_type="group")
    assert addressed_to_bot(update, "familybot", 999)
    assert (
        strip_mention("@FamilyBot what should we do? @familybot", "familybot")
        == "what should we do?"
    )
    update, _ = _update("sounds good", chat_type="group", reply_from=999)
    assert addressed_to_bot(update, "familybot", 999)
    update, _ = _update("sounds good", chat_type="group", reply_from=5)
    assert not addressed_to_bot(update, "familybot", 999)


def test_split_text_respects_limits() -> None:
    assert split_text("short") == ["short"]
    long = "\n".join(f"line {i}" for i in range(2000))
    chunks = split_text(long, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "\n".join(chunks).split() == long.split()
    assert split_text("x" * 250, limit=100) == ["x" * 100, "x" * 100, "x" * 50]


def test_on_message_runs_the_pipeline_and_replies(settings, clock, monkeypatch) -> None:
    from familydb.app import App

    app = App(settings, clock)
    channel = TelegramChannel(app, token="123456:TEST-TOKEN")
    seen = []

    def fake_handle(application, msg):
        seen.append(msg)
        return OutgoingMessage(msg.chat_id, "Saved #1.", "ok")

    monkeypatch.setattr("familydb.channels.telegram.handle_incoming", fake_handle)
    update, replies = _update("we should try the ramen place")
    context, actions = _context()
    asyncio.run(channel.on_message(update, context))
    assert replies == ["Saved #1."]
    assert actions == [(42, "typing")]
    assert seen[0].text == "we should try the ramen place"


def test_group_mention_mode(settings, clock, monkeypatch) -> None:
    from familydb.app import App

    app = App(settings.model_copy(update={"telegram_require_mention": True}), clock)
    channel = TelegramChannel(app, token="123456:TEST-TOKEN")
    seen = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: seen.append(msg) or OutgoingMessage(msg.chat_id, "ok", "ok"),
    )
    context, _ = _context()
    update, replies = _update("just chatting", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_message(update, context))
    assert seen == [] and replies == []
    update, replies = _update("@familybot what should we do?", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_message(update, context))
    assert seen[0].text == "what should we do?" and seen[0].chat_id == "-100"
    assert replies == ["ok"]


def test_a_group_message_keeps_who_sent_it(settings, clock, monkeypatch) -> None:
    """The mention comes off the words and the sender's name stays, for a stranger's knock."""
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    seen = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: seen.append(msg) or OutgoingMessage(msg.chat_id, "ok", "ok"),
    )
    context, _ = _context()
    update, _ = _update("@familybot hello", chat_type="group", chat_id=-100)
    update.effective_user.full_name = "Jo Bloggs"
    asyncio.run(channel.on_message(update, context))
    assert seen[0].text == "hello" and seen[0].sender_name == "Jo Bloggs"


def test_duplicate_update_sends_nothing(settings, clock, monkeypatch) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    monkeypatch.setattr("familydb.channels.telegram.handle_incoming", lambda a, m: None)
    update, replies = _update("again")
    context, _ = _context()
    asyncio.run(channel.on_message(update, context))
    assert replies == []


def test_start_command(settings, clock) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    update, replies = _update("/start")
    asyncio.run(channel.on_start(update, None))
    assert replies[0].startswith("Hi, I'm Vera.")


def test_polling_asks_for_the_edits_a_live_location_moves_by(settings, clock, monkeypatch) -> None:
    """Telegram sends a bot only the kinds of update it asks for, and a live location moving
    along arrives as edits to the message that shared it."""
    from familydb.app import App

    asked: list[dict[str, Any]] = []

    async def nothing(*args: Any, **kwargs: Any) -> None:
        return None

    async def start_polling(self: Any, **kwargs: Any) -> None:
        asked.append(kwargs)

    monkeypatch.setattr(Application, "initialize", nothing)
    monkeypatch.setattr(Application, "start", nothing)
    monkeypatch.setattr(Updater, "start_polling", start_polling)
    monkeypatch.setattr(Application, "run_polling", lambda self, **kwargs: asked.append(kwargs))
    monkeypatch.setattr(TelegramChannel, "_post_init", nothing)
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    asyncio.run(channel.start())  # as the supervisor runs it
    channel.run()  # and on its own
    assert [a["allowed_updates"] for a in asked] == [UPDATES, UPDATES]
    assert Update.MESSAGE in UPDATES and Update.EDITED_MESSAGE in UPDATES
    assert Update.CALLBACK_QUERY in UPDATES  # a button tapped


def test_an_edit_is_taken_only_as_a_live_location_moving(settings, clock) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    question = {"text": "what should we do?"}
    start = {"text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}
    here = {"location": {"latitude": 45.52, "longitude": -122.68, "live_period": 900}}
    spoken = {"voice": {"file_id": "v1", "file_unique_id": "u1", "duration": 4}}
    assert _takers(channel, _telegram("message", **question)) == ["on_message"]
    assert _takers(channel, _telegram("message", **start)) == ["on_start"]
    assert _takers(channel, _telegram("message", **spoken)) == ["on_voice"]
    assert _takers(channel, _telegram("message", **here)) == ["on_location"]
    # An edited question, command or voice note is not answered, or heard, a second time.
    assert _takers(channel, _telegram("edited_message", **question)) == []
    assert _takers(channel, _telegram("edited_message", **start)) == []
    assert _takers(channel, _telegram("edited_message", **spoken)) == []
    assert _takers(channel, _telegram("edited_message", **here)) == ["on_location"]


def test_a_live_location_is_followed_until_it_stops(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.app import App

    # The live period as the library's next major version gives it (a timedelta, not seconds),
    # which it asks for now with a warning; only whether there is one is read.
    monkeypatch.setenv("PTB_TIMEDELTA", "1")
    app = App(settings, clock, geocoder=SimpleNamespace(reverse=lambda lat, lon: "Old Town"))
    live = {"latitude": 45.519, "longitude": -122.679, "live_period": 3600}
    shared = location_from_update(_telegram("message", location=live))
    confirmed = record_location(app, shared)
    assert confirmed is not None and "Got it (Old Town)" in confirmed.text
    # Moving along, then the last edit when sharing stops, which no longer carries the live
    # period: both followed without a word, neither taken for a new share to confirm.
    for lat, rest in ((45.53, {"live_period": 3600}), (45.54, {})):
        where = {"latitude": lat, "longitude": -122.679, **rest}
        moved = location_from_update(_telegram("edited_message", location=where))
        assert moved.live
        assert record_location(app, moved) is None
        assert locations.get(conn, family["sam"].id).lat == lat
    # A location sent once, with no live period, is not live.
    once = location_from_update(_telegram("message", location={"latitude": 1.0, "longitude": 2.0}))
    assert not once.live


def test_start_takes_turns_by_the_update_it_answers(settings, clock) -> None:
    """/start has no facts of its own, so without the update's id to choose by it would read the
    same every time; with it, the same update sent again reads as it did."""
    from familydb import voice
    from familydb.app import App

    lines = {"start": ["Hi, I'm {name}.", "Hello, {name} here.", "{name}, at your service."]}
    app = App(settings.model_copy(update={"voice_lines": lines}), clock)
    channel = TelegramChannel(app, token="123456:TEST-TOKEN")
    said = []
    for update_id in range(12):
        update, replies = _update("/start", update_id=update_id)
        asyncio.run(channel.on_start(update, None))
        assert replies == [voice.say(app.settings, "start", seed=update_id)]
        said.append(replies[0])
    assert len(set(said)) > 1


# -- buttons ---------------------------------------------------------------------------------------


def _query(data, *, who=1001, text="Reminder: bins out. Task #1.", tap_id="cb1"):
    """A tap on a button under one of her messages, as python-telegram-bot hands it over."""
    seen: dict[str, Any] = {}

    async def answer(words=None):
        seen["answer"] = words

    async def edit_message_text(words):
        seen["text"] = words

    async def edit_message_reply_markup(reply_markup=None):
        seen["markup"] = reply_markup

    query = SimpleNamespace(
        id=tap_id,
        data=data,
        from_user=SimpleNamespace(id=who),
        message=SimpleNamespace(chat=SimpleNamespace(id=42), text=text),
        answer=answer,
        edit_message_text=edit_message_text,
        edit_message_reply_markup=edit_message_reply_markup,
    )
    return SimpleNamespace(callback_query=query), seen


def test_a_tap_is_routed_to_the_buttons(settings, clock) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    tapped = Update.de_json(
        {
            "update_id": 9,
            "callback_query": {
                "id": "cb1",
                "from": {"id": 1001, "is_bot": False, "first_name": "Sam"},
                "chat_instance": "c1",
                "data": "done:1",
            },
        },
        Bot(TOKEN),
    )
    assert _takers(channel, tapped) == ["on_tap"]


def test_a_tap_is_answered_and_the_message_says_who_did_it(settings, clock, conn, family):
    from familydb.app import App
    from familydb.store import tasks
    from familydb.tools import ToolContext
    from familydb.tools.tasks import AddTaskInput, add_task

    app = App(settings, clock)
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    task = add_task(ctx, AddTaskInput(title="Bins out", remind_at="2026-09-20T18:00"))["task"]
    channel = TelegramChannel(app, token=TOKEN)
    update, seen = _query(f"done:{task['id']}")
    asyncio.run(channel.on_tap(update, None))
    assert seen["answer"] == "Ticked off ✓ (Sam)."
    assert seen["text"] == "Reminder: bins out. Task #1.\n\nTicked off ✓ (Sam)."
    assert tasks.get(conn, task["id"]).status == "done"
    # A message that cannot take the note still loses its buttons, its job done.
    task = add_task(ctx, AddTaskInput(title="Recycling", remind_at="2026-09-20T18:00"))["task"]
    update, seen = _query(f"done:{task['id']}", tap_id="cb2")

    async def too_long(words):
        raise RuntimeError("message is too long")

    update.callback_query.edit_message_text = too_long
    asyncio.run(channel.on_tap(update, None))
    assert seen["markup"] is None and "text" not in seen
    # Somebody not in the family: told so, and the buttons stay for the family.
    update, seen = _query(f"done:{task['id']}", who=9999, tap_id="cb3")
    asyncio.run(channel.on_tap(update, None))
    assert seen == {"answer": "Sorry, only the family can use these."}


def test_buttons_go_under_the_last_part_of_what_is_sent(settings, clock, monkeypatch) -> None:
    from familydb.app import App

    row = [{"label": "✓ Done", "data": "done:12"}, {"label": "Tomorrow", "data": "tomorrow:12"}]
    markup = keyboard(row)
    assert [(b.text, b.callback_data) for b in markup.inline_keyboard[0]] == [
        ("✓ Done", "done:12"),
        ("Tomorrow", "tomorrow:12"),
    ]
    # A reply carrying a reminder puts its buttons under its last part.
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: OutgoingMessage(msg.chat_id, "x" * 5000, "ok", buttons=row),
    )
    sent: list[tuple[str, Any]] = []

    async def reply_text(value, reply_markup=None):
        sent.append((value, reply_markup))

    update, _ = _update("thanks")
    update.effective_message.reply_text = reply_text
    context, _ = _context()
    asyncio.run(channel.on_message(update, context))
    assert [markup is None for _, markup in sent] == [True, False]
    assert sent[-1][1].inline_keyboard[0][0].callback_data == "done:12"
