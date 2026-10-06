"""Settings, loaded from the environment and an optional .env file."""

from __future__ import annotations

import json
import logging
import os
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from familydb.errors import ConfigError

Effort = Literal["low", "medium", "high", "xhigh", "max"]
# Strength in the order each company prices them (agent/providers/catalog.py).
Level = Literal["everyday", "better", "best"]
ProviderName = Literal["anthropic", "openai", "gemini"]
CacheTTL = Literal["5m", "1h"]
LookupsWhen = Literal["evening", "asap"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]

# An empty line in .env (`HOME_LAT=`) means "not set", so the default applies; what `cp .env.example
# .env` leaves behind. These are the exceptions where empty is an answer: no worker provider, no
# worker model, no home area.
EMPTY_MEANS_UNSET_EXCEPT = frozenset(
    {
        "worker_provider",
        "worker_model",
        "openai_worker_model",
        "gemini_worker_model",
        "home_area",
    }
)

SECRET_FIELDS = frozenset(
    {
        "anthropic_api_key",
        "gemini_api_key",
        "openai_api_key",
        "telegram_bot_token",
        "web_password",
        "web_password_hash",
        "web_secret_key",
    }
)
log = logging.getLogger(__name__)


def _zone_or_none(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().lstrip(":")
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return candidate


class PersonaRewrite(BaseModel):
    """One persona's character as the family rewrote it, laid over that persona alone."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(max_length=20_000)
    # Her own character as shipped when they wrote it, so the page can tell when hers has changed.
    # Empty when not known (a rewrite an older version saved).
    of: str = Field(default="", max_length=40_000)


def _field_names(cls: type[BaseSettings]) -> dict[str, str]:
    names: dict[str, str] = {}
    for name, field in cls.model_fields.items():
        names[name.lower()] = name
        alias = field.validation_alias
        candidates = alias.choices if isinstance(alias, AliasChoices) else [alias]
        for candidate in candidates:
            if isinstance(candidate, str):
                names[candidate.lower()] = name
    return names


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", validate_by_name=True
    )

    # `worker_provider` empty means lookups and discovery use `provider`. GPT-6 Luna by default: the
    # cheapest capable model of the three.
    provider: ProviderName = "openai"
    worker_provider: ProviderName | Literal[""] = ""
    provider_fallback: bool = True
    # Model strength per situation, whichever company: `everyday` is the company's model named
    # below, `better` and `best` its stronger ones (catalog.py).
    chat_level: Level = "everyday"
    digest_level: Level = "everyday"
    lookup_level: Level = "everyday"
    # A company's better and best models in place of the lineup's; empty uses the lineup's.
    openai_better_model: str = ""
    openai_best_model: str = ""
    anthropic_better_model: str = ""
    anthropic_best_model: str = ""
    gemini_better_model: str = ""
    gemini_best_model: str = ""
    # Judgement calls (judgement.py): a stronger model is asked, rarely, when a change needs
    # weighing; code checks the answer and admins see it. Off until the family turns it on; at most
    # `judgement_budget` US$ a month, within the daily limit.
    judgements: bool = False
    judgement_level: Level = "best"
    # `within_cost` puts in a model that costs no more than the one it replaces
    # (judgement.SAME_COST); anything dearer, and everything under `suggest`, waits for an admin's
    # press.
    judgement_acts: Literal["within_cost", "suggest"] = "within_cost"
    judgement_budget: float = Field(default=1.0, ge=0, le=50)

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_worker_model: str = "gemini-3.1-flash-lite"

    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"
    openai_worker_model: str = "gpt-6-luna"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    # A persona's folder in familydb/personas, or "none". Not empty for none: empty means "the
    # default" everywhere else and would bring her back. `personas.active` lays the settings below
    # over her own.
    persona: str = "default"
    # What the family call her; empty for her own name. Kept but unused with no persona.
    persona_name: str = Field(default="", max_length=40)
    # Her character as rewritten, by persona key, so each rewrite is laid over the persona it was
    # written for. Unparsed from the environment, because a plain string there is a rewrite, not
    # JSON.
    persona_text: Annotated[dict[str, PersonaRewrite], NoDecode] = Field(default_factory=dict)
    # The family's notes on how she talks, kept apart from her description so they last when hers is
    # improved. Kept but unused with no persona.
    persona_notes: str = Field(default="", max_length=1_000)
    about_family: str = Field(default="", max_length=4_000)
    # The family's wording for what she says unasked, by event (voice.EVENTS); a missing line uses
    # the persona's, then the plain one. A string is one wording, as older installs stored every
    # line.
    voice_lines: dict[str, str | list[str]] = Field(default_factory=dict)
    # Applies to whoever answers. Accepts ANTHROPIC_EFFORT, the name older .env files use.
    effort: Effort = Field(
        default="medium", validation_alias=AliasChoices("EFFORT", "ANTHROPIC_EFFORT")
    )
    # Caps the answer on any vendor. Accepts ANTHROPIC_MAX_TOKENS, the name older .env files use.
    max_output_tokens: int = Field(
        default=16000,
        ge=256,
        le=64_000,
        validation_alias=AliasChoices("MAX_OUTPUT_TOKENS", "ANTHROPIC_MAX_TOKENS"),
    )
    # Dollars a day across every model call, estimated from prices.py and checked before each call.
    # 0 turns the limit off.
    daily_spend_limit: float = Field(default=2.0, ge=0, le=500)
    kid_daily_spend: float = Field(default=0.25, ge=0, le=50)
    wish_daily_count: int = Field(default=5, ge=1, le=50)
    occasion_list_size: int = Field(default=25, ge=1, le=100)
    parent_asks_per_week: int = Field(default=2, ge=0, le=14)
    wording_daily_after: int = Field(default=3, ge=1, le=20)
    # Messages each kid may have answered by a model in a day (roles.py says who is limited).
    # Commands and buttons ask no model, so do not count. 0 is no limit.
    kid_daily_messages: int = Field(default=0, ge=0, le=500)
    # Tell every admin with a Telegram id what only an admin can fix (alerts.py). No model call.
    admin_alerts: bool = True
    # Once a day, ask each company which models the key can use and read two public price lists
    # (model_watch.py, usage_watch.py). No model call.
    model_watch: bool = True
    anthropic_fallbacks: bool = True
    # An hour, because a family writes in bursts: a five-minute cache would be cold almost every
    # time.
    anthropic_cache_ttl: CacheTTL = "1h"
    agent_max_iterations: int = Field(default=8, ge=1, le=20)
    history_limit: int = Field(default=20, ge=0, le=200)
    # The ideas list rides in the cached prompt on every message, so it cannot grow without end:
    # past this many the oldest are left out and the model is told to search for them.
    prompt_idea_limit: int = Field(default=150, ge=0, le=5000)
    history_hours: float = Field(default=6.0, ge=0, le=720)

    familydb_path: Path = Path("data/familydb.sqlite3")
    family_tz: str | None = Field(default=None, validation_alias="FAMILYDB_TZ")
    _tz: str = PrivateAttr(default="UTC")
    home_lat: Latitude | None = None
    home_lon: Longitude | None = None
    home_area: str = ""
    weather_units: Literal["metric", "imperial"] = "metric"

    web_tools_enabled: bool = False
    telegram_bot_token: str | None = None
    # Seconds to wait before answering on Telegram so several messages sent in a row get one turn
    # and one reply (pipeline.receive). 0 answers each at once.
    gather_seconds: int = Field(default=4, ge=0, le=30)
    telegram_require_mention: bool = False
    # What is only for one person goes to them (routing.py): their own Telegram chat with her, else
    # their conversation on the page, rather than the group, the page or the chat it began in.
    private_when_personal: bool = True
    # The family's chat, where a reminder for everyone goes when it was not asked for in a group
    # (routing.family_chat): a Telegram chat id, or "web" for the page. Unset: the weekend ideas'.
    family_chat_id: str | None = None
    # Voice notes are heard by a speech model, then answered as if typed (gateway.listen). Claude
    # hears nothing, so a family on Claude alone needs an OpenAI or Gemini key.
    voice_notes: bool = True
    voice_max_minutes: int = Field(default=5, ge=1, le=30)
    transcribe_provider: Literal["", "openai", "gemini"] = ""
    # Photos are looked at by the lookup model, which writes down what they show (gateway.look). The
    # picture is not kept.
    photos: bool = True
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    gemini_transcribe_model: str = ""
    retry_interval_minutes: int = Field(default=5, ge=1, le=1440)
    retry_max_attempts: int = Field(default=3, ge=0, le=20)

    enrich_interval_minutes: int = Field(default=2, ge=1, le=1440)
    # When ideas are looked up on the web: together each evening at lookup_hour, or each as soon as
    # it is added. One asked for now (look_up_now) is looked up within enrich_interval_minutes
    # either way.
    lookups_when: LookupsWhen = "evening"
    lookup_hour: int = Field(default=21, ge=0, le=23)
    enrich_batch: int = Field(default=3, ge=1, le=20)
    place_stale_days: int = Field(default=30, ge=1, le=3650)
    worker_max_iterations: int = Field(default=12, ge=1, le=30)
    # Lookups and discovery are extraction, not judgement, so they run with less thinking.
    # `worker_model` is Anthropic's lookup model, as `openai_worker_model` and `gemini_worker_model`
    # are the others'; empty uses `anthropic_model`.
    worker_model: str = "claude-haiku-4-5"
    worker_effort: Effort = "low"
    travel_speed_kmh: float = Field(default=50.0, gt=0, le=200)
    road_factor: float = Field(default=1.3, ge=1, le=3)
    digest_chat_id: str | None = None
    digest_day: Weekday = "thu"
    digest_hour: int = Field(default=18, ge=0, le=23)
    follow_up_hour: int = Field(default=10, ge=0, le=23)
    task_nudges: bool = True
    follow_ups: bool = True
    plan_checks: bool = True
    plan_check_hour: int = Field(default=19, ge=0, le=23)
    # The morning message (jobs/morning.py): each part on by default, the family's decision.
    morning_hour: int = Field(default=7, ge=0, le=23)
    morning_agenda: bool = True
    chase_missed: bool = True
    deadline_heads_up: bool = True
    forgotten_roundup: bool = True
    roundup_day: Weekday = "sun"
    google_calendar_id: str | None = None
    google_key_path: Path = Path("data/google_key.json")
    enrichment_notes: bool = True

    web_enabled: bool = False
    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8080, ge=1, le=65535)
    web_password: str | None = None
    # The family password as chosen on the page or by `familydb password`, hashed (web/auth.py).
    # Once there is one, WEB_PASSWORD (the installer's) opens nothing.
    web_password_hash: str | None = None
    web_secret_key: str | None = None
    web_session_days: int = Field(default=30, ge=1, le=3650)
    web_allow_no_password: bool = False
    web_trust_proxy: bool = False
    web_title: str = "FamilyDB"
    # A mic beside every box that takes words, through the browser's own speech recognition
    # (static/dictate.js). The sound goes from the browser to its maker, never through FamilyDB:
    # what leaves the house is the family's decision (docs/DESIGN.md section 16).
    web_dictation: bool = True

    console_member: str | None = None
    log_level: str = "INFO"
    # Sent with each OpenStreetMap geocoder lookup as its usage policy asks (an email address or a
    # web page). Empty, none is sent: it leaves the house with every lookup, so it is the operator's
    # to give.
    geocoder_contact: str = ""

    @model_validator(mode="before")
    @classmethod
    def _blank_means_unset(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        names = _field_names(cls)
        return {
            key: value
            for key, value in data.items()
            if not (
                isinstance(value, str)
                and not value.strip()
                and names.get(str(key).lower(), str(key).lower()) not in EMPTY_MEANS_UNSET_EXCEPT
            )
        }

    @field_validator("persona")
    @classmethod
    def _known_persona(cls, value: str) -> str:
        from familydb import personas

        key = personas.key_for(value)
        choices = (*personas.available(), personas.NONE)
        if key not in choices:
            raise ValueError(f"no persona called {value!r}; the choices are {', '.join(choices)}")
        return key

    @field_validator("persona_name", mode="before")
    @classmethod
    def _one_plain_name(cls, value: Any) -> Any:
        """A name on one line, with no control characters and no braces, since {name} inside it
        would be filled in again.
        """
        if not isinstance(value, str):
            return value
        name = value.strip()
        if any(unicodedata.category(character) in ("Cc", "Zl", "Zp") for character in name):
            raise ValueError("her name goes on one line, with no control characters in it")
        if "{" in name or "}" in name:
            raise ValueError("her name cannot have a brace in it")
        return name

    @field_validator("persona_text", mode="before")
    @classmethod
    def _rewrites_by_persona(cls, value: Any) -> Any:
        """Each rewrite under the persona it belongs to.

        A string that is not a JSON object is the default persona's rewrite, as older installs
        stored it: a setting that fails to load takes every stored setting with it. A key with no
        folder is kept and never used.
        """
        from familydb import personas

        if value is None:
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                return {personas.DEFAULT: {"text": value}} if value.strip() else {}
            value = parsed
        if not isinstance(value, Mapping):
            return value
        rewrites: dict[str, Any] = {}
        for key, entry in value.items():
            if isinstance(entry, PersonaRewrite):
                entry = entry.model_dump()
            elif isinstance(entry, str) or entry is None:
                entry = {"text": entry}
            if isinstance(entry, Mapping) and not str(entry.get("text") or "").strip():
                continue
            rewrites[personas.key_for(str(key))] = entry
        return rewrites

    @field_validator("family_tz")
    @classmethod
    def _valid_zone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        zone = _zone_or_none(value)
        if zone is None:
            raise ValueError(
                f"unknown timezone {value!r}; use an IANA name such as America/Vancouver"
            )
        return zone

    @field_validator("log_level")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _resolve_timezone(self) -> Settings:
        if self.family_tz:
            self._tz = self.family_tz
            return self
        inherited = os.environ.get("TZ")
        zone = _zone_or_none(inherited)
        if zone:
            self._tz = zone
        else:
            self._tz = "UTC"
            if inherited:
                log.warning("ignoring TZ=%r (not an IANA zone); set FAMILYDB_TZ", inherited)
        return self

    @property
    def tz(self) -> str:
        return self._tz

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self._tz)

    @property
    def southern_hemisphere(self) -> bool:
        return self.home_lat is not None and self.home_lat < 0

    def masked(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, value in self.model_dump().items():
            if name in SECRET_FIELDS and value:
                value = "****"
            out[name] = value
        out["tz"] = self.tz
        return out


def describe(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors():
        name = ".".join(str(part) for part in error["loc"]) or "setting"
        lines.append(f"  {name}: {error['msg']}")
    return "a setting will not do:\n" + "\n".join(lines)


def load_settings(env_file: str | Path | None = ".env", **overrides: Any) -> Settings:
    """Build settings from the environment, an optional .env file and overrides; a bad value arrives
    as a ConfigError naming the setting.
    """
    try:
        return Settings(_env_file=env_file, **overrides)
    except ValidationError as exc:
        raise ConfigError(describe(exc)) from exc


def apply_overrides(base: Settings, values: dict[str, Any]) -> Settings:
    """`base` with these values on top, validated; raises pydantic's ValidationError, which the page
    puts against the right box.
    """
    if not values:
        return base
    merged = {**base.model_dump(), **values}
    merged.pop("tz", None)
    return Settings(_env_file=None, **merged)
