"""Anthropic's server-side web tools. They run on Anthropic's side; nothing to implement here."""

from __future__ import annotations

from typing import Any

from familydb.availability import web_tools_available
from familydb.config import Settings

WEB_SEARCH: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
WEB_FETCH: dict[str, Any] = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5}


def server_tools(settings: Settings) -> list[dict[str, Any]]:
    """The server tools to append to the tool list, in a fixed order, when enabled."""
    if not web_tools_available(settings):
        return []
    return [dict(WEB_SEARCH), dict(WEB_FETCH)]
