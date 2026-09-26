"""Tool registry: what the model may call, input validation, dispatch and result shaping."""

from __future__ import annotations

import inspect
import json
import logging
import sqlite3
import typing
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from familydb.agent.providers.base import ToolDef
from familydb.clock import Clock
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import ToolError, ToolUnavailable
from familydb.store.members import Member
from familydb.tools.schema import strict_schema

log = logging.getLogger(__name__)


# Where a tool leaves a reply it offers to end the turn with (`ToolContext.offer_reply`).
OFFERED = "offered_reply"


@dataclass
class ToolContext:
    """What a tool handler gets: a connection, settings, the clock, and who is asking."""

    conn: sqlite3.Connection
    settings: Settings
    clock: Clock
    member: Member | None = None
    message_id: int | None = None
    calendar: Any = None  # a CalendarAPI (integrations.google_calendar) when connected
    weather: Any = None  # a ForecastAPI (integrations.open_meteo) when configured
    geocoder: Any = None  # a GeocoderAPI (integrations.geocode) when available
    api: Any = None  # a test's stand-in model, for tools that run a worker turn (discovery)
    discover_cache: Any = None  # the App-level cache of discovery results
    allowed_tools: frozenset[str] | None = None
    worker_idea_id: int | None = None
    operation_id: str | None = None  # durable browser write operation, not model input
    resume_scope: str | None = None  # the browser session, to resume what a lost reply left
    idea_revision: str | None = None  # browser optimistic concurrency precondition
    task_revision: int | None = None
    scratch: dict[str, Any] = field(default_factory=dict)  # per-turn hand-back area

    def now_iso(self) -> str:
        return utc_iso(self.clock.now())

    def offer_reply(self, text: str) -> None:
        """A tool that can be all a turn does hands the family's reply over with its input; the
        loop ends the turn with it when nothing else ran in that step (see `run_turn`)."""
        self.scratch[OFFERED] = text

    def take_reply(self) -> str | None:
        return self.scratch.pop(OFFERED, None)


@dataclass(frozen=True)
class ToolResult:
    content: str
    is_error: bool = False
    summary: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[ToolContext, Any], Any]
Availability = Callable[[Settings], bool]


def always(_settings: Settings) -> bool:
    return True


def never(_settings: Settings) -> bool:
    return False


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Handler
    available: Availability = always
    unavailable_reason: str = "not available yet"
    writes: bool = False
    worker_only: bool = False  # declared to its worker turn, never to the chat model

    def api_definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": strict_schema(self.input_model),
            "strict": True,
        }


def dump(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, default=str)


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._definitions: dict[str, dict[str, Any]] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"duplicate tool {spec.name!r}")
        self._specs[spec.name] = spec
        self._definitions[spec.name] = spec.api_definition()

    def tool(
        self,
        *,
        name: str,
        description: str,
        input_model: type[BaseModel] | None = None,
        available: Availability = always,
        unavailable_reason: str = "not available yet",
        writes: bool = False,
        worker_only: bool = False,
    ) -> Callable[[Handler], Handler]:
        """Register a handler. The input model comes from its second parameter's annotation."""

        def decorator(handler: Handler) -> Handler:
            self.register(
                ToolSpec(
                    name=name,
                    description=description,
                    input_model=input_model or _infer_input_model(handler),
                    handler=handler,
                    available=available,
                    unavailable_reason=unavailable_reason,
                    writes=writes,
                    worker_only=worker_only,
                )
            )
            return handler

        return decorator

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def specs(self) -> list[ToolSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def names(self) -> list[str]:
        return sorted(self._specs)

    def tool_defs(self, names: Iterable[str] | None = None) -> list[ToolDef]:
        """Declared tools sorted by name, in terms no vendor owns. Stable across chat turns.

        Worker turns pass their subset in `names`. Without `names` this is the chat list, which
        leaves out the hand-back tools only a worker ever calls: they cost input tokens on every
        message and the chat model must not use them. Either way the list is the same from turn
        to turn, so the prompt cache still holds.
        """
        if names is None:
            wanted = sorted(name for name, spec in self._specs.items() if not spec.worker_only)
        else:
            wanted = sorted(names)
        unknown = set(wanted) - set(self._specs)
        if unknown:
            raise ValueError(f"unknown tools: {sorted(unknown)}")
        return [
            ToolDef(
                name=name,
                description=self._specs[name].description,
                schema=self._definitions[name]["input_schema"],
            )
            for name in wanted
        ]

    def dispatch(self, name: str, raw_input: Any, ctx: ToolContext) -> ToolResult:
        if ctx.allowed_tools is not None and name not in ctx.allowed_tools:
            return _error(name, "tool is not permitted in this turn")
        spec = self._specs.get(name)
        if spec is None:
            return _error(name, f"unknown tool {name!r}")
        # A provider whose strict mode forbids an absent field sends null instead. Dropping
        # those lets the input model's own default apply, as it does everywhere else.
        if isinstance(raw_input, dict):
            raw_input = {key: value for key, value in raw_input.items() if value is not None}
        try:
            args = spec.input_model.model_validate(raw_input or {})
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in exc.errors(include_url=False)
            )
            return _error(name, f"invalid input: {problems}")
        if not spec.available(ctx.settings):
            return _unavailable(name, spec.unavailable_reason)
        if ctx.worker_idea_id is not None and getattr(args, "idea_id", None) != ctx.worker_idea_id:
            return _error(name, "worker may only write its assigned idea")
        try:
            result = spec.handler(ctx, args)
        except ToolUnavailable as exc:
            return _unavailable(name, str(exc))
        except ToolError as exc:
            return _error(name, str(exc))
        except Exception as exc:
            log.exception("tool %s failed", name)
            return _error(name, f"internal error: {type(exc).__name__}")
        summary: dict[str, Any] = {"tool": name, "ok": True}
        if isinstance(result, dict):
            for key in ("id", "duplicate_of"):
                if key in result:
                    summary[key] = result[key]
            for key in ("plan", "idea", "outcome", "place", "suggestion", "task"):
                nested = result.get(key)
                if isinstance(nested, dict) and "id" in nested:
                    summary[f"{key}_id"] = nested["id"]
        return ToolResult(dump(result), False, summary)


def _infer_input_model(handler: Handler) -> type[BaseModel]:
    params = list(inspect.signature(handler).parameters)
    hints = typing.get_type_hints(handler)
    model = hints.get(params[1]) if len(params) > 1 else None
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"{handler.__name__}: second parameter must be annotated with a BaseModel")
    return model


def _error(name: str, message: str) -> ToolResult:
    return ToolResult(dump({"error": message}), True, {"tool": name, "ok": False, "error": message})


def _unavailable(name: str, reason: str) -> ToolResult:
    payload = {"available": False, "tool": name, "reason": reason}
    return ToolResult(dump(payload), False, {"tool": name, "ok": False, "unavailable": True})


REGISTRY = ToolRegistry()
tool = REGISTRY.tool
