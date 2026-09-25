"""The Telegram channel: long polling, the pipeline in a worker thread, one lane per bot."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from telegram import Update
from telegram.constants import (
    BotDescriptionLimit,
    BotNameLimit,
    ChatAction,
    ChatType,
    MessageLimit,
)
from telegram.error import InvalidToken, NetworkError, RetryAfter
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from familydb import personas, voice, whereabouts
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.config import Settings
from familydb.delivery import deliver
from familydb.pipeline import handle_incoming

log = logging.getLogger(__name__)

CHANNEL = "telegram"
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}


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


@dataclass(frozen=True)
class SharedLocation:
    chat_id: str
    channel_user_id: str
    lat: float
    lon: float
    live: bool


def location_from_update(update: Any) -> SharedLocation | None:
    """A location someone shared, or None. A live location carries how long it is shared for."""
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
        live=getattr(where, "live_period", None) is not None,
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
    text = (message.text or "").lower()
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
        self.application.add_handler(CommandHandler("start", self.on_start))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )
        # A shared location, and a live one as it moves (those arrive as edits).
        self.application.add_handler(MessageHandler(filters.LOCATION, self.on_location))

    async def _post_init(self, application: Application) -> None:
        self._loop = asyncio.get_running_loop()
        self.app.senders[CHANNEL] = self.send_text_threadsafe
        me = await application.bot.get_me()
        self.username = me.username
        log.info("telegram: polling as @%s", me.username)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is not None:
            hello = voice.say(self.app.settings, "start", seed=update.update_id)
            await update.effective_message.reply_text(hello)

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
        try:
            await bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        except Exception:  # a failed typing indicator must never block the reply
            log.debug("typing action failed", exc_info=True)
        reply = await asyncio.to_thread(handle_incoming, self.app, msg)
        if reply is None:
            return

        async def send_reply():
            for chunk in split_text(reply.text):
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

    def send_text_threadsafe(self, chat_id: str, text: str) -> None:
        """Deliver a message from another thread (background jobs)."""
        if self._loop is None:
            raise RuntimeError("Telegram is not running")
        for chunk in split_text(text):
            future = asyncio.run_coroutine_threadsafe(
                self.application.bot.send_message(chat_id=int(chat_id), text=chunk), self._loop
            )
            future.result(timeout=30)

    async def start(self) -> None:
        """Start polling inside the running event loop. Raises InvalidToken for a bad token."""
        await self.application.initialize()  # asks Telegram who the bot is: a bad token fails here
        await self._post_init(self.application)
        await self.application.start()
        assert self.application.updater is not None
        await self.application.updater.start_polling(
            allowed_updates=[Update.MESSAGE], bootstrap_retries=-1
        )

    async def stop(self) -> None:
        if self.app.senders.get(CHANNEL) == self.send_text_threadsafe:
            self.app.senders.pop(CHANNEL, None)
        updater = self.application.updater
        if updater is not None and updater.running:
            await updater.stop()
        if self.application.running:
            await self.application.stop()
        await self.application.shutdown()

    def run(self) -> None:
        """Block until SIGINT or SIGTERM. python-telegram-bot installs the signal handlers."""
        # bootstrap_retries=-1: a server that boots before its network is up, or a Telegram
        # blip at the wrong moment, must not end the process. Once polling is up the updater
        # already retries forever, so this covers the one gap that took the bot down.
        self.application.run_polling(allowed_updates=[Update.MESSAGE], bootstrap_retries=-1)


class TelegramSupervisor:
    """Keeps the Telegram channel running with whatever token the settings hold now.

    A token added, replaced or cleared on the settings page takes effect within a few seconds,
    with no restart: the old connection is closed and a new one opened. A token Telegram refuses
    is not tried again until it changes; one that fails only because Telegram cannot be reached
    is tried again every `RETRY_SECONDS`.

    While a persona is chosen, the bot's own contact in Telegram says her name and her
    introduction (`_introduce`), and follows them when the page changes them, with no trip to
    BotFather.
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
        """Make the contact say her name and her introduction, after a connect or a change.

        Telegram is asked after each connect, and again only when her name or her introduction
        (her /start line) differs from what it was last asked to say: a setting that moves
        nothing she says asks nothing. Under none the contact is left alone, for the admin to
        name in BotFather, and choosing her again says it all again. A wait Telegram asks for is
        waited out, across a reconnect too; any other failure is logged and not tried again until
        something she says changes or the channel reconnects. Nothing here stops or reconnects
        the channel. No model call.
        """
        settings = self.app.settings
        # App.refresh builds new settings whenever a stored value moves, so the same ones mean
        # nothing she says can have changed since the last look.
        if settings is self._seen or time.monotonic() < self._introduce_at:
            return
        self._seen = settings
        her = personas.active(settings)
        if her is personas.PLAIN:
            self._introduced = None
            return
        said = (her.name, voice.say(settings, "start"))
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
