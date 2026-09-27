"""Tools for the kids' wish lists (docs/WISHES.md). The rules are wish_service.py's; these only
say who is asking and hand back the few fields the model needs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb import roles, wish_service
from familydb.errors import ToolError
from familydb.store import members
from familydb.store.members import Member
from familydb.tools.registry import ToolContext, tool

List = Literal["everyday", "christmas", "birthday"]
Category = Literal["app", "buy", "do", "go", "watch", "play", "eat", "gift", "other"]


class AddWishInput(BaseModel):
    title: str
    topic: str = Field(description="1-2 words, shared by the same ask (cat, dog: pet).")
    list: List = "everyday"
    category: Category | None = None
    notes: str | None = None
    for_whom: str | None = Field(default=None, description="A kid's name; parents only.")
    idea_id: int | None = Field(default=None, description="An idea saved alongside.")


class UpdateWishInput(BaseModel):
    wish_id: int
    position: int | None = Field(default=None, description="1 is the top of its list.")
    list: List | None = None
    title: str | None = None
    notes: str | None = None
    status: Literal["withdrawn", "granted", "declined"] | None = None
    answer_note: str | None = None
    ask_parent: bool = Field(
        default=False, description="She asks a parent about a turned-away ask."
    )


class TurnAwayInput(BaseModel):
    summary: str = Field(description="One neutral line.")
    concern: Literal["rule", "sibling", "inappropriate"]
    parent_may_review: bool = Field(description="Fair to let her ask a parent.")


def _asker(ctx: ToolContext) -> Member:
    if ctx.member is None:
        raise ToolError("nobody to keep a wish list for")
    return ctx.member


def _occasion(chosen: List | None) -> Any:
    if chosen is None:
        return wish_service.KEEP
    return None if chosen == "everyday" else chosen


@tool(
    name="add_wish",
    description=(
        "Put a kid's own want on her wish list. Result: added, duplicate, locked (with when "
        "she may ask again), too_many or list_full."
    ),
    writes=True,
)
def add_wish(ctx: ToolContext, args: AddWishInput) -> dict[str, Any]:
    by = _asker(ctx)
    owner = by
    if args.for_whom:
        if not roles.may(by.role, "decide"):
            raise ToolError("a kid's wish goes on her own list")
        found = members.find_by_name(ctx.conn, args.for_whom)
        if found is None:
            raise ToolError(f"no family member called {args.for_whom!r}")
        owner = found
    added = wish_service.add(
        ctx.conn,
        ctx.settings,
        by=by,
        owner=owner,
        title=args.title,
        topic=args.topic,
        occasion=_occasion(args.list),
        category=args.category,
        notes=args.notes,
        idea_id=args.idea_id,
        message_id=ctx.message_id,
        now=ctx.clock.now(),
    )
    return added.compact()


@tool(
    name="update_wish",
    description=(
        "Move (position, list), reword or withdraw a wish; a parent grants or declines it."
    ),
    writes=True,
)
def update_wish(ctx: ToolContext, args: UpdateWishInput) -> dict[str, Any]:
    by = _asker(ctx)
    now = ctx.clock.now()
    wish = None
    if args.title is not None or args.notes is not None:
        wish = wish_service.edit(
            ctx.conn,
            by=by,
            wish_id=args.wish_id,
            title=args.title,
            notes=wish_service.KEEP if args.notes is None else args.notes,
            now=now,
        )
    if args.position is not None or args.list is not None:
        wish = wish_service.move(
            ctx.conn,
            ctx.settings,
            by=by,
            wish_id=args.wish_id,
            position=args.position,
            occasion=_occasion(args.list),
            now=now,
        )
    if args.ask_parent:
        wish = wish_service.ask_parent(ctx.conn, ctx.settings, by=by, wish_id=args.wish_id, now=now)
    if args.status == "withdrawn":
        wish = wish_service.withdraw(ctx.conn, by=by, wish_id=args.wish_id, now=now)
    elif args.status in ("granted", "declined"):
        wish = wish_service.answer(
            ctx.conn,
            ctx.settings,
            by=by,
            wish_id=args.wish_id,
            granted=args.status == "granted",
            note=args.answer_note,
            now=now,
        )
    if wish is None:
        raise ToolError("nothing to change: give a position, list, title, notes or status")
    out: dict[str, Any] = {
        "wish": {"id": wish.id, "title": wish.title, "status": wish.status, "rank": wish.rank}
    }
    if wish.status == "declined" and wish.locked_until:
        out["locked_until"] = wish.locked_until[:10]
    return out


@tool(
    name="turn_away",
    description=(
        "Record a kid's ask you are saying no to (a house rule, against a sibling, or "
        "inappropriate: the parents are told)."
    ),
    writes=True,
)
def turn_away(ctx: ToolContext, args: TurnAwayInput) -> dict[str, Any]:
    owner = _asker(ctx)
    if roles.may(owner.role, "decide"):
        raise ToolError("only a kid's ask is turned away")
    turned = wish_service.turn_away(
        ctx.conn,
        ctx.settings,
        owner=owner,
        summary=args.summary,
        concern=args.concern,
        reviewable=args.parent_may_review,
        message_id=ctx.message_id,
        now=ctx.clock.now(),
    )
    return turned.compact()
