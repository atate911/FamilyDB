"""Stage: where travel is estimated from. Home, unless the family said, or shared, where they are.

- `near` names a place ("downtown Portland", "the Pearl"): it is looked up with the free geocoder,
  and a match far from home is tried again with the home area added, so "Main St" is the local one.
- `near` says "here": the asker's location shared on Telegram in the last few hours.
- Nothing said, but a question about now or today and a fresh shared location: that location.
  Someone who shared where they are and asks what's open now means near there.

Nothing here costs a model call; a failed lookup is a skipped check and travel is from home.
"""

from __future__ import annotations

import logging

from familydb import whereabouts
from familydb.integrations.geocode import GeoPoint, haversine_km
from familydb.suggest.types import Origin
from familydb.tools import ToolContext

log = logging.getLogger(__name__)

HERE = frozenset(
    {"here", "me", "near me", "nearby", "near here", "around here", "where i am", "my location"}
)
# Further than this from home, a name probably matched somewhere else of the same name.
FAR_KM = 150.0


def resolve(ctx: ToolContext, near: str, window: str) -> tuple[Origin | None, str | None]:
    """Where to estimate travel from (None: home), and a note when a request for it failed."""
    said = " ".join(near.casefold().split())
    now = ctx.clock.now()
    shared = whereabouts.current(ctx.conn, ctx.member.id, now) if ctx.member else None

    def from_shared() -> Origin:
        assert shared is not None and ctx.member is not None
        ago = whereabouts.minutes_ago(shared, now)
        where = f" ({shared.label})" if shared.label else ""
        return Origin(
            shared.lat,
            shared.lon,
            shared.label or f"{ctx.member.display_name}'s location",
            f"{ctx.member.display_name}'s location{where}, {ago} min ago",
            shared=True,
        )

    if said in HERE:
        if shared is not None:
            return from_shared(), None
        return None, "no location shared in the last 3 hours, so travel is from home"
    if said:
        point = _place(ctx, near.strip())
        if point is not None:
            return Origin(point.lat, point.lon, near.strip(), near.strip()), None
        return None, f"could not place {near.strip()!r}, so travel is from home"
    if shared is not None and window in ("now", "today"):
        return from_shared(), None
    return None, None


def _place(ctx: ToolContext, name: str) -> GeoPoint | None:
    if ctx.geocoder is None:
        return None
    settings = ctx.settings
    tries = [name]
    if settings.home_area and settings.home_area.casefold() not in name.casefold():
        tries.append(f"{name}, {settings.home_area}")
    for query in tries:
        try:
            point = ctx.geocoder.geocode(query)
        except Exception:  # a lookup failure is a skipped check, never a failed suggestion
            log.warning("could not geocode %r", query, exc_info=True)
            return None
        if point is None:
            continue
        if settings.home_lat is None or settings.home_lon is None:
            return point
        if haversine_km(settings.home_lat, settings.home_lon, point.lat, point.lon) <= FAR_KM:
            return point
    return None
