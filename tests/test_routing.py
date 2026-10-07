"""What the bot sends of its own accord goes to whoever it is for (routing.py): a reminder for
somebody's own task goes to them, as a Telegram notification when they have their chat with her
(the family's decision, docs/DESIGN.md section 16), not to the whole group, the page or whoever's
chat it was asked for in; a task for everyone goes to the family; and presents never go where a
kid reads."""

from datetime import timedelta

from familydb import audience, routing
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


def _due_task(
    conn, clock, *, owner_id=None, chat_id=GROUP, gift_for=None, channel="telegram", by=None
) -> int:
    with db.transaction(conn):
        task_id = tasks.insert(
            conn,
            title="Renew the library cards",
            notes="",
            owner_id=owner_id,
            due_at=None,
            preferred_window="",
            operation_key=f"k{owner_id}{channel}{chat_id}{gift_for}",
            channel=channel,
            chat_id=chat_id,
            now=utc_iso(clock.now()),
            gift_for=gift_for,
            created_by_member_id=by,
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


def test_their_own_chat_is_never_moved_and_anywhere_else_reaches_them(
    settings, clock, conn, family
) -> None:
    """Asked for in their own chat, it stays there. Asked for on the page, or in somebody else's
    chat ("remind Alex to..." in Sam's), it goes to them: their Telegram chat with her, which the
    family asked for, or, for a kid, who has none, her own conversation on the page. This used to
    leave the page and every private chat alone, and a reminder set on the page reached no phone."""
    sam, alex, girls = family["sam"], family["alex"], family["girls"]
    _written(conn, "1001", sam.id)
    _written(conn, "1002", alex.id)
    assert routing.for_person(conn, settings, "telegram", "1002", alex.id) == ("telegram", "1002")
    assert routing.for_person(conn, settings, "telegram", "1001", alex.id) == ("telegram", "1002")
    assert routing.for_person(conn, settings, "web", "web", alex.id) == ("telegram", "1002")
    own = audience.private_chat(girls.id)
    assert routing.for_person(conn, settings, "web", "web", girls.id) == ("web", own)
    assert routing.for_person(conn, settings, "web", own, girls.id) == ("web", own)
    assert routing.for_person(conn, settings, "telegram", "1001", girls.id) == ("web", own)


def test_one_who_never_opened_her_chat_hears_on_the_page(settings, clock, conn, family) -> None:
    """Telegram lets a bot write to nobody who has not written first: until Alex does, a reminder
    set for Alex on the page stays there, and one set in Sam's chat goes to the page."""
    alex = family["alex"]
    assert routing.for_person(conn, settings, "web", "web", alex.id) == ("web", "web")
    assert routing.for_person(conn, settings, "telegram", "1001", alex.id) == ("web", "web")
    off = settings.model_copy(update={"private_when_personal": False})
    assert routing.for_person(conn, off, "telegram", "1001", alex.id) == ("telegram", "1001")


def test_a_reminder_set_on_the_page_reaches_their_phone(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    said = _sent(app)
    alex = family["alex"]
    _written(conn, "1002", alex.id)
    _due_task(conn, clock, owner_id=alex.id, channel="web", chat_id="web")
    assert run_reminders(app) == 1
    assert [chat for chat, _ in said] == ["1002"]


def test_a_parents_reminder_for_a_kid_reaches_her_own_page(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    girls = family["girls"]
    task_id = _due_task(
        conn, clock, owner_id=girls.id, channel="web", chat_id="web", by=family["sam"].id
    )
    run_reminders(app)
    sent = messages.get(conn, tasks.get(conn, task_id).reminder.message_id)
    assert (sent.channel, sent.chat_id) == ("web", audience.private_chat(girls.id))
    assert "Sam asked me to remind you." in sent.text


def test_a_reminder_for_everyone_goes_to_the_familys_chat(settings, clock, conn, family) -> None:
    """Nobody's task is everyone's: asked for on the page or in somebody's own chat, it goes to the
    family's chat; asked for in a group, it stays there (the test above)."""
    app = App(settings.model_copy(update={"family_chat_id": GROUP}), clock)
    said = _sent(app)
    _due_task(conn, clock, channel="web", chat_id="web")
    _due_task(conn, clock, chat_id="1001")
    run_reminders(app)
    assert [chat for chat, _ in said] == [GROUP, GROUP]
    unset = App(settings, clock)
    assert routing.for_task(conn, unset.settings, tasks.get(conn, 1)) == ("web", "web")


def test_who_asked_is_said_only_where_the_owner_hears_it_alone(
    settings, clock, conn, family
) -> None:
    """Set for Alex by Sam, it says so in Alex's own chat. In the group, where Alex has no chat with
    her to take it to, the "(Alex)" in it says whose it is; and Sam's own says nothing more."""
    sam, alex = family["sam"], family["alex"]
    app = App(settings, clock)
    said = _sent(app)
    _due_task(conn, clock, owner_id=alex.id, chat_id=GROUP, by=sam.id)
    _due_task(conn, clock, owner_id=sam.id, chat_id="1001", by=sam.id)
    run_reminders(app)
    assert [chat for chat, _ in said] == [GROUP, "1001"]
    assert not any("asked me" in text for _, text in said)
    _written(conn, "1002", alex.id)
    _due_task(conn, clock, owner_id=alex.id, chat_id="1001", by=sam.id)
    run_reminders(app)
    assert said[-1][0] == "1002" and "Sam asked me to remind you." in said[-1][1]


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
