"""What the bot sends of its own accord goes to whoever it is for (routing.py): a reminder for
somebody's own task goes to their own chat, not the whole family group, and presents never go
where a kid reads."""

from datetime import timedelta

from familydb import routing
from familydb.app import App
from familydb.dates import utc_iso
from familydb.jobs.reminders import run_reminders
from familydb.store import db, ideas, messages, tasks

GROUP = "-100"


def _sent(app) -> list[tuple[str, str]]:
    said: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: said.append((chat, text))
    return said


def _written(conn, chat_id: str, member_id: int) -> None:
    """Somebody has written to her in their own chat, so she may write to them there."""
    with db.transaction(conn):
        messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=f"u{chat_id}",
            chat_id=chat_id,
            member_id=member_id,
            text="/start",
            now="2026-09-01T00:00:00Z",  # long ago: a chat talking now would hold the message
        )


def _due_task(conn, clock, *, owner_id=None, chat_id=GROUP, gift_for=None) -> int:
    with db.transaction(conn):
        task_id = tasks.insert(
            conn,
            title="Renew the library cards",
            notes="",
            owner_id=owner_id,
            due_at=None,
            preferred_window="",
            operation_key=f"k{owner_id}{chat_id}{gift_for}",
            channel="telegram",
            chat_id=chat_id,
            now=utc_iso(clock.now()),
            gift_for=gift_for,
        )
        tasks.add_reminder(conn, task_id, utc_iso(clock.now() - timedelta(minutes=1)))
    return task_id


def test_a_reminder_for_somebody_s_own_task_goes_to_their_own_chat(
    settings, clock, conn, family
) -> None:
    app = App(settings, clock)
    said = _sent(app)
    alex = family["alex"]
    _written(conn, "1002", alex.id)
    _due_task(conn, clock, owner_id=alex.id)
    assert run_reminders(app) == 1
    assert [chat for chat, _ in said] == ["1002"]


def test_it_stays_in_the_group_when_they_have_never_written_to_her(
    settings, clock, conn, family
) -> None:
    """Telegram lets a bot write to nobody who has not written to it first."""
    app = App(settings, clock)
    said = _sent(app)
    _due_task(conn, clock, owner_id=family["alex"].id)
    run_reminders(app)
    assert [chat for chat, _ in said] == [GROUP]


def test_a_task_nobody_owns_and_the_switch_off_keep_it_in_the_group(
    settings, clock, conn, family
) -> None:
    alex = family["alex"]
    _written(conn, "1002", alex.id)
    app = App(settings, clock)
    said = _sent(app)
    _due_task(conn, clock)
    run_reminders(app)
    off = App(settings.model_copy(update={"private_when_personal": False}), clock)
    said_off = _sent(off)
    _due_task(conn, clock, owner_id=alex.id, chat_id="-200")
    run_reminders(off)
    assert [chat for chat, _ in said] == [GROUP]
    assert [chat for chat, _ in said_off] == ["-200"]


def test_a_private_chat_or_the_page_is_never_moved(settings, clock, conn, family) -> None:
    alex = family["alex"]
    _written(conn, "1002", alex.id)
    assert routing.for_person(conn, settings, "telegram", "1001", alex.id) == ("telegram", "1001")
    assert routing.for_person(conn, settings, "web", "web", alex.id) == ("web", "web")


def test_presents_never_go_where_a_kid_reads(settings, clock, conn, family) -> None:
    """A birthday's reminder lists the gifts saved for them: never in a group a kid may be in,
    so it goes there as the reminder alone; in a parent's own chat, with the gifts."""
    with db.transaction(conn):
        ideas.insert(
            conn,
            title="Roller skates",
            kind="gift",
            participants=["the girls"],
            status="idea",
            now="2026-09-01T00:00:00Z",
        )
    app = App(settings, clock)
    said = _sent(app)
    _due_task(conn, clock, gift_for="the girls")
    alex = family["alex"]
    _written(conn, "1002", alex.id)
    _due_task(conn, clock, owner_id=alex.id, gift_for="the girls")
    run_reminders(app)
    by_chat = dict(said)
    assert "Roller skates" not in by_chat[GROUP] and "gift" not in by_chat[GROUP].lower()
    assert "Roller skates" in by_chat["1002"]


def test_a_late_reminder_where_a_kid_reads_does_not_say_the_bot_was_off(
    settings, clock, conn, family
) -> None:
    app = App(settings, clock)
    said = _sent(app)
    with db.transaction(conn):
        task_id = tasks.insert(
            conn,
            title="Pack the swim bag",
            notes="",
            owner_id=None,
            due_at=None,
            preferred_window="",
            operation_key="late",
            channel="telegram",
            chat_id=GROUP,
            now=utc_iso(clock.now()),
        )
        tasks.add_reminder(conn, task_id, utc_iso(clock.now() - timedelta(hours=3)))
    run_reminders(app)
    [(_, text)] = said
    assert text.startswith("Reminder: Pack the swim bag") and "offline" not in text
