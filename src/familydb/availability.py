"""Which optional integrations are configured. Shared by the tools, jobs and the prompt context."""

from __future__ import annotations

from pathlib import Path

from familydb.config import Settings


def calendar_available(settings: Settings) -> bool:
    return bool(settings.google_calendar_id) and Path(settings.google_token_path).exists()


def weather_available(settings: Settings) -> bool:
    return settings.home_lat is not None and settings.home_lon is not None


def web_tools_available(settings: Settings) -> bool:
    return settings.web_tools_enabled


def enrichment_available(settings: Settings) -> bool:
    """Enrichment and discovery need the web tools."""
    return web_tools_available(settings)


def digest_configured(settings: Settings) -> bool:
    return bool(settings.digest_chat_id)
