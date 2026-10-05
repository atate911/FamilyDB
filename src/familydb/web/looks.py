"""The looks the page can wear, and how a browser's choice of one is kept.

A look is a theme in `static/themes.css`: a set of colour tokens with a day value and a night value
together, which the whole stylesheet reads. Phosphor, the page as first drawn, is the default and is
written into `style.css` itself; it is dark only. The choice is one small cookie in the browser
(`fdb_look`, "rail.dark"), not anything the family's database knows: it is how this screen looks to
whoever is at it, so it follows the browser and costs nothing to read. A value that is not one of
these is the default, so nobody can put anything else on the page with it.
"""

from __future__ import annotations

from dataclasses import dataclass

COOKIE = "fdb_look"
COOKIE_DAYS = 365
DEFAULT = "phosphor"
AUTO, LIGHT, DARK = "auto", "light", "dark"
MODES = (AUTO, LIGHT, DARK)
MODE_WORDS = {
    AUTO: ("Match my device", "Day by day and night by night, as the phone or computer does."),
    LIGHT: ("Always day", "The light version, whatever the device is set to."),
    DARK: ("Always night", "The dark version, whatever the device is set to."),
}


@dataclass(frozen=True)
class Look:
    key: str
    name: str
    blurb: str
    # Whether it has a day, or is night only. Phosphor is a green screen: it has no day.
    has_day: bool
    # The band's colour by day and by night, for the browser's own bar (theme-color). themes.css
    # is where they are written; a test holds the two together.
    band: tuple[str, str]


LOOKS = (
    Look(
        "phosphor",
        "Phosphor",
        "The page as first drawn: charcoal with a breath of green, lit the way an old "
        "green screen was.",
        False,
        ("#0b0e0d", "#0b0e0d"),
    ),
    Look(
        "midnight",
        "Midnight",
        "Made for night: a blue-black page, a darker panel, soft-white ink, each colour "
        "lit like a window.",
        True,
        ("#0A0F1E", "#04060D"),
    ),
    Look(
        "homecomputer",
        "Home Computer",
        "An early-80s family machine: a putty case, a brown-black keyboard, one orange "
        "key for “this one”.",
        True,
        ("#231C17", "#2E251E"),
    ),
    Look(
        "ink",
        "Ink",
        "Almost no colour: a white page, black ink, a black panel. Colour is left for "
        "late, for Vera and for people.",
        True,
        ("#000000", "#000000"),
    ),
    Look(
        "enamel",
        "Enamel",
        "Old enamel signs and good painted interiors: warm grey plaster, a deep petrol "
        "panel, earthy colours.",
        True,
        ("#0D2D40", "#143344"),
    ),
    Look(
        "rail",
        "Rail yellow",
        "Station signage: a deep rail-blue panel, a crisp light page, and one signal "
        "yellow for what you act on next.",
        True,
        ("#0B2C69", "#13336F"),
    ),
    Look(
        "fjord",
        "Fjord",
        "A pale northern sky over deep slate water: cool and quiet, with fjord blue for "
        "what you act on.",
        True,
        ("#252B4A", "#272E52"),
    ),
)
BY_KEY = {look.key: look for look in LOOKS}


def get(key: str | None) -> Look:
    return BY_KEY.get(key or "", BY_KEY[DEFAULT])


def parse(value: str | None) -> tuple[Look, str]:
    """The look and mode a cookie names; the default for anything else, a half-readable value
    included."""
    key, _, mode = (value or "").partition(".")
    look = BY_KEY.get(key)
    if look is None or mode not in MODES:
        return BY_KEY[DEFAULT], AUTO
    return look, mode if look.has_day else AUTO


def choose(key: str | None, mode: str | None) -> tuple[Look, str] | None:
    """What a form asked for, if it is a look and a mode this page has; None if it is not."""
    if key not in BY_KEY or mode not in MODES:
        return None
    look = BY_KEY[key]
    return look, mode if look.has_day else AUTO


def value(look: Look, mode: str) -> str:
    return f"{look.key}.{mode}"


def scheme(look: Look, mode: str) -> str:
    """What to tell the browser about the page's colour scheme: it styles scrollbars and the
    boxes it draws itself to match."""
    if not look.has_day or mode == DARK:
        return "dark"
    return "light" if mode == LIGHT else "light dark"


def theme_colours(look: Look, mode: str) -> list[tuple[str | None, str]]:
    """The colour the browser's own bar should be, with the media query each goes with."""
    day, night = look.band
    if not look.has_day or mode == DARK:
        return [(None, night)]
    if mode == LIGHT:
        return [(None, day)]
    return [("(prefers-color-scheme: light)", day), ("(prefers-color-scheme: dark)", night)]
