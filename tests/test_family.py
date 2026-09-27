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


# -- linking Telegram by a link -----------------------------------------------------------------


def _at(hours: float = 0):
    from datetime import UTC, datetime, timedelta

    return datetime(2026, 9, 20, 21, 3, tzinfo=UTC) + timedelta(hours=hours)


def test_a_link_links_whoever_opens_it_to_its_person_once(conn, family_members) -> None:
    from familydb.store import invites

    jo = family.add(conn, "Jo", "parent", telegram_id=None, now=NOW)
    code = family.invite(conn, jo.id, by=family_members["sam"].id, now=_at())
    assert family.is_invite_code(code) and len(code) <= 64  # Telegram's start parameter
    kept = conn.execute("SELECT code_hash FROM telegram_invites WHERE member_id = ?", (jo.id,))
    assert kept.fetchone()["code_hash"] == invites.digest(code) != code  # only a hash is kept
    linked = family.accept_invite(conn, code, telegram_id="1003", now=_at(1))
    assert (linked.id, linked.channel, linked.channel_user_id) == (jo.id, "telegram", "1003")
    assert members.resolve(conn, "telegram", "1003") == linked  # the bot answers them now
    with pytest.raises(family.InviteRefused) as spent:
        family.accept_invite(conn, code, telegram_id="1004", now=_at(2))
    assert spent.value.why == "stale"  # used once, and gone


def test_a_link_past_its_day_or_replaced_opens_nothing(conn, family_members) -> None:
    jo = family.add(conn, "Jo", "parent", telegram_id=None, now=NOW)
    old = family.invite(conn, jo.id, by=None, now=_at())
    new = family.invite(conn, jo.id, by=None, now=_at())
    with pytest.raises(family.InviteRefused):
        family.accept_invite(conn, old, telegram_id="1003", now=_at(1))  # replaced by the new
    with pytest.raises(family.InviteRefused):
        family.accept_invite(conn, new, telegram_id="1003", now=_at(family.INVITE_HOURS))
    assert members.resolve(conn, "telegram", "1003") is None
    for nonsense in ("", "short", "x" * 65, "has spaces in it, plenty", "../../etc/passwd-ok"):
        with pytest.raises(family.InviteRefused):
            family.accept_invite(conn, nonsense, telegram_id="1003", now=_at())


def test_a_link_opened_by_a_telegram_already_on_the_list_is_left_for_its_person(
    conn, family_members
) -> None:
    """An admin trying the link on their own phone must not move their Telegram to somebody
    else, nor use the link up."""
    jo = family.add(conn, "Jo", "parent", telegram_id=None, now=NOW)
    code = family.invite(conn, jo.id, by=None, now=_at())
    with pytest.raises(family.InviteRefused) as taken:
        family.accept_invite(conn, code, telegram_id="1001", now=_at())  # Sam's
    assert (taken.value.why, taken.value.owner) == ("taken", "Sam")
    assert members.resolve(conn, "telegram", "1001").display_name == "Sam"
    assert family.accept_invite(conn, code, telegram_id="1003", now=_at()).id == jo.id


def test_no_link_for_somebody_switched_off_or_not_there(conn, family_members) -> None:
    jo = family.add(conn, "Jo", "parent", telegram_id=None, now=NOW)
    code = family.invite(conn, jo.id, by=None, now=_at())
    _change(conn, jo, active=False)
    with pytest.raises(family.InviteRefused):
        family.accept_invite(conn, code, telegram_id="1003", now=_at())
    with pytest.raises(family.FamilyError, match="switched off"):
        family.invite(conn, jo.id, by=None, now=_at())
    with pytest.raises(family.FamilyError, match="nobody by that number"):
        family.invite(conn, 999, by=None, now=_at())


def test_links_past_their_day_are_forgotten_whatever_is_opened(conn, family_members) -> None:
    """A refusal undoes its own transaction, so forgetting expired links has one of its own."""
    jo = family.add(conn, "Jo", "parent", telegram_id=None, now=NOW)
    family.invite(conn, jo.id, by=None, now=_at())
    with pytest.raises(family.InviteRefused):
        family.accept_invite(conn, "x" * 32, telegram_id="1003", now=_at(family.INVITE_HOURS))
    assert conn.execute("SELECT count(*) FROM telegram_invites").fetchone()[0] == 0


# -- taking somebody off for good ------------------------------------------------------------------


def test_every_column_that_points_at_a_member_is_named_for_taking_somebody_off(conn) -> None:
    """A table added later that points at a member must say what happens to it, or taking
    somebody off would stop on it."""
    pointing = {
        (table, fk["from"])
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        for fk in conn.execute(f"PRAGMA foreign_key_list({table})")
        if fk["table"] == "members"
    }
    assert pointing == set(members.POINTING_AT)


def test_somebody_taken_off_leaves_what_they_said_unnamed_and_takes_what_was_theirs(
    conn, family_members
) -> None:
    from familydb.store import ideas, locations, logins, memories

    alex, sam = family_members["alex"], family_members["sam"]
    with db.transaction(conn):
        said = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="9",
            chat_id="c",
            member_id=alex.id,
            text="we should try the ramen place",
            now=NOW,
        )
        idea = ideas.insert(conn, title="Ramen", kind="restaurant", suggested_by=alex.id, now=NOW)
        about = memories.insert(
            conn,
            member_id=alex.id,
            category="food",
            fact="Alex is vegetarian",
            firm=True,
            inferred=False,
            until=None,
            source_message_id=said.id,
            said_by=alex.id,
            now=NOW,
        )
        told = memories.insert(
            conn,
            member_id=None,
            category="food",
            fact="The family likes ramen",
            firm=False,
            inferred=True,
            until=None,
            source_message_id=said.id,
            said_by=alex.id,
            now=NOW,
        )
        conn.execute("UPDATE memories SET replaced_by = ? WHERE id = ?", (about.id, told.id))
        locations.record(conn, alex.id, lat=1.0, lon=2.0, live=False, now=NOW)
    family.give_starting_password(conn, alex.id, by=sam.id, now=NOW)
    family.invite(conn, alex.id, by=sam.id, now=_at())

    gone = family.remove(conn, alex.id, by=sam.id, seen=family.revision(alex), now=NOW)
    assert gone.display_name == "Alex" and members.get(conn, alex.id) is None
    kept = messages.get(conn, said.id)
    assert kept.text == "we should try the ramen place" and kept.member_id is None
    assert ideas.get(conn, idea.id).suggested_by is None
    # What she knew about Alex went; what Alex told her about the family stays, unnamed.
    assert [row["id"] for row in conn.execute("SELECT id FROM memories")] == [told.id]
    assert conn.execute("SELECT said_by, replaced_by FROM memories").fetchone()[:] == (None, None)
    assert logins.get(conn, alex.id) is None
    for table in ("member_locations", "telegram_invites"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table
    # The name is free again, for somebody new.
    family.add(conn, "Alex", "parent", telegram_id="1002", now=NOW)


def test_nobody_takes_themselves_or_the_last_admin_off(conn, family_members) -> None:
    sam, alex = family_members["sam"], family_members["alex"]
    with pytest.raises(family.FamilyError, match="yourself"):
        family.remove(conn, alex.id, by=alex.id, seen=family.revision(alex), now=NOW)
    with pytest.raises(family.FamilyError, match="only admin"):
        family.remove(conn, sam.id, by=alex.id, seen=family.revision(sam), now=NOW)
    with pytest.raises(family.FamilyError, match="changed since"):
        family.remove(conn, alex.id, by=sam.id, seen="stale", now=NOW)
    assert members.get(conn, sam.id) and members.get(conn, alex.id)
