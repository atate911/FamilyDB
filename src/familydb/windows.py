"""A task's preferred window, read in code as days of the week and parts of the day.

"One of these Saturday mornings" is kept as said (`tasks.preferred_window`); so it can be nudged
when one comes round (jobs/nudges.py) its words are read against a short list: days, weekend,
weekdays, morning, afternoon, evening. Any other word ("before Christmas", "after school", "next
Saturday") means not read at all, so a nudge never comes at a time the family did not mean and
the task stays as it was.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

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
_FILLER = frozenset(
    {"a", "an", "and", "any", "of", "one", "or", "some", "the", "these", "those"}
    | {"at", "day", "days", "during", "in", "on", "over", "sometime", "time", "week"}
    | {"free", "quiet", "spare"}
)


@dataclass(frozen=True)
class Window:
    days: frozenset[int]
    parts: tuple[str, ...]

    def open_at(self, moment: datetime) -> str | None:
        if moment.weekday() not in self.days:
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
        return f"{'an' if said[0].lower() in 'aeiou' else 'a'} {said}"

    def now_words(self, moment: datetime, part: str) -> str:
        day = DAYS[moment.weekday()]
        return day if part == "day" else f"{day} {part}"


def read(text: str) -> Window | None:
    """The window in these words, or None when any word is unknown or none says when."""
    words = re.sub(r"['\u2019]s\b", "", text.lower())
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
    if re.search(r"\d", text) or (not days and not parts):
        return None
    ordered = tuple(part for part in PARTS if part in parts) or ("day",)
    return Window(frozenset(days) or EVERY_DAY, ordered)
