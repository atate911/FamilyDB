"""The provider-neutral types the loop speaks in; each provider translates to and from its API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Stop = Literal["end", "tool_use", "refusal", "max_tokens", "paused"]
Surface = Literal["chat", "worker"]
# `Provider.check_key`'s answer. Only "refused" is a definite no; "unchecked" is no answer.
KeyCheck = Literal["works", "refused", "unknown_model", "unchecked", "no_key"]


@dataclass(frozen=True)
class SystemBlock:
    """A piece of the system prompt; `cacheable` is ignored by providers that cache on their own."""

    text: str
    cacheable: bool = False


@dataclass(frozen=True)
class Message:
    """A turn of the conversation; parts of the newest go as separate blocks where supported."""

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
    """Hosted search and page reading for a worker turn; never the chat surface."""

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
    """One answer from a model, in the loop's terms."""

    stop: Stop
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int | None] = field(default_factory=dict)
    model: str | None = None
    request_id: str | None = None
    refusal: str | None = None
    raw: Any = None  # the provider's own assistant output, replayed when resuming a paused turn
    # Parts the company refused and the request was resent without (providers/parts.py).
    dropped: tuple[str, ...] = ()


@dataclass(frozen=True)
class Audio:
    """A recording to be heard, as its channel handed it over."""

    data: bytes
    mime: str  # what the channel says it is, e.g. audio/ogg
    seconds: int
    name: str = "voice.ogg"  # one vendor goes by the extension


@dataclass(frozen=True)
class Heard:
    """The words a model heard in a recording, or saw in a picture, and what that cost."""

    text: str
    usage: dict[str, int | None] = field(default_factory=dict)
    model: str | None = None
    request_id: str | None = None
    # As a reply's `stop`: a refusal or cut-short answer is still billed, so it comes back.
    stop: Stop = "end"
    dropped: tuple[str, ...] = ()  # as a reply's: parts of the request left out on refusal


Seen = Heard


@dataclass(frozen=True)
class Picture:
    """A photo to be looked at, as its channel handed it over."""

    data: bytes
    mime: str  # image/jpeg, image/png or image/webp


# Output room for a picture's description plus thinking.
LOOK_TOKENS = 1024


@dataclass
class Exchange:
    """An assistant answer and the tool results sent back to it."""

    reply: ModelReply
    outcomes: list[ToolOutcome] = field(default_factory=list)


@dataclass
class TurnRequest:
    """Everything one call needs; the loop appends to `exchanges`."""

    system: list[SystemBlock]
    messages: list[Message]
    tools: list[ToolDef] = field(default_factory=list)
    web: WebAccess | None = None
    model: str | None = None
    effort: str | None = None
    max_tokens: int | None = None
    exchanges: list[Exchange] = field(default_factory=list)


class Provider(Protocol):
    """A model vendor; one module beside this file each."""

    name: str

    def configured(self) -> bool:
        """Whether credentials are present; False means try the other provider."""
        ...

    def model_for(self, surface: Surface) -> str: ...

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        """The request as it would be sent (`debug prompt`, `send`)."""
        ...

    def send(self, request: TurnRequest) -> ModelReply:
        """One round trip; raises AgentError (with `retryable`) on failure."""
        ...

    def model_exists(self, model: str) -> bool | None:
        """Whether the vendor knows this model. None when it cannot be asked: never a no. Free."""
        ...

    def listed_models(self) -> list[str] | None:
        """Every model name listed for this key, as sent (model_watch.py). None when it cannot be
        asked: never "none". Free."""
        ...

    def check_key(self) -> KeyCheck:
        """Whether the vendor takes this key, by looking the chat model up (free); for the
        company-and-key form."""
        ...

    def count_tokens(self, request: TurnRequest) -> int:
        """Input tokens this request would cost; `validate-tools` uses it to check schemas."""
        ...

    def listener(self) -> str | None:
        """The model that hears recordings, or None."""
        ...

    def transcribe(self, audio: Audio, hints: str) -> Heard:
        """The words in a recording; `hints` names people and places. A declined request comes
        back with its `stop`."""
        ...

    def viewer(self) -> str | None:
        """The model that looks at pictures (the lookup model), or None."""
        ...

    def describe(self, picture: Picture, ask: str) -> Seen:
        """What a picture shows, as `ask` asks, in one request; a declined one comes back with its
        `stop`."""
        ...
