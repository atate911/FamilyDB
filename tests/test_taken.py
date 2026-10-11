"""What came of a suggestion (suggest/taken.py): a plan is put down to the latest suggestion in
the three days before it that offered its idea or a find of its name, with where it stood there
and how it went; read only, no model call."""

from __future__ import annotations

from typing import Any

from familydb.store import db, ideas, outcomes, plans, suggestions
from familydb.suggest import taken
from tests.conftest import NOW_ISO


def _idea(conn, title: str) -> int:
    with db.transaction(conn):
        return ideas.insert(conn, title=title, kind="activity", now=NOW_ISO).id


def _asked(conn, at: str, candidates: list[dict[str, Any]], finds=(), picks=None) -> int:
    with db.transaction(conn):
        row = suggestions.insert(
            conn,
            asked_by=None,
            window_start="2026-09-26",
            window_end="2026-09-27",
            candidates=candidates,
            web_finds=list(finds),
            now=at,
        )
        if picks is not None:
            suggestions.set_picks(conn, row.id, picks)
    return row.id


def _plan(conn, title: str, at: str, idea_id: int | None = None, start="2026-09-26T10:00") -> int:
    with db.transaction(conn):
        return plans.insert(
            conn, title=title, start=start, end=None, all_day=False, idea_id=idea_id, now=at
        ).id


def _rated(conn, idea_id: int, plan_id: int | None, rating: int, on="2026-09-26") -> None:
    with db.transaction(conn):
        outcomes.insert(
            conn,
            idea_id=idea_id,
            plan_id=plan_id,
            happened_on=on,
            rating=rating,
            would_repeat=None,
            notes=None,
            recorded_by=None,
            now=NOW_ISO,
        )


def test_each_plan_is_put_down_to_where_it_stood_and_how_it_went(conn) -> None:
    zoo, museum, hike, pizza, held = (
        _idea(conn, name) for name in ("Zoo", "Museum", "Hike", "Pizza", "Held back")
    )
    first = _asked(
        conn,
        "2026-09-20T10:00:00Z",
        [
            {"idea_id": zoo, "verdict": "good", "shown": True},
            {"idea_id": museum, "verdict": "possible", "shown": True},
            {"idea_id": hike, "verdict": "ruled_out", "shown": True, "reasons": ["rain likely"]},
            {"idea_id": held, "verdict": "good", "shown": False},
        ],
        finds=[{"title": "Lantern walk", "url": "https://parks.example/lanterns"}],
        picks={"picks": [{"ref": f"idea:{pizza}", "idea_id": pizza, "slot": "new"}]},
    )
    _asked(conn, "2026-09-21T09:00:00Z", [{"idea_id": pizza, "verdict": "good", "shown": True}])
    zoo_plan = _plan(conn, "Zoo", "2026-09-20T12:00:00Z", zoo)
    _plan(conn, "Museum", "2026-09-20T12:05:00Z", museum)
    _plan(conn, "Hike", "2026-09-21T08:00:00Z", hike)
    _plan(conn, "Held back", "2026-09-21T08:10:00Z", held)
    _plan(conn, "Lantern walk!", "2026-09-21T08:20:00Z")  # a find, by its name
    _plan(conn, "Pizza", "2026-09-21T12:00:00Z", pizza)  # the later suggestion offered it
    _plan(conn, "Dentist", "2026-09-21T13:00:00Z")  # offered by nothing
    _rated(conn, zoo, zoo_plan, 9)
    _rated(conn, hike, None, 7)  # by its idea, from the plan's day on

    found = taken.report(conn, since="2026-09-01T00:00:00Z")
    assert (found.asked, found.chosen, found.led_to_plan, found.unoffered) == (2, 1, 2, 1)
    assert found.take_rate == 100
    where = {one.title: (one.source, one.suggestion_id, one.rating) for one in found.took}
    assert where["Zoo"] == ("good", first, 9)
    assert where["Museum"] == ("possible", first, None)
    assert where["Hike"] == ("ruled_out", first, 7)
    assert where["Held back"][0] == "held_back"
    assert where["Lantern walk!"][0] == "find"
    assert where["Pizza"][0] == "good"  # the latest suggestion that offered it wins
    (against,) = found.against()
    assert against.title == "Hike" and against.reason == "rain likely"
    rows = {one.key: (one.planned, one.rated, one.average) for one in found.sources()}
    assert rows["good"] == (2, 1, 9.0) and rows["ruled_out"] == (1, 1, 7.0)
    assert list(rows) == ["good", "possible", "held_back", "find", "ruled_out"]  # SOURCES order
    assert found.planned_from()[first] >= {zoo, museum, hike, held}


def test_a_pick_counts_as_the_stronger_calls_and_a_late_plan_as_nobodys(conn) -> None:
    pizza = _idea(conn, "Pizza")
    _asked(
        conn,
        "2026-09-20T10:00:00Z",
        [{"idea_id": pizza, "verdict": "good", "shown": True}],
        picks={"picks": [{"ref": f"idea:{pizza}", "idea_id": pizza, "slot": "new"}]},
    )
    _plan(conn, "Pizza", "2026-09-20T11:00:00Z", pizza)
    _plan(conn, "Pizza again", "2026-09-25T11:00:00Z", pizza)  # five days on: not hers
    found = taken.report(conn, since="2026-09-01T00:00:00Z")
    assert [one.source for one in found.took] == ["pick"] and found.unoffered == 1


def test_nothing_asked_is_an_empty_report(conn) -> None:
    found = taken.report(conn, since="2026-09-01T00:00:00Z")
    assert (found.asked, found.take_rate, found.sources(), found.against()) == (0, 0, [], [])


def test_the_wait_for_choosing_is_reported(conn) -> None:
    """Turning choosing on for "right now" adds the stronger call's wait: the report says it."""
    from familydb.store import calls

    with db.transaction(conn):
        for ms in (3000, 5400):
            calls.log_llm_call(
                conn,
                message_id=None,
                iteration=1,
                model="claude-opus-5",
                served_model=None,
                request_id=None,
                stop_reason="tool_use",
                usage={},
                duration_ms=ms,
                now="2026-09-20T10:00:00Z",
                kind="choose",
            )
    found = taken.report(conn, since="2026-09-01T00:00:00Z")
    assert (found.choosing_calls, found.choosing_wait) == (2, 4.2)


def test_an_ignored_good_idea_comes_back_sooner_than_one_passed_over(conn) -> None:
    """Shown as good and nothing came of it: it sinks for three days, then is as good as it was.
    Shown as good while the family planned something else from the same suggestion: it was
    passed over, and sinks for two weeks."""
    from datetime import UTC, datetime

    lately, a_while, passed, chosen, long_ago = (
        _idea(conn, name) for name in ("Lately", "A while", "Passed", "Chosen", "Long ago")
    )
    _asked(conn, "2026-09-19T10:00:00Z", [{"idea_id": lately, "verdict": "good", "shown": True}])
    _asked(conn, "2026-09-15T10:00:00Z", [{"idea_id": a_while, "verdict": "good", "shown": True}])
    _asked(
        conn,
        "2026-09-14T10:00:00Z",
        [
            {"idea_id": passed, "verdict": "good", "shown": True},
            {"idea_id": chosen, "verdict": "good", "shown": True},
        ],
    )
    _plan(conn, "Chosen", "2026-09-14T12:00:00Z", chosen)
    _asked(conn, "2026-09-01T10:00:00Z", [{"idea_id": long_ago, "verdict": "good"}])
    now = datetime(2026, 9, 20, 21, 3, tzinfo=UTC)
    assert taken.sinking(conn, now=now) == {lately, passed}


def test_a_find_ruled_out_and_planned_anyway_says_why(conn) -> None:
    _asked(
        conn,
        "2026-09-20T10:00:00Z",
        [],
        finds=[
            {"title": "Late show", "verdict": "ruled_out", "reasons": ["busy while it is on"]},
            {"title": "Matinee", "verdict": "good", "reasons": ["on Saturday 14:00-16:00"]},
        ],
    )
    _plan(conn, "Late show", "2026-09-20T12:00:00Z")
    _plan(conn, "Matinee", "2026-09-20T12:05:00Z")
    found = taken.report(conn, since="2026-09-01T00:00:00Z")
    where = {one.title: (one.source, one.reason) for one in found.took}
    assert where == {"Late show": ("ruled_out", "busy while it is on"), "Matinee": ("find", None)}


def test_what_became_of_her_finds_by_where_they_came_from(conn) -> None:
    from familydb.store import finds

    with db.transaction(conn):
        scouted, _ = finds.keep(
            conn,
            "web:near-home",
            "web",
            [
                finds.NewFind(title="Rose garden", url="https://a.example/"),
                finds.NewFind(title="Gig", url="https://b.example/"),
                finds.NewFind(title="Old", url="https://c.example/"),
            ],
            now="2026-09-20T10:00:00Z",
        )
        roses, gig, _ = scouted
        finds.judged(
            conn,
            [roses.id, gig.id],
            {roses.id: {"why": "w", "when": "w"}},
            now="2026-09-20T21:00:00Z",
        )
    idea = _idea(conn, "Rose garden")
    with db.transaction(conn):
        finds.mark_saved(conn, roses.id, idea_id=idea, now="2026-09-21T10:00:00Z")
        finds.mark_passed(conn, gig.id, by=None, why=None, now="2026-09-21T10:00:00Z")
    _rated(conn, idea, None, 8, on="2026-09-27")
    [scouting] = taken.origins(conn, since="2026-09-01T00:00:00Z")
    assert (scouting.label, scouting.found, scouting.recommended) == ("Her scouting", 3, 1)
    assert (scouting.saved, scouting.planned, scouting.passed) == (1, 0, 1)
    assert (scouting.rated, scouting.average) == (1, 8.0)
