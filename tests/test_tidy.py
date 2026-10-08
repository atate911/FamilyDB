"""The nightly tidy (jobs/tidy.py): an idea whose dates are a week past leaves the list, through
update_idea as the job, with no model call; anything else stays."""

from __future__ import annotations

from familydb.app import App
from familydb.jobs.tidy import run_tidy
from familydb.store import db, ideas
from tests.conftest import NOW_ISO


def _idea(conn, title, **fields):
    with db.transaction(conn):
        return ideas.insert(conn, title=title, kind="event", now=NOW_ISO, **fields)


def test_what_is_a_week_over_leaves_the_list(settings, clock, conn) -> None:
    """Sunday 20 September: over by the 12th goes; over on the 15th is left a little longer."""
    gone = _idea(conn, "Pumpkin fair", happens_from="2026-09-05", happens_until="2026-09-12")
    recent = _idea(conn, "Street fair", happens_from="2026-09-15", happens_until="2026-09-15")
    planned = _idea(conn, "Harvest supper", happens_from="2026-09-01", happens_until="2026-09-01")
    with db.transaction(conn):
        ideas.update(conn, planned.id, {"status": "planned"}, now=NOW_ISO)
    always = _idea(conn, "Ramen place")
    app = App(settings, clock)
    assert run_tidy(app) == 1
    assert ideas.get(conn, gone.id).status == "dropped"
    assert {ideas.get(conn, i.id).status for i in (recent, always)} == {"idea"}
    assert ideas.get(conn, planned.id).status == "planned"
    row = conn.execute("SELECT tool_name, source, member_id FROM tool_calls").fetchone()
    assert tuple(row) == ("update_idea", "job", None)
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0
    assert run_tidy(app) == 0  # once


def test_the_family_can_turn_it_off(settings, clock, conn) -> None:
    gone = _idea(conn, "Pumpkin fair", happens_from="2026-09-05", happens_until="2026-09-12")
    app = App(settings.model_copy(update={"tidy_ideas": False}), clock)
    assert run_tidy(app) == 0 and ideas.get(conn, gone.id).status == "idea"


def test_old_messages_lose_their_words_when_the_family_says_so(settings, clock, conn, family):
    """Kept for 30 days: older words go, the rows stay; never one still to be answered or sent."""
    from familydb.store import messages

    with db.transaction(conn):
        old = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="old",
            chat_id="42",
            member_id=family["sam"].id,
            text="the girls are vegetarian now",
            now="2026-07-01T10:00:00Z",
        )
        messages.mark_processed(conn, old.id, [], now="2026-07-01T10:00:05Z")
        waiting = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="waiting",
            chat_id="42",
            member_id=family["sam"].id,
            text="still to be answered",
            now="2026-07-01T10:00:00Z",
        )
        unsent = messages.insert_out(
            conn, channel="telegram", chat_id="42", text="still to go", now="2026-07-01T10:00:00Z"
        )
        recent = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="recent",
            chat_id="42",
            member_id=family["sam"].id,
            text="last week's",
            now="2026-09-13T10:00:00Z",
        )
    app = App(settings.model_copy(update={"keep_messages_days": 7, "tidy_ideas": False}), clock)
    run_tidy(app)  # seven is read as the least there is, thirty
    assert messages.get(conn, old.id).text == messages.WORDS_GONE
    assert messages.get(conn, waiting.id).text == "still to be answered"
    assert messages.get(conn, unsent.id).text == "still to go"
    assert messages.get(conn, recent.id).text == "last week's"
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 4
    # Kept for good, the default: nothing is touched.
    with db.transaction(conn):
        conn.execute("UPDATE messages SET text = 'back' WHERE id = ?", (old.id,))
    run_tidy(App(settings, clock))
    assert messages.get(conn, old.id).text == "back"


def test_old_knocks_and_spent_links_go_in_the_night(settings, clock, conn, family) -> None:
    """Both were only dropped when the next of their kind came, which may be never."""
    from datetime import timedelta

    from familydb.store import invites, knocks

    app = App(settings, clock)
    now = clock.now()
    with db.transaction(conn):
        knocks.record(
            conn, channel="telegram", channel_user_id="old", name="X", chat_id="1",
            now=now - timedelta(days=knocks.KEEP_DAYS + 2),
        )  # fmt: skip
        invites.put(
            conn, family["sam"].id, invites.digest("a-code"), made_by=None,
            now="2026-09-01T10:00:00Z", expires="2026-09-02T10:00:00Z",
        )  # fmt: skip
    run_tidy(app)
    assert conn.execute("SELECT count(*) FROM knocks").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM telegram_invites").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0] == 0
