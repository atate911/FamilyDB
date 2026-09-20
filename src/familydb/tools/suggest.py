"""Suggestion tools: the discovery worker's hand-back now; the `suggest` tool joins in step 5."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from familydb.tools.registry import ToolContext, tool

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


def _clean_url(url: str) -> str | None:
    value = url.strip()
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return value


@tool(
    name="report_finds",
    description=(
        "Used by the discovery worker to hand back time-bound options found on the web. "
        "Not for chat."
    ),
)
def report_finds(ctx: ToolContext, args: ReportFindsInput) -> dict[str, Any]:
    finds: list[dict[str, Any]] = ctx.scratch.setdefault("finds", [])
    seen = {f["url"].lower() for f in finds}
    recorded = 0
    rejected = 0
    for find in args.finds:
        url = _clean_url(find.url)
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
