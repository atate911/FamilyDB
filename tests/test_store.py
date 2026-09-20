import sqlite3
from datetime import date

import pytest

from familydb.agent.render import render_idea_line
from familydb.store import calls, db, ideas, members, messages, outcomes
from familydb.store.members import Member
from tests.conftest import NOW_ISO


def _idea(conn: sqlite3.Connection, family: dict[str, Member], **overrides) -> ideas.Idea:
    fields = {
        "title": "Ramen place on Main St",
        "kind": "restaurant",
        "participants": ["whole family"],
        "tags": ["Food", "cheap", "food"],
        "setting": "indoor",
        "suggested_by": family["sam"].id,
        "now": NOW_ISO,
    }
    fields.update(overrides)
    with db.transaction(conn):
        return ideas.insert(conn, **fields)


def test_members_resolve_by_channel_and_console_name(conn, family) -> None:
    assert members.resolve(conn, "telegram", "1001").display_name == "Sam"
    assert members.resolve(conn, "telegram", "9999") is None
    assert members.resolve(conn, "console", "alex").display_name == "Alex"
    assert family["girls"].channel is None
    with pytest.raises(sqlite3.IntegrityError):
        members.add(conn, "sam", "member", now=NOW_ISO)  # names are unique, case-insensitively


def test_idea_round_trip_normalises_json_fields(conn, family) -> None:
    idea = _idea(conn, family)
    assert idea.tags == ["cheap", "food"]
    assert idea.participants == ["whole family"]
    assert idea.suggested_by_name == "Sam"
    assert idea.enrichment == "pending"
    row = conn.execute("SELECT tags, title_norm FROM ideas WHERE id = ?", (idea.id,)).fetchone()
    assert row["tags"] == '["cheap","food"]'
    assert row["title_norm"] == "ramen place on main st"


def test_fts_follows_insert_update_and_delete(conn, family) -> None:
    idea = _idea(conn, family)
    assert [i.id for i in ideas.search(conn, text="ramen")] == [idea.id]
    with db.transaction(conn):
        ideas.update(conn, idea.id, {"title": "Noodle bar on Main St"}, now=NOW_ISO)
    assert ideas.search(conn, text="ramen") == []
    assert [i.id for i in ideas.search(conn, text="noodle")] == [idea.id]
    conn.execute("DELETE FROM ideas WHERE id = ?", (idea.id,))
    assert ideas.search(conn, text="noodle") == []


def test_search_filters(conn, family) -> None:
    ramen = _idea(conn, family)
    hike = _idea(
        conn,
        family,
        title="The falls hike",
        kind="outing",
        tags=["hike"],
        participants=["with the girls"],
        setting="outdoor",
        duration_min=180,
        cost_level=0,
    )
    dropped = _idea(conn, family, title="Dropped thing", kind="other", status="dropped")
    assert {i.id for i in ideas.search(conn)} == {ramen.id, hike.id}
    assert [i.id for i in ideas.search(conn, kind="outing")] == [hike.id]
    assert [i.id for i in ideas.search(conn, tags=["HIKE"])] == [hike.id]
    assert [i.id for i in ideas.search(conn, max_duration=60)] == [ramen.id]
    assert [i.id for i in ideas.search(conn, status="dropped")] == [dropped.id]
    assert [i.id for i in ideas.search(conn, participant="Whole Family")] == [ramen.id]
    assert [i.id for i in ideas.search(conn, participant="with the girls")] == [hike.id]
    with db.transaction(conn):
        ideas.apply_outcome(conn, hike.id, happened_on="2026-09-13", avg_rating=9.0, now=NOW_ISO)
    recent = ideas.search(conn, exclude_done_within_days=30, today=date(2026, 9, 20))
    assert [i.id for i in recent] == [ramen.id]
    assert [i.id for i in ideas.list_for_prompt(conn)] == [ramen.id, hike.id]


def test_find_similar_title(conn, family) -> None:
    idea = _idea(conn, family)
    assert ideas.find_similar_title(conn, "ramen place on main st!").id == idea.id
    assert ideas.find_similar_title(conn, "Ramen place on Main Street").id == idea.id
    assert ideas.find_similar_title(conn, "Board game cafe") is None


def test_messages_log(conn, family) -> None:
    with db.transaction(conn):
        inbound = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="42",
            chat_id="chat-1",
            member_id=family["sam"].id,
            text="we should try that ramen place",
            now=NOW_ISO,
        )
    assert messages.exists_update(conn, "telegram", "42")
    assert not messages.exists_update(conn, "telegram", "43")
    with pytest.raises(sqlite3.IntegrityError):
        messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="42",
            chat_id="chat-1",
            member_id=None,
            text="dup",
            now=NOW_ISO,
        )
    with db.transaction(conn):
        reply = messages.insert_out(
            conn,
            channel="telegram",
            chat_id="chat-1",
            text="Saved.",
            reply_to=inbound.id,
            now="2026-09-20T21:03:05Z",
        )
        messages.mark_processed(conn, inbound.id, [{"tool": "add_idea", "id": 1}], now=NOW_ISO)
    stored = messages.get(conn, inbound.id)
    assert stored.status == "processed"
    assert stored.actions == [{"tool": "add_idea", "id": 1}]
    assert reply.reply_to == inbound.id
    recent = messages.recent_for_chat(conn, "chat-1", limit=10, since="2026-09-20T00:00:00Z")
    assert [m.direction for m in recent] == ["in", "out"]
    assert messages.recent_for_chat(conn, "chat-1", limit=10, since="2026-09-21T00:00:00Z") == []
    with db.transaction(conn):
        messages.mark_failed(conn, inbound.id, "boom", now=NOW_ISO)
    assert [m.id for m in messages.failed(conn)] == [inbound.id]


def test_outcomes_update_idea_bookkeeping(conn, family) -> None:
    idea = _idea(conn, family)
    with db.transaction(conn):
        outcomes.insert(
            conn,
            idea_id=idea.id,
            plan_id=None,
            happened_on="2026-09-05",
            rating=8,
            would_repeat=True,
            notes=None,
            recorded_by=family["sam"].id,
            now=NOW_ISO,
        )
        ideas.apply_outcome(
            conn,
            idea.id,
            happened_on="2026-09-05",
            avg_rating=outcomes.average_rating(conn, idea.id),
            now=NOW_ISO,
        )
        outcomes.insert(
            conn,
            idea_id=idea.id,
            plan_id=None,
            happened_on="2026-09-19",
            rating=10,
            would_repeat=True,
            notes="even better",
            recorded_by=family["alex"].id,
            now=NOW_ISO,
        )
        updated = ideas.apply_outcome(
            conn,
            idea.id,
            happened_on="2026-09-19",
            avg_rating=outcomes.average_rating(conn, idea.id),
            now=NOW_ISO,
        )
    assert updated.times_done == 2
    assert updated.last_done_at == "2026-09-19"
    assert updated.avg_rating == 9.0
    assert updated.status == "done"
    assert len(outcomes.list_for_idea(conn, idea.id)) == 2


def test_call_logs(conn) -> None:
    with db.transaction(conn):
        calls.log_tool_call(
            conn,
            message_id=None,
            iteration=1,
            tool_use_id="tu_1",
            tool_name="add_idea",
            input={"title": "x"},
            output='{"id": 1}',
            is_error=False,
            duration_ms=3,
            now=NOW_ISO,
        )
        calls.log_llm_call(
            conn,
            message_id=None,
            iteration=1,
            model="claude-opus-5",
            served_model="claude-opus-5",
            request_id="req_1",
            stop_reason="end_turn",
            usage={"input_tokens": 100, "cache_read_input_tokens": 90, "output_tokens": 10},
            duration_ms=800,
            now=NOW_ISO,
        )
    recent = calls.recent_llm_calls(conn)
    assert recent[0]["cache_read_input_tokens"] == 90
    assert recent[0]["cache_creation_input_tokens"] is None


def test_render_idea_line_is_compact_and_complete(conn, family) -> None:
    idea = _idea(conn, family, duration_min=60, duration_max=90, cost_level=2, needs_booking=True)
    line = render_idea_line(idea)
    assert line == (
        f"#{idea.id} | [restaurant] | Ramen place on Main St | for: whole family | "
        "tags: cheap, food | indoor/any | 1 h to 1.5 h | cost: $$ | needs booking | "
        "status: idea | by Sam 2026-09-20 | details: pending"
    )
