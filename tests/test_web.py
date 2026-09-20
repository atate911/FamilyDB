from datetime import timedelta

import pytest

from familydb.app import App
from familydb.errors import ConfigError
from familydb.web import check_configuration, create_app

PASSWORD = "open sesame"


def _client(settings, clock, **overrides):
    return create_app(App(settings.model_copy(update=overrides), clock)).test_client()


def _signed_in(settings, clock, **overrides):
    client = _client(settings, clock, web_password=PASSWORD, **overrides)
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def test_health_check_needs_no_password(settings, clock) -> None:
    response = _client(settings, clock, web_password=PASSWORD).get("/healthz")
    assert response.status_code == 200 and response.text.strip() == "ok"
    assert response.mimetype == "text/plain"


def test_pages_are_behind_the_password(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    response = client.get("/idea/1")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/idea/1"
    assert client.post("/idea/1").status_code == 401  # a redirect would hide the reason
    page = client.get("/login")
    assert page.status_code == 200 and "Family password" in page.text


def test_signing_in_and_out(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    wrong = client.post("/login", data={"password": "guess"})
    assert wrong.status_code == 401 and "not right" in wrong.text
    good = client.post("/login", data={"password": PASSWORD, "next": "/plans"})
    assert good.status_code == 302 and good.headers["Location"] == "/plans"
    cookie = good.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Secure" not in cookie
    assert client.get("/nope").status_code == 404  # signed in: a real page, not a redirect
    assert client.get("/login").headers["Location"] == "/"  # already in
    assert client.post("/logout").headers["Location"] == "/login"
    assert client.get("/nope").status_code == 302


def test_the_next_parameter_cannot_leave_the_site(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    for target in ("//evil.example/x", "https://evil.example", "javascript:alert(1)"):
        response = client.post("/login", data={"password": PASSWORD, "next": target})
        assert response.headers["Location"] == "/", target
        client.post("/logout")


def test_repeated_failures_lock_the_address_out(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    for _ in range(4):
        assert client.post("/login", data={"password": "no"}).status_code == 401
    locked = client.post("/login", data={"password": "no"})
    assert locked.status_code == 401 and "Too many tries" in locked.text
    still = client.post("/login", data={"password": PASSWORD})
    assert still.status_code == 429  # the right password does not shorten the wait
    clock.advance(timedelta(minutes=16))
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302


def test_a_post_from_another_site_is_refused(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    elsewhere = {"Origin": "https://evil.example"}
    refused = client.post("/login", data={"password": PASSWORD}, headers=elsewhere)
    assert refused.status_code == 400 and "did not come from this page" in refused.text
    client.post("/login", data={"password": PASSWORD})
    client.post("/logout", headers=elsewhere)
    assert client.get("/nope").status_code == 404  # still signed in


def test_every_response_carries_the_security_headers(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    plain = client.get("/login")
    assert "script-src 'none'" in plain.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in plain.headers["Content-Security-Policy"]
    assert plain.headers["X-Content-Type-Options"] == "nosniff"
    assert plain.headers["Referrer-Policy"] == "no-referrer"
    assert plain.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in plain.headers  # plain HTTP: nothing to promise
    secure = client.get("/login", base_url="https://familydb.example")
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=")


def test_a_loopback_page_without_a_password_is_open(settings, clock) -> None:
    client = _client(settings, clock)
    assert client.get("/nope").status_code == 404  # no gate at all
    assert client.get("/login").headers["Location"] == "/"
    assert "Sign out" not in client.get("/nope").text


def test_a_public_page_without_a_password_refuses_to_start(settings, clock) -> None:
    public = settings.model_copy(update={"web_host": "0.0.0.0"})
    with pytest.raises(ConfigError) as info:
        check_configuration(public)
    assert "WEB_PASSWORD" in str(info.value) and "WEB_ALLOW_NO_PASSWORD" in str(info.value)
    check_configuration(public.model_copy(update={"web_password": PASSWORD}))
    check_configuration(public.model_copy(update={"web_allow_no_password": True}))
    assert _client(settings, clock, web_host="0.0.0.0", web_allow_no_password=True) is not None


def test_behind_a_proxy_the_cookie_is_secure_and_the_client_is_the_real_one(settings, clock):
    client = _client(settings, clock, web_password=PASSWORD, web_trust_proxy=True)
    forwarded = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.7"}
    response = client.post("/login", data={"password": PASSWORD}, headers=forwarded)
    assert response.status_code == 302 and "Secure" in response.headers["Set-Cookie"]
    client.post("/logout", headers=forwarded)
    # The lockout counts the forwarded address, so one guesser cannot lock the whole family out.
    for _ in range(5):
        client.post("/login", data={"password": "no"}, headers=forwarded)
    assert client.post("/login", data={"password": PASSWORD}, headers=forwarded).status_code == 429
    other = {**forwarded, "X-Forwarded-For": "203.0.113.8"}
    assert client.post("/login", data={"password": PASSWORD}, headers=other).status_code == 302
