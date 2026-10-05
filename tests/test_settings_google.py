"""Connecting Google Calendar from the settings page: a service account's key and a calendar id."""

from __future__ import annotations

import json
import re

import httplib2
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from googleapiclient.errors import HttpError

from familydb.app import App
from familydb.integrations import google_calendar as google
from familydb.web import create_app

PASSWORD = "open sesame please"
EMAIL = "familydb@project.iam.gserviceaccount.com"
CALENDAR = "family@group.calendar.google.com"


def _key(**changes) -> str:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    info = {
        "type": "service_account",
        "project_id": "project",
        "private_key_id": "abc",
        "private_key": private.decode(),
        "client_email": EMAIL,
        "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return json.dumps({**info, **changes})


KEY = _key()


def _token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/connections").text)
    assert found is not None
    return found.group(1)


class Events:
    """The three calls `check_access` makes, answering as Google would, or refusing."""

    def __init__(self, refuse: dict[str, int] | None = None) -> None:
        self.refuse = refuse or {}
        self.calls: list[str] = []

    def _do(self, name: str, answer: dict):
        events = self

        class Request:
            def execute(self) -> dict:
                events.calls.append(name)
                if name in events.refuse:
                    status = events.refuse[name]
                    raise HttpError(httplib2.Response({"status": status}), b"{}", "no")
                return answer

        return Request()

    def list(self, **_):
        return self._do("list", {})

    def insert(self, **_):
        return self._do("insert", {"id": "check1"})

    def delete(self, **_):
        return self._do("delete", {})


@pytest.fixture
def events(monkeypatch) -> Events:
    found = Events()
    monkeypatch.setattr(
        google, "build_service", lambda creds: type("S", (), {"events": lambda self: found})()
    )
    return found


@pytest.fixture
def page(settings, clock, conn, family, events):
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    client.post("/login", data={"password": PASSWORD})
    client.app = app
    return client


def _connect(client, key=KEY, calendar=CALENDAR):
    return client.post(
        "/settings/google/connect",
        data={"csrf": _token(client), "key": key, "calendar_id": calendar},
    )


def test_connecting_is_one_form_and_keeps_the_key_and_the_calendar(page, events) -> None:
    response = _connect(page)
    assert response.status_code == 302
    assert events.calls == ["list", "insert", "delete"]  # read it, then changed it and put it back
    saved = json.loads(page.app.settings.google_key_path.read_text())
    assert saved["client_email"] == EMAIL
    assert page.app.settings.google_calendar_id == CALENDAR
    shown = page.get("/settings/connections").text
    assert "Connected, using" in shown and EMAIL in shown


def test_the_key_file_is_owner_only(page) -> None:
    _connect(page)
    assert page.app.settings.google_key_path.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize(
    ("refused", "words"),
    [
        ({"list": 404}, "shared with"),
        ({"list": 403}, "can see that calendar but not change"),
        ({"insert": 403}, "Make changes to events"),
    ],
)
def test_a_calendar_that_cannot_be_used_is_explained_and_nothing_is_kept(
    page, events, refused, words
) -> None:
    events.refuse = refused
    response = _connect(page)
    assert response.status_code == 400 and words in response.text
    assert EMAIL in response.text
    assert not page.app.settings.google_key_path.exists()
    assert page.app.settings.google_calendar_id is None


def test_a_project_without_the_calendar_api_is_told_to_turn_it_on(page, monkeypatch) -> None:
    class Disabled(Events):
        def list(self, **_):
            class Request:
                def execute(self_inner):
                    raise HttpError(
                        httplib2.Response({"status": 403}), b'{"error": "accessNotConfigured"}', "x"
                    )

            return Request()

    found = Disabled()
    monkeypatch.setattr(
        google, "build_service", lambda creds: type("S", (), {"events": lambda self: found})()
    )
    response = _connect(page)
    assert response.status_code == 400 and "Turn on the Google Calendar API" in response.text


def test_an_oauth_client_pasted_by_mistake_is_not_a_service_account_key(page) -> None:
    old = json.dumps({"installed": {"client_id": "123", "client_secret": "s"}})
    response = _connect(page, key=old)
    assert response.status_code == 400 and "service account" in response.text


@pytest.mark.parametrize("text", ["nope", "[1]", json.dumps({"type": "authorized_user"})])
def test_something_that_is_not_a_key_is_refused(page, text) -> None:
    assert _connect(page, key=text).status_code == 400


def test_a_damaged_private_key_is_refused(page) -> None:
    damaged = _key(private_key="-----BEGIN PRIVATE KEY-----\nzz")
    assert _connect(page, key=damaged).status_code == 400


def test_a_calendar_id_is_required(page) -> None:
    response = _connect(page, calendar="  ")
    assert response.status_code == 400 and "calendar's id" in response.text


# -- the integration's own checks


def test_a_service_account_key_loads_without_asking_google(tmp_path) -> None:
    path = tmp_path / "key.json"
    google.save_key(path, KEY)
    creds = google.load_credentials(path)
    assert creds.service_account_email == EMAIL
    assert google.service_account_email(path) == EMAIL


def test_with_no_key_saved_there_is_no_address_to_share_with(tmp_path) -> None:
    assert google.service_account_email(tmp_path / "none.json") is None


def test_an_unreadable_key_asks_to_connect_again(tmp_path) -> None:
    from familydb.errors import ToolUnavailable

    path = tmp_path / "key.json"
    path.write_text("{ half a file")
    with pytest.raises(ToolUnavailable, match="connect the calendar again"):
        google.load_credentials(path)
