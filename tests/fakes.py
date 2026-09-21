"""Scripted stand-ins for the Anthropic messages API."""

from __future__ import annotations

import json
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


def enrich_script(save_place_input: dict[str, Any]) -> list[BetaMessage]:
    """A worker that searches (paused turn), then hands back with save_place, then stops."""
    return [
        message(
            [
                server_tool_use("srvtoolu_1", "web_search", {"query": "official site"}),
                web_search_result(
                    "srvtoolu_1", [{"url": "https://example.com/place", "title": "Place"}]
                ),
            ],
            stop_reason="pause_turn",
        ),
        message([tool_use("tu_save", "save_place", save_place_input)], stop_reason="tool_use"),
        message([text("Saved.")]),
    ]


def discover_script(finds: list[dict[str, Any]]) -> list[BetaMessage]:
    """A worker that searches (paused turn), then hands back with report_finds, then stops."""
    return [
        message(
            [
                server_tool_use("srvtoolu_2", "web_search", {"query": "events this weekend"}),
                web_search_result(
                    "srvtoolu_2", [{"url": "https://example.com/events", "title": "Events"}]
                ),
            ],
            stop_reason="pause_turn",
        ),
        message([tool_use("tu_finds", "report_finds", {"finds": finds})], stop_reason="tool_use"),
        message([text("Reported.")]),
    ]


# --- OpenAI's Responses API -----------------------------------------------------------------


def oa_text(value: str) -> dict[str, Any]:
    return {
        "type": "message",
        "id": "msg_1",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": value, "annotations": []}],
    }


def oa_refusal(reason: str = "I can't help with that.") -> dict[str, Any]:
    return {
        "type": "message",
        "id": "msg_r",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "refusal", "refusal": reason}],
    }


def oa_tool_call(call_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": f"fc_{call_id}",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments),
        "status": "completed",
    }


def oa_web_call(call_id: str = "ws_1", query: str = "hopscotch portland") -> dict[str, Any]:
    return {
        "type": "web_search_call",
        "id": call_id,
        "status": "completed",
        "action": {"type": "search", "query": query},
    }


def oa_response(
    output: list[dict[str, Any]],
    *,
    status: str = "completed",
    incomplete: str | None = None,
    model: str = "gpt-5",
    usage: dict[str, Any] | None = None,
) -> Any:
    from openai.types.responses.response import Response

    payload: dict[str, Any] = {
        "id": "resp_test",
        "created_at": 0.0,
        "model": model,
        "object": "response",
        "output": output,
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "status": status,
        "usage": usage
        or {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens": 10,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 110,
        },
    }
    if incomplete:
        payload["incomplete_details"] = {"reason": incomplete}
    return Response.model_validate(payload)


class FakeResponsesAPI:
    """Scripted stand-in for `client.responses`, recording every request."""

    def __init__(self, *responses: Any) -> None:
        self.queue = list(responses)
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append({**kwargs, "input": list(kwargs.get("input", []))})
        if not self.queue:
            raise AssertionError("no scripted response left for this request")
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def openai_rate_limit() -> Any:
    import openai

    return openai.RateLimitError("slow down", response=_response(429), body=None)


def openai_server_error() -> Any:
    import openai

    return openai.InternalServerError("boom", response=_response(503), body=None)


def oa_enrich_script(save_place_input: dict[str, Any]) -> list[Any]:
    """A worker that searches, then hands back with save_place, then stops."""
    return [
        oa_response([oa_web_call("ws_1")]),
        oa_response([oa_tool_call("call_save", "save_place", save_place_input)]),
        oa_response([oa_text("Saved.")]),
    ]


def oa_discover_script(finds: list[dict[str, Any]]) -> list[Any]:
    """A worker that searches, then hands back with report_finds, then stops."""
    return [
        oa_response([oa_web_call("ws_2")]),
        oa_response([oa_tool_call("call_finds", "report_finds", {"finds": finds})]),
        oa_response([oa_text("Reported.")]),
    ]


# --- Gemini -----------------------------------------------------------------------------------


def gm_text(value: str) -> dict[str, Any]:
    return {"text": value}


def gm_tool_call(call_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"function_call": {"id": call_id, "name": name, "args": args}}


def gm_response(
    parts: list[dict[str, Any]],
    *,
    finish_reason: str = "STOP",
    model: str = "gemini-2.5-pro",
    usage: dict[str, Any] | None = None,
) -> Any:
    from google.genai import types

    return types.GenerateContentResponse.model_validate(
        {
            "candidates": [
                {"content": {"role": "model", "parts": parts}, "finish_reason": finish_reason}
            ],
            "model_version": model,
            "response_id": "resp_gm",
            "usage_metadata": usage
            or {
                "prompt_token_count": 100,
                "cached_content_token_count": 0,
                "candidates_token_count": 10,
                "total_token_count": 110,
            },
        }
    )


class FakeGeminiAPI:
    """Scripted stand-in for `client.models`, recording every request."""

    def __init__(self, *responses: Any) -> None:
        self.queue = list(responses)
        self.requests: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.requests.append({**kwargs, "contents": list(kwargs.get("contents", []))})
        if not self.queue:
            raise AssertionError("no scripted response left for this request")
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def gemini_rate_limit() -> Any:
    from google.genai import errors

    return errors.ClientError(429, {"error": {"message": "quota exceeded"}})


def gemini_server_error() -> Any:
    from google.genai import errors

    return errors.ServerError(503, {"error": {"message": "overloaded"}})


def gm_enrich_script(save_place_input: dict[str, Any]) -> list[Any]:
    """A worker that hands back with save_place, then stops. Its search happens server side."""
    return [
        gm_response([gm_tool_call("c1", "save_place", save_place_input)]),
        gm_response([gm_text("Saved.")]),
    ]
