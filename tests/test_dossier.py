"""The dossier the stronger call chooses from: what goes in it, what never does, and its bounds."""

from __future__ import annotations

from datetime import datetime

from familydb.integrations.open_meteo import DayForecast
from familydb.store import ideas, memories, messages, outcomes, plans
from familydb.store.db import transaction
from familydb.suggest import dossier
from familydb.suggest.engine import assess
from familydb.suggest.types import SuggestInput
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO, TZ

EARLIER_TODAY = "2026-09-24T20:00:00Z"  # Thursday 13:00 in Vancouver
SAT_FORECAST = DayForecast(
    datetime(2026, 9, 26).date(), 1, "mainly clear", 19.0, 9.0, 5, 0.0, 7 * 60, 19 * 60
)


def _setup(conn, family, *, chat="-100", text="what should we do this weekend?"):
    with transaction(conn):
        conn.execute(
            "UPDATE members SET birth_date = '2016-04-02' WHERE id = ?", (family["girls"].id,)
        )
        ramen = ideas.insert(conn, title="Ramen at Menya", kind="restaurant", now=NOW_ISO)
        zoo = ideas.insert(conn, title="Oregon Zoo", kind="outing", setting="outdoor", now=NOW_ISO)
        ideas.insert(conn, title="Ski day", kind="outing", seasons=["winter"], now=NOW_ISO)
        for idea, rating, notes in ((ramen, 9, "the girls loved it"), (zoo, 6, "too crowded")):
            outcome = outcomes.insert(
                conn,
                idea_id=idea.id,
                plan_id=None,
                happened_on="2026-06-13",
                rating=rating,
                would_repeat=None,
                notes=notes,
                recorded_by=family["sam"].id,
                now=NOW_ISO,
            )
            ideas.apply_outcome(
                conn,
                idea.id,
                happened_on=outcome.happened_on,
                avg_rating=float(rating),
                now=NOW_ISO,
            )
        memories.insert(
            conn,
            member_id=family["alex"].id,
            category="health",
            fact="allergic to shellfish",
            firm=True,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=None,
        )
        memories.insert(
            conn,
            member_id=None,
            category="food",
            fact="we like noodles",
            firm=False,
            inferred=False,
            until=None,
            source_message_id=None,
            said_by=None,
        )
        messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="x1",
            chat_id="1001",
            member_id=family["sam"].id,
            text="a secret from Sam's own chat",
            now=EARLIER_TODAY,
        )
        messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="g1",
            chat_id=chat,
            member_id=family["alex"].id,
            text="we're wiped this week",
            now=EARLIER_TODAY,
        )
        asked = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="g2",
            chat_id=chat,
            member_id=family["sam"].id,
            text=text,
            now=EARLIER_TODAY,
        )
    return asked, ramen, zoo


def _build(conn, settings, clock, family, asked):
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=family["sam"],
        message_id=asked.id,
        calendar=fakes.FakeCalendar(TZ),
        weather=fakes.FakeForecast([SAT_FORECAST]),
    )
    args = SuggestInput(window="this_weekend", question="what should we do?", discover=False)
    a = assess(ctx, args)
    return dossier.build(ctx, args, a), a


def test_it_carries_what_the_family_knows_and_cites_it(conn, full_settings, thursday_clock, family):
    asked, ramen, zoo = _setup(conn, family)
    made, _ = _build(conn, full_settings, thursday_clock, family, asked)
    text = made.text
    assert f"idea:{ramen.id}" in made.options and f"idea:{zoo.id}" in made.options
    assert made.options[f"idea:{ramen.id}"].done_before
    assert '"the girls loved it"' in text and "rated 9/10" in text
    assert "allergic to shellfish (must)" in text and "we like noodles" in text
    assert "we're wiped this week" in text  # this chat
    assert "everyone in it reads your reply, kids among them" in text
    assert "the girls (kid), 10" in text and "2016-04-02" not in text  # an age, never a birthday
    assert "daylight 07:00-19:00" in text
    assert any(c.startswith("m") for c in made.cites) and any(c.startswith("o") for c in made.cites)


def test_never_another_chat_and_never_what_was_ruled_out_as_an_option(
    conn, full_settings, thursday_clock, family
):
    asked, *_ = _setup(conn, family)
    made, a = _build(conn, full_settings, thursday_clock, family, asked)
    assert "a secret from Sam's own chat" not in made.text
    ski = next(c for c in a.candidates if c.title == "Ski day")
    assert ski.verdict == "ruled_out" and f"idea:{ski.idea_id}" not in made.options
    assert f"idea:{ski.idea_id} Ski day" in made.text  # shown for context only


def test_the_same_question_builds_the_same_words(conn, full_settings, thursday_clock, family):
    asked, *_ = _setup(conn, family)
    first, _ = _build(conn, full_settings, thursday_clock, family, asked)
    again, _ = _build(conn, full_settings, thursday_clock, family, asked)
    assert first.text == again.text


def test_it_stays_within_its_bounds_and_keeps_every_firm_memory(
    conn, full_settings, thursday_clock, family
):
    asked, *_ = _setup(conn, family)
    with transaction(conn):
        for n in range(80):
            ideas.insert(
                conn,
                title=f"Idea number {n} with a long and realistic name",
                kind="outing",
                now=NOW_ISO,
            )
        for n in range(60):
            memories.insert(
                conn,
                member_id=None,
                category="other",
                fact=f"a taste of ours, number {n}, " + "x" * 80,
                firm=False,
                inferred=False,
                until=None,
                source_message_id=None,
                said_by=None,
            )
        for n in range(8):
            memories.insert(
                conn,
                member_id=None,
                category="health",
                fact=f"never number {n}",
                firm=True,
                inferred=False,
                until=None,
                source_message_id=None,
                said_by=None,
            )
    made, _ = _build(conn, full_settings, thursday_clock, family, asked)
    assert len(made.text) <= dossier.TOTAL + 1000  # the headings, and firm memories beyond the cap
    assert made.sizes["options"] <= dossier.CAPS["options"] + 100
    assert all(f"never number {n} (must)" in made.text for n in range(8))
    assert "more not shown)" in made.text


def test_plans_around_the_question_are_in_it(conn, full_settings, thursday_clock, family):
    asked, *_ = _setup(conn, family)
    with transaction(conn):
        plans.insert(
            conn,
            idea_id=None,
            title="Soccer tournament",
            start="2026-09-27T09:00:00-07:00",
            end="2026-09-27T15:00:00-07:00",
            all_day=False,
            location=None,
            notes=None,
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
    made, _ = _build(conn, full_settings, thursday_clock, family, asked)
    assert "Soccer tournament (planned)" in made.text
