"""Tools for the ideas list."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.agent.render import render_idea_line
from familydb.dates import parse_date, parse_datetime
from familydb.errors import ToolError
from familydb.store import ideas, members, messages, outcomes, places
from familydb.store.db import transaction
from familydb.store.ideas import KIND_SUGGESTIONS
from familydb.tools.registry import ToolContext, tool

Season = Literal["spring", "summer", "autumn", "winter"]
Setting = Literal["indoor", "outdoor", "either"]
Weather = Literal["any", "dry", "warm", "snow"]
Status = Literal["idea", "planned", "done", "dropped"]
CostLevel = Literal[0, 1, 2, 3, 4]

KIND_HELP = (
    "Free text, lowercase. Prefer one of: "
    + ", ".join(KIND_SUGGESTIONS)
    + ". Invent a new kind only when none fits."
)
PARTICIPANTS_HELP = (
    "Who it is for, as said, e.g. ['whole family'], ['with the girls'], ['adults']. "
    "Empty means anyone."
)
FROM_HELP = (
    "Only for a thing tied to dates (a festival, a show's run, a concert): the first day it is "
    "on, YYYY-MM-DD, or YYYY-MM-DDTHH:MM when a start time was said."
)
UNTIL_HELP = (
    "The last day it is on, YYYY-MM-DD: the same day for a one-day thing, empty when it has no "
    "end. A start time alone means one day."
)
CLEARS = " An empty string clears it."


class AddIdeaInput(BaseModel):
    title: str = Field(description="Short name for the idea, e.g. 'Ramen place on Main St'.")
    kind: str = Field(description=KIND_HELP)
    description: str | None = Field(default=None, description="Anything else that was said.")
    participants: list[str] = Field(default_factory=list, description=PARTICIPANTS_HELP)
    location_name: str | None = Field(
        default=None, description="Place or area if mentioned, e.g. 'Portland' or 'Main St'."
    )
    url: str | None = Field(default=None, description="A link if one was shared.")
    tags: list[str] = Field(
        default_factory=list,
        description="Lowercase keywords: food, hike, art, kids, cheap, date night, ...",
    )
    setting: Setting = Field(default="either", description="Indoor, outdoor, or either.")
    seasons: list[Season] = Field(
        default_factory=list, description="Only when the idea is season-specific."
    )
    weather: Weather = Field(default="any", description="Weather it needs, if any.")
    duration_min: int | None = Field(default=None, description="Typical minimum, in minutes.")
    duration_max: int | None = Field(default=None, description="Typical maximum, in minutes.")
    cost_level: CostLevel | None = Field(
        default=None, description="0 free, 1 cheap, 2 moderate, 3 pricey, 4 expensive."
    )
    needs_booking: bool = Field(default=False, description="Tickets or a reservation needed.")
    lead_time_days: int | None = Field(
        default=None, description="How far ahead it must be booked, in days."
    )
    happens_from: str | None = Field(default=None, description=FROM_HELP)
    happens_until: str | None = Field(default=None, description=UNTIL_HELP)
    suggested_by: str | None = Field(
        default=None,
        description="Family member's name, only when someone other than the sender suggested it.",
    )


class UpdateIdeaInput(BaseModel):
    id: int = Field(description="The idea number, e.g. 42 for #42.")
    title: str | None = None
    kind: str | None = Field(default=None, description=KIND_HELP)
    description: str | None = None
    participants: list[str] | None = Field(default=None, description=PARTICIPANTS_HELP)
    location_name: str | None = None
    url: str | None = None
    tags: list[str] | None = None
    setting: Setting | None = None
    seasons: list[Season] | None = None
    weather: Weather | None = None
    duration_min: int | None = None
    duration_max: int | None = None
    cost_level: CostLevel | None = None
    needs_booking: bool | None = None
    lead_time_days: int | None = None
    happens_from: str | None = Field(default=None, description=FROM_HELP + CLEARS)
    happens_until: str | None = Field(default=None, description=UNTIL_HELP + CLEARS)
    status: Status | None = Field(
        default=None,
        description="'dropped' removes it from the list; 'idea' brings a done idea back.",
    )


class DescribeIdeaInput(BaseModel):
    id: int = Field(description="The idea number.")


class SearchIdeasInput(BaseModel):
    text: str | None = Field(
        default=None, description="Free text matched against title, description, tags, location."
    )
    kind: str | None = None
    status: Status | None = Field(
        default=None, description="Default: everything except dropped ideas."
    )
    participant: str | None = Field(default=None, description="e.g. 'with the girls'.")
    setting: Literal["indoor", "outdoor"] | None = Field(
        default=None, description="Ideas marked 'either' always match."
    )
    max_duration_minutes: int | None = None
    max_cost_level: CostLevel | None = None
    tags: list[str] = Field(default_factory=list, description="All listed tags must match.")
    exclude_done_within_days: int | None = Field(
        default=None, description="Leave out ideas done more recently than this."
    )
    limit: int = Field(default=50, description="1 to 200.")


DATES = ("happens_from", "happens_until")


def _dated(
    ctx: ToolContext,
    given_from: str | None,
    given_until: str | None,
    before: ideas.Idea | None = None,
) -> dict[str, str | None]:
    """What changes in the days an idea is on, checked and spelled one way; {} for nothing.

    `before` is the idea as it stands. An empty string clears one, and clearing the first day
    clears both. A first day with a time and no last day is a one-day thing. Days given again
    as they were are no change, so a form sent back as drawn passes; changed ones that are
    already over are refused, since an idea is for something still to come.
    """
    changes: dict[str, str | None] = {}
    if given_from is not None:
        changes["happens_from"] = _first(ctx, given_from) if given_from.strip() else None
    if given_until is not None:
        # The last day only: an end time ("until 11pm") says nothing about which days it is on.
        last_day = given_until.strip().split("T")[0]
        changes["happens_until"] = parse_date(last_day).isoformat() if last_day else None
    elif given_from is not None and not given_from.strip():
        changes["happens_until"] = None  # no longer tied to dates at all
    was = {
        "happens_from": before.happens_from if before else None,
        "happens_until": before.happens_until if before else None,
    }
    changes = {key: value for key, value in changes.items() if value != was[key]}
    if not changes:
        return {}
    first = changes.get("happens_from", was["happens_from"])
    last = changes.get("happens_until", was["happens_until"])
    if first and "T" in first and last is None and given_until is None:
        last = changes["happens_until"] = first[:10]
    if first is None and last is not None:
        raise ToolError("give happens_from, the first day it is on, as well as the last")
    if first and last and last < first[:10]:
        raise ToolError(f"happens_until {last} is before happens_from {first[:10]}")
    if last and date.fromisoformat(last) < ctx.clock.today():
        raise ToolError(f"that was over on {last}; an idea is for something still to come")
    return changes


def _first(ctx: ToolContext, text: str) -> str:
    """A first day as stored: the date, with the time of day when one was said."""
    text = text.strip()
    if len(text) <= 10:
        return parse_date(text).isoformat()
    return parse_datetime(text, ctx.clock.tz).strftime("%Y-%m-%dT%H:%M")


def _resolve_member_name(ctx: ToolContext, name: str | None) -> int | None:
    if name is None:
        return ctx.member.id if ctx.member else None
    member = members.find_by_name(ctx.conn, name)
    if member is None:
        raise ToolError(f"no family member called {name!r}")
    return member.id


@tool(
    name="add_idea",
    description=(
        "Save something the family might do one day: a restaurant, outing, trip, show, event or "
        "any other idea. Infer the fields from what was said; never ask for them. Returns the "
        "saved record, or the existing record with 'duplicate_of' if the title already exists."
    ),
    writes=True,
)
def add_idea(ctx: ToolContext, args: AddIdeaInput) -> dict[str, Any]:
    existing = ideas.find_similar_title(ctx.conn, args.title)
    if existing is not None:
        return {
            "duplicate_of": existing.id,
            "note": "An idea with this title already exists; nothing was added.",
            "idea": existing.model_dump(mode="json"),
        }
    suggested_by = _resolve_member_name(ctx, args.suggested_by)
    fields = args.model_dump(exclude={"title", "kind", "suggested_by", *DATES})
    fields |= _dated(ctx, args.happens_from, args.happens_until)
    with transaction(ctx.conn):
        idea = ideas.insert(
            ctx.conn,
            title=args.title,
            kind=args.kind,
            now=ctx.now_iso(),
            suggested_by=suggested_by,
            source_message_id=ctx.message_id,
            **fields,
        )
    return idea.model_dump(mode="json")


@tool(
    name="update_idea",
    description=(
        "Change an idea: fix a title, re-tag it, add details, or set its status. Only the fields "
        "given are changed. Returns the updated record."
    ),
    writes=True,
)
def update_idea(ctx: ToolContext, args: UpdateIdeaInput) -> dict[str, Any]:
    changes = {k: v for k, v in args.model_dump(exclude={"id", *DATES}).items() if v is not None}
    dated = args.happens_from is not None or args.happens_until is not None
    if not changes and not dated:
        raise ToolError("nothing to change: give at least one field besides id")
    with transaction(ctx.conn):
        current = ideas.get(ctx.conn, args.id)
        if ctx.idea_revision is not None and (
            current is None or ideas.revision(current) != ctx.idea_revision
        ):
            raise ToolError(
                f"#{args.id} was changed since you opened it, so nothing was saved. "
                "Here it is as it is now; make your change again."
            )
        if current is None:
            raise ToolError(f"no idea #{args.id}")
        changes |= _dated(ctx, args.happens_from, args.happens_until, current)
        idea = ideas.update(ctx.conn, args.id, changes, now=ctx.now_iso())
    if idea is None:
        raise ToolError(f"no idea #{args.id}")
    return idea.model_dump(mode="json")


@tool(
    name="describe_idea",
    description=(
        "Everything known about one idea: the record, its place details if looked up, and how "
        "past visits went."
    ),
)
def describe_idea(ctx: ToolContext, args: DescribeIdeaInput) -> dict[str, Any]:
    idea = ideas.get(ctx.conn, args.id)
    if idea is None:
        raise ToolError(f"no idea #{args.id}")
    place = places.get(ctx.conn, idea.place_id) if idea.place_id else None
    original = messages.get(ctx.conn, idea.source_message_id) if idea.source_message_id else None
    return {
        "original_message": messages.as_said(original.text) if original else None,
        "idea": idea.model_dump(mode="json"),
        "place": place.model_dump(mode="json") if place else None,
        "outcomes": [o.model_dump(mode="json") for o in outcomes.list_for_idea(ctx.conn, idea.id)],
    }


@tool(
    name="search_ideas",
    description=(
        "Filter the ideas list. With no filters it returns everything that is not dropped. Each "
        "result is one compact line starting with the idea number."
    ),
)
def search_ideas(ctx: ToolContext, args: SearchIdeasInput) -> dict[str, Any]:
    limit = max(1, min(args.limit, 200))
    found = ideas.search(
        ctx.conn,
        text=args.text,
        kind=args.kind,
        status=args.status,
        participant=args.participant,
        setting=args.setting,
        max_duration=args.max_duration_minutes,
        max_cost=args.max_cost_level,
        tags=args.tags,
        exclude_done_within_days=args.exclude_done_within_days,
        today=ctx.clock.today(),
        limit=limit,
    )
    return {"count": len(found), "ideas": [render_idea_line(idea) for idea in found]}
