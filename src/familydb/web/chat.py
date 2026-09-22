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
from familydb.channels.web import DEFAULT_CHAT, WebChat
from familydb.store import members as member_store
from familydb.store import messages as message_store
from familydb.web import auth, views

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
NO_FAMILY = "There is nobody in the family list yet. Add someone with `familydb member add`."
STALLED = (
    "That message was never answered: the bot was probably restarted while it was thinking. "
    "Send it again."
)


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
    # A message nothing has answered, with nothing thinking about it, is one whose turn died
    # with the process. Saying so beats refreshing for ever, and the text comes back in the box.
    last = thread[-1] if thread else None
    stalled = last is not None and last.direction == "in" and last.id not in answered
    return (
        render_template(
            "chat.html",
            lines=lines,
            who=_who([member.display_name for member in family]),
            family=[member.display_name for member in family],
            thinking=thinking,
            stalled=stalled and not thinking,
            again=last.text if stalled and not thinking and last else None,
            error=error or (NO_FAMILY if not family else None),
            typed=typed,
            refresh=REFRESH_SECONDS if thinking else None,
            here=url_for("chat.show", _anchor=LATEST),
            latest=LATEST,
            stalled_note=STALLED,
        ),
        status,
    )


@bp.get("/chat")
def show() -> Any:
    return page()


@bp.post("/chat")
def send() -> Response | Any:
    """Hand one message to the channel and come straight back to the thread."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, typed=request.form.get("text", ""), status=400)
    text = request.form.get("text", "")
    who = request.form.get("who", "").strip()
    if not who:
        return page(error=NOBODY, typed=text, status=400)
    session[WHO_KEY] = who
    if (complaint := _chat().ask(text, who, DEFAULT_CHAT)) is not None:
        return page(error=complaint, typed=text, status=400)
    log.info("web chat: %s asked something", who)
    # Redirect rather than render: the browser is about to be asked to refresh this page every
    # few seconds, and refreshing a POST would send the message again.
    return redirect(url_for("chat.show", _anchor=LATEST))
