"""Connecting Google Calendar from the settings page, with no browser on the server."""

from __future__ import annotations

import json
import re

import pytest

from familydb.app import App
from familydb.integrations import google_calendar as google
from familydb.web import create_app

PASSWORD = "open sesame please"
DESKTOP = json.dumps(
    {
        "installed": {
            "client_id": "123.apps.googleusercontent.com",
            "client_secret": "not-really-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
)


class Flow:
    """What google_auth_oauthlib's Flow does for us: take a code, hold the credentials."""

    def __init__(self) -> None:
        self.codes: list[str] = []
        self.credentials = type("Creds", (), {"to_json": lambda self: '{"token": "t"}'})()

    def fetch_token(self, *, code: str) -> None:
        if code == "rejected":
            raise ValueError("invalid_grant")
        self.codes.append(code)


def _token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/connections").text)
    assert found is not None
    return found.group(1)


@pytest.fixture
def page(settings, clock, conn, family, monkeypatch):
    flow = Flow()
    calendars = [
        {
            "id": "family@group.calendar.google.com",
            "summary": "Family",
            "primary": False,
            "access": "owner",
        },
        {"id": "sam@example.com", "summary": "Sam", "primary": True, "access": "owner"},
    ]
    monkeypatch.setattr(
        google, "begin_consent", lambda config: ("https://accounts.google.com/x", flow, "st8")
    )
    monkeypatch.setattr(google, "list_calendars", lambda creds: calendars)
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    client.post("/login", data={"password": PASSWORD})
    client.app, client.flow = app, flow
    return client


def test_connecting_takes_three_steps_on_the_page(page) -> None:
    started = page.post("/settings/google/start", data={"csrf": _token(page), "client": DESKTOP})
    assert started.status_code == 200 and "https://accounts.google.com/x" in started.text

    pasted = "http://127.0.0.1:53682/?state=st8&code=4/abc&scope=calendar"
    finished = page.post("/settings/google/finish", data={"csrf": _token(page), "pasted": pasted})
    assert finished.status_code == 200 and "Which calendar is the family" in finished.text
    assert page.flow.codes == ["4/abc"]
    token = page.app.settings.google_token_path
    assert json.loads(token.read_text()) == {"token": "t"}

    chosen = page.post(
        "/settings/google/calendar",
        data={"csrf": _token(page), "calendar_id": "family@group.calendar.google.com"},
    )
    assert chosen.status_code == 302
    assert page.app.settings.google_calendar_id == "family@group.calendar.google.com"
    assert "Connected, using" in page.get("/settings/connections").text


def test_a_calendar_the_connection_did_not_offer_is_refused(page) -> None:
    page.post("/settings/google/start", data={"csrf": _token(page), "client": DESKTOP})
    page.post("/settings/google/finish", data={"csrf": _token(page), "pasted": "4/abc"})
    refused = page.post(
        "/settings/google/calendar", data={"csrf": _token(page), "calendar_id": "someone@else"}
    )
    assert refused.status_code == 400 and page.app.settings.google_calendar_id is None


def test_a_web_application_client_is_explained_not_accepted(page) -> None:
    web = json.dumps({"web": {"client_id": "x"}})
    response = page.post("/settings/google/start", data={"csrf": _token(page), "client": web})
    assert response.status_code == 400 and "Desktop app" in response.text


def test_finishing_without_starting_says_to_start_again(page) -> None:
    response = page.post("/settings/google/finish", data={"csrf": _token(page), "pasted": "x"})
    assert response.status_code == 400 and "Start again" in response.text


# -- the integration's own checks ---------------------------------------------------------


def test_an_address_from_an_earlier_try_is_refused(tmp_path) -> None:
    with pytest.raises(google.GoogleSetupError, match="earlier try"):
        google.finish_consent(
            Flow(), "http://127.0.0.1:53682/?state=old&code=c", tmp_path / "t.json", state="new"
        )


def test_google_saying_no_is_passed_on(tmp_path) -> None:
    with pytest.raises(google.GoogleSetupError, match="access_denied"):
        google.finish_consent(Flow(), "http://127.0.0.1:53682/?error=access_denied", tmp_path)


def test_a_code_google_rejects_saves_nothing(tmp_path) -> None:
    with pytest.raises(google.GoogleSetupError, match="would not take"):
        google.finish_consent(Flow(), "rejected", tmp_path / "t.json")
    assert not (tmp_path / "t.json").exists()


def test_the_real_library_makes_a_consent_link_with_pkce() -> None:
    url, flow, state = google.begin_consent(google.client_config(DESKTOP))
    assert url.startswith("https://accounts.google.com/o/oauth2/auth?")
    assert "code_challenge_method=S256" in url and f"state={state}" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A53682%2F" in url
    assert "access_type=offline" in url and flow.code_verifier
