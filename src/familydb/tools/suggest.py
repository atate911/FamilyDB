"""Suggestion tools: `suggest` for the chat model, `report_finds` for the discovery worker and
the weekly search near home, and `report_feeds` for the lookup that finds calendars near home."""

from __future__ import annotations

from datetime import date, time
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from familydb.suggest.types import SuggestInput
from familydb.tools.registry import ToolContext, tool
from familydb.tools.urls import clean_url

MAX_FINDS = 6
MAX_FEEDS = 10


class Find(BaseModel):
    title: str
    url: str = Field(description="The page you saw, exactly as given.")
    dates: str | None = Field(default=None, description="Dates or times as written on the page.")
    starts_on: str | None = Field(
        default=None, description="YYYY-MM-DD, the first day it is on, when the page says."
    )
    starts_time: str | None = Field(
        default=None, description="HH:MM, 24-hour, when it starts, when the page says."
    )
    summary: str = Field(description="One line.")


class ReportFindsInput(BaseModel):
    finds: list[Find] = Field(
        default_factory=list, description="Up to 6 finds; empty when nothing fits the window."
    )


@tool(
    name="report_finds",
    description=(
        "Used by the discovery worker to hand back time-bound options found on the web. "
        "Not for chat."
    ),
    worker_only=True,
)
def report_finds(ctx: ToolContext, args: ReportFindsInput) -> dict[str, Any]:
    finds: list[dict[str, Any]] = ctx.scratch.setdefault("finds", [])
    seen = {f["url"].lower() for f in finds}
    recorded = 0
    rejected = 0
    for find in args.finds:
        url = clean_url(find.url)
        starts = _starts(find)
        if url is None or starts is False:
            rejected += 1
            continue
        if url.lower() in seen or len(finds) >= MAX_FINDS:
            continue
        seen.add(url.lower())
        kept: dict[str, Any] = {
            "title": find.title.strip(),
            "url": url,
            "dates": find.dates.strip() if find.dates else None,
            "summary": find.summary.strip(),
            "source": urlsplit(url).hostname,
        }
        if starts:
            kept["starts"] = starts
        finds.append(kept)
        recorded += 1
    return {"recorded": recorded, "rejected": rejected, "total": len(finds)}


def _starts(find: Find) -> str | bool | None:
    """When it starts as code can read it, "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"; None when the
    page did not say; False when what was said is no day or time at all, which refuses the find
    rather than storing a guess."""
    if not find.starts_on:
        return False if find.starts_time else None
    try:
        day = date.fromisoformat(find.starts_on.strip())
    except ValueError:
        return False
    if not find.starts_time:
        return day.isoformat()
    text = find.starts_time.strip()
    try:
        at = time.fromisoformat(text)
    except ValueError:
        return False
    if len(text) != 5 or at.second or at.microsecond:
        return False
    return f"{day.isoformat()}T{at:%H:%M}"


class Feed(BaseModel):
    title: str = Field(description="Whose calendar it is: 'Fort Vancouver Regional Library'.")
    url: str = Field(
        description="The calendar's iCal or .ics address, exactly as the page gives it."
    )
    why: str = Field(description="One line: what is on it.")


class ReportFeedsInput(BaseModel):
    feeds: list[Feed] = Field(
        default_factory=list, description="Up to 10 calendars; empty when none was found."
    )


@tool(
    name="report_feeds",
    description=(
        "Used by the lookup that finds event calendars near home to hand back the iCal "
        "addresses it found. Not for chat."
    ),
    worker_only=True,
)
def report_feeds(ctx: ToolContext, args: ReportFeedsInput) -> dict[str, Any]:
    feeds: list[dict[str, Any]] = ctx.scratch.setdefault("feeds", [])
    seen = {f["url"].lower() for f in feeds}
    recorded = rejected = 0
    for feed in args.feeds:
        url = clean_url(feed.url.strip().replace("webcal://", "https://", 1))
        if url is None:
            rejected += 1
            continue
        if url.lower() in seen or len(feeds) >= MAX_FEEDS:
            continue
        seen.add(url.lower())
        feeds.append({"title": feed.title.strip(), "url": url, "why": feed.why.strip()})
        recorded += 1
    return {"recorded": recorded, "rejected": rejected, "total": len(feeds)}


@tool(
    name="suggest",
    description=(
        "Checked suggestions for a window: looks at the calendar's free time, the forecast, every "
        "idea on the list and the cached place details, and returns candidates with a verdict "
        "(good, possible, ruled_out) and the reasons, plus time-bound web finds when discovery "
        "is on. Call it once for 'what should we do' questions, then write the reply from it."
    ),
)
def suggest(ctx: ToolContext, args: SuggestInput) -> dict[str, Any]:
    from familydb.suggest.engine import run

    # Nulls carry no information here and this result is not cached: it is sent to the model,
    # then sent again with the reply. Leaving them out roughly halves it.
    return run(ctx, args).model_dump(mode="json", exclude_none=True)
