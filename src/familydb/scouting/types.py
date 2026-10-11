"""What a search hands back, as code reads it (`report_finds`, tools/suggest.py)."""

from __future__ import annotations

from pydantic import BaseModel


class Found(BaseModel):
    """Something found outside the family's list: an event on a date, or a place. The engine's
    result row (suggest/types.WebFind) is one of these."""

    title: str
    url: str
    dates: str | None = None
    summary: str = ""
    source: str | None = None
    # When it starts, as code reads it ("YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"), when known.
    starts: str | None = None
    # A place found for what nothing saved fits (scouting/search.py): never checked here.
    kind: str | None = None
    hours: str | None = None  # as the page writes them
    address: str | None = None
    # Who it is for and why it suits them, as the search said (docs/FINDS.md): "grown-ups",
    # "whole family", a kid's age; a place to go any time has no day.
    for_whom: list[str] = []
    why: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    any_time: bool = False
    saved_as: int | None = None  # already on the list, as this idea
    # The stored find this is, for one the family's sources list (store/finds.py), so her picks
    # can lead to its page; never sent to the model (tools/suggest.py leaves it out).
    find_id: int | None = None
