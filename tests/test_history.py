from familydb.agent.history import load_history
from familydb.store import db, messages


def test_load_history_renders_recent_turns(conn, family, clock) -> None:
    with db.transaction(conn):
        old = messages.insert_in(
            conn,
            channel="console",
            channel_update_id="u0",
            chat_id="console",
            member_id=family["sam"].id,
            text="ancient",
            now="2026-09-19T10:00:00Z",
        )
        messages.insert_out(
            conn,
            channel="console",
            chat_id="console",
            text="ancient reply",
            reply_to=old.id,
            now="2026-09-19T10:00:05Z",
        )
        first = messages.insert_in(
            conn,
            channel="console",
            channel_update_id="u1",
            chat_id="console",
            member_id=family["sam"].id,
            text="we should try the ramen place",
            now="2026-09-20T20:00:00Z",
        )
        messages.insert_out(
            conn,
            channel="console",
            chat_id="console",
            text="Saved #1.",
            reply_to=first.id,
            now="2026-09-20T20:00:05Z",
        )
        messages.insert_in(
            conn,
            channel="console",
            channel_update_id="u2",
            chat_id="other",
            member_id=family["alex"].id,
            text="different chat",
            now="2026-09-20T20:30:00Z",
        )
        current = messages.insert_in(
            conn,
            channel="console",
            channel_update_id="u3",
            chat_id="console",
            member_id=family["alex"].id,
            text="tell me about #1",
            now="2026-09-20T21:03:00Z",
        )
    turns = load_history(
        conn, "console", clock=clock, limit=20, since_hours=6, exclude_message_id=current.id
    )
    assert [(t.role, t.text) for t in turns] == [
        ("user", "[Sam] we should try the ramen place"),
        ("assistant", "Saved #1."),
    ]
    assert load_history(conn, "console", clock=clock, limit=1, since_hours=6)[-1].text == (
        "[Alex] tell me about #1"
    )


def test_history_limit_counts_only_earlier_messages(conn, family, clock) -> None:
    with db.transaction(conn):
        for n in (1, 2, 3):
            inbound = messages.insert_in(
                conn,
                channel="console",
                channel_update_id=f"in{n}",
                chat_id="console",
                member_id=family["sam"].id,
                text=f"in{n}",
                now=f"2026-09-20T20:0{n}:00Z",
            )
            messages.insert_out(
                conn,
                channel="console",
                chat_id="console",
                text=f"Saved #{n}.",
                reply_to=inbound.id,
                now=f"2026-09-20T20:0{n}:30Z",
            )
        current = messages.insert_in(
            conn,
            channel="console",
            channel_update_id="now",
            chat_id="console",
            member_id=family["sam"].id,
            text="current",
            now="2026-09-20T21:03:00Z",
        )
    turns = load_history(
        conn, "console", clock=clock, limit=4, since_hours=6, exclude_message_id=current.id
    )
    assert [t.text for t in turns] == ["[Sam] in2", "Saved #2.", "[Sam] in3", "Saved #3."]


def test_history_can_exclude_replies_to_a_message(conn, family, clock) -> None:
    with db.transaction(conn):
        inbound = messages.insert_in(
            conn,
            channel="console",
            channel_update_id="r1",
            chat_id="console",
            member_id=family["sam"].id,
            text="hello",
            now="2026-09-20T20:00:00Z",
        )
        messages.insert_out(
            conn,
            channel="console",
            chat_id="console",
            text="I'll retry later.",
            reply_to=inbound.id,
            now="2026-09-20T20:00:05Z",
        )
    turns = load_history(
        conn,
        "console",
        clock=clock,
        limit=20,
        since_hours=6,
        exclude_message_id=inbound.id,
        exclude_replies_to=inbound.id,
    )
    assert turns == []


def test_history_keeps_the_newest_turns_within_a_budget() -> None:
    from familydb.agent.history import CUT, MESSAGE_CHARS, HistoryTurn, within_budget

    paste = "x" * 10_000
    turns = [
        HistoryTurn("user", "oldest"),
        HistoryTurn("user", paste),
        HistoryTurn("assistant", "a" * 900),
        HistoryTurn("user", "newest"),
    ]
    kept = within_budget(turns, 2410)
    # The paste is cut to one message's share; the oldest no longer fits and is dropped.
    assert [t.text[:5] for t in kept] == ["xxxxx", "aaaaa", "newes"]
    assert len(kept[0].text) == MESSAGE_CHARS and kept[0].text.endswith(CUT)
    assert within_budget(turns, 2410) == kept  # deterministic
    assert within_budget(turns, 5) == []
    assert within_budget(turns[-1:], 6000) == turns[-1:]


def test_load_history_applies_the_budget(conn, family, clock) -> None:
    with db.transaction(conn):
        for n in range(6):
            messages.insert_in(
                conn,
                channel="console",
                channel_update_id=f"b{n}",
                chat_id="console",
                member_id=family["sam"].id,
                text=f"{n}" * 3000,
                now=f"2026-09-20T20:0{n}:00Z",
            )
    turns = load_history(conn, "console", clock=clock, limit=20, since_hours=6)
    assert sum(len(t.text) for t in turns) <= 6000
    assert turns[-1].text.startswith("[Sam] 5")  # the newest survives
