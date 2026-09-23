"""Which optional integrations are configured. Shared by the tools, jobs and the prompt context."""

from __future__ import annotations

from pathlib import Path

from familydb.config import Settings

LOOPBACK_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1", "[::1]"})


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


def web_available(settings: Settings) -> bool:
    """Whether `familydb run` should also serve the page."""
    return settings.web_enabled


def web_is_public(settings: Settings) -> bool:
    """Whether the configured host would be reachable from anywhere but this machine."""
    return settings.web_host.strip().lower() not in LOOPBACK_HOSTS


def web_password_required(settings: Settings) -> bool:
    """A page off the loopback needs a password unless that was waived on purpose."""
    return web_is_public(settings) and not settings.web_allow_no_password
