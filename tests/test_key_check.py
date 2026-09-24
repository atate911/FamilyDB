"""Checking a key before it is stored: each vendor's own answer, read for what it says.

The setup page asks this once, when a key is pasted. It costs nothing: it is the model lookup
`model_exists` makes, and only a definite "that key is wrong" may stop a key being saved.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from familydb.agent import providers
from familydb.agent.providers import anthropic as anthropic_provider
from familydb.agent.providers import gemini as gemini_provider
from familydb.agent.providers import openai as openai_provider
from familydb.errors import AgentError

REQUEST = httpx.Request("GET", "https://api.example.com/v1/models/x")


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=REQUEST)


class _Models:
    def __init__(self, outcome: Exception | None) -> None:
        self.outcome = outcome
        self.asked: list[str] = []

    def retrieve(self, model: str) -> Any:
        self.asked.append(model)
        if self.outcome is not None:
            raise self.outcome
        return {"id": model}

    def get(self, *, model: str) -> Any:  # Google's spelling of the same question
        return self.retrieve(model)


class _Client:
    """Stands in for a vendor SDK's client: only the model lookup, and closing."""

    def __init__(self, outcome: Exception | None) -> None:
        self.models = _Models(outcome)
        self.options: dict[str, Any] = {}
        self.closed = False

    def with_options(self, **options: Any) -> _Client:
        self.options = options
        return self

    def close(self) -> None:
        self.closed = True


def _provider(monkeypatch, module, name: str, settings, outcome, **keys):
    client = _Client(outcome)
    monkeypatch.setattr(module, "make_client", lambda *args, **kwargs: client)
    return providers.build(name, settings.model_copy(update=keys)), client


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (None, "works"),
        (
            openai_provider.openai.AuthenticationError(
                "Incorrect API key provided", response=_response(401), body=None
            ),
            "refused",
        ),
        (
            openai_provider.openai.NotFoundError(
                "The model does not exist", response=_response(404), body=None
            ),
            "unknown_model",
        ),
        # A key limited to writing replies may not list models: that is not a wrong key.
        (
            openai_provider.openai.PermissionDeniedError(
                "insufficient permissions", response=_response(403), body=None
            ),
            "unchecked",
        ),
        (openai_provider.openai.APIConnectionError(request=REQUEST), "unchecked"),
    ],
)
def test_openai_says_what_it_thinks_of_a_key(settings, monkeypatch, outcome, verdict) -> None:
    provider, client = _provider(
        monkeypatch, openai_provider, "openai", settings, outcome, openai_api_key="sk-test"
    )
    assert provider.check_key() == verdict
    assert client.models.asked == [provider.model_for("chat")]
    assert client.options == {"timeout": 10.0, "max_retries": 0}  # a page is waiting on it
    assert client.closed


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (None, "works"),
        (
            anthropic_provider.anthropic.AuthenticationError(
                "invalid x-api-key", response=_response(401), body=None
            ),
            "refused",
        ),
        (
            anthropic_provider.anthropic.NotFoundError(
                "model: claude-nope", response=_response(404), body=None
            ),
            "unknown_model",
        ),
        (anthropic_provider.anthropic.APIConnectionError(request=REQUEST), "unchecked"),
    ],
)
def test_anthropic_says_what_it_thinks_of_a_key(settings, monkeypatch, outcome, verdict) -> None:
    provider, client = _provider(monkeypatch, anthropic_provider, "anthropic", settings, outcome)
    assert provider.check_key() == verdict
    assert client.models.asked == [provider.model_for("chat")]
    assert client.closed


def _google(code: int, message: str) -> Exception:
    return gemini_provider.genai_errors.ClientError(
        code, {"error": {"code": code, "message": message, "status": "X"}}
    )


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (None, "works"),
        # Google says a key it does not know is a bad argument, not a missing credential.
        (_google(400, "API key not valid. Please pass a valid API key."), "refused"),
        (_google(401, "Request had invalid authentication credentials."), "refused"),
        (_google(404, "models/gemini-nope is not found"), "unknown_model"),
        (_google(400, "Some other bad request"), "unchecked"),
        (_google(403, "Generative Language API has not been used in project"), "unchecked"),
        (httpx.ConnectTimeout("timed out"), "unchecked"),
    ],
)
def test_gemini_says_what_it_thinks_of_a_key(settings, monkeypatch, outcome, verdict) -> None:
    provider, client = _provider(
        monkeypatch, gemini_provider, "gemini", settings, outcome, gemini_api_key="AIza-test"
    )
    assert provider.check_key() == verdict
    assert client.models.asked == [provider.model_for("chat")]


@pytest.mark.parametrize(
    ("module", "name"),
    [(openai_provider, "openai"), (anthropic_provider, "anthropic"), (gemini_provider, "gemini")],
)
def test_no_key_is_no_key_and_nothing_is_asked(settings, monkeypatch, module, name) -> None:
    def no_credentials(*args: Any, **kwargs: Any) -> Any:
        # What each make_client raises when there is nothing to send. Anthropic's also looks in
        # the SDK's own places first, so an empty setting alone is not the same thing there.
        raise AgentError("no credentials", retryable=False)

    monkeypatch.setattr(module, "make_client", no_credentials)
    assert providers.build(name, settings).check_key() == "no_key"
