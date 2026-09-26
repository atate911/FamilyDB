"""One inbound message, end to end: dedupe, allowlist, persist, think, reply, persist."""

from __future__ import annotations

import dataclasses
import logging
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any

from familydb import memory, personas, voice, whereabouts
from familydb.agent import gateway, spending
from familydb.agent.history import load_history
from familydb.agent.loop import MessagesAPI, TurnResult
from familydb.agent.providers import Audio
from familydb.agent.render import (
    render_audience_line,
    render_folded_line,
    render_location_line,
    render_memories,
    render_retry_note,
    render_user_turn,
)
from familydb.agent.spending import SpendingLimitReached
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.delivery import deliver, lease
from familydb.errors import AgentError
from familydb.store import calls, knocks, members, messages, suggestions
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

# The most a voice note may weigh: what Telegram lets a bot download.
MAX_AUDIO_BYTES = 20 * 1024 * 1024
# What the weekend digest's question is stored under, followed by the day, so the retry job can
# tell a digest from a message somebody wrote.
DIGEST_UPDATE = "digest:"


def handle_incoming(
    app: App,
    msg: IncomingMessage,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
    hearing: Any = None,
) -> OutgoingMessage | None:
    """Process one message. Returns None for an update already seen (a restart, a retry).

    A voice note is heard first (`hearing` stands in for the speech endpoint in tests).
    """
    if conn is not None:
        return _handle(app, msg, api, conn, hearing)
    with closing(app.connect()) as own:
        return _handle(app, msg, api, own, hearing)


def handle_synthetic(
    app: App,
    msg: IncomingMessage,
    member: Member,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    """Process a message the bot wrote itself on a member's behalf (the weekend digest).

    Same dedupe on the update id and the same storage as a real message, but the sender is given
    and a failure stores no notice for the family: the retry job picks the message up later.
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


def _handle(
    app: App,
    msg: IncomingMessage,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
    hearing: Any = None,
) -> OutgoingMessage | None:
    if _seen(conn, msg):
        return None

    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
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
        # Their message is not stored, so the update itself chooses the words: the same knock
        # sent again reads the same, and the next one may not.
        return OutgoingMessage(
            msg.chat_id,
            voice.say(app.settings, "stranger", seed=msg.channel_update_id, id=msg.channel_user_id),
            "unknown_sender",
        )

    inbound_id = _store_inbound(app, conn, msg, member)
    if inbound_id is None:
        return None
    return _run(app, msg, member, inbound_id, api, conn, notify=True, hearing=hearing)


def _seen(conn: sqlite3.Connection, msg: IncomingMessage) -> bool:
    if msg.channel_update_id and messages.exists_update(conn, msg.channel, msg.channel_update_id):
        log.info("ignoring duplicate update %s/%s", msg.channel, msg.channel_update_id)
        return True
    return False


def _store_inbound(
    app: App, conn: sqlite3.Connection, msg: IncomingMessage, member: Member
) -> int | None:
    """Store the inbound message; None when the same update landed at the same moment.

    A voice note is stored as a mark saying how long it was, before a byte of it is fetched:
    its words replace the mark once they are heard.
    """
    try:
        with transaction(conn):
            inbound = messages.insert_in(
                conn,
                channel=msg.channel,
                channel_update_id=msg.channel_update_id,
                chat_id=msg.chat_id,
                member_id=member.id,
                text=messages.unheard(msg.voice.seconds) if msg.voice else msg.text,
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
) -> OutgoingMessage | None:
    with lease(app, conn, inbound_id) as owned:
        if not owned:
            return None
        row = messages.get(conn, inbound_id)
        if row is None or row.status == "processed" or row.give_up:
            return None
        current_member = members.get(conn, member.id)
        if current_member is None or not current_member.active:
            with transaction(conn):
                messages.mark_failed(
                    conn, inbound_id, "member_inactive", now=utc_iso(app.clock.now())
                )
                messages.give_up(conn, inbound_id)
            return None
        member = current_member
        if msg.voice is not None:
            heard = _hear(app, msg, inbound_id, conn, hearing)
            if isinstance(heard, OutgoingMessage):
                return heard
            msg = heard
        elif messages.is_unheard(row.text):
            # Stored, and then the process stopped before it was heard. The recording is not
            # kept, so there is nothing to answer: say so, even on a retry, since it is final.
            return _not_heard(app, conn, msg, inbound_id, "stopped before it was heard")
        if retry:
            if row.retries >= app.settings.retry_max_attempts:
                return None
            with transaction(conn):
                conn.execute(
                    "UPDATE messages SET retries = retries + 1 WHERE id = ?", (inbound_id,)
                )
        return _run_owned(
            app, msg, member, inbound_id, api, conn, notify=notify, retry=retry, kind=kind
        )


def _hear(
    app: App, msg: IncomingMessage, inbound_id: int, conn: sqlite3.Connection, hearing: Any
) -> IncomingMessage | OutgoingMessage:
    """A voice note's words, stored in place of its mark and handed on as the message's text.

    Or the notice saying why it was not heard, worded by code: turned off, nobody with a key
    who can hear, too long, not fetched, not heard, or the day's limit spent. The recording is
    not kept, so a voice note that was not heard is given up rather than retried.
    """
    note = msg.voice
    assert note is not None
    settings = app.settings
    if not settings.voice_notes:
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
    with transaction(conn):
        messages.set_text(conn, inbound_id, text)
    log.info("heard voice note %s: %s s, %s characters", inbound_id, note.seconds, len(words))
    return dataclasses.replace(msg, text=text, voice=None)


def _not_heard(
    app: App,
    conn: sqlite3.Connection,
    msg: IncomingMessage,
    inbound_id: int,
    error: str,
    event: str = "voice_unheard",
    **facts: Any,
) -> OutgoingMessage:
    log.warning("voice note %s not heard: %s", inbound_id, error)
    with transaction(conn):
        messages.give_up(conn, inbound_id)
    notice = voice.say(app.settings, event, **facts)
    return _fail(app, conn, msg, inbound_id, f"voice note: {error}", notice)


def _hints(app: App, conn: sqlite3.Connection) -> str:
    """Names a voice note may say, so they are written the family's way: who is in the family,
    what she is called, where home is. The same for every voice note, and short."""
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
) -> OutgoingMessage:
    """Think and persist the outcome, carrying anything held for this conversation (voice.py)."""
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
        )
    finally:
        # Whatever the reply did not carry goes as written: at once, not after the wait.
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
) -> OutgoingMessage:
    """Think and persist the outcome. With notify off (retries) failures stay silent."""
    if not app.can_ask("chat", api=api):
        # A fresh install before its key is typed in: say so plainly, and do not keep retrying.
        log.warning("message %s saved, but there is no model key to answer it with", inbound_id)
        with transaction(conn):
            messages.give_up(conn, inbound_id)
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            "no model key",
            voice.say(app.settings, "no_key", seed=inbound_id) if notify else None,
        )
    try:
        result = _think(
            app, msg, member, inbound_id, api, conn, retry=retry, kind=kind, taken=taken
        )
    except AgentError as exc:
        log.error("agent error on message %s: %s (retryable=%s)", inbound_id, exc, exc.retryable)
        if not exc.retryable:
            with transaction(conn):
                messages.give_up(conn, inbound_id)
        if isinstance(exc, SpendingLimitReached):
            reply = voice.say(
                app.settings, "limit_reached", seed=inbound_id, limit=f"{exc.limit:.2f}"
            )
        else:
            reply = voice.say(
                app.settings, "retry_later" if exc.retryable else "cannot_reach", seed=inbound_id
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
            voice.say(app.settings, "retry_later", seed=inbound_id) if notify else None,
        )

    if result.status == "failed" and result.error == "max_iterations":
        # Given up for good, so a person who asked is told now, even on a retry; the digest
        # asked nobody and stays quiet, as its failures always have.
        log.error("turn on message %s ran out of steps; not retrying it", inbound_id)
        with transaction(conn):
            messages.give_up(conn, inbound_id)
        notice = _gave_up_reply(app, result, inbound_id) if kind != "digest" else None
        return _fail(app, conn, msg, inbound_id, "max_iterations", notice, result.actions)
    if result.status == "failed":
        log.error("turn failed on message %s: %s", inbound_id, result.error)
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            result.error or "failed",
            voice.say(app.settings, "retry_later", seed=inbound_id) if notify else None,
            result.actions,
        )

    reply_text = result.text or voice.say(app.settings, "done", seed=inbound_id)
    # What the reply was to carry and did not name goes with it in its written words.
    forgotten = [h.text for h in taken if h.mention.casefold() not in reply_text.casefold()]
    if forgotten:
        reply_text = "\n\n".join([reply_text, *forgotten])
    now = utc_iso(app.clock.now())
    with transaction(conn):
        # Carried by this reply: marked sent with it, so the delivery job has nothing to find.
        messages.mark_delivered(conn, [h.message_id for h in taken], now=now)
        outbound = messages.insert_out(
            conn,
            channel=msg.channel,
            chat_id=msg.chat_id,
            text=reply_text,
            reply_to=inbound_id,
            now=now,
        )
        messages.mark_processed(conn, inbound_id, result.actions, now=now)
        for action in result.actions:
            if action.get("tool") == "suggest" and action.get("suggestion_id"):
                suggestions.set_reply(conn, int(action["suggestion_id"]), outbound.id)
    app.held.done(taken)
    return OutgoingMessage(
        msg.chat_id, reply_text, result.status, inbound_id, outbound.id, result.actions
    )


def retry_message(
    app: App,
    message_id: int,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    """Reprocess a failed inbound message. Returns None when it is not eligible."""
    if conn is None:
        with closing(app.connect()) as own:
            return retry_message(app, message_id, api=api, conn=own)
    row = messages.get(conn, message_id)
    if row is None or row.direction != "in" or row.status not in {"failed", "received"}:
        return None
    if row.give_up or row.retries >= app.settings.retry_max_attempts:
        return None
    if row.channel != "console" and row.channel not in app.senders:
        # Only a process that can deliver the answer may consume the retry.
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
    # The digest asked again is still the digest: answered at its level, and quiet if it gives up.
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
) -> TurnResult:
    app.refresh(conn)  # a model or a limit changed on the settings page applies from here on
    settings = app.settings
    history = load_history(
        conn,
        msg.chat_id,
        clock=app.clock,
        limit=settings.history_limit,
        since_hours=settings.history_hours,
        exclude_message_id=inbound_id,
        exclude_replies_to=inbound_id if retry else None,
    )
    origin = messages.get(conn, inbound_id)
    received_clock = (
        FixedClock(
            datetime.fromisoformat(origin.received_at), app.clock.tz, southern=app.clock.southern
        )
        if origin
        else app.clock
    )
    # Who reads the reply depends on the chat, so it goes in the turn and never in the prefix.
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
    if retry:
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
        api=api,  # a stand-in for the discovery worker inside `suggest`, when a test injects one
        discover_cache=app.discover_cache,
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


def _gave_up_reply(app: App, result: TurnResult, inbound_id: int) -> str:
    """What to tell the family when a turn ran out of steps, worded by code, not by a model."""
    written = {spec.name for spec in app.registry.specs() if spec.writes}
    completed = [a for a in result.actions if a.get("ok") and a.get("tool") in written]
    if not completed:
        return voice.say(app.settings, "gave_up", seed=inbound_id)
    partly = voice.say(app.settings, "gave_up_partly", seed=inbound_id)
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
    """Mark the message failed; with a reply text, also store the notice sent to the family."""
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
