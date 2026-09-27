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


def test_a_birthday_and_a_gender_are_kept_until_changed(conn, family_members) -> None:
    kid = family.add(conn, "Mia", "kid", telegram_id=None, now=NOW)
    mia = _change(conn, kid, birth_date="2017-03-14", gender="female")
    assert (mia.birth_date, mia.gender) == ("2017-03-14", "female")
    assert family.revision(mia) != family.revision(kid)  # a form drawn before is refused
    # A change that says nothing of them (linking Telegram, say) keeps both.
    mia = _change(conn, mia, telegram_id="1009")
    assert (mia.birth_date, mia.gender) == ("2017-03-14", "female")
    # An empty one takes it away.
    mia = _change(conn, mia, birth_date="", gender="")
    assert (mia.birth_date, mia.gender) == (None, None)


@pytest.mark.parametrize(
    ("birth_date", "gender", "complaint"),
    [
        ("14/03/2017", None, "is a date"),
        ("2027-01-01", None, "not a day that has been"),
        ("1850-01-01", None, "not a day that has been"),
        (None, "robot", "male or female"),
    ],
)
def test_a_birthday_or_gender_that_cannot_be_is_refused(
    conn, family_members, birth_date, gender, complaint
) -> None:
    kid = family.add(conn, "Mia", "kid", telegram_id=None, now=NOW)
    given = {"birth_date": birth_date} if birth_date else {"gender": gender}
    with pytest.raises(family.FamilyError, match=complaint):
        _change(conn, kid, **given)


def test_an_age_and_the_next_birthday_are_worked_out_by_code() -> None:
    from datetime import date

    today = date(2026, 9, 27)
    assert family.age_on("2017-09-28", today) == 8  # the day before
    assert family.age_on("2017-09-27", today) == 9  # on the day
    assert family.age_on(None, today) is None
    assert family.next_birthday("2017-09-27", today) == today
    assert family.next_birthday("2017-03-14", today) == date(2027, 3, 14)
    assert family.next_birthday("2016-02-29", today) == date(2027, 3, 1)  # no 29th in 2027
    assert family.next_birthday("2016-02-29", date(2027, 12, 1)) == date(2028, 2, 29)
