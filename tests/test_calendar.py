import json
from datetime import date, datetime, timedelta

from familydb.integrations.google_calendar import CalendarEvent, event_body, parse_event
from familydb.store import ideas, plans
from familydb.tools import ToolContext, ToolRegistry
from familydb.tools.gcal import free_blocks, on_day
from tests import fakes
from tests.conftest import NOW_ISO, TZ


def _ctx(conn, calendar_settings, clock, family, calendar) -> ToolContext:
    return ToolContext(
        conn=conn, settings=calendar_settings, clock=clock, member=family["sam"], calendar=calendar
    )


def _call(registry: ToolRegistry, ctx: ToolContext, name: str, **payload):
    result = registry.dispatch(name, payload, ctx)
    return result, json.loads(result.content)


def test_parse_event_timed_and_all_day() -> None:
    timed = parse_event(
        {
            "id": "e1",
            "summary": "Symphony",
            "start": {"dateTime": "2026-09-27T03:00:00Z"},
            "end": {"dateTime": "2026-09-27T05:30:00Z"},
            "location": "Concert hall",
            "htmlLink": "https://cal/e1",
        },
        TZ,
    )
    assert timed.all_day is False
    assert timed.start == datetime(2026, 9, 26, 20, 0, tzinfo=TZ)
    assert timed.end.hour == 22 and timed.end.minute == 30
    assert timed.location == "Concert hall"
    whole = parse_event(
        {"id": "e2", "start": {"date": "2026-09-26"}, "end": {"date": "2026-09-27"}}, TZ
    )
    assert whole.all_day is True
    assert whole.title == "(no title)"
    assert (whole.start, whole.end) == (date(2026, 9, 26), date(2026, 9, 27))


def test_event_body_shapes() -> None:
    start = datetime(2026, 9, 26, 20, 0, tzinfo=TZ)
    body = event_body(
        tz=TZ, title="Symphony", start=start, end=start + timedelta(hours=2), all_day=False
    )
    assert body["start"] == {
        "dateTime": "2026-09-26T20:00:00-07:00",
        "timeZone": "America/Vancouver",
    }
    body = event_body(tz=TZ, start=date(2026, 9, 26), end=date(2026, 9, 27), all_day=True)
    assert body == {"start": {"date": "2026-09-26"}, "end": {"date": "2026-09-27"}}
    assert event_body(tz=TZ, title="x") == {"summary": "x"}


def test_free_blocks_and_on_day() -> None:
    day = date(2026, 9, 26)
    at = lambda h, m=0: datetime(2026, 9, 26, h, m, tzinfo=TZ)  # noqa: E731
    events = [
        CalendarEvent("a", "Dentist", at(10), at(11), False),
        CalendarEvent("b", "Grandma visiting", day, day + timedelta(days=1), True, busy=False),
    ]
    assert free_blocks(events, day, TZ) == ["afternoon", "evening"]
    events.append(CalendarEvent("c", "Dinner", at(16, 30), at(18), False))
    assert free_blocks(events, day, TZ) == []
    assert on_day(events[1], day, TZ) and not on_day(events[1], day + timedelta(days=1), TZ)
    late = CalendarEvent("d", "Party", at(23), datetime(2026, 9, 27, 1, tzinfo=TZ), False)
    assert on_day(late, day, TZ) and on_day(late, day + timedelta(days=1), TZ)


def test_get_calendar_reports_days(registry, conn, calendar_settings, clock, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    calendar.seed(
        "Dentist", datetime(2026, 9, 26, 10, tzinfo=TZ), datetime(2026, 9, 26, 11, tzinfo=TZ)
    )
    calendar.seed(
        "Grandparents dinner",
        datetime(2026, 9, 27, 18, tzinfo=TZ),
        datetime(2026, 9, 27, 21, tzinfo=TZ),
        location="Their place",
    )
    calendar.seed("Sam away", date(2026, 9, 27), date(2026, 9, 28), all_day=True)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    result, data = _call(registry, ctx, "get_calendar", start="2026-09-26", end="2026-09-27")
    assert not result.is_error, data
    assert [d["weekday"] for d in data["days"]] == ["Saturday", "Sunday"]
    saturday, sunday = data["days"]
    assert saturday["events"] == [
        {"title": "Dentist", "start": "10:00", "end": "11:00", "location": None}
    ]
    assert saturday["free"] == ["afternoon", "evening"]
    assert sunday["all_day"] == ["Sam away"]
    assert sunday["free"] == []  # a busy all-day event takes the whole day
    result, data = _call(registry, ctx, "get_calendar", start="2026-09-27", end="2026-09-26")
    assert result.is_error and "before start" in data["error"]


def test_calendar_tools_report_unavailable_without_a_client(
    registry, conn, calendar_settings, clock, family, settings
) -> None:
    ctx = _ctx(conn, calendar_settings, clock, family, calendar=None)
    result, data = _call(registry, ctx, "get_calendar", start="2026-09-26", end="2026-09-27")
    assert not result.is_error and data["available"] is False
    plain = ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=family["sam"],
        calendar=fakes.FakeCalendar(TZ),
    )
    result, data = _call(registry, plain, "get_calendar", start="2026-09-26", end="2026-09-27")
    assert not result.is_error and data["available"] is False  # settings say not configured


def test_create_event_links_idea_and_stores_plan(
    registry, conn, calendar_settings, clock, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, idea = _call(registry, ctx, "add_idea", title="Vancouver Symphony", kind="show")
    result, data = _call(
        registry,
        ctx,
        "create_event",
        title="Vancouver Symphony",
        start="2026-09-26T20:00",
        idea_id=idea["id"],
        location="Concert hall",
    )
    assert not result.is_error, data
    plan = data["plan"]
    assert plan["start"] == "2026-09-26T20:00-07:00"
    assert plan["end"] == "2026-09-26T22:00-07:00"
    assert plan["all_day"] is False and plan["google_event_id"] == "evt1"
    assert plan["calendar_id"] == "family@group.calendar.google.com"
    assert data["idea"]["status"] == "planned"
    assert data["event"]["link"].endswith("evt1")
    stored = calendar.events["evt1"]
    assert (
        stored.start == datetime(2026, 9, 26, 20, tzinfo=TZ) and stored.location == "Concert hall"
    )
    assert plans.for_idea(conn, idea["id"])[0].id == plan["id"]
    assert result.summary["plan_id"] == plan["id"]
    assert result.summary["idea_id"] == idea["id"]


def test_create_event_all_day_past_and_unknown_idea(
    registry, conn, calendar_settings, clock, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, data = _call(
        registry, ctx, "create_event", title="Camping", start="2026-10-03", end="2026-10-04"
    )
    assert data["plan"]["all_day"] is True
    assert (data["plan"]["start"], data["plan"]["end"]) == ("2026-10-03", "2026-10-04")
    assert calendar.events["evt1"].end == date(2026, 10, 5)  # exclusive end for Google
    result, data = _call(registry, ctx, "create_event", title="Old", start="2026-09-01T10:00")
    assert result.is_error and "in the past" in data["error"]
    result, data = _call(
        registry, ctx, "create_event", title="Nope", start="2026-10-10T10:00", idea_id=99
    )
    assert result.is_error and "no idea #99" in data["error"]
    assert len(calendar.events) == 1  # no orphan event was created


def test_update_and_cancel_event(registry, conn, calendar_settings, clock, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, idea = _call(registry, ctx, "add_idea", title="The falls hike", kind="outing")
    _, created = _call(
        registry,
        ctx,
        "create_event",
        title="Falls hike",
        start="2026-09-26T10:00",
        idea_id=idea["id"],
    )
    plan_id = created["plan"]["id"]
    result, data = _call(
        registry,
        ctx,
        "update_event",
        plan_id=plan_id,
        start="2026-09-27T09:00",
        end="2026-09-27T12:00",
        title="Falls hike (moved)",
    )
    assert not result.is_error, data
    assert data["plan"]["start"] == "2026-09-27T09:00-07:00"
    assert calendar.events["evt1"].title == "Falls hike (moved)"
    assert calendar.events["evt1"].start == datetime(2026, 9, 27, 9, tzinfo=TZ)
    result, data = _call(registry, ctx, "update_event", plan_id=plan_id)
    assert result.is_error and "nothing to change" in data["error"]
    result, data = _call(registry, ctx, "update_event", plan_id=plan_id, status="cancelled")
    assert not result.is_error
    assert data["plan"]["status"] == "cancelled"
    assert data["idea"]["status"] == "idea"
    assert calendar.deleted == ["evt1"]
    result, data = _call(registry, ctx, "update_event", plan_id=plan_id, title="x")
    assert result.is_error and "cancelled" in data["error"]
    result, data = _call(registry, ctx, "delete_event", plan_id=999)
    assert result.is_error and "no plan #999" in data["error"]


def test_delete_event(registry, conn, calendar_settings, clock, family) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, created = _call(registry, ctx, "create_event", title="Camping", start="2026-10-03")
    result, data = _call(registry, ctx, "delete_event", plan_id=created["plan"]["id"])
    assert not result.is_error and data["plan"]["status"] == "cancelled"
    assert calendar.events == {}
    result, data = _call(registry, ctx, "delete_event", plan_id=created["plan"]["id"])
    assert data["note"] == "already cancelled"


def test_plans_repository(conn, family) -> None:
    from familydb.store.db import transaction

    with transaction(conn):
        idea = ideas.insert(conn, title="Camping", kind="trip", now=NOW_ISO)
        plan = plans.insert(
            conn,
            title="Camping",
            start="2026-10-03",
            end="2026-10-04",
            all_day=True,
            idea_id=idea.id,
            now=NOW_ISO,
        )
        moved = plans.update(
            conn, plan.id, {"start": "2026-10-10", "end": "2026-10-11"}, now=NOW_ISO
        )
    assert moved.start == "2026-10-10"
    assert [p.id for p in plans.for_idea(conn, idea.id)] == [plan.id]
    assert [p.id for p in plans.list_between(conn, "2026-10-01", "2026-11-01")] == [plan.id]


def test_moving_only_the_start_keeps_the_duration(
    registry, conn, calendar_settings, clock, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, created = _call(
        registry,
        ctx,
        "create_event",
        title="Hike",
        start="2026-09-26T09:00",
        end="2026-09-26T13:00",
    )
    _, moved = _call(
        registry, ctx, "update_event", plan_id=created["plan"]["id"], start="2026-09-27T10:00"
    )
    assert (moved["plan"]["start"], moved["plan"]["end"]) == (
        "2026-09-27T10:00-07:00",
        "2026-09-27T14:00-07:00",
    )
    _, trip = _call(
        registry, ctx, "create_event", title="Trip", start="2026-10-02", end="2026-10-05"
    )
    _, moved = _call(registry, ctx, "update_event", plan_id=trip["plan"]["id"], start="2026-10-03")
    assert (moved["plan"]["start"], moved["plan"]["end"]) == ("2026-10-03", "2026-10-06")
    assert calendar.events["evt2"].end == date(2026, 10, 7)


def test_converting_all_day_to_timed_needs_a_time(
    registry, conn, calendar_settings, clock, family
) -> None:
    calendar = fakes.FakeCalendar(TZ)
    ctx = _ctx(conn, calendar_settings, clock, family, calendar)
    _, created = _call(registry, ctx, "create_event", title="Fair", start="2026-10-10")
    result, data = _call(
        registry, ctx, "update_event", plan_id=created["plan"]["id"], all_day=False
    )
    assert result.is_error and "start time" in data["error"]
    _, timed = _call(
        registry,
        ctx,
        "update_event",
        plan_id=created["plan"]["id"],
        all_day=False,
        start="2026-10-10T19:00",
    )
    assert timed["plan"]["all_day"] is False and timed["plan"]["start"] == "2026-10-10T19:00-07:00"
    assert calendar.events["evt1"].all_day is False


def test_patch_body_clears_the_unused_time_key() -> None:
    body = event_body(
        tz=TZ,
        start=date(2026, 10, 10),
        end=date(2026, 10, 11),
        all_day=True,
        clear_other_time_key=True,
    )
    assert body["start"] == {"date": "2026-10-10", "dateTime": None, "timeZone": None}
    start = datetime(2026, 10, 10, 19, tzinfo=TZ)
    body = event_body(
        tz=TZ, start=start, end=start + timedelta(hours=2), all_day=False, clear_other_time_key=True
    )
    assert body["start"]["date"] is None and body["start"]["dateTime"].startswith(
        "2026-10-10T19:00"
    )


def test_google_delete_tolerates_missing_events(calendar_settings) -> None:
    import httplib2
    from googleapiclient.errors import HttpError

    from familydb.errors import ToolError
    from familydb.integrations.google_calendar import GoogleCalendar

    class Request:
        def __init__(self, status):
            self.status = status

        def execute(self):
            if self.status:
                raise HttpError(httplib2.Response({"status": self.status}), b"gone")
            return {}

    class Events:
        def __init__(self, status):
            self.status = status

        def delete(self, **_kwargs):
            return Request(self.status)

    client = GoogleCalendar(calendar_settings)
    client._events = lambda: Events(410)  # already deleted by hand
    client.delete_event("evt1")
    client._events = lambda: Events(403)
    try:
        client.delete_event("evt1")
    except ToolError as exc:
        assert "403" in str(exc)
    else:
        raise AssertionError("a 403 must still be reported")


def test_create_event_records_the_originating_chat(
    registry, conn, calendar_settings, clock, family
) -> None:
    from familydb.store import db, messages

    with db.transaction(conn):
        inbound = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="u9",
            chat_id="-100",
            member_id=family["sam"].id,
            text="symphony saturday",
            now=NOW_ISO,
        )
    ctx = _ctx(conn, calendar_settings, clock, family, fakes.FakeCalendar(TZ))
    ctx.message_id = inbound.id
    _, data = _call(registry, ctx, "create_event", title="Symphony", start="2026-09-26T20:00")
    assert data["plan"]["channel"] == "telegram" and data["plan"]["chat_id"] == "-100"
