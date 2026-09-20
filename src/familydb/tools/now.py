"""The current date and time, for long conversations where the context line has gone stale."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from familydb.dates import weekend_window
from familydb.tools.registry import ToolContext, tool


class NowInput(BaseModel):
    pass


@tool(
    name="now",
    description=(
        "The current date, weekday, time, timezone and season, plus the dates of the coming "
        "weekend. The same information is at the top of the latest message; call this only if "
        "the conversation has gone on for a while."
    ),
)
def now(ctx: ToolContext, _args: NowInput) -> dict[str, Any]:
    moment = ctx.clock.now()
    start, end = weekend_window(moment.date())
    return {
        "date": moment.date().isoformat(),
        "weekday": moment.strftime("%A"),
        "time": moment.strftime("%H:%M"),
        "timezone": ctx.clock.tz.key,
        "utc_offset": moment.strftime("%z"),
        "season": ctx.clock.season(),
        "weekend": {"start": start.isoformat(), "end": end.isoformat()},
    }
