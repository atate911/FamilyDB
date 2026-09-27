"""The rules of the kids' wish lists (docs/WISHES.md), held in code."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from familydb import wish_service as ws
from familydb.errors import ToolError
from familydb.store import db, members
from tests.conftest import NOW_ISO, TZ

NOW = datetime(2026, 9, 20, 14, 3, tzinfo=TZ)


@pytest.fixture
def kids(conn, family):
    with db.transaction(conn):
        chloe = members.add(conn, "Chloe", "kid", now=NOW_ISO)
    mia = members.get(conn, family["girls"].id)
    return {"mia": mia, "chloe": chloe, "parent": family["alex"]}


def _add(conn, settings, who, title, *, by=None, now=NOW, **given):
    return ws.add(conn, settings, by=by or who, owner=who, title=title, now=now, **given)


def _decline(conn, settings, kids, wish_id, now=NOW):
    return ws.answer(conn, settings, by=kids["parent"], wish_id=wish_id, granted=False, now=now)


def test_a_wish_goes_to_the_bottom_of_her_list(conn, settings, kids) -> None:
    first = _add(conn, settings, kids["mia"], "iPhone", topic="phone")
    second = _add(conn, settings, kids["mia"], "Roblox", topic="roblox")
    assert (first.result, second.result) == ("added", "added")
    assert (first.wish.rank, second.wish.rank) == (1, 2)
    assert second.compact() == {
        "result": "added",
        "wish": {"id": second.wish.id, "title": "Roblox", "occasion": None},
        "asked_today": 2,
    }


def test_the_same_thing_twice_is_one_wish(conn, settings, kids) -> None:
    cat = _add(conn, settings, kids["mia"], "A cat", topic="pet")
    dog = _add(conn, settings, kids["mia"], "A dog", topic="pet")  # materially the same ask
    assert dog.result == "duplicate" and dog.wish.id == cat.wish.id
    # With no topic to say so, nearly the same title is the backstop.
    again = _add(conn, settings, kids["mia"], "a cat!")
    assert again.result == "duplicate"
    # The same thing may also be flagged for Christmas: several lists are fine.
    assert _add(conn, settings, kids["mia"], "A cat", topic="pet", occasion="christmas").result == (
        "added"
    )


def test_not_this_time_climbs_the_ladder(conn, settings, kids) -> None:
    now = NOW
    locks = []
    for _ in range(6):
        asked = _add(conn, settings, kids["mia"], "A cat", topic="pet", now=now)
        assert asked.result == "added"
        declined = _decline(conn, settings, kids, asked.wish.id, now=now)
        until = datetime.fromisoformat(declined.locked_until.replace("Z", "+00:00"))
        locks.append((until.astimezone(TZ).date() - now.date()).days)
        now = until + timedelta(hours=1)  # asked again the moment it unlocks
    assert locks == [14, 30, 90, 120, 365, 365]


def test_a_locked_thing_is_refused_every_day_but_welcome_for_christmas(
    conn, settings, kids
) -> None:
    cat = _add(conn, settings, kids["mia"], "A cat", topic="pet")
    _decline(conn, settings, kids, cat.wish.id)
    dog = _add(conn, settings, kids["mia"], "A dog", topic="pet", now=NOW + timedelta(days=3))
    assert dog.result == "locked" and dog.compact()["locked_until"] == "2026-10-04"
    assert dog.compact()["times_declined"] == 1
    # A new title with no topic to give it away is caught by the title.
    assert _add(conn, settings, kids["mia"], "A cat!").result == "locked"
    for_christmas = _add(conn, settings, kids["mia"], "A dog", topic="pet", occasion="christmas")
    assert for_christmas.result == "added"
    # A parent may put it back on her list after all.
    assert _add(conn, settings, kids["mia"], "A cat", topic="pet", by=kids["parent"]).result == (
        "added"
    )
    # Her sister's lock is not hers.
    assert _add(conn, settings, kids["chloe"], "A cat", topic="pet").result == "added"


def test_an_occasion_no_lasts_until_the_occasion_has_passed(conn, settings, kids) -> None:
    with db.transaction(conn):
        conn.execute("UPDATE members SET birth_date = '2017-11-02' WHERE id = ?", (kids["mia"].id,))
    mia = members.get(conn, kids["mia"].id)
    xmas = _add(conn, settings, mia, "Drone", topic="drone", occasion="christmas")
    bday = _add(conn, settings, mia, "Drone", topic="drone", occasion="birthday")
    no_for_christmas = _decline(conn, settings, kids, xmas.wish.id)
    assert no_for_christmas.locked_until.startswith("2026-12-26")
    assert no_for_christmas.refusal_rung is None
    assert _decline(conn, settings, kids, bday.wish.id).locked_until.startswith("2026-11-03")
    # Nothing is locked on her everyday list by it.
    assert _add(conn, settings, mia, "Drone", topic="drone").result == "added"


def test_a_few_everyday_wishes_a_day_then_restraint(conn, settings, kids) -> None:
    things = ["Slime", "Lego", "Kite", "Paints", "Roller skates", "Headphones"]
    for thing in things[: ws.WISH_DAILY_COUNT]:
        assert _add(conn, settings, kids["mia"], thing).result == "added"
    sixth = _add(conn, settings, kids["mia"], things[5])
    assert sixth.result == "too_many" and sixth.compact()["asked_today"] == 6
    assert sixth.wish.status == "turned_away" and sixth.wish.concern == "too_many"
    # Occasion lists have no daily count.
    assert _add(conn, settings, kids["mia"], "Bike", topic="bike", occasion="birthday").result == (
        "added"
    )
    # Tomorrow is a new day.
    tomorrow = NOW + timedelta(days=1)
    assert _add(conn, settings, kids["mia"], "Yo-yo", now=tomorrow).result == "added"


def test_a_parent_adding_for_her_is_not_counted_against_her_restraint(conn, settings, kids) -> None:
    things = ["Slime", "Lego", "Kite", "Paints", "Roller skates", "Headphones", "Yo-yo"]
    for thing in things:
        assert _add(conn, settings, kids["mia"], thing, by=kids["parent"]).result == "added"


def test_her_order_is_hers_and_moving_is_free(conn, settings, kids) -> None:
    ids = [_add(conn, settings, kids["mia"], t, topic=t).wish.id for t in ("a", "b", "c")]
    ws.move(conn, settings, by=kids["mia"], wish_id=ids[2], position=1, now=NOW)
    order = [w.id for w in ws.wishes.open_list(conn, kids["mia"].id, None)]
    assert order == [ids[2], ids[0], ids[1]]
    # Flagged for her birthday, it leaves the everyday list and goes to the bottom of the other.
    moved = ws.move(conn, settings, by=kids["mia"], wish_id=ids[0], occasion="birthday", now=NOW)
    assert (moved.occasion, moved.rank) == ("birthday", 1)
    assert [w.id for w in ws.wishes.open_list(conn, kids["mia"].id, None)] == [ids[2], ids[1]]
    assert [w.rank for w in ws.wishes.open_list(conn, kids["mia"].id, None)] == [1, 2]


def test_moving_onto_the_everyday_list_is_held_to_its_rules(conn, settings, kids) -> None:
    cat = _add(conn, settings, kids["mia"], "A cat", topic="pet")
    _decline(conn, settings, kids, cat.wish.id)
    xmas = _add(conn, settings, kids["mia"], "A kitten", topic="pet", occasion="christmas")
    with pytest.raises(ToolError, match="locked"):
        ws.move(conn, settings, by=kids["mia"], wish_id=xmas.wish.id, occasion=None, now=NOW)
    # And not a way round the daily count.
    parked = [
        _add(conn, settings, kids["mia"], f"x{n}", topic=f"x{n}", occasion="birthday").wish.id
        for n in range(ws.WISH_DAILY_COUNT + 1)
    ]
    for wish_id in parked[:4]:  # the declined cat was one ask today already
        ws.move(conn, settings, by=kids["mia"], wish_id=wish_id, occasion=None, now=NOW)
    with pytest.raises(ToolError, match="enough everyday wishes"):
        ws.move(conn, settings, by=kids["mia"], wish_id=parked[4], occasion=None, now=NOW)


def test_too_much_moving_in_a_day_is_refused(conn, settings, kids, monkeypatch) -> None:
    monkeypatch.setattr(ws, "WISH_MOVES_PER_DAY", 2)
    wish = _add(conn, settings, kids["mia"], "a", topic="a").wish
    ws.move(conn, settings, by=kids["mia"], wish_id=wish.id, position=1, now=NOW)
    ws.move(conn, settings, by=kids["mia"], wish_id=wish.id, position=1, now=NOW)
    with pytest.raises(ToolError, match="a lot of moving"):
        ws.move(conn, settings, by=kids["mia"], wish_id=wish.id, position=1, now=NOW)


def test_a_sister_cannot_touch_her_list_or_answer_it(conn, settings, kids) -> None:
    wish = _add(conn, settings, kids["mia"], "iPad", topic="ipad").wish
    with pytest.raises(ToolError, match="somebody else's"):
        _add(conn, settings, kids["mia"], "Slime", by=kids["chloe"])
    for change in (
        lambda: ws.move(conn, settings, by=kids["chloe"], wish_id=wish.id, position=1, now=NOW),
        lambda: ws.withdraw(conn, by=kids["chloe"], wish_id=wish.id, now=NOW),
        lambda: ws.edit(conn, by=kids["chloe"], wish_id=wish.id, title="Nope", now=NOW),
    ):
        with pytest.raises(ToolError, match="somebody else's"):
            change()
    with pytest.raises(ToolError, match="only a parent"):
        ws.answer(conn, settings, by=kids["mia"], wish_id=wish.id, granted=True, now=NOW)


def test_withdrawing_and_granting_close_the_gap_in_her_order(conn, settings, kids) -> None:
    ids = [_add(conn, settings, kids["mia"], t, topic=t).wish.id for t in ("a", "b", "c")]
    ws.withdraw(conn, by=kids["mia"], wish_id=ids[0], now=NOW)
    ws.answer(conn, settings, by=kids["parent"], wish_id=ids[1], granted=True, note="Yes!", now=NOW)
    left = ws.wishes.open_list(conn, kids["mia"].id, None)
    assert [(w.id, w.rank) for w in left] == [(ids[2], 1)]
    # Withdrawn locks nothing: she may ask again.
    assert _add(conn, settings, kids["mia"], "a", topic="a").result == "added"


def test_a_new_title_does_not_escape_a_lockout(conn, settings, kids) -> None:
    wish = _add(conn, settings, kids["mia"], "A cat", topic="pet").wish
    edited = ws.edit(conn, by=kids["mia"], wish_id=wish.id, title="A hamster", now=NOW)
    assert edited.topic == "pet" and edited.revision == wish.revision + 1


def test_a_turned_away_ask_is_kept_and_ask_a_parent_is_limited(conn, settings, kids) -> None:
    rude = ws.turn_away(
        conn,
        settings,
        owner=kids["mia"],
        summary="something inappropriate",
        concern="inappropriate",
        reviewable=True,
        now=NOW,
    )
    assert rude.tell_parents and not rude.may_ask_parent  # never offered for this
    offers = [
        ws.turn_away(
            conn,
            settings,
            owner=kids["mia"],
            summary=f"more screen time {n}",
            concern="rule",
            reviewable=True,
            now=NOW,
        )
        for n in range(3)
    ]
    assert [o.may_ask_parent for o in offers] == [True, True, False]
    assert not any(o.tell_parents for o in offers)
    asked = ws.ask_parent(conn, by=kids["mia"], wish_id=offers[0].wish.id, now=NOW)
    assert asked.parent_review == "asked"
    with pytest.raises(ToolError, match="nothing to ask"):
        ws.ask_parent(conn, by=kids["mia"], wish_id=offers[0].wish.id, now=NOW)
    not_reviewable = ws.turn_away(
        conn,
        settings,
        owner=kids["chloe"],
        summary="Mia has more",
        concern="sibling",
        reviewable=False,
        now=NOW,
    )
    assert not not_reviewable.may_ask_parent
    # A parent may still say yes to what was turned away.
    yes = ws.answer(
        conn, settings, by=kids["parent"], wish_id=offers[0].wish.id, granted=True, now=NOW
    )
    assert yes.status == "granted"
