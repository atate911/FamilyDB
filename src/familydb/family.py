"""Who is in the family: the rules for adding somebody and changing them.

The family list is who the bot talks to — a Telegram id on it is somebody allowed to message
the bot — and the web page and the console find people on it by name. So it is not a tool: the
model must never be able to change who may talk to it. The page calls these functions, and
so could any other front end; the rules live here rather than in a form.

- A name belongs to one person, whatever its case, because a name is how the page and the
  console say who is speaking.
- There is always an active admin: the weekend digest is asked as one, and somebody has to be
  able to put things right.
- A change is refused if the person changed since the form was opened, so two people editing
  one profile do not quietly undo each other.
- Somebody is not changed while one of their messages is being answered.
- Taking somebody off the list gives up their unanswered messages, so the retry job does not
  answer for them later.

The same goes for who signs in to the web page, and with what. Each person may have their own
password if their role may sign in (familydb/roles.py), which for now every role may.

- The first admin to choose their own password ends the family password: from then on it opens
  nothing, and everybody signs in as themselves.
- An admin gives everybody else a starting password, made up here and shown once, and each
  person chooses their own the first time they sign in with it.
- Once people sign in as themselves there is always an admin who can, so the page never falls
  back to a shared password nobody meant to bring back, and somebody can always put it right.
"""

from __future__ import annotations

import hashlib
import sqlite3

from familydb import passwords, roles
from familydb.store import logins, members, messages
from familydb.store.db import transaction
from familydb.store.members import Member, Role

TELEGRAM = "telegram"
MAX_NAME = 80
NOBODY = "There is nobody by that number any more."
PASSWORD_SHORT = (
    "That one is {length} characters. It needs at least {least}: a short sentence is easy to "
    "remember and long enough."
)
PASSWORD_LONG = "That is longer than a password needs to be."


class FamilyError(ValueError):
    """What to tell whoever asked, in words they can act on."""


def revision(member: Member) -> str:
    """A short mark of a profile as it stands. The members table keeps no updated time."""
    seen = f"{member.display_name}|{member.role}|{member.active}|{member.channel_user_id}"
    return hashlib.sha256(seen.encode()).hexdigest()[:16]


def clean_name(name: str) -> str:
    """One space between words and none around them, so "Sam " and "Sam" are one person."""
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > MAX_NAME:
        raise FamilyError(f"A name needs 1 to {MAX_NAME} characters.")
    return cleaned


def clean_telegram_id(value: str | None) -> str | None:
    """A Telegram user id, as the bot shows it to somebody it does not know yet, or nothing."""
    value = (value or "").strip()
    if not value:
        return None
    if not value.lstrip("-").isdigit():
        raise FamilyError("A Telegram id is a number. The bot tells people theirs when they write.")
    return value


def _check_role(role: str) -> Role:
    if role not in members.ROLES:
        raise FamilyError("Choose admin, parent or kid.")
    return role  # type: ignore[return-value]


def _name_taken(conn: sqlite3.Connection, name: str, *, besides: int | None = None) -> None:
    for person in members.list_all(conn, active_only=False):
        if person.id != besides and person.display_name.casefold() == name.casefold():
            if person.active:
                raise FamilyError(f"There is already somebody called {person.display_name}.")
            raise FamilyError(
                f"{person.display_name} is on the list but switched off. Switch them back on "
                "instead of adding them again."
            )


def _telegram_taken(conn: sqlite3.Connection, telegram: str, *, besides: int | None) -> None:
    for person in members.list_all(conn, active_only=False):
        if (
            person.id != besides
            and person.channel == TELEGRAM
            and person.channel_user_id == telegram
        ):
            raise FamilyError(f"That Telegram id is already {person.display_name}'s.")


def add(
    conn: sqlite3.Connection, name: str, role: str, *, telegram_id: str | None, now: str
) -> Member:
    """Put somebody on the family list. Raises FamilyError with the reason when it cannot."""
    name, role_ = clean_name(name), _check_role(role)
    telegram = clean_telegram_id(telegram_id)
    try:
        with transaction(conn):
            _name_taken(conn, name)
            if telegram:
                _telegram_taken(conn, telegram, besides=None)
            return members.add(
                conn,
                name,
                role_,
                channel=TELEGRAM if telegram else None,
                channel_user_id=telegram,
                now=now,
            )
    except sqlite3.IntegrityError as exc:  # somebody got there between the check and the write
        raise FamilyError("That name or Telegram id was taken a moment ago. Try again.") from exc


def change(
    conn: sqlite3.Connection,
    member_id: int,
    *,
    name: str,
    role: str,
    active: bool,
    telegram_id: str | None,
    seen: str,
    now: str,
) -> Member:
    """Change somebody, given the `revision` the form was drawn from. Raises FamilyError."""
    name, role_ = clean_name(name), _check_role(role)
    telegram = clean_telegram_id(telegram_id)
    try:
        with transaction(conn):
            current = members.get(conn, member_id)
            if current is None:
                raise FamilyError(NOBODY)
            if revision(current) != seen:
                raise FamilyError(
                    f"{current.display_name} was changed since you opened this. Here they are "
                    "as they are now; make your change again."
                )
            _name_taken(conn, name, besides=member_id)
            if telegram:
                _telegram_taken(conn, telegram, besides=member_id)
            everyone = members.list_all(conn, active_only=False)
            losing_admin = (
                current.active and current.role == "admin" and (not active or role_ != "admin")
            )
            if losing_admin and not any(
                p.id != member_id and p.active and p.role == "admin" for p in everyone
            ):
                raise FamilyError(
                    f"{current.display_name} is the only admin. Make somebody else one first."
                )
            if losing_admin and _last_admin_signing_in(conn, current):
                raise FamilyError(LAST_TO_SIGN_IN.format(name=current.display_name))
            if messages.member_is_being_answered(conn, member_id, now=now):
                raise FamilyError(
                    f"The bot is answering {current.display_name} right now. Try again in a moment."
                )
            # Somebody the bot knew on another channel keeps it; only Telegram is set here.
            channel, channel_user_id = current.channel, current.channel_user_id
            if telegram or current.channel == TELEGRAM:
                channel = TELEGRAM if telegram else None
                channel_user_id = telegram
            changed = members.update_profile(
                conn,
                member_id,
                display_name=name,
                role=role_,
                active=active,
                channel=channel,
                channel_user_id=channel_user_id,
            )
            if current.active and not active:
                messages.give_up_for_member(conn, member_id, now=now)
    except sqlite3.IntegrityError as exc:
        raise FamilyError("That name or Telegram id was taken a moment ago. Try again.") from exc
    assert changed is not None
    return changed


# -- signing in to the web page -----------------------------------------------------------------

LAST_TO_SIGN_IN = (
    "{name} is the only admin who can sign in to the page. Give another admin a password first."
)
ROLE_DOES_NOT_SIGN_IN = "{name} is on the list as a {role}, and a {role} does not sign in."
SWITCHED_OFF = "{name} is switched off. Switch them back on first."
NOT_AN_ADMIN = (
    "Only an admin can be the first to have their own password: they give everybody else theirs."
)
ALREADY_PERSONAL = "People sign in as themselves now. Sign in as yourself to choose a new password."
NO_PASSWORD_TO_TAKE = "{name} has no password to take away."


def check_password(password: str) -> str:
    """A password somebody chose, if it will do. Raises FamilyError with what is wrong."""
    if len(password) < passwords.MIN_LENGTH:
        raise FamilyError(PASSWORD_SHORT.format(length=len(password), least=passwords.MIN_LENGTH))
    if len(password) > passwords.MAX_LENGTH:
        raise FamilyError(PASSWORD_LONG)
    return password


def _may_sign_in(person: Member) -> None:
    if not person.active:
        raise FamilyError(SWITCHED_OFF.format(name=person.display_name))
    if not roles.may(person.role, "sign_in"):
        raise FamilyError(ROLE_DOES_NOT_SIGN_IN.format(name=person.display_name, role=person.role))


def _someone(conn: sqlite3.Connection, member_id: int) -> Member:
    person = members.get(conn, member_id)
    if person is None:
        raise FamilyError(NOBODY)
    return person


def _last_admin_signing_in(conn: sqlite3.Connection, person: Member) -> bool:
    """Whether this person is the one admin who can sign in, so that losing them would leave
    nobody to look after the page, and hand it back to the password the family used to share."""
    signing_in = logins.admins_signing_in(conn)
    return [admin.id for admin in signing_in] == [person.id]


def choose_password(conn: sqlite3.Connection, member_id: int, password: str, *, now: str) -> None:
    """Somebody's own choice of password, in place of the one they signed in with.

    Every other browser signed in as them is signed out by it, since each sign-in carries a mark
    of the password it was made with. Whoever calls this has made sure it is the person
    themselves: the page, by their signing in.
    """
    hashed = passwords.hash_password(check_password(password))  # slow on purpose: not in the lock
    with transaction(conn):
        person = _someone(conn, member_id)
        _may_sign_in(person)
        logins.put(conn, member_id, hashed, temporary=False, now=now, set_by=member_id)


def claim(conn: sqlite3.Connection, member_id: int, password: str, *, now: str) -> Member:
    """An admin choosing their own password while the family still shares one.

    The first to do it ends the shared password for everyone. Somebody let in by that password is
    not known to be anybody in particular, and may do everything on the page, so taking an admin
    who has no password yet gives them nothing the shared one did not. Once an admin signs in as
    themselves, there is nobody left to take: they give everybody else a starting password.
    """
    hashed = passwords.hash_password(check_password(password))
    with transaction(conn):
        person = _someone(conn, member_id)
        _may_sign_in(person)
        if person.role != "admin":
            raise FamilyError(NOT_AN_ADMIN)
        if logins.admin_can_sign_in(conn):
            raise FamilyError(ALREADY_PERSONAL)
        logins.put(conn, member_id, hashed, temporary=False, now=now, set_by=member_id)
    return person


def give_starting_password(
    conn: sqlite3.Connection, member_id: int, *, by: int | None, now: str
) -> str:
    """Make up a password for somebody to sign in with once, and return it, to be shown once.

    They choose their own as soon as they sign in with it. Anywhere they were signed in, they are
    signed out, so this is also what to do for a lost phone. `by` is the admin who asked, or None
    for whoever ran `familydb password` on the server.
    """
    made = passwords.make_up(passwords.STARTING_LENGTH)
    hashed = passwords.hash_password(made)
    with transaction(conn):
        _may_sign_in(_someone(conn, member_id))
        logins.put(conn, member_id, hashed, temporary=True, now=now, set_by=by)
    return made


def remove_login(conn: sqlite3.Connection, member_id: int) -> Member:
    """Take somebody's password away: they cannot sign in, and are signed out wherever they were.

    Never the last admin who can sign in, which would leave nobody to look after the page.
    """
    with transaction(conn):
        person = _someone(conn, member_id)
        if logins.get(conn, member_id) is None:
            raise FamilyError(NO_PASSWORD_TO_TAKE.format(name=person.display_name))
        if _last_admin_signing_in(conn, person):
            raise FamilyError(LAST_TO_SIGN_IN.format(name=person.display_name))
        logins.remove(conn, member_id)
    return person
