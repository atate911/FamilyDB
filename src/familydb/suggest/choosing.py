"""Choosing what to suggest: for a planning question, a stronger call weighs the dossier
(suggest/dossier.py) and picks, and the chat model words the picks (gateway kind `choose`).

The family's principle: pay for judgement, not lookups, and give the judgement everything. Code
has already checked the hours, the travel, the weather and the free time; what it cannot know is
what suits this family this week, and that is what this call is for.

Its five answers (docs/AI_CALLS.md): asked by code from inside the chat's `suggest`, never by
the model escalating, and only while `choosing` is on, for a chat message from a grown-up about
anything but right now, with at least two options, a model to ask, room in the day's limit and
in `choose_budget` for this call's own estimate; it sees the dossier, nothing else; it may only
hand back picks among the options, which `give_picks` checks; what it hands back leads the
result, and the chat model says it in her words; and it is at most two calls at the family's
`choose_level`. One choice a message: a retry, or a second `suggest` in the same turn, reuses the
picks already made when they still hold, with no call.

Whatever goes wrong, the engine's own order is the answer, and nobody is told: why it did not
choose is logged, never put in the skipped checks the chat model reads out, since a kid must not
hear of budgets and nobody needs to hear of a call that was not made.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, time
from typing import Any

from familydb import roles
from familydb.agent import gateway, spending, uses
from familydb.agent.prompt import load_prompt
from familydb.agent.worker import worker_turn
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls, suggestions
from familydb.store.db import transaction
from familydb.suggest import dossier as dossiers
from familydb.suggest.types import Chosen, Pick, SuggestInput
from familydb.tools import ToolContext, build_registry

log = logging.getLogger(__name__)

KIND = "choose"
# What the prompt and the tool's schema add to the dossier, for the estimate.
TOOL_CHARS = 3000


def reason_not_to(ctx: ToolContext, args: SuggestInput) -> str | None:
    """Why no choice is made for this question, or None when one may be."""
    settings = ctx.settings
    if not uses.on(settings, "choose"):
        return "off"
    if args.window == "now":
        return "a question about right now"
    if ctx.message_id is None or ctx.member is None:
        return "not a chat message"
    if roles.daily_limited(ctx.member.role):
        return "a kid's question"
    if not settings.choose_budget:
        return "no budget"
    if not gateway.can_ask(settings, KIND, api=ctx.api):
        return "no model to ask"
    if spending.used_up(ctx.conn, settings, ctx.clock.now()):
        return "the day's limit is used up"
    return None


def spent_this_month(conn: sqlite3.Connection, settings: Any, now: datetime) -> float:
    local = now.astimezone(settings.tzinfo)
    start = datetime.combine(local.date().replace(day=1), time(), tzinfo=settings.tzinfo)
    return calls.spent_on(conn, (KIND,), since=utc_iso(start))


def _estimate(ctx: ToolContext, made: dossiers.Dossier) -> float:
    """The most this call could cost, at the model it would be asked of."""
    provider, model = gateway.answering(ctx.settings, KIND, api=ctx.api)
    spec = gateway.spec(KIND)
    return spending.estimate(
        provider.name,
        model,
        input_chars=len(made.text) + len(load_prompt(spec.prompt)) + TOOL_CHARS,
        max_tokens=spec.max_tokens or ctx.settings.max_output_tokens,
    )


def _fresh(ctx: ToolContext, made: dossiers.Dossier, a: Any) -> ToolContext:
    """A context of its own, so the chat turn keeps its own tools and turn id; the same message,
    so the call's cost and its tool call are the message's."""
    fresh = ToolContext(
        conn=ctx.conn,
        settings=ctx.settings,
        clock=ctx.clock,
        member=None,
        message_id=ctx.message_id,
        api=ctx.api,
        about=f"choosing, {a.label}",
    )
    fresh.scratch.update({"options": made.options, "cites": made.cites, "window": a.context.window})
    return fresh


def _made_before(ctx: ToolContext, fresh: ToolContext) -> bool:
    """Whether a choice made earlier for this message still holds; it is then put in `fresh`."""
    earlier = [
        row
        for row in calls.tool_calls_for_message(ctx.conn, ctx.message_id or 0)
        if row["tool_name"] == "give_picks" and not row["is_error"]
    ]
    if not earlier:
        return False
    try:
        given = json.loads(earlier[-1]["input"])
    except ValueError:
        return False
    answer = build_registry().dispatch("give_picks", given, fresh)
    return not answer.is_error and "chosen" in fresh.scratch


def choose(ctx: ToolContext, args: SuggestInput, a: Any) -> Chosen | None:
    """The picks for this question, or None for the engine's own order."""
    try:
        return _choose(ctx, args, a)
    except Exception:  # choosing is an improvement; it must never cost the suggestion
        log.exception("choosing what to suggest failed")
        return None


def _choose(ctx: ToolContext, args: SuggestInput, a: Any) -> Chosen | None:
    made = dossiers.build(ctx, args, a)
    if len(made.options) < 2:
        log.info("nothing to choose between for %s", a.label)
        return None
    fresh = _fresh(ctx, made, a)
    if not _made_before(ctx, fresh):
        now = ctx.clock.now()
        if spent_this_month(ctx.conn, ctx.settings, now) + _estimate(ctx, made) > (
            ctx.settings.choose_budget
        ):
            log.info("not choosing: this month's budget for it would be passed")
            return None
        try:
            result = gateway.ask(
                KIND,
                settings=ctx.settings,
                registry=build_registry(),
                ctx=fresh,
                current=worker_turn(ctx.clock, made.text),
                api=ctx.api,
            )
        except AgentError as exc:
            log.warning("the choice could not be made: %s", exc)
            return None
        if not gateway.handed_back(gateway.spec(KIND), result) or "chosen" not in fresh.scratch:
            log.warning("the choice came back without picks: %s", result.error or result.status)
            return None
    chosen = fresh.scratch["chosen"]
    picks = []
    for given in chosen["picks"]:
        option = made.options[given["ref"]]
        picks.append(
            Pick(
                ref=given["ref"],
                title=option.title,
                slot=given["slot"],
                reason=given["reason"],
                day=given["day"],
                idea_id=option.idea_id,
                url=option.url,
            )
        )
    kept = {"picks": [p.model_dump(exclude_none=True) for p in picks], "framing": chosen["framing"]}
    with transaction(ctx.conn):
        suggestions.set_picks(ctx.conn, a.suggestion_id, kept)
    return Chosen(picks, chosen["framing"])
