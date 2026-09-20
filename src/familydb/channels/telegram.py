"""The Telegram channel: long polling, the pipeline in a worker thread, one lane per bot."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Update
from telegram.constants import ChatAction, ChatType, MessageLimit
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming

log = logging.getLogger(__name__)

CHANNEL = "telegram"
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
START_TEXT = (
    'Hi! I\'m the family planning bot. Tell me ideas ("we should try that ramen place"), '
    'plans ("we\'re going to the symphony next Saturday") or ask "what should we do this '
    'weekend?"'
)


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
    )


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
        self.application: Application = (
            ApplicationBuilder().token(token).post_init(self._post_init).build()
        )
        self.application.add_handler(CommandHandler("start", self.on_start))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )

    async def _post_init(self, application: Application) -> None:
        self._loop = asyncio.get_running_loop()
        self.app.senders[CHANNEL] = self.send_text_threadsafe
        me = await application.bot.get_me()
        log.info("telegram: polling as @%s", me.username)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is not None:
            await update.effective_message.reply_text(START_TEXT)

    async def on_message(self, update: Any, context: Any) -> None:
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
        for chunk in split_text(reply.text):
            await update.effective_message.reply_text(chunk)

    def send_text_threadsafe(self, chat_id: str, text: str) -> None:
        """Deliver a message from another thread (background jobs)."""
        if self._loop is None:
            raise RuntimeError("Telegram is not running")
        for chunk in split_text(text):
            future = asyncio.run_coroutine_threadsafe(
                self.application.bot.send_message(chat_id=int(chat_id), text=chunk), self._loop
            )
            future.result(timeout=30)

    def run(self) -> None:
        """Block until SIGINT or SIGTERM. python-telegram-bot installs the signal handlers."""
        self.application.run_polling(allowed_updates=[Update.MESSAGE])
