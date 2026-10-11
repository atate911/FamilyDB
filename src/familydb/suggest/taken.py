"""What came of a suggestion: which of what she offered the family planned, and how it went.

Read from what is already kept, with no model and nothing written: every suggestion logs each
idea's verdict and whether it was shown (`suggestions`), and the stronger call's picks; a plan
says which idea it is for and when it was made; an outcome says how it went. A plan is put down
to the latest suggestion made in the `ATTRIBUTE_DAYS` before it that offered its idea, or a find
of the same name, whoever asked. Plans nothing offered are counted apart.

It answers the questions the engine's rules are tuned by: how often a suggestion leads to a plan,
whether the stronger call's picks are taken more and rated higher than the engine's own order,
and what the family planned that the engine had ruled out (where a rule was wrong for them). The
Status page and `familydb debug suggestions` show it; the engine reads which suggestions led to a
plan, to let what was ignored come back sooner (engine.recently).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from familydb.store import ideas, outcomes, plans, suggestions
from familydb.store.ideas import normalize_title
from familydb.store.plans import Plan
from familydb.store.suggestions import Suggestion

# A plan made this long after a suggestion offered it is put down to that suggestion.
ATTRIBUTE_DAYS = 3
# Where what was planned stood in the suggestion, in the order they are reported.
SOURCES = {
    "pick": "Picked by the stronger call",
    "good": "Offered as good",
    "possible": "Offered as possible",
    "held_back": "Checked but not shown",
    "find": "Found outside the list",
    "ruled_out": "Ruled out, planned anyway",
}
# The most of what was planned against a verdict listed by name.
AGAINST_SHOWN = 8


@dataclass(frozen=True)
class Took:
    """One plan made from a suggestion."""

    plan_id: int
    title: str
    suggestion_id: int
    source: str  # a key of SOURCES
    idea_id: int | None = None
    reason: str | None = None  # the verdict's first reason, for one planned against it
    rating: int | None = None  # how it went, when the family said


@dataclass(frozen=True)
class Source:
    key: str
    label: str
    planned: int
    rated: int
    average: float | None


@dataclass
class Report:
    asked: int = 0  # suggestions in the period
    chosen: int = 0  # of which the stronger call chose for
    took: list[Took] = field(default_factory=list)
    unoffered: int = 0  # plans made in the period that no suggestion offered

    @property
    def led_to_plan(self) -> int:
        """How many suggestions led to at least one plan."""
        return len({one.suggestion_id for one in self.took})

    @property
    def take_rate(self) -> int:
        return round(self.led_to_plan / self.asked * 100) if self.asked else 0

    def sources(self) -> list[Source]:
        """Each source that led to a plan, in SOURCES' order."""
        shown = []
        for key, label in SOURCES.items():
            mine = [one for one in self.took if one.source == key]
            if not mine:
                continue
            ratings = [one.rating for one in mine if one.rating is not None]
            average = round(sum(ratings) / len(ratings), 1) if ratings else None
            shown.append(Source(key, label, len(mine), len(ratings), average))
        return shown

    def against(self) -> list[Took]:
        """What was planned though the engine ruled it out, newest first, a few."""
        ruled = [one for one in self.took if one.source == "ruled_out"]
        return list(reversed(ruled))[:AGAINST_SHOWN]

    def planned_from(self) -> dict[int, set[int]]:
        """For each suggestion that led to a plan, the ideas planned from it."""
        found: dict[int, set[int]] = {}
        for one in self.took:
            if one.idea_id is not None:
                found.setdefault(one.suggestion_id, set()).add(one.idea_id)
            else:
                found.setdefault(one.suggestion_id, set())
        return found


def _moment(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _names(plan: Plan, titles: dict[int, str]) -> set[str]:
    """The names a plan goes by: its own title and its idea's."""
    names = {normalize_title(plan.title)}
    if plan.idea_id is not None and plan.idea_id in titles:
        names.add(normalize_title(titles[plan.idea_id]))
    return {name for name in names if name}


def _picked(suggestion: Suggestion) -> tuple[set[int], set[str]]:
    """The ideas and the finds (by name) the stronger call picked for a suggestion."""
    picks = (suggestion.picks or {}).get("picks") or []
    ids = {p["idea_id"] for p in picks if isinstance(p, dict) and isinstance(p.get("idea_id"), int)}
    finds = {
        normalize_title(str(p.get("title") or ""))
        for p in picks
        if isinstance(p, dict) and str(p.get("ref", "")).startswith("find:")
    }
    return ids, finds


def _place(plan: Plan, names: set[str], suggestion: Suggestion) -> Took | None:
    """Where a plan stood in a suggestion, or None when it offered nothing like it."""
    ids, picked_finds = _picked(suggestion)
    candidate = next(
        (
            c
            for c in suggestion.candidates
            if isinstance(c, dict) and plan.idea_id is not None and c.get("idea_id") == plan.idea_id
        ),
        None,
    )
    find = next(
        (
            f
            for f in suggestion.web_finds
            if isinstance(f, dict) and normalize_title(str(f.get("title") or "")) in names
        ),
        None,
    )
    if candidate is None and find is None:
        return None
    reason = None
    if (plan.idea_id is not None and plan.idea_id in ids) or (names & picked_finds):
        source = "pick"
    elif candidate is not None:
        verdict = candidate.get("verdict")
        if verdict == "ruled_out":
            source = "ruled_out"
            reasons = candidate.get("reasons") or []
            reason = str(reasons[0]) if reasons else None
        elif not candidate.get("shown", True):
            source = "held_back"
        else:
            source = "good" if verdict == "good" else "possible"
    else:
        source = "find"
    return Took(
        plan_id=plan.id,
        title=plan.title,
        suggestion_id=suggestion.id,
        source=source,
        idea_id=plan.idea_id,
        reason=reason,
    )


def _rating(plan: Plan, said: Iterable[outcomes.Outcome]) -> int | None:
    """How a plan went: its own outcome, else its idea's first one from its day on."""
    said = list(said)
    own = [o for o in said if o.plan_id == plan.id and o.rating is not None]
    if own:
        return own[0].rating
    later = sorted(
        (
            o
            for o in said
            if plan.idea_id is not None
            and o.idea_id == plan.idea_id
            and o.plan_id is None
            and o.happened_on >= plan.start[:10]
            and o.rating is not None
        ),
        key=lambda o: (o.happened_on, o.id),
    )
    return later[0].rating if later else None


def report(conn: sqlite3.Connection, *, since: str) -> Report:
    """What came of the suggestions made at or after `since` (UTC ISO)."""
    asked = suggestions.since(conn, since=since)
    made = plans.made_since(conn, since=since)
    titles = {idea.id: idea.title for idea in ideas.list_all(conn, include_dropped=True)}
    said = outcomes.recent(conn, since=since[:10])
    found = Report(asked=len(asked), chosen=sum(1 for s in asked if s.picks))
    window = timedelta(days=ATTRIBUTE_DAYS)
    for plan in made:
        names = _names(plan, titles)
        at = _moment(plan.created_at)
        took = None
        for suggestion in reversed(asked):
            asked_at = _moment(suggestion.asked_at)
            if asked_at > at:
                continue
            if at - asked_at > window:
                break
            took = _place(plan, names, suggestion)
            if took is not None:
                break
        if took is None:
            found.unoffered += 1
            continue
        found.took.append(replace(took, rating=_rating(plan, said)))
    return found
