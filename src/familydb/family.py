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
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Literal

from familydb.store import members, messages
from familydb.store.db import transaction
from familydb.store.members import Member, Role

TELEGRAM = "telegram"
MAX_NAME = 80
Outcome = Literal["added", "changed"]


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
        raise FamilyError("Choose admin, member or kid.")
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
                raise FamilyError("There is nobody by that number any more.")
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
