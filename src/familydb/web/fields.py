"""What the settings page shows, and how a filled-in form becomes settings again.

The shape of each box comes from `Settings` itself: a Literal becomes a dropdown, a bool a
yes/no, a number a number box. Only the label and the sentence under it are written out here, so
a changed Literal can never leave the page offering something the setting will not take.

Everything here is a pure function over strings: the routes do the storing.
"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from typing import Any, Literal

from familydb.agent.providers.prices import suggestions
from familydb.config import Settings
from familydb.store.settings import BEHAVIOUR

NUMBER = {"int": "a whole number", "float": "a number"}
NOT_A_NUMBER = "That needs to be {what}."
TOO_LONG = "That is longer than a setting should be."
MAX_LENGTH = 400


@dataclass(frozen=True)
class Field:
    """One box on the settings page."""

    key: str
    label: str
    note: str
    kind: str  # choice, toggle, int, float or text
    choices: tuple[str, ...] = ()
    # Offered as the box is typed in, without limiting it: a model released next week still fits.
    suggested: tuple[str, ...] = ()


def _bare(annotation: Any) -> Any:
    """An annotation with any Annotated metadata (a range, say) taken off the front."""
    return typing.get_args(annotation)[0] if hasattr(annotation, "__metadata__") else annotation


def _members(annotation: Any) -> list[Any]:
    """The parts of a union, flattened, with None dropped. A plain type is its own part."""
    annotation = _bare(annotation)
    if typing.get_origin(annotation) in (types.UnionType, typing.Union):
        return [_bare(part) for part in typing.get_args(annotation) if part is not type(None)]
    return [annotation]


def _shape(annotation: Any) -> tuple[str, tuple[str, ...]]:
    """How to draw a box for this annotation.

    An empty string is never offered as a choice: leaving the box alone already means "whatever
    the environment says", and two ways to say nothing would only be confusing.
    """
    parts = _members(annotation)
    if parts and all(typing.get_origin(part) is Literal for part in parts):
        allowed = [str(value) for part in parts for value in typing.get_args(part) if value != ""]
        return "choice", tuple(allowed)
    if bool in parts:
        return "toggle", ("true", "false")
    if int in parts:
        return "int", ()
    if float in parts:
        return "float", ()
    return "text", ()


def _rules(annotation: Any) -> list[Any]:
    """Every constraint on an annotation, including one tucked inside an Optional.

    A range written as `Field(ge=..., le=...)` arrives wrapped in a FieldInfo, which carries the
    constraints in a list of its own; unwrap that so both spellings read the same.
    """
    carriers = list(getattr(annotation, "__metadata__", ()))
    inner = _bare(annotation)
    if typing.get_origin(inner) in (types.UnionType, typing.Union):
        for part in typing.get_args(inner):
            carriers.extend(getattr(part, "__metadata__", ()))
    found: list[Any] = []
    for carrier in carriers:
        found.extend(getattr(carrier, "metadata", None) or [carrier])
    return found


def limits(key: str) -> str:
    """What the setting will take, read off the setting itself rather than written out again."""
    one = Settings.model_fields[key]
    low: Any = None
    high: Any = None
    over = False  # whether the bottom of the range is one the setting will not actually take
    for rule in [*one.metadata, *_rules(one.annotation)]:
        if low is None:
            low = getattr(rule, "ge", None)
            if low is None:
                low = getattr(rule, "gt", None)
                over = low is not None
        if high is None:
            high = getattr(rule, "le", getattr(rule, "lt", None))
    if low is None and high is None:
        return ""
    if low is None:
        return f"At most {high}."
    if high is None:
        return f"More than {low}." if over else f"At least {low}."
    return f"More than {low}, up to {high}." if over else f"Between {low} and {high}."


def field(
    key: str,
    label: str,
    note: str = "",
    choices: tuple[str, ...] = (),
    suggested: tuple[str, ...] = (),
) -> Field:
    kind, derived = _shape(Settings.model_fields[key].annotation)
    return Field(
        key=key,
        label=label,
        note=" ".join(part for part in (note, limits(key)) if part),
        kind=kind,
        choices=choices or derived,
        suggested=suggested,
    )


MODEL_NOTE = "Pick one or type any model name the company offers; the cheapest are listed first."


# The page, in the order it reads. Every name in BEHAVIOUR appears exactly once; a test says so.
GROUPS: tuple[tuple[str, str, tuple[Field, ...]], ...] = (
    (
        "Who answers",
        "Which model writes the replies, and which one does the looking up.",
        (
            field("provider", "Chat model company", "Who answers a message in the chat."),
            field(
                "worker_provider",
                "Lookup company",
                "Who looks places up on the web. Leave it alone to use the same one.",
            ),
            field(
                "provider_fallback",
                "Ask the other one when the first cannot",
                "Only ever before anything has been done, so nothing happens twice.",
            ),
            field(
                "openai_model", "OpenAI: chat model", MODEL_NOTE, suggested=suggestions("openai")
            ),
            field("openai_worker_model", "OpenAI: lookup model", suggested=suggestions("openai")),
            field("anthropic_model", "Claude: chat model", suggested=suggestions("anthropic")),
            field(
                "worker_model",
                "Claude: lookup model",
                "A smaller one is usually plenty.",
                suggested=suggestions("anthropic"),
            ),
            field("gemini_model", "Gemini: chat model", suggested=suggestions("gemini")),
            field("gemini_worker_model", "Gemini: lookup model", suggested=suggestions("gemini")),
        ),
    ),
    (
        "What it may spend",
        "The settings that decide what a message costs. Lower is cheaper and usually enough.",
        (
            field(
                "daily_spend_limit",
                "Daily spending limit (US$)",
                "Estimated across every model call; it stops answering until midnight once "
                "reached. 0 means no limit. Set a limit on the API key with the company too.",
            ),
            field("effort", "Chat thinking", "How long it may think before answering."),
            field("worker_effort", "Lookup thinking"),
            field("max_output_tokens", "Longest answer", "In tokens. An answer is rarely near it."),
            field(
                "agent_max_iterations",
                "Tool rounds per message",
                "How many times it may use a tool before it has to answer.",
            ),
            field("worker_max_iterations", "Tool rounds per lookup"),
            field(
                "anthropic_cache_ttl",
                "Claude prompt cache",
                "How long Claude keeps the unchanging part of the prompt. 1h costs less overall.",
            ),
            field(
                "prompt_idea_limit",
                "Ideas sent with every message",
                "The newest this many; the rest are still found by searching. 0 means all of them.",
            ),
            field("history_limit", "Chat turns remembered"),
            field(
                "history_hours",
                "Hours of chat remembered",
                "0 makes every message stand on its own, with no conversation behind it.",
            ),
        ),
    ),
    (
        "Looking things up",
        "The separate turns that may read the web to fill an idea in.",
        (
            field(
                "web_tools_enabled",
                "Look ideas up on the web",
                "Off means no idea is ever enriched and nothing new is discovered.",
            ),
            field("enrich_interval_minutes", "Minutes between lookups"),
            field("enrich_batch", "Ideas looked up at a time"),
            field("enrichment_notes", "Say in the chat when an idea is filled in"),
            field(
                "place_stale_days",
                "Days before details look old",
                "After this the page marks hours and prices as worth re-checking.",
            ),
        ),
    ),
    (
        "Home",
        "Where the family is, which decides the weather, the travel estimates and what is nearby.",
        (
            field(
                "family_tz",
                "Timezone",
                "An IANA name such as America/Vancouver. Dates, the digest and follow-ups "
                "keep this clock.",
            ),
            field("home_area", "Home area", "In words, as you would tell someone: town and state."),
            field("home_lat", "Latitude", "Negative south of the equator."),
            field("home_lon", "Longitude", "Negative west of Greenwich."),
            field("weather_units", "Units"),
            field("travel_speed_kmh", "Assumed driving speed (km/h)"),
            field("road_factor", "Road detour factor", "1.0 is a straight line; 1.3 is usual."),
            field("google_calendar_id", "Google calendar id", "The shared family calendar."),
        ),
    ),
    (
        "When it speaks first",
        "The messages the bot sends without being asked, and what it does after a failure.",
        (
            field(
                "digest_chat_id",
                "Digest chat",
                "Choose from the chats it has seen, or type a Telegram chat id. A group is offered"
                " once somebody on the family list has written in it. Empty sends no digest.",
            ),
            field("digest_day", "Digest day"),
            field("digest_hour", "Digest hour", "24-hour clock, in the family's timezone."),
            field("follow_up_hour", "Follow-up hour", "When it asks how yesterday's plan went."),
            field("retry_interval_minutes", "Minutes between retries"),
            field("retry_max_attempts", "Retries before giving up"),
        ),
    ),
    (
        "This page",
        "",
        (
            field("web_title", "What the page calls itself"),
            field("web_session_days", "Days a sign-in lasts"),
            field(
                "log_level",
                "Log detail",
                "DEBUG is loud; INFO is the usual one.",
                choices=("DEBUG", "INFO", "WARNING", "ERROR"),
            ),
        ),
    ),
)

FIELDS: tuple[Field, ...] = tuple(one for _, _, group in GROUPS for one in group)
BY_KEY: dict[str, Field] = {one.key: one for one in FIELDS}


def parse(one: Field, given: str) -> Any:
    """One box as the value it stands for. Empty means no override: the environment's again.

    Raises ValueError with a sentence the family can act on.
    """
    text = given.strip()
    if not text:
        return None
    if len(text) > MAX_LENGTH:
        raise ValueError(TOO_LONG)
    if one.kind == "toggle":
        return text == "true"
    if one.kind in NUMBER:
        try:
            return int(text) if one.kind == "int" else float(text)
        except ValueError:
            raise ValueError(NOT_A_NUMBER.format(what=NUMBER[one.kind])) from None
    return text


def read_form(form: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Every box the form carried, as values and as complaints. Absent boxes are left alone."""
    values: dict[str, Any] = {}
    problems: dict[str, str] = {}
    for one in FIELDS:
        if one.key not in form:
            continue
        try:
            values[one.key] = parse(one, form[one.key])
        except ValueError as exc:
            problems[one.key] = str(exc)
    return values, problems


def shown(one: Field, override: Any) -> str:
    """What to put in the box: the stored value, or nothing when there is no override."""
    if override is None:
        return ""
    return str(override).lower() if one.kind == "toggle" else str(override)


def placeholder(one: Field, fallback: Any) -> str:
    """What the box says when it is empty: what the family gets without an override."""
    if fallback is None or fallback == "":
        return "not set"
    return str(fallback).lower() if one.kind == "toggle" else str(fallback)


__all__ = [
    "BEHAVIOUR",
    "BY_KEY",
    "FIELDS",
    "GROUPS",
    "Field",
    "parse",
    "placeholder",
    "read_form",
    "shown",
]
