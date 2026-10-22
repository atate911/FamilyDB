"""Recipes (docs/RECIPES.md): the facts a recipe idea carries on `add_idea` and `update_idea`
(`RecipeFacts`), `find_recipes` to rank them for a meal, and the lookup's hand-backs for a link
whose page has no recipe block (`save_recipe`, `skip_recipe`). Recipes are kept out of the
prompt's idea list, so the model finds them here; the ranking and its reasons are code's
(familydb/meals.py)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb import meals
from familydb.base.errors import ToolError
from familydb.store import ideas, plans
from familydb.store import recipes as store
from familydb.store.db import transaction
from familydb.store.ideas import RECIPE
from familydb.store.recipes import Occasion
from familydb.tools.registry import ToolContext, tool

MOST_INGREDIENTS = 40
MOST_STEPS = 30
MOST_LINE = 300
MOST_NOTE = 300
LONGEST = 24 * 60
MOST_SERVES = 50
MOST_TAGS = 5


class RecipeFacts(BaseModel):
    """Only what was said or shown; never guessed minutes or ingredients."""

    occasions: list[Occasion] | None = Field(
        default=None, description="Situations they said it suits; the whole list."
    )
    occasions_guessed: list[Occasion] | None = Field(
        default=None, description="Situations you read between the lines."
    )
    active_minutes: int | None = None
    total_minutes: int | None = None
    serves: int | None = None
    ingredients: list[str] | None = Field(default=None, description="One line each, as written.")
    steps: list[str] | None = None
    prep_note: str | None = Field(default=None, description="e.g. 'marinate the night before'.")


def given(facts: RecipeFacts | None) -> dict[str, Any]:
    """The facts given, checked: lists bounded, numbers that could be. Raises ToolError."""
    if facts is None:
        return {}
    out: dict[str, Any] = {}
    for key in ("active_minutes", "total_minutes"):
        value = getattr(facts, key)
        if value is not None:
            if not 0 < value <= LONGEST:
                raise ToolError(f"{key} is 1 to {LONGEST}")
            out[key] = value
    if facts.serves is not None:
        if not 0 < facts.serves <= MOST_SERVES:
            raise ToolError(f"serves is 1 to {MOST_SERVES}")
        out["serves"] = facts.serves
    for key, most in (("ingredients", MOST_INGREDIENTS), ("steps", MOST_STEPS)):
        value = getattr(facts, key)
        if value is not None:
            lines = [" ".join(line.split()) for line in value if line.strip()]
            if len(lines) > most:
                raise ToolError(f"at most {most} {key}")
            out[key] = [line[:MOST_LINE] for line in lines]
    for key in ("occasions", "occasions_guessed"):
        value = getattr(facts, key)
        if value is not None:
            out[key] = [one for one in store.OCCASIONS if one in set(value)]
    if facts.prep_note is not None:
        out["prep_note"] = " ".join(facts.prep_note.split())[:MOST_NOTE] or None
    return out


def for_kind(kind: str, facts: RecipeFacts | None) -> None:
    if facts is not None and ideas.normal_kind(kind) != RECIPE:
        raise ToolError("recipe facts are only for an idea of kind recipe")


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


class FindRecipesInput(BaseModel):
    occasion: Occasion | None = None
    most_minutes: int | None = Field(default=None, description="'Quick' is 30.")
    text: str | None = Field(default=None, description="A dish, cuisine or ingredient.")
    favorites: bool = Field(default=False, description="Their usual, what they loved.")
    limit: int = Field(default=5, description="1 to 10.")


@tool(
    name="find_recipes",
    description=(
        "The family's recipes, ranked by code for tonight or what was asked, each with its "
        "reason. Recipes are not in the ideas list; this finds them."
    ),
)
def find_recipes(ctx: ToolContext, args: FindRecipesInput) -> dict[str, Any]:
    limit = max(1, min(args.limit, meals.MOST_SHOWN))
    if args.most_minutes is not None and not 0 < args.most_minutes <= LONGEST:
        raise ToolError(f"most_minutes is 1 to {LONGEST}")
    now = ctx.clock.now()
    today = now.date().isoformat()
    tonight = meals.situation(
        now,
        plans.overlapping(ctx.conn, today, today),
        rest=meals.rest_days(ctx.conn, now.date()),
    )
    asked = meals.Asked(
        occasion=args.occasion,
        most_minutes=args.most_minutes,
        text=(args.text or "").strip() or None,
        favorites=args.favorites,
        meal=None if args.occasion in ("breakfast", "lunchbox") else "dinner",
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
        RecipeFacts(
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
