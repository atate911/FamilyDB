"""Who is coming, read in code against the family list.

An idea keeps who it is for in the family's words ("with the girls", "date night"), and a question
names who is coming in its own ("the kids", "just the two of us"). Compared as text the two missed
each other: "the kids" ruled out an idea kept "with the girls". Here each is read as the people it
means, by name or by group (the kids; the girls or the boys, by what an admin set, every kid when
nothing is; the grown-ups), and an idea fits when the two share somebody. Words it cannot place
(a friend's name, "the neighbours") are still compared as text, as they always were.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from familydb.store.ideas import Idea
from familydb.store.members import Member

# Anybody at all: an idea for the whole family fits whoever is coming.
ANYONE = frozenset(
    {"whole family", "family", "everyone", "everybody", "anyone", "anybody", "all of us", "all"}
)
KIDS = frozenset({"kids", "kiddos", "children", "little ones", "young ones"})
GIRLS = frozenset({"girls", "daughters"})
BOYS = frozenset({"boys", "sons"})
GROWN_UPS = frozenset(
    {
        "adults",
        "grown-ups",
        "grownups",
        "grown ups",
        "parents",
        "mom and dad",
        "mum and dad",
        "two of us",
        "us two",
        "couple",
        "date night",
    }
)
# Words around a name or a group that say nothing of who: "with the girls", "just Sam", "adults
# only".
LEADING = re.compile(r"^(?:(?:with|for|just|only|and|plus|the|our|my|both)\s+)+")
TRAILING = re.compile(r"(?:\s+(?:only|too|as well|alone))+$")
POSSESSIVE = re.compile(r"'s\b")
SPLIT = re.compile(r"\s*(?:,|&|\+|/|\band\b|\bor\b|\bwith\b)\s*")


@dataclass(frozen=True)
class Who:
    """Who some words mean: anybody, or these people, with the words that could not be placed."""

    ids: frozenset[int] = frozenset()
    anyone: bool = False
    unplaced: tuple[str, ...] = ()


def plain(text: str) -> str:
    """Folded, without the words around it that say nothing of who."""
    text = " ".join(text.casefold().replace("\u2019", "'").split())
    text = POSSESSIVE.sub("", text).strip(" .!?;:'\"")
    text = LEADING.sub("", text)
    return TRAILING.sub("", text).strip()


def resolve(phrases: Iterable[str], people: Sequence[Member]) -> Who:
    ids: set[int] = set()
    unplaced: list[str] = []
    for phrase in phrases:
        text = plain(phrase)
        if not text:
            continue
        if text in ANYONE:
            return Who(anyone=True)
        whole = _group(text, people)
        if whole is not None:
            ids |= whole
            continue
        for piece in SPLIT.split(text):
            part = plain(piece)
            if not part:
                continue
            if part in ANYONE:
                return Who(anyone=True)
            found = _group(part, people)
            if found is None:
                unplaced.append(part)
            else:
                ids |= found
    return Who(frozenset(ids), False, tuple(unplaced))


def _names(member: Member) -> set[str]:
    name = plain(member.display_name)
    return {name, name.split()[0]} if name else set()


def _group(text: str, people: Sequence[Member]) -> set[int] | None:
    """The people these words name, or None when they name nobody on the list."""
    found = {member.id for member in people if text in _names(member)}
    if not found:
        kids = [member for member in people if member.role == "kid"]
        if text in KIDS:
            found = {kid.id for kid in kids}
        elif text in GIRLS:
            found = {kid.id for kid in kids if kid.gender != "male"}
        elif text in BOYS:
            found = {kid.id for kid in kids if kid.gender != "female"}
        elif text in GROWN_UPS:
            found = {member.id for member in people if member.role != "kid"}
    return found or None


# Words in an idea's "for" that mean the family, or the kids, or the grown-ups alone.
EVERYONE_WORDS = frozenset({"everyone", "family", "the family", "whole family", "all", "us all"})
KIDS_WORDS = frozenset({"kids", "the kids", "children", "the children", "the girls", "the boys"})
ADULT_WORDS = frozenset({"adults", "the adults", "parents", "the parents", "just us", "date night"})


def with_the_kids(idea: Idea, people: Sequence[Member]) -> bool:
    """Whether an idea is for the kids too: it names nobody (so everyone), the family, the kids,
    or a kid by name."""
    if not idea.participants:
        return True
    kids = {p.display_name.casefold() for p in people if p.role == "kid"}
    for one in idea.participants:
        word = one.casefold().strip()
        if word in EVERYONE_WORDS or word in KIDS_WORDS or word in kids:
            return True
    return False


def just_us(idea: Idea, people: Sequence[Member]) -> bool:
    """Whether an idea is the grown-ups' alone: it names only grown-ups, or says so."""
    if not idea.participants:
        return False
    grown = {p.display_name.casefold() for p in people if p.role != "kid"}
    return all(
        one.casefold().strip() in ADULT_WORDS or one.casefold().strip() in grown
        for one in idea.participants
    )
