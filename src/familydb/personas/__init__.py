"""Who the assistant is: a name and a character, one Markdown file per persona in this folder.

The persona is how the chat model speaks, not what it does. It goes first in the cached prompt
prefix, ahead of the product spec (`agent/prompts/system.md`), which says what to do and wins
where the two meet. Only turns a person reads carry it: chat, the digest and retries. The lookup
and discovery workers, whose prose nobody reads, never do.

Chosen, and rewritten in place, on the settings page's Personality page (/settings/personality);
no persona speaks with none at all. The rewrite is stored as a setting over the file, and
restoring the original drops it. Adding a persona is adding a file here. Every word is sent,
cached, with each message; the page and `familydb debug cost` say what that comes to.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from importlib import resources
from typing import Any


def available() -> tuple[str, ...]:
    """Every persona there is a file for, by name."""
    folder = resources.files(__name__)
    return tuple(
        sorted(entry.name[:-3] for entry in folder.iterdir() if entry.name.endswith(".md"))
    )


# The persona setting's value for speaking with none at all.
NONE = "none"
# What the assistant is called with no persona: the product's own name.
NAMELESS = "FamilyDB"


def display_name(settings: Any) -> str:
    """What the family calls her, on the page and in Telegram's greeting: Vera, or FamilyDB."""
    return NAMELESS if settings.persona == NONE else settings.persona.capitalize()


def text_for(settings: Any) -> str:
    """What the chat is told she is: the family's rewrite if there is one, else the file's.

    No persona chosen means none at all, whatever text was once saved."""
    if settings.persona == NONE:
        return ""
    return settings.persona_text.strip() or load(settings.persona)


@lru_cache(maxsize=8)
def lines(name: str) -> dict[str, str]:
    """The persona's own wording for what she says unasked (`<name>.lines.toml`), by event."""
    if not name or name == NONE:
        return {}
    source = resources.files(__name__) / f"{name}.lines.toml"
    if not source.is_file():
        return {}
    return {str(k): str(v) for k, v in tomllib.loads(source.read_text("utf-8")).items()}


@lru_cache(maxsize=8)
def load(name: str) -> str:
    """The persona's text, or "" for none. An unknown name is refused when it is saved."""
    if not name or name == NONE:
        return ""
    return (resources.files(__name__) / f"{name}.md").read_text("utf-8").strip()
