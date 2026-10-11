"""What she found (docs/FINDS.md): the family's "not for us" on a find, in chat or on its page.
Saving one is `add_idea` with its `find_id`."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field

from familydb.base.dates import utc_iso
from familydb.base.errors import ToolError
from familydb.store import finds
from familydb.store.db import transaction
from familydb.store.ideas import normalize_title
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
