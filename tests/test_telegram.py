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

    async def reply_text(value: str, **_: Any) -> None:
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


def test_start_command(settings, clock, conn, family) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    update, replies = _update("/start")
    context, actions = _context()
    asyncio.run(channel.on_start(update, context))
    assert replies[0].startswith("Hi, I'm Vera.")
    assert actions == [(42, "typing")]


def test_a_stranger_pressing_start_knocks_as_the_pages_promise(settings, clock, conn, family):
    """The setup and Family pages say: send them the bot's link, and once they press Start they
    appear, ready to be let in. Start is all that is sent, so it has to knock."""
    from familydb.app import App
    from familydb.store import knocks

    channel = TelegramChannel(App(settings, clock), token="123456:TEST-TOKEN")
    update, replies = _update("/start", user_id=4242)
    update.effective_user.full_name = "Grandma Jo"
    asyncio.run(channel.on_start(update, _context()[0]))
    assert replies == [
        "Sorry, I only talk to the family. Ask one of them to add you; your id here is 4242."
    ]
    knocked = knocks.recent(conn, channel="telegram")
    assert [(k.channel_user_id, k.name, k.chat_id) for k in knocked] == [
        ("4242", "Grandma Jo", "42")
    ]


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
    assert Update.MY_CHAT_MEMBER in UPDATES  # added to a group


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


def test_start_takes_turns_by_the_update_it_answers(settings, clock, conn, family) -> None:
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
        asyncio.run(channel.on_start(update, _context()[0]))
        assert replies == [voice.say(app.settings, "start", seed=update_id)]
        said.append(replies[0])
    assert len(set(said)) > 1


# -- buttons ---------------------------------------------------------------------------------------


def _query(data, *, who=1001, text="Reminder: bins out. Task #1.", tap_id="cb1"):
    """A tap on a button under one of her messages, as python-telegram-bot hands it over."""
    seen: dict[str, Any] = {}

    async def answer(words=None):
        seen["answer"] = words

    async def edit_message_text(words, **_):
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

    async def reply_text(value, reply_markup=None, **_):
        sent.append((value, reply_markup))

    update, _ = _update("thanks")
    update.effective_message.reply_text = reply_text
    context, _ = _context()
    asyncio.run(channel.on_message(update, context))
    assert [markup is None for _, markup in sent] == [True, False]
    assert sent[-1][1].inline_keyboard[0][0].callback_data == "done:12"


# -- typing, strangers in a group, and what cannot be read -----------------------------------------


def test_typing_stays_up_until_the_answer_is_ready(settings, clock, monkeypatch) -> None:
    """Telegram shows "typing…" for five seconds, and a turn with tools takes longer."""
    import time

    from familydb.app import App
    from familydb.channels import telegram

    monkeypatch.setattr(telegram, "TYPING_EVERY", 0.02)
    channel = TelegramChannel(App(settings, clock), token=TOKEN)

    def slow(application, msg):
        time.sleep(0.15)
        return OutgoingMessage(msg.chat_id, "Saved #1.", "ok")

    monkeypatch.setattr("familydb.channels.telegram.handle_incoming", slow)
    update, replies = _update("we should try the ramen place")
    context, actions = _context()
    asyncio.run(channel.on_message(update, context))
    assert replies == ["Saved #1."]
    assert len(actions) >= 3 and set(actions) == {(42, "typing")}
    shown = len(actions)
    asyncio.run(asyncio.sleep(0.1))
    assert len(actions) == shown  # and none after the answer went


def test_typing_that_fails_never_holds_up_the_answer(settings, clock, monkeypatch) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: OutgoingMessage(msg.chat_id, "ok", "ok"),
    )

    async def refused(**_: Any) -> None:
        raise RuntimeError("Telegram is down")

    update, replies = _update("hello")
    bot = SimpleNamespace(username="familybot", id=999, send_chat_action=refused)
    asyncio.run(channel.on_message(update, SimpleNamespace(bot=bot)))
    assert replies == ["ok"]


def test_in_a_group_a_stranger_is_answered_only_when_they_ask_her(
    settings, clock, conn, family
) -> None:
    """A family group is full of people talking among themselves: somebody not on the list is
    not told so on every message, but their knock is kept for the Family page."""
    from familydb.app import App
    from familydb.store import knocks

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    update, replies = _update("see you all on sunday", chat_type="group", chat_id=-100, user_id=77)
    context, actions = _context()
    asyncio.run(channel.on_message(update, context))
    assert replies == [] and actions == []  # not even "typing…"
    assert [knock.channel_user_id for knock in knocks.recent(conn, channel="telegram")] == ["77"]
    update, replies = _update(
        "@familybot who are you?", chat_type="group", chat_id=-100, user_id=77, update_id=8
    )
    asyncio.run(channel.on_message(update, context))
    assert replies == [
        "Sorry, I only talk to the family. Ask one of them to add you; your id here is 77."
    ]


def test_in_a_group_the_family_is_answered_without_asking_her(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: OutgoingMessage(msg.chat_id, "Saved #3.", "ok"),
    )
    update, replies = _update("we should go camping", chat_type="group", chat_id=-100)
    context, actions = _context()
    asyncio.run(channel.on_message(update, context))
    assert replies == ["Saved #3."] and actions == [(-100, "typing")]


def test_stickers_files_and_videos_go_to_their_own_handler(settings, clock) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    sticker = {
        "file_id": "s1",
        "file_unique_id": "u1",
        "type": "regular",
        "width": 512,
        "height": 512,
        "is_animated": False,
        "is_video": False,
    }
    document = {"file_id": "d1", "file_unique_id": "u2", "file_name": "flyer.pdf"}
    video = {"file_id": "v1", "file_unique_id": "u3", "width": 1, "height": 1, "duration": 9}
    assert _takers(channel, _telegram("message", sticker=sticker)) == ["on_unread"]
    assert _takers(channel, _telegram("message", document=document)) == ["on_unread"]
    assert _takers(channel, _telegram("message", video=video, caption="this hike!")) == [
        "on_unread"
    ]
    assert _takers(channel, _telegram("edited_message", video=video, caption="edited")) == []
    joined = {"new_chat_members": [{"id": 5, "is_bot": False, "first_name": "Jo"}]}
    assert _takers(channel, _telegram("message", **joined)) == []  # nothing to say to that


def _sent(kind: str, *, caption=None, chat_type="private", chat_id=42, user_id=1001):
    update, replies = _update(None, chat_type=chat_type, chat_id=chat_id, user_id=user_id)
    setattr(update.effective_message, kind, SimpleNamespace(file_id="f1"))
    update.effective_message.caption = caption
    return update, replies


def test_a_sticker_with_no_words_is_answered_by_code(settings, clock, conn, family) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    update, replies = _sent("sticker")
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert replies == ["I can't open that kind of message, I'm afraid. Could you tell me in words?"]
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0  # nothing to keep
    # A stranger is told they are not family, as for anything else they send.
    update, replies = _sent("document", user_id=4242)
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert replies[0].startswith("Sorry, I only talk to the family.")
    # In a group, a sticker not sent to her is left to the family.
    update, replies = _sent("sticker", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert replies == []


def test_the_words_with_a_video_are_answered_marked_as_not_seen(
    settings, clock, conn, family, monkeypatch
) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    seen = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: (
            seen.append(msg) or OutgoingMessage(msg.chat_id, "Saved #9.", "ok")
        ),
    )
    update, replies = _sent("video", caption="we should do this hike next weekend")
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert seen[0].text == "(with a video, not seen) we should do this hike next weekend"
    assert replies == ["Saved #9."]
    update, _ = _sent("animation", caption="@familybot this one", chat_type="group", chat_id=-100)
    update.effective_message.document = SimpleNamespace(file_id="f2")  # as Telegram sends a GIF
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert seen[1].text == "(with a GIF, not seen) this one"
    # In a family group where everything is for her, words need not name her; a mention alone,
    # with no other words, is nothing to answer but that it cannot be read.
    update, _ = _sent("video", caption="the falls, on saturday?", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert seen[2].text == "(with a video, not seen) the falls, on saturday?"
    update, replies = _sent("video", caption="@familybot", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_unread(update, _context()[0]))
    assert len(seen) == 3 and replies[0].startswith("I can't open that kind of message")


# -- in a group ------------------------------------------------------------------------------------


def _added(by: int, *, was="left", now="member", chat_type="group"):
    """The bot's own membership changing, as Telegram tells it: added to a group by `by`."""
    return Update.de_json(
        {
            "update_id": 21,
            "my_chat_member": {
                "chat": {"id": -100, "type": chat_type, "title": "Tates"},
                "from": {"id": by, "is_bot": False, "first_name": "Sam"},
                "date": 1790000000,
                "old_chat_member": {
                    "user": {"id": 999, "is_bot": True, "first_name": "V"},
                    "status": was,
                },
                "new_chat_member": {
                    "user": {"id": 999, "is_bot": True, "first_name": "V"},
                    "status": now,
                },
            },
        },
        Bot(TOKEN),
    )


def _me(reads: bool):
    async def get_me():
        return SimpleNamespace(username="familybot", can_read_all_group_messages=reads)

    return SimpleNamespace(bot=SimpleNamespace(get_me=get_me))


def test_being_added_to_a_group_is_routed_to_her(settings, clock) -> None:
    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    assert _takers(channel, _added(1001)) == ["on_membership"]


def test_added_by_the_family_she_says_hello_and_how_to_talk_to_her(
    settings, clock, conn, family
) -> None:
    from familydb.app import App

    app = App(settings, clock)
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    channel = TelegramChannel(app, token=TOKEN)
    asyncio.run(channel.on_membership(_added(1001), _me(reads=True)))
    assert sent == [
        (
            "-100",
            "Hi all, I'm Vera. Tell me ideas and plans as they come up here, or ask what we should "
            "do this weekend.",
        )
    ]
    # Kept, as everything she says unasked, and marked as sent.
    kept = conn.execute("SELECT * FROM messages WHERE chat_id = '-100'").fetchone()
    assert kept["direction"] == "out" and kept["delivered_at"] is not None
    # Where Telegram's privacy setting means she sees only what mentions her, she says so.
    asyncio.run(channel.on_membership(_added(1001), _me(reads=False)))
    assert "Mention @familybot or reply to me" in sent[-1][1]


def test_added_by_a_stranger_or_taken_out_she_says_nothing(settings, clock, conn, family) -> None:
    from familydb.app import App

    app = App(settings, clock)
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    channel = TelegramChannel(app, token=TOKEN)
    asyncio.run(channel.on_membership(_added(4242), _me(reads=True)))
    asyncio.run(channel.on_membership(_added(1001, was="member", now="left"), _me(reads=True)))
    asyncio.run(channel.on_membership(_added(1001, chat_type="private"), _me(reads=True)))
    assert sent == []
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0


def test_answer_only_when_mentioned_is_set_on_the_page(settings, clock, conn, family, monkeypatch):
    """A setting the family would change: from the Connections page, taken up at once."""
    from familydb.app import App
    from familydb.store import settings as settings_store
    from familydb.store.db import transaction

    app = App(settings, clock)
    channel = TelegramChannel(app, token=TOKEN)
    seen = []
    monkeypatch.setattr(
        "familydb.channels.telegram.handle_incoming",
        lambda application, msg: seen.append(msg) or OutgoingMessage(msg.chat_id, "ok", "ok"),
    )
    with transaction(conn):
        settings_store.set_many(conn, {"telegram_require_mention": True}, source="test")
    update, replies = _update("just chatting", chat_type="group", chat_id=-100)
    asyncio.run(channel.on_message(update, _context()[0]))
    assert seen == [] and replies == [] and app.settings.telegram_require_mention


# -- formatting ------------------------------------------------------------------------------------


def test_what_a_job_sends_goes_formatted_with_its_buttons(settings, clock) -> None:
    """A reminder or a digest is sent from a job's thread onto the bot's own loop."""
    import threading

    from familydb.app import App

    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    sent: list[tuple[int, str, dict[str, Any]]] = []

    async def send_message(chat_id, text, **extra):
        sent.append((chat_id, text, extra))

    channel.application = SimpleNamespace(bot=SimpleNamespace(send_message=send_message))
    loop = asyncio.new_event_loop()
    running = threading.Thread(target=loop.run_forever, daemon=True)
    running.start()
    channel._loop = loop
    try:
        row = [{"label": "✓ Done", "data": "done:1"}]
        channel.send_buttons_threadsafe("42", "Reminder: **bins** out & back", row)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        running.join(timeout=5)
    [(chat, text, extra)] = sent
    assert (chat, text, extra["parse_mode"]) == (42, "Reminder: <b>bins</b> out &amp; back", "HTML")
    assert extra["reply_markup"].inline_keyboard[0][0].callback_data == "done:1"


def test_a_tap_keeps_the_message_s_own_formatting(settings, clock, conn, family) -> None:
    from familydb.app import App
    from familydb.tools import ToolContext
    from familydb.tools.tasks import AddTaskInput, add_task

    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    task = add_task(ctx, AddTaskInput(title="Bins out", remind_at="2026-09-20T18:00"))["task"]
    channel = TelegramChannel(App(settings, clock), token=TOKEN)
    update, seen = _query(f"done:{task['id']}", text="Reminder: bins out & back")
    update.callback_query.message.text_html = "Reminder: <b>bins</b> out &amp; back"
    asyncio.run(channel.on_tap(update, None))
    assert seen["text"] == "Reminder: <b>bins</b> out &amp; back\n\nTicked off ✓ (Sam)."
