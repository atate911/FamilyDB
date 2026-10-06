"""Taking back the last thing somebody changed, for the `undo` tool, /undo, a page's Undo and the
button under a reply.

A write that can be taken back works out how in its own handler, from what it read before
writing, and leaves it with `keep`; dispatch stores it with the call (`tool_calls.undo`). Undoing
finds the call (the one a page or a button names, else the last of this person's in this chat
within a day), checks the record is as that call left it, and puts it back: so an undo never
undoes somebody else's later change. A call is undone once (`undone_at`).

What can be taken back: an idea added (dropped) or changed (its fields put back); a task added
(cancelled) or changed, snoozed, done or cancelled when it does not repeat (put back, its reminder
again if that time is still to come); a plan made (cancelled, its reminders with it) or moved or
renamed (put back); something remembered (forgotten); a list's things added, taken off, ticked or
unticked (the opposite). What cannot: how a plan went (counted into
the idea's numbers), a repeating task's round, a plan cancelled or a hand-made event deleted
(gone from Google), a kid's wish answered (she has been told), a memory replaced or forgotten, a
lookup asked for, and anything already sent.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from familydb import roles, task_service
from familydb.dates import utc_iso
from familydb.errors import ToolError
from familydb.store import calls, ideas, memories, plans, tasks
from familydb.store.db import from_json, transaction
from familydb.tools.registry import UNDO, ToolContext

# How long after a change it can be taken back.
WINDOW = timedelta(hours=24)
NOTHING = "nothing of yours to undo here from the last day"
CHANGED = "it has changed since, so it was left as it is"
TOO_LATE = "that was more than a day ago"
DONE_ALREADY = "that was undone already"
NOT_YOURS = "only your own things to do can be undone; ask a parent"
TASK_OPS = frozenset({"cancel_task", "restore_task"})


def keep(ctx: ToolContext, op: str, about: str, **facts: Any) -> None:
    """Leave how to take back what a tool just did, for dispatch to keep with the call. `about`
    says what was done, as the undo will say it ("added task #5 Call the plumber")."""
    ctx.scratch[UNDO] = {"op": op, "about": about, **facts}


def take_back(ctx: ToolContext) -> dict[str, Any]:
    """Undo the call `ctx.undo_target` names, else this person's last in this chat within a day.
    Returns what was undone; a ToolError says why nothing was."""
    conn = ctx.conn
    since = utc_iso(ctx.clock.now() - WINDOW)
    row = _target(ctx, since)
    if row is None:
        raise ToolError(NOTHING)
    if row["undone_at"] is not None:
        raise ToolError(DONE_ALREADY)
    if row["created_at"] < since:
        raise ToolError(TOO_LATE)
    inverse = from_json(row["undo"])
    _may(ctx, row, inverse)
    stamp = ctx.now_iso()
    with transaction(conn):
        if not calls.claim_undo(conn, row["id"], now=stamp):
            raise ToolError(DONE_ALREADY)  # a second press, at the same moment
    try:
        OPS[inverse["op"]](ctx, inverse)
    except Exception:
        with transaction(conn):
            calls.release_undo(conn, row["id"])
        raise
    return {"undone": inverse["about"]}


def _target(ctx: ToolContext, since: str) -> sqlite3.Row | None:
    if ctx.undo_target is not None:
        row = calls.get(ctx.conn, ctx.undo_target)
        return row if row is not None and row["undo"] is not None else None
    if ctx.member is None or ctx.message_id is None:
        return None
    return calls.last_undoable(
        ctx.conn, member_id=ctx.member.id, message_id=ctx.message_id, since=since
    )


def _may(ctx: ToolContext, row: sqlite3.Row, inverse: dict[str, Any]) -> None:
    """Whoever made the change may take it back, and anybody who may change things; a kid, only
    her own change to her own thing to do."""
    member = ctx.member
    if member is None or roles.may(member.role, "change"):
        return
    if row["member_id"] != member.id or inverse["op"] not in TASK_OPS:
        raise ToolError(NOT_YOURS)
    task = tasks.get(ctx.conn, inverse["task"])
    if task is None or task.owner_id != member.id:
        raise ToolError(NOT_YOURS)


# -- each way of putting something back


def _drop_idea(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    with transaction(ctx.conn):
        idea = ideas.get(ctx.conn, inverse["idea"])
        if idea is None or idea.status != inverse["status"]:
            raise ToolError(CHANGED)  # planned, done or dropped since
        ideas.update(ctx.conn, idea.id, {"status": "dropped"}, now=ctx.now_iso())


def _restore_idea(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    with transaction(ctx.conn):
        idea = ideas.get(ctx.conn, inverse["idea"])
        if idea is None:
            raise ToolError(CHANGED)
        now_as = idea.model_dump(mode="json")
        if any(now_as.get(key) != value for key, value in inverse["after"].items()):
            raise ToolError(CHANGED)
        ideas.update(ctx.conn, idea.id, inverse["before"], now=ctx.now_iso())


def _cancel_task(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    task_service.update(
        ctx.conn,
        inverse["task"],
        {"status": "cancelled"},
        now=ctx.now_iso(),
        revision=inverse["revision"],
        settings=ctx.settings,
    )


def _restore_task(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    """Its boxes as they were, and its reminder again if that time is still to come."""
    reminder = inverse.get("reminder")
    if reminder is not None and datetime.fromisoformat(reminder) <= ctx.clock.now():
        reminder = None
    task_service.update(
        ctx.conn,
        inverse["task"],
        dict(inverse["before"]),
        now=ctx.now_iso(),
        reminder=reminder,
        replace_reminder=inverse.get("reminder_changed", False),
        revision=inverse["revision"],
        settings=ctx.settings,
    )


def _plan_unchanged(ctx: ToolContext, inverse: dict[str, Any]) -> plans.Plan:
    plan = plans.get(ctx.conn, inverse["plan"])
    if plan is None or plan.status == "cancelled" or plan.updated_at != inverse["updated_at"]:
        raise ToolError(CHANGED)
    return plan


def _cancel_plan(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    from familydb.tools.gcal import UpdateEventInput, update_event

    plan = _plan_unchanged(ctx, inverse)
    update_event(_apart(ctx), UpdateEventInput(plan_id=plan.id, status="cancelled"))


def _restore_plan(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    from familydb.tools.gcal import UpdateEventInput, update_event

    plan = _plan_unchanged(ctx, inverse)
    before = inverse["before"]
    update_event(
        _apart(ctx),
        UpdateEventInput(
            plan_id=plan.id,
            title=before["title"],
            start=_local(before["start"], before["all_day"], ctx),
            end=_local(before["end"], before["all_day"], ctx) if before["end"] else None,
            all_day=before["all_day"],
        ),
    )


def _local(stored: str, all_day: bool, ctx: ToolContext) -> str:
    """A plan's stored time as the calendar tools take it: a date, or the family's clock."""
    if all_day:
        return stored[:10]
    return datetime.fromisoformat(stored).astimezone(ctx.clock.tz).strftime("%Y-%m-%dT%H:%M")


def _forget(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    with transaction(ctx.conn):
        kept = [memories.get(ctx.conn, memory_id) for memory_id in inverse["memories"]]
        if any(memory is None or memory.status != "active" for memory in kept):
            raise ToolError(CHANGED)
        for memory in kept:
            assert memory is not None
            memories.forget(
                ctx.conn, memory.id, by=ctx.member.id if ctx.member else None, now=ctx.now_iso()
            )


def _list(ctx: ToolContext, inverse: dict[str, Any]) -> None:
    """The opposite on the same things: added are taken off, ticked are unticked."""
    from familydb.tools.lists import ShoppingListInput, shopping_list

    shopping_list(
        _apart(ctx),
        ShoppingListInput(action=inverse["action"], items=inverse["items"], name=inverse["list"]),
    )


def _apart(ctx: ToolContext) -> ToolContext:
    """The context for a tool run to put something back: its own scratch, so what that run would
    leave to undo is not kept (undoing an undo is not offered)."""
    return dataclasses.replace(ctx, scratch={}, undo_target=None)


OPS: dict[str, Callable[[ToolContext, dict[str, Any]], None]] = {
    "drop_idea": _drop_idea,
    "restore_idea": _restore_idea,
    "cancel_task": _cancel_task,
    "restore_task": _restore_task,
    "cancel_plan": _cancel_plan,
    "restore_plan": _restore_plan,
    "forget": _forget,
    "list": _list,
}
