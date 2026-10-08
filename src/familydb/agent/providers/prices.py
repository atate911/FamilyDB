"""What each model costs (an estimate, not a bill), and which models the settings page suggests.

SDK-free. What the daily check found (familydb/model_watch.py) is laid over the built-in table
(US dollars per million tokens, September 2026) by `use`. A model not listed is counted at
`UNLISTED`, dearer than any listed, so the daily limit stops early rather than late."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PER_MILLION = 1_000_000


@dataclass(frozen=True)
class Price:
    input: float
    output: float
    cached: float  # reading the cached prefix
    search: float  # one hosted web search
    minute: float = 0.0  # a minute of recording, for a model that hears by the minute


# Claude writes the cache at 1.25x the input price for five minutes, 2x for an hour.
CACHE_WRITE = {"5m": 1.25, "1h": 2.0}
UNLISTED = Price(input=15.0, output=75.0, cached=1.5, search=0.035, minute=0.1)


def _claude(inp: float, out: float) -> Price:
    return Price(input=inp, output=out, cached=inp / 10, search=0.01)


# Looked up by prefix, longest first (`price`), so a dated snapshot such as
# claude-haiku-4-5-20251001 costs what its family does.
PRICES: dict[str, dict[str, Price]] = {
    "anthropic": {
        "claude-fable-5-1": _claude(10.0, 50.0),
        "claude-fable-5": _claude(10.0, 50.0),
        "claude-opus-5-5": _claude(4.0, 20.0),
        "claude-opus-5": _claude(5.0, 25.0),
        "claude-opus-4-8": _claude(5.0, 25.0),
        "claude-sonnet-5": _claude(2.0, 10.0),
        "claude-sonnet-4-6": _claude(3.0, 15.0),
        "claude-haiku-4-5": _claude(1.0, 5.0),
    },
    "openai": {
        # Up to 272K tokens of input; past that twice as much.
        "gpt-6-luna": Price(input=0.10, output=0.50, cached=0.01, search=0.01),
        "gpt-6-sol": Price(input=2.0, output=10.0, cached=0.20, search=0.01),
        "gpt-6-astra": Price(input=10.0, output=50.0, cached=1.0, search=0.01),
        "gpt-5-mini": Price(input=0.25, output=2.0, cached=0.025, search=0.01),
        "gpt-5": Price(input=1.25, output=10.0, cached=0.125, search=0.01),
    },
    "gemini": {
        # Up to 200K tokens of input; $14 per thousand grounded searches on Gemini 3.
        "gemini-3.1-flash-lite": Price(input=0.25, output=1.50, cached=0.025, search=0.014),
        "gemini-3.8-flash": Price(input=0.75, output=3.75, cached=0.075, search=0.014),
        "gemini-3.1-pro-preview": Price(input=2.0, output=12.0, cached=0.20, search=0.014),
        "gemini-2.5-pro": Price(input=1.25, output=10.0, cached=0.31, search=0.035),
    },
}


# Models that only hear voice notes, apart from PRICES so none is offered for chat. Audio is
# counted as input tokens; whisper-1 is billed by the minute.
HEARING: dict[str, dict[str, Price]] = {
    "openai": {
        "gpt-4o-mini-transcribe": Price(input=1.25, output=5.0, cached=0.0, search=0.0),
        "gpt-4o-transcribe": Price(input=2.5, output=10.0, cached=0.0, search=0.0),
        "whisper-1": Price(input=0.0, output=0.0, cached=0.0, search=0.0, minute=0.006),
    },
}


# One hosted web search, by company, for a price the lists gave without one.
SEARCH = {"anthropic": 0.01, "openai": 0.01, "gemini": 0.014}

# The daily check's findings, laid over PRICES; set whole by `use` (App.refresh).
_LIVE: dict[str, dict[str, Price]] = {}
_OFFERED: dict[str, tuple[str, ...]] = {}
_NOTES: dict[tuple[str, str], str] = {}
_SWAPS: dict[tuple[str, str], str] = {}
# What the admin of a company the settings define typed for its models (companies.use); it wins
# over what the daily check found, since it is the family's own word.
_OWN: dict[str, dict[str, Price]] = {}


def own(table: dict[str, dict[str, Price]]) -> None:
    """Put in force the prices typed for added companies' models, by company then model name."""
    global _OWN
    _OWN = table


def use(
    live: dict[str, dict[str, Price]],
    offered: dict[str, tuple[str, ...]],
    notes: dict[tuple[str, str], str] | None = None,
    swaps: dict[tuple[str, str], str] | None = None,
) -> None:
    """Put what the daily check found in force."""
    global _LIVE, _OFFERED, _NOTES, _SWAPS
    _LIVE, _OFFERED, _NOTES, _SWAPS = live, offered, notes or {}, swaps or {}


def swapped(provider: str, model: str) -> str:
    """The model to ask in this one's place: itself, unless gone or past its day
    (model_watch.replacement)."""
    return _SWAPS.get((provider, model.lower()), model)


def note(provider: str, model: str) -> str | None:
    """The daily check's word on a model: new, or the day it goes."""
    return _NOTES.get((provider, model.lower()))


def price(provider: str | None, model: str | None) -> Price | None:
    """The price as the daily check found it, else built in; None when neither knows it. A
    company the settings define is matched by the exact name only: a prefix would price a dearer
    variant at its cheaper sibling's rate."""
    named = (model or "").lower()
    exact_only = (provider or "") not in PRICES
    for tables in (_OWN, _LIVE, PRICES, HEARING):
        table = tables.get(provider or "", {})
        if exact_only:
            if named in table:
                return table[named]
            continue
        for prefix in sorted(table, key=len, reverse=True):
            if named == prefix or named.startswith(prefix + "-"):
                return table[prefix]
    return None


def suggestions(provider: str) -> tuple[str, ...]:
    """Models to offer on the settings page, cheapest first: the daily check's, else built in."""
    if _OFFERED.get(provider):
        return _OFFERED[provider]
    table = PRICES.get(provider) or _OWN.get(provider, {})
    return tuple(sorted(table, key=lambda name: (table[name].output, name)))


def hearing_suggestions(provider: str) -> tuple[str, ...]:
    """Models worth offering for hearing voice notes, cheapest first."""
    table = HEARING.get(provider, {})
    return tuple(sorted(table, key=lambda name: (table[name].input, name)))


def cost(
    provider: str | None,
    model: str | None,
    usage: dict[str, Any],
    *,
    cache_ttl: str = "1h",
) -> tuple[float, bool]:
    """Dollars for one call, and whether the model was listed. `input_tokens` is the uncached
    part only; `audio_seconds` is for a model that bills by the minute."""
    listed = price(provider, model)
    rate = listed or UNLISTED
    write = rate.input * CACHE_WRITE.get(cache_ttl, 2.0) if provider == "anthropic" else rate.input
    dollars = (
        (
            (usage.get("input_tokens") or 0) * rate.input
            + (usage.get("cache_read_input_tokens") or 0) * rate.cached
            + (usage.get("cache_creation_input_tokens") or 0) * write
            + (usage.get("output_tokens") or 0) * rate.output
        )
        / PER_MILLION
        + (usage.get("web_searches") or 0) * rate.search
        + (usage.get("audio_seconds") or 0) / 60 * rate.minute
    )
    return dollars, listed is not None
