"""Recipes (docs/RECIPES.md): `find_recipes` ranks them for a meal (a read); `recipe` saves a
new one with what was said and changes one's facts (the writes); and the lookup's hand-backs for
a link whose page has no recipe block (`save_recipe`, `skip_recipe`). Recipes are ideas of kind
recipe kept out of the prompt's idea list, so the model finds them here; their facts are on these
tools alone, so the idea tools every message carries keep their size. Reading and writing are two
tools so a question about dinner is never counted as a change. The ranking and its reasons are
code's (familydb/meals.py)."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb import meals, presents
from familydb.availability import calendar_available
from familydb.base import roles
from familydb.base.errors import ToolError
from familydb.saved_plans import SavedPlans
from familydb.store import ideas
from familydb.store import recipes as store
from familydb.store.db import transaction
from familydb.store.ideas import RECIPE
from familydb.store.recipes import Occasion
from familydb.tools.registry import NOT_THEIRS, ToolContext, keep_undo, tool

MOST_INGREDIENTS = 40
MOST_STEPS = 30
MOST_LINE = 300
MOST_NOTE = 300
LONGEST = 24 * 60
MOST_SERVES = 50
MOST_TAGS = 5
FACTS = (
    "occasions",
    "occasions_guessed",
    "active_minutes",
    "total_minutes",
    "serves",
    "ingredients",
    "steps",
    "prep_note",
)
log = logging.getLogger(__name__)


class RecipeInput(BaseModel):
    """Only what was said or shown; never guessed."""

    action: Literal["save", "change"] = Field(description="save a new one; change one by id.")
    id: int | None = Field(default=None, description="change: its number.")
    title: str | None = Field(default=None, description="save: as said, else the link's words.")
    url: str | None = Field(default=None, description="save: the recipe's link.")
    description: str | None = Field(default=None, description="save: anything else said.")
    occasions: list[Occasion] | None = Field(
        default=None, description="As they said; on change, the whole list."
    )
    occasions_guessed: list[Occasion] | None = Field(
        default=None, description="Ones you read between the lines."
    )
    active_minutes: int | None = None
    total_minutes: int | None = None
    serves: int | None = None
    ingredients: list[str] | None = Field(default=None, description="One line each, as written.")
    steps: list[str] | None = None
    prep_note: str | None = Field(default=None, description="e.g. 'marinate the night before'.")


class FindRecipesInput(BaseModel):
    occasion: Occasion | None = None
    most_minutes: int | None = Field(default=None, description="'Quick' is 30.")
    text: str | None = Field(default=None, description="A dish, cuisine or ingredient.")
    favorites: bool = Field(default=False, description="Their usual, what they loved.")


def given(source: Any) -> dict[str, Any]:
    """The facts given (on the tool's input, or any object with those names), checked: lists
    bounded, numbers that could be. Raises ToolError."""
    out: dict[str, Any] = {}
    for key in ("active_minutes", "total_minutes"):
        value = getattr(source, key, None)
        if value is not None:
            if not 0 < value <= LONGEST:
                raise ToolError(f"{key} is 1 to {LONGEST}")
            out[key] = value
    serves = getattr(source, "serves", None)
    if serves is not None:
        if not 0 < serves <= MOST_SERVES:
            raise ToolError(f"serves is 1 to {MOST_SERVES}")
        out["serves"] = serves
    for key, most in (("ingredients", MOST_INGREDIENTS), ("steps", MOST_STEPS)):
        value = getattr(source, key, None)
        if value is not None:
            lines = [" ".join(line.split()) for line in value if line.strip()]
            if len(lines) > most:
                raise ToolError(f"at most {most} {key}")
            out[key] = [line[:MOST_LINE] for line in lines]
    for key in ("occasions", "occasions_guessed"):
        value = getattr(source, key, None)
        if value is not None:
            out[key] = [one for one in store.OCCASIONS if one in set(value)]
    note = getattr(source, "prep_note", None)
    if note is not None:  # an empty one clears it
        out["prep_note"] = " ".join(note.split())[:MOST_NOTE]
    return out


def shown(recipe: store.Recipe) -> dict[str, Any]:
    """A recipe as the model reads it back: the facts, without the kept bookkeeping."""
    out = recipe.model_dump(
        mode="json",
        exclude={"idea_id", "updated_at", "name_wanted", "filled_by", "filled_at"},
        exclude_none=True,
    )
    out["ingredients"] = [one.text for one in recipe.ingredients]
    if not out.get("occasions_guessed"):
        out.pop("occasions_guessed", None)
    out["read"] = recipe.read
    return out


@tool(
    name="recipe",
    description="Save a recipe (a dish or a link) or change one's facts.",
    writes=True,
)
def recipe(ctx: ToolContext, args: RecipeInput) -> dict[str, Any]:
    if args.action == "save":
        return _save(ctx, args)
    return _change(ctx, args)


def _save(ctx: ToolContext, args: RecipeInput) -> dict[str, Any]:
    """A new recipe through `add_idea` (its duplicate checks, its undo), then its facts."""
    from familydb.tools.ideas import AddIdeaInput, add_idea

    title = (args.title or "").strip() or meals.title_from_link(args.url) or ""
    if not title:
        raise ToolError("save needs a title or a link")
    if ctx.allowed_tools is not None and "add_idea" not in ctx.allowed_tools:
        raise ToolError("saving an idea is not allowed in this turn")
    facts = given(args)
    made = add_idea(
        ctx,
        AddIdeaInput(title=title, kind=RECIPE, url=args.url, description=args.description),
    )
    if "duplicate_of" in made or not facts:
        return made
    idea = ideas.get(ctx.conn, made["id"])
    assert idea is not None
    with transaction(ctx.conn):
        kept = meals.keep(ctx.conn, idea, facts, by="family", now=ctx.now_iso())
    return {**made, "recipe": shown(kept)}


def _change(ctx: ToolContext, args: RecipeInput) -> dict[str, Any]:
    """One recipe's facts, as the family said them; its old facts kept for undo."""
    # A kid may save a recipe, as she may add an idea, but not change one: the registry's gate,
    # by hand here since the tool's save is hers too (`ToolSpec.needs` covers a whole tool).
    if ctx.member is not None and not roles.may(ctx.member.role, "change"):
        raise ToolError(NOT_THEIRS)
    if args.id is None:
        raise ToolError("change needs the recipe's id")
    facts = given(args)
    if not facts:
        raise ToolError("nothing to change: give a fact")
    with transaction(ctx.conn):
        idea = ideas.get(ctx.conn, args.id)
        if idea is None or idea.kind != RECIPE:
            raise ToolError(f"no recipe #{args.id}")
        before = store.get(ctx.conn, idea.id) or store.Recipe(idea_id=idea.id)
        after = meals.keep(ctx.conn, idea, facts, by="family", now=ctx.now_iso())
    old, new = before.model_dump(mode="json"), after.model_dump(mode="json")
    moved = sorted(key for key in FACTS if old.get(key) != new.get(key))
    if moved:
        keep_undo(
            ctx,
            "restore_idea",
            f"changed recipe #{idea.id} {idea.title}",
            idea=idea.id,
            before={},
            after={},
            recipe_before={key: old.get(key) for key in moved},
            recipe_after={key: new.get(key) for key in moved},
        )
    return {"id": idea.id, "title": idea.title, "recipe": shown(after)}


def _today(ctx: ToolContext, now: datetime) -> list[SimpleNamespace]:
    """What is on today, as the other pages and /dinner read it: the Google calendar through the
    tool's own client when one is connected (events somebody added by hand included), else the
    plans kept here. A calendar that does not answer falls back to the plans kept here."""
    start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    end = start + timedelta(days=1)
    saved = SavedPlans(ctx.conn, ctx.clock.tz)
    calendar = ctx.calendar if calendar_available(ctx.settings) and ctx.calendar else saved
    try:
        events = calendar.recent_events(start, end)  # Google's, kept a minute (app.calendar)
    except Exception:
        log.warning("the calendar could not be read for tonight's recipes; plans kept here used")
        events = saved.list_events(start, end)
    return [
        SimpleNamespace(start=event.start.isoformat(), all_day=event.all_day, title=event.title)
        for event in events
        if event.busy and event.status != "cancelled"
    ]


@tool(
    name="find_recipes",
    description=(
        "The family's recipes, which are not in the ideas list, ranked by code for tonight or "
        "what was asked, each with its reason."
    ),
)
def find_recipes(ctx: ToolContext, args: FindRecipesInput) -> dict[str, Any]:
    limit = meals.MOST_SHOWN // 2
    if args.most_minutes is not None and not 0 < args.most_minutes <= LONGEST:
        raise ToolError(f"most_minutes is 1 to {LONGEST}")
    now = ctx.clock.now()
    today = now.date().isoformat()
    # A plan for a present is only "a plan" in a reason where it is kept from the asker, and
    # every present's where a kid reads the chat (ctx.plain), as /dinner does (commands.py).
    kept = presents.kept_ids(ctx.conn, ctx.member)
    if ctx.plain:
        kept |= presents.gift_ids(ctx.conn)
    tonight = meals.situation(
        now,
        _today(ctx, now),
        rest=meals.rest_days(ctx.conn, now.date()),
        unnamed=presents.plan_titles(ctx.conn, today, today, kept),
    )
    occasion = args.occasion
    asked = meals.Asked(
        occasion=occasion,
        most_minutes=args.most_minutes,
        text=(args.text or "").strip() or None,
        favorites=args.favorites,
        meal=None if occasion in ("breakfast", "lunchbox") else "dinner",
    )
    ranked = meals.rank(store.live(ctx.conn), tonight, asked)
    kept = [one for one in ranked if one.verdict != "out"]
    out = [one for one in ranked if one.verdict == "out"]
    said: dict[str, Any] = {
        "recipes": [
            {
                "id": one.idea.id,
                "title": one.idea.title,
                "verdict": one.verdict,
                "why": one.reason,
                **({"occasions": one.recipe.occasions} if one.recipe.occasions else {}),
                **(
                    {"looks_like": one.recipe.occasions_guessed}
                    if one.recipe.occasions_guessed
                    else {}
                ),
            }
            for one in kept[:limit]
        ],
        "not_shown": max(0, len(kept) - limit),
    }
    if out:
        said["ruled_out"] = [
            {"id": one.idea.id, "title": one.idea.title, "why": one.reason} for one in out[:3]
        ]
        said["ruled_out_more"] = max(0, len(out) - 3)
    if tonight.minutes_free is not None and not asked.most_minutes:
        said["tonight"] = f"{tonight.minutes_free} min to cook before {tonight.plan}"
    if not ranked:
        said["note"] = "no recipes saved yet"
    return said


# -- the lookup's hand-backs, for a page with no recipe block ------------------------------------


class FoundIngredient(BaseModel):
    text: str = Field(description="The line as the page writes it.")
    item: str = Field(description="What to buy: '2 cups chopped onion' is 'onion'.")
    amount: str | None = Field(default=None, description="'2 cups'.")


class SaveRecipeInput(BaseModel):
    idea_id: int
    name: str | None = Field(default=None, description="The recipe's name on the page.")
    ingredients: list[FoundIngredient] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list, description="In order, as written.")
    prep_minutes: int | None = None
    total_minutes: int | None = None
    serves: int | None = None
    tags: list[str] = Field(default_factory=list, description="Cuisine, diet: 'mexican'.")


class SkipRecipeInput(BaseModel):
    idea_id: int
    status: Literal["not_a_recipe", "unreadable"] = Field(
        description="not_a_recipe: the page is not one recipe; unreadable: it could not be read."
    )
    reason: str = Field(description="One short sentence.")


def _recipe_idea(ctx: ToolContext, idea_id: int) -> ideas.Idea:
    idea = ideas.get(ctx.conn, idea_id)
    if idea is None or idea.kind != RECIPE:
        raise ToolError(f"no recipe #{idea_id}")
    return idea


@tool(
    name="save_recipe",
    description=(
        "Keep what the page says of the recipe: only what it states. Used by the recipe lookup."
    ),
    writes=True,
    worker_only=True,
)
def save_recipe(ctx: ToolContext, args: SaveRecipeInput) -> dict[str, Any]:
    idea = _recipe_idea(ctx, args.idea_id)
    if not args.ingredients and not args.steps:
        raise ToolError("give the ingredients or the steps, or skip_recipe")
    facts = given(
        SimpleNamespace(
            active_minutes=_sane(args.prep_minutes),
            total_minutes=_sane(args.total_minutes),
            serves=args.serves if args.serves and 0 < args.serves <= MOST_SERVES else None,
            steps=args.steps[:MOST_STEPS],
        )
    )
    facts["ingredients"] = [
        one.model_dump() for one in args.ingredients[:MOST_INGREDIENTS] if one.text.strip()
    ]
    if args.name and args.name.strip():
        facts["name"] = " ".join(args.name.split())[:200]
    tags = [tag.strip().casefold() for tag in args.tags if 0 < len(tag.strip()) <= 30]
    now = ctx.now_iso()
    with transaction(ctx.conn):
        recipe = meals.from_page(ctx.conn, idea, facts, by="lookup", tags=tags[:MOST_TAGS], now=now)
    return {"idea_id": idea.id, "recipe": shown(recipe)}


def _sane(minutes: int | None) -> int | None:
    return minutes if minutes is not None and 0 < minutes <= LONGEST else None


@tool(
    name="skip_recipe",
    description="The page is not one recipe, or could not be read. Used by the recipe lookup.",
    writes=True,
    worker_only=True,
)
def skip_recipe(ctx: ToolContext, args: SkipRecipeInput) -> dict[str, Any]:
    idea = _recipe_idea(ctx, args.idea_id)
    status = "skipped" if args.status == "not_a_recipe" else "failed"
    with transaction(ctx.conn):
        meals.not_read(ctx.conn, idea, args.reason, status=status, now=ctx.now_iso())
    return {"idea_id": idea.id, "status": status, "reason": args.reason}
