"""Who is in the family: the rules for adding, changing and taking off somebody, and for how each
signs in.

The family list is who the bot talks to, so it is not a tool: the model must never change who may
talk to it. Rules held here, not in a form:

- A name belongs to one person whatever its case. - There is always an active admin (the weekend
digest is asked as one), and once people sign in as themselves an admin who can, so the page
never falls back to a shared password. - A change on a form drawn before somebody else saved is
refused; nobody is changed while one of their messages is being answered; taking somebody off
gives up their unanswered messages. - The first admin's own password ends the family password; an
admin gives everybody else a made-up starting password, shown once, which they replace on first
sign in. - An admin's link (`invite`) links a Telegram when opened and Start is pressed
(`accept_invite`). The family chose that knowing whoever opens it first is taken for that person,
so it works once, for a day, only for somebody on the list and switched on, and never moves a
Telegram already somebody else's.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from familydb import audience, passwords, roles
from familydb.dates import age_on as age_on
from familydb.dates import next_birthday as next_birthday
from familydb.dates import utc_iso
from familydb.store import invites, logins, members, messages, plans, tasks
from familydb.store import pins as pin_store
from familydb.store import push as push_store
from familydb.store.db import transaction
from familydb.store.members import Gender, Member, Role

log = logging.getLogger(__name__)

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
    seen = (
        f"{member.display_name}|{member.role}|{member.active}|{member.channel_user_id}"
        f"|{member.birth_date}|{member.gender}"
    )
    return hashlib.sha256(seen.encode()).hexdigest()[:16]


KEEP: Any = object()
OLDEST = 1900


def clean_birth_date(value: str | None, *, today: date) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        born = date.fromisoformat(value)
    except ValueError:
        raise FamilyError("A birthday is a date, such as 2017-03-14.") from None
    if born > today or born.year < OLDEST:
        raise FamilyError("That birthday is not a day that has been.")
    return born.isoformat()


def clean_gender(value: str | None) -> Gender | None:
    value = (value or "").strip().lower()
    if not value:
        return None
    if value not in members.GENDERS:
        raise FamilyError("Choose male or female, or leave it unsaid.")
    return value  # type: ignore[return-value]


def clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > MAX_NAME:
        raise FamilyError(f"A name needs 1 to {MAX_NAME} characters.")
    return cleaned


def clean_telegram_id(value: str | None) -> str | None:
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


def _telegram_owner(
    conn: sqlite3.Connection, telegram: str, *, besides: int | None
) -> Member | None:
    for person in members.list_all(conn, active_only=False):
        if (
            person.id != besides
            and person.channel == TELEGRAM
            and person.channel_user_id == telegram
        ):
            return person
    return None


def _telegram_taken(conn: sqlite3.Connection, telegram: str, *, besides: int | None) -> None:
    owner = _telegram_owner(conn, telegram, besides=besides)
    if owner is not None:
        raise FamilyError(f"That Telegram id is already {owner.display_name}'s.")


def add(
    conn: sqlite3.Connection, name: str, role: str, *, telegram_id: str | None, now: str
) -> Member:
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
    except sqlite3.IntegrityError as exc:
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
    birth_date: Any = KEEP,
    gender: Any = KEEP,
) -> Member:
    """Change somebody given the `revision` the form was drawn from. A birthday or gender not given
    (`KEEP`) stays; an empty one is taken away.
    """
    name, role_ = clean_name(name), _check_role(role)
    telegram = clean_telegram_id(telegram_id)
    today = datetime.fromisoformat(now.replace("Z", "+00:00")).date()
    born = birth_date if birth_date is KEEP else clean_birth_date(birth_date, today=today)
    gender_ = gender if gender is KEEP else clean_gender(gender)
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
                birth_date=current.birth_date if born is KEEP else born,
                gender=current.gender if gender_ is KEEP else gender_,
            )
            if current.active and not active:
                messages.give_up_for_member(conn, member_id, now=now)
    except sqlite3.IntegrityError as exc:
        raise FamilyError("That name or Telegram id was taken a moment ago. Try again.") from exc
    assert changed is not None
    return changed


def remove(
    conn: sqlite3.Connection, member_id: int, *, by: int | None, seen: str, now: str
) -> Member:
    """Take somebody off the list for good (store/members.py `POINTING_AT` says what goes and what
    stays).

    Never the last admin or last admin who can sign in, nor whoever is asking, nor while the bot
    is answering them, nor on a stale form.
    """
    with transaction(conn):
        current = members.get(conn, member_id)
        if current is None:
            raise FamilyError(NOBODY)
        if revision(current) != seen:
            raise FamilyError(
                f"{current.display_name} was changed since you opened this. Here they are "
                "as they are now; decide again."
            )
        if by is not None and by == member_id:
            raise FamilyError(NOT_YOURSELF)
        everyone = members.list_all(conn, active_only=False)
        if current.role == "admin" and current.active:
            if not any(p.id != member_id and p.active and p.role == "admin" for p in everyone):
                raise FamilyError(
                    f"{current.display_name} is the only admin. Make somebody else one first."
                )
            if _last_admin_signing_in(conn, current):
                raise FamilyError(LAST_TO_SIGN_IN.format(name=current.display_name))
        if messages.member_is_being_answered(conn, member_id, now=now):
            raise FamilyError(
                f"The bot is answering {current.display_name} right now. Try again in a moment."
            )
        messages.give_up_for_member(conn, member_id, now=now)
        if current.channel == TELEGRAM and current.channel_user_id:
            # Their private chat, whose id is theirs, falls silent: no reminder, follow-up, plan
            # check or queued message.
            private = current.channel_user_id
            tasks.cancel_in_chat(conn, TELEGRAM, private, now)
            plans.leave_chat(conn, TELEGRAM, private)
            messages.cancel_unsent(conn, TELEGRAM, private, now=now)
        web_own = audience.private_chat(member_id)
        tasks.cancel_in_chat(conn, "web", web_own, now)
        # Their own things to do asked for on the page or in somebody's chat: with the name taken
        # off, each would be nobody's, which reads as everyone's (routing.for_task), and their
        # errand would go to the family's chat. A group's stays the family's, as before.
        tasks.cancel_owned_by(conn, member_id, now)
        plans.leave_chat(conn, "web", web_own)
        messages.cancel_unsent(conn, "web", web_own, now=now)
        touched = members.erase(conn, member_id)
    log.info("member %s taken off the list for good: %s", member_id, touched)
    return current


NOT_YOURSELF = "You cannot take yourself off the list. Another admin can."


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
    """Whether this is the one admin who can sign in, so losing them would hand the page back to the
    shared password.
    """
    signing_in = logins.admins_signing_in(conn)
    return [admin.id for admin in signing_in] == [person.id]


NOT_A_LOOK = "That is not one of the looks on the Look page."


def choose_look(conn: sqlite3.Connection, member_id: int, value: str) -> str:
    """Keep somebody's look with them, so it follows them to every phone and computer they sign in
    on. `value` is what the Look page's form holds as the look cookie does ("rail.dark"); one that
    names no look is refused. Only ever for the person signed in: the page passes their own id."""
    from familydb.web import looks  # the looks are the page's; this checks a choice against them

    key, _, mode = value.partition(".")
    chosen = looks.choose(key, mode)
    if chosen is None:
        raise FamilyError(NOT_A_LOOK)
    kept = looks.value(*chosen)
    with transaction(conn):
        _someone(conn, member_id)
        members.set_look(conn, member_id, kept)
    return kept


def choose_password(conn: sqlite3.Connection, member_id: int, password: str, *, now: str) -> None:
    """Somebody's own choice of password. Every other browser signed in as them is signed out, since
    each sign-in carries a mark of its password. The caller has made sure it is the person.
    """
    hashed = passwords.hash_password(check_password(password))
    with transaction(conn):
        person = _someone(conn, member_id)
        _may_sign_in(person)
        logins.put(conn, member_id, hashed, temporary=False, now=now, set_by=member_id)


def claim(conn: sqlite3.Connection, member_id: int, password: str, *, now: str) -> Member:
    """An admin choosing their own password while the family still shares one: the first to do it
    ends the shared password for everyone.

    Whoever is let in by the shared password may do everything on the page, so taking an admin
    with no password yet gives nothing it did not.
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
    """Make up a password to sign in with once, returned to be shown once; they choose their own on
    signing in. Signs them out everywhere, so it is also the answer to a lost phone. `by` is the
    asking admin, or None for `familydb password`.
    """
    made = passwords.make_up(passwords.STARTING_LENGTH)
    hashed = passwords.hash_password(made)
    with transaction(conn):
        _may_sign_in(_someone(conn, member_id))
        logins.put(conn, member_id, hashed, temporary=True, now=now, set_by=by)
    return made


def remove_login(conn: sqlite3.Connection, member_id: int) -> Member:
    """Take somebody's password away and sign them out. Never the last admin who can sign in."""
    with transaction(conn):
        person = _someone(conn, member_id)
        if logins.get(conn, member_id) is None:
            raise FamilyError(NO_PASSWORD_TO_TAKE.format(name=person.display_name))
        if _last_admin_signing_in(conn, person):
            raise FamilyError(LAST_TO_SIGN_IN.format(name=person.display_name))
        logins.remove(conn, member_id)
    return person


# Long and random enough not to be guessed, short enough for Telegram's start parameter (64 of A-Z,
# a-z, 0-9, _ and -).
INVITE_HOURS = 24
INVITE_BYTES = 24
INVITE_CODE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


class InviteRefused(FamilyError):
    """A link that did nothing: `stale` (unknown, used, past its time, or for somebody switched off)
    or `taken` (this Telegram is already `owner`'s).
    """

    def __init__(self, why: str, owner: str | None = None) -> None:
        super().__init__(why)
        self.why = why
        self.owner = owner


def invite(conn: sqlite3.Connection, member_id: int, *, by: int | None, now: datetime) -> str:
    """Make the code of a link that links whoever opens it to this person's Telegram, shown once;
    replaces any earlier one.
    """
    code = secrets.token_urlsafe(INVITE_BYTES)
    with transaction(conn):
        person = _someone(conn, member_id)
        if not person.active:
            raise FamilyError(SWITCHED_OFF.format(name=person.display_name))
        invites.forget_expired(conn, utc_iso(now))
        invites.put(
            conn,
            member_id,
            invites.digest(code),
            made_by=by,
            now=utc_iso(now),
            expires=utc_iso(now + timedelta(hours=INVITE_HOURS)),
        )
    return code


def is_invite_code(text: str) -> bool:
    return 16 <= len(text) <= 64 and set(text) <= INVITE_CODE


def accept_invite(
    conn: sqlite3.Connection, code: str, *, telegram_id: str, now: datetime
) -> Member:
    """Link this Telegram to whoever the link was made for, and use it up. Raises InviteRefused when
    it does nothing; a Telegram already somebody else's is left as it was.
    """
    telegram = clean_telegram_id(telegram_id)
    if telegram is None or not is_invite_code(code):
        raise InviteRefused("stale")
    stamp = utc_iso(now)
    with transaction(conn):
        invites.forget_expired(conn, stamp)
    try:
        with transaction(conn):
            found = invites.find(conn, invites.digest(code))
            if found is None:
                raise InviteRefused("stale")
            person = members.get(conn, found.member_id)
            if person is None or not person.active:
                raise InviteRefused("stale")
            owner = _telegram_owner(conn, telegram, besides=person.id)
            if owner is not None:
                raise InviteRefused("taken", owner.display_name)
            linked = members.update_profile(
                conn,
                person.id,
                display_name=person.display_name,
                role=person.role,
                active=person.active,
                channel=TELEGRAM,
                channel_user_id=telegram,
                birth_date=person.birth_date,
                gender=person.gender,
            )
            invites.remove(conn, found.code_hash)
    except sqlite3.IntegrityError as exc:
        raise InviteRefused("taken") from exc
    assert linked is not None
    return linked


# -- notifications on somebody's own devices (push.py)

MAX_ENDPOINT = 1000


class PushRefused(ValueError):
    """Why a device was not turned on: not a browser's push address, or keys that are not."""


def subscribe_push(
    conn: sqlite3.Connection,
    member: Member,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    now: datetime,
) -> None:
    """Tell this person on this device (push.py): a browser's push address and the keys to
    encrypt to it, checked. Done again for the same device, it is that device still; a device
    somebody else turned on before is theirs now."""
    from familydb import push

    if not endpoint.startswith("https://") or len(endpoint) > MAX_ENDPOINT:
        raise PushRefused("that is not a browser's push address")
    if not push.valid_device(p256dh, auth):
        raise PushRefused("those are not a browser's keys")
    with transaction(conn):
        push_store.subscribe(
            conn, member.id, endpoint=endpoint, p256dh=p256dh, auth=auth, now=utc_iso(now)
        )


# Her replies a person keeps at hand (docs/INTERFACE.md section 8): at most this many, the oldest
# going when another is pinned.
PINS_MOST = pin_store.MOST


class PinRefused(Exception):
    """Why a message was not pinned: only one of her replies in a conversation the person reads."""


def pin(
    conn: sqlite3.Connection, member: Member, message_id: int, *, chat_id: str, now: datetime
) -> None:
    """Keep one of her replies at hand for this person, on a shelf of their own: a reply of hers,
    with words, in `chat_id`, the conversation they read on the page."""
    message = messages.get(conn, message_id)
    if (
        message is None
        or message.direction != "out"
        or message.chat_id != chat_id
        or not message.text.strip()
    ):
        raise PinRefused("only one of her replies to you can be pinned")
    with transaction(conn):
        pin_store.pin(conn, member.id, message_id, now=utc_iso(now))
        pin_store.keep_newest(conn, member.id, PINS_MOST)


def unpin(conn: sqlite3.Connection, member: Member, message_id: int) -> bool:
    """Off this person's shelf; False when it was not on it."""
    with transaction(conn):
        return pin_store.unpin(conn, member.id, message_id) > 0


def unsubscribe_push(conn: sqlite3.Connection, member: Member, *, endpoint: str) -> bool:
    """This device tells this person nothing now; False when it told them nothing already."""
    with transaction(conn):
        return push_store.unsubscribe(conn, member.id, endpoint) > 0
