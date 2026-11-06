"""Recording how something went."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from familydb.base.dates import parse_date
from familydb.base.errors import ToolError
from familydb.store import ideas, outcomes, plans
from familydb.store.db import transaction
from familydb.tools.registry import ToolContext, tool


class RecordOutcomeInput(BaseModel):
    idea_id: int | None = Field(default=None, description="The idea number, if known.")
    plan_id: int | None = Field(default=None, description="The plan number, if known instead.")
    happened_on: str | None = Field(default=None, description="YYYY-MM-DD. Default: today.")
    rating: int | None = Field(default=None, description="1 (awful) to 10 (perfect).")
    would_repeat: bool | None = Field(default=None, description="Worth doing again?")
    notes: str | None = Field(default=None, description="What they said about it.")


@tool(
    name="record_outcome",
    description=(
        "Record that an idea was done and how it went. Marks the idea done (a recipe stays one to "
        "cook), counts the visit and updates its average rating. Returns the outcome and the "
        "updated idea."
    ),
    writes=True,
    needs="change",
)
def record_outcome(ctx: ToolContext, args: RecordOutcomeInput) -> dict[str, Any]:
    plan = None
    if args.plan_id is not None:
        plan = plans.get(ctx.conn, args.plan_id)
        if plan is None:
            raise ToolError(f"no plan #{args.plan_id}")
    idea_id = args.idea_id if args.idea_id is not None else (plan.idea_id if plan else None)
    if idea_id is None:
        raise ToolError("give idea_id (or a plan_id that is linked to an idea)")
    if plan is not None and plan.idea_id is not None and plan.idea_id != idea_id:
        raise ToolError(
            f"plan #{plan.id} is for idea #{plan.idea_id}, not #{idea_id}; nothing was recorded"
        )
    if ideas.get(ctx.conn, idea_id) is None:
        raise ToolError(f"no idea #{idea_id}")
    if args.rating is not None and not 1 <= args.rating <= 10:
        raise ToolError("rating must be between 1 and 10")
    day = parse_date(args.happened_on) if args.happened_on else ctx.clock.today()
    if day > ctx.clock.today():
        raise ToolError(
            f"{day.isoformat()} is in the future; outcomes are for things that happened"
        )
    with transaction(ctx.conn):
        # Answered again after a failure, a message finds the visit it already counted: the
        # outcome and the idea's count are one write, and the call's record another (registry).
        before = (
            outcomes.for_message(
                ctx.conn,
                ctx.message_id,
                idea_id=idea_id,
                happened_on=day.isoformat(),
            )
            if ctx.message_id is not None
            else None
        )
        if before is not None:
            return {
                "duplicate_of": before.id,
                "note": "Already recorded for this message; nothing was counted again.",
                "outcome": before.model_dump(mode="json"),
                "idea": _idea(ctx, idea_id),
            }
        outcome = outcomes.insert(
            ctx.conn,
            idea_id=idea_id,
            plan_id=args.plan_id,
            happened_on=day.isoformat(),
            rating=args.rating,
            would_repeat=args.would_repeat,
            notes=args.notes,
            recorded_by=ctx.member.id if ctx.member else None,
            message_id=ctx.message_id,
            now=ctx.now_iso(),
        )
        idea = ideas.apply_outcome(
            ctx.conn,
            idea_id,
            happened_on=day.isoformat(),
            avg_rating=outcomes.average_rating(ctx.conn, idea_id),
            now=ctx.now_iso(),
        )
    return {
        "outcome": outcome.model_dump(mode="json"),
        "idea": idea.model_dump(mode="json") if idea else None,
    }


def _idea(ctx: ToolContext, idea_id: int) -> dict[str, Any] | None:
    idea = ideas.get(ctx.conn, idea_id)
    return idea.model_dump(mode="json") if idea else None
