"""What each model costs, and so which models the settings page suggests.

No SDK is imported here, so the page and the spending limit can read it without loading one.
Prices are US dollars per million tokens as the vendors published them in September 2026, plus
the price of one hosted web search. They are an estimate for the daily limit and the status
page, not a bill: check them against the vendor's own figures now and then.

A model that is not listed is counted at `UNLISTED`, which is dearer than anything listed, so
a new or mistyped name makes the daily limit stop early rather than late.
"""

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


# Claude writes the cache at 1.25x the input price for five minutes, 2x for an hour.
CACHE_WRITE = {"5m": 1.25, "1h": 2.0}
UNLISTED = Price(input=15.0, output=75.0, cached=1.5, search=0.035)


def _claude(inp: float, out: float) -> Price:
    return Price(input=inp, output=out, cached=inp / 10, search=0.01)


# Longest name first where one is the start of another, since lookup is by prefix: a dated
# snapshot such as claude-haiku-4-5-20251001 costs what its family does.
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
        # Up to 272K tokens of input; past that a request costs twice as much, which a family
        # conversation never reaches.
        "gpt-6-luna": Price(input=0.10, output=0.50, cached=0.01, search=0.01),
        "gpt-5-mini": Price(input=0.25, output=2.0, cached=0.025, search=0.01),
        "gpt-5": Price(input=1.25, output=10.0, cached=0.125, search=0.01),
    },
    "gemini": {
        "gemini-2.5-pro": Price(input=1.25, output=10.0, cached=0.31, search=0.035),
    },
}


def price(provider: str | None, model: str | None) -> Price | None:
    """The listed price for this model, or None when it is not listed."""
    named = (model or "").lower()
    table = PRICES.get(provider or "", {})
    for prefix in sorted(table, key=len, reverse=True):
        if named == prefix or named.startswith(prefix + "-"):
            return table[prefix]
    return None


def suggestions(provider: str) -> tuple[str, ...]:
    """Models worth offering on the settings page for this provider, cheapest first."""
    table = PRICES.get(provider, {})
    return tuple(sorted(table, key=lambda name: (table[name].output, name)))


def cost(
    provider: str | None,
    model: str | None,
    usage: dict[str, Any],
    *,
    cache_ttl: str = "1h",
) -> tuple[float, bool]:
    """What one call cost in dollars, and whether the model was listed or counted as UNLISTED.

    `input_tokens` is the uncached part only, as every provider reports it to the loop.
    """
    listed = price(provider, model)
    rate = listed or UNLISTED
    write = rate.input * CACHE_WRITE.get(cache_ttl, 2.0) if provider == "anthropic" else rate.input
    dollars = (
        (usage.get("input_tokens") or 0) * rate.input
        + (usage.get("cache_read_input_tokens") or 0) * rate.cached
        + (usage.get("cache_creation_input_tokens") or 0) * write
        + (usage.get("output_tokens") or 0) * rate.output
    ) / PER_MILLION + (usage.get("web_searches") or 0) * rate.search
    return dollars, listed is not None
