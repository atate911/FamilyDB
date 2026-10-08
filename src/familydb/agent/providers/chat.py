"""Any service that speaks the OpenAI chat protocol (`/chat/completions`, `/models`), as a company
the settings define (config.CompanyDef): OpenRouter, DeepSeek, Moonshot, Z.ai, MiniMax, Qwen, a
model on the family's own network. One adapter, parameterised by the definition, so adding a
company is data and not a module.

What the protocol leaves to each company is data on the definition, not code here:
  * the address and the key;
  * the field a model's thinking comes back in, which some require sent back unchanged beside a
    tool call (`reasoning_fields`);
  * switches of the company's own, merged into every request (`extra_body`: OpenRouter's
    `provider` preferences, a `thinking` object), always sent;
  * its models and what they cost (`prices`), counted at the dearer unlisted price until known.

What it does not do: hosted web search (every company has its own, or none; `searches` is False and
the providers' selection hands a lookup to a company that has it), voice and photos, strict tool
schemas, prompt-cache markers (companies that cache do it by prefix on their own). A request the
company refuses naming a part of it (the replayed thinking, its extra fields) is sent again without
that part, as the other providers' are (parts.py). The extra fields are never left out that way:
one may be the family's protection (OpenRouter's refusal of services that keep what they are sent).
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Callable
from typing import Any

import openai

from familydb.agent.providers import parts
from familydb.agent.providers.base import (
    Audio,
    Heard,
    KeyCheck,
    ModelReply,
    Picture,
    Seen,
    Stop,
    Surface,
    ToolCall,
    TurnRequest,
)
from familydb.agent.providers.companies import Company
from familydb.config import Settings
from familydb.errors import AgentError

log = logging.getLogger(__name__)

# How a finish reason reads in the loop's terms. A reason not here is read by what came back.
STOPS: dict[str, Stop] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}
# A company that stopped short for a reason of its own (DeepSeek's insufficient_system_resource):
# the answer is not whole, and asking again is the remedy.
INTERRUPTED = frozenset({"insufficient_system_resource", "error"})
# Request fields the SDK takes by name; everything else in a payload goes in `extra_body`.
SDK_FIELDS = ("model", "messages", "tools", "max_tokens")
REPLAYED = "the thinking sent back"
TIMEOUT = 120.0
CHECK_TIMEOUT = 10.0
NOTHING = "no answer came back"


class ChatProvider:
    """The Provider protocol over any service speaking `chat.completions`."""

    searches = False  # no hosted web search; see the module's note

    def __init__(
        self,
        settings: Settings,
        company: Company,
        api: Any = None,
        http_client: Any = None,
        retries: int = 2,
    ) -> None:
        if company.defined is None:
            raise ValueError(f"{company.slug} is not a company the settings define")
        self.settings = settings
        self.company = company
        self.defined = company.defined
        self.name = company.slug
        self._api = api  # `client.chat.completions`, or a test's stand-in for it
        self._http = http_client  # a test's transport
        self._retries = retries  # the SDK's own, for a dropped connection, 429 or 5xx
        self._client: openai.OpenAI | None = None

    # -- the company -----------------------------------------------------------------------------

    @property
    def key(self) -> str | None:
        return self.company.key(self.settings)

    def configured(self) -> bool:
        """A key (a service on the family's own network may need none) and a model to ask."""
        injected = self._api is not None
        has_key = bool(self.key) or self.defined.local
        return injected or (has_key and bool(self.model_for("chat")))

    @property
    def client(self) -> openai.OpenAI:
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self.key or "none",  # the SDK insists on one; a local service ignores it
                base_url=self.defined.base_url,
                max_retries=self._retries,
                timeout=TIMEOUT,
                http_client=self._http,
            )
        return self._client

    @property
    def api(self) -> Any:
        if self._api is None:
            self._api = self.client.chat.completions
        return self._api

    def model_for(self, surface: Surface) -> str:
        if surface == "worker":
            return self.company.worker_model(self.settings)
        return self.company.chat_model(self.settings)

    # -- the request -----------------------------------------------------------------------------

    def messages(self, request: TurnRequest, *, replay: bool) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        system = "\n\n".join(block.text for block in request.system if block.text)
        if system:
            out.append({"role": "system", "content": system})
        out.extend({"role": message.role, "content": message.text} for message in request.messages)
        for exchange in request.exchanges:
            reply = exchange.reply
            turn: dict[str, Any] = {"role": "assistant", "content": reply.text or None}
            if reply.tool_calls:
                turn["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                    }
                    for call in reply.tool_calls
                ]
            kept = reply.raw if isinstance(reply.raw, dict) else {}
            if replay:
                turn.update(kept)  # the thinking, exactly as the company sent it
            out.append(turn)
            out.extend(
                {"role": "tool", "tool_call_id": outcome.id, "content": outcome.content}
                for outcome in exchange.outcomes
            )
        return out

    def payload(self, request: TurnRequest) -> dict[str, Any]:
        if request.web is not None:
            raise AgentError(
                f"{self.company.label} has no web search for a lookup to use",
                retryable=False,
                trouble="refused",
            )
        model = request.model or self.model_for("chat")
        left_out = parts.left_out(self.name, model)
        payload: dict[str, Any] = {
            "model": model,
            "messages": self.messages(request, replay=REPLAYED not in left_out),
            "max_tokens": request.max_tokens or self.settings.max_output_tokens,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema,
                    },
                }
                for tool in request.tools
            ]
        payload.update(self.defined.extra_body)
        return payload

    def _carried(self, payload: dict[str, Any]) -> set[str]:
        carried: set[str] = set()
        if any(
            field in message
            for message in payload["messages"]
            if message.get("role") == "assistant"
            for field in self.defined.reasoning_fields
        ):
            carried.add(REPLAYED)
        return carried

    def _parts(self) -> tuple[parts.Part, ...]:
        words = tuple(field.lower() for field in self.defined.reasoning_fields)
        return (parts.Part(REPLAYED, words),) if words else ()

    # -- the answer ------------------------------------------------------------------------------

    def reply(self, response: Any) -> ModelReply:
        choices = getattr(response, "choices", None) or []
        if not choices:
            # Some services answer 200 with the failure in the body.
            said = getattr(getattr(response, "error", None), "message", None) or NOTHING
            raise AgentError(f"{self.company.label}: {said}", retryable=True)
        choice = choices[0]
        message = choice.message
        calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=_arguments(call.function))
            for call in (getattr(message, "tool_calls", None) or [])
        ]
        finish = getattr(choice, "finish_reason", None) or "stop"
        if finish in INTERRUPTED:
            raise AgentError(f"{self.company.label} stopped short ({finish})", retryable=True)
        stop: Stop = "tool_use" if calls else STOPS.get(finish, "end")
        usage = getattr(response, "usage", None)
        cached = _cached(usage)
        prompt = getattr(usage, "prompt_tokens", None)
        return ModelReply(
            stop=stop,
            text=(getattr(message, "content", None) or "").strip(),
            tool_calls=calls,
            usage={
                # prompt_tokens counts the cached ones; the column means "everything else".
                "input_tokens": None if prompt is None else max(prompt - (cached or 0), 0),
                "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": None,
                "output_tokens": getattr(usage, "completion_tokens", None),
                "web_searches": 0,
            },
            model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None) or getattr(response, "id", None),
            refusal=finish if stop == "refusal" else None,
            raw=self._thinking(message),
        )

    def _thinking(self, message: Any) -> dict[str, Any] | None:
        """The first thinking field the answer carried, to be sent back as it came."""
        extra = getattr(message, "model_extra", None) or {}
        for field in self.defined.reasoning_fields:
            value = extra.get(field, getattr(message, field, None))
            if value:
                return {field: value}
        return None

    def send(self, request: TurnRequest) -> ModelReply:
        response, dropped = self._create(lambda: self.payload(request))
        return dataclasses.replace(self.reply(response), dropped=dropped)

    def _create(self, build: Callable[[], dict[str, Any]]) -> tuple[Any, tuple[str, ...]]:
        """One request, sent again without any part a 400 names (PARTS), each once."""
        dropped: list[str] = []
        while True:
            payload = build()
            wanted = {key: payload[key] for key in SDK_FIELDS if key in payload}
            extra = {key: value for key, value in payload.items() if key not in SDK_FIELDS}
            try:
                if extra:
                    return self.api.create(**wanted, extra_body=extra), tuple(dropped)
                return self.api.create(**wanted), tuple(dropped)
            except openai.BadRequestError as exc:
                part = parts.refused(str(exc), self._parts(), self._carried(payload))
                if part is None or part.name in dropped:
                    raise _failure(exc, self.company.label) from exc
                log.warning(
                    "%s refused %s for %s; leaving it out",
                    self.company.label,
                    part.name,
                    payload["model"],
                )
                parts.leave_out(self.name, payload["model"], part.name)
                dropped.append(part.name)
            except openai.OpenAIError as exc:
                raise _failure(exc, self.company.label) from exc

    # -- the free questions ----------------------------------------------------------------------

    def _listing(self, timeout: float) -> list[dict[str, Any]]:
        """The company's list of models, each as the company sent it (prices and all)."""
        page = self.client.with_options(timeout=timeout, max_retries=0).models.list()
        return [model.model_dump() for model in page]

    def listed_models(self) -> list[str] | None:
        try:
            return [str(row["id"]) for row in self._listing(20.0) if row.get("id")]
        except Exception as exc:  # unreachable, unauthorised: not an answer about the models
            log.info("could not ask %s for its models: %s", self.company.label, exc)
            return None

    def priced_models(self) -> dict[str, tuple[float, float, float | None]] | None:
        """What the company's own list says its models cost, in US dollars a million tokens
        (input, output, cached), for those that say; None when the list could not be had. A list
        that carries no prices (most do not) gives an empty answer."""
        try:
            rows = self._listing(20.0)
        except Exception as exc:
            log.info("could not ask %s for its prices: %s", self.company.label, exc)
            return None
        found: dict[str, tuple[float, float, float | None]] = {}
        for row in rows:
            pricing = row.get("pricing")
            if not isinstance(pricing, dict) or not row.get("id"):
                continue
            rate = _per_million(pricing.get("prompt")), _per_million(pricing.get("completion"))
            if rate[0] is None or rate[1] is None:
                continue
            found[str(row["id"]).lower()] = (
                rate[0],
                rate[1],
                _per_million(pricing.get("input_cache_read")),
            )
        return found

    def model_exists(self, model: str) -> bool | None:
        names = self.listed_models()
        if names is None:
            return None
        return model.lower() in {name.lower() for name in names}

    def check_key(self) -> KeyCheck:
        if not self.key and not self.defined.local:
            return "no_key"
        try:
            names = [str(row.get("id", "")) for row in self._listing(CHECK_TIMEOUT)]
        except openai.AuthenticationError:
            return "refused"
        except Exception as exc:  # unreachable, or a key limited to what it may read
            log.info("could not check the %s key: %s", self.company.label, exc)
            return "unchecked"
        asked = self.model_for("chat")
        if asked and names and asked.lower() not in {name.lower() for name in names}:
            return "unknown_model"
        return "works"

    def count_tokens(self, request: TurnRequest) -> int:
        raise NotImplementedError(
            f"{self.company.label} has no token-counting endpoint; send a short message to check"
        )

    # -- what it does not do ---------------------------------------------------------------------

    def listener(self) -> str | None:
        return None

    def transcribe(self, audio: Audio, hints: str) -> Heard:
        raise AgentError(f"{self.company.label} is not set up to hear voice notes", retryable=False)

    def viewer(self) -> str | None:
        return None

    def describe(self, picture: Picture, ask: str) -> Seen:
        raise AgentError(f"{self.company.label} is not set up to look at photos", retryable=False)


def _cached(usage: Any) -> int | None:
    """Prompt tokens read from the cache, under the name the company gave them: the OpenAI
    protocol's `prompt_tokens_details.cached_tokens`, or DeepSeek's `prompt_cache_hit_tokens`."""
    details = getattr(usage, "prompt_tokens_details", None)
    for found in (
        getattr(details, "cached_tokens", None),
        getattr(usage, "prompt_cache_hit_tokens", None),
    ):
        if isinstance(found, int) and not isinstance(found, bool):
            return found
    return None


def _per_million(value: Any) -> float | None:
    """A per-token price (a number or a string, as the lists give it) in dollars a million."""
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return round(amount * 1_000_000, 6) if amount >= 0 else None


def _arguments(function: Any) -> dict[str, Any]:
    """Arguments arrive as a JSON string."""
    raw = getattr(function, "arguments", None)
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        log.warning("could not read tool arguments for %s: %r", getattr(function, "name", "?"), raw)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _failure(exc: openai.OpenAIError, company: str) -> AgentError:
    """A failed request as the loop understands it. Companies disagree on what a refusal looks like:
    out of credit is a 402 at some and a 429 at others, and a 403 may be a refused key or a
    refused message."""
    if isinstance(exc, openai.APIConnectionError):  # a timeout is one
        return AgentError(f"{company}: connection error: {exc}", retryable=True)
    if isinstance(exc, openai.APIStatusError):
        status = getattr(exc, "status_code", None) or 0
        said = str(exc)
        trouble = _trouble(status, said)
        return AgentError(
            f"{company}: API error {status}: {said}",
            retryable=trouble is None and (status in (408, 409, 425, 429) or status >= 500),
            request_id=getattr(exc, "request_id", None),
            trouble=trouble,
        )
    return AgentError(f"{company}: {exc}", retryable=False)


def _trouble(status: int, said: str) -> str | None:
    """What an admin would have to fix, from a refusal."""
    lowered = said.lower()
    if status == 402 or (
        status == 429 and any(word in lowered for word in ("insufficient", "quota", "balance"))
    ):
        return "credit"
    if status == 401 or (
        status == 403 and any(word in lowered for word in ("key", "credential", "auth"))
    ):
        return "key"
    if status == 404 and "model" in lowered:
        return "model"
    if 400 <= status < 500 and status not in (408, 409, 425, 429):
        return "refused"  # something about the request this adapter cannot name
    return None
