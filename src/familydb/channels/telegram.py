"""The Telegram channel: long polling, the pipeline in a worker thread.

A voice note or photo arrives as a way to fetch it, called by the pipeline only once the sender
is known to be family; the download runs on the bot's own event loop, like every send. Buttons,
/start and wordless stickers/files/videos are done by code (buttons.py, commands.py). In a group
a stranger is answered only when they address the bot, since a family group talks among itself.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import html
import logging
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import Any

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import (
    BotDescriptionLimit,
    BotNameLimit,
    ChatAction,
    ChatMemberStatus,
    ChatType,
    MessageLimit,
    ParseMode,
)
from telegram.error import BadRequest, InvalidToken, NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from familydb import buttons, commands, personas, routing, voice, whereabouts
from familydb.app import App
from familydb.base.config import Settings
from familydb.channels import markup
from familydb.channels.base import IncomingMessage, OutgoingMessage, PhotoNote, VoiceNote
from familydb.delivery import deliver
from familydb.pipeline import answer_gathered, handle_incoming, receive
from familydb.store import members, messages

log = logging.getLogger(__name__)

CHANNEL = "telegram"
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
# Telegram sends a bot only the update kinds it asks for: edits (live location), callback queries
# (buttons) and membership changes.
UPDATES = [Update.MESSAGE, Update.EDITED_MESSAGE, Update.CALLBACK_QUERY, Update.MY_CHAT_MEMBER]
OUTSIDE = frozenset({ChatMemberStatus.LEFT, ChatMemberStatus.BANNED})
INSIDE = frozenset({ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR})
# Everything but a location answers new messages only, so an edited question is not answered twice.
NEW = filters.UpdateType.MESSAGE
FETCH_SECONDS = 60
# "typing…" lasts five seconds on Telegram, so it is resent this often, for no longer than a turn
# takes.
TYPING_EVERY = 4.5
TYPING_AT_MOST = 180.0
# A photo is fetched at the largest size no longer than this on its long side: plenty for a poster's
# words, while a vendor's count for a picture grows with its size.
LONGEST = 1600
PICTURE_KINDS = ("image/jpeg", "image/png", "image/webp")
# An album arrives as one message per photo sharing a media group id: gathered for this long, then
# handed over as one.
ALBUM_SECONDS = 1.5
PICTURES = filters.PHOTO | filters.Document.MimeType(PICTURE_KINDS[0])
for _kind in PICTURE_KINDS[1:]:
    PICTURES = PICTURES | filters.Document.MimeType(_kind)
# What a message may carry that nobody reads, by caption wording, first match wins (an animation
# also carries a document).
UNREAD = (
    ("video_note", "a video"),
    ("video", "a video"),
    ("animation", "a GIF"),
    ("sticker", "a sticker"),
    ("document", "a file"),
    ("contact", "a contact"),
    ("poll", "a poll"),
    ("dice", "a dice roll"),
)
UNREADABLE = (
    filters.VIDEO_NOTE
    | filters.VIDEO
    | filters.ANIMATION
    | filters.Sticker.ALL
    | filters.Document.ALL
    | filters.CONTACT
    | filters.POLL
    | filters.Dice.ALL
)
# The speech endpoint goes by file extension.
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


def unread(message: Any) -> str | None:
    if message is None:
        return None
    return next((words for field, words in UNREAD if getattr(message, field, None)), None)


def incoming_unread(update: Any, bot_username: str | None = None) -> IncomingMessage | None:
    """A sticker, file or video as the words that came with it, marked as something not seen; None
    if it is none of those.
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    what = unread(message)
    if what is None or user is None or chat is None:
        return None
    words = strip_mention(getattr(message, "caption", None) or "", bot_username)
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=str(update.update_id),
        chat_id=str(chat.id),
        channel_user_id=str(user.id),
        text=messages.unseen(what, words) if words else "",
        sender_name=sender_name(user),
    )


def picture(message: Any) -> tuple[Any, str, int | None] | None:
    """The photo a message carries as (what to fetch, kind, size in bytes): the largest size within
    `LONGEST`, or an image file a model reads.
    """
    if message is None:
        return None
    sizes = list(getattr(message, "photo", None) or [])
    if sizes:
        fitting = [size for size in sizes if max(size.width, size.height) <= LONGEST]
        chosen = max(fitting or [min(sizes, key=_area)], key=_area)
        return chosen, "image/jpeg", getattr(chosen, "file_size", None)
    document = getattr(message, "document", None)
    kind = (getattr(document, "mime_type", None) or "").lower()
    if document is not None and kind in PICTURE_KINDS:
        return document, kind, getattr(document, "file_size", None)
    return None


def _area(size: Any) -> int:
    return int(size.width) * int(size.height)


def family_knows(app: App, channel_user_id: str) -> bool:
    with closing(app.connect()) as conn:
        return members.resolve(conn, CHANNEL, channel_user_id) is not None


def recording(message: Any) -> Any:
    if message is None:
        return None
    return getattr(message, "voice", None) or getattr(message, "audio", None)


def incoming_voice(update: Any, fetch: Any) -> IncomingMessage | None:
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

    An edit is live however it reads: a location sent once cannot be edited, and the last edit no
    longer carries the live period.
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
    name = getattr(user, "full_name", None)
    handle = getattr(user, "username", None)
    return " ".join(part for part in (name, f"@{handle}" if handle else None) if part) or None


def addressed_to_bot(update: Any, bot_username: str | None, bot_id: int | None) -> bool:
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
    return "\n".join(" ".join(line.split()) for line in cleaned.splitlines()).strip()


async def formatted(
    send: Callable[..., Awaitable[Any]],
    words: str,
    *,
    heading: bool = False,
    drawn: str | None = None,
    **extra: Any,
) -> Any:
    """Send one part as Telegram HTML (markup.py), or `drawn` if already HTML; if Telegram refuses
    the formatting, send the plain words so nothing is lost.
    """
    try:
        html_text = drawn if drawn is not None else markup.to_html(words, heading=heading)
        return await send(html_text, parse_mode=ParseMode.HTML, **extra)
    except BadRequest as exc:
        if "parse entities" not in str(exc).lower():
            raise
        log.warning("telegram: the formatting was refused, so it went as plain words (%s)", exc)
        return await send(words, **extra)


async def confirm(message: Any) -> None:
    """A group's "saved": a reaction (buzzes nobody), or where reactions are off the ✓ as a silent
    reply.
    """
    try:
        await message.set_reaction(routing.REACTION)
    except TelegramError as exc:
        log.info("telegram: no reaction here (%s), so the ✓ goes quietly", exc)
        await message.reply_text(routing.CONFIRMED, disable_notification=True)


def split_text(text: str, limit: int = int(MessageLimit.MAX_TEXT_LENGTH)) -> list[str]:
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
    """The buttons under a message: one row, or one per `row` key in the order they come
    (buttons.in_row)."""
    rows: dict[str, list[InlineKeyboardButton]] = {}
    for button in row:
        rows.setdefault(button.get("row", ""), []).append(
            InlineKeyboardButton(button["label"], callback_data=button["data"])
        )
    return InlineKeyboardMarkup(list(rows.values()))


def without_row(markup: Any, data: str) -> InlineKeyboardMarkup | None:
    """What stays under a message once the row holding the button tapped goes; None for none."""
    rows = [
        list(row)
        for row in getattr(markup, "inline_keyboard", None) or ()
        if not any(getattr(button, "callback_data", None) == data for button in row)
    ]
    return InlineKeyboardMarkup(rows) if rows else None


def tap_in_thread(app: App, query: Any) -> buttons.Tapped | None:
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
    from telegram import Bot

    async def _send() -> None:
        async with Bot(token) as bot:
            for chunk in split_text(text):
                await formatted(partial(bot.send_message, int(chat_id)), chunk)

    asyncio.run(_send())


class TelegramChannel:
    def __init__(self, app: App, *, token: str | None = None) -> None:
        self.app = app
        token = token or app.settings.telegram_bot_token
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        self._loop: asyncio.AbstractEventLoop | None = None
        self.username: str | None = None
        # Album photos by media group until handed over, and the tasks that hand them over, kept so
        # they are not dropped.
        self._albums: dict[str, list[Any]] = {}
        self._gathering: set[asyncio.Task[None]] = set()
        self.application: Application = (
            ApplicationBuilder().token(token).post_init(self._post_init).build()
        )
        self.application.add_handler(CommandHandler("start", self.on_start, filters=NEW))
        self.application.add_handler(
            CommandHandler(sorted(commands.NAMES), self.on_command, filters=NEW)
        )
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & NEW, self.on_message)
        )
        # Only when new: an edited caption would otherwise be paid for and answered twice.
        self.application.add_handler(
            MessageHandler((filters.VOICE | filters.AUDIO) & NEW, self.on_voice)
        )
        # Before what cannot be read, which takes every other file.
        self.application.add_handler(MessageHandler(PICTURES & NEW, self.on_photo))
        self.application.add_handler(MessageHandler(UNREADABLE & NEW, self.on_unread))
        self.application.add_handler(MessageHandler(filters.LOCATION, self.on_location))
        self.application.add_handler(CallbackQueryHandler(self.on_tap))
        self.application.add_handler(
            ChatMemberHandler(self.on_membership, ChatMemberHandler.MY_CHAT_MEMBER)
        )

    async def _post_init(self, application: Application) -> None:
        self._loop = asyncio.get_running_loop()
        self.app.senders[CHANNEL] = self.send_text_threadsafe
        self.app.button_senders[CHANNEL] = self.send_buttons_threadsafe
        me = await application.bot.get_me()
        self.username = me.username
        log.info("telegram: polling as @%s", me.username)
        await self.offer_commands(application.bot)

    async def offer_commands(self, bot: Any) -> None:
        """Telegram's "/" menu. Set only when it differs; a failure leaves the commands working,
        only unlisted.
        """
        wanted = [BotCommand(name, about) for name, about in commands.MENU]
        try:
            if list(await bot.get_my_commands()) != wanted:
                await bot.set_my_commands(wanted)
        except Exception:
            log.warning("telegram: the command menu could not be set", exc_info=True)

    async def facts(self) -> dict[str, Any]:
        """Whether the bot reads every message in a group (BotFather's privacy setting) or only
        mentions and replies.
        """
        me = await self.application.bot.get_me()
        return {"reads_groups": bool(me.can_read_all_group_messages)}

    async def on_membership(self, update: Any, context: Any) -> None:
        """Introduce her in a group she was added to by someone on the family list. No model
        call."""
        changed = getattr(update, "my_chat_member", None)
        if changed is None or changed.chat.type not in GROUP_TYPES:
            return
        joined = (
            changed.old_chat_member.status in OUTSIDE and changed.new_chat_member.status in INSIDE
        )
        if not joined or changed.from_user is None:
            return
        await asyncio.to_thread(self.app.refresh)
        try:
            me = await context.bot.get_me()
        except Exception as exc:
            log.info("telegram: could not ask Telegram about the bot to say hello (%s)", exc)
            return
        needs = self.app.settings.telegram_require_mention or not me.can_read_all_group_messages
        stored = await asyncio.to_thread(
            commands.joined_group,
            self.app,
            channel=CHANNEL,
            chat_id=str(changed.chat.id),
            added_by=str(changed.from_user.id),
            mentioned=needs,
            bot=me.username,
        )
        if stored is not None:
            # Stored first, as everything she says, so one that does not go now goes with the next
            # delivery job.
            await asyncio.to_thread(deliver, self.app, stored)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = incoming_from_update(update)
        if msg is None:
            return
        await self._answer(update, context.bot, msg, handle=commands.start)

    async def on_command(self, update: Any, context: Any) -> None:
        msg = incoming_from_update(update)
        if msg is None:
            return
        await self._answer(update, context.bot, msg, handle=commands.answer, heading=True)

    async def introduce(self, name: str, about: str) -> None:
        """Set the bot's contact name and description in Telegram, each only when it differs: a
        rename is rate-limited.
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
        addressed = in_group and addressed_to_bot(update, bot.username, bot.id)
        if in_group and self.app.settings.telegram_require_mention and not addressed:
            return
        msg = incoming_from_update(update)
        if msg is None:
            return
        if in_group:
            text = strip_mention(msg.text, bot.username)
            if not text:
                return
            msg = dataclasses.replace(msg, text=text)
        if self.app.settings.gather_seconds:
            await self._after_a_pause(update, bot, msg, quiet=in_group and not addressed)
        else:
            await self._answer(update, bot, msg, quiet=in_group and not addressed)

    async def _after_a_pause(
        self, update: Any, bot: Any, msg: IncomingMessage, *, quiet: bool
    ) -> None:
        """Keep a message now and answer it after `gather_seconds` with any the same person sends
        meanwhile. Returns at once so the next update is kept.
        """
        kept = await asyncio.to_thread(receive, self.app, msg)
        if kept is None:
            return
        if isinstance(kept, OutgoingMessage):
            await self._answer(update, bot, msg, handle=lambda _app, _msg: kept, quiet=quiet)
            return
        pause = self.app.settings.gather_seconds

        def later(app: App, message: IncomingMessage) -> OutgoingMessage | None:
            time.sleep(pause)
            return answer_gathered(app, message, kept)

        task = asyncio.get_running_loop().create_task(
            self._answer(update, bot, msg, handle=later, quiet=quiet)
        )
        self._gathering.add(task)
        task.add_done_callback(self._gathering.discard)

    async def on_voice(self, update: Any, context: Any) -> None:
        await asyncio.to_thread(self.app.refresh)
        chat = update.effective_chat
        bot = context.bot
        in_group = chat is not None and chat.type in GROUP_TYPES
        addressed = in_group and addressed_to_bot(update, bot.username, bot.id)
        if in_group and self.app.settings.telegram_require_mention and not addressed:
            return
        note = recording(update.effective_message)
        loop = asyncio.get_running_loop()

        def fetch() -> bytes:
            future = asyncio.run_coroutine_threadsafe(download(note), loop)
            return future.result(timeout=FETCH_SECONDS)

        msg = incoming_voice(update, fetch)
        if msg is None:
            return
        if in_group and msg.text:
            msg = dataclasses.replace(msg, text=strip_mention(msg.text, bot.username))
        await self._answer(update, bot, msg, quiet=in_group and not addressed)

    async def on_photo(self, update: Any, context: Any) -> None:
        await asyncio.to_thread(self.app.refresh)
        group = getattr(update.effective_message, "media_group_id", None)
        if group is None:
            await self._photos([update], context.bot)
            return
        album = self._albums.setdefault(str(group), [])
        album.append(update)
        if len(album) == 1:
            # Its own task: the rest of the album arrives as updates after this one has been
            # answered.
            task = asyncio.get_running_loop().create_task(self._album(str(group), context.bot))
            self._gathering.add(task)
            task.add_done_callback(self._gathering.discard)

    async def _album(self, group: str, bot: Any) -> None:
        await asyncio.sleep(ALBUM_SECONDS)
        try:
            await self._photos(self._albums.pop(group, []), bot)
        except Exception:
            log.exception("telegram: an album could not be answered")

    async def _photos(self, updates: list[Any], bot: Any) -> None:
        """Photos handed over as one message. In a group only when sent to her (mention in the
        caption, or a reply): each one looked at is paid for.
        """
        if not updates:
            return
        first = updates[0]
        chat, user = first.effective_chat, first.effective_user
        if chat is None or user is None:
            return
        in_group = chat.type in GROUP_TYPES
        if in_group and not any(addressed_to_bot(u, bot.username, bot.id) for u in updates):
            return
        loop = asyncio.get_running_loop()

        def fetcher(file: Any) -> Callable[[], bytes]:
            def fetch() -> bytes:
                future = asyncio.run_coroutine_threadsafe(download(file), loop)
                return future.result(timeout=FETCH_SECONDS)

            return fetch

        notes: list[PhotoNote] = []
        caption = ""
        for one in updates:
            found = picture(one.effective_message)
            if found is None:
                continue
            file, kind, size = found
            notes.append(PhotoNote(mime=kind, fetch=fetcher(file), size=size))
            caption = caption or (getattr(one.effective_message, "caption", None) or "").strip()
        if not notes:
            return
        msg = IncomingMessage(
            channel=CHANNEL,
            channel_update_id=str(first.update_id),
            chat_id=str(chat.id),
            channel_user_id=str(user.id),
            text=strip_mention(caption, bot.username if in_group else None),
            sender_name=sender_name(user),
            photos=tuple(notes),
        )
        await self._answer(first, bot, msg)

    async def on_unread(self, update: Any, context: Any) -> None:
        """A sticker, file or video. In a group only when sent to her."""
        await asyncio.to_thread(self.app.refresh)
        chat = update.effective_chat
        bot = context.bot
        in_group = chat is not None and chat.type in GROUP_TYPES
        addressed = in_group and addressed_to_bot(update, bot.username, bot.id)
        msg = incoming_unread(update, bot.username if in_group else None)
        if msg is None or (in_group and not addressed and not msg.text):
            return
        if not msg.text:
            await self._answer(update, bot, msg, handle=commands.cannot_read)
        elif not (in_group and self.app.settings.telegram_require_mention and not addressed):
            await self._answer(update, bot, msg, quiet=in_group and not addressed)

    @contextlib.asynccontextmanager
    async def _typing(self, bot: Any, chat_id: Any, *, shown: bool = True) -> AsyncIterator[None]:
        """Keep "typing…" up while the body runs; a failing indicator never holds up the reply."""

        async def show() -> None:
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                log.debug("typing action failed", exc_info=True)

        async def keep_up() -> None:
            waited = 0.0
            while waited + TYPING_EVERY <= TYPING_AT_MOST:
                await asyncio.sleep(TYPING_EVERY)
                waited += TYPING_EVERY
                await show()

        if not shown:
            yield
            return
        await show()
        again = asyncio.create_task(keep_up())
        try:
            yield
        finally:
            again.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await again

    async def _answer(
        self,
        update: Any,
        bot: Any,
        msg: IncomingMessage,
        handle: Callable[[App, IncomingMessage], OutgoingMessage | None] | None = None,
        *,
        quiet: bool = False,
        heading: bool = False,
    ) -> None:
        """Run the pipeline (or `handle`) on its own thread and send its reply, stored first, with
        "typing…" up.

        `quiet`: a group message not addressed to her gets no answer and no typing, though the
        pipeline still keeps a stranger's knock.
        """
        chat = update.effective_chat
        family = not quiet or await asyncio.to_thread(family_knows, self.app, msg.channel_user_id)
        async with self._typing(bot, chat.id, shown=family):
            reply = await asyncio.to_thread(handle or handle_incoming, self.app, msg)
        if reply is None or (quiet and reply.status == "unknown_sender"):
            return

        async def send_reply():
            if chat.type in GROUP_TYPES and routing.is_confirmation(reply.text):
                await confirm(update.effective_message)
                return
            chunks = split_text(reply.text)
            bold = heading and reply.status == "ok"
            for index, chunk in enumerate(chunks):
                extra = {}
                if reply.buttons and index == len(chunks) - 1:
                    extra["reply_markup"] = keyboard(reply.buttons)
                reply_text = update.effective_message.reply_text
                await formatted(reply_text, chunk, heading=bold and index == 0, **extra)

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
            await formatted(message.reply_text, reply.text)

        loop = asyncio.get_running_loop()

        def sender(_chat_id, _text):
            asyncio.run_coroutine_threadsafe(send_reply(), loop).result(timeout=120)

        await asyncio.to_thread(deliver, self.app, reply.out_message_id, sender)

    async def on_tap(self, update: Any, context: Any) -> None:
        """A button tapped: done by code, said in her words (buttons.py). Everyone in the chat sees
        who did what, and the buttons go: its own row, where a message has several.
        """
        query = update.callback_query
        if query is None:
            return
        await asyncio.to_thread(self.app.refresh)
        tapped = await asyncio.to_thread(tap_in_thread, self.app, query)
        try:
            await query.answer(tapped.toast if tapped else None)
        except Exception:
            log.debug("telegram: could not answer a tap", exc_info=True)
        if tapped is None or not tapped.finished:
            return
        words = getattr(query.message, "text", None) if query.message is not None else None
        left = without_row(getattr(query.message, "reply_markup", None), query.data or "")
        if tapped.note and words:
            kept = getattr(query.message, "text_html", None) or html.escape(words, quote=False)
            try:
                await formatted(
                    query.edit_message_text,
                    f"{words}\n\n{tapped.note}",
                    drawn=f"{kept}\n\n{markup.to_html(tapped.note)}",
                    **({"reply_markup": left} if left is not None else {}),
                )
                return
            except Exception:
                log.info("telegram: could not add who did it to a message", exc_info=True)
        try:
            await query.edit_message_reply_markup(reply_markup=left)
        except Exception:
            log.info("telegram: could not take the buttons off a message", exc_info=True)

    def send_text_threadsafe(self, chat_id: str, text: str) -> None:
        self._send_threadsafe(chat_id, text, None)

    def send_buttons_threadsafe(self, chat_id: str, text: str, row: list[dict[str, str]]) -> None:
        self._send_threadsafe(chat_id, text, row)

    def _send_threadsafe(self, chat_id: str, text: str, row: list[dict[str, str]] | None) -> None:
        if self._loop is None:
            raise RuntimeError("Telegram is not running")
        chunks = split_text(text)
        # A "saved" sent later than its turn cannot be a reaction; in a group it goes silently.
        quiet = routing.is_group(CHANNEL, chat_id) and routing.is_confirmation(text)
        hushed = {"disable_notification": True} if quiet else {}
        send = partial(self.application.bot.send_message, int(chat_id), **hushed)
        for index, chunk in enumerate(chunks):
            under = keyboard(row) if row and index == len(chunks) - 1 else None
            future = asyncio.run_coroutine_threadsafe(
                formatted(send, chunk, reply_markup=under), self._loop
            )
            future.result(timeout=30)

    async def start(self) -> None:
        """Start polling inside the running event loop. Raises InvalidToken for a bad token."""
        await self.application.initialize()
        await self._post_init(self.application)
        await self.application.start()
        assert self.application.updater is not None
        # bootstrap_retries=-1: a boot before the network is up, or a Telegram blip, must not end
        # the process.
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
        self.application.run_polling(allowed_updates=UPDATES, bootstrap_retries=-1)


class TelegramSupervisor:
    """Keeps the channel running with the token the settings hold now: a changed token reconnects
    within seconds, with no restart.

    A token Telegram refuses waits until it changes; one that merely cannot be reached is retried
    every `RETRY_SECONDS`. The bot's contact says who is speaking (`_introduce`), with no trip to
    BotFather.
    """

    CHECK_SECONDS = 5.0
    RETRY_SECONDS = 30.0
    # A privacy change in BotFather reaches the bot in no update, so it is asked again this often.
    FACTS_SECONDS = 300.0

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
        # For `_introduce`: what it was last asked to say, the settings that came from, and when
        # Telegram may be asked again.
        self._introduced: tuple[str, str] | None = None
        self._seen: Settings | None = None
        self._introduce_at = 0.0
        self._learn_at = 0.0

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
        if not state.startswith("connected"):
            self.app.channel_facts.pop(CHANNEL, None)

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
                await self._learn(running)
            await asyncio.to_thread(self._stop.wait, self.check_seconds)
        if running is not None:
            await running.stop()
        self._set("off")

    def _token_refused(self, refused: bool) -> None:
        """Noted for the Status page (alerts.py, kind telegram), or forgotten once it connects;
        never told on Telegram, which cannot carry it."""
        from familydb import alerts

        with closing(self.app.connect()) as conn:
            if refused:
                alerts.note(conn, "telegram", "", "the token was refused", self.app.clock.now())
            else:
                alerts.working(conn, "telegram")

    async def _open(self, token: str) -> tuple[Any, bool]:
        channel = self.make_channel(self.app, token)
        try:
            await channel.start()
        except InvalidToken:
            log.error("telegram: Telegram refused the bot token; replace it on the settings page")
            self._set("the token was refused by Telegram")
            await asyncio.to_thread(self._token_refused, True)
            await _quietly_stop(channel)
            return None, True
        except NetworkError as exc:
            log.warning("telegram: cannot reach Telegram (%s); trying again shortly", exc)
            self._set("cannot reach Telegram; trying again")
            await _quietly_stop(channel)
            return None, False
        name = getattr(channel, "username", None)
        self._set(f"connected as @{name}" if name else "connected")
        await asyncio.to_thread(self._token_refused, False)
        self._introduced = self._seen = None
        self._learn_at = 0.0
        return channel, False

    async def _learn(self, channel: Any) -> None:
        """What Telegram says of the bot (`TelegramChannel.facts`): after each connect and every
        `FACTS_SECONDS`. Never stops the channel.
        """
        if time.monotonic() < self._learn_at:
            return
        self._learn_at = time.monotonic() + self.FACTS_SECONDS
        try:
            self.app.channel_facts[CHANNEL] = await channel.facts()
        except Exception as exc:
            log.info("telegram: could not ask Telegram about the bot (%s)", exc)

    async def _introduce(self, channel: Any) -> None:
        """Make the contact say who is speaking: her name and /start line, or FamilyDB's under none.

        Asked after each connect, and again only when the name or introduction differs from what
        it was last asked to say. A wait Telegram asks for is waited out, across a reconnect too;
        Telegram out of reach is retried every `RETRY_SECONDS`; a refusal is logged and not
        retried until something changes. No model call.
        """
        settings = self.app.settings
        # App.refresh builds new settings whenever a stored value moves, so the same object means
        # nothing changed.
        if settings is self._seen or time.monotonic() < self._introduce_at:
            return
        self._seen = settings
        said = (personas.active(settings).name, voice.say(settings, "start"))
        if said == self._introduced:
            return
        try:
            await channel.introduce(*said)
        except RetryAfter as exc:
            wait = exc.retry_after
            seconds = wait.total_seconds() if isinstance(wait, timedelta) else float(wait)
            log.info("telegram: Telegram asks for %.0f seconds before her name is set", seconds)
            self._seen, self._introduce_at = None, time.monotonic() + seconds
            return
        except NetworkError as exc:
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
