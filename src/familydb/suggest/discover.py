"""Stage: the search made while answering (scouting/search.py `search_for`): what suits the
family for the window, events and places alike, kept as finds and offered as the engine's result
rows."""

from __future__ import annotations

from familydb.scouting import search
from familydb.scouting.reach import Reach
from familydb.suggest.types import Constraints, Context, WebFind
from familydb.tools import ToolContext


def discover(
    ctx: ToolContext, context: Context, constraints: Constraints, question: str = ""
) -> tuple[list[WebFind], str | None]:
    """Finds for the window, plus a `skipped_checks` note when no search ran."""
    found, note = search.search_for(Reach.of(ctx), context, constraints, question)
    return [WebFind(**one.model_dump()) for one in found], note
