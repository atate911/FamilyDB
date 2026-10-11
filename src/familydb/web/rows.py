"""The typed rows the family's pages draw, one dataclass a kind, so a view, a template and a
test name the same fields and a missing one is an error, not an empty cell. Built in `views.py`
and `page_rows.py`; a template reads them as attributes (`row.title`); code that needs a mapping
(to lay more over one) takes `as_dict`."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanRow:
    """What is on, as every page draws it (This week, a day, the board, Plans, the month, Now's
    lines, a plan's own page): a plan kept here or an event read from Google."""

    id: int | None  # the plan's; None for an event from Google alone
    idea_id: int | None
    title: str
    when: str  # "Saturday 3 October, 6:30 pm", or the days a long one runs
    time: str | None  # "6:30 pm"; None all day
    relative: str | None  # "today", "in 3 days", "now" while it runs
    chip: dict[str, Any] | None  # the tear-off date: weekday, day, month
    on_today: bool
    all_day: bool
    location: str | None
    notes: str | None
    status: str  # confirmed, tentative, cancelled
    from_google: bool  # made elsewhere: shown, not movable here
    start_value: str  # for a datetime-local box
    end_value: str | None
    people: list[dict[str, Any]]  # who it is for, each with their colour; Everyone when nobody
    who: str  # the same as words
    away: str | None  # how far, in words
    day: str  # the first day, ISO
    end: str  # the last day, ISO
    short: str  # "Sun 27 Sep"
    linked: bool = True  # its idea still exists, so the title opens it
    anchor: bool = False  # the first plan of its day: what a link to the day lands on


@dataclass(frozen=True)
class ToRate:
    """A plan nobody has said how it went: the question Now, This week, the month and What we did
    ask, and the faces that answer it."""

    plan_id: int
    idea_id: int | None
    title: str
    day: str
    when: str
    people: list[dict[str, Any]]
    glyph: str
    more: int = 0  # how many others wait behind it, where only the first is shown


def as_dict(row: Any) -> dict[str, Any]:
    """A row's fields as a mapping, shallow, for a view that lays more over it."""
    return {one.name: getattr(row, one.name) for one in dataclasses.fields(row)}
