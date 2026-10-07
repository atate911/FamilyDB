"""The To do page, a to-do's own Edit page, and Plans as a month and as a list."""

from __future__ import annotations

import re
from datetime import date

from familydb.store import db, ideas, outcomes, plans, tasks
from familydb.web import views
from tests.conftest import NOW_ISO
from tests.test_web_edits import _client


def _row(day, end=None, *, title="Event", slot=1, rid=1):
    return {
        "id": rid,
        "title": title,
        "day": day,
        "end": end or day,
        "people": [{"name": "Sam", "slot": slot, "initial": "S"}],
        "who": "Sam",
        "time": "",
    }


# -- the month


def test_a_plan_over_a_week_end_is_cut_into_one_bar_to_each_week() -> None:
    weeks = views.month_calendar(
        [_row("2026-10-02", "2026-10-06", title="Camping")], date(2026, 10, 1), date(2026, 10, 20)
    )
    bars = [(w["events"][0]["column"], w["events"][0]["length"]) for w in weeks if w["events"]]
    assert bars == [(5, 3), (1, 2)]  # Fri to Sun, then Mon and Tue
    first, second = (w["events"][0] for w in weeks if w["events"])
    assert first["to"] and not first["before"] and second["before"] and not second["to"]
    assert all(e["past"] for w in weeks for e in w["events"])  # both ended before the 20th


def test_a_fourth_plan_on_a_day_is_counted_not_drawn() -> None:
    rows = [_row("2026-10-07", title=f"Plan {n}", rid=n) for n in range(1, 6)]
    week = next(
        w for w in views.month_calendar(rows, date(2026, 10, 1), date(2026, 10, 1)) if w["events"]
    )
    assert [e["lane"] for e in week["events"]] == [1, 2, 3]
    assert week["more"] == [{"column": 3, "count": 2}]  # the Wednesday


def test_a_day_says_what_is_on_it_and_what_is_still_to_rate() -> None:
    rows = [_row("2026-10-07", title="Roller rink", rid=7)]
    weeks = views.month_calendar(rows, date(2026, 10, 1), date(2026, 10, 20), {7})
    day = next(d for w in weeks for d in w["days"] if d["iso"] == "2026-10-07")
    assert "Roller rink" in day["label"] and "Not rated yet" in day["label"]
    assert day["rate"] == 7 and day["dots"][0]["slot"] == 1
    other = next(d for w in weeks for d in w["days"] if d["iso"] == "2026-10-08")
    assert other["label"] is None and other["dots"] == []


def test_a_day_draws_a_dot_for_each_person_and_the_house_only_for_everyone() -> None:
    two = {**_row("2026-10-04", title="Roller rink", rid=1)}
    two["people"] = [
        {"name": "Maya", "slot": 3, "initial": "M"},
        {"name": "Theo", "slot": 4, "initial": "T"},
    ]
    everyone = {**_row("2026-10-05", title="Picnic", rid=2)}
    everyone["people"] = [{"name": views.EVERYONE, "slot": 0, "initial": ""}]
    weeks = views.month_calendar([two, everyone], date(2026, 10, 1), date(2026, 10, 20))
    days = {d["iso"]: d for w in weeks for d in w["days"]}
    assert [dot["initial"] for dot in days["2026-10-04"]["dots"]] == ["M", "T"]
    assert [dot["name"] for dot in days["2026-10-05"]["dots"]] == [views.EVERYONE]


def test_a_plan_rated_from_the_month_goes_back_to_the_month(settings, clock, conn, family) -> None:
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        plan = plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=idea.id,
        )
    client = _client(settings, clock)
    month = client.get("/plans/month").text
    assert "Silver Falls hike" in month and "Not great" in month
    form = re.search(r'<li class="rate" id="r-\d+">.*?</form>', month, re.S).group(0)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', form))
    assert fields["back"] == "plans" and fields["plan_id"] == str(plan.id)
    sent = client.post(f"/idea/{idea.id}/outcome", data={**fields, "went": "ok"})
    assert (
        sent.headers["Location"].startswith("/plans/month") and "#rate" in sent.headers["Location"]
    )
    assert [o.rating for o in outcomes.list_for_idea(conn, idea.id)] == [6]


# -- to-dos


def _make(conn, title="Bins out", **changes):
    with db.transaction(conn):
        return tasks.insert(
            conn,
            title=title,
            notes="",
            owner_id=changes.pop("owner_id", None),
            due_at=None,
            preferred_window="",
            operation_key=title,
            channel="web",
            chat_id="web",
            now=NOW_ISO,
            **changes,
        )


def test_a_to_do_has_its_own_page_to_edit_with_a_way_back(settings, clock, conn, family) -> None:
    task_id = _make(conn)
    client = _client(settings, clock)
    list_page = client.get("/tasks").text
    assert f'href="/task/{task_id}/edit"' in list_page
    assert f'action="/task/{task_id}/edit"' not in list_page  # the boxes are on its own page
    page = client.get(f"/task/{task_id}/edit")
    assert page.status_code == 200 and 'value="Bins out"' in page.text
    assert 'href="/tasks"' in page.text  # the way back
    assert client.get("/task/9999/edit").status_code == 404


def test_open_to_dos_are_late_first_then_yours_then_by_day() -> None:
    from datetime import date as day_of
    from zoneinfo import ZoneInfo

    from familydb.store.tasks import Task

    def task(number, owner, due):
        return Task(
            id=number,
            title=f"t{number}",
            owner_id=owner,
            due_at=due,
            channel="web",
            chat_id="web",
            created_at=NOW_ISO,
            updated_at=NOW_ISO,
        )

    found = [
        task(1, 2, "2026-09-30T17:00:00Z"),  # someone else's, soon
        task(2, 1, None),  # mine, no date
        task(3, 2, "2026-09-10T17:00:00Z"),  # someone else's, late
        task(4, 1, "2026-10-05T17:00:00Z"),  # mine, later
        task(5, 1, "2026-09-12T17:00:00Z"),  # mine, late
    ]
    ordered = views.todo_order(found, ZoneInfo("America/Vancouver"), day_of(2026, 9, 20), me=1)
    assert [t.id for t in ordered] == [5, 3, 4, 2, 1]


def test_the_adder_always_offers_everyone_and_the_tool_takes_it(settings, clock, conn, family):
    from familydb.tools import ToolContext, build_registry

    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    made = build_registry().dispatch("add_task", {"title": "Renew cards", "owner": "Everyone"}, ctx)
    assert not made.is_error and tasks.get(conn, 1).owner_id is None
