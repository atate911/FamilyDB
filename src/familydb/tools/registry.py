"""Tool registry: what the model may call, input validation, dispatch and result shaping."""

from __future__ import annotations

import dataclasses
import inspect
import json
import logging
import sqlite3
import time
import typing
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from familydb.agent.providers.base import ToolDef
from familydb.clock import Clock
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import ToolError, ToolUnavailable
from familydb.store import calls
from familydb.store.db import transaction
from familydb.store.members import Member
from familydb.tools.schema import strict_schema

log = logging.getLogger(__name__)


OFFERED = "offered_reply"
# Where the inverse of a write is left for dispatch to keep (tool_calls.undo).
UNDO = "undo"
Source = Literal["chat", "tap", "page", "command", "job", "worker", "cli"]


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
    geocoder: Any = None  # integrations.geocode.Geocoder, when available
    api: Any = None  # a test's stand-in model, for tools that run a worker turn (discovery)
    discover_cache: Any = None  # the App-level cache of discovery results
    allowed_tools: frozenset[str] | None = None
    worker_idea_id: int | None = None
    operation_id: str | None = None  # durable browser write operation, not model input
    resume_scope: str | None = None  # the browser session, to resume what a lost reply left
    idea_revision: str | None = None  # browser optimistic concurrency precondition
    task_revision: int | None = None
    # Whom the idea form chose to keep a present from (member ids); None where it chose nobody.
    # Kept out of the model's tool schemas: only the page sets it.
    hidden_from: list[int] | None = None
    scratch: dict[str, Any] = field(default_factory=dict)  # per-turn hand-back area
    # The turn the calls belong to (set by the loop) and what a worker turn is about, for status.
    turn: str | None = None
    about: str | None = None
    # A kid reads the chat (audience.plain): code speaks plainly of the workings.
    plain: bool = False
    # The time asked about counts as free, plans and all: the evening check's backup asks about a
    # plan's own time, which the plan itself would fill (jobs/plan_checks.py).
    ignore_busy: bool = False
    # Where the call comes from, kept with it (tool_calls.source): the chat's model, a button
    # tapped, a page form, a command, a job, a worker turn, the command line.
    source: Source = "chat"
    # The call a page's or a button's Undo names (tool_calls.id); never the tool's input.
    undo_target: int | None = None

    def now_iso(self) -> str:
        return utc_iso(self.clock.now())

    def offer_reply(self, text: str) -> None:
        """Hand the family's reply over with a tool's input; the loop may end the turn with it."""
        self.scratch[OFFERED] = text

    def take_reply(self) -> str | None:
        return self.scratch.pop(OFFERED, None)


@dataclass(frozen=True)
class ToolResult:
    content: str
    is_error: bool = False
    summary: dict[str, Any] = field(default_factory=dict)
    # The tool_calls row it was kept as (dispatch), and whether it can be taken back (undo.py).
    call_id: int | None = None
    undoable: bool = False


Handler = Callable[[ToolContext, Any], Any]
Availability = Callable[[Settings], bool]


def always(_settings: Settings) -> bool:
    return True


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
        """Declared tools sorted by name. Worker turns pass their subset in `names`; without it,
        the chat list, which leaves out `worker_only` tools (input tokens on every message). The
        list never varies between turns, so the prompt cache holds."""
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

    def dispatch(
        self,
        name: str,
        raw_input: Any,
        ctx: ToolContext,
        *,
        call_id: str | None = None,
        iteration: int = 0,
    ) -> ToolResult:
        """Run one tool as `ctx` says, and keep the call (tool_calls), whoever made it and from
        where: the one place every tool call is recorded, with the inverse a write left
        (`UNDO` in `ctx.scratch`). `call_id` is the model's id for the call, or a tap's."""
        ctx.scratch.pop(UNDO, None)
        started = time.monotonic()
        result = self._run(name, raw_input, ctx)
        undo = ctx.scratch.pop(UNDO, None)
        values = {
            "message_id": ctx.message_id,
            "iteration": iteration,
            "tool_use_id": call_id,
            "tool_name": name,
            "input": raw_input,
            "output": result.content,
            "is_error": result.is_error,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "now": ctx.now_iso(),
            "turn": ctx.turn,
            "member_id": ctx.member.id if ctx.member else None,
            "source": ctx.source,
            "undo": None if result.is_error else undo,
        }
        if ctx.conn.in_transaction:  # part of the caller's work, which commits it
            row = calls.log_tool_call(ctx.conn, **values)
        else:
            with transaction(ctx.conn):
                row = calls.log_tool_call(ctx.conn, **values)
        return dataclasses.replace(result, call_id=row, undoable=values["undo"] is not None)

    def _run(self, name: str, raw_input: Any, ctx: ToolContext) -> ToolResult:
        if ctx.allowed_tools is not None and name not in ctx.allowed_tools:
            return _error(name, "tool is not permitted in this turn")
        spec = self._specs.get(name)
        if spec is None:
            return _error(name, f"unknown tool {name!r}")
        # Strict mode sends null for an absent field, at any depth; dropping them applies defaults.
        raw_input = without_nulls(raw_input)
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
            for key in ("plan", "idea", "outcome", "place", "suggestion", "task", "wish"):
                nested = result.get(key)
                if isinstance(nested, dict) and "id" in nested:
                    summary[f"{key}_id"] = nested["id"]
        return ToolResult(dump(result), False, summary)


def without_nulls(value: Any) -> Any:
    """`value` without null object fields at any depth; a null list item stays. A strict schema
    makes the model send every field, null for one it means to leave out, so a tool's input is
    read through this (and the evals' graders read it the same way)."""
    if isinstance(value, dict):
        return {key: without_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value]
    return value


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
