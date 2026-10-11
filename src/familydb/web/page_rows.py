"""The rows several pages draw: what is on (This week, a day, Now, What we did), the plans
nobody has said how they went, an idea's small row. Built here once so the pages agree."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from familydb import agenda, presents
from familydb.app import App
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.web import map_view, shell, views


def plan_rows(
    conn: Any,
    app: App,
    entries: list[agenda.Entry],
    today: date,
    slots: dict[str, int],
    only_for: member_store.Member | None,
    *,
    past: bool = False,
) -> list[dict[str, Any]]:
    """What is on, with whom it is for and how far it is: what is coming, and what was too when
    `past`. With `only_for` (a kid), the ones that name her, or nobody (so everybody)."""
    rows = []
    for entry in entries:
        if entry.days()[-1] < today and not past:
            continue
        idea = idea_store.get(conn, entry.idea_id) if entry.idea_id else None
        people = views.people_for(idea, slots)
        if only_for is not None and not views.names_in(people, only_for):
            continue
        place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
        away = map_view.away_from_home(place, app.settings)
        row = views.entry_row(entry, today, people=people, away=away)
        # A plan whose idea has since gone is still a plan, with no page to link to.
        row["linked"] = idea is not None
        rows.append(row)
    seen: set[str] = set()
    for row in rows:  # the first plan of a day is what a link to that day lands on
        row["anchor"] = row["day"] not in seen
        seen.add(row["day"])
    return rows


def unrated(
    conn: Any, today: date, slots: dict[str, int], who: member_store.Member | None
) -> list[dict[str, Any]]:
    """Every plan of the last two weeks nobody has said how it went, oldest first, without the
    ones made from a present kept from `who`."""
    waiting = presents.without(
        plan_store.unrated(
            conn,
            today=today.isoformat(),
            since=(today - timedelta(days=shell.RATE_DAYS)).isoformat(),
        ),
        presents.kept_ids(conn, who),
    )
    found = []
    for plan in waiting:
        idea = idea_store.get(conn, plan.idea_id) if plan.idea_id else None
        day = date.fromisoformat(plan.start[:10])
        found.append(
            {
                "plan_id": plan.id,
                "idea_id": plan.idea_id,
                "title": plan.title,
                "day": plan.start[:10],
                "when": views.day_short(day),
                "people": views.people_for(idea, slots),
                "glyph": views.glyph_for(idea.kind if idea else None),
            }
        )
    return found


def to_rate(
    conn: Any, today: date, slots: dict[str, int], who: member_store.Member | None
) -> dict[str, Any] | None:
    """The oldest plan nobody has said how it went, for Home's three faces, and how many more."""
    waiting = unrated(conn, today, slots, who)
    return {**waiting[0], "more": len(waiting) - 1} if waiting else None


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
