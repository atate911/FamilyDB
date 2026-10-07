"""Orchestrates the stages: frame, context, shortlist, evaluate, discover, compose, log."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from familydb import happening
from familydb.availability import enrichment_available
from familydb.dates import parse_date_range, utc_iso, weekend_window
from familydb.errors import ToolError
from familydb.store import ideas, members, memories, outcomes, plans, suggestions
from familydb.store.db import transaction
from familydb.store.ideas import Idea
from familydb.suggest import listed as listing
from familydb.suggest.compose import choose, compose
from familydb.suggest.context import build_context
from familydb.suggest.discover import discover
from familydb.suggest.evaluate import evaluate
from familydb.suggest.log import log_suggestion
from familydb.suggest.origin import resolve as resolve_origin
from familydb.suggest.places import find_places
from familydb.suggest.places import wanted as places_wanted
from familydb.suggest.rules import fold
from familydb.suggest.shortlist import FAVOURITE_RATING, RATING_DAYS, shortlist
from familydb.suggest.types import (
    DAY_END,
    DAY_START,
    Candidate,
    Chosen,
    Constraints,
    Context,
    DayBounds,
    SuggestInput,
    SuggestResult,
    WebFind,
    clock,
)
from familydb.tools import ToolContext

RECENT_SUGGESTION_DAYS = 14


NOW_HOURS = 4
MAX_TOPIC = 80
MAX_NOW_HOURS = 12


def _minute(value: str | None, name: str) -> int | None:
    if not value:
        return None
    try:
        at = time.fromisoformat(value.strip())
    except ValueError as exc:
        raise ToolError(f"{name} must be HH:MM") from exc
    return at.hour * 60 + at.minute


def resolve_window(
    args: SuggestInput, now: datetime
) -> tuple[tuple[date, date] | None, str, DayBounds]:
    """The days asked about, how to say them, and the part of each day that counts."""
    today = now.date()
    # Rounded up to five minutes, which steadies the labels.
    minute = min(24 * 60, -(-(now.hour * 60 + now.minute) // 5) * 5)
    from_minute = _minute(args.from_time, "from_time")
    until_minute = _minute(args.until_time, "until_time")
    if from_minute is not None and until_minute is not None and until_minute <= from_minute:
        raise ToolError("until_time must be after from_time")
    bounds = DayBounds(
        start=from_minute if from_minute is not None else DAY_START,
        end=until_minute if until_minute is not None else DAY_END,
    )
    if args.window == "someday":
        return None, "someday", bounds
    if args.window == "now":
        hours = args.hours or NOW_HOURS
        if not 1 <= hours <= MAX_NOW_HOURS:
            raise ToolError(f"hours must be 1 to {MAX_NOW_HOURS}")
        end = min(24 * 60, minute + hours * 60)
        # Not held to the usual 08:00 to 22:00.
        frame = DayBounds(start=0, end=24 * 60, first_start=minute, last_end=end)
        return (today, today), f"now until {clock(end)}", frame
    if args.window == "today":
        start = max(minute, bounds.start)
        if start >= bounds.end:
            raise ToolError("that part of today has passed; ask about another day")
        frame = replace(bounds, first_start=start)
        return (today, today), f"today ({today:%a %d %b}) from {clock(start)}", frame
    if args.window == "dates":
        if not args.start or not args.end:
            raise ToolError("window=dates needs start and end")
        start_day, end_day = parse_date_range(args.start, args.end)
        if (end_day - start_day).days > 14:
            raise ToolError("ask about at most two weeks at a time")
        label = "those dates"
    elif args.window == "next_weekend":
        # On a weekend day this means the coming Saturday.
        _, this_end = weekend_window(today)
        start_day, end_day = weekend_window(this_end + timedelta(days=1))
        label = "next weekend"
    else:
        start_day, end_day = weekend_window(today)
        label = "this weekend"
    if start_day == end_day:
        label += f" ({start_day:%a %d %b})"
    else:
        label += f" ({start_day:%a %d} to {end_day:%a %d %b})"
    if from_minute is not None or until_minute is not None:
        label += f", {clock(bounds.start)}-{clock(bounds.end)}"
    # Asked on the day itself, the part gone is not free time.
    frame = replace(bounds, first_start=minute) if start_day == today else bounds
    return (start_day, end_day), label, frame


@dataclass
class Assessment:
    """Everything the engine found for one question, before it is cut down for the chat model:
    every candidate with its verdict, the finds, the notes, and the suggestion's log row. A
    stronger call choosing among them reads it whole (suggest/dossier.py)."""

    args: SuggestInput
    context: Context
    label: str
    candidates: list[Candidate]
    finds: list[WebFind]
    skipped: list[str]
    by_id: dict[int, Idea]
    recently: set[int]
    suggestion_id: int
    loved: set[int]  # done and loved: "again", or rated FAVOURITE_RATING or more lately
    shown: list[Candidate]  # the engine's own cut, when nobody chose
    held_back: int


def run(ctx: ToolContext, args: SuggestInput, *, refresh_stale: bool = True) -> SuggestResult:
    """The whole engine for one question; returns the structured result the chat model composes.
    `refresh_stale` queues a paid lookup per stale place; code running with no model call
    (commands.py, the evening check) passes False."""
    return result_of(assess(ctx, args, refresh_stale=refresh_stale))


def result_of(a: Assessment, chosen: Chosen | None = None) -> SuggestResult:
    """The result the chat model is given: the engine's own cut, or, when a stronger call chose
    (suggest/choosing.py), its picks leading and never cut."""
    shown, held_back = a.shown, a.held_back
    picked = [p.idea_id for p in chosen.picks if p.idea_id is not None] if chosen else []
    if picked:
        shown, held_back = choose(
            a.candidates, a.by_id, a.recently, prefer=a.args.prefer, loved=a.loved, picked=picked
        )
    return compose(
        a.context, a.label, shown, held_back, a.finds, a.skipped, a.suggestion_id, chosen
    )


def assess(ctx: ToolContext, args: SuggestInput, *, refresh_stale: bool = True) -> Assessment:
    """Every stage but the last: the window, the context, the rules, the checks, the engine's own
    cut, the finds and the log."""
    window, label, bounds = resolve_window(args, ctx.clock.now())
    context = build_context(ctx, window, bounds)
    context.origin, where_note = resolve_origin(ctx, args.near, args.window)
    if where_note:
        context.skipped.append(where_note)
    all_ideas = ideas.list_all(ctx.conn)
    listed = {idea.id for idea in all_ideas if idea.status != "dropped"}
    unknown = sorted(set(args.idea_ids) - listed)
    idea_ids = [idea_id for idea_id in args.idea_ids if idea_id in listed]
    constraints = Constraints(
        idea_ids=idea_ids,
        participants=list(args.participants),
        max_cost_level=args.max_cost_level,
        setting=args.setting,
        max_travel_minutes=args.max_travel_minutes,
        max_duration_minutes=args.max_duration_minutes,
        # Folded, so the same subject is the same search.
        topic=" ".join(args.topic.casefold().split())[:MAX_TOPIC],
    )
    # The family's firm rules for who is coming, held by code (suggest/rules.py).
    people = members.list_all(ctx.conn)
    held = memories.held(ctx.conn, today=ctx.clock.today())
    constraints = fold(constraints, held, people, ctx.member)
    # What the family said of what they did: "not again" leaves it out, a rating counts for a
    # year, and "again" or a high rating is a favourite.
    again = outcomes.latest_preferences(ctx.conn)
    excluded = {idea_id for idea_id, yes in again.items() if not yes}
    year_ago = ctx.clock.today() - timedelta(days=RATING_DAYS)
    ratings = outcomes.recent_ratings(ctx.conn, since=year_ago.isoformat())
    loved = {idea_id for idea_id, yes in again.items() if yes} | {
        idea_id for idea_id, said in ratings.items() if said and said[0] >= FAVOURITE_RATING
    }
    kept, ruled_out = shortlist(
        [idea for idea in all_ideas if idea.id not in excluded],
        context,
        constraints,
        ctx.settings,
        people=people,
        plans=plans.latest_by_idea(ctx.conn),
        ratings=ratings,
        prefer=args.prefer,
    )
    ruled_out.extend(
        Candidate(
            idea_id=idea.id,
            title=idea.title,
            verdict="ruled_out",
            reasons=["family said they would not repeat this"],
        )
        for idea in all_ideas
        if idea.id in excluded
        and idea.status != "dropped"
        and (not idea_ids or idea.id in idea_ids)
    )
    evaluated, stale_ids = evaluate(ctx.conn, kept, context, constraints, ctx.settings, ctx.clock)
    candidates = evaluated + ruled_out
    since = utc_iso(ctx.clock.now() - timedelta(days=RECENT_SUGGESTION_DAYS))
    recently = suggestions.recently_suggested(ctx.conn, since=since)
    by_id = {idea.id: idea for idea in all_ideas}
    shown, held_back = choose(candidates, by_id, recently, prefer=args.prefer, loved=loved)
    skipped = list(context.skipped)
    if unknown:
        # A wrong number must not quietly empty the answer: say so, widen when nothing is left.
        names = ", ".join(f"#{idea_id}" for idea_id in unknown)
        widened = "; considered every idea instead" if not idea_ids else ""
        skipped.append(f"no idea {names} on the list{widened}")
    # Looked up again only if it is shown: every idea is evaluated now, and a lookup is paid for.
    on_show = {c.idea_id for c in shown}
    stale_shown = [idea_id for idea_id in stale_ids if idea_id in on_show]
    if stale_shown and refresh_stale and enrichment_available(ctx.settings):
        with transaction(ctx.conn):
            ideas.requeue_enrichment(ctx.conn, stale_shown, now=ctx.now_iso())
        skipped.append("stale place details re-queued for a refresh")

    # What the family's sources already list for these days costs nothing to read; when they
    # list enough, the web is not searched again, unless the question asks for something.
    stored = listing.listed(ctx, context)
    finds, note = ([], None)
    # A place nothing saved fits, found on the web, when the family has it on (suggest/places.py).
    if places_wanted(context, constraints, candidates, ctx.settings):
        finds, note = find_places(ctx, context, constraints)
        if note:
            skipped.append(note)
    if args.discover and (constraints.topic or len(stored) < listing.COVERED):
        events, note = discover(ctx, context, constraints)
        finds = finds + events
        if note:
            skipped.append(note)
    finds, more = listing.merge_finds(stored, finds)
    if more:
        skipped.append(f"{more} more listed for these days on the page {happening.NAME}")

    suggestion_id = log_suggestion(
        ctx.conn,
        asked_by=ctx.member.id if ctx.member else None,
        window_start=window[0].isoformat() if window else None,
        window_end=window[1].isoformat() if window else None,
        candidates=candidates,
        shown=on_show,
        finds=finds,
        now=ctx.now_iso(),
    )
    return Assessment(
        args,
        context,
        label,
        candidates,
        finds,
        skipped,
        by_id,
        recently,
        suggestion_id,
        loved,
        shown,
        held_back,
    )
