"""Settings, loaded from the environment and an optional .env file."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, Field, PrivateAttr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]
ProviderName = Literal["anthropic", "openai", "gemini"]
CacheTTL = Literal["5m", "1h"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

SECRET_FIELDS = frozenset(
    {
        "anthropic_api_key",
        "gemini_api_key",
        "openai_api_key",
        "telegram_bot_token",
        "web_password",
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


class Settings(BaseSettings):
    """Runtime configuration. Field names double as environment variable names, any case."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", validate_by_name=True
    )

    # Claude
    # Who answers. `worker_provider` empty means the lookup and discovery turns use `provider`.
    provider: ProviderName = "anthropic"
    worker_provider: ProviderName | Literal[""] = ""
    provider_fallback: bool = True

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-pro"
    gemini_worker_model: str = "gemini-2.5-flash"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5"
    openai_worker_model: str = "gpt-5-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    # Applies to whoever answers, so it is not named for one of them. ANTHROPIC_EFFORT still works.
    effort: Effort = Field(
        default="medium", validation_alias=AliasChoices("EFFORT", "ANTHROPIC_EFFORT")
    )
    # Named for no vendor, because it caps the answer on either. The old ANTHROPIC_MAX_TOKENS
    # still works for anyone who already has it in a .env.
    max_output_tokens: int = Field(
        default=16000, validation_alias=AliasChoices("MAX_OUTPUT_TOKENS", "ANTHROPIC_MAX_TOKENS")
    )
    anthropic_fallbacks: bool = True
    # An hour, because a family writes in bursts with long gaps: a five-minute cache would be
    # cold almost every time and the whole prefix would be paid for again.
    anthropic_cache_ttl: CacheTTL = "1h"
    agent_max_iterations: int = 8
    history_limit: int = 20
    # The ideas list rides in the cached prompt on every message, so it cannot grow without end.
    # Past this many, the oldest are left out and the model is told to search for them.
    prompt_idea_limit: int = 150
    history_hours: float = 6.0

    # Storage and home
    familydb_path: Path = Path("data/familydb.sqlite3")
    # FAMILYDB_TZ, an IANA name. When unset, the OS TZ variable is used if it names a zone.
    family_tz: str | None = Field(default=None, validation_alias="FAMILYDB_TZ")
    _tz: str = PrivateAttr(default="UTC")
    home_lat: float | None = None
    home_lon: float | None = None
    home_area: str = ""
    weather_units: Literal["metric", "imperial"] = "metric"

    # Optional services
    web_tools_enabled: bool = False
    telegram_bot_token: str | None = None
    # In groups, only answer messages that mention the bot or reply to it.
    telegram_require_mention: bool = False
    # Failed messages are retried this often, this many times.
    retry_interval_minutes: int = 5
    retry_max_attempts: int = 3

    # Enrichment, suggestions and scheduled prompts
    enrich_interval_minutes: int = 2
    enrich_batch: int = 3
    place_stale_days: int = 30
    worker_max_iterations: int = 12
    # Looking a place up and finding events are extraction jobs, not judgement calls, so they run
    # on a smaller model with less thinking. Empty falls back to the chat model.
    worker_model: str = "claude-haiku-4-5-20251001"
    worker_effort: Effort = "low"
    travel_speed_kmh: float = 50.0
    road_factor: float = 1.3
    digest_chat_id: str | None = None
    digest_day: Weekday = "thu"
    digest_hour: int = 18
    follow_up_hour: int = 10
    google_calendar_id: str | None = None
    google_token_path: Path = Path("data/google_token.json")
    enrichment_notes: bool = True

    # The read-only web page (see familydb/web/). Off unless WEB_ENABLED is set.
    web_enabled: bool = False
    web_host: str = "127.0.0.1"
    web_port: int = 8080
    web_password: str | None = None
    web_secret_key: str | None = None
    web_session_days: int = 30
    web_allow_no_password: bool = False
    web_trust_proxy: bool = False
    web_title: str = "FamilyDB"

    # Console and logging
    console_member: str | None = None
    log_level: str = "INFO"

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
        """All settings as a dict, with secrets replaced by a marker, plus the resolved zone."""
        out: dict[str, Any] = {}
        for name in type(self).model_fields:
            value = getattr(self, name)
            if name in SECRET_FIELDS and value:
                value = "****"
            out[name] = value
        out["tz"] = self.tz
        return out


def load_settings(env_file: str | Path | None = ".env", **overrides: Any) -> Settings:
    """Build settings from the environment, an optional .env file, and explicit overrides."""
    return Settings(_env_file=env_file, **overrides)
