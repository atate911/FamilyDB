"""The channel-agnostic message shapes every adapter speaks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class VoiceNote:
    """A recording sent, not yet heard. `fetch` is called only once the sender is known to be
    family, so a stranger's voice note costs nothing, not even the download.
    """

    seconds: int
    mime: str
    fetch: Callable[[], bytes]
    name: str = "voice.ogg"
    size: int | None = None


@dataclass(frozen=True)
class PhotoNote:
    """A photo sent, not yet looked at. `fetch` is called only once the sender is known to be
    family.
    """

    mime: str
    fetch: Callable[[], bytes]
    size: int | None = None


@dataclass(frozen=True)
class IncomingMessage:
    channel: str
    channel_update_id: str | None
    chat_id: str
    channel_user_id: str
    text: str
    # How the channel names the sender, for offering to add a stranger. Never trusted for more.
    sender_name: str | None = None
    # A voice note for the pipeline to hear first; `text` is any caption.
    voice: VoiceNote | None = None
    # A photo, or an album's, likewise.
    photos: tuple[PhotoNote, ...] = ()


@dataclass(frozen=True)
class OutgoingMessage:
    chat_id: str
    text: str
    status: Literal["ok", "refused", "failed", "unknown_sender"]
    in_message_id: int | None = None
    out_message_id: int | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, str]] = field(default_factory=list)
