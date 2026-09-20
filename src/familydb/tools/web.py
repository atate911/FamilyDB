"""Anthropic's server-side web tools. They run on Anthropic's side; nothing to implement here."""

from __future__ import annotations

from typing import Any

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

    Only worker turns get them, which is what `force` means. The chat agent never searches the
    web itself: searches are billed one by one, so a model free to search on a whim is an open
    tab on every message. Searching happens in bounded worker turns instead, with a cap on uses,
    and the results come back through strict tools. `web_tools_available` decides whether those
    worker turns run at all, not whether chat may search.
    """
    if not force:
        return []
    search = dict(WEB_SEARCH)
    fetch = dict(WEB_FETCH)
    if max_uses is not None:
        search["max_uses"] = max_uses
        fetch["max_uses"] = max_uses
    if user_location:
        search["user_location"] = dict(user_location)
    return [search, fetch]
