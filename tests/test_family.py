"""The family list: adding and changing people, and the rules that keep it usable."""

from __future__ import annotations

import pytest

from familydb import family
from familydb.delivery import lease
from familydb.store import db, members, messages

NOW = "2026-09-20T21:03:00Z"


def _change(conn, person, **given):
    values = {
        "name": person.display_name,
        "role": person.role,
        "active": person.active,
        "telegram_id": person.channel_user_id if person.channel == "telegram" else None,
        "seen": family.revision(person),
        "now": NOW,
    }
    values.update(given)
    return family.change(conn, person.id, **values)


def test_somebody_can_be_added_with_their_telegram_id(conn, family_members) -> None:
    jo = family.add(conn, "  Jo   Smith ", "parent", telegram_id="1003", now=NOW)
    assert jo.display_name == "Jo Smith"  # spaces tidied, so "Jo  Smith" is the same person
    assert (jo.channel, jo.channel_user_id) == ("telegram", "1003")
    assert members.resolve(conn, "telegram", "1003") == jo  # and the bot now answers them


@pytest.mark.parametrize(
    ("name", "telegram", "complaint"),
    [
        ("sam", None, "already somebody called Sam"),
        ("", None, "1 to 80 characters"),
        ("x" * 81, None, "1 to 80 characters"),
        ("Jo", "1001", "already Sam's"),
        ("Jo", "not a number", "is a number"),
    ],
)
def test_what_cannot_be_added_says_why(conn, family_members, name, telegram, complaint) -> None:
    with pytest.raises(family.FamilyError, match=complaint):
        family.add(conn, name, "parent", telegram_id=telegram, now=NOW)


def test_a_switched_off_name_is_switched_back_on_not_added_twice(conn, family_members) -> None:
    alex = family_members["alex"]
    _change(conn, alex, active=False)
    with pytest.raises(family.FamilyError, match="switched off"):
        family.add(conn, "Alex", "parent", telegram_id=None, now=NOW)


def test_somebody_can_be_renamed_and_given_a_telegram_id(conn, family_members) -> None:
    girls = family_members["girls"]
    changed = _change(conn, girls, name="The girls", role="parent", telegram_id="2001")
    assert changed.id == girls.id and changed.display_name == "The girls"
    assert (changed.channel, changed.channel_user_id) == ("telegram", "2001")
    cleared = _change(conn, changed, telegram_id="")
    assert cleared.channel is None and cleared.channel_user_id is None


def test_there_is_always_an_active_admin(conn, family_members) -> None:
    sam = family_members["sam"]  # the only admin
    for given in ({"active": False}, {"role": "parent"}):
        with pytest.raises(family.FamilyError, match="only admin"):
            _change(conn, sam, **given)
    _change(conn, family_members["alex"], role="admin")
    assert _change(conn, members.get(conn, sam.id), role="parent").role == "parent"


def test_a_change_on_top_of_somebody_else_s_is_refused(conn, family_members) -> None:
    alex = family_members["alex"]
    _change(conn, alex, name="Alexandra")  # somebody else saves first
    with pytest.raises(family.FamilyError, match="changed since you opened"):
        _change(conn, alex, role="kid")  # the form still shows the old profile
    assert members.get(conn, alex.id).role == "parent"


def test_nobody_is_changed_while_the_bot_answers_them(conn, family_members, settings, clock):
    from familydb.app import App

    alex = family_members["alex"]
    with db.transaction(conn):
        row = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="u1",
            chat_id="c",
            member_id=alex.id,
            text="hello",
            now=NOW,
        )
    app = App(settings, clock)
    with lease(app, conn, row.id) as owned:
        assert owned
        with pytest.raises(family.FamilyError, match="answering Alex right now"):
            _change(conn, alex, active=False)


def test_switching_somebody_off_gives_up_what_they_left_unanswered(conn, family_members):
    alex = family_members["alex"]
    with db.transaction(conn):
        waiting = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="u2",
            chat_id="c",
            member_id=alex.id,
            text="are you there?",
            now=NOW,
        )
    _change(conn, alex, active=False)
    left = messages.get(conn, waiting.id)
    assert left.give_up and left.error == "member_inactive"
    assert messages.pending(conn, max_retries=3, now=NOW) == []  # the retry job will not answer


@pytest.fixture
def family_members(family):
    return family
