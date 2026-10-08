"""One inbound message, end to end: dedupe, allowlist, persist, think, reply, persist."""

from __future__ import annotations

import dataclasses
import logging
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from typing import Any

from familydb import (
    audience,
    buttons,
    family,
    memory,
    personas,
    roles,
    routing,
    undo,
    voice,
    whereabouts,
    wish_service,
    wording,
)
from familydb.agent import gateway, spending, uses
from familydb.agent.history import load_history
from familydb.agent.loop import MessagesAPI, TurnResult
from familydb.agent.providers import Audio, Picture, companies
from familydb.agent.render import (
    render_audience_line,
    render_folded_line,
    render_kid_line,
    render_location_line,
    render_memories,
    render_retry_note,
    render_user_turn,
)
from familydb.agent.spending import CompanyLimitReached, SpendingLimitReached
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage, PhotoNote
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.delivery import claim_also, deliver, hold_for_gathering, lease
from familydb.errors import AgentError
from familydb.store import calls, knocks, members, messages, suggestions, wishes
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

# Telegram's download limit for a bot.
MAX_AUDIO_BYTES = 20 * 1024 * 1024
# What every vendor takes: Claude counts its five megabytes on the base64, a third larger than the
# picture.
MAX_PHOTO_BYTES = 3_900_000
# Each photo is a call of its own; the rest are said to be there.
MAX_PHOTOS = 4


class _Unseen(Exception):
    def __init__(self, error: str, event: str = "photo_unseen") -> None:
        super().__init__(error)
        self.error = error
        self.event = event


# The weekend digest's question is stored under this plus the day, so the retry job can tell it from
# a written message.
DIGEST_UPDATE = "digest:"


def handle_incoming(
    app: App,
    msg: IncomingMessage,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
    hearing: Any = None,
    seeing: Any = None,
) -> OutgoingMessage | None:
    """Process one message. Returns None for an update already seen (a restart, a retry)."""
    if conn is not None:
        return _handle(app, msg, api, conn, hearing, seeing)
    with closing(app.connect()) as own:
        return _handle(app, msg, api, own, hearing, seeing)


def handle_synthetic(
    app: App,
    msg: IncomingMessage,
    member: Member,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    """Process a message the bot wrote on a member's behalf (the weekend digest): a failure stores
    no notice, the retry job picks it up later.
    """
    if conn is None:
        with closing(app.connect()) as own:
            return handle_synthetic(app, msg, member, api=api, conn=own)
    if _seen(conn, msg):
        return None
    inbound_id = _store_inbound(app, conn, msg, member)
    if inbound_id is None:
        return None
    return _run(app, msg, member, inbound_id, api, conn, notify=False, kind="digest")


# How long past its pause a gathered message is kept from the retry job in case the answering
# process stops; as long as a claim, since it may wait for a turn to finish.
GATHER_HOLD_SECONDS = 300

# Turns in one chat run one at a time: a concurrent one would read the other's message as unanswered
# and might repeat what it asked.
_chat_locks: dict[tuple[str, str], threading.RLock] = {}
_chat_locks_guard = threading.Lock()


@contextmanager
def _one_at_a_time(channel: str, chat_id: str) -> Iterator[None]:
    with _chat_locks_guard:
        lock = _chat_locks.setdefault((channel, chat_id), threading.RLock())
    with lock:
        yield


def receive(
    app: App, msg: IncomingMessage, *, conn: sqlite3.Connection | None = None
) -> int | OutgoingMessage | None:
    """Keep a message to be answered after a pause (`answer_gathered`).

    None for an update already seen, a stranger's answer at once, or the stored message's id,
    held from the retry job meanwhile (delivery.GATHER).
    """
    if conn is None:
        with closing(app.connect()) as own:
            return receive(app, msg, conn=own)
    if _seen(conn, msg):
        return None
    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
        return _stranger(app, conn, msg)
    inbound_id = _store_inbound(app, conn, msg, member)
    if inbound_id is None:
        return None
    pause = app.settings.gather_seconds + GATHER_HOLD_SECONDS
    with transaction(conn):
        hold_for_gathering(
            conn, inbound_id, until=utc_iso(app.clock.now() + timedelta(seconds=pause))
        )
    return inbound_id


def answer_gathered(
    app: App,
    msg: IncomingMessage,
    inbound_id: int,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    """Answer a kept message once its pause is over, with every earlier one from the same person in
    this chat still waiting; not at all when a newer one is waiting, which answers this one.
    """
    if conn is None:
        with closing(app.connect()) as own:
            return answer_gathered(app, msg, inbound_id, api=api, conn=own)
    with _one_at_a_time(msg.channel, msg.chat_id):
        row = messages.get(conn, inbound_id)
        if row is None or row.status == "processed" or row.give_up or row.member_id is None:
            return None
        now = utc_iso(app.clock.now())
        if messages.gathering(conn, row.chat_id, row.member_id, after=inbound_id, now=now):
            return None
        member = members.get(conn, row.member_id)
        if member is None:
            return None
        earlier = messages.gathering(conn, row.chat_id, row.member_id, before=inbound_id, now=now)
        return _run(
            app,
            msg,
            member,
            inbound_id,
            api,
            conn,
            notify=True,
            gathered=[one.id for one in earlier],
        )


def _stranger(app: App, conn: sqlite3.Connection, msg: IncomingMessage) -> OutgoingMessage:
    log.warning("unknown sender %s on %s", msg.channel_user_id, msg.channel)
    with transaction(conn):
        knocks.record(
            conn,
            channel=msg.channel,
            channel_user_id=msg.channel_user_id,
            name=msg.sender_name,
            chat_id=msg.chat_id,
            now=app.clock.now(),
        )
    # Not stored, so the update itself chooses the words: the same knock sent again reads the same.
    return OutgoingMessage(
        msg.chat_id,
        voice.say(app.settings, "stranger", seed=msg.channel_update_id, id=msg.channel_user_id),
        "unknown_sender",
    )


def _handle(
    app: App,
    msg: IncomingMessage,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    hearing: Any = None,
    seeing: Any = None,
) -> OutgoingMessage | None:
    if _seen(conn, msg):
        return None

    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
        return _stranger(app, conn, msg)

    inbound_id = _store_inbound(app, conn, msg, member)
    if inbound_id is None:
        return None
    return _run(
        app, msg, member, inbound_id, api, conn, notify=True, hearing=hearing, seeing=seeing
    )


def _seen(conn: sqlite3.Connection, msg: IncomingMessage) -> bool:
    if msg.channel_update_id and messages.exists_update(conn, msg.channel, msg.channel_update_id):
        log.info("ignoring duplicate update %s/%s", msg.channel, msg.channel_update_id)
        return True
    return False


def _store_inbound(
    app: App, conn: sqlite3.Connection, msg: IncomingMessage, member: Member
) -> int | None:
    """Store the inbound message; None when the same update landed at the same moment.

    A voice note or photo is stored as a mark first, before a byte is fetched; its words replace
    the mark.
    """
    if msg.voice:
        text = messages.unheard(msg.voice.seconds)
    elif msg.photos:
        text = messages.unlooked(len(msg.photos))
    else:
        text = msg.text
    try:
        with transaction(conn):
            inbound = messages.insert_in(
                conn,
                channel=msg.channel,
                channel_update_id=msg.channel_update_id,
                chat_id=msg.chat_id,
                member_id=member.id,
                text=text,
                now=utc_iso(app.clock.now()),
            )
    except sqlite3.IntegrityError:
        if not msg.channel_update_id:
            raise
        log.info("update %s/%s arrived twice at once", msg.channel, msg.channel_update_id)
        return None
    return inbound.id


def _run(
    app: App,
    msg: IncomingMessage,
    member: Member,
    inbound_id: int,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    *,
    notify: bool,
    retry: bool = False,
    kind: str = "chat",
    hearing: Any = None,
    seeing: Any = None,
    gathered: list[int] | None = None,
) -> OutgoingMessage | None:
    with _one_at_a_time(msg.channel, msg.chat_id), lease(app, conn, inbound_id) as owned:
        if not owned:
            return None
        row = messages.get(conn, inbound_id)
        if row is None or row.status == "processed" or row.give_up:
            return None
        # Taken under this claim and folded in at once, so however this turn ends they go with it
        # and a retry answers the whole burst knowing what the first try did.
        taken = claim_also(app, conn, owned, gathered) if gathered else []
        if taken:
            with transaction(conn):
                messages.fold_into(conn, taken, inbound_id, now=utc_iso(app.clock.now()))
        folded = messages.folded_into(conn, inbound_id)
        current_member = members.get(conn, member.id)
        if current_member is None or not current_member.active:
            with transaction(conn):
                messages.mark_failed(
                    conn, inbound_id, "member_inactive", now=utc_iso(app.clock.now())
                )
                messages.give_up(conn, inbound_id)
            return None
        member = current_member
        if kind != "digest" and _over_daily_number(app, conn, member, inbound_id):
            # Kept but not answered, heard or retried: said so in her words, no model call.
            with transaction(conn):
                messages.give_up(conn, inbound_id)
            limit = app.settings.kid_daily_messages
            reply = voice.say(app.settings, "kid_limit", seed=inbound_id, limit=limit)
            return _fail(app, conn, msg, inbound_id, "kid_daily_limit", reply)
        if msg.voice is not None:
            heard = _hear(app, msg, inbound_id, conn, hearing)
            if isinstance(heard, OutgoingMessage):
                return heard
            msg = heard
        elif msg.photos:
            seen = _look(app, msg, inbound_id, conn, seeing)
            if isinstance(seen, OutgoingMessage):
                return seen
            msg = seen
        elif messages.is_unheard(row.text):
            # Stored, then the process stopped before it was heard. The recording is not kept, so
            # say so, even on a retry: it is final.
            return _not_heard(app, conn, msg, inbound_id, "stopped before it was heard")
        elif messages.is_unlooked(row.text):
            return _not_heard(
                app,
                conn,
                msg,
                inbound_id,
                "stopped before it was looked at",
                "photo_unseen",
                what="photo",
            )
        if retry:
            if row.retries >= app.settings.retry_max_attempts:
                return None
            with transaction(conn):
                conn.execute(
                    "UPDATE messages SET retries = retries + 1 WHERE id = ?", (inbound_id,)
                )
        if folded:
            msg = dataclasses.replace(msg, text="\n".join([*(f.text for f in folded), msg.text]))
        return _run_owned(
            app,
            msg,
            member,
            inbound_id,
            api,
            conn,
            notify=notify,
            retry=retry,
            kind=kind,
            gathered=[one.id for one in folded],
        )


def _over_daily_number(app: App, conn: sqlite3.Connection, member: Member, inbound_id: int) -> bool:
    """Whether a kid (roles.DAILY_LIMITED) has had as many model-answered messages today as the
    family allows.
    """
    limit = app.settings.kid_daily_messages
    if not limit or not roles.daily_limited(member.role):
        return False
    since = spending.day_start(app.settings, app.clock.now())
    return calls.answered_for(conn, member.id, since=since, other_than=inbound_id) >= limit


def _hear(
    app: App, msg: IncomingMessage, inbound_id: int, conn: sqlite3.Connection, hearing: Any
) -> IncomingMessage | OutgoingMessage:
    """A voice note's words, stored in place of its mark and handed on as the message's text.

    Or a notice, worded by code, saying why not (off, nobody who can hear, too long, not fetched,
    not heard, daily limit). The recording is not kept, so it is given up, not retried.
    """
    note = msg.voice
    assert note is not None
    settings = app.settings
    if not uses.on(settings, "hear"):
        return _not_heard(app, conn, msg, inbound_id, "voice notes are off", "voice_off")
    if not gateway.can_listen(settings, audio=hearing):
        return _not_heard(app, conn, msg, inbound_id, "nobody can hear", "voice_no_ears")
    minutes = settings.voice_max_minutes
    if note.seconds > minutes * 60 or (note.size or 0) > MAX_AUDIO_BYTES:
        return _not_heard(app, conn, msg, inbound_id, "too long", "voice_too_long", minutes=minutes)
    try:
        data = note.fetch()
    except Exception as exc:
        log.warning("could not fetch voice note %s: %s", inbound_id, exc)
        return _not_heard(app, conn, msg, inbound_id, f"not fetched: {type(exc).__name__}")
    if len(data) > MAX_AUDIO_BYTES:
        return _not_heard(
            app, conn, msg, inbound_id, "too large", "voice_too_long", minutes=minutes
        )
    try:
        heard = gateway.listen(
            settings=settings,
            conn=conn,
            clock=app.clock,
            audio=Audio(data=data, mime=note.mime, seconds=note.seconds, name=note.name),
            hints=_hints(app, conn),
            message_id=inbound_id,
            api=hearing,
        )
    except SpendingLimitReached as exc:
        return _not_heard(
            app, conn, msg, inbound_id, str(exc), "limit_reached", limit=f"{exc.limit:.2f}"
        )
    except AgentError as exc:
        return _not_heard(app, conn, msg, inbound_id, str(exc))
    words = heard.text.strip()
    if not words:
        return _not_heard(app, conn, msg, inbound_id, "no words in it")
    caption = msg.text.strip()
    text = messages.VOICE_PREFIX + words + (f"\n\n{caption}" if caption else "")
    log.info("heard voice note %s: %s s, %s characters", inbound_id, note.seconds, len(words))
    return _heard_as(conn, msg, inbound_id, text)


def _look(
    app: App, msg: IncomingMessage, inbound_id: int, conn: sqlite3.Connection, seeing: Any
) -> IncomingMessage | OutgoingMessage:
    """What a photo (or each of an album's) shows, stored in place of its mark with its caption
    after it.

    Or a notice, worded by code, saying why not. Of an album the first `MAX_PHOTOS` are looked at
    and the rest said not to be. The pictures are not kept, so it is given up, not retried.
    """
    notes = msg.photos
    settings = app.settings
    caption = msg.text.strip()
    if not uses.on(settings, "look"):
        if not caption:
            return _not_heard(
                app, conn, msg, inbound_id, "photos are off", "photo_off", what="photo"
            )
        what = "a photo" if len(notes) == 1 else f"{len(notes)} photos"
        return _heard_as(conn, msg, inbound_id, messages.unseen(what, caption))
    if not gateway.can_look(settings, api=seeing):
        return _not_heard(
            app, conn, msg, inbound_id, "nobody can look", "photo_unseen", what="photo"
        )
    hints = _hints(app, conn)
    seen: list[str | None] = []
    failed: _Unseen | None = None
    for note in notes[:MAX_PHOTOS]:
        try:
            seen.append(_look_at(app, conn, note, inbound_id, hints, seeing))
        except SpendingLimitReached as exc:
            return _not_heard(
                app,
                conn,
                msg,
                inbound_id,
                str(exc),
                "limit_reached",
                what="photo",
                limit=f"{exc.limit:.2f}",
            )
        except _Unseen as why:
            log.warning("photo in message %s not looked at: %s", inbound_id, why.error)
            seen.append(None)
            failed = failed or why
    if not any(seen):
        why = failed or _Unseen("nothing written down")
        return _not_heard(app, conn, msg, inbound_id, why.error, why.event, what="photo")
    written = messages.seen_in_photos(seen, len(notes))
    log.info("looked at %s photo(s) in message %s", len(seen), inbound_id)
    return _heard_as(conn, msg, inbound_id, written + (f"\n\n{caption}" if caption else ""))


def _look_at(
    app: App,
    conn: sqlite3.Connection,
    note: PhotoNote,
    inbound_id: int,
    hints: str,
    seeing: Any,
) -> str:
    if (note.size or 0) > MAX_PHOTO_BYTES:
        raise _Unseen("too large", "photo_too_large")
    try:
        data = note.fetch()
    except Exception as exc:
        raise _Unseen(f"not fetched: {type(exc).__name__}") from exc
    if len(data) > MAX_PHOTO_BYTES:
        raise _Unseen("too large", "photo_too_large")
    try:
        seen = gateway.look(
            settings=app.settings,
            conn=conn,
            clock=app.clock,
            picture=Picture(data=data, mime=note.mime),
            hints=hints,
            message_id=inbound_id,
            api=seeing,
        )
    except SpendingLimitReached:
        raise
    except AgentError as exc:
        raise _Unseen(str(exc)) from exc
    words = seen.text.strip()
    if not words:
        raise _Unseen("nothing written down")
    return words + " …" if seen.stop == "max_tokens" else words


def _heard_as(
    conn: sqlite3.Connection, msg: IncomingMessage, inbound_id: int, text: str
) -> IncomingMessage:
    with transaction(conn):
        messages.set_text(conn, inbound_id, text)
    return dataclasses.replace(msg, text=text, voice=None, photos=())


def _not_heard(
    app: App,
    conn: sqlite3.Connection,
    msg: IncomingMessage,
    inbound_id: int,
    error: str,
    event: str = "voice_unheard",
    *,
    what: str = "voice note",
    **facts: Any,
) -> OutgoingMessage:
    log.warning("%s in message %s not taken in: %s", what, inbound_id, error)
    with transaction(conn):
        messages.give_up(conn, inbound_id)
    # Seeded by the message like every notice here, so a resend reads the same.
    sender = members.resolve(conn, msg.channel, msg.channel_user_id)
    plain = audience.plain(conn, msg.channel, msg.chat_id, sender)
    notice = voice.say(app.settings, event, seed=inbound_id, plain=plain, **facts)
    return _fail(app, conn, msg, inbound_id, f"{what}: {error}", notice)


def _hints(app: App, conn: sqlite3.Connection) -> str:
    """Names a voice note may say, so they are written the family's way: members, her name, home.
    Same for every note, and short.
    """
    names = [member.display_name for member in members.list_all(conn) if member.active]
    names.append(personas.active(app.settings).name)
    hints = "Names: " + ", ".join(names) + "."
    if app.settings.home_area:
        hints += f" Home: {app.settings.home_area}."
    return hints


def _run_owned(
    app: App,
    msg: IncomingMessage,
    member: Member,
    inbound_id: int,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    *,
    notify: bool,
    retry: bool = False,
    kind: str = "chat",
    gathered: list[int] | None = None,
) -> OutgoingMessage:
    taken = app.held.take((msg.channel, msg.chat_id), app.clock.now())
    try:
        return _answer(
            app,
            msg,
            member,
            inbound_id,
            api,
            conn,
            notify=notify,
            retry=retry,
            kind=kind,
            taken=taken,
            gathered=gathered or [],
        )
    finally:
        app.held.let_go(taken, app.clock.now())


def _answer(
    app: App,
    msg: IncomingMessage,
    member: Member,
    inbound_id: int,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    *,
    notify: bool,
    retry: bool = False,
    kind: str = "chat",
    taken: list[voice.Held],
    gathered: list[int] | None = None,
) -> OutgoingMessage:
    """Think and persist the outcome. With notify off (a retry, the digest) failures stay silent.

    `gathered`: the earlier messages of a burst, folded into this one (`_run`).
    """
    gathered = gathered or []
    plain = audience.plain(conn, msg.channel, msg.chat_id, member)
    if not app.can_ask("chat", api=api):
        log.warning("message %s saved, but there is no model key to answer it with", inbound_id)
        with transaction(conn):
            messages.give_up(conn, inbound_id)
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            "no model key",
            voice.say(app.settings, "no_key", seed=inbound_id, plain=plain) if notify else None,
        )
    kid = roles.may(member.role, "wish") and not roles.may(member.role, "decide")
    if kid and spending.kid_used_up(conn, app.settings, app.clock.now(), member.id):
        log.info("message %s: %s's share of the day is used up", inbound_id, member.id)
        with transaction(conn):
            messages.give_up(conn, inbound_id)
        notice = voice.say(app.settings, "kid_share", seed=inbound_id, kid=member.display_name)
        return _fail(app, conn, msg, inbound_id, "kid share used up", notice if notify else None)
    try:
        result = _think(
            app,
            msg,
            member,
            inbound_id,
            api,
            conn,
            retry=retry,
            kind=kind,
            taken=taken,
            gathered=gathered,
            plain=plain,
        )
    except AgentError as exc:
        log.error("agent error on message %s: %s (retryable=%s)", inbound_id, exc, exc.retryable)
        if not exc.retryable:
            with transaction(conn):
                messages.give_up(conn, inbound_id)
        if isinstance(exc, SpendingLimitReached):
            reply = voice.say(
                app.settings,
                "limit_reached",
                seed=inbound_id,
                plain=plain,
                limit=f"{exc.limit:.2f}",
            )
        elif isinstance(exc, CompanyLimitReached):
            reply = voice.say(
                app.settings,
                "company_limit",
                seed=inbound_id,
                plain=plain,
                company=companies.label(exc.company, app.settings),
                limit=f"${exc.limit:.2f}",
            )
        else:
            reply = voice.say(
                app.settings,
                "retry_later" if exc.retryable else "cannot_reach",
                seed=inbound_id,
                plain=plain,
            )
        return _fail(app, conn, msg, inbound_id, str(exc), reply if notify else None)
    except Exception as exc:
        log.exception("unexpected error on message %s", inbound_id)
        error = f"{type(exc).__name__}: {exc}"
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            error,
            voice.say(app.settings, "retry_later", seed=inbound_id, plain=plain)
            if notify
            else None,
        )

    if result.status == "failed" and result.error == "max_iterations":
        # Given up for good, so a person who asked is told now, even on a retry; the digest asked
        # nobody and stays quiet.
        log.error("turn on message %s ran out of steps; not retrying it", inbound_id)
        with transaction(conn):
            messages.give_up(conn, inbound_id)
        notice = _gave_up_reply(app, result, inbound_id, plain) if kind != "digest" else None
        return _fail(app, conn, msg, inbound_id, "max_iterations", notice, result.actions)
    if result.status == "failed":
        log.error("turn failed on message %s: %s", inbound_id, result.error)
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            result.error or "failed",
            voice.say(app.settings, "retry_later", seed=inbound_id, plain=plain)
            if notify
            else None,
            result.actions,
        )

    reply_text = result.text or voice.say(app.settings, "done", seed=inbound_id)
    forgotten = [h.text for h in taken if h.mention.casefold() not in reply_text.casefold()]
    if forgotten:
        reply_text = "\n\n".join([reply_text, *forgotten])
    # One message with buttons (a reminder) goes with them; with several, which is which would be a
    # guess.
    carried = [
        held.buttons
        for held in (messages.get(conn, h.message_id) for h in taken)
        if held is not None and held.buttons
    ]
    reply_buttons = carried[0] if len(carried) == 1 else None
    now = utc_iso(app.clock.now())
    # In somebody's own Telegram chat, a reply that changed something can take it back: an Undo
    # under it (familydb/undo.py), on its own row. A group is spared one under every "saved".
    if msg.channel == "telegram" and not routing.is_group(msg.channel, msg.chat_id):
        since = utc_iso(app.clock.now() - undo.WINDOW)
        changed = calls.undoable_for(conn, [inbound_id], since=since).get(inbound_id)
        if changed is not None:
            carried_too = buttons.in_row(reply_buttons, "carried") if reply_buttons else []
            reply_buttons = carried_too + buttons.for_undo(int(changed["id"]))
    with transaction(conn):
        # Carried by this reply: marked sent with it, so the delivery job finds nothing.
        messages.mark_delivered(conn, [h.message_id for h in taken], now=now)
        outbound = messages.insert_out(
            conn,
            channel=msg.channel,
            chat_id=msg.chat_id,
            text=reply_text,
            reply_to=inbound_id,
            now=now,
            buttons=reply_buttons,
            sent_as="digest" if kind == "digest" else None,
        )
        messages.mark_processed(conn, inbound_id, result.actions, now=now)
        for action in result.actions:
            if action.get("tool") == "suggest" and action.get("suggestion_id"):
                suggestions.set_reply(conn, int(action["suggestion_id"]), outbound.id)
    app.held.done(taken)
    if any(action.get("tool") in ("turn_away", "update_wish") for action in result.actions):
        for waiting in wish_service.waiting_for_parents(conn):
            deliver(app, waiting)
    return OutgoingMessage(
        msg.chat_id,
        reply_text,
        result.status,
        inbound_id,
        outbound.id,
        result.actions,
        reply_buttons or [],
    )


def retry_message(
    app: App,
    message_id: int,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    if conn is None:
        with closing(app.connect()) as own:
            return retry_message(app, message_id, api=api, conn=own)
    row = messages.get(conn, message_id)
    if row is None or row.direction != "in" or row.status not in {"failed", "received"}:
        return None
    if row.give_up or row.retries >= app.settings.retry_max_attempts:
        return None
    if row.channel != "console" and row.channel not in app.senders:
        log.info("not retrying message %s: no sender for %s here", message_id, row.channel)
        return None
    member = members.get(conn, row.member_id) if row.member_id is not None else None
    if member is None:
        log.warning("cannot retry message %s: sender unknown", message_id)
        return None
    msg = IncomingMessage(
        channel=row.channel,
        channel_update_id=row.channel_update_id,
        chat_id=row.chat_id,
        channel_user_id=member.channel_user_id or member.display_name,
        text=row.text,
    )
    log.info("retrying message %s (attempt %s)", message_id, row.retries + 1)
    digest = (row.channel_update_id or "").startswith(DIGEST_UPDATE)
    kind = "digest" if digest else "retry"
    reply = _run(app, msg, member, message_id, api, conn, notify=False, retry=True, kind=kind)
    if reply is not None and reply.out_message_id is not None:
        deliver(app, reply.out_message_id)
    return reply


def _think(
    app: App,
    msg: IncomingMessage,
    member: Member,
    inbound_id: int,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    *,
    retry: bool = False,
    kind: str = "chat",
    taken: list[voice.Held] | None = None,
    gathered: list[int] | None = None,
    plain: bool = False,
) -> TurnResult:
    app.refresh(conn)
    settings = app.settings
    history = load_history(
        conn,
        msg.chat_id,
        clock=app.clock,
        limit=settings.history_limit,
        since_hours=settings.history_hours,
        exclude_message_id=inbound_id,
        exclude_replies_to=inbound_id if retry else None,
        also_exclude=gathered or (),
        before_id=None if retry else inbound_id,
    )
    origin = messages.get(conn, inbound_id)
    received_clock = (
        FixedClock(
            datetime.fromisoformat(origin.received_at), app.clock.tz, southern=app.clock.southern
        )
        if origin
        else app.clock
    )
    audience = render_audience_line(msg.channel, msg.chat_id, members.list_all(conn))
    current = render_user_turn(member.display_name, msg.text, received_clock, audience)
    shared = whereabouts.current(conn, member.id, app.clock.now())
    if shared is not None:
        current.append(
            render_location_line(
                member.display_name,
                shared.label,
                shared.lat,
                shared.lon,
                whereabouts.minutes_ago(shared, app.clock.now()),
            )
        )
    if roles.may(member.role, "wish") and not roles.may(member.role, "decide"):
        current.append(_kid_line(app, conn, member, msg.text, private=audience is None))
    remembered = render_memories(
        memory.choose(conn, msg.text, sender_id=member.id, today=app.clock.today())
    )
    if remembered:
        current.append(remembered)
    if taken:
        current.append(render_folded_line([held.text for held in taken]))
    if retry:
        current.append(
            "Processing retry now: "
            + app.clock.describe()
            + ". Resolve relative dates from the original message time above."
        )
        write_tools = {spec.name for spec in app.registry.specs() if spec.writes}
        note = render_retry_note(calls.tool_calls_for_message(conn, inbound_id), write_tools)
        if note:
            current.append(note)
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=app.clock,
        member=member,
        message_id=inbound_id,
        calendar=app.calendar,
        weather=app.weather,
        geocoder=app.geocoder,
        api=api,  # a stand-in for the discovery worker inside `suggest`, injected by tests
        discover_cache=app.discover_cache,
        plain=plain,
    )
    return gateway.ask(
        kind,
        settings=settings,
        registry=app.registry,
        ctx=ctx,
        current=current,
        history=history,
        api=api,
    )


def _kid_line(
    app: App, conn: sqlite3.Connection, member: Member, text: str, *, private: bool
) -> str:
    """A kid's age and, where nobody else reads, her wish topics and whether to nudge her wording
    (docs/WISHES.md): in a group "can we…" is a question for the family, and a nudge there would
    be said in front of everyone. All chosen by code.
    """
    now = app.clock.now()
    today = now.astimezone(app.settings.tzinfo).date()
    return render_kid_line(
        member.display_name,
        family.age_on(member.birth_date, today),
        member.gender,
        wishes.topics(conn, member.id, utc_iso(now)) if private else None,
        wording.choose(conn, app.settings, member.id, text, now) if private else None,
    )


def _gave_up_reply(app: App, result: TurnResult, inbound_id: int, plain: bool = False) -> str:
    written = {spec.name for spec in app.registry.specs() if spec.writes}
    completed = [a for a in result.actions if a.get("ok") and a.get("tool") in written]
    if not completed:
        return voice.say(app.settings, "gave_up", seed=inbound_id, plain=plain)
    partly = voice.say(app.settings, "gave_up_partly", seed=inbound_id, plain=plain)
    return spending.done_lines(completed) + " " + partly


def _fail(
    app: App,
    conn: sqlite3.Connection,
    msg: IncomingMessage,
    inbound_id: int,
    error: str,
    reply_text: str | None,
    actions: list[dict[str, Any]] | None = None,
) -> OutgoingMessage:
    now = utc_iso(app.clock.now())
    outbound_id = None
    with transaction(conn):
        messages.mark_failed(conn, inbound_id, error, now=now)
        if reply_text is not None:
            outbound = messages.insert_out(
                conn,
                channel=msg.channel,
                chat_id=msg.chat_id,
                text=reply_text,
                reply_to=inbound_id,
                now=now,
            )
            outbound_id = outbound.id
    return OutgoingMessage(
        msg.chat_id, reply_text or "", "failed", inbound_id, outbound_id, actions or []
    )
