"""What a search is told about the family (scouting/brief.py): who they are without a name, their
musts and tastes, where they go, and what they have, never a present, and capped."""

from __future__ import annotations

from datetime import date

from familydb.scouting.brief import CAPS, brief
from familydb.store import db, finds, ideas, memories, outcomes
from tests.conftest import NOW_ISO

TODAY = date(2026, 9, 20)


def _memory(conn, member, fact, *, firm, category="food"):
    memories.insert(
        conn,
        member_id=member.id if member else None,
        category=category,
        fact=fact,
        firm=firm,
        inferred=False,
        until=None,
        source_message_id=None,
        said_by=None,
        now=NOW_ISO,
    )


def test_the_family_is_said_without_a_name_or_a_present(conn, settings, family):
    with db.transaction(conn):
        conn.execute(
            "UPDATE members SET birth_date = '2015-06-01' WHERE id = ?", (family["girls"].id,)
        )
        _memory(conn, family["alex"], "Alex never eats peanuts", firm=True)
        _memory(conn, None, "We love ramen", firm=False)
        _memory(conn, family["sam"], "Sam's birthday surprise is a kayak", firm=True)
        _memory(conn, family["sam"], "Sam sleeps late", firm=False, category="routine")
        noodles = ideas.insert(conn, title="Noodle bar", kind="restaurant", now=NOW_ISO)
        ideas.insert(conn, title="Kayak for Sam", kind="gift", now=NOW_ISO)
        outcomes.insert(
            conn,
            idea_id=noodles.id,
            plan_id=None,
            happened_on="2026-08-01",
            rating=9,
            would_repeat=None,
            notes=None,
            recorded_by=None,
        )
        [passed], _ = finds.keep(
            conn,
            "request",
            "request",
            [finds.NewFind(title="Loud gig", url="https://g.example")],
            now="1",
        )
        finds.mark_passed(conn, passed.id, by=None, why="too loud for Alex", now="2026-09-01")
    told = brief(
        conn,
        settings.model_copy(
            update={"home_area": "Vancouver, WA", "scouting_areas": "Portland\n\nthe Pearl"}
        ),
        today=TODAY,
    )
    text = told.text
    assert "- 2 grown-ups; 1 kid, aged 11" in text
    assert "- a grown-up: a grown-up never eats peanuts" in text
    assert "- the family: We love ramen" in text and "- loved: Noodle bar (restaurant)" in text
    assert "- they go to: Portland" in text and "- they go to: the Pearl" in text
    assert "- Loud gig: too loud for a grown-up" in text
    for kept_back in ("Alex", "Sam", "kayak", "Kayak", "sleeps late"):
        assert kept_back not in text
    # What a cached search is known by leaves out what is already found or passed on.
    assert "Loud gig" not in told.steady and "Noodle bar" in told.steady
    assert brief(conn, settings, today=TODAY) == brief(conn, settings, today=TODAY)


def test_each_part_is_capped_at_a_whole_line(conn, settings, family):
    with db.transaction(conn):
        for number in range(200):
            ideas.insert(conn, title=f"Idea number {number:03d}", kind="outing", now=NOW_ISO)
    text = brief(conn, settings, today=TODAY).text
    have = text.split("Already on their list (look for something new):\n")[1].split("\n\n")[0]
    assert len(have) <= CAPS["have"] + 30 and have.splitlines()[-1].startswith("- … and ")


def test_the_search_leans_towards_what_they_saved_of_what_was_found(conn, settings, family):
    with db.transaction(conn):
        kept, _ = finds.keep(
            conn,
            "web:near-home",
            "web",
            [
                finds.NewFind(title="Pottery night", url="https://clay.example/", category="Class"),
                finds.NewFind(title="Wine walk", url="https://wine.example/"),
            ],
            now="2026-09-01T00:00:00Z",
        )
        finds.mark_saved(conn, kept[0].id, idea_id=None, now="2026-09-10T00:00:00Z")
    text = brief(conn, settings, today=TODAY).text
    liked = text.split("What they saved of what was found before (more like these):\n")[1]
    assert liked.startswith("- Pottery night (Class)") and "Wine walk" not in liked
