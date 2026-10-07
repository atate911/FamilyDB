"""The chat page and the box Home shares with it. The form hands the message to the web channel,
which answers on its own thread; this page only reads the message log (`glance` is Home's brief
view of it) and, while an answer is on its way, asks the browser to fetch it again."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from familydb import personas, roles
from familydb.agent import spending
from familydb.app import App
from familydb.channels.web import DEFAULT_CHAT, MAX_MESSAGE, Handing, WebChat
from familydb.config import Settings
from familydb.store import calls
from familydb.store import members as member_store
from familydb.store import messages as message_store
from familydb.store.messages import Message
from familydb.web import auth, views
from familydb.web import status as status_page
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("chat", __name__)

# Who the person last said they were, while the family shares a password and the page cannot know.
WHO_KEY = "who"
# Whether this browser sends where it is with each message: off until someone ticks the box.
WHERE_KEY = "send_where"
THREAD_LIMIT = 60
# While an answer is on its way a page asks again soon, then less often, then stops and leaves a
# visible link: a page left open does not ask all night. Seconds before each next look, by what the
# message is waiting for; a message waiting on the retry job takes minutes, so it asks less often.
REFRESH_STEPS = {"thinking": (3, 5, 10, 10, 10, 10, 10), "retrying": (30, 30)}
REFRESH_SECONDS = REFRESH_STEPS["thinking"][0]
# The newest line carries this id and every way back points at it: without a script nothing else
# scrolls the page.
LATEST = "latest"
NOBODY = "Say who is asking."
NO_FAMILY = "There is nobody in the family list yet. Add someone on the Family page."
RETRY_REFRESH_SECONDS = REFRESH_STEPS["retrying"][0]
# `n` this far along asks no more: the page's own "Stop updating" link.
STOP_LOOKING = len(REFRESH_STEPS["thinking"])
# Slack on top of every attempt the settings allow, a retry interval apart.
RETRY_SLACK_MINUTES = 5
# What the page says in her place while the newest message waits: its words, no model call.
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
# For somebody who does not see how the bot works (a kid, roles.py `browse`).
RETRYING_PLAIN = "{name} will answer that soon. The answer will show here when it arrives."
PROMPT = "Message {name}"
LOCKED = "You can write again once {name} has answered."
HOME_PROMPT = "Plans for the weekend, an idea to keep, a reminder, the calendar…"
KID_HOME_PROMPT = "Something you\u2019d like, a question, something fun to do…"
# Atop a kid's list: goes to her conversation, where it is sorted.
KID_LIST_PROMPT = "Something you\u2019d like, a question, an idea… {name} will sort it out"
KID_LIST_LABEL = "Tell {name} anything"
# Home's briefer version of the chat's states.
AT_HOME = {
    "thinking": "Answering a message now.",
    "retrying": "A message was interrupted by a restart. It will be tried again shortly.",
    "lost": "The last message was not answered. It is back in the chat, ready to send again.",
}
AT_HOME_PLAIN = {**AT_HOME, "retrying": "{name} will answer your message soon."}
RECENT = timedelta(hours=24)
GLANCE_LIMIT = 12


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _chat() -> WebChat:
    return current_app.config["FAMILYDB_CHAT"]


# A kid's own conversation, which a parent may read (docs/WISHES.md).
PRIVATE = "member:{id}"


def private_chat(member_id: int) -> str:
    return PRIVATE.format(id=member_id)


def messages_left(app: App, conn: Any, member: member_store.Member | None) -> int | None:
    """How many more messages a kid may send today, counted as the pipeline counts them; None for
    anybody the limit does not hold (grown-ups, or no limit set)."""
    limit = app.settings.kid_daily_messages
    if member is None or not limit or not roles.daily_limited(member.role):
        return None
    since = spending.day_start(app.settings, app.clock.now())
    return max(0, limit - calls.answered_for(conn, member.id, since=since))


def is_kid() -> bool:
    """A kid, by roles.py: keeps a wish list and decides on nobody's."""
    visitor = auth.visitor()
    return visitor.member is not None and visitor.may("wish") and not visitor.may("decide")


def my_chat() -> str:
    """A kid talks in her own conversation; everybody else in the family's."""
    visitor = auth.visitor()
    if visitor.member is not None and not visitor.may("decide"):
        return private_chat(visitor.member.id)
    return DEFAULT_CHAT


def _who(names: list[str]) -> str | None:
    """Whoever is signed in, or what this session last chose while they are still family."""
    if (me := auth.visitor().name) is not None:
        return me
    chosen = session.get(WHO_KEY)
    if chosen in names:
        return chosen
    return names[0] if len(names) == 1 else None


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


def box(family: list[str], *, locked: bool = False, prompt: str = PROMPT) -> dict[str, Any]:
    """What the box needs wherever it is drawn."""
    name = personas.active(_app().settings).name
    return {
        "family": family,
        "who": _who(family),
        "send_where": bool(session.get(WHERE_KEY)),
        "locked": locked,
        "placeholder": (LOCKED if locked else prompt).format(name=name),
    }


def asked() -> str | None:
    """A question handed over by a link; it waits in the box until Send."""
    return request.args.get("ask", "")[:MAX_MESSAGE].strip() or None


def standing(
    app: App, thread: list[Message], chat_id: str = DEFAULT_CHAT
) -> tuple[str | None, Handing | None]:
    """How the newest message stands (see `waiting_on`), and a message just handed over that the
    log does not hold yet: the turn stores it a moment after the browser is back, so until then
    the page draws it from the channel's memory."""
    chat = _chat()
    handing = chat.handing_over(chat_id)
    if handing is not None and any(m.channel_update_id == handing.update_id for m in thread):
        handing = None  # stored: the log shows it now
    if handing is not None:
        return "thinking", handing
    answered = {message.reply_to for message in thread if message.reply_to is not None}
    last = thread[-1] if thread else None
    busy = chat.busy(chat_id)
    return waiting_on(last, answered, busy=busy, now=app.clock.now(), settings=app.settings), None


def glance(app: App, conn: Any) -> dict[str, Any]:
    """How the conversation stands, for Home, read from the log like the chat page."""
    chat_id = my_chat()
    thread = message_store.last_for_chat(conn, chat_id, limit=GLANCE_LIMIT)
    now = app.clock.now()
    state, _ = standing(app, thread, chat_id)
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
                assistant=personas.active(app.settings).name,
            )
    notes = AT_HOME if auth.visitor().may("browse") else AT_HOME_PLAIN
    name = personas.active(app.settings).name
    return {"state": state, "note": notes.get(state or "", "").format(name=name), "line": line}


def refresh_after(state: str | None, looked: int) -> int | None:
    """Seconds before the page next asks for the answer, or None once it has asked enough.
    `looked` is how many times it already has."""
    steps = REFRESH_STEPS.get(state or "", ())
    return steps[looked] if 0 <= looked < len(steps) else None


def page(
    *,
    error: str | None = None,
    typed: str | None = None,
    status: int = 200,
    reading: member_store.Member | None = None,
    before: int | None = None,
    looked: int = 0,
) -> Any:
    """Draw the chat. `reading` is a kid whose conversation a parent is reading: no box. `before`
    is the message to read earlier ones than; `looked` how often the page has already asked."""
    app = _app()
    visitor = auth.visitor()
    chat_id = private_chat(reading.id) if reading is not None else my_chat()
    tz = app.settings.tzinfo
    assistant = personas.active(app.settings).name
    kid_chat = chat_id != DEFAULT_CHAT and reading is None
    with closing(app.connect()) as conn:
        family = member_store.list_all(conn)
        thread = message_store.last_for_chat(conn, chat_id, limit=THREAD_LIMIT, before=before)
        older = bool(thread) and message_store.has_before(conn, chat_id, thread[0].id)
        kids = [m for m in family if m.role == "kid"] if visitor.may("decide") else []
        names = {member.id: member.display_name for member in family}
        slots = views.slot_map(family)
        convos = _conversations(conn, app, family, kids, chat_id, assistant) if kids else []
        if kid_chat:  # hers is the only one, drawn the same way
            said = views.snippet(thread[-1] if thread else None, assistant, names)
            convos = [
                {
                    **views.person_of(visitor.name, slots),
                    "name": f"You and {assistant}",
                    "href": url_for("chat.show", _anchor=LATEST),
                    "current": True,
                    "snippet": said or "No messages yet",
                }
            ]
        left = messages_left(app, conn, visitor.member)
    # The log keeps a turn's tool calls against the question; the page shows them under the
    # answer to those who browse the household. A kid never sees how it works (DESIGN.md 16).
    answered = {message.reply_to for message in thread if message.reply_to is not None}
    actions = {message.id: message.actions for message in thread}
    lines = [
        views.chat_line(
            message,
            names,
            tz,
            did=views.tools_used(actions.get(message.reply_to)) if visitor.may("browse") else [],
            waiting=message.id not in answered,
            assistant=assistant,
            slots=slots,
        )
        for message in thread
    ]
    last = thread[-1] if thread else None
    # Older messages are only to be read: nothing is on its way there, so nothing waits.
    state, handing = (None, None) if before else standing(app, thread, chat_id)
    if handing is not None:
        lines.append(
            views.handed_line(handing.member_name, handing.text, app.clock.now(), tz, slots)
        )
    today = app.clock.today()
    for line in lines:  # where the day changes, the thread says so
        line["heading"] = views.day_heading(line["day"], today)
    # A page holding typed words never refreshes (it would lose them); with nothing typed the box
    # is closed while an answer is on its way.
    held = bool(typed and typed.strip())
    locked = state == "thinking" and not held
    refresh = None if held else refresh_after(state, looked)
    retrying = RETRYING if visitor.may("browse") else RETRYING_PLAIN
    pending = {
        "thinking": HELD if held else THINKING,
        "retrying": retrying.format(name=assistant),
        "lost": LOST,
    }
    who_here = _room(family, chat_id, reading, assistant, slots)
    with_kid = {"with": reading.id} if reading else {}
    return (
        render_template(
            "chat.html",
            lines=lines,
            **box([member.display_name for member in family], locked=locked),
            state=state,
            pending=pending.get(state or ""),
            typed=typed or (last.text if state == "lost" and last else None),
            error=error or (NO_FAMILY if not family else None),
            refresh=refresh,
            # With the box open, the script looks again, only on a GET (reloading a post resends).
            look_again=refresh if refresh and not locked and request.method == "GET" else None,
            here=url_for(
                "chat.show", n=looked + 1, **with_kid, _anchor=LATEST
            ),  # the next look, one further along
            check=url_for("chat.show", **with_kid, _anchor=LATEST),  # a look from the start
            # Without this the page reloads itself with no way to stop it (WCAG 2.2.1).
            stop=url_for("chat.show", n=STOP_LOOKING, **with_kid, _anchor=LATEST)
            if refresh
            else None,
            latest=LATEST,
            reading=reading.display_name if reading else None,
            private=kid_chat,
            convos=convos,
            room=who_here,
            earlier=url_for("chat.show", before=thread[0].id, **with_kid) if older else None,
            newest=url_for("chat.show", **with_kid, _anchor=LATEST) if before else None,
            where="chat",
            readers=_readers(family),
            telegram=_telegram(app) if visitor.may("browse") else None,
            me=_me(visitor, slots),
            left=left,
        ),
        status,
    )


def _readers(family: list[member_store.Member]) -> str:
    """Who may read a kid's conversation: the people who decide, as "Sam and Alex"."""
    return views.names_text(
        [{"name": m.display_name} for m in family if roles.may(m.role, "decide")]
    )


def _me(visitor: auth.Visitor, slots: dict[str, int]) -> dict[str, Any] | None:
    """The person writing, with their colour; None while the family shares one password."""
    return views.person_of(visitor.name, slots) if visitor.name else None


def _telegram(app: App) -> tuple[str, str]:
    """How the other way in stands, for a grown-up: (the tag's state, its words)."""
    if status_page.telegram_name(app):
        return "ok", "Telegram: connected"
    return "better", "Telegram: not connected"


def _room(
    family: list[member_store.Member],
    chat_id: str,
    reading: member_store.Member | None,
    assistant: str,
    slots: dict[str, int],
) -> dict[str, Any]:
    """Whose conversation this is: who is in it, and what it is called."""
    if reading is not None:
        return {
            "title": f"{reading.display_name} and {assistant}",
            "line": "Her own conversation, for you to read",
            "people": [views.person_of(reading.display_name, slots)],
        }
    if chat_id != DEFAULT_CHAT:
        return {
            "title": f"You and {assistant}",
            "line": "",
            "people": [views.person_of(auth.visitor().name, slots)],
        }
    people = [views.person_of(m.display_name, slots) for m in family]
    return {
        "title": "Family",
        "line": views.names_text([*people, {"name": assistant}]),
        "people": people,
    }


def _conversations(
    conn: Any,
    app: App,
    family: list[member_store.Member],
    kids: list[member_store.Member],
    chat_id: str,
    assistant: str,
) -> list[dict[str, Any]]:
    """The family's conversation and each kid's, for a parent to move between, with the last thing
    said in each."""
    names = {member.id: member.display_name for member in family}
    slots = views.slot_map(family)
    rows = [
        {
            "name": "Family",
            "slot": 0,
            "initial": "",
            "href": url_for("chat.show", _anchor=LATEST),
            "current": chat_id == DEFAULT_CHAT,
            "snippet": views.snippet(_last(conn, DEFAULT_CHAT), assistant, names),
        }
    ]
    for kid in kids:
        mine = private_chat(kid.id)
        latest = _last(conn, mine)
        # When she last wrote, never what: her words belong to her conversation, not this page.
        said = (
            f"{kid.display_name} and {assistant} · last message "
            f"{views.local_moment(latest.received_at, app.settings.tzinfo)}"
            if latest
            else f"{kid.display_name} and {assistant} · no messages yet"
        )
        rows.append(
            {
                "name": kid.display_name,
                "slot": views.slot_of(kid.display_name, slots),
                "initial": kid.display_name[:1].upper(),
                "href": url_for("chat.show", **{"with": kid.id}, _anchor=LATEST),
                "current": chat_id == mine,
                "snippet": said,
            }
        )
    return rows


def _last(conn: Any, chat_id: str) -> Message | None:
    found = message_store.last_for_chat(conn, chat_id, limit=1)
    return found[0] if found else None


def _number(name: str, ceiling: int) -> int | None:
    """A whole number from the address, kept inside bounds; None when there is none."""
    given = request.args.get(name, "")
    return min(int(given), ceiling) if given.isdigit() else None


@bp.get("/chat")
def show() -> Any:
    wanted = request.args.get("with", "")
    older = _number("before", 2**62)
    looked = _number("n", len(REFRESH_STEPS["thinking"])) or 0
    if not wanted:
        return page(typed=asked(), before=older, looked=looked)
    if not wanted.isdigit() or not auth.visitor().may("decide"):
        abort(404)
    with closing(_app().connect()) as conn:
        kid = member_store.get(conn, int(wanted))
    if kid is None or kid.role != "kid":
        abort(404)
    return page(reading=kid, before=older, looked=looked)


def _position(form: Any) -> tuple[float, float] | None:
    """Where the phone said it was; None when it said nothing or "Send where I am" is not ticked."""
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
    """Hand one message to the channel and come back to the thread. Home's box posts here too."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, typed=request.form.get("text", ""), status=400)
    text = request.form.get("text", "")
    # Signed in as themselves, they are who is asking whatever the form says.
    me = auth.visitor().name
    who = me or request.form.get("who", "").strip()
    if not who:
        return page(error=NOBODY, typed=text, status=400)
    sent = text
    if request.form.get("intent") == "save_idea" and text.strip():
        sent = message_store.CAPTURE_PREFIX + text
    if me is None:
        session[WHO_KEY] = who
    session[WHERE_KEY] = request.form.get(WHERE_KEY) == "1"  # the box stays as they left it
    if (complaint := _chat().ask(sent, who, my_chat(), _position(request.form))) is not None:
        return page(error=complaint, typed=text, status=400)
    log.info("web chat: %s asked something", who)
    # Redirect, since refreshing a POST would send the message again.
    return redirect(url_for("chat.show", _anchor=LATEST))
