"""The persona layer: who the assistant is to the family, as one object.

A `Persona` is a name, a character and her own lines. The name is what she is called, and it is
written once: her character and her lines say `{name}` wherever it goes, so the chat model, her
lines, Telegram's /start and the chat page all have it from one place. The character is how she
talks, not what she does: it goes first in the cached chat prefix, ahead of the product spec
(`agent/prompts/system.md`), which says what to do and wins where the two meet. The lines are her
wording for what the bot says unasked (`voice.EVENTS`), filled in by code, never by a model call.

Each persona ships as a folder here: `persona.toml` names her, `character.md` is her character
and `lines.toml` her lines, which she may go without (a line she lacks is said plainly). Adding a
persona is adding a folder. `DEFAULT` is the one the family meets unless they choose another:
Vera, as she was first written. `NONE` chooses none at all, which is `PLAIN`: the bot speaking
for itself, with no character and no lines of its own.

`active(settings)` is the persona in force, and what anything that speaks as her asks: the one
the `persona` setting chooses, with what the family wrote on the Personality page
(/settings/personality) laid over her own, the character as her rewrite in `persona_text` and
the lines as `voice_lines`. A rewrite of her character is a copy of one persona's and is kept
under her key, so it is laid over her and nobody else; restoring her original drops it. With no
persona chosen their words are kept but not used, and come back when one is chosen again.

Only turns a person reads carry her character: chat, the digest and retries. The lookup and
discovery workers, whose prose nobody reads, never do. Every word of it is sent, cached, with
each message; the Personality page and `familydb debug cost` say what that comes to.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from familydb.config import Settings

# What a persona's folder holds: her name, how she talks, and what she says unasked.
MANIFEST = "persona.toml"
CHARACTER = "character.md"
LINES = "lines.toml"
# Where her name goes, in her character and in any of her lines.
NAME = "{name}"


@dataclass(frozen=True)
class Persona:
    """Who the assistant is: what she is called, how she talks, and her lines."""

    key: str  # her folder here, and the `persona` setting's value
    name: str  # what she is called
    character: str  # how she talks, as written: {name} wherever her name goes; empty for none
    lines: Mapping[str, str]  # her wording by voice event; one she has no line for is plain

    @property
    def prompt(self) -> str:
        """Her character as the chat model is told it, with her name in it."""
        return self.character.replace(NAME, self.name)


# The persona the family meets unless they choose another.
DEFAULT = "default"
# The persona setting's value for speaking with none at all, and who speaks then: the bot as
# itself, under the product's name, with no character and the plain wording for everything.
NONE = "none"
PLAIN = Persona(NONE, "FamilyDB", "", MappingProxyType({}))
# Keys a setting may still hold from before a persona's folder was renamed. The default one was
# "vera" until her name was written once, apart from her folder; a setting that fails to load
# takes every stored setting down with it, keys included, so an old value must still find her.
RENAMED = {"vera": DEFAULT}


def key_for(value: str) -> str:
    """The persona a setting names, however it was written: any case, spaces, an older key."""
    key = value.strip().casefold()
    return RENAMED.get(key, key)


def available() -> tuple[str, ...]:
    """Every persona there is a folder for, by key."""
    folder = resources.files(__name__)
    return tuple(sorted(entry.name for entry in folder.iterdir() if (entry / MANIFEST).is_file()))


@lru_cache(maxsize=8)
def load(key: str) -> Persona:
    """A persona as she ships. `NONE` is `PLAIN`; a key with no folder here is refused."""
    if key == NONE:
        return PLAIN
    if key not in available():
        raise LookupError(f"no persona called {key!r}")
    folder = resources.files(__name__) / key
    name = tomllib.loads((folder / MANIFEST).read_text("utf-8")).get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"personas/{key}/{MANIFEST} does not give her a name")
    lines = folder / LINES
    said = tomllib.loads(lines.read_text("utf-8")) if lines.is_file() else {}
    return Persona(
        key=key,
        name=name.strip(),
        character=(folder / CHARACTER).read_text("utf-8").strip(),
        lines=MappingProxyType({str(event): str(line) for event, line in said.items()}),
    )


def active(settings: Settings) -> Persona:
    """The persona in force: the one chosen, with the family's own words laid over hers.

    Her character is replaced only by the family's rewrite of her; one written for another
    persona is never hers. No persona chosen means none at all, whatever the family once wrote
    for her."""
    chosen = load(settings.persona)
    if chosen is PLAIN:
        return PLAIN
    rewrite = settings.persona_text.get(chosen.key)
    own = {event: line for event, line in settings.voice_lines.items() if line}
    return replace(
        chosen,
        character=(rewrite.text.strip() if rewrite else "") or chosen.character,
        lines=MappingProxyType({**chosen.lines, **own}),
    )
