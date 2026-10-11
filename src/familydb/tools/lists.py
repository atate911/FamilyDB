"""The family's lists: one tool for the shopping list and any other they name ("the hardware
list"). Not tasks: a thing to buy has no time; "remind me to buy milk on Tuesday" is a task.

Adding and ticking are for whoever may change things; a kid reads them (what kids may do with the
lists is the family's to decide, docs/DESIGN.md section 16).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.base import roles
from familydb.base.errors import ToolError
from familydb.store import lists
from familydb.store.db import transaction
from familydb.tools.registry import ToolContext, keep_undo, tool

MAX_ITEMS = 30
MAX_TEXT = 120
# A list said back is what is still to get, and the last few ticked.
TICKED_SHOWN = 5
GROWN_UPS = "the lists are kept by the grown-ups; ask a parent to put it on"


class ShoppingListInput(BaseModel):
    action: Literal["add", "tick", "untick", "remove", "clear_ticked", "show"]
    items: list[str] = Field(
        default_factory=list, description="The things, as said; none for show or clear_ticked."
    )
    name: str = Field(default="shopping", description="Which list, if another is named.")


@tool(
    name="shopping_list",
    description=(
        "The family's lists: add what they need, tick what is bought, show one. A thing to do at "
        "a time is a task."
    ),
    writes=True,
)
def shopping_list(ctx: ToolContext, args: ShoppingListInput) -> dict[str, Any]:
    name = lists.name_of(args.name)
    wanted = [text.strip()[:MAX_TEXT] for text in args.items if text.strip()][:MAX_ITEMS]
    if args.action == "show":
        return _shown(ctx, name)
    if ctx.member is not None and not roles.may(ctx.member.role, "change"):
        raise ToolError(GROWN_UPS)
    if args.action != "clear_ticked" and not wanted:
        raise ToolError(f"say what to {args.action}")
    now = ctx.now_iso()
    by = ctx.member.id if ctx.member else None
    done: list[str] = []
    other: list[str] = []
    with transaction(ctx.conn):
        list_ref = lists.list_id(ctx.conn, name, now)
        if args.action == "clear_ticked":
            cleared = lists.clear_ticked(ctx.conn, list_ref)
            return {"list": name, "cleared": cleared, "open": _open(ctx, list_ref)}
        for text in wanted:
            if args.action == "add":
                added = lists.add(ctx.conn, list_ref, text, by=by, now=now)
                (done if added is not None else other).append(added.text if added else text)
                continue
            there = lists.by_text(ctx.conn, list_ref, text)
            if there is None:
                other.append(text)
            elif args.action == "remove":
                lists.remove(ctx.conn, there.id)
                done.append(there.text)
            else:
                ticked = args.action == "tick"
                lists.set_ticked(ctx.conn, there.id, by=by, now=now if ticked else None)
                done.append(there.text)
    if done:
        _keep_undo(ctx, args.action, name, done)
    said: dict[str, Any] = {"list": name, args.action: done, "open": _open(ctx, list_ref)}
    if other:
        said["already" if args.action == "add" else "not_on_it"] = other
    return said


def _open(ctx: ToolContext, list_ref: int) -> int:
    return sum(1 for item in lists.items(ctx.conn, list_ref) if item.ticked_at is None)


def _shown(ctx: ToolContext, name: str) -> dict[str, Any]:
    list_ref = lists.find(ctx.conn, name)
    if list_ref is None:
        return {"list": name, "to_get": [], "others": lists.names(ctx.conn)}
    held = lists.items(ctx.conn, list_ref)
    return {
        "list": name,
        "to_get": [item.text for item in held if item.ticked_at is None],
        "ticked": [item.text for item in held if item.ticked_at is not None][:TICKED_SHOWN],
    }


# What undoing each does: the opposite, on the same things.
OPPOSITE = {"add": "remove", "remove": "add", "tick": "untick", "untick": "tick"}


def _keep_undo(ctx: ToolContext, action: str, name: str, done: list[str]) -> None:
    if action not in OPPOSITE:
        return  # a cleared list is not brought back
    said = {"add": "added", "remove": "took off", "tick": "ticked", "untick": "unticked"}[action]
    keep_undo(
        ctx,
        "list",
        f"{said} {', '.join(done)} on the {name} list",
        list=name,
        action=OPPOSITE[action],
        items=done,
    )
