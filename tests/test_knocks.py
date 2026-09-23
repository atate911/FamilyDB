"""Strangers who messaged the bot are remembered briefly, by who and when, never what they said."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from familydb.store import knocks
from familydb.store.db import transaction

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def _knock(conn, user: str, when: datetime, name: str | None = "Robin") -> None:
    with transaction(conn):
        knocks.record(
            conn, channel="telegram", channel_user_id=user, name=name, chat_id=user, now=when
        )


def test_a_second_knock_counts_and_keeps_the_name(conn) -> None:
    _knock(conn, "5555", NOW)
    _knock(conn, "5555", NOW + timedelta(minutes=5), name=None)
    [knock] = knocks.recent(conn, channel="telegram")
    assert knock.times == 2 and knock.name == "Robin"


def test_family_members_are_not_listed(conn, family) -> None:
    _knock(conn, "1001", NOW)  # Sam, already on the list
    assert knocks.recent(conn, channel="telegram") == []


def test_old_knocks_drop_off_and_the_list_is_bounded(conn) -> None:
    _knock(conn, "old", NOW - timedelta(days=knocks.KEEP_DAYS + 1))
    for n in range(knocks.KEEP + 5):
        _knock(conn, str(n), NOW + timedelta(seconds=n))
    count = conn.execute("SELECT count(*) FROM knocks").fetchone()[0]
    assert count == knocks.KEEP
    assert "old" not in {
        k.channel_user_id for k in knocks.recent(conn, channel="telegram", limit=500)
    }


def test_a_long_name_is_cut(conn) -> None:
    _knock(conn, "9", NOW, name="x" * 500)
    assert len(knocks.recent(conn, channel="telegram")[0].name) == knocks.MAX_NAME
