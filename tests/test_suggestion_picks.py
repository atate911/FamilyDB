"""What was chosen for a suggestion is kept with it, and the outcomes a dossier reads."""

from __future__ import annotations

from familydb.store import ideas, outcomes, suggestions
from familydb.store.db import transaction
from tests.conftest import NOW_ISO


def test_picks_are_kept_with_their_suggestion_and_read_back(conn) -> None:
    with transaction(conn):
        plain = suggestions.insert(
            conn,
            asked_by=None,
            window_start=None,
            window_end=None,
            candidates=[],
            web_finds=[],
            now="2026-09-10T10:00:00Z",
        )
        chosen = suggestions.insert(
            conn,
            asked_by=None,
            window_start=None,
            window_end=None,
            candidates=[],
            web_finds=[],
            now="2026-09-19T10:00:00Z",
        )
        picks = {
            "picks": [{"ref": "idea:1", "title": "Ramen", "slot": "favourite"}],
            "framing": "easy",
        }
        suggestions.set_picks(conn, chosen.id, picks)
    assert suggestions.get(conn, plain.id).picks is None
    assert suggestions.get(conn, chosen.id).picks == picks
    assert [s.id for s in suggestions.picked_since(conn, since="2026-09-01T00:00:00Z")] == [
        chosen.id
    ]
    assert suggestions.picked_since(conn, since="2026-09-20T00:00:00Z") == []


def test_recent_outcomes_and_the_latest_for_each_idea(conn) -> None:
    with transaction(conn):
        ramen = ideas.insert(conn, title="Ramen", kind="restaurant", now=NOW_ISO)
        zoo = ideas.insert(conn, title="Zoo", kind="outing", now=NOW_ISO)
        for idea, day, rating, notes in (
            (ramen, "2026-08-01", 7, "fine"),
            (ramen, "2026-09-12", 9, "the girls loved it"),
            (zoo, "2026-09-02", 4, "too crowded"),
        ):
            outcomes.insert(
                conn,
                idea_id=idea.id,
                plan_id=None,
                happened_on=day,
                rating=rating,
                would_repeat=None,
                notes=notes,
                recorded_by=None,
                now=NOW_ISO,
            )
    assert [o.notes for o in outcomes.recent(conn, since="2026-09-01")] == [
        "the girls loved it",
        "too crowded",
    ]
    latest = outcomes.latest_for(conn, [ramen.id, zoo.id, 999])
    assert (latest[ramen.id].rating, latest[zoo.id].rating) == (9, 4) and 999 not in latest
    assert outcomes.latest_for(conn, []) == {}
