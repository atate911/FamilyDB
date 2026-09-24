"""Who the assistant is: a name and a character, one Markdown file per persona in this folder.

The persona is how the chat model speaks, not what it does. It goes first in the cached prompt
prefix, ahead of the product spec (`agent/prompts/system.md`), which says what to do and wins
where the two meet. Only turns a person reads carry it: chat, the digest and retries. The lookup
and discovery workers, whose prose nobody reads, never do.

Choose one on the settings page ("persona"); empty speaks with no persona at all. Adding one is
adding a file here. Every word is sent, cached, with each message, so `familydb debug cost` shows
what one costs before it is chosen.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources


def available() -> tuple[str, ...]:
    """Every persona there is a file for, by name."""
    folder = resources.files(__name__)
    return tuple(
        sorted(entry.name[:-3] for entry in folder.iterdir() if entry.name.endswith(".md"))
    )


@lru_cache(maxsize=8)
def load(name: str) -> str:
    """The persona's text, or "" for none. An unknown name is refused when it is saved."""
    if not name:
        return ""
    return (resources.files(__name__) / f"{name}.md").read_text("utf-8").strip()
