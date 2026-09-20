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
WindowKind = Literal["this_weekend", "next_weekend", "dates", "someday"]


class SuggestInput(BaseModel):
    window: WindowKind = Field(
        description="this_weekend, next_weekend, dates (give start and end), or someday."
    )
    start: str | None = Field(default=None, description="YYYY-MM-DD, for window=dates.")
    end: str | None = Field(default=None, description="YYYY-MM-DD, for window=dates.")
    participants: list[str] = Field(
        default_factory=list, description="Who is coming, as said: ['with the girls'], ['adults']."
    )
    max_cost_level: CostLevel | None = Field(default=None, description="Cheap = 1, free = 0.")
    setting: Literal["indoor", "outdoor"] | None = Field(
        default=None, description="Only when the question insists, e.g. a rainy day."
    )
    max_travel_minutes: int | None = None
    max_duration_minutes: int | None = None
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
    free: list[str]
    free_known: bool
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
    days: list[DaySummary]
    candidates: list[Candidate]
    web_finds: list[WebFind]
    skipped_checks: list[str]
    suggestion: dict[str, int] | None = None


@dataclass
class Constraints:
    participants: list[str] = field(default_factory=list)
    max_cost_level: int | None = None
    setting: str | None = None
    max_travel_minutes: int | None = None
    max_duration_minutes: int | None = None


@dataclass
class DayContext:
    date: date
    free: list[str]
    free_known: bool
    forecast: DayForecast | None


@dataclass
class Context:
    window: tuple[date, date] | None
    days: list[DayContext]
    season: str
    today: date
    skipped: list[str] = field(default_factory=list)

    def day(self, when: date) -> DayContext | None:
        return next((d for d in self.days if d.date == when), None)


@dataclass
class Shortlisted:
    idea: Idea
    fits_days: list[date]
    weather: Literal["ok", "poor", "unknown"]
