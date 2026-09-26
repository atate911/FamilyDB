"""The channel-agnostic message shapes every adapter speaks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class VoiceNote:
    """A recording somebody sent, not yet heard: how long it is, and how to fetch it.

    `fetch` downloads it, and is only called once the sender is known to be family, so a
    stranger's voice note costs nothing, not even the download.
    """

    seconds: int
    mime: str
    fetch: Callable[[], bytes]
    name: str = "voice.ogg"  # with an extension that says what it is
    size: int | None = None  # in bytes, when the channel says


@dataclass(frozen=True)
class IncomingMessage:
    channel: str
    channel_update_id: str | None
    chat_id: str
    channel_user_id: str
    text: str
    # How the channel names the sender, for offering to add a stranger. Never trusted for more.
    sender_name: str | None = None
    # A voice note, for the pipeline to hear before anything is answered. `text` is then any
    # caption that came with it.
    voice: VoiceNote | None = None


@dataclass(frozen=True)
class OutgoingMessage:
    chat_id: str
    text: str
    status: Literal["ok", "refused", "failed", "unknown_sender"]
    in_message_id: int | None = None
    out_message_id: int | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    # The buttons the reply goes with, when it carries a message that had them (buttons.py).
    buttons: list[dict[str, str]] = field(default_factory=list)
