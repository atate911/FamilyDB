"""The chat page, where the family talks to her, and the box Home shares with it.

Nothing is thought about here. The form hands the message to the web channel, which answers on
its own thread, and this page only ever reads the message log. That is why it needs no
JavaScript: while an answer is on its way the page asks the browser to fetch it again in a few
seconds, and stops asking as soon as the reply is in the log or the turn has given up.

Home shows the same conversation in brief: `glance` says how it stands and what she said last,
read from the same log with no model call, and Home's box posts here, so a message started
there lands in the thread it joins.

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

from familydb import personas
from familydb.app import App
from familydb.channels.web import DEFAULT_CHAT, MAX_MESSAGE, Handing, WebChat
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
# Whether this browser sends where it is with each message: off until someone ticks the box.
WHERE_KEY = "send_where"
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
# What the page says in her place while the newest message waits, as the last line of the
# thread. The page's words, not hers: no model call is made to say them.
THINKING = "Thinking about the last message. The answer will show here when it arrives."
HELD = (
    "Still answering the last message. What you wrote is kept in the box below: send it once "
    "the answer is in."
)
RETRYING = (
    "That message was interrupted, probably by a restart. It will be tried again automatically "
    "within a few minutes, and the answer will appear here."
)
LOST = "That message was not answered. Send it again if it still matters."
# What the empty box says, on Home and in the chat alike: who it goes to, and while an answer
# is on its way, why it is closed.
PROMPT = "Message {name}"
LOCKED = "You can write again once {name} has answered."
# On Home, under her question, what the box is for: what she takes on, without saying what she is.
HOME_PROMPT = "Plans for the weekend, an idea to keep, a reminder, the calendar…"
# The same states as Home puts them, more briefly: the conversation is one tap away.
AT_HOME = {
    "thinking": "Answering a message now.",
    "retrying": "A message was interrupted by a restart. It will be tried again shortly.",
    "lost": "The last message was not answered. It is back in the chat, ready to send again.",
}
# What she said last stays on Home for this long; after that it is only in the chat.
RECENT = timedelta(hours=24)
# Enough of the log to know how its newest message stands and to find her last line.
GLANCE_LIMIT = 12


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


def box(family: list[str], *, locked: bool = False, prompt: str = PROMPT) -> dict[str, Any]:
    """What the box needs wherever it is drawn: who may speak, who spoke last, whether this
    browser sends where it is, whether it is closed while an answer is on its way, and what it
    says while it is empty."""
    name = personas.display_name(_app().settings)
    return {
        "family": family,
        "who": _who(family),
        "send_where": bool(session.get(WHERE_KEY)),
        "locked": locked,
        "placeholder": (LOCKED if locked else prompt).format(name=name),
    }


def asked() -> str | None:
    """A question handed over by a link, which waits in the box until somebody presses Send."""
    return request.args.get("ask", "")[:MAX_MESSAGE].strip() or None


def standing(app: App, thread: list[Message]) -> tuple[str | None, Handing | None]:
    """How the newest message stands (see `waiting_on`), and a message just handed over that
    the log does not hold yet.

    A turn stores its message a moment after it starts, and the browser is back sooner. Until
    the log has it, the page draws it from the channel's memory, and it is being thought about.
    """
    chat = _chat()
    handing = chat.handing_over(DEFAULT_CHAT)
    if handing is not None and any(m.channel_update_id == handing.update_id for m in thread):
        handing = None  # stored: the log shows it now
    if handing is not None:
        return "thinking", handing
    answered = {message.reply_to for message in thread if message.reply_to is not None}
    last = thread[-1] if thread else None
    busy = chat.busy(DEFAULT_CHAT)
    return waiting_on(last, answered, busy=busy, now=app.clock.now(), settings=app.settings), None


def glance(app: App, conn: Any) -> dict[str, Any]:
    """How the conversation stands, for Home: waiting on her, or the last thing she said lately.

    Read from the log like the chat page, so the two never disagree, and asked of nobody.
    """
    thread = message_store.last_for_chat(conn, DEFAULT_CHAT, limit=GLANCE_LIMIT)
    now = app.clock.now()
    state, _ = standing(app, thread)
    said = next((message for message in reversed(thread) if message.direction == "out"), None)
    line = None
    if state is None and said is not None:
        when = datetime.fromisoformat(said.received_at.replace("Z", "+00:00"))
        if now - when < RECENT:
            line = views.chat_line(
                said,
                {},
                app.settings.tzinfo,
                did=[],
                waiting=False,
                assistant=personas.display_name(app.settings),
            )
    return {"state": state, "note": AT_HOME.get(state or ""), "line": line}


def page(*, error: str | None = None, typed: str | None = None, status: int = 200) -> Any:
    """Draw the chat. Read fresh every time, because the answer arrives on another thread."""
    app = _app()
    with closing(app.connect()) as conn:
        family = member_store.list_all(conn)
        thread = message_store.last_for_chat(conn, DEFAULT_CHAT, limit=THREAD_LIMIT)
    names = {member.id: member.display_name for member in family}
    assistant = personas.display_name(app.settings)
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
            assistant=assistant,
        )
        for message in thread
    ]
    last = thread[-1] if thread else None
    state, handing = standing(app, thread)
    if handing is not None:
        lines.append(
            views.handed_line(
                handing.member_name, handing.text, app.clock.now(), app.settings.tzinfo
            )
        )
    # A page holding words somebody typed never fetches itself again: the refresh would take
    # them with it. While an answer is on its way and nothing is typed, the box is closed
    # instead, so there is nothing to lose; it opens again with the answer.
    held = bool(typed and typed.strip())
    locked = state == "thinking" and not held
    refresh = None
    if not held:
        refresh = {"thinking": REFRESH_SECONDS, "retrying": RETRY_REFRESH_SECONDS}.get(state or "")
    pending = {"thinking": HELD if held else THINKING, "retrying": RETRYING, "lost": LOST}
    return (
        render_template(
            "chat.html",
            lines=lines,
            **box([member.display_name for member in family], locked=locked),
            state=state,
            pending=pending.get(state or ""),
            # A message nobody will answer now comes back to the box, to send again.
            typed=typed or (last.text if state == "lost" and last else None),
            starters=[] if lines else views.starters(app.clock.today()),
            error=error or (NO_FAMILY if not family else None),
            refresh=refresh,
            # With the box open, the script looks again instead, and never while somebody is
            # writing; only on a page drawn for a visit, since reloading a post would resend it.
            look_again=refresh if refresh and not locked and request.method == "GET" else None,
            here=url_for("chat.show", _anchor=LATEST),
            latest=LATEST,
        ),
        status,
    )


@bp.get("/chat")
def show() -> Any:
    return page(typed=asked())


def _position(form: Any) -> tuple[float, float] | None:
    """Where the phone said it was, from the page's one script; None when it said nothing, or
    when nobody ticked "Send where I am" (a position without it is not kept)."""
    if form.get(WHERE_KEY) != "1":
        return None
    try:
        lat, lon = float(form.get("lat", "")), float(form.get("lon", ""))
    except ValueError:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None  # also refuses nan and inf, which compare false with everything
    return lat, lon


@bp.post("/chat")
@once
def send() -> Response | Any:
    """Hand one message to the channel and come straight back to the thread.

    Home's box posts here too, so a message started there lands in the conversation it joins.
    """
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
    session[WHERE_KEY] = request.form.get(WHERE_KEY) == "1"  # the box stays as they left it
    if (complaint := _chat().ask(sent, who, DEFAULT_CHAT, _position(request.form))) is not None:
        return page(error=complaint, typed=text, status=400)
    log.info("web chat: %s asked something", who)
    # Redirect rather than render: the browser is about to be asked to refresh this page every
    # few seconds, and refreshing a POST would send the message again.
    return redirect(url_for("chat.show", _anchor=LATEST))
