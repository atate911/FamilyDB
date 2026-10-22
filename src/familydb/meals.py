"""What to cook (docs/RECIPES.md): the situations a recipe suits, guessed from its facts when
nobody said, and the family's recipes ranked for a meal, with reasons, all by code. The page's
pick, `find_recipes` and "what's for dinner?" ask here; the model frames the question and words
the reply, and never ranks.

A fact rules a recipe out (longer than the time there is, a situation asked for that it is not,
words asked for that it lacks); a matter of taste (made lately, a guessed situation) only lowers
it to a maybe, said first. Situations the family said stand; guessed ones lean.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Literal, Protocol
from urllib.parse import unquote, urlsplit

from familydb import groceries
from familydb.base.dates import fmt_minutes
from familydb.store import ideas as idea_store
from familydb.store import lists, memories
from familydb.store import recipes as recipe_store
from familydb.store.ideas import RECIPE, Idea
from familydb.store.recipes import OCCASIONS, FilledBy, Ingredient, Recipe

# A recipe made within this many days rests; asked for a favourite it does not.
REST_DAYS = 10
# Up to this many minutes is a weeknight one, from this many slow.
QUICK = 30
WEEKNIGHT_MOST = 40
# Longer than this is not a weeknight one, whatever else is said of it, unless the family says so.
WEEKNIGHT_LONGEST = 60
SLOW = 180
# Serves this many or more: a family dinner; this many or more: guests too.
FAMILY = 6
GUESTS = 8
# When dinner is, for the evening's plans: cooking starts by DINNER, a plan before LATEST counts.
DINNER = time(17, 30)
LATEST = time(21, 0)
MOST_SHOWN = 10

OCCASION_WORDS = {
    "weeknight": "weeknight",
    "family_dinner": "family dinner",
    "prep_ahead": "prep ahead",
    "slow": "slow cook",
    "date_night": "date night",
    "guests": "for guests",
    "kids_cook": "kids can make it",
    "lunchbox": "lunchbox",
    "freezer": "freezes well",
}
CLUES: dict[str, tuple[str, ...]] = {
    "prep_ahead": (
        "make ahead",
        "make-ahead",
        "night before",
        "overnight",
        "ahead of time",
        "the day before",
        "marinate",
        "refrigerate for",
        "chill for",
    ),
    "slow": ("slow cooker", "slow-cooker", "crock pot", "crockpot", "braise", "low and slow"),
    "freezer": ("freezes well", "freezer", "freeze for", "can be frozen", "to freeze"),
    "lunchbox": ("lunchbox", "lunch box", "packed lunch"),
    "kids_cook": ("kids can", "with the kids", "kid-friendly", "kid friendly"),
}


class Planned(Protocol):
    """Something on the day, as `agenda.Entry` is."""

    start: str
    all_day: bool


def occasion_words(occasions: Iterable[str]) -> list[str]:
    return [OCCASION_WORDS.get(one, one.replace("_", " ")) for one in occasions]


def guess_occasions(recipe: Recipe, idea: Idea | None = None) -> list[str]:
    """The situations its facts point to, when the family named none: read from the minutes, the
    yield and the words of its name, notes and steps. None when the facts say nothing."""
    text = " ".join(
        [
            recipe.name or "",
            recipe.prep_note or "",
            *recipe.steps,
            *(idea.tags if idea else []),
            (idea.title if idea else ""),
            (idea.description or "" if idea else ""),
        ]
    ).casefold()
    found: list[str] = []
    minutes = recipe.minutes
    if minutes is not None and minutes <= QUICK:
        found.append("weeknight")
    if minutes is not None and minutes >= SLOW:
        found.append("slow")
    for occasion, clues in CLUES.items():
        if any(clue in text for clue in clues):
            found.append(occasion)
    if recipe.serves is not None and recipe.serves >= FAMILY:
        found.append("family_dinner")
    if recipe.serves is not None and recipe.serves >= GUESTS:
        found.append("guests")
    return [one for one in OCCASIONS if one in set(found)]


@dataclass(frozen=True)
class Situation:
    """The meal asked about: its day, how long there is to cook when a plan cuts the evening
    short (None when nothing does), and how long a recipe made rests (the family's, when they
    said: `rest_days` for kind recipe)."""

    day: date
    weekend: bool
    minutes_free: int | None = None
    plan: str | None = None
    rest_days: int = REST_DAYS


def rest_days(conn: sqlite3.Connection, today: date) -> int:
    """How long a recipe made rests: what the family said about recipes (`remember`'s rule,
    rest_kind recipe), the latest winning, else `REST_DAYS`. A rest for everything is about
    going out, and is not read here."""
    days = REST_DAYS
    for memory in memories.held(conn, today=today):
        rule = memory.rule or {}
        if memory.member_id is None and rule.get("rest_kind") == RECIPE:
            days = int(rule.get("rest_days", days))
    return days


def situation(
    now: datetime, planned: Iterable[Planned] = (), *, rest: int = REST_DAYS
) -> Situation:
    """Tonight as code reads it: the weekday, and the minutes from when cooking starts (now, or
    `DINNER` if earlier) to the first timed plan before `LATEST`."""
    today = now.date()
    start = max(now, datetime.combine(today, DINNER, tzinfo=now.tzinfo))
    latest = datetime.combine(today, LATEST, tzinfo=now.tzinfo)
    first: tuple[datetime, str] | None = None
    for entry in planned:
        if entry.all_day or len(entry.start) <= 10:
            continue
        try:
            begins = datetime.fromisoformat(entry.start)
        except ValueError:
            continue
        if begins.tzinfo is None:
            begins = begins.replace(tzinfo=now.tzinfo)
        begins = begins.astimezone(now.tzinfo)
        later = first is None or begins < first[0]
        if begins.date() == today and start <= begins <= latest and later:
            first = (begins, getattr(entry, "title", "") or "a plan")
    free = int((first[0] - start).total_seconds() // 60) if first else None
    return Situation(
        day=today,
        weekend=today.weekday() >= 5,
        minutes_free=free,
        plan=first[1] if first else None,
        rest_days=rest,
    )


@dataclass(frozen=True)
class Asked:
    """What the question narrowed to; nothing given is the meal as code reads it."""

    occasion: str | None = None
    most_minutes: int | None = None
    text: str | None = None
    favorites: bool = False


@dataclass
class Ranked:
    idea: Idea
    recipe: Recipe
    verdict: Literal["good", "maybe", "out"]
    reasons: list[str] = field(default_factory=list)
    score: tuple[float, ...] = ()

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


def _words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{3,}", text.casefold())}


def _matches(idea: Idea, recipe: Recipe, wanted: set[str]) -> bool:
    said = _words(
        " ".join(
            [
                idea.title,
                idea.description or "",
                " ".join(idea.tags),
                recipe.name or "",
                " ".join(ingredient.item for ingredient in recipe.ingredients),
            ]
        )
    )
    said |= {word[:-1] for word in said if word.endswith("s")}
    return bool(wanted & said)


def _ago(idea: Idea, today: date) -> int | None:
    if not idea.last_done_at:
        return None
    try:
        return (today - date.fromisoformat(idea.last_done_at[:10])).days
    except ValueError:
        return None


def _when_words(days: int) -> str:
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def judge(idea: Idea, recipe: Recipe, now: Situation, asked: Asked) -> Ranked:
    """One recipe for the meal asked about."""
    reasons: list[str] = []
    out: list[str] = []
    maybe: list[str] = []
    minutes = recipe.minutes
    limit = asked.most_minutes
    if limit is None and now.minutes_free is not None and asked.occasion != "prep_ahead":
        limit = now.minutes_free
    if minutes is not None:
        reasons.append(fmt_minutes(minutes))
        if limit is not None and minutes > limit:
            why = f"takes {fmt_minutes(minutes)}, there are {fmt_minutes(max(limit, 0))}"
            if now.plan and asked.most_minutes is None:
                why += f" before {now.plan}"
            out.append(why)
    elif limit is not None:
        maybe.append("how long it takes is not known")
    if recipe.serves:
        reasons.append(f"serves {recipe.serves}")
    if asked.occasion:
        words = OCCASION_WORDS.get(asked.occasion, asked.occasion)
        quick_enough = (
            asked.occasion == "weeknight" and minutes is not None and minutes <= WEEKNIGHT_MOST
        )
        too_long = (
            asked.occasion == "weeknight" and minutes is not None and minutes > WEEKNIGHT_LONGEST
        )
        if asked.occasion in recipe.occasions or quick_enough:
            reasons.append(words)
        elif too_long:
            out.append(f"takes {fmt_minutes(minutes or 0)}, too long for a weeknight")
        elif asked.occasion in recipe.occasions_guessed:
            maybe.append(f"looks like {words}, nobody said")
        elif recipe.occasions:
            out.append(f"not a {words} one")
        else:
            maybe.append(f"nobody said if it is {words}")
    if asked.text:
        wanted = _words(asked.text)
        wanted |= {word[:-1] for word in wanted if word.endswith("s")}
        if wanted and not _matches(idea, recipe, wanted):
            out.append(f"nothing of {asked.text}")
    days = _ago(idea, now.day)
    if idea.times_done:
        made = "made once" if idea.times_done == 1 else f"made {idea.times_done} times"
        if idea.avg_rating is not None:
            made += f", {idea.avg_rating:g}/10"
        reasons.append(made)
        if days is not None:
            reasons.append(f"last {_when_words(days)}")
    else:
        reasons.append("new to us")
    if days is not None and days < now.rest_days and not asked.favorites:
        maybe.append(f"had it {_when_words(days)}")
    verdict: Literal["good", "maybe", "out"] = "out" if out else ("maybe" if maybe else "good")
    shown = out if out else [*maybe, *reasons]
    rating = idea.avg_rating if idea.avg_rating is not None else 6.0
    score = (
        {"good": 0, "maybe": 1, "out": 2}[verdict],
        -(rating + (1.5 if asked.favorites and idea.times_done else 0)),
        -min(idea.times_done, 5) if asked.favorites else 0,
        minutes if minutes is not None else 90,
        -idea.id,
    )
    return Ranked(idea, recipe, verdict, shown, tuple(float(x) for x in score))


ANYTHING = Asked()


def rank(
    chosen: Iterable[tuple[Idea, Recipe]], now: Situation, asked: Asked = ANYTHING
) -> list[Ranked]:
    """Every recipe judged and ordered: the good, then the maybes, then what is ruled out."""
    return sorted((judge(idea, recipe, now, asked) for idea, recipe in chosen), key=_order)


def _order(ranked: Ranked) -> tuple[float, ...]:
    return ranked.score


def pick(chosen: Iterable[tuple[Idea, Recipe]], now: Situation) -> Ranked | None:
    """The page's pick for the meal: on a weeknight a weeknight one when there is one."""
    everything = list(chosen)
    if not everything:
        return None
    asked = Asked(occasion=None if now.weekend else "weeknight")
    ranked = rank(everything, now, asked)
    if ranked[0].verdict == "out" and asked.occasion:
        ranked = rank(everything, now)
    best = ranked[0]
    return best if best.verdict != "out" else None


def guessed_for(recipe: Recipe, idea: Idea | None = None) -> list[str]:
    """What to keep as guessed: nothing when the family named any situation."""
    return [] if recipe.occasions else guess_occasions(recipe, idea)


# -- what a recipe keeps ------------------------------------------------------------------------

# What may change how a recipe is guessed: a change to any of these guesses again.
GUESSED_FROM = frozenset(
    {"name", "steps", "prep_note", "active_minutes", "total_minutes", "serves", "ingredients"}
)
FILLABLE = ("name", "ingredients", "steps", "active_minutes", "total_minutes", "serves")


def ingredients(lines: Iterable[Any]) -> list[Ingredient]:
    """Each line with what to buy read out of it; a line already split (a lookup's) keeps its
    split, folded, and is parsed only where it gave no item."""
    found: list[Ingredient] = []
    for line in lines:
        if isinstance(line, Ingredient):
            line = line.model_dump()
        if isinstance(line, dict):
            text = " ".join(str(line.get("text") or "").split())
            item = lists.fold(str(line.get("item") or ""))
            amount = " ".join(str(line.get("amount") or "").split()) or None
            if not text:
                continue
            found.append(
                Ingredient(text=text, item=item, amount=amount) if item else groceries.parse(text)
            )
        elif isinstance(line, str) and line.strip():
            found.append(groceries.parse(line))
    return found


def keep(
    conn: sqlite3.Connection,
    idea: Idea,
    given: dict[str, Any],
    *,
    by: FilledBy,
    now: str,
) -> Recipe:
    """Keep a recipe's facts. What the family gives replaces; what a page or a lookup gives fills
    only what is empty, so what the family said stands. Situations nobody named are guessed from
    the facts when they change, kept apart, never the family's. Call inside a transaction."""
    before = recipe_store.get(conn, idea.id) or Recipe(idea_id=idea.id)
    fields: dict[str, Any] = {}
    for key, value in given.items():
        if value is None:
            continue
        if key == "ingredients":
            value = ingredients(value)
        if by == "family" or key not in FILLABLE or not getattr(before, key):
            fields[key] = value
    if by == "family" and fields:
        fields["filled_by"] = before.filled_by or "family"
    merged = before.model_copy(update=fields)
    if "occasions" in fields:
        fields["occasions_guessed"] = [
            one for one in merged.occasions_guessed if one not in merged.occasions
        ]
        merged = merged.model_copy(update=fields)
    if GUESSED_FROM & set(fields):
        guessed = set(merged.occasions_guessed) | set(guess_occasions(merged, idea))
        fields["occasions_guessed"] = [
            one for one in OCCASIONS if one in guessed and one not in merged.occasions
        ]
    if not fields and recipe_store.get(conn, idea.id) is not None:
        return before
    return recipe_store.upsert(conn, idea.id, fields, now=now)


def from_page(
    conn: sqlite3.Connection,
    idea: Idea,
    found: dict[str, Any],
    *,
    by: FilledBy,
    tags: list[str],
    now: str,
) -> Recipe:
    """What a page said of a recipe, kept: its facts where the family left them empty, its name as
    the title where the title was only the link's words, its tags where the idea has none, and the
    idea marked filled in. Call inside a transaction."""
    recipe = keep(conn, idea, found, by=by, now=now)
    recipe = recipe_store.upsert(
        conn, idea.id, {"filled_at": now, "filled_by": by, "fill_note": None}, now=now
    )
    changes: dict[str, Any] = {"enrichment": "done", "enriched_at": now, "enrichment_note": None}
    if recipe.name_wanted and recipe.name:
        changes["title"] = recipe.name[:200]
        recipe_store.upsert(conn, idea.id, {"name_wanted": False}, now=now)
    if tags and not idea.tags:
        changes["tags"] = tags
    idea_store.update(conn, idea.id, changes, now=now)
    return recipe_store.get(conn, idea.id) or recipe


def not_read(
    conn: sqlite3.Connection, idea: Idea, note: str, *, status: str | None, now: str
) -> None:
    """Why a recipe's link could not be read. With a `status` (skipped, failed) the idea's lookup
    is over; without, it waits for the paid lookup. Call inside a transaction."""
    recipe_store.upsert(conn, idea.id, {"fill_note": note[:200]}, now=now)
    if status is not None:
        idea_store.update(
            conn,
            idea.id,
            {"enrichment": status, "enriched_at": now, "enrichment_note": note[:200]},
            now=now,
        )


def details(recipe: Recipe) -> str:
    """A recipe's facts in a line, for the note after it is read: "35 min, serves 4, 11
    ingredients, from seriouseats.com"."""
    parts: list[str] = []
    if recipe.minutes is not None:
        parts.append(fmt_minutes(recipe.minutes))
    if recipe.serves:
        parts.append(f"serves {recipe.serves}")
    if recipe.ingredients:
        count = len(recipe.ingredients)
        parts.append(f"{count} ingredient{'s' if count != 1 else ''}")
    if recipe.source_site:
        parts.append(f"from {recipe.source_site}")
    return ", ".join(parts) or "nothing more than the link"


SLUG_NOISE = re.compile(r"^(?:\d+|recipe|recipes|html?|php|aspx?|amp|index)$")


def title_from_link(url: str | None) -> str | None:
    """A title from the link's last part, read as words: ".../sheet-pan-chicken-fajitas" is
    "Sheet pan chicken fajitas". None when the link has nothing to read."""
    if not url:
        return None
    path = unquote(urlsplit(url).path or "")
    parts = [part for part in path.split("/") if part]
    for part in reversed(parts):
        words = [
            w for w in re.split(r"[-_+.\s]+", part) if w and not SLUG_NOISE.match(w.casefold())
        ]
        if len(words) >= 1 and any(len(w) > 2 for w in words):
            text = " ".join(words)
            return text[:1].upper() + text[1:].lower()
    return None
