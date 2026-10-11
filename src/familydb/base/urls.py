"""Links that came from the model or from fetched pages: keep only real web addresses."""

from __future__ import annotations

from urllib.parse import urlsplit


def clean_url(value: str | None) -> str | None:
    """The stripped URL when it is http(s) with a host, else None."""
    if not value:
        return None
    text = value.strip()
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return text
