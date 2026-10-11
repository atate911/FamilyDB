"""Data shapes shared by the suggestion stages, the `suggest` tool and the log. The shapes of a
moment (the days, the hours, who is coming, from where, the limits) live in familydb/moment.py,
below the engine, so the scouting layer can read them too; they are named here as well."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.moment import (
    DAY_END,
    DAY_START,
    Constraints,
    Context,
    CostLevel,
    DayBounds,
    DayContext,
    Origin,
    clock,
)
from familydb.scouting.types import Found
from familydb.store.ideas import Idea

Verdict = Literal["good", "possible", "ruled_out"]
# What a pick is for (suggest/choosing.py): one they know and love, one new to them, one
# further out.
Slot = Literal["favorite", "new", "wildcard"]
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
    discover: bool = Field(
        default=True, description="Also search the web; false only for their own list alone."
    )
    prefer: Literal["new", "favorites"] = Field(
        default="new", description="favorites for what they loved before: 'our usual'."
    )
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
    resting: bool = False  # done or planned lately (suggest/shortlist.py), said first


class Candidate(BaseModel):
    idea_id: int
    title: str
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    fits_days: list[str] = Field(default_factory=list)
    checks: Checks = Field(default_factory=Checks)


class WebFind(Found):
    """Something found outside the list, as the engine offers it (scouting/types.Found)."""


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


class Pick(BaseModel):
    """One of the stronger call's picks, as the chat model is given it to word."""

    ref: str  # "idea:12", or "find:2" for the second web find
    title: str
    slot: Slot
    reason: str
    day: str | None = None  # YYYY-MM-DD, when it chose one
    idea_id: int | None = None
    url: str | None = None
    find_id: int | None = None  # the stored find, so her picks on Now can lead to it


@dataclass
class Chosen:
    picks: list[Pick]
    framing: str | None = None
    # When the stronger call corrected the question's framing (suggest/choosing.py): the
    # engine's assessment of the corrected question, and why, in its words.
    reframed: Any = None
    why: str | None = None


class SuggestResult(BaseModel):
    window: Window
    travel_from: str = "home"  # where the travel estimates start
    days: list[DaySummary]
    candidates: list[Candidate]
    web_finds: list[WebFind]
    skipped_checks: list[str]
    not_shown: int = 0  # further ideas ranked below the ones listed
    suggestion: dict[str, int] | None = None
    # What a stronger call chose, in order, when one did (suggest/choosing.py); None otherwise, so
    # a result nobody chose for is what it always was.
    picks: list[Pick] | None = None
    framing: str | None = None
    # Why the question was checked in other terms than first framed, when the stronger call
    # corrected it: the reply should say what was looked at.
    reframed: str | None = None


@dataclass
class Shortlisted:
    idea: Idea
    fits_days: list[date]
    weather: Literal["ok", "poor", "unknown"]
    # Said first and making it possible at best, a matter of taste rather than a fact: done
    # lately, disappointing visits, rain or cold, a long day out with something else on the day.
    caveats: list[str] = field(default_factory=list)
    # Done or planned lately and resting (shortlist.rest_days): it comes last among the possible,
    # and her picks made ahead leave it out (familydb/picks.py).
    resting: bool = False
    # Said after the caveats and lowering nothing: rain the family said is fine.
    notes: list[str] = field(default_factory=list)


# What this module offers, the moment's shapes among them (familydb/moment.py).
__all__ = [
    "DAY_END",
    "DAY_START",
    "Candidate",
    "Checks",
    "Chosen",
    "Constraints",
    "Context",
    "CostLevel",
    "DayBounds",
    "DayContext",
    "DaySummary",
    "Origin",
    "Pick",
    "Shortlisted",
    "Slot",
    "SuggestInput",
    "SuggestResult",
    "Verdict",
    "WebFind",
    "Window",
    "WindowKind",
    "clock",
]
