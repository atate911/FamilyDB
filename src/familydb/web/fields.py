"""What the settings pages show (`SECTIONS`, each with `GROUPS` of boxes) and how a filled-in
form becomes settings again. A box's shape comes from `Settings` itself (a Literal is a dropdown,
a bool yes/no, a number a number box), so a changed Literal can never leave the page offering
what the setting will not take. Pure functions over strings; the routes store."""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from functools import cache
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
COMPANIES = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google"}
# Places, not legacy aliases and offsets, and UTC, which many a server keeps.
ZONE_PREFIXES = ("Africa/", "America/", "Antarctica/", "Asia/", "Atlantic/", "Australia/")
ZONE_PREFIXES += ("Europe/", "Indian/", "Pacific/")
ZONE_ALSO = frozenset({"UTC"})


@dataclass(frozen=True)
class Field:
    """One box on a settings page."""

    key: str
    label: str
    note: str
    kind: str  # choice, toggle, int, float or text
    choices: tuple[str, ...] = ()
    # Offered as the box is typed in, without limiting it.
    suggested: tuple[str, ...] = ()
    # How a value is shown where the stored one reads badly: "thu", "true".
    words: tuple[tuple[str, str], ...] = ()
    # What no value means, where "not set" would not say.
    unset: str = ""
    # For a model box, whose model it is.
    company: str = ""
    # The keyboard a phone offers: numeric, decimal or all of it.
    keyboard: str = ""
    # For a list box, the words for the last choice, which opens a box to type any other.
    another: str = ""

    def word(self, value: str) -> str:
        return dict(self.words).get(value, value)


@dataclass(frozen=True)
class Section:
    """One page of the settings."""

    name: str  # its address, /settings/<name>
    title: str
    icon: str  # in static/icons.svg, or "presence"
    blurb: str


@dataclass(frozen=True)
class Group:
    section: str
    name: str  # where a link lands, /settings/<section>#<name>
    title: str
    note: str
    fields: tuple[Field, ...]
    folded: bool = False  # fine-tuning


def _bare(annotation: Any) -> Any:
    """An annotation with any Annotated metadata taken off."""
    return typing.get_args(annotation)[0] if hasattr(annotation, "__metadata__") else annotation


def _members(annotation: Any) -> list[Any]:
    """The parts of a union, flattened, with None dropped. A plain type is its own part."""
    annotation = _bare(annotation)
    if typing.get_origin(annotation) in (types.UnionType, typing.Union):
        return [_bare(part) for part in typing.get_args(annotation) if part is not type(None)]
    return [annotation]


def _shape(annotation: Any) -> tuple[str, tuple[str, ...]]:
    """How to draw a box for this annotation. An empty string is never a choice: an empty box
    already means the default."""
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
    """Every constraint on an annotation, including inside an Optional. A `Field(ge=...)` arrives
    wrapped in a FieldInfo, which is unwrapped so both spellings read the same."""
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
    over = False  # the bottom of the range is itself refused
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
    """What the setting will take, read off the setting itself."""
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
    another: str = "",
) -> Field:
    kind, derived = _shape(Settings.model_fields[key].annotation)
    if kind == "toggle" and not words:
        words = YES_NO
    return Field(
        key=key,
        label=label,
        # A dropdown already says what it takes.
        note=" ".join(part for part in (note, "" if choices else limits(key)) if part),
        kind=kind,
        choices=choices or derived,
        suggested=suggested,
        words=words,
        unset=unset,
        company=company,
        keyboard=_keyboard(key, kind),
        another=another or ("Another model" if suggested else ""),
    )


def _keyboard(key: str, kind: str) -> str:
    """Which keyboard a phone offers. Number pads have no minus sign, so a number that may be
    negative (a longitude) keeps the whole keyboard."""
    low, _, _ = _bounds(key)
    if kind not in NUMBER or low is None or low < 0:
        return ""
    return "numeric" if kind == "int" else "decimal"


@cache
def zones() -> tuple[str, ...]:
    """Every time zone worth offering, and UTC. Cached: reading it walks the zone files."""
    return tuple(
        sorted(
            zone
            for zone in available_timezones()
            if zone.startswith(ZONE_PREFIXES) or zone in ZONE_ALSO
        )
    )


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


# Boxes whose list is fixed rather than found by the daily check of models.
FIXED_OFFERS = frozenset({"openai_transcribe_model"})
# Each company's chat model and lookup model.
MODEL_KEYS = {
    "openai": ("openai_model", "openai_worker_model"),
    "anthropic": ("anthropic_model", "worker_model"),  # the first, so unprefixed
    "gemini": ("gemini_model", "gemini_worker_model"),
}


def _models(company: str, label: str) -> tuple[Field, Field]:
    """A company's two everyday model boxes, offering its models without limiting to them."""
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


SECTIONS: tuple[Section, ...] = (
    Section("general", "General", "home", "Where home is, its clock and units, and this page."),
    Section("model", "AI model", "mark", "Which company answers, with which model, and its key."),
    Section("spending", "Spending", "coin", "The daily limit, and what one message may use."),
    Section("messages", "Messages", "bell", "What is sent without being asked, and when."),
    Section("lookups", "Lookups", "search", "Filling ideas in, and taking off what is over."),
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

# Every name in BEHAVIOUR appears exactly once; a test says so.
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
                "go out on their own are sent. Choose the nearest city in the same zone.",
                # Drawn under its region, with its offset now (views.py).
                choices=zones(),
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
            field(
                "web_dictation",
                "A mic to speak instead of typing",
                "Beside each box that takes words. The browser writes down what is said: Safari "
                "sends the sound to Apple, Chrome to Google, as a phone keyboard's mic does. It "
                "never passes through FamilyDB and costs nothing. Firefox has no mic.",
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
            # A company without a key cannot be chosen: nothing would answer.
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
        "least expensive first, or choose Another model to type any the company offers.",
        (
            *_models("openai", "OpenAI"),
            *_models("anthropic", "Claude"),
            *_models("gemini", "Gemini"),
        ),
    ),
    Group(
        "model",
        "watch",
        "Keeping up with the companies",
        "Once a day it asks each company you have a key for which models the key can use, and "
        "reads two public price lists, LiteLLM's and OpenRouter's, taking a price when they "
        "agree. New models then appear here and new prices are counted, and admins are told on "
        "Telegram when a model you use is going or its price moves. No model call, and nothing "
        "about the family is sent.",
        (
            field(
                "model_watch",
                "Check models and prices daily",
                "Off, the prices built into this version are used, and nobody is told.",
            ),
        ),
    ),
    Group(
        "model",
        "judgement",
        "Asking a stronger model to weigh a change",
        "Some changes need judgement rather than a rule: which model should take the place of one "
        "that is going, what a refusal nobody can read means, which new models belong at which "
        "level, and what a price the lists disagree on really is. With this on, the questions "
        "that come up are asked together once a day, with the evening's lookups, in one call; "
        "only a refusal is asked at once. The answer is checked, told to admins, and never "
        "changes a setting by itself. It is sent model names, prices and error messages, never "
        "the family's messages.",
        (
            field(
                "judgements",
                "Ask a stronger model when a change needs judgement",
                "A few cents each time, and nothing on a day with no question.",
            ),
            field(
                "judgement_level",
                "How strong a model weighs it",
                "Best by default: rare questions, where a better answer is worth a cent more.",
            ),
            field(
                "judgement_acts",
                "What it may do by itself",
                "A better model at the same cost or less can be put in by itself, and admins are "
                "told, with a way to put it back; anything dearer waits for an admin.",
                words=(
                    ("within_cost", "Put in a model at the same cost or less"),
                    ("suggest", "Only suggest"),
                ),
            ),
            field(
                "judgement_budget",
                "Most to spend on it in a month (US$)",
                "Counted within the daily limit as well. 0 asks nothing.",
            ),
        ),
    ),
    Group(
        "model",
        "stronger",
        "Better and best models",
        "The models a company answers with at the better and best levels. Empty uses the ones "
        "this version knows (shown as the default); a judgement may suggest newer ones.",
        tuple(
            field(
                f"{company}_{level}_model",
                f"{label} {level} model",
                suggested=suggestions(company),
                unset="this version's",
                company=company,
            )
            for company, label in (
                ("openai", "OpenAI"),
                ("anthropic", "Claude"),
                ("gemini", "Gemini"),
            )
            for level in ("better", "best")
        ),
        folded=True,
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
                company="openai",
            ),
            field(
                "gemini_transcribe_model",
                "Gemini hearing model",
                "Leave it empty to use Gemini's lookup model.",
                suggested=suggestions("gemini"),
                unset="Gemini's lookup model",
                company="gemini",
            ),
        ),
    ),
    Group(
        "model",
        "photos",
        "Photos",
        "A photo sent on Telegram (a poster, a menu, a ticket) is read by the model that looks "
        "things up, which writes down what it shows; that is answered as if it had been typed. "
        "The photo goes to that company, costs about a tenth of a cent, and is not kept.",
        (
            field(
                "photos",
                "Look at photos",
                "Off asks for it in words. In a group, a photo is looked at only when it is sent "
                "to the bot, by a mention in its caption or a reply.",
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
            field(
                "kid_daily_messages",
                "Messages a kid may send a day",
                "For each kid on the family list, counting only messages a model answered: "
                "/today and the buttons under a reminder cost nothing and are not counted. Past "
                "it, she says so and answers again tomorrow. 0 means no limit.",
            ),
            field(
                "kid_daily_spend",
                "Each kid's daily share (US$)",
                "What each kid's own messages may spend in a day, within the limit above. When "
                "it is used up she is told, kindly, to come back tomorrow; her wish list still "
                "works. 0 means no share of her own.",
            ),
        ),
    ),
    Group(
        "spending",
        "wishes",
        "The kids' wish lists",
        "How much the kids may ask for, and how the bot guides how they ask.",
        (
            field(
                "wish_daily_count",
                "Everyday wishes a day",
                "How many things a kid may add to her everyday list in a day. The next is kindly "
                "turned away, and shows on the Kids card. Christmas and birthday lists have no "
                "daily count.",
            ),
            field(
                "occasion_list_size",
                "Longest Christmas or birthday list",
                "How many wishes each of her Christmas and birthday lists may hold at once.",
            ),
            field(
                "parent_asks_per_week",
                "Ask a parent, times a week",
                "How often a kid may send you something the bot said no to, when it offers. 0 "
                "means never.",
            ),
            field(
                "wording_daily_after",
                'Nudge "we should" every day after',
                'Once a kid has said "we should" for a want of her own this many times in a '
                'week, the bot reflects "I want" back to her once a day; less often, every '
                "few days.",
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
                "Choose a chat it has seen, or another Telegram chat by its id. A group is "
                "offered once somebody on the family list has written in it. Default sends none.",
                unset="nowhere",
                another="Another Telegram chat",
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
                "follow_ups",
                "Ask how a plan went",
                "The day after, with buttons to answer in one tap, so the ideas list learns what "
                "you liked. No means nobody is asked; how it went can still be told any time.",
            ),
            field(
                "follow_up_hour",
                "Time to ask how a plan went",
                "The day after a plan, in the family's time zone.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
            field(
                "plan_checks",
                "Check tomorrow's plans the evening before",
                "Rain for an outdoor plan, or the place listed as closed then: said only when "
                "something is off, with another idea for the same time when one fits.",
            ),
            field(
                "plan_check_hour",
                "Time to check tomorrow's plans",
                "In the family's time zone.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
            field(
                "task_nudges",
                "Bring up a task kept for “some Saturday morning”",
                "When such a morning comes round and the calendar is free for the hour ahead: "
                "each task once a week at most, and one a day in each chat.",
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
        "morning",
        "Each morning",
        "One message a morning in each chat that has something for it, and none on an empty day. "
        "Written, not thought up, so it costs nothing.",
        (
            field(
                "morning_hour",
                "Time of the morning message",
                "In the family's time zone. After a restart it still goes, until noon.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
            field(
                "morning_agenda",
                "The day ahead",
                "Today's plans, reminders and deadlines, and a dated idea that ends this week when "
                "a free day could fit it.",
            ),
            field(
                "chase_missed",
                "A reminder nobody acted on, once more",
                "The morning after a reminder went and was neither done nor snoozed, once, with a "
                "button to tick it off.",
            ),
            field(
                "deadline_heads_up",
                "What is due tomorrow",
                "The morning before a deadline, so a deadline is not missed for want of a "
                "reminder.",
            ),
            field(
                "forgotten_roundup",
                "What has waited a week or more",
                "Once a week: to-dos a week old or more with no reminder or time to bring them up, "
                "five at most.",
            ),
            field("roundup_day", "Day of the week for that", words=tuple(DAY_NAMES.items())),
        ),
    ),
    Group(
        "messages",
        "push",
        "On phones and tablets",
        "For anybody who uses only the page: each turns it on for their own device, under Your "
        "password.",
        (
            field(
                "web_push",
                "Say when she has written",
                "A notice on the device that she has a message, when she writes of her own accord "
                "(a reminder, the morning message), never the words. Apple's or Google's push "
                "service carries it and sees only that one went.",
            ),
        ),
    ),
    Group(
        "messages",
        "admins",
        "When something needs fixing",
        "Written, not thought up, so they cost nothing. The status page lists the same.",
        (
            field(
                "admin_alerts",
                "Tell admins on Telegram",
                "When a company says its account is out of credit or refuses its key, the day's "
                "spending limit is used up, or Google stops letting it at the calendar: each admin "
                "with a Telegram id is told, and again at most twice a day while it lasts.",
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
        "when",
        "When",
        "Filling an idea in rarely changes what you do next, so by default it waits for the "
        "evening and every idea waiting is looked up together, with one note in each chat for "
        "what was found. Asked for now, by asking her, by the button on the status page or an "
        "idea's page, or by /lookup on Telegram, one is looked up within a few minutes.",
        (
            field(
                "lookups_when",
                "Look ideas up",
                words=(("evening", "together, each evening"), ("asap", "as soon as each is added")),
            ),
            field(
                "lookup_hour",
                "Time for the evening's lookups",
                "In the family's time zone.",
                choices=HOURS,
                words=HOUR_WORDS,
            ),
        ),
    ),
    Group(
        "lookups",
        "tidy",
        "What is over",
        "",
        (
            field(
                "tidy_ideas",
                "Take an idea off a week after its last day",
                "An event or a show whose dates have passed leaves the list overnight, so it stops "
                "coming up and is no longer sent with every message. Its page can bring it back.",
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
                "Minutes between checks",
                "How often it checks for ideas due to be looked up: how soon one asked for now is.",
            ),
            field(
                "enrich_batch",
                "Ideas looked up at a time",
                "When each is looked up as it is added. The evening's lookups take every idea "
                "waiting.",
            ),
        ),
        folded=True,
    ),
    Group(
        "connections",
        "telegram-answering",
        "Answering on Telegram",
        "",
        (
            field(
                "gather_seconds",
                "Seconds to wait for more before answering",
                "Several messages sent one after another are answered together, in one reply "
                "and one model call, when each comes within this long of the last. Every "
                "answer waits this long first. 0 answers each at once.",
            ),
        ),
    ),
    Group(
        "connections",
        "telegram-groups",
        "In a Telegram group",
        "",
        (
            field(
                "telegram_require_mention",
                "Answer only when mentioned",
                "Yes: only a message that @mentions the bot or replies to it. Suits a busy group "
                "the family uses for other things too. No suits a group kept for planning, where "
                "everything said is for her.",
            ),
            field(
                "private_when_personal",
                "Send what's for one person to them",
                "A reminder for somebody's own task, a note on an idea they added, how their "
                "plan went: to their own chat with the bot on Telegram, once they have written "
                "to it there, or else to their conversation on this page, rather than to the "
                "group, this page or whoever's chat it was asked for in. What is for everyone "
                'stays in the group. Either way, a plain "saved" in the group is a 👌 on the '
                "message, which buzzes nobody.",
            ),
            field(
                "family_chat_id",
                "The family's chat",
                "Where a reminder for everyone goes when it was asked for on this page or in "
                "somebody's own chat (one asked for in a group stays there). Choose a chat it "
                "has seen, or another Telegram chat by its id. Default: where the weekend ideas "
                "go, else where it was asked for.",
                unset="where the weekend ideas go",
                another="Another Telegram chat",
            ),
        ),
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
                "Set when you connect. For another calendar, share it with the service account "
                "first, then paste its id from Google Calendar: the calendar's Settings and "
                "sharing, under Integrate calendar.",
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
    return tuple(group for group in GROUPS if group.section == section)


def parse(one: Field, given: str) -> Any:
    """One box as its value; empty means no override. Raises ValueError with a sentence the
    family can act on."""
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


# The last choice in a list box: "the one typed under it".
ANOTHER = "another"


def given(one: Field, form: Any) -> str:
    chosen = form[one.key]
    if one.another and chosen == ANOTHER:
        return form.get(f"{one.key}_{ANOTHER}", "")
    return chosen


def read_form(form: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Every box the form carried, as values and complaints. Absent boxes are left alone."""
    values: dict[str, Any] = {}
    problems: dict[str, str] = {}
    for one in FIELDS:
        if one.key not in form:
            continue
        try:
            values[one.key] = parse(one, given(one, form))
        except ValueError as exc:
            problems[one.key] = str(exc)
    return values, problems


def shown(one: Field, override: Any) -> str:
    if override is None:
        return ""
    return str(override).lower() if one.kind == "toggle" else str(override)


def fallback(one: Field, base: Settings) -> Any:
    """What the family gets with no override. An empty FAMILYDB_TZ still means the server's zone."""
    return base.tz if one.key == "family_tz" else getattr(base, one.key)


def placeholder(one: Field, value: Any) -> str:
    if value is None or value == "":
        return one.unset or "not set"
    return one.word(str(value).lower() if one.kind == "toggle" else str(value))


__all__ = [
    "ANOTHER",
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
    "given",
    "groups_in",
    "parse",
    "placeholder",
    "read_form",
    "shown",
    "zones",
]
