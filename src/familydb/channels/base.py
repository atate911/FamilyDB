"""The channel-agnostic message shapes every adapter speaks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class IncomingMessage:
    channel: str
    channel_update_id: str | None
    chat_id: str
    channel_user_id: str
    text: str


@dataclass(frozen=True)
class OutgoingMessage:
    chat_id: str
    text: str
    status: Literal["ok", "refused", "failed", "unknown_sender"]
    in_message_id: int | None = None
    out_message_id: int | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
