"""Stage: what the family's sources list near home for the days asked (jobs/happening.py), read
from the `finds` table, with no model and no network.

Listed only, for now: each is offered as a web find is, with when it is on and who listed it,
for the model to name as not on the list. They are not yet checked against the free time,
the forecast or the travel as saved ideas are (shortlist, evaluate); that is the next step, and
this is where it goes in. What is said of each is code's: the day and time in the family's
words, and the name of the calendar, Ticketmaster, or the site the weekly search read.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from familydb import happening
from familydb.base.urls import clean_url
from familydb.store import finds
from familydb.store.finds import Find
from familydb.suggest.types import Context, WebFind
from familydb.tools import ToolContext

# The most offered with one answer, the discovery worker's own finds among them: the result is
# sent to the model and sent again with its reply.
MAX_LISTED = 8
SUMMARY_MAX = 100
# A window that is already this well covered by what the sources list asks the web nothing
# more, unless the question is about something in particular.
COVERED = 3


def window_for(context: Context) -> tuple[date, date]:
    """The days asked about, or for "someday" the weeks the sources are read for."""
    if context.window is not None:
        return context.window
    return context.today, context.today + timedelta(days=happening.HORIZON_DAYS)


def _day(text: str) -> date:
    return date.fromisoformat(text[:10])


def when_text(find: Find) -> str:
    """When it is on, as the family would say it: "Sat 10 Oct 19:30", "Sat 10 to Sun 11 Oct"."""
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
    if find.kind == happening.WEB and find.url:
        return happening.host(find.url)
    return happening.source_name(find.source)


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
    )


def _in_hours(find: Find, context: Context) -> bool:
    """A timed thing starts inside the part of its day asked about (tonight, the rest of today);
    an all-day one, or a day not in the window, is kept."""
    if "T" not in find.starts_at:
        return True
    starts = datetime.fromisoformat(find.starts_at)
    day = context.day(starts.date())
    if day is None:
        return True
    minute = starts.hour * 60 + starts.minute
    return day.bounds[0] <= minute < day.bounds[1]


def listed(ctx: ToolContext, context: Context) -> list[Find]:
    """What the sources list for the days asked, soonest first, inside the hours asked."""
    start, end = window_for(context)
    found = finds.upcoming(ctx.conn, start=start, end=end, limit=MAX_LISTED * 4)
    return [find for find in found if _in_hours(find, context)]


def merge_finds(stored: list[Find], searched: list[WebFind]) -> tuple[list[WebFind], int]:
    """The discovery worker's finds first (asked for this question), then what the sources
    list, one of each page, up to MAX_LISTED. Returns them and how many were left out."""
    merged = list(searched[:MAX_LISTED])
    seen = {find.url.lower() for find in merged}
    left = 0
    for one in stored:
        shown = to_web_find(one)
        if shown.url and shown.url.lower() in seen:
            continue
        if len(merged) >= MAX_LISTED:
            left += 1
            continue
        if shown.url:
            seen.add(shown.url.lower())
        merged.append(shown)
    return merged, left
