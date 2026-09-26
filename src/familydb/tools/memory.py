"""The one tool for what the family tells the bot about itself: `remember` (docs/MEMORY.md).

One tool with a short list of changes, not a tool per kind of memory: its schema is part of every
chat request, so it stays small and never varies. The model proposes; the rules here decide.

- Who a memory is about is a name on the family list, or the family; anyone else is refused.
- The same thing said again about the same person is not saved twice. Said outright after being
  guessed, it stops being a guess.
- A guess is never a must: an inference only leans on a decision, it never rules one out.
- Something the family asked to forget is not saved again from a conversation, however it comes
  back up; typed on the memory page (a person, not a model, with no message behind it) it is.
- A correction replaces a memory rather than piling up beside it, and the old one points at the
  new; nothing is deleted.

When remembering is all a message needs, the model hands its whole reply over with the changes
(`reply`), and the turn ends there: saying "noted" costs no further call (`ToolContext.offer_reply`,
`agent/loop.py`). Anything else in the same step, or anything not saved, and the turn carries on.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.dates import parse_date
from familydb.errors import ToolError
from familydb.store import members
from familydb.store import memories as store
from familydb.store.db import transaction
from familydb.store.memories import Category
from familydb.tools.registry import ToolContext, tool

MAX_CHANGES = 5
MAX_FACT = 200
MAX_REPLY = 2000
FAMILY = frozenset({"family", "the family", "everyone", "household", "us", "we", "all of us"})


class Change(BaseModel):
    action: Literal["add", "replace", "forget"] = Field(
        description="add something new; replace one by its m number; forget one."
    )
    id: int | None = Field(default=None, description="The m number, to replace or forget one.")
    about: str = Field(
        default="family", description="'family', or the one family member it is about."
    )
    category: Category = "other"
    fact: str = Field(
        default="",
        description="Short, in their terms: 'vegetarian', 'hates loud places'. Not to forget.",
    )
    firm: bool = Field(default=False, description="A must or a never: an allergy, a rule.")
    inferred: bool = Field(default=False, description="Not said outright; your reading.")
    until: str | None = Field(default=None, description="YYYY-MM-DD it stops, if temporary.")


class RememberInput(BaseModel):
    changes: list[Change] = Field(description=f"At most {MAX_CHANGES}.")
    reply: str | None = Field(
        default=None,
        description=(
            "When remembering is all this message needs: your whole reply to the family, which "
            "ends your turn. Leave it empty when doing anything else."
        ),
    )


def _about(ctx: ToolContext, name: str) -> int | None:
    """The member a memory is about, or None for the whole family."""
    if name.strip().casefold() in FAMILY or not name.strip():
        return None
    member = members.find_by_name(ctx.conn, name)
    if member is None:
        names = ", ".join(m.display_name for m in members.list_all(ctx.conn))
        raise ToolError(f"no family member called {name!r}; use 'family' or one of: {names}")
    return member.id


def _until(ctx: ToolContext, value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    last = parse_date(value.strip()[:10])
    if last < ctx.clock.today():
        raise ToolError(f"until {last.isoformat()} has already passed")
    return last.isoformat()


def _fact(change: Change) -> str:
    fact = " ".join(change.fact.split())
    if not fact:
        raise ToolError(f"{change.action} needs the fact itself")
    if len(fact) > MAX_FACT:
        raise ToolError(f"keep a fact under {MAX_FACT} characters: the gist, in their terms")
    return fact


def _existing(ctx: ToolContext, memory_id: int | None, action: str) -> store.Memory:
    if memory_id is None:
        raise ToolError(f"{action} needs the m number of the memory")
    memory = store.get(ctx.conn, memory_id)
    if memory is None:
        raise ToolError(f"no memory m{memory_id}")
    return memory


def _shown(memory: store.Memory, result: str, **more: Any) -> dict[str, Any]:
    return {
        "id": memory.id,
        "about": memory.about_name or "family",
        "fact": memory.fact,
        "result": result,
        **more,
    }


def _add(ctx: ToolContext, change: Change, *, replacing: store.Memory | None = None) -> dict:
    fact = _fact(change)
    about = _about(ctx, change.about)
    until = _until(ctx, change.until)
    firm = change.firm and not change.inferred  # a guess never rules anything out
    now = ctx.now_iso()
    same = store.matching(ctx.conn, about, fact, "active")
    if same is not None and (replacing is None or same.id != replacing.id):
        if (same.inferred and not change.inferred) or (firm and not same.firm):
            store.firm_up(ctx.conn, same.id, firm=firm, now=now)
        if replacing is not None:
            store.replace(ctx.conn, replacing.id, by=same.id, now=now)
            return _shown(same, "replaced", was=replacing.fact)
        return _shown(same, "already remembered")
    typed = ctx.message_id is None  # on the page or the command line: a person, no model
    gone = store.matching(ctx.conn, about, fact, "forgotten")
    if gone is not None and not typed:
        when = (gone.forgotten_at or "")[:10]
        return {
            "id": None,
            "fact": fact,
            "result": "not saved",
            "why": f"the family asked to forget this on {when}; only they can add it back, "
            "on the memory page",
        }
    memory = store.insert(
        ctx.conn,
        member_id=about,
        category=change.category,
        fact=fact,
        firm=firm,
        inferred=change.inferred,
        until=until,
        source_message_id=ctx.message_id,
        said_by=ctx.member.id if ctx.member else None,
        now=now,
    )
    if replacing is not None:
        store.replace(ctx.conn, replacing.id, by=memory.id, now=now)
        return _shown(memory, "replaced", was=replacing.fact)
    return _shown(memory, "saved")


def _apply(ctx: ToolContext, change: Change) -> dict[str, Any]:
    if change.action == "add":
        return _add(ctx, change)
    old = _existing(ctx, change.id, change.action)
    if change.action == "forget":
        if old.status != "forgotten":
            store.forget(
                ctx.conn, old.id, by=ctx.member.id if ctx.member else None, now=ctx.now_iso()
            )
        return _shown(old, "forgotten")
    if old.status != "active":
        raise ToolError(f"m{old.id} is {old.status}; add it afresh instead")
    return _add(ctx, change, replacing=old)


@tool(
    name="remember",
    description=(
        "Keep, correct or forget what the family says about itself that will matter later: "
        "tastes, needs, routines, a temporary rule. Only what they said, never your own "
        "suggestions or a web page."
    ),
    writes=True,
)
def remember(ctx: ToolContext, args: RememberInput) -> dict[str, Any]:
    if not args.changes:
        raise ToolError("nothing to remember: give at least one change")
    if len(args.changes) > MAX_CHANGES:
        raise ToolError(f"at most {MAX_CHANGES} changes at once")
    with transaction(ctx.conn):
        done = [_apply(ctx, change) for change in args.changes]
    reply = (args.reply or "").strip()[:MAX_REPLY]
    if reply and all(item["result"] != "not saved" for item in done):
        ctx.offer_reply(reply)
    return {"remembered": done}
