"""Each night at 03:30, with no model call: an idea tied to dates whose last day is over a week
gone is taken off the list, through `update_idea` as the job, so it no longer comes up nor goes
with every message the model is sent, and the list does not have to depend on the date to leave
it out. Dropped is not deleted: its page brings it back. A plan made from it is not touched, nor
an idea that is planned or done. Nothing to do costs one query. `tidy_ideas` turns it off."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import timedelta

from familydb.app import App
from familydb.store import ideas
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

# The week after an event: long enough to say how it went, or that it was missed.
GRACE_DAYS = 7


def run_tidy(app: App) -> int:
    """Take off the ideas whose dates are past; returns how many."""
    app.refresh()
    settings = app.settings
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
