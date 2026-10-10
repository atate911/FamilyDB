"""Her picks for Now, made ahead (familydb/picks.py): every hour the sets that are due are remade
by code, so the page never asks a model when viewed. Idle when every set is fresh: one read a
window."""

from __future__ import annotations

import logging

from familydb import picks
from familydb.app import App

log = logging.getLogger(__name__)


def run_picks(app: App, *, force: bool = False) -> dict[str, int]:
    """Make the sets that are due (all of them with `force`); how many were made per window."""
    made = picks.refresh(app, force=force)
    if any(made.values()):
        log.info("picks made: %s", made)
    return made
