"""Each company's models by level, and what each can do.

Every company sells a small family of models, from a cheap quick one to a dear strong one: GPT-6
Luna, Sol and Astra; Claude Haiku, Sonnet and Opus; Gemini Flash-Lite, Flash and Pro. The family
chooses a level for each situation (`chat_level`, `digest_level`, `lookup_level` in the
settings) rather than a name, so the choice holds whichever company answers, and a message that
moves to the fallback company is answered at the same level there.

`everyday` is the company's model as the settings name it, per surface: its cheapest unless the
family typed another (a test holds the defaults to that). `better` and `best` are the ones
listed here, unless the everyday model already costs more (`providers.model_at`): a level up
never answers with a cheaper model. What a model costs is `prices.py`'s business, and how a
request is shaped for it the provider module's; this table only says where each model stands and
what it can do, and a test checks that against what the provider modules send.

No SDK is imported here, so the settings page can read it without loading one.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from familydb.agent.providers.prices import Price, price
from familydb.config import Level

LEVELS: tuple[Level, ...] = typing.get_args(Level)
EVERYDAY: Level = "everyday"


@dataclass(frozen=True)
class Model:
    """One model in a company's lineup."""

    provider: str
    name: str  # the id sent to the company
    label: str  # what people call it
    level: Level
    # Whether it thinks before answering, so whether the thinking settings do anything for it.
    thinks: bool = True

    @property
    def price(self) -> Price | None:
        return price(self.provider, self.name)


# In level order, cheapest first. Claude's strongest here is Opus rather than Fable, which costs
# twice as much for work a family planner does not ask of it; it can still be typed in by name.
LINEUP: dict[str, tuple[Model, ...]] = {
    "openai": (
        Model("openai", "gpt-6-luna", "GPT-6 Luna", "everyday"),
        Model("openai", "gpt-6-sol", "GPT-6 Sol", "better"),
        Model("openai", "gpt-6-astra", "GPT-6 Astra", "best"),
    ),
    "anthropic": (
        # The one current Claude that takes a fixed thinking budget rather than an effort; the
        # provider sends it neither (anthropic.OLDER_MODELS).
        Model("anthropic", "claude-haiku-4-5", "Claude Haiku 4.5", "everyday", thinks=False),
        Model("anthropic", "claude-sonnet-5", "Claude Sonnet 5", "better"),
        Model("anthropic", "claude-opus-5", "Claude Opus 5", "best"),
    ),
    "gemini": (
        Model("gemini", "gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite", "everyday"),
        Model("gemini", "gemini-3.8-flash", "Gemini 3.8 Flash", "better"),
        Model("gemini", "gemini-3.1-pro-preview", "Gemini 3.1 Pro", "best"),
    ),
}


def lineup(provider: str) -> tuple[Model, ...]:
    """This company's models, cheapest first. Empty for a company the table does not know."""
    return LINEUP.get(provider, ())


def at(provider: str, level: str) -> Model | None:
    """This company's model at this level, or None when the table has none for it."""
    return next((model for model in lineup(provider) if model.level == level), None)


def known(provider: str | None, name: str | None) -> Model | None:
    """The lineup entry this model name belongs to, if any.

    A dated snapshot (claude-haiku-4-5-20251001, gpt-6-luna-2026-09-01) is its family; anything
    else longer is another model, as claude-opus-5-5 is not claude-opus-5.
    """
    named = (name or "").lower()
    for model in lineup(provider or ""):
        if named == model.name:
            return model
        digits = named.removeprefix(model.name + "-").replace("-", "")
        if (
            named.startswith(model.name + "-")
            and digits.isdigit()
            and len(digits) == len("YYYYMMDD")
        ):
            return model
    return None


__all__ = ["EVERYDAY", "LEVELS", "LINEUP", "Model", "at", "known", "lineup"]
