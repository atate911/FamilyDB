"""The rules of the kids' wish lists, in code (docs/WISHES.md). The tools and the page both come
here, so a wish added from the chat and one added on the page are held to the same rules.

Everyday wishes are held to the daily rules: a few a day, and a "not this time" locks the thing
(its topic) for longer each time it comes back. A wish flagged for Christmas or a birthday is held
to looser ones: no daily count, only a cap on how long the list may grow, and a "not this time"
that lasts until the occasion has passed. Moving wishes, in her order or between her lists, is
free, with only a cap against excess.

Each change is one short transaction, as in task_service.py. Nothing here calls a model.
"""

from __future__ import annotations

import difflib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from familydb import buttons, family, roles, voice
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import ToolError
from familydb.store import members, messages, wishes
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.store.wishes import Concern, Occasion, Wish

# Days a "not this time" locks an everyday wish, by how many times that thing has been declined:
# two weeks the first time, then a month, three months, four, and a year each time after.
LOCKOUT_DAYS = (14, 30, 90, 120, 365)
# Moving is free; this only stops a day of excess. The family's own limits (a day's wishes, the
# length of an occasion list, Ask a parent) are settings (config.py, the Spending page).
WISH_MOVES_PER_DAY = 300
# How alike two titles must be to count as one ask when no topic says so.
SAME_TITLE = 0.9
MAX_TITLE = 120
MAX_NOTES = 500
KEEP: Any = object()

NOT_YOURS = "that is somebody else's list"
FOR_A_PARENT = "only a parent can answer a wish"
NO_SUCH = "no wish #{id}"
NOT_OPEN = "wish #{id} is not open any more"
TOO_MANY_MOVES = "that is a lot of moving for one day; try again tomorrow"

Result = Literal["added", "duplicate", "locked", "too_many", "list_full"]


@dataclass(frozen=True)
class Added:
    """What asking for a wish came to, for the tool to hand back and the page to say."""

    result: Result
    wish: Wish | None = None
    locked_until: str | None = None  # when a locked thing may be asked for again
    rung: int | None = None  # how many times it has been declined
    asked_today: int = 0  # her everyday asks today, this one included

    def compact(self) -> dict[str, Any]:
        """The few fields the model needs, and no more."""
        out: dict[str, Any] = {"result": self.result}
        if self.wish is not None:
            out["wish"] = {
                "id": self.wish.id,
                "title": self.wish.title,
                "occasion": self.wish.occasion,
            }
        if self.locked_until:
            out["locked_until"] = self.locked_until[:10]
            out["times_declined"] = self.rung
        if self.result in ("added", "too_many") and self.wish is not None:
            out["asked_today"] = self.asked_today
        return out


# -- who and when ---------------------------------------------------------------------------------


def _may_keep(by: Member, owner: Member) -> None:
    """A kid keeps her own list; somebody who may decide keeps anybody's."""
    if roles.may(by.role, "decide"):
        return
    if by.id == owner.id and roles.may(by.role, "wish"):
        return
    raise ToolError(NOT_YOURS)


def _may_decide(by: Member) -> None:
    if not roles.may(by.role, "decide"):
        raise ToolError(FOR_A_PARENT)


def _today(settings: Settings, now: datetime) -> date:
    return now.astimezone(settings.tzinfo).date()


def _start_of(settings: Settings, day: date) -> str:
    """Midnight at home on that day, as the log stores times."""
    return utc_iso(datetime.combine(day, time(0), tzinfo=settings.tzinfo))


def _owner_of(conn: sqlite3.Connection, wish: Wish) -> Member:
    owner = members.get(conn, wish.member_id)
    assert owner is not None
    return owner


def _get(conn: sqlite3.Connection, wish_id: int) -> Wish:
    wish = wishes.get(conn, wish_id)
    if wish is None:
        raise ToolError(NO_SUCH.format(id=wish_id))
    return wish


def _same(wish: Wish, topic: str, title_norm: str) -> bool:
    """Whether this wish asks for the same thing: the same topic, or nearly the same title, the
    backstop for a topic named differently."""
    if topic and wish.topic == topic:
        return True
    return difflib.SequenceMatcher(None, wish.title_norm, title_norm).ratio() >= SAME_TITLE


def _clean(title: str, notes: str | None) -> tuple[str, str | None]:
    title = " ".join(title.split())
    if not title or len(title) > MAX_TITLE:
        raise ToolError(f"a wish needs a title of 1 to {MAX_TITLE} characters")
    notes = (notes or "").strip() or None
    if notes and len(notes) > MAX_NOTES:
        raise ToolError(f"notes are at most {MAX_NOTES} characters")
    return title, notes


def occasion_passes(settings: Settings, occasion: Occasion, owner: Member, today: date) -> date:
    """The day after the coming occasion: when a "not this time" for it runs out."""
    if occasion == "christmas":
        christmas = date(today.year, 12, 25)
        if christmas < today:
            christmas = date(today.year + 1, 12, 25)
        return christmas + timedelta(days=1)
    birthday = family.next_birthday(owner.birth_date, today)
    return (birthday or today + timedelta(days=364)) + timedelta(days=1)


# -- telling ------------------------------------------------------------------------------------


def private_chat(member_id: int) -> str:
    """A kid's own conversation on the page (web/chat.py)."""
    return f"member:{member_id}"


def _tell_parents(
    conn: sqlite3.Connection, settings: Settings, wish: Wish, event: str, kid: Member, now: str
) -> int:
    """Store a message about a kid's ask for each parent the bot reaches on Telegram, with the
    buttons to answer it; delivery sends them (docs/WISHES.md: only two things ever do this)."""
    told = 0
    for person in members.list_all(conn):
        if not roles.may(person.role, "decide"):
            continue
        if person.channel != "telegram" or not person.channel_user_id:
            continue
        messages.insert_out(
            conn,
            channel="telegram",
            chat_id=person.channel_user_id,
            text=voice.say(settings, event, seed=wish.id, kid=kid.display_name, what=wish.title),
            now=now,
            buttons=buttons.for_wish(wish.id),
            sent_as=event,
        )
        told += 1
    return told


def waiting_for_parents(conn: sqlite3.Connection) -> list[int]:
    """Messages about a kid's ask stored for the parents and not sent yet, to send at once."""
    rows = conn.execute(
        "SELECT id FROM messages WHERE direction = 'out' AND delivered_at IS NULL "
        "AND cancelled_at IS NULL AND buttons LIKE '%\"wish_yes:%' ORDER BY id"
    )
    return [int(row[0]) for row in rows]


def _tell_kid(
    conn: sqlite3.Connection, settings: Settings, wish: Wish, kid: Member, today: date, now: str
) -> None:
    """A parent's answer, in her own conversation, worded by code; only a kid is told so."""
    if roles.may(kid.role, "decide"):
        return
    note = f" {wish.answer_note}" if wish.answer_note else ""
    if wish.status == "granted":
        text = voice.say(
            settings, "wish_granted", seed=wish.id, kid=kid.display_name, wish=wish.title, note=note
        )
    else:
        until = date.fromisoformat((wish.locked_until or now)[:10])
        again = f"{until.day} {until:%B}" + (f" {until.year}" if until.year != today.year else "")
        text = voice.say(
            settings,
            "wish_declined",
            seed=wish.id,
            kid=kid.display_name,
            wish=wish.title,
            note=note,
            again=again,
        )
    messages.insert_out(
        conn,
        channel="web",
        chat_id=private_chat(kid.id),
        text=text,
        now=now,
        sent_as="wish_granted" if wish.status == "granted" else "wish_declined",
    )


# -- asking ---------------------------------------------------------------------------------------


def _lock_on(
    conn: sqlite3.Connection,
    owner: Member,
    occasion: Occasion | None,
    topic: str,
    title_norm: str,
    now_iso: str,
) -> Wish | None:
    """The declined wish that still locks this ask, if one does. An everyday lock is for her
    everyday list only: asking for the same thing for Christmas is the habit to encourage."""
    for wish in wishes.for_member(conn, owner.id):
        if (
            wish.status == "declined"
            and wish.occasion == occasion
            and wish.locked_until
            and wish.locked_until > now_iso
            and _same(wish, topic, title_norm)
        ):
            return wish
    return None


def _asked_today(conn: sqlite3.Connection, owner: Member, today: date) -> int:
    """Her everyday asks today: the ones she asked for, and the ones she moved onto that list
    from Christmas or her birthday, which would otherwise be a way round the daily count."""
    return wishes.day_of(conn, owner.id, today.isoformat())[0]


def add(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    by: Member,
    owner: Member,
    title: str,
    topic: str | None = None,
    occasion: Occasion | None = None,
    category: str | None = None,
    notes: str | None = None,
    idea_id: int | None = None,
    message_id: int | None = None,
    now: datetime,
) -> Added:
    """Put a wish on her list, or say why not: already there, locked, too many today, or a full
    occasion list. Too many is kept as a turned-away ask, so the parents see the pattern."""
    _may_keep(by, owner)
    title, notes = _clean(title, notes)
    topic_ = wishes.normalize_topic(topic or title) or wishes.normalize_topic(title)
    title_norm = wishes.normalize_title(title)
    now_iso = utc_iso(now)
    today = _today(settings, now)
    with transaction(conn):
        listed = wishes.open_list(conn, owner.id, occasion)
        for wish in listed:
            if _same(wish, topic_, title_norm):
                return Added("duplicate", wish)
        # A lockout holds her back, not a parent, who may put it on her list after all.
        locking = _lock_on(conn, owner, occasion, topic_, title_norm, now_iso)
        if locking is not None and not roles.may(by.role, "decide"):
            return Added(
                "locked", locking, locked_until=locking.locked_until, rung=locking.refusal_rung
            )
        extra = {"notes": notes, "category": category, "source_message_id": message_id}
        counted = occasion is None and not roles.may(by.role, "decide")
        if counted:
            asked = _asked_today(conn, owner, today) + 1
            wishes.count_day(conn, owner.id, today.isoformat(), asks=1)
            if asked > settings.wish_daily_count:
                kept = wishes.insert(
                    conn,
                    member_id=owner.id,
                    title=title,
                    topic=topic_,
                    occasion=None,
                    rank=0,
                    now=now_iso,
                    status="turned_away",
                    concern="too_many",
                    **extra,
                )
                return Added("too_many", kept, asked_today=asked)
        else:
            asked = 0
            if occasion is not None and len(listed) >= settings.occasion_list_size:
                return Added("list_full")
        wish = wishes.insert(
            conn,
            member_id=owner.id,
            title=title,
            topic=topic_,
            occasion=occasion,
            rank=len(listed) + 1,
            now=now_iso,
            idea_id=idea_id,
            **extra,
        )
    return Added("added", wish, asked_today=asked)


# -- changing her list ----------------------------------------------------------------------------


def move(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    by: Member,
    wish_id: int,
    position: int | None = None,
    occasion: Any = KEEP,
    now: datetime,
) -> Wish:
    """Put an open wish at this place in its list (1 is the top), or on another of her lists (at
    the bottom, unless a place is given too). Free, and never starts a lockout; only a day of
    excess is refused."""
    day = _today(settings, now).isoformat()
    with transaction(conn):
        wish = _get(conn, wish_id)
        owner = _owner_of(conn, wish)
        _may_keep(by, owner)
        if wish.status != "open":
            raise ToolError(NOT_OPEN.format(id=wish_id))
        if wishes.day_of(conn, by.id, day)[1] >= WISH_MOVES_PER_DAY:
            raise ToolError(TOO_MANY_MOVES)
        target = wish.occasion if occasion is KEEP else occasion
        if target not in (None, *wishes.OCCASIONS):
            raise ToolError("a wish is for every day, Christmas or a birthday")
        into_everyday = target is None and wish.occasion is not None
        if into_everyday and not roles.may(by.role, "decide"):
            # Onto the everyday list is asking for it every day: held to those rules.
            if _lock_on(conn, owner, None, wish.topic, wish.title_norm, utc_iso(now)):
                raise ToolError("that one is locked on your everyday list for now")
            if _asked_today(conn, owner, _today(settings, now)) >= settings.wish_daily_count:
                raise ToolError("that is enough everyday wishes for today; try tomorrow")
        if target != wish.occasion:
            if target is not None and len(wishes.open_list(conn, owner.id, target)) >= (
                settings.occasion_list_size
            ):
                raise ToolError("that list is full; take something off it first")
            old = [w.id for w in wishes.open_list(conn, owner.id, wish.occasion) if w.id != wish_id]
            wishes.renumber(conn, old)
            wish = wishes.update(conn, wish_id, {"occasion": target}, now=utc_iso(now))
        order = [w.id for w in wishes.open_list(conn, owner.id, target) if w.id != wish_id]
        place = len(order) if position is None else max(0, min(position - 1, len(order)))
        order.insert(place, wish_id)
        wishes.renumber(conn, order)
        wishes.count_day(conn, by.id, day, moves=1)
        if into_everyday and not roles.may(by.role, "decide"):
            wishes.count_day(conn, owner.id, day, asks=1)
        return _get(conn, wish_id)


def edit(
    conn: sqlite3.Connection,
    *,
    by: Member,
    wish_id: int,
    title: str | None = None,
    notes: Any = KEEP,
    category: Any = KEEP,
    now: datetime,
) -> Wish:
    """Reword an open wish. Its topic stays: a new title never escapes a lockout."""
    with transaction(conn):
        wish = _get(conn, wish_id)
        _may_keep(by, _owner_of(conn, wish))
        if wish.status != "open":
            raise ToolError(NOT_OPEN.format(id=wish_id))
        new_title, new_notes = _clean(
            title if title is not None else wish.title,
            wish.notes if notes is KEEP else notes,
        )
        changes: dict[str, Any] = {"title": new_title, "notes": new_notes}
        if category is not KEEP:
            changes["category"] = category
        return wishes.update(conn, wish_id, changes, now=utc_iso(now))


def withdraw(conn: sqlite3.Connection, *, by: Member, wish_id: int, now: datetime) -> Wish:
    """Take a wish off her list: she changed her mind. Nothing is locked by it."""
    with transaction(conn):
        wish = _get(conn, wish_id)
        owner = _owner_of(conn, wish)
        _may_keep(by, owner)
        if wish.status != "open":
            raise ToolError(NOT_OPEN.format(id=wish_id))
        changed = wishes.update(conn, wish_id, {"status": "withdrawn"}, now=utc_iso(now))
        rest = [w.id for w in wishes.open_list(conn, owner.id, wish.occasion)]
        wishes.renumber(conn, rest)
        return changed


# -- a parent's answer ----------------------------------------------------------------------------


def answer(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    by: Member,
    wish_id: int,
    granted: bool,
    note: str | None = None,
    now: datetime,
) -> Wish:
    """Yes, or not this time. An everyday "not this time" locks the thing by the ladder; one for
    an occasion lasts until the occasion has passed."""
    _may_decide(by)
    note = (note or "").strip() or None
    if note and len(note) > MAX_NOTES:
        raise ToolError(f"a note is at most {MAX_NOTES} characters")
    now_iso = utc_iso(now)
    today = _today(settings, now)
    with transaction(conn):
        wish = _get(conn, wish_id)
        if wish.status not in ("open", "turned_away"):
            raise ToolError(NOT_OPEN.format(id=wish_id))
        owner = _owner_of(conn, wish)
        changes: dict[str, Any] = {
            "status": "granted" if granted else "declined",
            "answer_note": note,
            "answered_by": by.id,
            "answered_at": now_iso,
        }
        if not granted:
            if wish.occasion is None:
                before = [
                    w
                    for w in wishes.for_member(conn, owner.id)
                    if w.id != wish.id
                    and w.status == "declined"
                    and w.occasion is None
                    and _same(w, wish.topic, wish.title_norm)
                ]
                rung = len(before) + 1
                days = LOCKOUT_DAYS[min(rung, len(LOCKOUT_DAYS)) - 1]
                until = today + timedelta(days=days)
            else:
                rung = None
                until = occasion_passes(settings, wish.occasion, owner, today)
            changes |= {"locked_until": _start_of(settings, until), "refusal_rung": rung}
        changed = wishes.update(conn, wish_id, changes, now=now_iso)
        rest = [w.id for w in wishes.open_list(conn, owner.id, wish.occasion)]
        wishes.renumber(conn, rest)
        _tell_kid(conn, settings, changed, owner, today, now_iso)
        return changed


# -- what the bot turns away ----------------------------------------------------------------------


@dataclass(frozen=True)
class TurnedAway:
    wish: Wish
    tell_parents: bool  # an inappropriate ask: the parents hear of it at once
    may_ask_parent: bool  # the "Ask a parent" button is on offer

    def compact(self) -> dict[str, Any]:
        return {"ask_a_parent_offered": self.may_ask_parent, "parents_told": self.tell_parents}


def turn_away(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    owner: Member,
    summary: str,
    concern: Concern,
    reviewable: bool,
    message_id: int | None = None,
    now: datetime,
) -> TurnedAway:
    """Keep an ask the bot turned away, so the parents see it. Ask a parent is offered only when
    the bot judged it reasonable, never for an inappropriate ask, and a couple of times a week."""
    summary = " ".join(summary.split())[:MAX_TITLE] or "a request"
    now_iso = utc_iso(now)
    week_ago = utc_iso(now - timedelta(days=7))
    with transaction(conn):
        # A turn tried again after a failure must not keep, or tell the parents of, it twice.
        if message_id is not None:
            row = conn.execute(
                "SELECT id FROM wishes WHERE source_message_id = ? AND status = 'turned_away' "
                "AND concern = ?",
                (message_id, concern),
            ).fetchone()
            if row is not None:
                kept = _get(conn, int(row[0]))
                return TurnedAway(kept, tell_parents=False, may_ask_parent=False)
        asked = conn.execute(
            "SELECT count(*) FROM wishes WHERE member_id = ? AND parent_review != 'none' "
            "AND updated_at >= ?",
            (owner.id, week_ago),
        ).fetchone()[0]
        offered = (
            reviewable and concern != "inappropriate" and asked < settings.parent_asks_per_week
        )
        wish = wishes.insert(
            conn,
            member_id=owner.id,
            title=summary,
            topic=summary,
            occasion=None,
            rank=0,
            now=now_iso,
            status="turned_away",
            concern=concern,
            parent_review="offered" if offered else "none",
            source_message_id=message_id,
        )
        if concern == "inappropriate":
            _tell_parents(conn, settings, wish, "kid_flagged", owner, now_iso)
    return TurnedAway(wish, tell_parents=concern == "inappropriate", may_ask_parent=offered)


def ask_parent(
    conn: sqlite3.Connection, settings: Settings, *, by: Member, wish_id: int, now: datetime
) -> Wish:
    """She pressed Ask a parent: it works once, for an ask it was offered for, and the parents
    get it on Telegram with the buttons to answer."""
    now_iso = utc_iso(now)
    with transaction(conn):
        wish = _get(conn, wish_id)
        owner = _owner_of(conn, wish)
        _may_keep(by, owner)
        if wish.parent_review != "offered":
            raise ToolError("there is nothing to ask a parent about here")
        asked = wishes.update(conn, wish_id, {"parent_review": "asked"}, now=now_iso)
        _tell_parents(conn, settings, asked, "kid_asks_parent", owner, now_iso)
        return asked
