"""The persona layer: who the assistant is to the family, as one object.

A `Persona` is a name, a character and her own lines. Her name is written once: her character and
lines say `{name}` wherever it goes. The character is how she talks, not what she does: it goes
first in the cached chat prefix, ahead of the product spec (`agent/prompts/system.md`), which
wins where they meet; the family's notes follow it, and the spec wins over them too. The lines
are her wording for what the bot says unasked (`voice.EVENTS`), filled in by code.

Each persona is a folder here: `persona.toml` (name, label), `character.md`, `lines.toml` (a line
she lacks is said plainly; a line may be a list of wordings, kept as a tuple). Two may share a
name, so the label tells them apart: a few words with {name} in them. `DEFAULT` is Vera as first
written. `NONE` is `PLAIN`: the bot as itself, with no character and no lines.

`active(settings)` is the persona in force: the one the `persona` setting chooses with the
family's Personality-page words laid over it (`persona_name`, `persona_text`, `persona_notes`,
`voice_lines`). Their name, notes and lines are theirs whoever she is; a rewrite of her character
is kept under her key and laid over her alone. With no persona chosen their words are kept but
unused.

Only turns a person reads carry her character (chat, digest, retries); the workers never do.
Every word is sent, cached, with each message: `familydb debug cost` shows what it comes to.
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
    from familydb.base.config import Settings

MANIFEST = "persona.toml"
CHARACTER = "character.md"
LINES = "lines.toml"
NAME = "{name}"
NOTES_HEADER = "## The family's own notes on how you talk\n\n"


@dataclass(frozen=True)
class Persona:
    key: str
    name: str
    character: str
    lines: Mapping[str, str | tuple[str, ...]]
    label: str = NAME
    notes: str = ""

    @property
    def prompt(self) -> str:
        told = f"{self.character}\n\n{NOTES_HEADER}{self.notes}" if self.notes else self.character
        return told.replace(NAME, self.name)

    @property
    def listed_as(self) -> str:
        return self.label.replace(NAME, self.name)


DEFAULT = "default"
# The `persona` setting's value for no persona: the bot as itself, under the product's name.
NONE = "none"
PLAIN = Persona(NONE, "FamilyDB", "", MappingProxyType({}))
# Older keys for a persona whose folder has another name ("vera" is the default). A setting that
# fails to load takes every stored setting with it, so an old value must still find her.
RENAMED = {"vera": DEFAULT}


def key_for(value: str) -> str:
    key = value.strip().casefold()
    return RENAMED.get(key, key)


def available() -> tuple[str, ...]:
    folder = resources.files(__name__)
    return tuple(sorted(entry.name for entry in folder.iterdir() if (entry / MANIFEST).is_file()))


@lru_cache(maxsize=8)
def load(key: str) -> Persona:
    if key == NONE:
        return PLAIN
    if key not in available():
        raise LookupError(f"no persona called {key!r}")
    folder = resources.files(__name__) / key
    manifest = tomllib.loads((folder / MANIFEST).read_text("utf-8"))
    name = manifest.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"personas/{key}/{MANIFEST} does not give her a name")
    label = manifest.get("label", NAME)
    if not isinstance(label, str) or any(brace in label.replace(NAME, "") for brace in "{}"):
        raise ValueError(f"personas/{key}/{MANIFEST}: her label is words, with no brace but {NAME}")
    lines = folder / LINES
    said = tomllib.loads(lines.read_text("utf-8")) if lines.is_file() else {}
    return Persona(
        key=key,
        name=name.strip(),
        character=(folder / CHARACTER).read_text("utf-8").strip(),
        lines=MappingProxyType(
            {str(event): _one_line(key, str(event), line) for event, line in said.items()}
        ),
        label=label.strip() or NAME,
    )


def _one_line(key: str, event: str, written: object) -> str | tuple[str, ...]:
    if isinstance(written, str):
        return written
    if isinstance(written, list) and all(isinstance(wording, str) for wording in written):
        return tuple(written)
    raise ValueError(f"personas/{key}/{LINES}: {event} is a wording, or a list of wordings")


def active(settings: Settings) -> Persona:
    """The persona in force: the one chosen, with the family's words laid over hers.

    Their name for her fills {name}. Her character is replaced only by a rewrite of her, never
    another persona's. Their notes go with whichever persona is chosen. No persona chosen means
    none at all, whatever the family once wrote for her.
    """
    chosen = load(settings.persona)
    if chosen is PLAIN:
        return PLAIN
    rewrite = settings.persona_text.get(chosen.key)
    own = {
        event: line if isinstance(line, str) else tuple(line)
        for event, line in settings.voice_lines.items()
        if (line if isinstance(line, str) else "".join(line)).strip()
    }
    return replace(
        chosen,
        name=settings.persona_name.strip() or chosen.name,
        character=(rewrite.text.strip() if rewrite else "") or chosen.character,
        lines=MappingProxyType({**chosen.lines, **own}),
        notes=settings.persona_notes.strip(),
    )
