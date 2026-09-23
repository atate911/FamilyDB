"""The chat page: ask the bot something without opening Telegram.

Nothing is thought about here. The form hands the message to the web channel, which answers on
its own thread, and this page only ever reads the message log. That is why it needs no
JavaScript: while an answer is on its way the page asks the browser to fetch it again in a few
seconds, and stops asking as soon as the reply is in the log or the turn has given up.

Writing, then, is the pipeline's: the same dedupe, the same allowlist, the same stored turn as a
message from any other channel. Nothing in this module touches a table.
"""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from familydb.app import App
from familydb.channels.web import DEFAULT_CHAT, MAX_MESSAGE, WebChat
from familydb.config import Settings
from familydb.store import members as member_store
from familydb.store import messages as message_store
from familydb.store.messages import Message
from familydb.web import auth, views
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("chat", __name__)

# Who the person last said they were. Not who they are: the page is behind one family password
# and cannot know that. It is remembered so nobody has to say it with every message.
WHO_KEY = "who"
THREAD_LIMIT = 60
# How long the browser waits before asking again while a reply is on its way. A turn takes a few
# seconds when it answers straight off and the better part of a minute when it runs tools, so
# this is a compromise: short enough to feel like a chat, long enough not to be a poll.
REFRESH_SECONDS = 3
# The newest line carries this id, and every way back to the page points at it: a redirect
# after sending, the refresh while waiting, and the link in the bar. Without a script nothing
# can scroll a page, and a chat read from the top is a chat read backwards.
LATEST = "latest"
NOBODY = "Say who is asking."
NO_FAMILY = "There is nobody in the family list yet. Add someone on the Family page."
# While a message a restart interrupted waits for the retry job, the page asks again this
# often: nothing is running yet, so the three-second pace would only be noise.
RETRY_REFRESH_SECONDS = 30
# How long to keep saying "it will be retried" before admitting it will not: every attempt the
# settings allow, a retry interval apart, and a little slack for the job's own schedule.
RETRY_SLACK_MINUTES = 5
RETRYING = (
    "That message was interrupted, probably by a restart. It will be tried again automatically "
    "within a few minutes, and the answer will appear here."
)
LOST = "That message was not answered. Send it again if it still matters."


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _chat() -> WebChat:
    return current_app.config["FAMILYDB_CHAT"]


def _who(names: list[str]) -> str | None:
    """Who the page will speak as: what this session last chose, while they are still family."""
    chosen = session.get(WHO_KEY)
    if chosen in names:
        return chosen
    return names[0] if len(names) == 1 else None


def waiting_on(
    last: Message | None, answered: set[int], *, busy: bool, now: datetime, settings: Settings
) -> str | None:
    """What the newest message is waiting for: None, "thinking", "retrying" or "lost".

    Thinking is a turn running now, from the page or from the retry job. A message nothing is
    running for is one a restart interrupted; the retry job picks those up, so for as long as
    it still has attempts left the page says so and checks back now and then. After that the
    page stops promising and hands the text back.
    """
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


def page(*, error: str | None = None, typed: str | None = None, status: int = 200) -> Any:
    """Draw the chat. Read fresh every time, because the answer arrives on another thread."""
    app = _app()
    thinking = _chat().busy(DEFAULT_CHAT)
    with closing(app.connect()) as conn:
        family = member_store.list_all(conn)
        thread = message_store.last_for_chat(conn, DEFAULT_CHAT, limit=THREAD_LIMIT)
    names = {member.id: member.display_name for member in family}
    # The log keeps a turn's tool calls against the question; the page shows them under the
    # answer. Pairing them here also says which questions have been answered at all.
    answered = {message.reply_to for message in thread if message.reply_to is not None}
    actions = {message.id: message.actions for message in thread}
    lines = [
        views.chat_line(
            message,
            names,
            app.settings.tzinfo,
            did=views.tools_used(actions.get(message.reply_to)),
            waiting=message.id not in answered,
        )
        for message in thread
    ]
    last = thread[-1] if thread else None
    state = waiting_on(last, answered, busy=thinking, now=app.clock.now(), settings=app.settings)
    refresh = {"thinking": REFRESH_SECONDS, "retrying": RETRY_REFRESH_SECONDS}.get(state or "")
    return (
        render_template(
            "chat.html",
            lines=lines,
            who=_who([member.display_name for member in family]),
            family=[member.display_name for member in family],
            thinking=state == "thinking",
            note={"retrying": RETRYING, "lost": LOST}.get(state or ""),
            again=last.text if state == "lost" and last else None,
            error=error or (NO_FAMILY if not family else None),
            typed=typed,
            refresh=refresh,
            here=url_for("chat.show", _anchor=LATEST),
            latest=LATEST,
        ),
        status,
    )


@bp.get("/chat")
def show() -> Any:
    # A question handed over by a link, such as the home page's "what should we do this
    # weekend?", waits in the box; nothing is sent until somebody presses Send.
    asked = request.args.get("ask", "")[:MAX_MESSAGE].strip()
    return page(typed=asked or None)


@bp.post("/chat")
@once
def send() -> Response | Any:
    """Hand one message to the channel and come straight back to the thread."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, typed=request.form.get("text", ""), status=400)
    text = request.form.get("text", "")
    who = request.form.get("who", "").strip()
    if not who:
        return page(error=NOBODY, typed=text, status=400)
    sent = text
    if request.form.get("intent") == "save_idea" and text.strip():
        sent = message_store.CAPTURE_PREFIX + text
    session[WHO_KEY] = who
    if (complaint := _chat().ask(sent, who, DEFAULT_CHAT)) is not None:
        return page(error=complaint, typed=text, status=400)
    log.info("web chat: %s asked something", who)
    # Redirect rather than render: the browser is about to be asked to refresh this page every
    # few seconds, and refreshing a POST would send the message again.
    return redirect(url_for("chat.show", _anchor=LATEST))
