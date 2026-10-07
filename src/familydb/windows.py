"""A task's preferred window, read in code as days of the week and parts of the day.

"One of these Saturday mornings" is kept as said (`tasks.preferred_window`); so it can be nudged
when one comes round (jobs/nudges.py) its words are read against a short list: days, weekend,
weekdays, morning, afternoon, evening. Any other word ("before Christmas", "after school", "next
Saturday") means not read at all, so a nudge never comes at a time the family did not mean and
the task stays as it was.

Two more are read whole. Free time ("next time I have some free time", "whenever we get a
chance") is any day the calendar has two hours free (`FREE_TIME`). "This weekend" and "sometime
this week" end on that week's Sunday, worked out from the day they were said and kept with the
task (`until`, `tasks.window_until`); past it, or with no day to count from, they are not read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAYS = frozenset(range(5))
WEEKEND = frozenset({5, 6})
EVERY_DAY = frozenset(range(7))

# Parts of a day in minutes after midnight, family clock; "day" is a day named with no part. A nudge
# goes from an hour into the part to an hour before its end (`LEAD`), never at eight on a Saturday
# morning or late in the evening.
PARTS: dict[str, tuple[int, int]] = {
    "morning": (8 * 60, 12 * 60),
    "afternoon": (12 * 60, 17 * 60),
    "evening": (17 * 60, 22 * 60),
    "day": (8 * 60, 22 * 60),
}
LEAD = 60

_DAY_WORDS: dict[str, frozenset[int]] = {
    **{name.lower(): frozenset({n}) for n, name in enumerate(DAYS)},
    **{name.lower() + "s": frozenset({n}) for n, name in enumerate(DAYS)},
    "weekend": WEEKEND,
    "weekends": WEEKEND,
    "weekday": WEEKDAYS,
    "weekdays": WEEKDAYS,
}
_PART_WORDS = {
    "morning": "morning",
    "mornings": "morning",
    "afternoon": "afternoon",
    "afternoons": "afternoon",
    "evening": "evening",
    "evenings": "evening",
    "night": "evening",
    "nights": "evening",
}
_BOTH = {"weeknight": (WEEKDAYS, "evening"), "weeknights": (WEEKDAYS, "evening")}
# Said whole, nothing else with it.
FREE_TIME = re.compile(
    r"(?:(?:the )?next time|whenever|when) (?:i|we) (?:have|get|find|have got|'ve got) "
    r"(?:(?:some|a bit of|a little|any) )?(?:(?:free|spare) )?(?:time|a (?:chance|minute|moment))"
    r"|(?:(?:the )?next time|whenever|when) (?:i'm|i am|we're|we are) free"
    r"|(?:(?:some|a bit of|a little|any) )?(?:free|spare) time"
    r"|(?:in|during) (?:my|our) (?:free|spare) time"
)
FREE_TIME_MINUTES = 120
THIS = re.compile(r"\bthis (weekend|week)\b")
_FILLER = frozenset(
    {"a", "an", "and", "any", "of", "one", "or", "some", "the", "these", "those"}
    | {"at", "day", "days", "during", "in", "on", "over", "sometime", "time", "week"}
    | {"free", "quiet", "spare"}
)


@dataclass(frozen=True)
class Window:
    days: frozenset[int]
    parts: tuple[str, ...]
    # The last day it holds ("this weekend"); None for every week.
    until: date | None = None
    # How long the calendar must be free for it to come up.
    min_free: int = LEAD

    def open_at(self, moment: datetime) -> str | None:
        if moment.weekday() not in self.days:
            return None
        if self.until is not None and moment.date() > self.until:
            return None
        minute = moment.hour * 60 + moment.minute
        for part in self.parts:
            start, end = PARTS[part]
            if start + LEAD <= minute <= end - LEAD:
                return part
        return None

    def words(self, before: str = "") -> str:
        """The window as the page and the model say it ("a Saturday morning", "a weekend day");
        `before` goes after the article ("a free evening").
        """
        if self.min_free > LEAD:
            return f"a day with {_hours(self.min_free)} free"
        days = self.days
        if days == EVERY_DAY:
            named = ""
        elif days == WEEKEND:
            named = "weekend"
        elif days == WEEKDAYS:
            named = "weekday"
        else:
            named = " or ".join(DAYS[n] for n in sorted(days))
        parts = " or ".join(part for part in self.parts if part != "day")
        if parts:
            said = f"{named} {parts}".strip()
        else:
            said = "weekend day" if days == WEEKEND else named or "day"
        said = f"{before} {said}".strip()
        if self.until is not None:  # "a free weekend day by Sun 27 Sep"
            said += f" by {DAYS[self.until.weekday()][:3]} {self.until.day} {self.until:%b}"
        return f"{'an' if said[0].lower() in 'aeiou' else 'a'} {said}"

    def now_words(self, moment: datetime, part: str) -> str:
        day = DAYS[moment.weekday()]
        if self.min_free > LEAD:
            hour = moment.hour
            now = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
            return f"{day} {now}, with {_hours(self.min_free)} free"
        return day if part == "day" else f"{day} {part}"


def _hours(minutes: int) -> str:
    return {120: "two hours", 180: "three hours"}.get(minutes, f"{minutes} minutes")


def until(text: str, said_on: date) -> date | None:
    """The last day "this weekend" or "this week" in a window means, said on `said_on`: that
    week's Sunday. None when it names neither."""
    if THIS.search(_plain(text)) is None:
        return None
    return said_on + timedelta(days=6 - said_on.weekday())


def _plain(text: str) -> str:
    folded = text.lower().replace("\u2019", "'")
    return " ".join(re.sub(r"[^a-z' ]+", " ", folded).split())


def read(text: str, *, until: date | None = None, today: date | None = None) -> Window | None:
    """The window in these words, or None when any word is unknown or none says when. `until`
    is the day "this weekend" or "this week" ends, kept from when it was said; with none, or
    `today` past it, those are not read."""
    plain = _plain(text)
    if FREE_TIME.fullmatch(plain):
        return Window(EVERY_DAY, ("day",), min_free=FREE_TIME_MINUTES)
    this = THIS.search(plain)
    if this is not None:
        if until is None or (today is not None and today > until):
            return None
        rest = " weekend " if this.group(1) == "weekend" else " "
        plain = plain[: this.start()] + rest + plain[this.end() :]
    words = re.sub(r"'s\b", "", plain)
    days: set[int] = set()
    parts: set[str] = set()
    for word in re.split(r"[^a-z]+", words):
        if not word or word in _FILLER:
            continue
        if word in _DAY_WORDS:
            days |= _DAY_WORDS[word]
        elif word in _PART_WORDS:
            parts.add(_PART_WORDS[word])
        elif word in _BOTH:
            both_days, part = _BOTH[word]
            days |= both_days
            parts.add(part)
        else:
            return None
    if re.search(r"\d", text) or (not days and not parts and this is None):
        return None
    ordered = tuple(part for part in PARTS if part in parts) or ("day",)
    return Window(frozenset(days) or EVERY_DAY, ordered, until if this else None)
