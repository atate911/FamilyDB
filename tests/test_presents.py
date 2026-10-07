"""A present is kept from every kid and the grown-up it is for, and the page says whom."""

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


def test_a_present_is_kept_from_every_kid_and_says_so(conn, kids) -> None:
    lego = _present(conn, participants=["Theo"])
    both = _present(conn, "Board game", participants=["Maya", "Theo"])
    kept = presents.of_presents(conn, [lego, both], _people(conn))
    assert kept[lego.id].words == presents.KIDS and kept[lego.id].label == "Hidden from the kids"
    assert kept[both.id].words == presents.KIDS  # a kid is never named: all of them are kept from
    both_kids = {m.id for m in _people(conn) if m.role == "kid"}  # the fixture has a third
    assert kept[lego.id].ids == both_kids == kept[both.id].ids
    # Always, even for a present that is not for a kid, or names nobody.
    anything = _present(conn, "Something nice", participants=["whole family"])
    assert presents.kept_ids(conn, kids["maya"]) == {lego.id, both.id, anything.id}
    assert presents.kept_ids(conn, kids["theo"]) == {lego.id, both.id, anything.id}
    assert presents.kept_ids(conn, kids["sam"]) == set()


def test_a_grown_up_it_is_for_is_kept_from_too(conn, kids) -> None:
    scarf = _present(conn, "Scarf", participants=["Alex"])
    kept = presents.of_presents(conn, [scarf], _people(conn))[scarf.id]
    assert kept.words == "the kids and Alex" and kept.label == "Hidden from the kids and Alex"
    assert presents.is_kept_from(conn, scarf, kids["alex"])
    assert presents.is_kept_from(conn, scarf, kids["maya"])
    assert not presents.is_kept_from(conn, scarf, kids["sam"])


def test_choosing_grown_ups_overrides_the_default_and_never_lets_a_kid_see_one(conn, kids) -> None:
    scarf = _present(conn, "Scarf", participants=["Alex"])
    with db.transaction(conn):
        ideas.set_hidden_from(conn, scarf.id, [])  # a choice: kept from no grown-up
    assert presents.kept_ids(conn, kids["alex"]) == set()
    assert presents.kept_ids(conn, kids["maya"]) == {scarf.id}  # kids by role, never by the list
    assert presents.of_presents(conn, [scarf], _people(conn))[scarf.id].words == presents.KIDS
    with db.transaction(conn):
        ideas.set_hidden_from(conn, scarf.id, [kids["sam"].id])
    assert presents.kept_ids(conn, kids["sam"]) == {scarf.id}
    with db.transaction(conn):
        ideas.set_hidden_from(conn, scarf.id, None)  # back to whom it is for
    assert presents.kept_ids(conn, kids["alex"]) == {scarf.id}


def test_choosing_exactly_the_default_keeps_following_whom_it_is_for(conn, kids) -> None:
    scarf = _present(conn, "Scarf", participants=["Alex"])
    with db.transaction(conn):
        presents.choose(conn, scarf, [kids["alex"].id, kids["maya"].id])  # a kid is ignored
    assert ideas.chosen_hidden_from(conn, [scarf.id]) == {scarf.id: None}
    with db.transaction(conn):
        presents.choose(conn, scarf, [kids["alex"].id, kids["sam"].id])
    assert ideas.chosen_hidden_from(conn, [scarf.id]) == {
        scarf.id: sorted([kids["alex"].id, kids["sam"].id])
    }
    with db.transaction(conn):
        presents.choose(conn, scarf, [])
    assert ideas.chosen_hidden_from(conn, [scarf.id]) == {scarf.id: []}


def test_any_way_of_saying_present_is_a_present(conn, kids) -> None:
    with db.transaction(conn):
        for number, kind in enumerate(["Present", " gifts ", "gift idea"]):
            ideas.insert(conn, title=f"Thing {number}", kind=kind, now=NOW_ISO)
        moved = ideas.insert(conn, title="Plain", kind="outing", now=NOW_ISO)
        ideas.update(conn, moved.id, {"kind": "Presents"})
    assert {idea.kind for idea in ideas.list_all(conn)} == {"gift"}
    assert len(presents.kept_ids(conn, kids["maya"])) == 4


def test_a_to_do_about_a_present_is_kept_from_whoever_the_present_is(conn, kids) -> None:
    from familydb.store import tasks

    watch = _present(conn, "Alex's watch", participants=["Alex"])
    with db.transaction(conn):
        for title, idea_id in (("Order the watch", watch.id), ("Dentist", None)):
            tasks.insert(
                conn,
                title=title,
                notes="",
                owner_id=kids["sam"].id,
                due_at=None,
                preferred_window="",
                operation_key=title,
                channel="console",
                chat_id="c",
                now=NOW_ISO,
                idea_id=idea_id,
            )
    every = tasks.list_all(conn)

    def seen(who):
        return [task.title for task in presents.visible_tasks(conn, every, who)]

    assert seen(kids["sam"]) == ["Order the watch", "Dentist"]
    assert seen(kids["alex"]) == ["Dentist"]  # it is for him
    assert seen(kids["maya"]) == ["Dentist"]
    assert seen(None) == ["Order the watch", "Dentist"]


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
    assert kept.words == presents.KIDS and "Matheo" not in kept.words


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
