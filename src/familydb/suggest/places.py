"""Stage: a place nothing saved fits, looked for on the web. "Thai food, what's open now?" with
nothing Thai on the list used to end at "nothing saved fits"; with `find_places` on (Lookups), one
places worker turn (`gateway.KINDS["places"]`, `prompts/places.md`) looks nearby and hands a few
back through `report_finds`, with their hours and address as written.

Code decides when, never the model, since each search is paid for: a topic was asked about, no
idea framed for it (`idea_ids`) is good or possible, and the window is now, today or starts within
`AHEAD_DAYS`. What comes back is never checked here: it goes with the web finds, said as found on
the web, and one already on the list is marked with its number (`saved_as`) by its name or its
site. Cached by the request, which carries the topic, the hours to the hour and where they are to
about a hundred metres, so the same ask within the hour is one search.
"""

from __future__ import annotations

from collections.abc import Sequence

from familydb.availability import web_tools_available
from familydb.base.config import Settings
from familydb.scouting import search
from familydb.scouting.reach import Reach
from familydb.scouting.search import saved as saved
from familydb.suggest.types import Candidate, Constraints, Context, WebFind
from familydb.tools import ToolContext

# Now, today, or a window that starts within this many days: a place found for next month may be
# gone by then, and the family can save it as an idea to be looked up properly.
AHEAD_DAYS = 2


def wanted(
    context: Context,
    constraints: Constraints,
    candidates: Sequence[Candidate],
    settings: Settings,
) -> bool:
    """Whether to look for a place on the web: the family turned it on, the web is there, a
    topic was asked about, nothing framed for it fits, and the window is near."""
    if not (settings.find_places and web_tools_available(settings) and constraints.topic):
        return False
    if context.window is None or (context.window[0] - context.today).days > AHEAD_DAYS:
        return False
    framed = set(constraints.idea_ids)
    return not any(c.idea_id in framed and c.verdict != "ruled_out" for c in candidates)


def find_places(
    ctx: ToolContext, context: Context, constraints: Constraints
) -> tuple[list[WebFind], str | None]:
    """Places found for the topic, each marked when already saved; a note when none could be
    (scouting/search.py `find_places`)."""
    found, note = search.find_places(Reach.of(ctx), context, constraints)
    return [WebFind(**one.model_dump()) for one in found], note
