"""Anthropic's server-side web tools. They run on Anthropic's side; nothing to implement here."""

from __future__ import annotations

from typing import Any

from familydb.availability import web_tools_available
from familydb.config import Settings

WEB_SEARCH: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
WEB_FETCH: dict[str, Any] = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5}


def server_tools(
    settings: Settings,
    *,
    force: bool = False,
    max_uses: int | None = None,
    user_location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """The server tools to append to a tool list, in a fixed order.

    The chat agent gets them only when enabled in settings; worker turns force them on and may
    cap uses or add an approximate location for searches.
    """
    if not (force or web_tools_available(settings)):
        return []
    search = dict(WEB_SEARCH)
    fetch = dict(WEB_FETCH)
    if max_uses is not None:
        search["max_uses"] = max_uses
        fetch["max_uses"] = max_uses
    if user_location:
        search["user_location"] = dict(user_location)
    return [search, fetch]
