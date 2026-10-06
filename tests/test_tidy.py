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
