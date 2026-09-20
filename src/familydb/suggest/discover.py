"""Stage: time-bound things on the web. Built out in the next step; for now it reports why not."""

from __future__ import annotations

from familydb.availability import web_tools_available
from familydb.suggest.types import Context, WebFind
from familydb.tools import ToolContext


def discover(ctx: ToolContext, context: Context, question: str) -> tuple[list[WebFind], str | None]:
    if not web_tools_available(ctx.settings):
        return [], "web discovery off"
    return [], "web discovery not available yet"
