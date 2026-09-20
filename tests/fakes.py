"""Scripted stand-ins for the Anthropic messages API."""

from __future__ import annotations

from typing import Any

import anthropic
import httpx2
from anthropic.types.beta import BetaMessage


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
