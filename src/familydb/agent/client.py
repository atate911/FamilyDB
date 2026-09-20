"""Anthropic client construction and the constant part of every request."""

from __future__ import annotations

from typing import Any

import anthropic

from familydb.config import Settings
from familydb.errors import AgentError

FALLBACK_BETA = "server-side-fallback-2026-07-01"
CREDENTIAL_ATTRS = ("api_key", "auth_token", "credentials")


def ensure_credentials(client: Any) -> None:
    """Fail early, and clearly, when the SDK found no credentials from any source."""
    if all(getattr(client, name, None) is None for name in CREDENTIAL_ATTRS):
        raise AgentError(
            "no Anthropic credentials configured: set ANTHROPIC_API_KEY (see .env.example)",
            retryable=False,
        )


def make_client(settings: Settings) -> anthropic.Anthropic:
    """A client for the configured key. With no key the SDK uses its own credential lookup."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)
    ensure_credentials(client)
    return client


def request_params(
    settings: Settings, *, model: str | None = None, effort: str | None = None
) -> dict[str, Any]:
    """Model, limits, thinking, effort and refusal fallbacks.

    Identical on every chat call, which is what keeps the prompt cache warm. Worker turns pass a
    smaller model and less thinking, and have their own cache.
    """
    params: dict[str, Any] = {
        "model": model or settings.anthropic_model,
        "max_tokens": settings.anthropic_max_tokens,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort or settings.anthropic_effort},
    }
    if settings.anthropic_fallbacks:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params
