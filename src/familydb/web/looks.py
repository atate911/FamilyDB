"""The look cookie (`fdb_look`, "rail.dark"), for the pages before anybody signs in; the looks
themselves are `familydb.looks`. Any other value is the default, Kitchen Table, so a cookie can put
nothing else on the page."""

from __future__ import annotations

from typing import Any

from familydb.looks import (
    AUTO,
    BY_KEY,
    DARK,
    DEFAULT,
    LIGHT,
    LOOKS,
    MODE_WORDS,
    MODES,
    Look,
    choose,
    parse,
    scheme,
    theme_colours,
    value,
)

COOKIE = "fdb_look"
COOKIE_DAYS = 365

__all__ = [
    "AUTO",
    "BY_KEY",
    "COOKIE",
    "COOKIE_DAYS",
    "DARK",
    "DEFAULT",
    "LIGHT",
    "LOOKS",
    "MODES",
    "MODE_WORDS",
    "Look",
    "choose",
    "parse",
    "remember",
    "scheme",
    "theme_colours",
    "value",
]


def remember(response: Any, value: str | None, *, secure: bool) -> None:
    """Set the browser's look cookie, or clear it for somebody who has not chosen one."""
    if value is None:
        response.delete_cookie(COOKIE)
        return
    response.set_cookie(
        COOKIE,
        value,
        max_age=COOKIE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=secure,
    )
