"""Time source abstraction: tests pin the clock, and the family timezone is always explicit."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

_NORTHERN_SEASONS = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}
_OPPOSITE = {"winter": "summer", "summer": "winter", "spring": "autumn", "autumn": "spring"}


def season_for(day: date, *, southern: bool = False) -> str:
    """Meteorological season for a date, by hemisphere."""
    season = _NORTHERN_SEASONS[day.month]
    return _OPPOSITE[season] if southern else season


class Clock:
    """Base clock. `now()` returns an aware datetime in the family timezone."""

    def __init__(self, tz: ZoneInfo, *, southern: bool = False) -> None:
        self.tz = tz
        self.southern = southern

    def now(self) -> datetime:
        raise NotImplementedError

    def today(self) -> date:
        return self.now().date()

    def utcnow(self) -> datetime:
        return self.now().astimezone(UTC)

    def season(self) -> str:
        return season_for(self.today(), southern=self.southern)

    def describe(self) -> str:
        """One line for the prompt, e.g. 'Sunday 20 September 2026, 14:03 (UTC), autumn'."""
        now = self.now()
        return f"{now:%A} {now.day} {now:%B %Y}, {now:%H:%M} ({self.tz.key}), {self.season()}"


class SystemClock(Clock):
    """The real wall clock in the family timezone."""

    def now(self) -> datetime:
        return datetime.now(self.tz)


class FixedClock(Clock):
    """A clock pinned to one instant: the tests' and the evals' clock, and a message's own
    arrival time when its turn is written (pipeline.py). `advance` moves it."""

    def __init__(self, at: datetime, tz: ZoneInfo, *, southern: bool = False) -> None:
        super().__init__(tz, southern=southern)
        self._at = at.replace(tzinfo=tz) if at.tzinfo is None else at.astimezone(tz)

    def now(self) -> datetime:
        return self._at

    def advance(self, delta: timedelta) -> None:
        self._at = self._at + delta
