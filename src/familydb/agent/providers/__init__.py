"""Model providers. One module per vendor, chosen per surface in the settings, and a model of
its lineup chosen by the level each situation asks for (`catalog`)."""

from __future__ import annotations

import logging
from typing import Any

from familydb.agent.providers import catalog, companies, prices
from familydb.agent.providers.base import (
    LOOK_TOKENS,
    Audio,
    Exchange,
    Heard,
    KeyCheck,
    Message,
    ModelReply,
    Picture,
    Provider,
    Seen,
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

NAMES = companies.SPARE_ORDER


def refusable_parts(name: str) -> tuple[str, ...]:
    """The parts of a request this company's module may leave out when refused (parts.py)."""
    import importlib

    try:
        module = importlib.import_module(f"familydb.agent.providers.{name}")
    except ImportError:
        return ()
    return tuple(part.name for part in getattr(module, "PARTS", ()))


def build(name: str, settings: Settings, api: Any = None, audio: Any = None) -> Provider:
    """The provider by name; `api` and `audio` inject test stand-ins."""
    if name == "anthropic":
        from familydb.agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(settings, api=api)
    if name == "openai":
        from familydb.agent.providers.openai import OpenAIProvider

        return OpenAIProvider(settings, api=api, audio=audio)
    if name == "gemini":
        from familydb.agent.providers.gemini import GeminiProvider

        return GeminiProvider(settings, api=api if api is not None else audio)
    raise ConfigError(f"unknown provider {name!r}; use one of {', '.join(NAMES)}")


owner = companies.owner


def chosen(settings: Settings, surface: Surface) -> str:
    """Which provider answers this surface; workers default to the chat choice."""
    if surface == "worker" and settings.worker_provider:
        return settings.worker_provider
    return settings.provider


def _named(provider: Provider, level: str) -> str:
    """The model the family named for this company at this level (`<company>_<level>_model`)."""
    settings = getattr(provider, "settings", None)
    return str(getattr(settings, f"{provider.name}_{level}_model", "") or "")


def level_model(provider: Provider, level: str) -> str | None:
    """The company's model at a level above everyday: the family's choice, or the lineup's."""
    named = _named(provider, level)
    if named:
        return named
    model = catalog.at(provider.name, level)
    return model.name if model is not None else None


def model_at(provider: Provider, surface: Surface, level: str) -> str:
    """The model this provider answers with at this level: everyday is the provider's own setting,
    above it the catalog's model, never cheaper than everyday (an unlisted model counts as dearer
    than any listed: prices.UNLISTED)."""
    everyday = provider.model_for(surface)
    stronger = None if level == catalog.EVERYDAY else level_model(provider, level)
    price = prices.price(provider.name, stronger) if stronger else None
    if stronger is None or (price is None and not _named(provider, level)):
        chosen = everyday
    else:
        own = prices.price(provider.name, everyday) or prices.UNLISTED
        theirs = price or prices.UNLISTED
        chosen = everyday if own.output > theirs.output else stronger
    # A model gone or going fails every call: the daily check's choice stands in (model_watch.py).
    return prices.swapped(provider.name, chosen)


def others(name: str) -> list[str]:
    """The other providers, in a fixed order so the same spare is chosen every time."""
    return [candidate for candidate in NAMES if candidate != name]


def for_surface(settings: Settings, surface: Surface, api: Any = None) -> Provider:
    """The provider to try first; an injected `api` means the configured one."""
    return build(chosen(settings, surface), settings, api=api)


def fallback_for(settings: Settings, surface: Surface, primary: str) -> Provider | None:
    """The other provider, when switched on and keyed; else None."""
    if not settings.provider_fallback:
        return None
    for candidate in others(primary):
        spare = build(candidate, settings)
        if spare.configured():
            return spare
    return None


def hearers(settings: Settings, audio: Any = None) -> list[Provider]:
    """Who may hear a voice note, in the order to ask: the chosen (else chat) company, then any
    other that can hear and has a key; spares only with the fallback on. Claude hears nothing.
    An injected `audio` answers alone for the first that could."""
    first = settings.transcribe_provider or settings.provider
    order = [first, *others(first)]
    if audio is not None:
        for name in order:
            provider = build(name, settings, audio=audio)
            if provider.listener():
                return [provider]
        return []
    able = [
        provider
        for provider in (build(name, settings) for name in order)
        if provider.listener() and provider.configured()
    ]
    if settings.transcribe_provider and (not able or able[0].name != settings.transcribe_provider):
        return able if settings.provider_fallback else []
    return able if settings.provider_fallback else able[:1]


def lookers(settings: Settings, api: Any = None) -> list[Provider]:
    """Who may look at a photo, in the order to ask: the lookup company, then any other with a
    key; spares only with the fallback on. An injected `api` answers alone."""
    first = chosen(settings, "worker")
    if api is not None:
        return [build(first, settings, api=api)]
    able = [
        provider
        for provider in (build(name, settings) for name in [first, *others(first)])
        if provider.viewer() and provider.configured()
    ]
    return able if settings.provider_fallback else able[:1]


def ready(settings: Settings, surface: Surface, api: Any = None) -> bool:
    """Whether any model can be asked on this surface (a fresh install has none until a key is
    typed); callers check this before calling."""
    primary = for_surface(settings, surface, api=api)
    return primary.configured() or fallback_for(settings, surface, primary.name) is not None


__all__ = [
    "LOOK_TOKENS",
    "NAMES",
    "Audio",
    "Exchange",
    "Heard",
    "KeyCheck",
    "Message",
    "ModelReply",
    "Picture",
    "Provider",
    "Seen",
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
    "hearers",
    "lookers",
    "model_at",
    "others",
    "owner",
]
