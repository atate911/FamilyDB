"""What a search is told about the family (docs/FINDS.md, "What the family decided"), so it looks
for what suits them rather than for any family near home.

Built by code, deterministic, and bounded: each section has a cap in characters and is cut at a
whole line, saying how many more there were. It carries who they are (how many grown-ups, the
kids' ages), their firm limits, what they said they like and what they loved, where they live and
go, and what they already have (their list, what she has already found, what they saved of it,
what they passed on and why), so the search looks for something new, leaning towards what they
saved and away from what they passed on. It never carries a name (a person is "a kid, 9" or "a
grown-up"), a birthday, a present or a wish list, another chat's words, a sign-in, or where
anybody is.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from familydb.base.config import Settings
from familydb.base.dates import age_on
from familydb.store import finds, ideas, members, memories, outcomes
from familydb.store.members import Member

CAPS = {
    "family": 300,
    "limits": 900,
    "likes": 900,
    "areas": 300,
    "have": 1200,
    "found": 600,
    "liked": 500,
    "passed": 500,
}
TOTAL = sum(CAPS.values())
STEADY = ("family", "limits", "likes", "areas")
HEADINGS = {
    "family": "Who they are",
    "limits": "Musts (keep to these)",
    "likes": "What they like",
    "areas": "Where they live and go",
    "have": "Already on their list (look for something new)",
    "found": "Already found for them (do not report again)",
    "liked": "What they saved of what was found before (more like these)",
    "passed": "They said not for them",
}
LOVED = 8  # a rating at or above this is something they loved
RATINGS_DAYS = 365
PASSED_DAYS = 180
LIKED_DAYS = 90
# What they said they like, from these kinds of memory; a must goes in whatever its kind.
TASTES = ("food", "activities", "places")
# A memory about a present is kept from a search, whatever else it says.
PRESENT_WORDS = re.compile(r"\b(gift|gifts|present|presents|surprise|birthday)\b", re.IGNORECASE)


def _fit(lines: list[str], cap: int) -> list[str]:
    """Whole lines up to `cap` characters, and a line saying how many more there were."""
    kept: list[str] = []
    used = 0
    for number, line in enumerate(lines):
        if used + len(line) + 1 > cap:
            kept.append(f"- … and {len(lines) - number} more")
            break
        kept.append(line)
        used += len(line) + 1
    return kept


def who(person: Member, today: date) -> str:
    """A person as a search may know them: a role and, for a kid, an age; never a name."""
    if person.role != "kid":
        return "a grown-up"
    age = age_on(person.birth_date, today)
    return f"a kid, {age}" if age is not None else "a kid"


def _unnamed(text: str, people: list[Member], today: date) -> str:
    """Their words with each name said as who that person is."""
    for person in sorted(people, key=lambda p: -len(p.display_name)):
        name = re.escape(person.display_name.strip())
        if name:
            text = re.sub(rf"\b{name}\b", who(person, today), text, flags=re.IGNORECASE)
    return text


def _family(people: list[Member], today: date) -> list[str]:
    grown = sum(1 for person in people if person.role != "kid")
    kids = [person for person in people if person.role == "kid"]
    line = f"- {grown} grown-up{'s' if grown != 1 else ''}"
    if kids:
        ages = sorted(age for age in (age_on(k.birth_date, today) for k in kids) if age is not None)
        said = ", ".join(str(age) for age in ages)
        line += f"; {len(kids)} kid{'s' if len(kids) != 1 else ''}"
        line += f", aged {said}" if said else ""
        unknown = len(kids) - len(ages)
        if ages and unknown:
            line += f" (and {unknown} not given)"
    return [line]


def _memory_lines(
    said: list[memories.Memory], people: list[Member], today: date, *, firm: bool
) -> list[str]:
    by_id = {person.id: person for person in people}
    lines = []
    for memory in said:
        if memory.inferred or memory.firm != firm or PRESENT_WORDS.search(memory.fact):
            continue
        if not firm and memory.category not in TASTES:
            continue
        about = by_id.get(memory.member_id) if memory.member_id is not None else None
        whose = who(about, today) if about is not None else "the family"
        lines.append(f"- {whose}: {memory.fact}")
    return lines


def _loved(conn: sqlite3.Connection, today: date, kept: dict[int, ideas.Idea]) -> list[ideas.Idea]:
    """The ideas on their list they rated highly last time, within a year."""
    since = (today - timedelta(days=RATINGS_DAYS)).isoformat()
    rated = outcomes.recent_ratings(conn, since=since, last=1)
    return sorted(
        (kept[idea_id] for idea_id, said in rated.items() if idea_id in kept and said[0] >= LOVED),
        key=lambda idea: (idea.title.casefold(), idea.id),
    )


@dataclass(frozen=True)
class Brief:
    text: str  # all of it, as the search is told it
    # Who they are, their musts, tastes and areas alone: what a cached search is known by, so a
    # search's own finds joining the list do not make the same ask a new search.
    steady: str


def brief(conn: sqlite3.Connection, settings: Settings, *, today: date) -> Brief:
    """The family as a search is told it, the same for the same household on the same day."""
    people = members.list_all(conn)
    said = memories.active(conn, today=today)
    on_list = {
        idea.id: idea
        for idea in ideas.list_all(conn)
        if idea.status != "dropped" and not ideas.is_gift(idea)
    }
    titles = sorted(on_list.values(), key=lambda idea: (idea.title.casefold(), idea.id))
    found = finds.upcoming(conn, start=today, end=today + timedelta(days=60), limit=40)
    found += finds.anytime(conn, limit=20)
    since = (today - timedelta(days=PASSED_DAYS)).isoformat()
    areas = [settings.home_area.strip() or "not set"]
    areas += [line.strip() for line in settings.scouting_areas.splitlines() if line.strip()]
    loved = _loved(conn, today, on_list)
    sections = {
        "family": _family(people, today),
        "limits": [
            _unnamed(line, people, today) for line in _memory_lines(said, people, today, firm=True)
        ],
        "likes": _memory_lines(said, people, today, firm=False)
        + [f"- loved: {idea.title} ({idea.kind})" for idea in loved],
        "areas": [f"- home: {areas[0]}"] + [f"- they go to: {area}" for area in areas[1:]],
        "have": [f"- {idea.title} ({idea.kind})" for idea in titles],
        "found": [f"- {one.title}" for one in sorted(found, key=lambda f: f.id)],
        "liked": [
            f"- {one.title}" + (f" ({one.category})" if one.category else "")
            for one in finds.saved_since(
                conn, since=(today - timedelta(days=LIKED_DAYS)).isoformat(), limit=20
            )
        ],
        "passed": [
            f"- {one.title}" + (f": {one.passed_why}" if one.passed_why else "")
            for one in finds.passed(conn, since=since)
        ],
    }
    # Titles and reasons are the family's words too: a name in them is said as who it is.
    for key in ("likes", "have", "liked", "passed"):
        sections[key] = [_unnamed(line, people, today) for line in sections[key]]
    parts = {
        key: f"{HEADINGS[key]}:\n" + "\n".join(_fit(lines, CAPS[key]))
        for key, lines in sections.items()
        if lines
    }
    return Brief(
        text="\n\n".join(parts.values()),
        steady="\n\n".join(part for key, part in parts.items() if key in STEADY),
    )
