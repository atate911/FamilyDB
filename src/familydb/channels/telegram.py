"""The Telegram channel: long polling, the pipeline in a worker thread, one lane per bot.

Text and voice notes both reach the pipeline. A voice note arrives as a way to fetch it, which
the pipeline calls only once the sender is known to be family; the download itself runs on the
bot's own event loop, like every send. A button under one of her messages (a reminder's Done) is
done by code, never the pipeline (buttons.py).
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import threading
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import (
    BotDescriptionLimit,
    BotNameLimit,
    ChatAction,
    ChatType,
    MessageLimit,
)
from telegram.error import BadRequest, InvalidToken, NetworkError, RetryAfter
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from familydb import buttons, commands, personas, voice, whereabouts
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage, VoiceNote
from familydb.config import Settings
from familydb.delivery import deliver
from familydb.pipeline import handle_incoming

log = logging.getLogger(__name__)

CHANNEL = "telegram"
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
# What the bot asks Telegram for. A live location moving along arrives as edits to the message
# that shared it, a button tapped as a callback query, and Telegram sends a bot only the kinds of
# update it asks for.
UPDATES = [Update.MESSAGE, Update.EDITED_MESSAGE, Update.CALLBACK_QUERY]
# Everything but a location answers new messages only, so an edited question is not answered
# a second time.
NEW = filters.UpdateType.MESSAGE
# How long fetching a voice note may take before it is given up as not heard.
FETCH_SECONDS = 60
# A file name for each kind of recording, since the speech endpoint goes by the extension.
EXTENSIONS = {
    "audio/ogg": "ogg",
    "audio/opus": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/flac": "flac",
}


def incoming_from_update(update: Any) -> IncomingMessage | None:
    """Our channel-agnostic shape from a Telegram update, or None if it has no text."""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None or not message.text:
        return None
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=str(update.update_id),
        chat_id=str(chat.id),
        channel_user_id=str(user.id),
        text=message.text,
        sender_name=sender_name(user),
    )


def recording(message: Any) -> Any:
    """The voice note, or the audio file, a message carries; None for anything else."""
    if message is None:
        return None
    return getattr(message, "voice", None) or getattr(message, "audio", None)


def incoming_voice(update: Any, fetch: Any) -> IncomingMessage | None:
    """A voice note as the pipeline takes it: how long, what kind, and how to fetch it."""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    note = recording(message)
    if note is None or user is None or chat is None:
        return None
    mime = (getattr(note, "mime_type", None) or "audio/ogg").split(";")[0].strip().lower()
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=str(update.update_id),
        chat_id=str(chat.id),
        channel_user_id=str(user.id),
        text=(getattr(message, "caption", None) or "").strip(),
        sender_name=sender_name(user),
        voice=VoiceNote(
            seconds=int(getattr(note, "duration", None) or 0),
            mime=mime,
            fetch=fetch,
            name=f"voice.{EXTENSIONS.get(mime, 'ogg')}",
            size=getattr(note, "file_size", None),
        ),
    )


async def download(note: Any) -> bytes:
    """A voice note's bytes, from Telegram."""
    file = await note.get_file()
    return bytes(await file.download_as_bytearray())


@dataclass(frozen=True)
class SharedLocation:
    chat_id: str
    channel_user_id: str
    lat: float
    lon: float
    live: bool


def location_from_update(update: Any) -> SharedLocation | None:
    """A location someone shared, or None.

    A live location carries how long it is shared for while it is active. An edit is live
    however it reads: a location sent once cannot be edited, and the last edit, when sharing
    stops, no longer carries that period.
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    where = getattr(message, "location", None) if message is not None else None
    if where is None or user is None or chat is None:
        return None
    return SharedLocation(
        chat_id=str(chat.id),
        channel_user_id=str(user.id),
        lat=float(where.latitude),
        lon=float(where.longitude),
        live=getattr(where, "live_period", None) is not None
        or getattr(update, "edited_message", None) is not None,
    )


def record_location(app: App, shared: SharedLocation) -> OutgoingMessage | None:
    with closing(app.connect()) as conn:
        return whereabouts.share(
            app,
            conn,
            channel=CHANNEL,
            channel_user_id=shared.channel_user_id,
            chat_id=shared.chat_id,
            lat=shared.lat,
            lon=shared.lon,
            live=shared.live,
        )


def sender_name(user: Any) -> str | None:
    """How a stranger introduced themselves: their name and @handle, as Telegram gives them."""
    name = getattr(user, "full_name", None)
    handle = getattr(user, "username", None)
    return " ".join(part for part in (name, f"@{handle}" if handle else None) if part) or None


def addressed_to_bot(update: Any, bot_username: str | None, bot_id: int | None) -> bool:
    """In a group: mentioned by @username, or a reply to one of the bot's messages."""
    message = update.effective_message
    if message is None:
        return False
    text = (message.text or getattr(message, "caption", None) or "").lower()
    if bot_username and f"@{bot_username.lower()}" in text:
        return True
    reply = getattr(message, "reply_to_message", None)
    sender = getattr(reply, "from_user", None) if reply is not None else None
    return bool(sender is not None and bot_id is not None and sender.id == bot_id)


def strip_mention(text: str, bot_username: str | None) -> str:
    if not bot_username:
        return text.strip()
    needle = f"@{bot_username}"
    cleaned = text
    while needle.lower() in cleaned.lower():
        index = cleaned.lower().index(needle.lower())
        cleaned = cleaned[:index] + cleaned[index + len(needle) :]
    return " ".join(cleaned.split())


def split_text(text: str, limit: int = int(MessageLimit.MAX_TEXT_LENGTH)) -> list[str]:
    """Telegram caps messages; split long replies at line breaks when possible."""
    text = text.strip() or "…"
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    chunks.append(text)
    return chunks


def keyboard(row: list[dict[str, str]]) -> InlineKeyboardMarkup:
    """A message's buttons, as one row under it (buttons.py)."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(button["label"], callback_data=button["data"]) for button in row]]
    )


def tap_in_thread(app: App, query: Any) -> buttons.Tapped | None:
    """Do what a tapped button says, from the pipeline's side of the thread boundary."""
    chat = getattr(query.message, "chat", None) if query.message is not None else None
    with closing(app.connect()) as conn:
        return buttons.tap(
            app,
            conn,
            channel=CHANNEL,
            chat_id=str(chat.id) if chat is not None else str(query.from_user.id),
            channel_user_id=str(query.from_user.id),
            tap_id=str(query.id),
            data=query.data or "",
        )


def send_once(token: str, chat_id: str, text: str) -> None:
    """Send from a process that is not running the bot, such as the manual retry command."""
    from telegram import Bot

    async def _send() -> None:
        async with Bot(token) as bot:
            for chunk in split_text(text):
                await bot.send_message(chat_id=int(chat_id), text=chunk)

    asyncio.run(_send())


class TelegramChannel:
    """Runs python-telegram-bot's polling loop and feeds messages through the pipeline."""

    def __init__(self, app: App, *, token: str | None = None) -> None:
        self.app = app
        token = token or app.settings.telegram_bot_token
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        self._loop: asyncio.AbstractEventLoop | None = None
        self.username: str | None = None
        self.application: Application = (
            ApplicationBuilder().token(token).post_init(self._post_init).build()
        )
        self.application.add_handler(CommandHandler("start", self.on_start, filters=NEW))
        # /today, /week, /tasks and /now: answered by code, with no model call (commands.py).
        self.application.add_handler(
            CommandHandler(sorted(commands.NAMES), self.on_command, filters=NEW)
        )
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & NEW, self.on_message)
        )
        # A voice note, or a recording sent as an audio file: heard, then answered as words. Only
        # when new: an edited caption would otherwise be paid for and answered a second time.
        self.application.add_handler(
            MessageHandler((filters.VOICE | filters.AUDIO) & NEW, self.on_voice)
        )
        # A shared location, and a live one as it moves (those arrive as edits).
        self.application.add_handler(MessageHandler(filters.LOCATION, self.on_location))
        # A button under one of her messages.
        self.application.add_handler(CallbackQueryHandler(self.on_tap))

    async def _post_init(self, application: Application) -> None:
        self._loop = asyncio.get_running_loop()
        self.app.senders[CHANNEL] = self.send_text_threadsafe
        self.app.button_senders[CHANNEL] = self.send_buttons_threadsafe
        me = await application.bot.get_me()
        self.username = me.username
        log.info("telegram: polling as @%s", me.username)
        await self.offer_commands(application.bot)

    async def offer_commands(self, bot: Any) -> None:
        """Telegram's "/" menu: the commands answered by code. Set only when it differs, since
        most starts change nothing; a failure leaves the commands working, only unlisted."""
        wanted = [BotCommand(name, about) for name, about in commands.MENU]
        try:
            if list(await bot.get_my_commands()) != wanted:
                await bot.set_my_commands(wanted)
        except Exception:
            log.warning("telegram: the command menu could not be set", exc_info=True)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is not None:
            hello = voice.say(self.app.settings, "start", seed=update.update_id)
            await update.effective_message.reply_text(hello)

    async def on_command(self, update: Any, context: Any) -> None:
        """/today, /week, /tasks or /now, answered by code and stored as her reply."""
        msg = incoming_from_update(update)
        if msg is None:
            return
        await self._answer(update, context.bot, msg, handle=commands.answer)

    async def introduce(self, name: str, about: str) -> None:
        """Make the bot's own contact in Telegram say this name and this description.

        The description is what Telegram shows in a chat with the bot before anything is sent.
        Both are cut to Telegram's limits, and each is set only when what Telegram has differs:
        a rename is rate-limited, and most calls change nothing.
        """
        bot = self.application.bot
        name = name[: int(BotNameLimit.MAX_NAME_LENGTH)].rstrip()
        about = about[: int(BotDescriptionLimit.MAX_DESCRIPTION_LENGTH)].rstrip()
        if (await bot.get_my_name()).name != name:
            await bot.set_my_name(name)
        if (await bot.get_my_description()).description != about:
            await bot.set_my_description(about)

    async def on_message(self, update: Any, context: Any) -> None:
        await asyncio.to_thread(self.app.refresh)
        chat = update.effective_chat
        bot = context.bot
        in_group = chat is not None and chat.type in GROUP_TYPES
        if (
            in_group
            and self.app.settings.telegram_require_mention
            and not addressed_to_bot(update, bot.username, bot.id)
        ):
            return
        msg = incoming_from_update(update)
        if msg is None:
            return
        if in_group:
            text = strip_mention(msg.text, bot.username)
            if not text:
                return
            msg = IncomingMessage(
                msg.channel, msg.channel_update_id, msg.chat_id, msg.channel_user_id, text
            )
        await self._answer(update, bot, msg)

    async def on_voice(self, update: Any, context: Any) -> None:
        """A voice note: handed over with a way to fetch it, heard and answered like words."""
        await asyncio.to_thread(self.app.refresh)
        chat = update.effective_chat
        bot = context.bot
        in_group = chat is not None and chat.type in GROUP_TYPES
        if (
            in_group
            and self.app.settings.telegram_require_mention
            and not addressed_to_bot(update, bot.username, bot.id)
        ):
            return
        note = recording(update.effective_message)
        loop = asyncio.get_running_loop()

        def fetch() -> bytes:
            # Called from the pipeline's thread; the download runs on this loop.
            future = asyncio.run_coroutine_threadsafe(download(note), loop)
            return future.result(timeout=FETCH_SECONDS)

        msg = incoming_voice(update, fetch)
        if msg is None:
            return
        if in_group and msg.text:
            msg = dataclasses.replace(msg, text=strip_mention(msg.text, bot.username))
        await self._answer(update, bot, msg)

    async def _answer(
        self,
        update: Any,
        bot: Any,
        msg: IncomingMessage,
        handle: Callable[[App, IncomingMessage], OutgoingMessage | None] | None = None,
    ) -> None:
        """Run the pipeline (or `handle`) on its own thread and send its reply, stored first,
        in this chat."""
        chat = update.effective_chat
        try:
            await bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        except Exception:  # a failed typing indicator must never block the reply
            log.debug("typing action failed", exc_info=True)
        reply = await asyncio.to_thread(handle or handle_incoming, self.app, msg)
        if reply is None:
            return

        async def send_reply():
            chunks = split_text(reply.text)
            for index, chunk in enumerate(chunks):
                if reply.buttons and index == len(chunks) - 1:
                    # A reminder this reply carries keeps its buttons, under the last part.
                    await update.effective_message.reply_text(
                        chunk, reply_markup=keyboard(reply.buttons)
                    )
                else:
                    await update.effective_message.reply_text(chunk)

        if reply.out_message_id is None:
            await send_reply()
        else:
            loop = asyncio.get_running_loop()

            def sender(_chat_id, _text):
                asyncio.run_coroutine_threadsafe(send_reply(), loop).result(timeout=120)

            await asyncio.to_thread(deliver, self.app, reply.out_message_id, sender)

    async def on_location(self, update: Any, context: Any) -> None:
        shared = location_from_update(update)
        if shared is None:
            return
        await asyncio.to_thread(self.app.refresh)
        reply = await asyncio.to_thread(record_location, self.app, shared)
        if reply is None or reply.out_message_id is None:
            return
        message = update.effective_message

        async def send_reply():
            await message.reply_text(reply.text)

        loop = asyncio.get_running_loop()

        def sender(_chat_id, _text):
            asyncio.run_coroutine_threadsafe(send_reply(), loop).result(timeout=120)

        await asyncio.to_thread(deliver, self.app, reply.out_message_id, sender)

    async def on_tap(self, update: Any, context: Any) -> None:
        """A button under one of her messages: done by code, said in her words (buttons.py).

        Whoever tapped is told what happened; when it did something, everyone in the chat sees
        who did what under the message, and its buttons go, having done their job."""
        query = update.callback_query
        if query is None:
            return
        await asyncio.to_thread(self.app.refresh)
        tapped = await asyncio.to_thread(tap_in_thread, self.app, query)
        try:
            await query.answer(tapped.toast if tapped else None)
        except Exception:  # an answer that does not arrive leaves a spinner, nothing worse
            log.debug("telegram: could not answer a tap", exc_info=True)
        if tapped is None or not tapped.finished:
            return
        words = getattr(query.message, "text", None) if query.message is not None else None
        if tapped.note and words:
            try:
                await query.edit_message_text(f"{words}\n\n{tapped.note}")
                return
            except Exception:  # too long with the note, say: the buttons still go below
                log.info("telegram: could not add who did it to a message", exc_info=True)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:  # too old to change, or changed already: what was done still stands
            log.info("telegram: could not take the buttons off a message", exc_info=True)

    def send_text_threadsafe(self, chat_id: str, text: str) -> None:
        """Deliver a message from another thread (background jobs)."""
        self._send_threadsafe(chat_id, text, None)

    def send_buttons_threadsafe(self, chat_id: str, text: str, row: list[dict[str, str]]) -> None:
        """Deliver a message with its buttons from another thread; they go under the last part."""
        self._send_threadsafe(chat_id, text, row)

    def _send_threadsafe(self, chat_id: str, text: str, row: list[dict[str, str]] | None) -> None:
        if self._loop is None:
            raise RuntimeError("Telegram is not running")
        chunks = split_text(text)
        for index, chunk in enumerate(chunks):
            markup = keyboard(row) if row and index == len(chunks) - 1 else None
            future = asyncio.run_coroutine_threadsafe(
                self.application.bot.send_message(
                    chat_id=int(chat_id), text=chunk, reply_markup=markup
                ),
                self._loop,
            )
            future.result(timeout=30)

    async def start(self) -> None:
        """Start polling inside the running event loop. Raises InvalidToken for a bad token."""
        await self.application.initialize()  # asks Telegram who the bot is: a bad token fails here
        await self._post_init(self.application)
        await self.application.start()
        assert self.application.updater is not None
        # bootstrap_retries=-1: a server that boots before its network is up, or a Telegram blip
        # at the wrong moment, must not end the process. Once polling is up the updater retries
        # forever on its own, so this covers the one gap left.
        await self.application.updater.start_polling(allowed_updates=UPDATES, bootstrap_retries=-1)

    async def stop(self) -> None:
        if self.app.senders.get(CHANNEL) == self.send_text_threadsafe:
            self.app.senders.pop(CHANNEL, None)
        if self.app.button_senders.get(CHANNEL) == self.send_buttons_threadsafe:
            self.app.button_senders.pop(CHANNEL, None)
        updater = self.application.updater
        if updater is not None and updater.running:
            await updater.stop()
        if self.application.running:
            await self.application.stop()
        await self.application.shutdown()

    def run(self) -> None:
        """Block until SIGINT or SIGTERM. python-telegram-bot installs the signal handlers."""
        # bootstrap_retries=-1 for the reason `start` gives.
        self.application.run_polling(allowed_updates=UPDATES, bootstrap_retries=-1)


class TelegramSupervisor:
    """Keeps the Telegram channel running with whatever token the settings hold now.

    A token added, replaced or cleared on the settings page takes effect within a few seconds,
    with no restart: the old connection is closed and a new one opened. A token Telegram refuses
    is not tried again until it changes; one that fails only because Telegram cannot be reached
    is tried again every `RETRY_SECONDS`.

    The bot's own contact in Telegram says who is speaking: her name and her introduction, or
    FamilyDB's plain ones under none (`_introduce`), and follows them when the page changes them,
    with no trip to BotFather.
    """

    CHECK_SECONDS = 5.0
    RETRY_SECONDS = 30.0

    def __init__(
        self,
        app: App,
        *,
        make_channel: Callable[[App, str], Any] | None = None,
        check_seconds: float | None = None,
    ) -> None:
        self.app = app
        self.make_channel = make_channel or (lambda app, token: TelegramChannel(app, token=token))
        self.check_seconds = check_seconds if check_seconds is not None else self.CHECK_SECONDS
        self.state: str = "off"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # For the contact (`_introduce`): what it was last asked to say on this connection, the
        # settings it was worked out from, and when Telegram may be asked again after a wait.
        self._introduced: tuple[str, str] | None = None
        self._seen: Settings | None = None
        self._introduce_at = 0.0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="familydb-telegram", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self) -> None:
        try:
            asyncio.run(self._watch())
        except Exception:
            log.exception("telegram: the channel supervisor stopped unexpectedly")

    def _set(self, state: str) -> None:
        self.state = state
        self.app.channel_states[CHANNEL] = state

    async def _watch(self) -> None:
        running: Any = None
        token: str | None = None
        refused = False
        retry_at = 0.0
        while not self._stop.is_set():
            await asyncio.to_thread(self.app.refresh)
            wanted = self.app.settings.telegram_bot_token or None
            if wanted != token:
                if running is not None:
                    await running.stop()
                    running = None
                    log.info("telegram: the token changed on the settings page; reconnecting")
                token, refused, retry_at = wanted, False, 0.0
                if token is None:
                    self._set("off")
            if token and running is None and not refused and time.monotonic() >= retry_at:
                running, refused = await self._open(token)
                if running is None and not refused:
                    retry_at = time.monotonic() + self.RETRY_SECONDS
            if running is not None:
                await self._introduce(running)
            await asyncio.to_thread(self._stop.wait, self.check_seconds)
        if running is not None:
            await running.stop()
        self._set("off")

    async def _open(self, token: str) -> tuple[Any, bool]:
        """A started channel, or None and whether Telegram refused the token outright."""
        channel = self.make_channel(self.app, token)
        try:
            await channel.start()
        except InvalidToken:
            log.error("telegram: Telegram refused the bot token; replace it on the settings page")
            self._set("the token was refused by Telegram")
            await _quietly_stop(channel)
            return None, True
        except NetworkError as exc:
            log.warning("telegram: cannot reach Telegram (%s); trying again shortly", exc)
            self._set("cannot reach Telegram; trying again")
            await _quietly_stop(channel)
            return None, False
        name = getattr(channel, "username", None)
        self._set(f"connected as @{name}" if name else "connected")
        # A new connection introduces her afresh, whatever the last one said.
        self._introduced = self._seen = None
        return channel, False

    async def _introduce(self, channel: Any) -> None:
        """Make the contact say who is speaking, after a connect or a change.

        That is her name and her introduction (her /start line), or under none FamilyDB's, since
        the plain bot calls itself FamilyDB everywhere else: a contact still called by her name
        would say one thing while the bot said another. Telegram is asked after each connect,
        and again only when the name or the introduction differs from what it was last asked to
        say: a setting that moves nothing said asks nothing. A wait Telegram asks for is
        waited out, across a reconnect too, and Telegram out of reach is tried again every
        `RETRY_SECONDS`; a refusal, or any other failure, is logged and not tried again until
        something she says changes or the channel reconnects. Nothing here stops or reconnects
        the channel. No model call.
        """
        settings = self.app.settings
        # App.refresh builds new settings whenever a stored value moves, so the same ones mean
        # nothing she says can have changed since the last look.
        if settings is self._seen or time.monotonic() < self._introduce_at:
            return
        self._seen = settings
        said = (personas.active(settings).name, voice.say(settings, "start"))
        if said == self._introduced:
            return
        try:
            await channel.introduce(*said)
        except RetryAfter as exc:
            wait = exc.retry_after  # seconds; a timedelta from python-telegram-bot 23
            seconds = wait.total_seconds() if isinstance(wait, timedelta) else float(wait)
            log.info("telegram: Telegram asks for %.0f seconds before her name is set", seconds)
            self._seen, self._introduce_at = None, time.monotonic() + seconds
            return
        except NetworkError as exc:
            # BadRequest is a NetworkError too, but it is Telegram refusing, not out of reach.
            if not isinstance(exc, BadRequest):
                log.warning("telegram: cannot reach Telegram to give the bot her name (%s)", exc)
                self._seen, self._introduce_at = None, time.monotonic() + self.RETRY_SECONDS
                return
            log.warning(
                "telegram: Telegram refused her name or introduction (%s); "
                "not trying again until either changes or the bot reconnects",
                exc,
            )
        except Exception as exc:
            log.warning(
                "telegram: could not give the bot her name and introduction (%s); "
                "not trying again until either changes or the bot reconnects",
                exc,
            )
        self._introduced = said


async def _quietly_stop(channel: Any) -> None:
    try:
        await channel.stop()
    except Exception:
        log.debug("telegram: tidying up a channel that did not start", exc_info=True)
