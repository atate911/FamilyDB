"""Each night at 03:30, with no model call: an idea tied to dates whose last day is over a week
gone is taken off the list, through `update_idea` as the job, so it no longer comes up nor goes
with every message the model is sent, and the list does not have to depend on the date to leave
it out. Dropped is not deleted: its page brings it back. A plan made from it is not touched, nor
an idea that is planned or done. `tidy_ideas` turns it off.

And when the family keeps messages for a number of days (`keep_messages_days`, Sign-in and
security; 0, for good, unless they choose), the words of every message older than that are
emptied (`messages.forget_words`): the row stays, since replies, reminders, memories, wishes and
calls point at it. The words of model calls kept for the Troubleshooting pages go after
`keep_ai_text_days`, or with the messages' words if those go sooner, and so does the problem log
past its month. Knocks from strangers past their month and Telegram links past their day go too.
Nothing to do costs a query or two."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import timedelta

from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import ai_texts, ideas, invites, knocks, messages, problems
from familydb.store.db import transaction
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

# The week after an event: long enough to say how it went, or that it was missed.
GRACE_DAYS = 7
# The fewest days messages are kept for, whatever is set: the chat's own history reaches back six
# hours, and a month leaves time to look back at what was said.
LEAST_KEEP_DAYS = 30


def run_tidy(app: App) -> int:
    """Take off the ideas whose dates are past, and forget old messages' words when the family
    keeps them for a while; returns how many ideas were taken off."""
    app.refresh()
    settings = app.settings
    if settings.keep_messages_days:
        forget_old_words(app, settings.keep_messages_days)
    forget_old_texts(app)
    forget_stale_callers(app)
    if not settings.tidy_ideas:
        return 0
    before = (app.clock.today() - timedelta(days=GRACE_DAYS)).isoformat()
    taken_off = 0
    with closing(app.connect()) as conn:
        for idea in ideas.over_before(conn, before):
            ctx = ToolContext(
                conn=conn, settings=settings, clock=app.clock, member=None, source="job"
            )
            done = app.registry.dispatch("update_idea", {"id": idea.id, "status": "dropped"}, ctx)
            if done.is_error:
                log.warning("tidy: #%s was left on the list: %s", idea.id, done.content)
            else:
                taken_off += 1
    if taken_off:
        log.info("tidy: took %d idea(s) off the list, their dates past", taken_off)
    return taken_off


def forget_stale_callers(app: App) -> int:
    """Drop strangers' knocks past their month and Telegram links past their day, which are
    otherwise only dropped when the next one is made."""
    with closing(app.connect()) as conn, transaction(conn):
        gone = knocks.forget_old(conn, app.clock.now())
        gone += invites.forget_expired(conn, utc_iso(app.clock.now()))
    return gone


def forget_old_texts(app: App) -> int:
    """Let go of the kept words of model calls past their time, and the old problem log."""
    settings = app.settings
    days = settings.keep_ai_text_days
    if settings.keep_messages_days:
        days = min(days, max(settings.keep_messages_days, LEAST_KEEP_DAYS)) if days else 0
    with closing(app.connect()) as conn, transaction(conn):
        problems.trim(conn, now=app.clock.now())
        if not days:
            return ai_texts.forget_all(conn)
        return ai_texts.forget_before(conn, ai_texts.cutoff(days, now=app.clock.now()))


def forget_old_words(app: App, days: int) -> int:
    """Empty the words of messages older than `days` (at least `LEAST_KEEP_DAYS`)."""
    before = utc_iso(app.clock.now() - timedelta(days=max(days, LEAST_KEEP_DAYS)))
    with closing(app.connect()) as conn, transaction(conn):
        forgotten = messages.forget_words(conn, before)
    if forgotten:
        log.info("tidy: %d message(s) past the family's keeping lost their words", forgotten)
    return forgotten
