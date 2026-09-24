"""Data shapes shared by the suggestion stages, the `suggest` tool and the suggestions log."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from familydb.integrations.open_meteo import DayForecast
from familydb.store.ideas import Idea

Verdict = Literal["good", "possible", "ruled_out"]
CostLevel = Literal[0, 1, 2, 3, 4]
WindowKind = Literal["now", "today", "this_weekend", "next_weekend", "dates", "someday"]


class SuggestInput(BaseModel):
    idea_ids: list[int] = Field(
        default_factory=list,
        description="Relevant saved idea IDs for this topic; empty considers all ideas.",
    )
    window: WindowKind = Field(
        description=(
            "now (the next few hours), today (the rest of it), this_weekend, next_weekend, "
            "dates (give start and end), or someday."
        )
    )
    start: str | None = Field(default=None, description="YYYY-MM-DD, for window=dates.")
    end: str | None = Field(default=None, description="YYYY-MM-DD, for window=dates.")
    hours: int | None = Field(default=None, description="For window=now: hours ahead, 1-12; 4.")
    from_time: str | None = Field(
        default=None, description="HH:MM each day starts, e.g. 17:00 for tonight."
    )
    until_time: str | None = Field(default=None, description="HH:MM each day ends.")
    participants: list[str] = Field(
        default_factory=list, description="Who is coming, as said: ['with the girls'], ['adults']."
    )
    max_cost_level: CostLevel | None = Field(default=None, description="Cheap = 1, free = 0.")
    setting: Literal["indoor", "outdoor"] | None = Field(
        default=None, description="Only when the question insists, e.g. a rainy day."
    )
    max_travel_minutes: int | None = None
    max_duration_minutes: int | None = None
    near: str = Field(
        default="",
        description=(
            "Where they are, only if said: 'downtown Portland', 'the Pearl'; 'here' for the "
            "location they shared. Empty: from home."
        ),
    )
    topic: str = Field(
        default="",
        description="What kind of thing, a few words: live jazz, puppet show. Empty for anything.",
    )
    discover: bool = Field(default=True, description="Also look for time-bound events on the web.")
    question: str = Field(description="The family's question, verbatim.")


class Checks(BaseModel):
    open: Literal["open", "closed", "unknown"] = "unknown"
    hours: str | None = None
    stale: bool = False
    travel_minutes: int | None = None
    travel_fits: bool | None = None
    booking: Literal["not_needed", "ok", "too_late", "unknown"] = "not_needed"
    booking_url: str | None = None
    weather: Literal["ok", "poor", "unknown"] = "unknown"


class Candidate(BaseModel):
    idea_id: int
    title: str
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    fits_days: list[str] = Field(default_factory=list)
    checks: Checks = Field(default_factory=Checks)


class WebFind(BaseModel):
    title: str
    url: str
    dates: str | None = None
    summary: str = ""
    source: str | None = None


class DaySummary(BaseModel):
    date: str
    weekday: str
    free: list[str]  # free stretches within the window, "HH:MM-HH:MM"
    free_known: bool
    commitments: list[str] = Field(default_factory=list)
    forecast: str | None = None
    rain_chance_pct: int | None = None
    high: float | None = None
    low: float | None = None


class Window(BaseModel):
    start: str | None
    end: str | None
    label: str


class SuggestResult(BaseModel):
    window: Window
    travel_from: str = "home"  # where the travel estimates start
    days: list[DaySummary]
    candidates: list[Candidate]
    web_finds: list[WebFind]
    skipped_checks: list[str]
    not_shown: int = 0  # further ideas ranked below the ones listed
    suggestion: dict[str, int] | None = None


@dataclass
class Constraints:
    idea_ids: list[int] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    max_cost_level: int | None = None
    setting: str | None = None
    max_travel_minutes: int | None = None
    max_duration_minutes: int | None = None
    topic: str = ""  # what the family asked for, for discovery only


# Minutes after midnight. Without a time given, a day is counted from 08:00 to 22:00.
DAY_START = 8 * 60
DAY_END = 22 * 60


def clock(minutes: int) -> str:
    """Minutes after midnight as HH:MM, midnight at the end of a day as 24:00."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}" if minutes < 24 * 60 else "24:00"


@dataclass(frozen=True)
class DayBounds:
    """The part of each day the question is about, and where the first and last days are cut.

    `first_start` is later than `start` when the window begins today and the morning has gone,
    or when the question is about right now; `last_end` cuts the last day for "the next hours".
    """

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
        """Nothing on in the part of the day asked about."""
        return self.longest >= self.bounds[1] - self.bounds[0] > 0


@dataclass(frozen=True)
class Origin:
    """Where travel is estimated from when the family is not at home."""

    lat: float
    lon: float
    label: str  # how each reason names it: "Sam's shared location", "the Pearl"
    detail: str  # how the result names it, with how old a shared location is
    shared: bool = False  # from a location shared on Telegram, which no model is given


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


@dataclass
class Shortlisted:
    idea: Idea
    fits_days: list[date]
    weather: Literal["ok", "poor", "unknown"]
