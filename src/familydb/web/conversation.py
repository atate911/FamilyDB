"""Which conversation this visitor reads, and how its newest message stands, read from the log
and the web channel's memory: what the frame's pill, the chat page and the box every page carries
all ask, so none of them can disagree. No model call."""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app

from familydb import audience
from familydb.app import App
from familydb.base.config import Settings
from familydb.channels.web import DEFAULT_CHAT, Handing, WebChat
from familydb.store.messages import Message
from familydb.web import auth

# Where the browser keeps which of her messages it has seen (shell.py).
SEEN_KEY = "seen"
# How much of the thread a glance reads.
GLANCE_LIMIT = 12
# Minutes past the retry job's last attempt before a message is given up on by the page.
RETRY_SLACK_MINUTES = 5


def channel() -> WebChat:
    return current_app.config["FAMILYDB_CHAT"]


def private_chat(member_id: int) -> str:
    """A kid's own conversation, which a parent may read (docs/WISHES.md; audience.py)."""
    return audience.private_chat(member_id)


def is_kid() -> bool:
    """A kid, by roles.py: keeps a wish list and decides on nobody's."""
    visitor = auth.visitor()
    return visitor.member is not None and visitor.may("wish") and not visitor.may("decide")


def my_chat() -> str:
    """A kid talks in her own conversation; everybody else in the family's (audience.page_chat,
    which routing.py also asks, so the page and what is sent to it cannot disagree)."""
    visitor = auth.visitor()
    if visitor.member is not None and not visitor.may("decide"):
        return private_chat(visitor.member.id)
    return DEFAULT_CHAT


def waiting_on(
    last: Message | None, answered: set[int], *, busy: bool, now: datetime, settings: Settings
) -> str | None:
    """What the newest message is waiting for: None, "thinking", "retrying" or "lost". A message
    nothing is running for was interrupted by a restart; the retry job picks it up while it has
    attempts left, after which the page hands the text back."""
    if last is None or last.direction != "in" or last.id in answered:
        return None
    if busy:
        return "thinking"
    received = datetime.fromisoformat(last.received_at.replace("Z", "+00:00"))
    window = timedelta(
        minutes=settings.retry_interval_minutes * (settings.retry_max_attempts + 1)
        + RETRY_SLACK_MINUTES
    )
    attempts_left = not last.give_up and last.retries < settings.retry_max_attempts
    if attempts_left and now - received < window:
        return "retrying"
    return "lost"


def standing(
    app: App, thread: list[Message], chat_id: str = DEFAULT_CHAT
) -> tuple[str | None, Handing | None]:
    """How the newest message stands (see `waiting_on`), and a message just handed over that the
    log does not hold yet: the turn stores it a moment after the browser is back, so until then
    the page draws it from the channel's memory."""
    chat = channel()
    handing = chat.handing_over(chat_id)
    if handing is not None and any(m.channel_update_id == handing.update_id for m in thread):
        handing = None  # stored: the log shows it now
    if handing is not None:
        return "thinking", handing
    answered = {message.reply_to for message in thread if message.reply_to is not None}
    last = thread[-1] if thread else None
    busy = chat.busy(chat_id)
    return waiting_on(last, answered, busy=busy, now=app.clock.now(), settings=app.settings), None
