"""Stage: the family's firm rules, held by code. A must kept with a rule (`remember`,
docs/MEMORY.md) for anybody coming, or for the whole family, tightens the question's limits
before anything is checked: the tightest limit wins, a rule's indoors or outdoors wins over the
question's, and the tags it avoids are left out. Each limit a rule set remembers which memory set
it, so the reasons name it ("further than m4 allows") and the reply can say why.

Who is coming is read as the question names them (suggest/people.py), with whoever asked. When it
names nobody, or nobody on the family list, everybody's rules hold: a rule kept for somebody who
might come is the safe side.
"""

from __future__ import annotations

from collections.abc import Sequence

from familydb.store.members import Member
from familydb.store.memories import Memory
from familydb.suggest import people as who
from familydb.suggest.types import Constraints

LIMITS = ("max_travel_minutes", "max_cost_level")


def coming(
    constraints: Constraints, people: Sequence[Member], asker: Member | None
) -> set[int] | None:
    """Who the question is about, with whoever asked; None for everybody."""
    if not constraints.participants:
        return None
    named = who.resolve(constraints.participants, people)
    if named.anyone or not named.ids:
        return None
    return set(named.ids) | ({asker.id} if asker is not None else set())


def fold(
    constraints: Constraints,
    held: Sequence[Memory],
    people: Sequence[Member],
    asker: Member | None,
) -> Constraints:
    """`constraints` tightened by the rules (`store.memories.held`) that apply to who is coming."""
    those = coming(constraints, people, asker)
    for memory in held:
        if memory.member_id is not None and those is not None and memory.member_id not in those:
            continue
        rule = memory.rule or {}
        for name in LIMITS:
            limit = rule.get(name)
            current = getattr(constraints, name)
            if limit is not None and (current is None or limit < current):
                setattr(constraints, name, limit)
                constraints.held_by[name] = memory.id
        setting = rule.get("setting")
        # A must wins over the question; between two that disagree, the first kept stands.
        if setting and "setting" not in constraints.held_by:
            constraints.setting = setting
            constraints.held_by["setting"] = memory.id
        for tag in rule.get("avoid", ()):
            if tag not in constraints.avoid:
                constraints.avoid.append(tag)
                constraints.held_by[f"avoid:{tag}"] = memory.id
    return constraints
