"""Orchestrates the stages: frame, context, shortlist, evaluate, discover, compose, log."""

from __future__ import annotations

from datetime import date, timedelta

from familydb.availability import enrichment_available
from familydb.dates import parse_date_range, utc_iso, weekend_window
from familydb.errors import ToolError
from familydb.store import ideas, suggestions
from familydb.store.db import transaction
from familydb.suggest.compose import compose
from familydb.suggest.context import build_context
from familydb.suggest.discover import discover
from familydb.suggest.evaluate import evaluate
from familydb.suggest.log import log_suggestion
from familydb.suggest.shortlist import shortlist
from familydb.suggest.types import Constraints, SuggestInput, SuggestResult
from familydb.tools import ToolContext

RECENT_SUGGESTION_DAYS = 14


def resolve_window(args: SuggestInput, today: date) -> tuple[tuple[date, date] | None, str]:
    if args.window == "someday":
        return None, "someday"
    if args.window == "dates":
        if not args.start or not args.end:
            raise ToolError("window=dates needs start and end")
        start, end = parse_date_range(args.start, args.end)
        if (end - start).days > 14:
            raise ToolError("ask about at most two weeks at a time")
        label = "those dates"
    elif args.window == "next_weekend":
        start, end = weekend_window(today + timedelta(days=7))
        label = "next weekend"
    else:
        start, end = weekend_window(today)
        label = "this weekend"
    if start == end:
        label += f" ({start:%a %d %b})"
    else:
        label += f" ({start:%a %d} to {end:%a %d %b})"
    return (start, end), label


def run(ctx: ToolContext, args: SuggestInput) -> SuggestResult:
    """The whole engine for one question; returns the structured result the chat model composes."""
    today = ctx.clock.today()
    window, label = resolve_window(args, today)
    context = build_context(ctx, window)
    constraints = Constraints(
        participants=list(args.participants),
        max_cost_level=args.max_cost_level,
        setting=args.setting,
        max_travel_minutes=args.max_travel_minutes,
        max_duration_minutes=args.max_duration_minutes,
    )
    all_ideas = ideas.list_all(ctx.conn)
    kept, ruled_out, extras = shortlist(all_ideas, context, constraints, ctx.settings)
    evaluated, stale_ids = evaluate(ctx.conn, kept, context, constraints, ctx.settings, ctx.clock)
    skipped = list(context.skipped)
    if stale_ids and enrichment_available(ctx.settings):
        with transaction(ctx.conn):
            ideas.requeue_enrichment(ctx.conn, stale_ids, now=ctx.now_iso())
        skipped.append("stale place details re-queued for a refresh")

    finds, note = ([], None)
    if args.discover:
        finds, note = discover(ctx, context, args.question)
    if note:
        skipped.append(note)

    since = utc_iso(ctx.clock.now() - timedelta(days=RECENT_SUGGESTION_DAYS))
    recently = suggestions.recently_suggested(ctx.conn, since=since)
    candidates = evaluated + extras + ruled_out
    suggestion_id = log_suggestion(
        ctx.conn,
        asked_by=ctx.member.id if ctx.member else None,
        window_start=window[0].isoformat() if window else None,
        window_end=window[1].isoformat() if window else None,
        candidates=candidates,
        finds=finds,
        now=ctx.now_iso(),
    )
    by_id = {idea.id: idea for idea in all_ideas}
    return compose(context, label, candidates, finds, skipped, by_id, recently, suggestion_id)
