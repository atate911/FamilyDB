"""A present is hidden from exactly the people it names, and the page says whom."""

from __future__ import annotations

import json

import pytest

from familydb import presents
from familydb.store import db, ideas, members
from familydb.tools.registry import ToolContext
from tests.conftest import NOW_ISO


@pytest.fixture
def kids(conn, family):
    """Two kids and two grown-ups: Maya and Theo, with Sam and Alex."""
    with db.transaction(conn):
        maya = members.add(conn, "Maya", "kid", now=NOW_ISO)
        theo = members.add(conn, "Theo", "kid", now=NOW_ISO)
    return {**family, "maya": maya, "theo": theo}


def _present(conn, title="Lego set", **fields):
    with db.transaction(conn):
        return ideas.insert(conn, title=title, kind="gift", now=NOW_ISO, **fields)


def _people(conn):
    return members.list_all(conn)


def test_a_present_is_kept_from_whoever_it_is_for(conn, kids) -> None:
    lego = _present(conn, participants=["Theo"])
    both = _present(conn, "Board game", participants=["Maya", "Theo"])
    kept = presents.of_presents(conn, [lego, both], _people(conn))
    assert kept[lego.id].words == "Theo" and kept[lego.id].label == "Hidden from Theo"
    assert kept[both.id].words == "Maya and Theo"
    assert kept[lego.id].ids == {kids["theo"].id}


def test_a_grown_up_can_be_the_one_it_is_for(conn, kids) -> None:
    scarf = _present(conn, "Scarf", participants=["Alex"])
    assert presents.is_kept_from(conn, scarf, kids["alex"])  # new: Alex is a parent
    assert not presents.is_kept_from(conn, scarf, kids["sam"])
    assert not presents.is_kept_from(conn, scarf, kids["maya"])  # a kid may know, and is told


def test_a_present_for_nobody_named_stays_kept_from_the_kids(conn, kids) -> None:
    """As every present was before somebody could choose: saving one with no name shows nobody's
    kids a surprise by accident."""
    anything = _present(conn, "Something nice", participants=["whole family"])
    kept = presents.of_presents(conn, [anything], _people(conn))[anything.id]
    assert kept.words == presents.KIDS
    assert presents.kept_ids(conn, kids["maya"]) == {anything.id}
    assert presents.kept_ids(conn, kids["alex"]) == set()


def test_choosing_overrides_the_default_even_with_nobody(conn, kids) -> None:
    lego = _present(conn, participants=["Theo"])
    with db.transaction(conn):
        ideas.set_hidden_from(conn, lego.id, [kids["maya"].id, kids["theo"].id])
    assert presents.kept_ids(conn, kids["maya"]) == {lego.id}
    with db.transaction(conn):
        ideas.set_hidden_from(conn, lego.id, [])  # kept from nobody: a choice, not the default
    assert presents.kept_ids(conn, kids["theo"]) == set()
    assert presents.of_presents(conn, [lego], _people(conn))[lego.id].words == ""
    with db.transaction(conn):
        ideas.set_hidden_from(conn, lego.id, None)  # back to whom it is for
    assert presents.kept_ids(conn, kids["theo"]) == {lego.id}


def test_choosing_exactly_the_default_keeps_following_whom_it_is_for(conn, kids) -> None:
    lego = _present(conn, participants=["Theo"])
    with db.transaction(conn):
        presents.choose(conn, lego, [kids["theo"].id])
    assert ideas.chosen_hidden_from(conn, [lego.id]) == {lego.id: None}
    with db.transaction(conn):
        presents.choose(conn, lego, [kids["theo"].id, kids["maya"].id])
    assert ideas.chosen_hidden_from(conn, [lego.id]) == {
        lego.id: sorted([kids["theo"].id, kids["maya"].id])
    }


def test_nothing_but_a_present_is_hidden_and_nobody_in_particular_sees_all(conn, kids) -> None:
    with db.transaction(conn):
        outing = ideas.insert(conn, title="Zoo", kind="outing", participants=["Theo"], now=NOW_ISO)
    lego = _present(conn, participants=["Theo"])
    assert presents.kept_ids(conn, kids["theo"]) == {lego.id}  # not the outing
    assert presents.kept_ids(conn, None) == set()  # the shared password, or a job
    assert not presents.is_kept_from(conn, outing, kids["theo"])


def test_a_name_inside_another_word_is_not_a_name(conn, kids) -> None:
    other = _present(conn, "Hat", participants=["Matheo"])  # not Theo: it names nobody here
    kept = presents.of_presents(conn, [other], _people(conn))[other.id]
    assert kept.words == presents.KIDS and "Theo" not in kept.words


def test_the_words_for_a_list_of_people() -> None:
    assert [presents.join_names(n) for n in (["A"], ["A", "B"], ["A", "B", "C"], [])] == [
        "A",
        "A and B",
        "A, B and C",
        "",
    ]


# -- what the chat sees


def _run(registry, name, values, ctx):
    result = registry.dispatch(name, values, ctx)
    out = json.loads(result.content)
    return {"error": out} if result.is_error else out


def test_the_chat_tells_no_kid_of_a_present_and_no_grown_up_of_their_own(
    conn, settings, clock, kids, registry
) -> None:
    lego = _present(conn, participants=["Theo"])
    scarf = _present(conn, "Scarf", participants=["Alex"])

    def asking(member):
        return ToolContext(conn=conn, settings=settings, clock=clock, member=member)

    def found(member):
        return _run(registry, "search_ideas", {"kind": "gift"}, asking(member))["count"]

    assert found(kids["theo"]) == 0  # a kid is told of none, his own or anyone's
    assert found(kids["maya"]) == 0  # the pages tell a kid of her brother's; the chat never does
    assert found(kids["alex"]) == 1 and found(kids["sam"]) == 2
    assert "error" in _run(registry, "describe_idea", {"id": lego.id}, asking(kids["theo"]))
    assert "error" in _run(
        registry, "update_idea", {"id": scarf.id, "title": "Hat"}, asking(kids["alex"])
    )
    assert ideas.get(conn, scarf.id).title == "Scarf"
    assert "error" in _run(registry, "describe_idea", {"id": lego.id}, asking(kids["maya"]))
    assert "error" not in _run(registry, "describe_idea", {"id": lego.id}, asking(kids["alex"]))


def test_what_the_model_reads_of_an_idea_is_unchanged(conn, kids) -> None:
    """Whom it is hidden from is the page's and the rules', never a field the model is shown, so
    the records it reads (and what it costs to read them) stay as they were."""
    lego = _present(conn, participants=["Theo"])
    assert "hidden_from" not in lego.model_dump(mode="json")
