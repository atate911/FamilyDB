"""The month as a grid of lanes: each plan laid in a lane across the days it spans, split at the
week's edge, and what a day's cell says to a screen reader. For the Plans page's Month tab."""

from __future__ import annotations

import calendar as months
from datetime import date
from typing import Any

from familydb.web.views import EVERYONE, day_short

LANES = 3
MORE_LANE = LANES + 1


def _event_slot(row: dict[str, Any]) -> int:
    """An event wears one person's colour; with several people, or everyone, it is neutral."""
    people = row["people"]
    return people[0]["slot"] if len(people) == 1 else 0


def _spoken(day: date, rows: list[dict[str, Any]], unrated: set[int]) -> str:
    """What a day's cell says to a screen reader, as there is no room to write it: "Sun 4 Oct:
    Oaks Park roller rink, 13:00, for Maya and Theo"."""
    parts = []
    for row in rows:
        said = f"{row['title']}, {row['time']}, " if row["time"] else f"{row['title']}, "
        said += f"for {row['who'] if row['who'] != EVERYONE else 'everyone'}"
        if row["id"] in unrated:
            said += ". Not rated yet"
        parts.append(said)
    return f"{day_short(day)}: " + "; ".join(parts)


def month_calendar(
    rows: list[dict[str, Any]], first: date, today: date, unrated: set[int] | None = None
) -> list[dict[str, Any]]:
    """A month as whole weeks, Monday first. Each week carries its seven days and the events that
    touch it, each placed by the column it starts in, how many days it runs inside the week and
    which of three lanes it sits in (an event over three deep is counted on its days instead). A
    plan that crosses a week is cut: one bar to each week, `to` where it goes on and `before` where
    it came from. `rows` are plan rows (`entry_row`)."""
    unrated = unrated or set()
    grid = months.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    weeks = []
    for number, week in enumerate(grid):
        start, end = week[0], week[-1]
        spans = [
            (date.fromisoformat(row["day"]), date.fromisoformat(row["end"]), row) for row in rows
        ]
        inside = [one for one in spans if one[0] <= end and one[1] >= start]
        inside.sort(key=lambda one: (one[0], -(one[1] - one[0]).days, one[2]["title"]))
        taken: list[list[tuple[int, int]]] = [[] for _ in range(LANES)]
        events: list[dict[str, Any]] = []
        overflow = [0] * 7
        for began, ended, row in inside:
            left = (max(began, start) - start).days + 1
            right = (min(ended, end) - start).days + 1
            lane = next(
                (
                    n
                    for n, used in enumerate(taken, 1)
                    if all(right < a or left > b for a, b in used)
                ),
                None,
            )
            if lane is None:
                for column in range(left, right + 1):
                    overflow[column - 1] += 1
                continue
            taken[lane - 1].append((left, right))
            events.append(
                {
                    **row,
                    "column": left,
                    "lane": lane,
                    "length": right - left + 1,
                    "to": ended > end,
                    "before": began < start,
                    "slot": _event_slot(row),
                    "past": ended < today,
                    "unrated": row["id"] in unrated,
                }
            )
        days = []
        for index, day in enumerate(week):
            today_rows = [r for b, e, r in spans if b <= day <= e]
            days.append(
                {
                    "date": day,
                    "iso": day.isoformat(),
                    "number": day.day,
                    "month": f"{day:%b}" if day.day == 1 or (number == 0 and index == 0) else None,
                    "current": day.month == first.month,
                    "today": day == today,
                    "weekend": day.weekday() >= 5,
                    # One dot for each person a plan is for, so two people never read as the house.
                    "dots": [
                        {**person, "past": day < today}
                        for r in today_rows
                        for person in (r["people"] or [people_dot()])
                    ][:3],
                    "label": _spoken(day, today_rows, unrated) if today_rows else None,
                    # The first plan that day still to be rated, so the day links to its faces.
                    "rate": next((r["id"] for r in today_rows if r["id"] in unrated), None),
                }
            )
        weeks.append(
            {
                "days": days,
                "events": events,
                "more": [
                    {"column": column + 1, "count": count}
                    for column, count in enumerate(overflow)
                    if count
                ],
            }
        )
    return weeks


def people_dot() -> dict[str, Any]:
    """The marker for a plan that is for everyone: the house."""
    return {"name": EVERYONE, "slot": 0, "initial": ""}
