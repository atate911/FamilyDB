"""Suggestion tools: `suggest` for the chat model, `report_finds` for the discovery worker."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from familydb.suggest.types import SuggestInput
from familydb.tools.registry import ToolContext, tool
from familydb.tools.urls import clean_url

MAX_FINDS = 6


class Find(BaseModel):
    title: str
    url: str = Field(description="The page you saw, exactly as given.")
    dates: str | None = Field(default=None, description="Dates or times as written on the page.")
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
        if url is None:
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
            }
        )
        recorded += 1
    return {"recorded": recorded, "rejected": rejected, "total": len(finds)}


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

    return run(ctx, args).model_dump(mode="json")
