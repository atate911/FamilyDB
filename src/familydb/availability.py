"""Which optional integrations are configured. Shared by the tools, jobs and the prompt context."""

from __future__ import annotations

from pathlib import Path

from familydb.config import Settings

LOOPBACK_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1", "[::1]"})


def calendar_available(settings: Settings) -> bool:
    return bool(settings.google_calendar_id) and Path(settings.google_key_path).exists()


def weather_available(settings: Settings) -> bool:
    return settings.home_lat is not None and settings.home_lon is not None


def web_tools_available(settings: Settings) -> bool:
    return settings.web_tools_enabled


def enrichment_available(settings: Settings) -> bool:
    """Enrichment and discovery need the web tools."""
    return web_tools_available(settings)


def ticketmaster_available(settings: Settings) -> bool:
    """Ticketmaster is asked what is on within a radius of home: it needs the key and home."""
    return bool(settings.ticketmaster_api_key) and weather_available(settings)


def happening_search_available(settings: Settings) -> bool:
    """The weekly search near home, and the lookup that proposes calendars: model calls with
    the web, so they need the web tools, home, and a monthly budget above nothing."""
    return (
        settings.happening_search
        and web_tools_available(settings)
        and weather_available(settings)
        and settings.happening_budget > 0
    )


def happening_available(settings: Settings) -> bool:
    """Whether there is anything near home to read (familydb/happening.py): a calendar,
    Ticketmaster or the search."""
    return (
        bool(settings.event_feeds.strip())
        or ticketmaster_available(settings)
        or happening_search_available(settings)
    )


def digest_configured(settings: Settings) -> bool:
    return bool(settings.digest_chat_id)


def web_available(settings: Settings) -> bool:
    """Whether `familydb run` should also serve the page."""
    return settings.web_enabled


def web_is_public(settings: Settings) -> bool:
    """Whether the configured host would be reachable from anywhere but this machine."""
    return settings.web_host.strip().lower() not in LOOPBACK_HOSTS


def web_password_required(settings: Settings) -> bool:
    """A page the network can reach needs a password. Off the loopback it can be waived on purpose,
    for a home network; behind a proxy it cannot, since the page is bound to the loopback there
    and a loopback address says nothing about who is on the far end.
    """
    if settings.web_trust_proxy:
        return True
    return web_is_public(settings) and not settings.web_allow_no_password
