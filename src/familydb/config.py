"""Settings, loaded from the environment and an optional .env file."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, PrivateAttr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]
CacheTTL = Literal["5m", "1h"]

SECRET_FIELDS = frozenset({"anthropic_api_key", "telegram_bot_token"})
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
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    anthropic_effort: Effort = "medium"
    anthropic_max_tokens: int = 16000
    anthropic_fallbacks: bool = True
    anthropic_cache_ttl: CacheTTL = "5m"
    agent_max_iterations: int = 8
    history_limit: int = 20
    history_hours: float = 6.0

    # Storage and home
    familydb_path: Path = Path("data/familydb.sqlite3")
    # FAMILYDB_TZ, an IANA name. When unset, the OS TZ variable is used if it names a zone.
    family_tz: str | None = Field(default=None, validation_alias="FAMILYDB_TZ")
    _tz: str = PrivateAttr(default="UTC")
    home_lat: float | None = None
    home_lon: float | None = None
    home_area: str = ""

    # Optional services, wired in later milestones
    web_tools_enabled: bool = False
    telegram_bot_token: str | None = None
    google_calendar_id: str | None = None
    google_token_path: Path = Path("data/google_token.json")
    enrichment_notes: bool = True

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
