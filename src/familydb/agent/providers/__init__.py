"""Model providers. One module per vendor, chosen per surface in the settings."""

from __future__ import annotations

import logging
from typing import Any

from familydb.agent.providers.base import (
    Exchange,
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


__all__ = [
    "NAMES",
    "Exchange",
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
    "others",
]
