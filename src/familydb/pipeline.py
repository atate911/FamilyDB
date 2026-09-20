"""One inbound message, end to end: dedupe, allowlist, persist, think, reply, persist."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from typing import Any

from familydb.agent.history import load_history
from familydb.agent.loop import MessagesAPI, TurnResult, run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.render import render_retry_note, render_user_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls, members, messages, suggestions
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

UNKNOWN_SENDER = (
    "Sorry, I only talk to the family. Your id on this channel is {id}; ask an admin to add you."
)
RETRY_REPLY = "Saved your message, but I couldn't process it right now. I'll retry later."
CONFIG_REPLY = (
    "Saved your message, but I can't reach the model at the moment. "
    "An admin needs to check the logs."
)
EMPTY_REPLY = "Done."


def handle_incoming(
    app: App,
    msg: IncomingMessage,
    *,
    api: MessagesAPI | None = None,
    conn: sqlite3.Connection | None = None,
) -> OutgoingMessage | None:
    """Process one message. Returns None for an update already seen (a restart, a retry)."""
    if conn is not None:
        return _handle(app, msg, api, conn)
    with closing(app.connect()) as own:
        return _handle(app, msg, api, own)


def _handle(
    app: App, msg: IncomingMessage, api: MessagesAPI | None, conn: sqlite3.Connection
) -> OutgoingMessage | None:
    if msg.channel_update_id and messages.exists_update(conn, msg.channel, msg.channel_update_id):
        log.info("ignoring duplicate update %s/%s", msg.channel, msg.channel_update_id)
        return None

    member = members.resolve(conn, msg.channel, msg.channel_user_id)
    if member is None:
        log.warning("unknown sender %s on %s", msg.channel_user_id, msg.channel)
        return OutgoingMessage(
            msg.chat_id, UNKNOWN_SENDER.format(id=msg.channel_user_id), "unknown_sender"
        )

    try:
        with transaction(conn):
            inbound = messages.insert_in(
                conn,
                channel=msg.channel,
                channel_update_id=msg.channel_update_id,
                chat_id=msg.chat_id,
                member_id=member.id,
                text=msg.text,
                now=utc_iso(app.clock.now()),
            )
    except sqlite3.IntegrityError:
        if not msg.channel_update_id:
            raise
        log.info("update %s/%s arrived twice at once", msg.channel, msg.channel_update_id)
        return None

    return _run(app, msg, member, inbound.id, api, conn, notify=True)


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
) -> OutgoingMessage:
    """Think and persist the outcome. With notify off (retries) failures stay silent."""
    try:
        result = _think(app, msg, member, inbound_id, api, conn, retry=retry)
    except AgentError as exc:
        log.error("agent error on message %s: %s (retryable=%s)", inbound_id, exc, exc.retryable)
        if not exc.retryable:
            with transaction(conn):
                messages.give_up(conn, inbound_id)
        reply = RETRY_REPLY if exc.retryable else CONFIG_REPLY
        return _fail(app, conn, msg, inbound_id, str(exc), reply if notify else None)
    except Exception as exc:
        log.exception("unexpected error on message %s", inbound_id)
        error = f"{type(exc).__name__}: {exc}"
        return _fail(app, conn, msg, inbound_id, error, RETRY_REPLY if notify else None)

    if result.status == "failed":
        log.error("turn failed on message %s: %s", inbound_id, result.error)
        return _fail(
            app,
            conn,
            msg,
            inbound_id,
            result.error or "failed",
            RETRY_REPLY if notify else None,
            result.actions,
        )

    reply_text = result.text or EMPTY_REPLY
    now = utc_iso(app.clock.now())
    with transaction(conn):
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
    if row is None or row.direction != "in" or row.status != "failed":
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
    with transaction(conn):
        messages.bump_retries(conn, message_id)
    msg = IncomingMessage(
        channel=row.channel,
        channel_update_id=row.channel_update_id,
        chat_id=row.chat_id,
        channel_user_id=member.channel_user_id or member.display_name,
        text=row.text,
    )
    log.info("retrying message %s (attempt %s)", message_id, row.retries + 1)
    reply = _run(app, msg, member, message_id, api, conn, notify=False, retry=True)
    if reply.status in {"ok", "refused"}:
        sender = app.senders.get(row.channel)
        if sender is not None:
            try:
                sender(row.chat_id, reply.text)
            except Exception:
                log.exception("could not deliver the retried reply for message %s", message_id)
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
) -> TurnResult:
    settings = app.settings
    system = build_system_blocks(conn, settings)
    history = load_history(
        conn,
        msg.chat_id,
        clock=app.clock,
        limit=settings.history_limit,
        since_hours=settings.history_hours,
        exclude_message_id=inbound_id,
        exclude_replies_to=inbound_id if retry else None,
    )
    current = render_user_turn(member.display_name, msg.text, app.clock)
    if retry:
        write_tools = {spec.name for spec in app.registry.specs() if spec.writes}
        note = render_retry_note(calls.tool_calls_for_message(conn, inbound_id), write_tools)
        if note:
            current.append({"type": "text", "text": note})
    turn = build_messages(history, current)
    messages_api = api if api is not None else app.client.beta.messages
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=app.clock,
        member=member,
        message_id=inbound_id,
        calendar=app.calendar,
        weather=app.weather,
        geocoder=app.geocoder,
        api=messages_api,  # for the discovery worker inside `suggest`
        discover_cache=app.discover_cache,
    )
    return run_turn(
        api=messages_api,
        settings=settings,
        registry=app.registry,
        ctx=ctx,
        system=system,
        messages=turn,
    )


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
