"""The family password, chosen and changed on the page instead of in a file on the server."""

from __future__ import annotations

import re
from contextlib import closing
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from familydb import passwords
from familydb.app import App
from familydb.store import settings as settings_store
from familydb.web import check_configuration, create_app

INSTALLERS = "installer-made-password-1"  # what WEB_PASSWORD holds after an install
OURS = "pancakes on sunday mornings"


@pytest.fixture
def page(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": INSTALLERS}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": INSTALLERS}).status_code == 302
    client.app = app
    client.clock = clock
    return client


def _token(client) -> str:
    return re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/security").text).group(1)


def _choose(client, new: str, again: str | None = None, **extra: str):
    form = {"csrf": _token(client), "new": new, "again": new if again is None else again}
    return client.post("/settings/password", data={**form, **extra})


def test_a_stored_password_is_a_salted_hash_that_only_its_password_matches() -> None:
    stored = passwords.hash_password(OURS)
    assert OURS not in stored and stored.startswith("scrypt$")
    assert passwords.hash_matches(stored, OURS)
    assert not passwords.hash_matches(stored, OURS + "!")
    assert passwords.hash_password(OURS) != stored  # a fresh salt every time
    for broken in ("", "scrypt$1$2", "md5$1$1$1$AAAA$AAAA", "scrypt$x$8$1$AAAA$AAAA"):
        assert not passwords.hash_matches(broken, OURS)


def test_the_family_chooses_their_own_right_after_signing_in(page, settings, clock) -> None:
    other = page.application.test_client()  # another browser, signed in with the installer's
    assert other.post("/login", data={"password": INSTALLERS}).status_code == 302

    done = _choose(page, OURS)  # no need to type the installer's again: it was just typed
    assert done.status_code == 302 and done.headers["Location"] == "/settings"
    assert page.app.settings.web_password_hash
    assert page.get("/settings").status_code == 200  # this browser stays signed in
    assert other.get("/settings").status_code == 302  # the other one is asked again

    fresh = page.application.test_client()
    assert fresh.post("/login", data={"password": INSTALLERS}).status_code == 401
    assert fresh.post("/login", data={"password": OURS}).status_code == 302


def test_after_that_a_change_needs_the_password_in_force(page) -> None:
    assert _choose(page, OURS).status_code == 302
    missing = _choose(page, "a different family sentence")
    assert missing.status_code == 401 and "Type the password you use now" in missing.text
    wrong = _choose(page, "a different family sentence", current="not it at all")
    assert wrong.status_code == 401 and "not right" in wrong.text
    right = _choose(page, "a different family sentence", current=OURS)
    assert right.status_code == 302
    fresh = page.application.test_client()
    assert fresh.post("/login", data={"password": "a different family sentence"}).status_code == 302


def test_guessing_the_password_in_force_is_locked_out(page) -> None:
    assert _choose(page, OURS).status_code == 302
    for _ in range(5):
        assert _choose(page, "yet another sentence", current="guess").status_code == 401
    locked = _choose(page, "yet another sentence", current=OURS)
    assert locked.status_code == 429  # even the right one, until the lockout passes


def test_a_first_choice_long_after_signing_in_still_needs_the_installers(page, clock) -> None:
    clock.advance(timedelta(hours=2))
    refused = _choose(page, OURS)
    assert refused.status_code == 401 and not page.app.settings.web_password_hash
    assert _choose(page, OURS, current=INSTALLERS).status_code == 302


@pytest.mark.parametrize(
    ("new", "again", "said"),
    [
        ("short one", "short one", "It needs at least 12"),
        (OURS, OURS + " ", "were not the same"),
        ("x" * 201, "x" * 201, "longer than a password needs"),
    ],
)
def test_a_password_that_will_not_do_is_not_saved(page, new, again, said) -> None:
    refused = _choose(page, new, again)
    assert refused.status_code == 400 and said in refused.text
    assert not page.app.settings.web_password_hash


def test_the_log_says_it_changed_and_never_what_to(page, conn) -> None:
    assert _choose(page, OURS).status_code == 302
    line = settings_store.history(conn, limit=1)[0]
    assert line["key"] == "web_password_hash" and line["secret"]
    assert line["old_value"] is None and line["new_value"] is None
    assert "replaced" in page.get("/settings/history").text


def test_setup_asks_to_come_back_and_nowhere_else(page) -> None:
    back = _choose(page, OURS, then="/setup/password")
    assert back.status_code == 302 and back.headers["Location"] == "/setup/password"
    elsewhere = _choose(page, "a different family sentence", current=OURS, then="//evil.example")
    assert elsewhere.headers["Location"] == "/settings"


def test_a_chosen_password_opens_a_public_page_whatever_the_file_says(settings) -> None:
    public = settings.model_copy(
        update={"web_host": "0.0.0.0", "web_password": "short", "web_trust_proxy": True}
    )
    with pytest.raises(Exception, match="5 characters"):
        check_configuration(public)
    check_configuration(
        public.model_copy(update={"web_password_hash": passwords.hash_password(OURS)})
    )


def test_familydb_password_lets_somebody_on_the_server_back_in(settings, conn, monkeypatch) -> None:
    from familydb import cli

    monkeypatch.setattr(cli, "build_app", lambda: App(settings))
    result = CliRunner().invoke(cli.app, ["password"])
    assert result.exit_code == 0, result.output
    fresh = re.search(r"The family password is now: (\S+)", result.output).group(1)
    assert len(fresh) >= passwords.MIN_LENGTH
    with closing(App(settings).connect()) as other:
        stored = settings_store.get(other, "web_password_hash")
    assert passwords.hash_matches(stored, fresh)
