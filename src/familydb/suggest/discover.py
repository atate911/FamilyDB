"""Stage: time-bound things found on the web for the window, through the scouting layer
(scouting/search.py `discover`), as the engine's result rows."""

from __future__ import annotations

from familydb.scouting import search
from familydb.scouting.reach import Reach
from familydb.suggest.types import Constraints, Context, WebFind
from familydb.tools import ToolContext


def discover(
    ctx: ToolContext, context: Context, constraints: Constraints
) -> tuple[list[WebFind], str | None]:
    """Finds for the window, plus a `skipped_checks` note when discovery did not run."""
    found, note = search.discover(Reach.of(ctx), context, constraints)
    return [WebFind(**one.model_dump()) for one in found], note
