"""The looks the page can wear (themes in `static/themes.css`), kept in one cookie (`fdb_look`,
"rail.dark"). Any other value is the default, Kitchen Table, so a cookie can put nothing else on
the page."""

from __future__ import annotations

from dataclasses import dataclass

COOKIE = "fdb_look"
COOKIE_DAYS = 365
DEFAULT = "kitchen"
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
    # Night only, as Phosphor is.
    has_day: bool
    # theme-color by day and by night; a test holds these to themes.css.
    band: tuple[str, str]


LOOKS = (
    Look(
        "kitchen",
        "Kitchen Table",
        "The family's table: cream paper by day, charcoal at night, deep green for what "
        "you act on, and each person in their own colour.",
        True,
        ("#EFE7D7", "#121816"),
    ),
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


def parse(value: str | None) -> tuple[Look, str]:
    """The look and mode a cookie names; the default for anything else."""
    key, _, mode = (value or "").partition(".")
    look = BY_KEY.get(key)
    if look is None or mode not in MODES:
        return BY_KEY[DEFAULT], AUTO
    return look, mode if look.has_day else AUTO


def choose(key: str | None, mode: str | None) -> tuple[Look, str] | None:
    """What a form asked for, or None if it is not a look and mode this page has."""
    if key not in BY_KEY or mode not in MODES:
        return None
    look = BY_KEY[key]
    return look, mode if look.has_day else AUTO


def value(look: Look, mode: str) -> str:
    return f"{look.key}.{mode}"


def scheme(look: Look, mode: str) -> str:
    """The colour scheme to tell the browser, which styles its own boxes to match."""
    if not look.has_day or mode == DARK:
        return "dark"
    return "light" if mode == LIGHT else "light dark"


def theme_colours(look: Look, mode: str) -> list[tuple[str | None, str]]:
    """The browser bar's colour, with the media query each goes with."""
    day, night = look.band
    if not look.has_day or mode == DARK:
        return [(None, night)]
    if mode == LIGHT:
        return [(None, day)]
    return [("(prefers-color-scheme: light)", day), ("(prefers-color-scheme: dark)", night)]
