"""The weekend digest: once a week the bot asks itself what the family should do this weekend.

The question goes through the normal pipeline as the first admin, into the configured chat, so
the reply is the same checked suggestion anyone would get by asking. The update id carries the
date, so a restart or a second run on the same day sends nothing.
"""

from __future__ import annotations

import logging
from contextlib import closing

from familydb.agent.loop import MessagesAPI
from familydb.app import App
from familydb.availability import digest_configured
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.pipeline import handle_synthetic
from familydb.store import members

log = logging.getLogger(__name__)

DIGEST_TEXT = "Weekend digest: what should we do this weekend?"


def digest_channel(chat_id: str) -> str:
    """Which channel a configured chat id belongs to.

    A Telegram chat id is a number, so the two chats that are not Telegram are named instead:
    "console" for trying things out, "web" for the chat on the page.
    """
    for named in ("console", "web"):
        if chat_id.startswith(named):
            return named
    return "telegram"


def run_digest(app: App, *, api: MessagesAPI | None = None) -> OutgoingMessage | None:
    """Ask and deliver the digest. Returns None when nothing was sent (and logs why)."""
    app.refresh()
    settings = app.settings
    if not digest_configured(settings):
        log.info("digest skipped: DIGEST_CHAT_ID is not set")
        return None
    chat_id = settings.digest_chat_id or ""
    channel = digest_channel(chat_id)
    sender = app.senders.get(channel)
    if sender is None:
        log.warning("digest skipped: nothing here can send to %s", channel)
        return None
    with closing(app.connect()) as conn:
        admin = next((m for m in members.list_all(conn) if m.role == "admin"), None)
        if admin is None:
            log.warning("digest skipped: no active admin to ask as")
            return None
        msg = IncomingMessage(
            channel=channel,
            channel_update_id=f"digest:{app.clock.today().isoformat()}",
            chat_id=chat_id,
            channel_user_id=admin.channel_user_id or admin.display_name,
            text=DIGEST_TEXT,
        )
        reply = handle_synthetic(app, msg, admin, api=api, conn=conn)
    if reply is None:
        log.info("digest already sent today")
        return None
    if reply.status not in {"ok", "refused"}:
        log.error("digest turn failed; the retry job will try again: %s", reply.text or "")
        return reply
    try:
        sender(chat_id, reply.text)
    except Exception:
        log.exception("could not deliver the digest to %s", chat_id)
    return reply
