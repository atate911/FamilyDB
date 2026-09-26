"""Model providers. One module per vendor, chosen per surface in the settings."""

from __future__ import annotations

import logging
from typing import Any

from familydb.agent.providers.base import (
    Audio,
    Exchange,
    Heard,
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


def build(name: str, settings: Settings, api: Any = None, audio: Any = None) -> Provider:
    """The provider by name. `api` injects a stand-in, which is how the tests drive these, and
    `audio` one for the vendor's way of hearing a recording where that is a separate endpoint."""
    if name == "anthropic":
        from familydb.agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(settings, api=api)
    if name == "openai":
        from familydb.agent.providers.openai import OpenAIProvider

        return OpenAIProvider(settings, api=api, audio=audio)
    if name == "gemini":
        from familydb.agent.providers.gemini import GeminiProvider

        # Gemini hears through the same endpoint it answers through.
        return GeminiProvider(settings, api=api if api is not None else audio)
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


def hearers(settings: Settings, audio: Any = None) -> list[Provider]:
    """Who may hear a voice note, in the order to ask them: none when nobody can.

    The company chosen for it, or with none chosen the chat company, then, if that one cannot
    hear or is not switched on, any other that can and has a key. Claude hears nothing, so a
    family on Claude alone has nobody. With the fallback on, the rest come after, as spares.
    An injected `audio` (a test's stand-in) answers for whoever would be asked first, alone.
    """
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
        # The one they chose cannot: it has no key. Somebody else only with the fallback on.
        return able if settings.provider_fallback else []
    return able if settings.provider_fallback else able[:1]


def ready(settings: Settings, surface: Surface, api: Any = None) -> bool:
    """Whether any model can be asked on this surface: the chosen one has a key, or another does
    and the fallback is on. False is the ordinary state of a fresh install, before a key is typed
    on the settings page, and everything that would call a model checks this first rather than
    failing on the way."""
    primary = for_surface(settings, surface, api=api)
    return primary.configured() or fallback_for(settings, surface, primary.name) is not None


__all__ = [
    "NAMES",
    "Audio",
    "Exchange",
    "Heard",
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
    "chosen",
    "fallback_for",
    "for_surface",
    "hearers",
    "others",
    "owner",
]
