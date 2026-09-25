"""Model providers. One module per vendor, chosen per surface in the settings, and a model of
its lineup chosen by the level each situation asks for (`catalog`)."""

from __future__ import annotations

import logging
from typing import Any

from familydb.agent.providers import catalog
from familydb.agent.providers.base import (
    Exchange,
    KeyCheck,
    Message,
    ModelReply,
    Provider,
    Stop,
    Surface,
    SystemBlock,
    ToolCall,
    ToolDef,
    ToolOutcome,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.errors import ConfigError

log = logging.getLogger(__name__)

NAMES = ("anthropic", "openai", "gemini")
# Which vendor a model name belongs to. Only ever used after the fact, to say who answered a
# call that is already logged; nothing is chosen by it.
OWNED = (
    ("anthropic", ("claude",)),
    ("openai", ("gpt", "o1", "o3", "o4", "chatgpt")),
    ("gemini", ("gemini",)),
)


def build(name: str, settings: Settings, api: Any = None) -> Provider:
    """The provider by name. `api` injects a stand-in, which is how the tests drive these."""
    if name == "anthropic":
        from familydb.agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(settings, api=api)
    if name == "openai":
        from familydb.agent.providers.openai import OpenAIProvider

        return OpenAIProvider(settings, api=api)
    if name == "gemini":
        from familydb.agent.providers.gemini import GeminiProvider

        return GeminiProvider(settings, api=api)
    raise ConfigError(f"unknown provider {name!r}; use one of {', '.join(NAMES)}")


def owner(model: str | None) -> str | None:
    """Whose model this name is, as far as the name says, or None when it does not say."""
    named = (model or "").lower()
    for name, prefixes in OWNED:
        if any(named.startswith(prefix) for prefix in prefixes):
            return name
    return None


def chosen(settings: Settings, surface: Surface) -> str:
    """Which provider answers this surface. Workers fall back to the chat choice when unset."""
    if surface == "worker" and settings.worker_provider:
        return settings.worker_provider
    return settings.provider


def model_at(provider: Provider, surface: Surface, level: str) -> str:
    """The model this provider answers with at this level.

    At everyday it is the provider's own setting for the surface, which is the company's cheapest
    unless the family named another; above it, the catalog's model at that level, so a stronger
    choice holds on whichever company answers, the fallback included.
    """
    if level != catalog.EVERYDAY:
        stronger = catalog.at(provider.name, level)
        if stronger is not None:
            return stronger.name
    return provider.model_for(surface)


def others(name: str) -> list[str]:
    """The rest, in a fixed order, so a fallback choice never depends on the weather."""
    return [candidate for candidate in NAMES if candidate != name]


def for_surface(settings: Settings, surface: Surface, api: Any = None) -> Provider:
    """The provider to try first. An injected `api` always means the configured one."""
    return build(chosen(settings, surface), settings, api=api)


def fallback_for(settings: Settings, surface: Surface, primary: str) -> Provider | None:
    """The other provider, when it is switched on and has a key. None means there is nowhere
    else to go, which is the ordinary case for a family using one account."""
    if not settings.provider_fallback:
        return None
    for candidate in others(primary):
        spare = build(candidate, settings)
        if spare.configured():
            return spare
    return None


def ready(settings: Settings, surface: Surface, api: Any = None) -> bool:
    """Whether any model can be asked on this surface: the chosen one has a key, or another does
    and the fallback is on. False is the ordinary state of a fresh install, before a key is typed
    on the settings page, and everything that would call a model checks this first rather than
    failing on the way."""
    primary = for_surface(settings, surface, api=api)
    return primary.configured() or fallback_for(settings, surface, primary.name) is not None


__all__ = [
    "NAMES",
    "Exchange",
    "KeyCheck",
    "Message",
    "ModelReply",
    "Provider",
    "Stop",
    "Surface",
    "SystemBlock",
    "ToolCall",
    "ToolDef",
    "ToolOutcome",
    "TurnRequest",
    "WebAccess",
    "build",
    "catalog",
    "chosen",
    "fallback_for",
    "for_surface",
    "model_at",
    "others",
    "owner",
]
