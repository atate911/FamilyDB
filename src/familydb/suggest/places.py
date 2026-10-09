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

import sqlite3
from collections.abc import Sequence
from urllib.parse import urlsplit

from familydb.agent import gateway
from familydb.availability import web_tools_available
from familydb.config import Settings
from familydb.store import ideas, places
from familydb.suggest.discover import search
from familydb.suggest.types import Candidate, Constraints, Context, WebFind, clock
from familydb.tools import ToolContext

# Now, today, or a window that starts within this many days: a place found for next month may be
# gone by then, and the family can save it as an idea to be looked up properly.
AHEAD_DAYS = 2
# A place's hours change slowly; the request's hour keeps "open now" honest.
PLACES_CACHE_SECONDS = 3600
NOTE_FAILED = "place search failed"


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


def render_places_request(context: Context, constraints: Constraints, settings: Settings) -> str:
    """What the worker is asked, from the framing only, so the same ask in other words is one
    search: what, when (to the hour), where, and the limits."""
    lines = [f"Find places for: {constraints.topic}."]
    if context.window is not None:
        start, end = context.window
        days = [day for day in context.days if day.bounds[1] > day.bounds[0]]
        if days and start == end:
            first, last = days[0].bounds
            hours = f"{clock(first // 60 * 60)}-{clock(min(24 * 60, -(-last // 60) * 60))}"
            lines.append(f"Open: {start:%A %d %B %Y}, {hours}.")
        else:
            lines.append(f"Open: {start:%A %d %B} to {end:%A %d %B %Y}.")
    lines.append(f"Home area: {settings.home_area or 'not set'}.")
    if context.origin is not None:
        origin = context.origin
        lines.append(f"They are near: {origin.label} ({origin.lat:.3f}, {origin.lon:.3f}).")
    limits = {
        "max_cost_level": constraints.max_cost_level,
        "setting": constraints.setting,
        "max_travel_minutes": constraints.max_travel_minutes,
        "avoid": constraints.avoid or None,
    }
    said = [
        f"{key} {', '.join(value) if isinstance(value, list) else value}"
        for key, value in limits.items()
        if value is not None
    ]
    if said:
        lines.append("Keep to: " + "; ".join(said) + ".")
    return "\n".join(lines)


def find_places(
    ctx: ToolContext, context: Context, constraints: Constraints
) -> tuple[list[WebFind], str | None]:
    """Places found for the topic, each marked when already saved; a note when none could be."""
    if not gateway.can_ask(ctx.settings, "places", api=ctx.api):
        return [], "place search waits for a model key"
    request = render_places_request(context, constraints, ctx.settings)
    found, note = search(
        ctx,
        "places",
        "places",
        request,
        f"places for {constraints.topic}",
        failed=NOTE_FAILED,
        seconds=PLACES_CACHE_SECONDS,
    )
    return saved(ctx.conn, found), note


def _host(url: str | None) -> str | None:
    host = urlsplit(url).hostname if url else None
    return host.removeprefix("www.") if host else None


def saved(conn: sqlite3.Connection, finds: list[WebFind]) -> list[WebFind]:
    """Each find already on the list marked with its idea's number, by its name or its site."""
    if not finds:
        return finds
    sites: dict[str, int] = {}
    for idea in ideas.list_all(conn):
        if idea.status == "dropped":
            continue
        place = places.get(conn, idea.place_id) if idea.place_id else None
        for url in (idea.url, place.website if place else None):
            if host := _host(url):
                sites.setdefault(host, idea.id)
    marked = []
    for find in finds:
        same = ideas.find_similar_title(conn, find.title)
        number = same.id if same is not None and same.status != "dropped" else None
        marked.append(find.model_copy(update={"saved_as": number or sites.get(_host(find.url))}))
    return marked
