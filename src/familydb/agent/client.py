"""Anthropic client construction and the constant part of every request."""

from __future__ import annotations

from typing import Any

import anthropic

from familydb.config import Settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def make_client(settings: Settings) -> anthropic.Anthropic:
    """A client for the configured key. With no key the SDK uses its own credential lookup."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)


def request_params(settings: Settings) -> dict[str, Any]:
    """Model, limits, thinking, effort and refusal fallbacks. Identical on every call."""
    params: dict[str, Any] = {
        "model": settings.anthropic_model,
        "max_tokens": settings.anthropic_max_tokens,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": settings.anthropic_effort},
    }
    if settings.anthropic_fallbacks:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params
