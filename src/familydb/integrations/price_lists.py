"""Two public price lists for the daily check (familydb/model_watch.py): LiteLLM's
model_prices_and_context_window.json and OpenRouter's models (no key). Each is kept to the three
companies as `Listed` (USD per million tokens, tool use, release and retirement days where
given). Read against each other since neither is the family's; nothing about the family is sent."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
PER_MILLION = 1_000_000
TIMEOUT = 30
# LiteLLM's list is about 3 MB.
MAX_BYTES = 40 * 1024 * 1024

# Each list's name for a company, and ours.
LITELLM_PROVIDERS = {"openai": "openai", "anthropic": "anthropic", "gemini": "gemini"}
OPENROUTER_PROVIDERS = {"openai": "openai", "anthropic": "anthropic", "google": "gemini"}
# What a model is for, in LiteLLM's words: only those that chat are offered.
CHAT_MODES = frozenset({"chat", "responses"})


class PriceListError(Exception):
    """A list could not be fetched or read."""


@dataclass(frozen=True)
class Listed:
    input: float | None
    output: float | None
    cached: float | None
    tools: bool | None
    retires_on: str | None
    released: str | None = None


Prices = dict[str, dict[str, Listed]]  # company -> model -> what the list says


class PriceListsAPI(Protocol):
    def litellm(self) -> Prices: ...

    def openrouter(self) -> Prices: ...


def _per_million(value: Any) -> float | None:
    """A per-token price (number or string) in dollars a million; None when not given."""
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return round(amount * PER_MILLION, 6) if amount >= 0 else None


def parse_litellm(document: Any) -> Prices:

    if not isinstance(document, dict):
        raise PriceListError("LiteLLM's list is not what it used to be: not a JSON object")
    found: Prices = {}
    for key, entry in document.items():
        if not isinstance(entry, dict):
            continue
        company = LITELLM_PROVIDERS.get(str(entry.get("litellm_provider", "")))
        if company is None or entry.get("mode") not in CHAT_MODES or ":" in key.split("/")[-1]:
            continue
        name = key.split("/")[-1].lower()
        found.setdefault(company, {})[name] = Listed(
            input=_per_million(entry.get("input_cost_per_token")),
            output=_per_million(entry.get("output_cost_per_token")),
            cached=_per_million(entry.get("cache_read_input_token_cost")),
            tools=entry.get("supports_function_calling"),
            retires_on=_day(entry.get("deprecation_date")),
        )
    if not found:
        raise PriceListError("LiteLLM's list named no model from OpenAI, Anthropic or Google")
    return found


def parse_openrouter(document: Any) -> Prices:

    rows = document.get("data") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise PriceListError("OpenRouter's list is not what it used to be: no data")
    found: Prices = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        maker, _, name = str(row.get("id", "")).partition("/")
        company = OPENROUTER_PROVIDERS.get(maker)
        # A variant (":free", ":online") is OpenRouter's own offer, not the company's price.
        if company is None or not name or ":" in name:
            continue
        name = name.lower()
        if company == "anthropic":
            name = name.replace(".", "-")  # OpenRouter's claude-sonnet-4.5 is claude-sonnet-4-5
        pricing = row.get("pricing") if isinstance(row.get("pricing"), dict) else {}
        parameters = row.get("supported_parameters")
        found.setdefault(company, {})[name] = Listed(
            input=_per_million(pricing.get("prompt")),
            output=_per_million(pricing.get("completion")),
            cached=_per_million(pricing.get("input_cache_read")),
            tools=("tools" in parameters) if isinstance(parameters, list) else None,
            retires_on=_day(row.get("expiration_date")),
            released=_released(row.get("created")),
        )
    if not found:
        raise PriceListError("OpenRouter's list named no model from OpenAI, Anthropic or Google")
    return found


def _released(value: Any) -> str | None:
    """OpenRouter's `created` (epoch seconds) as the day, else None."""
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, UTC).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _day(value: Any) -> str | None:
    """A list's date as YYYY-MM-DD, else None."""
    text = str(value or "")[:10]
    return text if len(text) == 10 and text[4] == "-" and text[7] == "-" else None


class PriceLists:
    """Both lists over HTTPS, fetched afresh each call (the check runs daily)."""

    @staticmethod
    def _fetch(url: str) -> Any:
        request = urllib.request.Request(
            url, headers={"User-Agent": "familydb/0.1", "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                body = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise PriceListError(f"{url} answered HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PriceListError(f"{url} could not be reached: {exc}") from exc
        if len(body) > MAX_BYTES:
            raise PriceListError(f"{url} sent more than a price list could be")
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise PriceListError(f"{url} did not send JSON: {exc}") from exc

    def litellm(self) -> Prices:
        return parse_litellm(self._fetch(LITELLM_URL))

    def openrouter(self) -> Prices:
        return parse_openrouter(self._fetch(OPENROUTER_URL))
