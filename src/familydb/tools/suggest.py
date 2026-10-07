"""Suggestion tools: `suggest` for the chat model, `report_finds` for the discovery worker and
the weekly search near home, and `report_feeds` for the lookup that finds calendars near home."""

from __future__ import annotations

from datetime import date, time
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from familydb.errors import ToolError
from familydb.suggest.types import SuggestInput
from familydb.tools.registry import ToolContext, tool
from familydb.tools.urls import clean_url

MAX_FINDS = 6
MAX_FEEDS = 10
MAX_FIELD = 200


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
    # For a place (the places worker): what it is, and where and when, as the page writes them.
    kind: str | None = Field(default=None, description="For a place: restaurant, park, ...")
    hours: str | None = Field(default=None, description="For a place: opening hours as written.")
    address: str | None = Field(default=None, description="For a place: its street address.")


class ReportFindsInput(BaseModel):
    finds: list[Find] = Field(
        default_factory=list, description="Up to 6 finds; empty when nothing fits the window."
    )


@tool(
    name="report_finds",
    description=(
        "Used by the discovery and places workers to hand back what they found on the web. "
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
        finds.append(
            {
                "title": find.title.strip(),
                "url": url,
                "dates": find.dates.strip() if find.dates else None,
                "summary": find.summary.strip(),
                "source": urlsplit(url).hostname,
                **{
                    key: value.strip()[:MAX_FIELD]
                    for key, value in (
                        ("kind", find.kind),
                        ("hours", find.hours),
                        ("address", find.address),
                    )
                    if value and value.strip()
                },
                **({"starts": starts} if starts else {}),
            }
        )
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


class PickInput(BaseModel):
    ref: str = Field(description="The option's reference exactly as listed: 'idea:12', 'find:2'.")
    slot: Literal["favorite", "new", "wildcard"]
    reason: str = Field(description="Under 200 characters, resting on something in the dossier.")
    day: str | None = Field(default=None, description="YYYY-MM-DD, when the day matters.")
    cites: list[str] = Field(
        default_factory=list, description="What the reason rests on: 'm3', 'o5', 'p7', 'idea:12'."
    )


class GivePicksInput(BaseModel):
    picks: list[PickInput] = Field(description="1 to 5 picks, the best first.")
    framing: str | None = Field(
        default=None, description="One line the picks share, under 200 characters, or none."
    )


MOST_PICKS = 5
MOST_WORDS = 200


@tool(
    name="give_picks",
    description=(
        "Used by the call that chooses what to suggest to hand back its picks, each one of the "
        "listed options. Not for chat."
    ),
    worker_only=True,
)
def give_picks(ctx: ToolContext, args: GivePicksInput) -> dict[str, Any]:
    """Every check code can make of a choice (suggest/choosing.py): the option exists and was not
    picked twice, a favorite was done before and a new one never was, the day is one it fits,
    the reason is short and what it cites is in the dossier. A pick that fails is refused, with
    what would do, so the call can put it right in its one more step."""
    options = ctx.scratch.get("options", {})
    known = ctx.scratch.get("cites", frozenset())
    window = ctx.scratch.get("window")
    if not args.picks or len(args.picks) > MOST_PICKS:
        raise ToolError(f"give 1 to {MOST_PICKS} picks")
    chosen: list[dict[str, Any]] = []
    for pick in args.picks:
        option = options.get(pick.ref)
        if option is None:
            raise ToolError(f"{pick.ref!r} is not one of the options: {sorted(options)}")
        if any(earlier["ref"] == pick.ref for earlier in chosen):
            raise ToolError(f"{pick.ref} is picked twice")
        if pick.slot == "favorite" and not option.done_before:
            raise ToolError(f"{pick.ref} has not been done before, so it is not a favorite")
        if pick.slot == "new" and option.done_before:
            raise ToolError(f"{pick.ref} has been done before, so it is not new")
        reason = " ".join(pick.reason.split())
        if not reason or len(reason) > MOST_WORDS:
            raise ToolError(f"the reason for {pick.ref} must be 1 to {MOST_WORDS} characters")
        unknown = sorted(set(pick.cites) - set(known))
        if unknown:
            raise ToolError(f"{pick.ref} cites {unknown}, which are not in the dossier")
        day = _pick_day(pick, option, window)
        chosen.append(
            {"ref": pick.ref, "slot": pick.slot, "reason": reason, "day": day, "cites": pick.cites}
        )
    framing = " ".join((args.framing or "").split()) or None
    if framing and len(framing) > MOST_WORDS:
        raise ToolError(f"the framing must be at most {MOST_WORDS} characters")
    ctx.scratch["chosen"] = {"picks": chosen, "framing": framing}
    return {"picked": len(chosen)}


def _pick_day(pick: PickInput, option: Any, window: tuple[date, date] | None) -> str | None:
    if not pick.day:
        return None
    try:
        day = date.fromisoformat(pick.day.strip())
    except ValueError:
        raise ToolError(f"the day for {pick.ref} must be YYYY-MM-DD") from None
    if window is not None and not window[0] <= day <= window[1]:
        raise ToolError(f"{day} is outside the days asked about, {window[0]} to {window[1]}")
    if option.days and day.isoformat() not in option.days:
        raise ToolError(f"{pick.ref} fits {', '.join(option.days)}, not {day}")
    return day.isoformat()


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
    from familydb.suggest import choosing
    from familydb.suggest.engine import assess, result_of

    # For a planning question a stronger call chooses (suggest/choosing.py); otherwise, and
    # whenever it cannot, the engine's own order.
    assessed = assess(ctx, args)
    chosen = None if choosing.reason_not_to(ctx, args) else choosing.choose(ctx, args, assessed)
    # Uncached and resent with the reply: leaving nulls out roughly halves it.
    return result_of(assessed, chosen).model_dump(mode="json", exclude_none=True)
