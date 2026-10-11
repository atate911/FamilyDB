"""Each company's models by level (everyday, better, best), and whether each thinks.

The family chooses a level per situation, so the choice holds on the fallback company too.
`everyday` is the settings' own model per surface (a test holds the defaults to the cheapest);
a level up never answers with a cheaper model (`providers.model_at`). A test checks this against
what the provider modules send. SDK-free."""

from __future__ import annotations

import typing
from dataclasses import dataclass

from familydb.agent.providers.prices import Price, price
from familydb.base.config import Level

LEVELS: tuple[Level, ...] = typing.get_args(Level)
EVERYDAY: Level = "everyday"


@dataclass(frozen=True)
class Model:
    provider: str
    name: str  # the id sent to the company
    label: str  # what people call it
    level: Level
    # Whether the thinking settings do anything for it.
    thinks: bool = True

    @property
    def price(self) -> Price | None:
        return price(self.provider, self.name)


# In level order, cheapest first. Claude's best is Opus, not the twice-dearer Fable (typeable).
LINEUP: dict[str, tuple[Model, ...]] = {
    "openai": (
        Model("openai", "gpt-6-luna", "GPT-6 Luna", "everyday"),
        Model("openai", "gpt-6-sol", "GPT-6 Sol", "better"),
        Model("openai", "gpt-6-astra", "GPT-6 Astra", "best"),
    ),
    "anthropic": (
        # Takes a fixed thinking budget, not an effort (anthropic.OLDER_MODELS).
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
    """This company's models, cheapest first."""
    return LINEUP.get(provider, ())


def at(provider: str, level: str) -> Model | None:
    """This company's model at this level, or None."""
    return next((model for model in lineup(provider) if model.level == level), None)


def known(provider: str | None, name: str | None) -> Model | None:
    """The lineup entry a name belongs to: a dated snapshot is its family, anything else longer
    is another model (claude-opus-5-5 is not claude-opus-5)."""
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
