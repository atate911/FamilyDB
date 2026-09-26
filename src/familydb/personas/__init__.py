"""The persona layer: who the assistant is to the family, as one object.

A `Persona` is a name, a character and her own lines. The name is what she is called, and it is
written once: her character and her lines say `{name}` wherever it goes, so the chat model, her
lines, Telegram's /start and the chat page all have it from one place. The character is how she
talks, not what she does: it goes first in the cached chat prefix, ahead of the product spec
(`agent/prompts/system.md`), which says what to do and wins where the two meet. The family's own
notes on how she talks, when they have written any, follow her character there, and the spec
wins over them too. The lines are her wording for what the bot says unasked (`voice.EVENTS`),
filled in by code, never by a model call.

Each persona ships as a folder here: `persona.toml` names her and says which of her she is,
`character.md` is her character and `lines.toml` her lines, which she may go without (a line she
lacks is said plainly). A line there may be one wording or a list of them, of which she picks one
each time (`voice.say`); `Persona.lines` keeps a list as a tuple, and the family's lines likewise.
Adding a persona is adding a folder. Two may share a name, so her label is what tells
them apart where they are listed together: a few words with {name} in them, such as "{name}, in
brief". `DEFAULT` is the one the family meets unless they choose another: Vera, as she was first
written. `NONE` chooses none at all, which is `PLAIN`: the bot speaking for itself, with no
character and no lines of its own.

`active(settings)` is the persona in force, and what anything that speaks as her asks: the one
the `persona` setting chooses, with what the family wrote on the Personality page
(/settings/personality) laid over her own, the name they call her as `persona_name`, the
character as her rewrite in `persona_text`, their notes on how she talks as `persona_notes` and
the lines as `voice_lines`. Their name for her, their notes and their lines are theirs whoever
she is. A rewrite of her character is a copy of one persona's and is kept under her key, so it is
laid over her and nobody else; restoring her original drops it and leaves their notes as they
are. With no persona chosen their words are kept but not used, and come back when one is chosen
again.

Only turns a person reads carry her character: chat, the digest and retries. The lookup and
discovery workers, whose prose nobody reads, never do. Every word of it is sent, cached, with
each message; the Personality page says roughly what each persona would add, and
`familydb debug cost` what the one in force comes to.
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
# What the family's notes follow her character under, so the model reads them as theirs.
NOTES_HEADER = "## The family's own notes on how you talk\n\n"


@dataclass(frozen=True)
class Persona:
    """Who the assistant is: what she is called, how she talks, and her lines."""

    key: str  # her folder here, and the `persona` setting's value
    name: str  # what she is called
    character: str  # how she talks, as written: {name} wherever her name goes; empty for none
    # Her line by voice event: one wording, or a tuple of several; one she has none for is plain.
    lines: Mapping[str, str | tuple[str, ...]]
    label: str = NAME  # which of her this is: a few words with {name} in them, or just her name
    notes: str = ""  # the family's own notes on how she talks; none ship with her

    @property
    def prompt(self) -> str:
        """Her character as the chat model is told it: the family's notes after it, under a
        header of their own, and her name in both."""
        told = f"{self.character}\n\n{NOTES_HEADER}{self.notes}" if self.notes else self.character
        return told.replace(NAME, self.name)

    @property
    def listed_as(self) -> str:
        """Her label as the family read it, beside the others, with her name in it."""
        return self.label.replace(NAME, self.name)


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
    manifest = tomllib.loads((folder / MANIFEST).read_text("utf-8"))
    name = manifest.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"personas/{key}/{MANIFEST} does not give her a name")
    # Her name is the only thing filled in, so any other brace would be shown as it was written.
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
    """A line as `lines.toml` writes it, one wording or a list of them, as `Persona.lines` keeps
    it: a list as a tuple."""
    if isinstance(written, str):
        return written
    if isinstance(written, list) and all(isinstance(wording, str) for wording in written):
        return tuple(written)
    raise ValueError(f"personas/{key}/{LINES}: {event} is a wording, or a list of wordings")


def active(settings: Settings) -> Persona:
    """The persona in force: the one chosen, with the family's own words laid over hers.

    The name the family call her is her name, and so goes wherever {name} is written. Her
    character is replaced only by the family's rewrite of her; one written for another persona
    is never hers. Their notes on how she talks go with whichever persona is chosen, since they
    are theirs, not a copy of hers. No persona chosen means none at all, whatever the family once
    wrote for her or called her."""
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
