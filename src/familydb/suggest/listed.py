"""Stage: her back pocket for the days asked (docs/FINDS.md), read from the `finds` table with
no model and no network: what the family's sources list near home (jobs/happening.py) and what
earlier searches found for those days, and a few places she found to go any time.

Each is offered as a web find is, with when it is on and who listed it, for the model to name as
not on the list, once checked as the ideas are (suggest/pocket.py). What is said of each is
code's: the day and time in the family's words, and the name of the calendar, Ticketmaster, or
the site a search read.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from familydb import happening
from familydb.base.urls import clean_url
from familydb.store import finds
from familydb.store.finds import Find
from familydb.suggest.types import Constraints, Context, WebFind
from familydb.tools import ToolContext

# The most offered with one answer, the discovery worker's own finds among them: the result is
# sent to the model and sent again with its reply.
MAX_LISTED = 8
SUMMARY_MAX = 100
# Places she found to go any time, offered with one answer at most, and read to choose them.
ANYTIME_MOST = 3
ANYTIME_READ = 30
# A word of the topic this short says nothing of what a place is.
TOPIC_WORD_LEAST = 3


def window_for(context: Context) -> tuple[date, date]:
    """The days asked about, or for "someday" the weeks the sources are read for."""
    if context.window is not None:
        return context.window
    return context.today, context.today + timedelta(days=happening.HORIZON_DAYS)


def _day(text: str) -> date:
    return date.fromisoformat(text[:10])


def when_text(find: Find) -> str:
    """When it is on, as the family would say it: "Sat 10 Oct 19:30", "Sat 10 to Sun 11 Oct",
    "any time" for a place."""
    if find.starts_at is None:
        return "any time"
    first = _day(find.starts_at)
    said = f"{first:%a} {first.day} {first:%b}"
    if "T" in find.starts_at:
        said += f" {find.starts_at[11:16]}"
    if find.ends_at and _day(find.ends_at) > first:
        last = _day(find.ends_at)
        said = f"{first:%a} {first.day} to {last:%a} {last.day} {last:%b}"
    return said


def _who(find: Find) -> str:
    """Who listed it: the calendar's site, Ticketmaster, or the page the search found."""
    return happening.listed_by(find.kind, find.source, find.url)


def to_web_find(find: Find) -> WebFind:
    summary = " ".join(part for part in (find.venue, find.price_note, find.summary) if part)
    if len(summary) > SUMMARY_MAX:
        summary = summary[: SUMMARY_MAX - 1].rstrip() + "…"
    return WebFind(
        title=find.title,
        url=clean_url(find.url) or "",
        dates=when_text(find),
        summary=summary,
        source=f"listed by {_who(find)}",
        starts=find.starts_at,
        find_id=find.id,
        for_whom=find.participants,
        why=find.why,
        min_age=find.min_age,
        max_age=find.max_age,
        any_time=find.any_time,
    )


def _in_hours(find: Find, context: Context) -> bool:
    """A timed thing starts inside the part of its day asked about (tonight, the rest of today);
    an all-day one, or a day not in the window, is kept."""
    if find.starts_at is None or "T" not in find.starts_at:
        return True
    starts = datetime.fromisoformat(find.starts_at)
    day = context.day(starts.date())
    if day is None:
        return True
    minute = starts.hour * 60 + starts.minute
    return day.bounds[0] <= minute < day.bounds[1]


def anytime(ctx: ToolContext, constraints: Constraints) -> list[Find]:
    """A few places she found to go any time, newest first; about the topic when one was asked."""
    found = finds.anytime(ctx.conn, limit=ANYTIME_READ)
    words = [w for w in constraints.topic.split() if len(w) >= TOPIC_WORD_LEAST]
    if words:
        found = [one for one in found if any(w in _words_of(one) for w in words)]
    return found[:ANYTIME_MOST]


def _words_of(find: Find) -> str:
    parts = (find.title, find.summary, find.category, find.why)
    return " ".join(part for part in parts if part).casefold()


def listed(ctx: ToolContext, context: Context) -> list[Find]:
    """What the sources list for the days asked, soonest first, inside the hours asked."""
    start, end = window_for(context)
    found = finds.upcoming(ctx.conn, start=start, end=end, limit=MAX_LISTED * 4)
    return [find for find in found if _in_hours(find, context)]


def merge_finds(found: list[WebFind]) -> tuple[list[WebFind], int]:
    """The finds in the order given, one of each page, up to MAX_LISTED. Returns them and how
    many were left out."""
    merged: list[WebFind] = []
    seen: set[str] = set()
    left = 0
    for one in found:
        if one.url and one.url.lower() in seen:
            continue
        if len(merged) >= MAX_LISTED:
            left += 1
            continue
        if one.url:
            seen.add(one.url.lower())
        merged.append(one)
    return merged, left
