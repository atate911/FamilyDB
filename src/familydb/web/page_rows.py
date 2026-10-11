"""The rows several pages draw: what is on (This week, a day, Now, What we did), the plans
nobody has said how they went, an idea's small row. Built here once so the pages agree."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from familydb import agenda, presents
from familydb.app import App
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.web import map_view, views
from familydb.web.rows import PlanRow, ToRate


def plan_rows(
    conn: Any,
    app: App,
    entries: list[agenda.Entry],
    today: date,
    slots: dict[str, int],
    only_for: member_store.Member | None,
    *,
    past: bool = False,
) -> list[PlanRow]:
    """What is on, with whom it is for and how far it is: what is coming, and what was too when
    `past`. With `only_for` (a kid), the ones that name her, or nobody (so everybody)."""
    rows: list[PlanRow] = []
    for entry in entries:
        if entry.days()[-1] < today and not past:
            continue
        idea = idea_store.get(conn, entry.idea_id) if entry.idea_id else None
        people = views.people_for(idea, slots)
        if only_for is not None and not views.names_in(people, only_for):
            continue
        place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
        away = map_view.away_from_home(place, app.settings)
        # A plan whose idea has since gone is still a plan, with no page to link to.
        rows.append(
            views.entry_row(entry, today, people=people, away=away, linked=idea is not None)
        )
    seen: set[str] = set()
    anchored = []
    for row in rows:  # the first plan of a day is what a link to that day lands on
        anchored.append(replace(row, anchor=row.day not in seen))
        seen.add(row.day)
    return anchored


def plan_card(
    conn: Any, app: App, plan: plan_store.Plan, today: date, slots: dict[str, int]
) -> PlanRow:
    """One plan kept here as its row, for its own page and its idea's."""
    idea = idea_store.get(conn, plan.idea_id) if plan.idea_id else None
    place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
    away = map_view.away_from_home(place, app.settings)
    people = views.people_for(idea, slots)
    return views.entry_row(
        agenda.entry_of(plan), today, people=people, away=away, linked=idea is not None
    )


# How far back a plan still waits for somebody to say how it went.
RATE_DAYS = 14


def unrated(
    conn: Any, today: date, slots: dict[str, int], who: member_store.Member | None
) -> list[ToRate]:
    """Every plan of the last two weeks nobody has said how it went, oldest first, without the
    ones made from a present kept from `who`. A plan's own page offers its faces from these."""
    waiting = presents.without(
        plan_store.unrated(
            conn,
            today=today.isoformat(),
            since=(today - timedelta(days=RATE_DAYS)).isoformat(),
        ),
        presents.kept_ids(conn, who),
    )
    found = []
    for plan in waiting:
        idea = idea_store.get(conn, plan.idea_id) if plan.idea_id else None
        day = date.fromisoformat(plan.start[:10])
        found.append(
            ToRate(
                plan_id=plan.id,
                idea_id=plan.idea_id,
                title=plan.title,
                day=plan.start[:10],
                when=views.day_short(day),
                people=views.people_for(idea, slots),
                glyph=views.glyph_for(idea.kind if idea else None),
            )
        )
    return found


def to_ask(
    app: App, conn: Any, today: date, slots: dict[str, int], who: member_store.Member | None
) -> list[ToRate]:
    """The plans the page asks how they went (Now, the board, What we did, a past day, the
    month): `unrated`, or none while the family said not to ask (`follow_ups`). How it went can
    still be told on the plan's own page, a place's page or to her."""
    return unrated(conn, today, slots, who) if app.settings.follow_ups else []


def idea_mini(conn: Any, app: App, idea: Any) -> dict[str, Any]:
    """A new idea as Home's small row: its picture, its title, and how far it is or that it has
    not been looked up."""
    place = place_store.get(conn, idea.place_id) if idea.place_id else None
    away = map_view.away_from_home(place, app.settings)
    row = views.idea_row(idea, app.settings.tzinfo)
    return {
        **row,
        "glyph": views.glyph_for(idea.kind, gift=idea_store.is_gift(idea)),
        "away": away.words if away else None,
    }
