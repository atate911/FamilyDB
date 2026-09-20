"""Scripted stand-ins for the Anthropic messages API."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import anthropic
import httpx2
from anthropic.types.beta import BetaMessage

from familydb.integrations.geocode import GeoPoint
from familydb.integrations.google_calendar import CalendarEvent
from familydb.integrations.open_meteo import DayForecast


def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


def tool_use(tool_use_id: str, name: str, input: dict[str, Any]) -> dict[str, Any]:  # noqa: A002
    return {"type": "tool_use", "id": tool_use_id, "name": name, "input": input}


def message(
    content: list[dict[str, Any]],
    *,
    stop_reason: str = "end_turn",
    usage: dict[str, int] | None = None,
    model: str = "claude-opus-5",
    stop_details: dict[str, Any] | None = None,
) -> BetaMessage:
    payload: dict[str, Any] = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 10, **(usage or {})},
    }
    if stop_details is not None:
        payload["stop_details"] = stop_details
    return BetaMessage.model_validate(payload)


class FakeMessagesAPI:
    """Returns scripted responses in order and records every request's kwargs."""

    def __init__(self, *responses: Any) -> None:
        self.queue = list(responses)
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        # Snapshot the transcript: the loop appends to the same list after this call.
        self.requests.append({**kwargs, "messages": list(kwargs.get("messages", []))})
        if not self.queue:
            raise AssertionError("no scripted response left for this request")
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _response(status: int) -> httpx2.Response:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx2.Response(status, request=request, headers={"request-id": "req_test"})


def rate_limit_error() -> anthropic.RateLimitError:
    return anthropic.RateLimitError("rate limited", response=_response(429), body=None)


def bad_request_error() -> anthropic.BadRequestError:
    return anthropic.BadRequestError("bad request", response=_response(400), body=None)


def server_error() -> anthropic.InternalServerError:
    return anthropic.InternalServerError("upstream", response=_response(503), body=None)


def connection_error() -> anthropic.APIConnectionError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=request)


class FakeCalendar:
    """In-memory CalendarAPI: enough of Google Calendar for the tools and their tests."""

    def __init__(self, tz: ZoneInfo) -> None:
        self.tz = tz
        self.events: dict[str, CalendarEvent] = {}
        self.deleted: list[str] = []
        self._counter = 0

    def _as_datetime(self, value: datetime | date, *, end: bool = False) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.combine(value, time.min, tzinfo=self.tz)

    def seed(
        self,
        title: str,
        start: datetime | date,
        end: datetime | date,
        *,
        all_day: bool = False,
        location: str | None = None,
    ) -> CalendarEvent:
        return self.insert_event(
            title=title, start=start, end=end, all_day=all_day, location=location, description=None
        )

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        found = [
            e
            for e in self.events.values()
            if self._as_datetime(e.start) < end and self._as_datetime(e.end) > start
        ]
        return sorted(found, key=lambda e: self._as_datetime(e.start))

    def insert_event(
        self,
        *,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool,
        location: str | None,
        description: str | None,
    ) -> CalendarEvent:
        self._counter += 1
        event = CalendarEvent(
            id=f"evt{self._counter}",
            title=title,
            start=start,
            end=end,
            all_day=all_day,
            location=location,
            description=description,
            link=f"https://calendar.example/evt{self._counter}",
        )
        self.events[event.id] = event
        return event

    def patch_event(self, event_id: str, **changes: Any) -> CalendarEvent:
        current = self.events[event_id]
        data = {
            "id": current.id,
            "title": changes.get("title", current.title),
            "start": changes.get("start", current.start),
            "end": changes.get("end", current.end),
            "all_day": changes.get("all_day", current.all_day),
            "location": changes.get("location", current.location),
            "description": changes.get("description", current.description),
            "status": current.status,
            "link": current.link,
        }
        event = CalendarEvent(**data)
        self.events[event_id] = event
        return event

    def delete_event(self, event_id: str) -> None:
        self.events.pop(event_id)
        self.deleted.append(event_id)


class FakeForecast:
    """In-memory ForecastAPI."""

    def __init__(self, days: list[DayForecast]) -> None:
        self.days = days
        self.calls: list[tuple[date, date]] = []

    def daily(self, start: date, end: date) -> list[DayForecast]:
        self.calls.append((start, end))
        return [d for d in self.days if start <= d.date <= end]


def server_tool_use(tool_use_id: str, name: str, input: dict[str, Any]) -> dict[str, Any]:  # noqa: A002
    return {"type": "server_tool_use", "id": tool_use_id, "name": name, "input": input}


def web_search_result(tool_use_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """A web_search_tool_result block; each result needs url and title."""
    return {
        "type": "web_search_tool_result",
        "tool_use_id": tool_use_id,
        "content": [
            {
                "type": "web_search_result",
                "url": r["url"],
                "title": r.get("title", r["url"]),
                "encrypted_content": r.get("encrypted_content", "opaque"),
                "page_age": r.get("page_age"),
            }
            for r in results
        ],
    }


class FakeGeocoder:
    """In-memory GeocoderAPI: answers from a dict of query -> GeoPoint, else a default."""

    def __init__(
        self, points: dict[str, GeoPoint] | None = None, default: GeoPoint | None = None
    ) -> None:
        self.points = {k.casefold(): v for k, v in (points or {}).items()}
        self.default = default
        self.queries: list[str] = []

    def geocode(self, query: str) -> GeoPoint | None:
        self.queries.append(query)
        return self.points.get(query.casefold(), self.default)
