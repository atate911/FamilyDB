from types import SimpleNamespace

import pytest

from familydb.agent.client import ensure_credentials, request_params
from familydb.errors import AgentError


def test_ensure_credentials_requires_some_source() -> None:
    empty = SimpleNamespace(api_key=None, auth_token=None, credentials=None)
    with pytest.raises(AgentError) as info:
        ensure_credentials(empty)
    assert info.value.retryable is False
    ensure_credentials(SimpleNamespace(api_key="sk", auth_token=None, credentials=None))
    ensure_credentials(SimpleNamespace(api_key=None, auth_token="tok", credentials=None))


def test_request_params_follow_settings(settings) -> None:
    params = request_params(settings)
    assert params["model"] == "claude-opus-5"
    assert params["betas"] == ["server-side-fallback-2026-07-01"]
    assert params["fallbacks"] == "default"
    assert params["output_config"] == {"effort": "medium"}
    quiet = settings.model_copy(update={"anthropic_fallbacks": False, "anthropic_effort": "low"})
    params = request_params(quiet)
    assert "fallbacks" not in params and "betas" not in params
    assert params["output_config"] == {"effort": "low"}
