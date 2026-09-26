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
# How strong a model answers, in the order each company prices them (agent/providers/catalog.py).
Level = Literal["everyday", "better", "best"]
ProviderName = Literal["anthropic", "openai", "gemini"]
CacheTTL = Literal["5m", "1h"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]

# An empty line in .env (`HOME_LAT=`) says "I have not set this", not "the empty string": it is
# what `cp .env.example .env` leaves behind, and what the installer writes when a lookup
# fails. Every such value is dropped before validation so the default applies. These few are the
# exceptions, where empty is an answer in itself: no separate worker provider, no separate worker
# model (use the chat one), no home area.
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
    """An IANA zone name if `value` is one (a leading ':' is tolerated), else None."""
    if not value:
        return None
    candidate = value.strip().lstrip(":")
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return candidate


class PersonaRewrite(BaseModel):
    """One persona's character as the family rewrote it on the Personality page.

    It belongs to the persona it rewrote and is laid over her alone: a rewrite of one is never
    somebody else's character.
    """

    model_config = ConfigDict(frozen=True)

    # Her character as the family rewrote it, with {name} where her name goes.
    text: str = Field(max_length=20_000)
    # Her own character as it shipped when they wrote it, so the page can tell when hers has
    # changed since. Empty when that is not known, as for a rewrite saved before it was recorded.
    of: str = Field(default="", max_length=40_000)


def _field_names(cls: type[BaseSettings]) -> dict[str, str]:
    """Every name a field answers to, lowercased, mapped to the field name itself."""
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
    """Runtime configuration. Field names double as environment variable names, any case."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", validate_by_name=True
    )

    # Who answers. `worker_provider` empty means the lookup and discovery turns use `provider`.
    # GPT-6 Luna for both by default: the cheapest capable model any of the three offers.
    provider: ProviderName = "openai"
    worker_provider: ProviderName | Literal[""] = ""
    provider_fallback: bool = True
    # How strong a model answers each situation, whichever company it is. `everyday` is the
    # company's model named below, its cheapest unless the family chose another; `better` and
    # `best` are its stronger ones, from agent/providers/catalog.py.
    chat_level: Level = "everyday"  # answering the family, and answering again after a failure
    digest_level: Level = "everyday"  # the weekend digest: once a week, so a stronger one is cheap
    lookup_level: Level = "everyday"  # looking ideas up, and searching for what is on

    # Each company's everyday models: its cheapest, for chat and for the lookups.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_worker_model: str = "gemini-3.1-flash-lite"

    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"
    openai_worker_model: str = "gpt-6-luna"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    # Who the assistant is to the family: a persona's folder in familydb/personas, or "none". Not
    # empty for none: an empty setting means "the default" everywhere else, and would bring her
    # back. `personas.active` reads it, and lays `persona_name`, `persona_text`, `persona_notes`
    # and `voice_lines` over her own.
    persona: str = "default"
    # What the family call her, from the Personality page; empty for her own name. It is theirs
    # whoever she is, and with no persona it is kept but not used: the bot is FamilyDB then.
    persona_name: str = Field(default="", max_length=40)
    # Her character as the family rewrote it on the Personality page, by persona key, so each
    # rewrite is laid over the persona it was written for; a persona with none uses her own.
    # Unparsed from the environment, because a plain string there is a rewrite, not JSON.
    persona_text: Annotated[dict[str, PersonaRewrite], NoDecode] = Field(default_factory=dict)
    # The family's own notes on how she talks, from the Personality page, kept after her
    # description: not a copy of hers, so they last when hers is improved or rewritten. Theirs
    # whoever she is, and with no persona kept but not used.
    persona_notes: str = Field(default="", max_length=1_000)
    # Who the family are, in their own words, for every chat: ages, tastes, what to avoid.
    about_family: str = Field(default="", max_length=4_000)
    # The family's own wording for what she says unasked, by event (voice.EVENTS); a line left
    # out uses the persona's, and then the plain one. A string is one wording, line breaks and
    # all, as every line was stored before a list could hold several.
    voice_lines: dict[str, str | list[str]] = Field(default_factory=dict)
    # Applies to whoever answers, so it is not named for one of them. ANTHROPIC_EFFORT still works.
    effort: Effort = Field(
        default="medium", validation_alias=AliasChoices("EFFORT", "ANTHROPIC_EFFORT")
    )
    # Named for no vendor, because it caps the answer on either. The old ANTHROPIC_MAX_TOKENS
    # still works for anyone who already has it in a .env.
    max_output_tokens: int = Field(
        default=16000,
        ge=256,
        le=64_000,
        validation_alias=AliasChoices("MAX_OUTPUT_TOKENS", "ANTHROPIC_MAX_TOKENS"),
    )
    # Dollars a day across every model call, estimated from agent/providers/prices.py and checked
    # before each call. Days are the family's. 0 turns the limit off.
    daily_spend_limit: float = Field(default=2.0, ge=0, le=500)
    anthropic_fallbacks: bool = True
    # An hour, because a family writes in bursts with long gaps: a five-minute cache would be
    # cold almost every time and the whole prefix would be paid for again.
    anthropic_cache_ttl: CacheTTL = "1h"
    agent_max_iterations: int = Field(default=8, ge=1, le=20)
    history_limit: int = Field(default=20, ge=0, le=200)
    # The ideas list rides in the cached prompt on every message, so it cannot grow without end.
    # Past this many, the oldest are left out and the model is told to search for them.
    prompt_idea_limit: int = Field(default=150, ge=0, le=5000)
    history_hours: float = Field(default=6.0, ge=0, le=720)

    # Storage and home
    familydb_path: Path = Path("data/familydb.sqlite3")
    # FAMILYDB_TZ, an IANA name. When unset, the OS TZ variable is used if it names a zone.
    family_tz: str | None = Field(default=None, validation_alias="FAMILYDB_TZ")
    _tz: str = PrivateAttr(default="UTC")
    home_lat: Latitude | None = None
    home_lon: Longitude | None = None
    home_area: str = ""
    weather_units: Literal["metric", "imperial"] = "metric"

    # Optional services
    web_tools_enabled: bool = False
    telegram_bot_token: str | None = None
    # In groups, only answer messages that mention the bot or reply to it.
    telegram_require_mention: bool = False
    # Voice notes sent on Telegram are heard by a speech model, then answered as if typed
    # (agent/gateway.listen). Claude hears nothing, so a family on Claude alone needs an OpenAI
    # or Gemini key for them.
    voice_notes: bool = True
    # A longer one is not heard at all: every minute of it is paid for.
    voice_max_minutes: int = Field(default=5, ge=1, le=30)
    # Who hears them. Empty: the chat company when it can, else another that can and has a key.
    transcribe_provider: Literal["", "openai", "gemini"] = ""
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    # Empty hears with Gemini's lookup model.
    gemini_transcribe_model: str = ""
    # Failed messages are retried this often, this many times.
    retry_interval_minutes: int = Field(default=5, ge=1, le=1440)
    retry_max_attempts: int = Field(default=3, ge=0, le=20)

    # Enrichment, suggestions and scheduled prompts
    enrich_interval_minutes: int = Field(default=2, ge=1, le=1440)
    enrich_batch: int = Field(default=3, ge=1, le=20)
    place_stale_days: int = Field(default=30, ge=1, le=3650)
    worker_max_iterations: int = Field(default=12, ge=1, le=30)
    # Looking a place up and finding events are extraction jobs, not judgement calls, so they run
    # on a smaller model with less thinking. Empty falls back to the chat model.
    worker_model: str = "claude-haiku-4-5"
    worker_effort: Effort = "low"
    travel_speed_kmh: float = Field(default=50.0, gt=0, le=200)
    road_factor: float = Field(default=1.3, ge=1, le=3)
    digest_chat_id: str | None = None
    digest_day: Weekday = "thu"
    digest_hour: int = Field(default=18, ge=0, le=23)
    follow_up_hour: int = Field(default=10, ge=0, le=23)
    # Bring up a task kept for "some Saturday morning" when one comes round free (jobs/nudges.py).
    task_nudges: bool = True
    google_calendar_id: str | None = None
    google_token_path: Path = Path("data/google_token.json")
    enrichment_notes: bool = True

    # The web page (see familydb/web/). Off unless WEB_ENABLED is set.
    web_enabled: bool = False
    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8080, ge=1, le=65535)
    web_password: str | None = None
    # The family password as chosen on the page, hashed (see web/auth.py). Once there is one it is
    # the only password the page takes: WEB_PASSWORD was the installer's, printed in a terminal.
    web_password_hash: str | None = None
    web_secret_key: str | None = None
    web_session_days: int = Field(default=30, ge=1, le=3650)
    web_allow_no_password: bool = False
    web_trust_proxy: bool = False
    web_title: str = "FamilyDB"

    # Console and logging
    console_member: str | None = None
    log_level: str = "INFO"

    @model_validator(mode="before")
    @classmethod
    def _blank_means_unset(cls, data: Any) -> Any:
        """Drop empty values so the default applies, as an unanswered question should."""
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
        """A name as it is said: on one line, with no control characters, and no braces, since
        it goes wherever {name} is written and a {name} inside it would be filled in again."""
        if not isinstance(value, str):
            return value  # pydantic says what is wrong with it
        name = value.strip()
        if any(unicodedata.category(character) in ("Cc", "Zl", "Zp") for character in name):
            raise ValueError("her name goes on one line, with no control characters in it")
        if "{" in name or "}" in name:
            raise ValueError("her name cannot have a brace in it")
        return name

    @field_validator("persona_text", mode="before")
    @classmethod
    def _rewrites_by_persona(cls, value: Any) -> Any:
        """Each rewrite under the persona it belongs to, from any value ever stored or set.

        It used to be one string, the rewrite of the only persona there was, and a setting that
        fails to load takes every stored setting with it, so a string that is not a JSON object
        still loads, as hers. A key is read as the persona setting reads it, so "vera" is still
        her; one with no folder is kept and never used, so removing a folder breaks nothing.
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
            return value  # pydantic says what is wrong with it
        rewrites: dict[str, Any] = {}
        for key, entry in value.items():
            if isinstance(entry, PersonaRewrite):
                entry = entry.model_dump()
            elif isinstance(entry, str) or entry is None:
                entry = {"text": entry}
            if isinstance(entry, Mapping) and not str(entry.get("text") or "").strip():
                continue  # nothing written is no rewrite
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
        """The resolved IANA zone name."""
        return self._tz

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self._tz)

    @property
    def southern_hemisphere(self) -> bool:
        return self.home_lat is not None and self.home_lat < 0

    def masked(self) -> dict[str, Any]:
        """All settings as a dict, a rewrite of her as one too, with secrets replaced by a marker,
        plus the resolved zone."""
        out: dict[str, Any] = {}
        for name, value in self.model_dump().items():
            if name in SECRET_FIELDS and value:
                value = "****"
            out[name] = value
        out["tz"] = self.tz
        return out


def describe(exc: ValidationError) -> str:
    """A validation failure as a person reading a journal wants it: which setting, and why."""
    lines = []
    for error in exc.errors():
        name = ".".join(str(part) for part in error["loc"]) or "setting"
        lines.append(f"  {name}: {error['msg']}")
    return "a setting will not do:\n" + "\n".join(lines)


def load_settings(env_file: str | Path | None = ".env", **overrides: Any) -> Settings:
    """Build settings from the environment, an optional .env file, and explicit overrides.

    A value that will not validate is a configuration problem, not a programming one, so it
    arrives as a ConfigError naming the setting. `apply_overrides` deliberately does not do
    this: the settings page wants pydantic's own error to put against the right box.
    """
    try:
        return Settings(_env_file=env_file, **overrides)
    except ValidationError as exc:
        raise ConfigError(describe(exc)) from exc


def apply_overrides(base: Settings, values: dict[str, Any]) -> Settings:
    """`base` with these values on top, validated as if they had been in the environment.

    Raises pydantic's ValidationError when a value will not do, which is what the page shows.
    """
    if not values:
        return base
    merged = {**base.model_dump(), **values}
    merged.pop("tz", None)  # a property, not a field
    return Settings(_env_file=None, **merged)
