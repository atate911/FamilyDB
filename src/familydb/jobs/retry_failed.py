"""Retry inbound messages whose processing failed, a bounded number of times."""

from __future__ import annotations

import logging
from contextlib import closing

from familydb.agent.loop import MessagesAPI
from familydb.app import App
from familydb.pipeline import retry_message
from familydb.store import messages

log = logging.getLogger(__name__)


def run_retries(app: App, *, api: MessagesAPI | None = None) -> int:
    """Retry every eligible failed message once. Returns how many were processed successfully."""
    with closing(app.connect()) as conn:
        app.refresh(conn)
        pending = messages.failed(conn, max_retries=app.settings.retry_max_attempts)
        if not pending:
            return 0
        log.info("retrying %s failed message(s)", len(pending))
        recovered = 0
        for row in pending:
            reply = retry_message(app, row.id, api=api, conn=conn)
            if reply is not None and reply.status in {"ok", "refused"}:
                recovered += 1
        return recovered
