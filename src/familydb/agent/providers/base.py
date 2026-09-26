"""What the agent loop knows about a model provider, and nothing more.

The loop speaks in these types; each provider translates them into its own API and back. Keeping
the conversation provider-neutral is what lets a turn start again on the other provider when one
is failing, and what keeps the loop free of any one vendor's response shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Stop = Literal["end", "tool_use", "refusal", "max_tokens", "paused"]
Surface = Literal["chat", "worker"]
# What a vendor said about a key when asked the free way (`Provider.check_key`). Only "refused"
# is a definite no; "unchecked" covers everything that is not an answer, such as no network, a
# timeout, or a key allowed to write replies but not to list models.
KeyCheck = Literal["works", "refused", "unknown_model", "unchecked", "no_key"]


@dataclass(frozen=True)
class SystemBlock:
    """A piece of the system prompt. `cacheable` marks a prefix worth caching where that is paid
    for explicitly; providers that cache on their own ignore it."""

    text: str
    cacheable: bool = False


@dataclass(frozen=True)
class Message:
    """A turn of the conversation. Several parts are sent as separate blocks where that is
    supported, so the date line and the message itself stay distinguishable."""

    role: Literal["user", "assistant"]
    parts: list[str]

    @property
    def text(self) -> str:
        return "\n\n".join(self.parts)


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class WebAccess:
    """Hosted search and page reading for a worker turn. Never granted to the chat surface."""

    max_uses: int | None = None
    user_location: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolOutcome:
    id: str
    content: str
    is_error: bool = False
    name: str = ""  # which tool answered; some providers match on the name, not the id


@dataclass(frozen=True)
class ModelReply:
    """One answer from a model, in the only terms the loop cares about."""

    stop: Stop
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int | None] = field(default_factory=dict)
    model: str | None = None
    request_id: str | None = None
    refusal: str | None = None
    raw: Any = None  # the provider's own assistant output, replayed when resuming a paused turn


@dataclass(frozen=True)
class Audio:
    """A recording to be heard, such as a voice note, as its channel handed it over."""

    data: bytes
    mime: str  # what the channel says it is, e.g. audio/ogg
    seconds: int
    name: str = "voice.ogg"  # with the right extension: one vendor goes by it


@dataclass(frozen=True)
class Heard:
    """The words a model heard in a recording, and what hearing them cost."""

    text: str
    usage: dict[str, int | None] = field(default_factory=dict)
    model: str | None = None
    request_id: str | None = None


@dataclass
class Exchange:
    """An assistant answer and the tool results sent back to it."""

    reply: ModelReply
    outcomes: list[ToolOutcome] = field(default_factory=list)


@dataclass
class TurnRequest:
    """Everything one call needs. The loop appends to `exchanges` as the turn goes on."""

    system: list[SystemBlock]
    messages: list[Message]
    tools: list[ToolDef] = field(default_factory=list)
    web: WebAccess | None = None
    model: str | None = None
    effort: str | None = None
    max_tokens: int | None = None
    exchanges: list[Exchange] = field(default_factory=list)


class Provider(Protocol):
    """A model vendor. Implementations live beside this file, one per vendor."""

    name: str

    def configured(self) -> bool:
        """Whether credentials are present. False means try the other provider, not fail."""
        ...

    def model_for(self, surface: Surface) -> str:
        """The model this provider uses for chat or for the mechanical worker turns."""
        ...

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        """The request as it would be sent. Used by `familydb debug prompt` and by send()."""
        ...

    def send(self, request: TurnRequest) -> ModelReply:
        """One round trip. Raises AgentError, with `retryable` set, for anything that failed."""
        ...

    def model_exists(self, model: str) -> bool | None:
        """Whether the vendor knows this model name. None when it cannot be asked (no key, no
        network), which must never be taken as a no. Costs no tokens."""
        ...

    def check_key(self) -> KeyCheck:
        """Whether the vendor takes this key, found by looking the chat model up: the same free
        question as `model_exists`, read for what it says about the key instead. For the setup
        page, which checks a key before storing it."""
        ...

    def count_tokens(self, request: TurnRequest) -> int:
        """What this request would cost in input tokens. Also how `validate-tools` checks the
        schemas: the API rejects a malformed tool before counting anything."""
        ...

    def listener(self) -> str | None:
        """The model this vendor hears recordings with, or None when it cannot hear at all."""
        ...

    def transcribe(self, audio: Audio, hints: str) -> Heard:
        """The words in a recording. `hints` names people and places it may mention, so they
        are spelled as the family spells them. Raises AgentError, with `retryable` set."""
        ...
