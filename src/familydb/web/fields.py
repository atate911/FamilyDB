"""What the settings pages show, and how a filled-in form becomes settings again.

The settings are split into sections, one page each (`SECTIONS`), and on each page the boxes sit
in groups under a heading (`GROUPS`); a group of fine-tuning is folded away until somebody opens
it. The shape of each box comes from `Settings` itself: a Literal becomes a dropdown, a bool a
yes/no, a number a number box. Only the label, the sentence under it and the words a choice is
shown in are written out here, so a changed Literal can never leave the page offering something
the setting will not take.

Everything here is a pure function over strings: the routes do the storing.
"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from typing import Any, Literal
from zoneinfo import available_timezones

from familydb.agent.providers.prices import hearing_suggestions, suggestions
from familydb.config import Settings
from familydb.store.settings import BEHAVIOUR
from familydb.web.views import DAY_NAMES

NUMBER = {"int": "a whole number", "float": "a number"}
NOT_A_NUMBER = "That needs to be {what}."
TOO_LONG = "That is longer than a setting should be."
MAX_LENGTH = 400
# The three companies by the names the page gives them everywhere, setup included.
COMPANIES = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google"}
# The zones worth offering: places, not the legacy aliases and offsets.
ZONE_PREFIXES = ("Africa/", "America/", "Antarctica/", "Asia/", "Atlantic/", "Australia/")
ZONE_PREFIXES += ("Europe/", "Indian/", "Pacific/")


@dataclass(frozen=True)
class Field:
    """One box on a settings page."""

    key: str
    label: str
    note: str
    kind: str  # choice, toggle, int, float or text
    choices: tuple[str, ...] = ()
    # Offered as the box is typed in, without limiting it: a model released next week still fits.
    suggested: tuple[str, ...] = ()
    # The words a value is shown in where the stored one would not read well: "thu", "true".
    words: tuple[tuple[str, str], ...] = ()
    # What having no value means, where "not set" would not say: no lookup company is the chat's.
    unset: str = ""
    # For a model box, whose model it is, so the company answering can be shown first.
    company: str = ""
    # The keyboard a phone offers for it: digits, digits and a point, or all of it.
    keyboard: str = ""

    def word(self, value: str) -> str:
        """A value as the page says it."""
        return dict(self.words).get(value, value)


@dataclass(frozen=True)
class Section:
    """One page of the settings, and its line in the list of them."""

    name: str  # its address, /settings/<name>
    title: str
    icon: str  # a name in static/icons.svg, or "presence" for her screen
    blurb: str  # what it is for, in a line


@dataclass(frozen=True)
class Group:
    """Boxes that belong together on a page, under one heading."""

    section: str
    name: str  # where a link lands, /settings/<section>#<name>
    title: str
    note: str
    fields: tuple[Field, ...]
    folded: bool = False  # fine-tuning, folded away until somebody opens it


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
    the default is", and two ways to say nothing would only be confusing.
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


def _bounds(key: str) -> tuple[Any, Any, bool]:
    """The lowest and highest the setting will take, and whether the lowest is itself refused."""
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
    return low, high, over


def limits(key: str) -> str:
    """What the setting will take, read off the setting itself rather than written out again."""
    low, high, over = _bounds(key)
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
    words: tuple[tuple[str, str], ...] = (),
    unset: str = "",
    company: str = "",
) -> Field:
    kind, derived = _shape(Settings.model_fields[key].annotation)
    if kind == "toggle" and not words:
        words = YES_NO
    return Field(
        key=key,
        label=label,
        # A dropdown already says what it takes, so only a box that is typed in says its range.
        note=" ".join(part for part in (note, "" if choices else limits(key)) if part),
        kind=kind,
        choices=choices or derived,
        suggested=suggested,
        words=words,
        unset=unset,
        company=company,
        keyboard=_keyboard(key, kind),
    )


def _keyboard(key: str, kind: str) -> str:
    """Which keyboard a phone should offer. A phone's number pads have no minus sign, so a
    number that may be below nought (a longitude) keeps the whole keyboard."""
    low, _, _ = _bounds(key)
    if kind not in NUMBER or low is None or low < 0:
        return ""
    return "numeric" if kind == "int" else "decimal"


def zones() -> list[str]:
    """Every time zone worth offering, by the place it is named for."""
    return sorted(zone for zone in available_timezones() if zone.startswith(ZONE_PREFIXES))


YES_NO = (("true", "yes"), ("false", "no"))
HOURS = tuple(str(hour) for hour in range(24))
HOUR_WORDS = tuple((str(hour), f"{hour:02d}:00") for hour in range(24))
EFFORT = (
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("xhigh", "Extra high"),
    ("max", "Most"),
)


# Each company's two models: the one that answers in the chat, and the one that looks things up.
MODEL_KEYS = {
    "openai": ("openai_model", "openai_worker_model"),
    "anthropic": ("anthropic_model", "worker_model"),  # the first, so named for no company
    "gemini": ("gemini_model", "gemini_worker_model"),
}


def _models(company: str, label: str) -> tuple[Field, Field]:
    """A company's two everyday model boxes, offering its models without limiting them to those."""
    chat, worker = MODEL_KEYS[company]
    offered = suggestions(company)
    return (
        field(chat, f"{label} everyday chat model", suggested=offered, company=company),
        field(
            worker,
            f"{label} everyday lookup model",
            "A smaller one is usually plenty." if company == "anthropic" else "",
            suggested=offered,
            company=company,
        ),
    )


# The pages, in the order the list of them reads.
SECTIONS: tuple[Section, ...] = (
    Section("general", "General", "home", "Where home is, its clock and units, and this page."),
    Section("model", "AI model", "mark", "Which company answers, with which model, and its key."),
    Section("spending", "Spending", "coin", "The daily limit, and what one message may use."),
    Section("messages", "Messages", "bell", "What is sent without being asked, and when."),
    Section("lookups", "Lookups", "search", "Filling ideas in from the web."),
    Section(
        "personality",
        "Personality and family",
        "presence",
        "Who she is, and who you are, in your own words.",
    ),
    Section("connections", "Connections", "plug", "Telegram, and Google Calendar."),
    Section(
        "security",
        "Sign-in and security",
        "key",
        "Passwords, how long a sign-in lasts, seeing a key, signing everyone out.",
    ),
    Section("history", "What has changed", "clock", "Every change made here, and who made it."),
)
SECTION_BY_NAME: dict[str, Section] = {one.name: one for one in SECTIONS}

# Every box, on the page and in the group it belongs to. Every name in BEHAVIOUR appears exactly
# once; a test says so.
GROUPS: tuple[Group, ...] = (
    Group(
        "general",
        "home",
        "Where home is",
        "It decides the forecast, how far away things are, and what is on nearby. The town is "
        "enough; no street address.",
        (
            field(
                "home_area",
                "Home town or area",
                "As you would tell someone: a town, and a state or country. When it changes it is "
                "looked up on the map, and the page says what it found.",
            ),
            field(
                "family_tz",
                "Time zone",
                "It decides what “tonight” and “this weekend” mean, and when the messages that "
                "go out on their own are sent.",
            ),
            field(
                "weather_units",
                "Units",
                "For the forecast and for distances.",
                words=(("metric", "°C and kilometres"), ("imperial", "°F and miles")),
            ),
        ),
    ),
    Group(
        "general",
        "position",
        "Exact position and travel times",
        "The position is found from the town when it is saved: type it only to be more exact. "
        "How long a journey takes is guessed from the other two.",
        (
            field("home_lat", "Latitude", "Negative south of the equator.", unset="not found yet"),
            field("home_lon", "Longitude", "Negative west of Greenwich.", unset="not found yet"),
            field(
                "travel_speed_kmh",
                "Average driving speed (km/h)",
                "Across town and highway together.",
            ),
            field(
                "road_factor",
                "Road detour factor",
                "How much longer the road is than a straight line: 1.3 is usual.",
            ),
        ),
        folded=True,
    ),
    Group(
        "general",
        "page",
        "This page",
        "",
        (
            field(
                "web_title",
                "Name of this page",
                "In the bar, on the sign-in page and in the browser's tab. Your family's name "
                "works well.",
            ),
        ),
    ),
    Group(
        "general",
        "log",
        "The server's log",
        "For whoever looks after the server.",
        (
            field(
                "log_level",
                "Log detail",
                "How much the server writes to its log. Debug is for chasing a problem.",
                choices=("DEBUG", "INFO", "WARNING", "ERROR"),
                words=(
                    ("DEBUG", "Debug: everything"),
                    ("INFO", "Info: the usual"),
                    ("WARNING", "Warnings and errors"),
                    ("ERROR", "Errors only"),
                ),
            ),
        ),
        folded=True,
    ),
    Group(
        "model",
        "who",
        "Who answers",
        "The model that reads each message and writes the answer comes from one of three "
        "companies, and you pay the company for what it uses.",
        (
            # Drawn as the three companies to choose between, with the key beside them: a
            # company without a key cannot be chosen, since then nothing would answer.
            field("provider", "Company that answers", words=tuple(COMPANIES.items())),
        ),
    ),
    Group(
        "model",
        "levels",
        "How strong a model answers",
        "How strong a model answers in each situation, whichever company it is: the cheapest by "
        "default, a stronger one where it is worth paying for.",
        (
            field(
                "chat_level",
                "Answering the family",
                "Everyday is the company's own model below; better and best are its stronger "
                "ones, never cheaper than everyday. Prices are US dollars for a million tokens "
                "read and written.",
            ),
            field(
                "digest_level",
                "The weekend digest",
                "Once a week, so a stronger model adds little to the month.",
            ),
            field(
                "lookup_level",
                "Looking things up",
                "Filling in an idea's details and finding what is on: everyday is usually plenty.",
            ),
        ),
    ),
    Group(
        "model",
        "models",
        "Models",
        "What everyday means for each company: its cheapest unless you choose another. Pick one, "
        "or type any model the company offers; the least expensive are listed first.",
        (
            *_models("openai", "OpenAI"),
            *_models("anthropic", "Claude"),
            *_models("gemini", "Gemini"),
        ),
    ),
    Group(
        "model",
        "second",
        "A second company",
        "With a key for another company as well, it can do the lookups, or stand in when the "
        "first cannot answer.",
        (
            field(
                "worker_provider",
                "Company for lookups",
                "Who looks ideas up on the web.",
                words=tuple(COMPANIES.items()),
                unset="the company that answers",
            ),
            field(
                "provider_fallback",
                "Ask another company when the first cannot",
                "Only one with a key, and only before anything has been done, so nothing "
                "happens twice. It answers at the same level.",
            ),
        ),
    ),
    Group(
        "model",
        "voice",
        "Voice notes",
        "Voice notes sent on Telegram are written down by a speech model, then answered as if "
        "they had been typed. Claude cannot hear them, so they need an OpenAI or Gemini key.",
        (
            field("voice_notes", "Listen to voice notes", "Off asks the family to type instead."),
            field(
                "voice_max_minutes",
                "Longest voice note heard (minutes)",
                "A longer one is not heard at all, since every minute is paid for.",
            ),
            field(
                "transcribe_provider",
                "Who hears them",
                "Leave it alone to use the chat company when it can, else another with a key.",
                words=tuple(COMPANIES.items()),
                unset="the chat company if it can",
            ),
            field(
                "openai_transcribe_model",
                "OpenAI hearing model",
                suggested=hearing_suggestions("openai"),
            ),
            field(
                "gemini_transcribe_model",
                "Gemini hearing model",
                "Leave it empty to use Gemini's lookup model.",
                suggested=suggestions("gemini"),
                unset="Gemini's lookup model",
            ),
        ),
    ),
    Group(
        "spending",
        "limit",
        "The daily limit",
        "",
        (
            field(
                "daily_spend_limit",
                "Daily spending limit (US$)",
                "Estimated across every model call. Once it is reached nothing more is asked of "
                "a model until midnight, and whoever writes is told why. 0 means no limit. Set a "
                "limit with the company too.",
            ),
        ),
    ),
    Group(
        "spending",
        "thinking",
        "Thinking",
        "How long the model may think before it answers. More helps with hard questions, and "
        "costs more.",
        (
            field("effort", "Chat thinking", words=EFFORT),
            field(
                "worker_effort",
                "Lookup thinking",
                "Looking a place up needs little: low is usually plenty.",
                words=EFFORT,
            ),
        ),
    ),
    Group(
        "spending",
        "each",
        "What one message may use",
        "Limits for a single message. The defaults suit a family: lower is cheaper, but can cut "
        "an answer short.",
        (
            field(
                "max_output_tokens",
                "Longest answer (tokens)",
                "A token is about three quarters of a word. An answer is rarely near it.",
            ),
            field(
                "agent_max_iterations",
                "Steps per message",
                "How many tools (a search, a save) it may use before it has to answer.",
            ),
            field("worker_max_iterations", "Steps per lookup"),
            field(
                "prompt_idea_limit",
                "Ideas sent with every message",
                "The newest this many; older ones are still found by searching. 0 sends them all.",
            ),
            field(
                "history_limit",
                "Messages of chat remembered",
                "How many earlier messages go with each new one.",
            ),
            field(
                "history_hours",
                "Hours of chat remembered",
                "Older messages are left out. 0 makes every message stand on its own.",
            ),
            field(
                "anthropic_cache_ttl",
                "Claude's prompt cache",
                "Only for Claude: how long it keeps the part of every request that does not "
                "change. An hour costs less, as a family writes in bursts.",
                words=(("5m", "5 minutes"), ("1h", "1 hour")),
            ),
        ),
        folded=True,
    ),
    Group(
        "messages",
        "weekend",
        "Weekend ideas",
        "Once a week it asks itself what the family should do at the weekend, and sends the "
        "answer: one model call a week.",
        (
            field(
                "digest_chat_id",
                "Weekend ideas go to",
                "Choose a chat it has seen, or type a Telegram chat id. A group is offered once "
                "somebody on the family list has written in it. Empty sends none.",
                unset="nowhere",
            ),
            field("digest_day", "Weekend ideas day", words=tuple(DAY_NAMES.items())),
            field(
                "digest_hour",
                "Weekend ideas time",
                "In the family's time zone.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
        ),
    ),
    Group(
        "messages",
        "others",
        "Follow-ups and notes",
        "These are written, not thought up, so they cost nothing.",
        (
            field(
                "follow_up_hour",
                "Time to ask how a plan went",
                "The day after a plan, so the ideas list learns what you liked.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
            field(
                "enrichment_notes",
                "Say in the chat when an idea is filled in",
                "A short note with what was found.",
            ),
        ),
    ),
    Group(
        "messages",
        "retries",
        "When a message cannot be answered",
        "If the model cannot be reached, the message is kept and tried again later.",
        (
            field("retry_interval_minutes", "Minutes between retries"),
            field("retry_max_attempts", "Retries before giving up"),
        ),
        folded=True,
    ),
    Group(
        "lookups",
        "web",
        "Looking ideas up",
        "A separate, smaller turn reads the web to fill in an idea's address, opening hours and "
        "prices, and to find what is on nearby. Each lookup costs a little, within the daily "
        "limit.",
        (
            field(
                "web_tools_enabled",
                "Look ideas up on the web",
                "Without it, no idea is filled in and nothing new is discovered.",
            ),
            field(
                "place_stale_days",
                "Days before details look old",
                "After this, an idea's hours and prices are marked as worth checking again.",
            ),
        ),
    ),
    Group(
        "lookups",
        "pace",
        "How often",
        "",
        (
            field(
                "enrich_interval_minutes",
                "Minutes between lookups",
                "How often it checks for ideas waiting to be looked up.",
            ),
            field("enrich_batch", "Ideas looked up at a time"),
        ),
        folded=True,
    ),
    Group(
        "connections",
        "calendar",
        "Google calendar id",
        "",
        (
            field(
                "google_calendar_id",
                "Google calendar id",
                "Chosen when you connect. For another calendar, paste its id from Google "
                "Calendar: the calendar's Settings and sharing, under Integrate calendar.",
            ),
        ),
    ),
    Group(
        "security",
        "signing-in",
        "Staying signed in",
        "",
        (
            field(
                "web_session_days",
                "Days a sign-in lasts",
                "How long a phone or computer stays signed in before it asks again.",
            ),
        ),
    ),
)

FIELDS: tuple[Field, ...] = tuple(one for group in GROUPS for one in group.fields)
BY_KEY: dict[str, Field] = {one.key: one for one in FIELDS}
SECTION_OF: dict[str, str] = {one.key: group.section for group in GROUPS for one in group.fields}


def groups_in(section: str) -> tuple[Group, ...]:
    """The groups on one page, in the order they are drawn."""
    return tuple(group for group in GROUPS if group.section == section)


def parse(one: Field, given: str) -> Any:
    """One box as the value it stands for. Empty means no override: the default again.

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


def fallback(one: Field, base: Settings) -> Any:
    """What the family gets with no override. The time zone is the one worked out, since an
    empty FAMILYDB_TZ still means the server's own zone, or UTC."""
    return base.tz if one.key == "family_tz" else getattr(base, one.key)


def placeholder(one: Field, value: Any) -> str:
    """What the box says when it is empty: what the family gets without an override."""
    if value is None or value == "":
        return one.unset or "not set"
    return one.word(str(value).lower() if one.kind == "toggle" else str(value))


__all__ = [
    "BEHAVIOUR",
    "BY_KEY",
    "COMPANIES",
    "FIELDS",
    "GROUPS",
    "SECTIONS",
    "SECTION_BY_NAME",
    "Field",
    "Group",
    "Section",
    "fallback",
    "groups_in",
    "parse",
    "placeholder",
    "read_form",
    "shown",
    "zones",
]
