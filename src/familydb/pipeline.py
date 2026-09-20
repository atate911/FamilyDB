"""One inbound message, end to end: dedupe, allowlist, persist, think, reply, persist."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from typing import Any

from familydb.agent.history import load_history
from familydb.agent.loop import MessagesAPI, TurnResult, run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.render import render_user_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import members, messages
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

    try:
        result = _think(app, msg, member, inbound.id, api, conn)
    except AgentError as exc:
        log.error("agent error on message %s: %s (retryable=%s)", inbound.id, exc, exc.retryable)
        return _fail(
            app, conn, msg, inbound.id, str(exc), RETRY_REPLY if exc.retryable else CONFIG_REPLY
        )
    except Exception as exc:
        log.exception("unexpected error on message %s", inbound.id)
        return _fail(app, conn, msg, inbound.id, f"{type(exc).__name__}: {exc}", RETRY_REPLY)

    if result.status == "failed":
        log.error("turn failed on message %s: %s", inbound.id, result.error)
        return _fail(
            app, conn, msg, inbound.id, result.error or "failed", RETRY_REPLY, result.actions
        )

    reply_text = result.text or EMPTY_REPLY
    now = utc_iso(app.clock.now())
    with transaction(conn):
        outbound = messages.insert_out(
            conn,
            channel=msg.channel,
            chat_id=msg.chat_id,
            text=reply_text,
            reply_to=inbound.id,
            now=now,
        )
        messages.mark_processed(conn, inbound.id, result.actions, now=now)
    return OutgoingMessage(
        msg.chat_id, reply_text, result.status, inbound.id, outbound.id, result.actions
    )


def _think(
    app: App,
    msg: IncomingMessage,
    member: Member,
    inbound_id: int,
    api: MessagesAPI | None,
    conn: sqlite3.Connection,
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
    )
    turn = build_messages(history, render_user_turn(member.display_name, msg.text, app.clock))
    ctx = ToolContext(
        conn=conn, settings=settings, clock=app.clock, member=member, message_id=inbound_id
    )
    return run_turn(
        api=api if api is not None else app.client.beta.messages,
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
    reply_text: str,
    actions: list[dict[str, Any]] | None = None,
) -> OutgoingMessage:
    now = utc_iso(app.clock.now())
    with transaction(conn):
        messages.mark_failed(conn, inbound_id, error, now=now)
        outbound = messages.insert_out(
            conn,
            channel=msg.channel,
            chat_id=msg.chat_id,
            text=reply_text,
            reply_to=inbound_id,
            now=now,
        )
    return OutgoingMessage(
        msg.chat_id, reply_text, "failed", inbound_id, outbound.id, actions or []
    )
