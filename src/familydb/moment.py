"""A moment the family is asking about: the days and the part of each day, the free time and
weather in them, where travel starts, and the limits that hold (who is coming, cost, setting,
drive, the firm rules). The suggestion engine frames a question as one (suggest/context.py,
suggest/rules.py) and the scouting layer reads it to search for it (familydb/scouting), so it
lives here, below both. Time is minutes after midnight."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from familydb.integrations.open_meteo import DayForecast

CostLevel = Literal[0, 1, 2, 3, 4]


@dataclass
class Constraints:
    idea_ids: list[int] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    max_cost_level: int | None = None
    setting: str | None = None
    max_travel_minutes: int | None = None
    max_duration_minutes: int | None = None
    topic: str = ""  # what the family asked for, for discovery only
    avoid: list[str] = field(default_factory=list)  # idea tags a firm rule leaves out
    # The family's taste, said outright (suggest/rules.py): rain lowers nothing, and how many
    # days a done idea rests, by kind ("*" for every kind).
    rain_ok: bool = False
    rest: dict[str, int] = field(default_factory=dict)
    # The memory behind each limit a firm rule set (suggest/rules.py), by the limit's name, or
    # "avoid:<tag>": {"max_travel_minutes": 4}.
    held_by: dict[str, int] = field(default_factory=dict)

    def because(self, name: str) -> str | None:
        """'m4' when memory 4 set this limit, for a reason to name it."""
        memory = self.held_by.get(name)
        return f"m{memory}" if memory is not None else None


# Minutes after midnight. Without a time given, a day is counted from 08:00 to 22:00.
DAY_START = 8 * 60
DAY_END = 22 * 60


def clock(minutes: int) -> str:
    """Minutes after midnight as HH:MM, midnight at the end of a day as 24:00."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}" if minutes < 24 * 60 else "24:00"


@dataclass(frozen=True)
class DayBounds:
    """The part of each day asked about; `first_start` cuts the first day (today, or "now") and
    `last_end` the last ("the next hours")."""

    start: int = DAY_START
    end: int = DAY_END
    first_start: int | None = None
    last_end: int | None = None

    def for_day(self, day: date, first: date, last: date) -> tuple[int, int]:
        start = max(self.start, self.first_start or 0) if day == first else self.start
        end = min(self.end, self.last_end) if day == last and self.last_end else self.end
        return start, max(start, end)


@dataclass
class DayContext:
    date: date
    spans: list[tuple[int, int]]  # free stretches within `bounds`, in minutes after midnight
    free_known: bool
    forecast: DayForecast | None
    commitments: list[str] = field(default_factory=list)
    bounds: tuple[int, int] = (DAY_START, DAY_END)

    @property
    def longest(self) -> int:
        return max((b - a for a, b in self.spans), default=0)

    @property
    def whole(self) -> bool:

        return self.longest >= self.bounds[1] - self.bounds[0] > 0


@dataclass(frozen=True)
class Origin:
    """Where travel is estimated from when not at home."""

    lat: float
    lon: float
    label: str  # how each reason names it: "Sam's shared location", "the Pearl"
    detail: str  # how the result names it, with how old a shared location is
    shared: bool = False  # from a location the phone sent, rather than a place named in words


@dataclass
class Context:
    window: tuple[date, date] | None
    days: list[DayContext]
    season: str
    today: date
    skipped: list[str] = field(default_factory=list)
    origin: Origin | None = None  # None: from home

    def day(self, when: date) -> DayContext | None:
        return next((d for d in self.days if d.date == when), None)
