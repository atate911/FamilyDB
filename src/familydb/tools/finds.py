"""What she found (docs/FINDS.md): the family's "not for us" on a find, in chat or on its page
(saving one is `add_idea` with its `find_id`), and the hand-backs of the lookup that fills a
find in (`save_find`, `skip_find`), which share the place-writing code of `save_place`."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field, create_model

from familydb.base.dates import utc_iso
from familydb.base.errors import ToolError
from familydb.store import finds
from familydb.store.db import transaction
from familydb.store.ideas import normalize_title
from familydb.tools.places import (
    LONGEST_VISIT,
    OLDEST,
    SavePlaceInput,
    place_fields,
    store_place,
    travel_of,
)
from familydb.tools.registry import ToolContext, keep_undo, tool

# How far back "that market" reaches when a find is named by its title.
RECENT_DAYS = 30
RECENT_MOST = 50


class PassFindInput(BaseModel):
    find_id: int | None = Field(default=None, description="Its find number, when known.")
    title: str | None = Field(default=None, description="Its title, as said, when no number.")
    why: str | None = Field(default=None, description="Why not, in their words, if said.")


def _named(ctx: ToolContext, args: PassFindInput) -> finds.Find:
    if args.find_id is not None:
        found = finds.get(ctx.conn, args.find_id)
        if found is None:
            raise ToolError(f"no find {args.find_id}")
        return found
    wanted = normalize_title(args.title or "")
    if not wanted:
        raise ToolError("say which find: its number or its title")
    since = utc_iso(ctx.clock.now() - timedelta(days=RECENT_DAYS))
    recent = finds.recent(ctx.conn, since=since, limit=RECENT_MOST)
    exact = [one for one in recent if normalize_title(one.title) == wanted]
    matches = exact or [one for one in recent if wanted in normalize_title(one.title)]
    if not matches:
        raise ToolError(f"nothing she found lately is called {args.title!r}")
    if len(matches) > 1:
        listed = "; ".join(f"{one.id}: {one.title}" for one in matches[:5])
        raise ToolError(f"more than one find matches; name its number ({listed})")
    return matches[0]


@tool(
    name="pass_find",
    description=(
        "Mark something she found (not an idea on their list) as not for them, so she stops "
        "offering it. Only when they say so."
    ),
    writes=True,
    needs="change",
)
def pass_find(ctx: ToolContext, args: PassFindInput) -> dict[str, Any]:
    found = _named(ctx, args)
    if found.state in ("saved", "planned"):
        raise ToolError(f"that is on their list as idea #{found.idea_id}; drop the idea instead")
    if found.state == "passed":
        return {"find_id": found.id, "title": found.title, "passed": True, "already": True}
    with transaction(ctx.conn):
        finds.mark_passed(
            ctx.conn,
            found.id,
            by=ctx.member.id if ctx.member else None,
            why=args.why,
            now=ctx.now_iso(),
        )
    keep_undo(
        ctx, "restore_find", f"passed on {found.title}", find=found.id, before=finds.fate(found)
    )
    return {"find_id": found.id, "title": found.title, "passed": True}


# A find's lookup hands back what an idea's does, for the find: its dates came with it.
SaveFindInput = create_model(
    "SaveFindInput",
    find_id=(int, ...),
    **{
        name: (field.annotation, field)
        for name, field in SavePlaceInput.model_fields.items()
        if name not in ("idea_id", "first_day", "last_day", "book_days_ahead")
    },
)


class SkipFindInput(BaseModel):
    find_id: int
    reason: str = Field(description="One short sentence: why nothing could be found.")


def _facts(args: Any) -> dict[str, Any]:
    """What the lookup found that suggestions need, each only when a page could have meant it."""
    facts: dict[str, Any] = {"cost_level": args.cost_level, "setting": args.setting}
    if args.visit_minutes is not None and 0 < args.visit_minutes <= LONGEST_VISIT:
        facts["duration_min"] = args.visit_minutes
    if args.needs_booking is not None:
        facts["needs_booking"] = int(args.needs_booking)
    low, high = args.min_age, args.max_age
    low = low if low is not None and 0 <= low <= OLDEST else None
    high = high if high is not None and 0 <= high <= OLDEST else None
    if low is None or high is None or low <= high:
        facts |= {"min_age": low, "max_age": high}
    return facts


@tool(
    name="save_find",
    description=(
        "Store looked-up details for something she found and its place. Used by the lookup that "
        "fills a find in; give only facts the pages state."
    ),
    input_model=SaveFindInput,
    writes=True,
    worker_only=True,
)
def save_find(ctx: ToolContext, args: Any) -> dict[str, Any]:
    found = finds.get(ctx.conn, args.find_id)
    if found is None:
        raise ToolError(f"no find {args.find_id}")
    area = found.venue or found.address or ctx.settings.home_area
    fields, note, geocoded = place_fields(ctx, args, area=area, about=f"find {found.id}")
    now = ctx.now_iso()
    with transaction(ctx.conn):
        place = store_place(ctx, args.name, fields, place_id=found.place_id)
        finds.mark_filled(
            ctx.conn, found.id, place_id=place.id, facts=_facts(args), note=note, now=now
        )
    return {
        "find_id": found.id,
        "place": place.model_dump(mode="json"),
        "geocoded": geocoded,
        "travel": travel_of(fields),
        "note": note,
    }


@tool(
    name="skip_find",
    description=(
        "Mark something she found as having nothing more to look up, with a one-line reason. "
        "Used by the lookup that fills a find in."
    ),
    writes=True,
    worker_only=True,
)
def skip_find(ctx: ToolContext, args: SkipFindInput) -> dict[str, Any]:
    found = finds.get(ctx.conn, args.find_id)
    if found is None:
        raise ToolError(f"no find {args.find_id}")
    with transaction(ctx.conn):
        finds.mark_filled(
            ctx.conn, found.id, place_id=None, facts={}, note=args.reason, now=ctx.now_iso()
        )
    return {"find_id": found.id, "skipped": True, "reason": args.reason}


# The most finds judged worth putting forward on one evening.
MOST_RECOMMENDED = 5


class Recommendation(BaseModel):
    find_id: int
    why: str = Field(description="One line: why it suits them, from what you were told.")
    when: str = Field(description="When to put it forward, in words: 'Saturdays in November'.")
    put_from: str | None = Field(default=None, description="YYYY-MM-DD, first day to offer it.")
    put_until: str | None = Field(default=None, description="YYYY-MM-DD, last day to offer it.")


class RecommendFindsInput(BaseModel):
    picks: list[Recommendation] = Field(
        default_factory=list, description="Up to 5, the best first; empty when none is worth it."
    )


def _day(text: str | None) -> str | None:
    try:
        return date.fromisoformat(text.strip()[:10]).isoformat() if text else None
    except ValueError:
        return None


@tool(
    name="recommend_finds",
    description=(
        "Hand back the finds worth putting forward to the family, from the pocket only, each "
        "with why and when. Call it once. Not for chat."
    ),
    worker_only=True,
)
def recommend_finds(ctx: ToolContext, args: RecommendFindsInput) -> dict[str, Any]:
    pocket: set[int] = set(ctx.scratch.get("pocket") or ())
    chosen: dict[int, dict[str, str | None]] = {}
    for pick in args.picks:
        if pick.find_id not in pocket:
            raise ToolError(
                f"find {pick.find_id} is not in the pocket; choose from {sorted(pocket)}"
            )
        if pick.find_id in chosen or len(chosen) >= MOST_RECOMMENDED:
            continue
        first, last = _day(pick.put_from), _day(pick.put_until)
        if first and last and last < first:
            first = last = None
        chosen[pick.find_id] = {
            "why": " ".join(pick.why.split()) or None,
            "when": " ".join(pick.when.split()) or None,
            "put_from": first,
            "put_until": last,
        }
    ctx.scratch["recommended"] = chosen
    return {"recorded": len(chosen)}
