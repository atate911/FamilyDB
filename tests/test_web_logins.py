"""Each person signing in as themselves: the rules, the gate, and the pages that lean on them."""

from __future__ import annotations

import re
from contextlib import closing

import pytest
from typer.testing import CliRunner

from familydb import family as rules
from familydb import passwords
from familydb.app import App
from familydb.store import ideas, logins, members, messages
from familydb.store import settings as settings_store
from familydb.web import check_configuration, create_app
from familydb.web.auth import DEVICE_COOKIE, GLOBAL_ATTEMPTS, MAX_ATTEMPTS
from tests import fakes
from tests.conftest import NOW_ISO

SHARED = "installer-made-password-1"  # what WEB_PASSWORD holds after an install
SAMS = "sam likes long sentences"
ALEXS = "alex chose this one today"


@pytest.fixture
def app(settings, clock, conn, family):
    return App(settings.model_copy(update={"web_password": SHARED}), clock)


def _browser(app, api=None):
    web = create_app(app, api=api)
    client = web.test_client()
    client.chat = web.config["FAMILYDB_CHAT"]
    return client


def _tokens(client, path: str) -> dict[str, str]:
    text = client.get(path).text
    found = {"csrf": re.search(r'name="csrf" value="([^"]+)"', text).group(1)}
    once = re.search(r'name="once" value="([^"]+)"', text)
    if once:
        found["once"] = once.group(1)
    return found


def _as_family(app, api=None):
    browser = _browser(app, api)
    assert browser.post("/login", data={"password": SHARED}).status_code == 302
    return browser


def _as(app, name: str, password: str, api=None):
    browser = _browser(app, api)
    signed_in = browser.post("/login", data={"name": name, "password": password})
    assert signed_in.status_code == 302, signed_in.text
    return browser


def _said(response) -> str:
    return " ".join(re.findall(r'class="said"[^>]*>\s*([^<]+)', response.text))


@pytest.fixture
def sam(app, family):
    """Sam, the admin, has chosen their own password, so everybody signs in as themselves."""
    browser = _as_family(app)
    form = {**_tokens(browser, "/you"), "member": str(family["sam"].id), "new": SAMS, "again": SAMS}
    assert browser.post("/you", data=form).headers["Location"] == "/"
    return browser


def _start(browser, member_id: int) -> str:
    """An admin makes somebody a starting password; their page shows it, once."""
    form = {**_tokens(browser, f"/family/{member_id}"), "action": "start"}
    sent = browser.post(f"/family/{member_id}/password", data=form)
    assert sent.status_code == 302 and sent.headers["Location"] == f"/family/{member_id}"
    page = browser.get(f"/family/{member_id}").text
    return re.search(r'<code class="made">([^<]+)</code>', page).group(1)


@pytest.fixture
def alex(app, sam, family):
    """Alex, a member, signed in with a password of their own, chosen from a starting one."""
    browser = _as(app, "Alex", _start(sam, family["alex"].id))
    form = {**_tokens(browser, "/you"), "new": ALEXS, "again": ALEXS}
    assert browser.post("/you", data=form).headers["Location"] == "/"
    return browser


# -- the rules -----------------------------------------------------------------------------------


def test_a_password_is_kept_hashed_and_apart_from_the_member(conn, family) -> None:
    rules.choose_password(conn, family["alex"].id, ALEXS, now=NOW_ISO)
    stored = logins.get(conn, family["alex"].id)
    assert stored.password_hash.startswith("scrypt$") and ALEXS not in stored.password_hash
    assert passwords.hash_matches(stored.password_hash, ALEXS) and not stored.temporary
    # The member record, which goes as far as the model's prompt, carries none of it.
    assert "password" not in str(members.get(conn, family["alex"].id).model_dump())


def test_kids_and_people_switched_off_are_not_given_one(conn, family) -> None:
    with pytest.raises(rules.FamilyError, match="kids do not sign in"):
        rules.give_starting_password(conn, family["girls"].id, by=None, now=NOW_ISO)
    members.set_active(conn, family["alex"].id, False)
    with pytest.raises(rules.FamilyError, match="switched off"):
        rules.choose_password(conn, family["alex"].id, ALEXS, now=NOW_ISO)
    with pytest.raises(rules.FamilyError, match="at least 12"):
        rules.choose_password(conn, family["sam"].id, "too short", now=NOW_ISO)
    assert logins.by_member(conn) == {}


def test_only_an_admin_is_first_and_only_while_the_family_shares_one(conn, family) -> None:
    with pytest.raises(rules.FamilyError, match="Only an admin"):
        rules.claim(conn, family["alex"].id, ALEXS, now=NOW_ISO)
    assert not logins.admin_can_sign_in(conn)
    rules.claim(conn, family["sam"].id, SAMS, now=NOW_ISO)
    assert logins.admin_can_sign_in(conn)
    pat = rules.add(conn, "Pat", "admin", telegram_id=None, now=NOW_ISO)
    with pytest.raises(rules.FamilyError, match="sign in as themselves now"):
        rules.claim(conn, pat.id, "pat would like it too", now=NOW_ISO)


def test_the_last_admin_who_can_sign_in_is_never_lost(conn, family) -> None:
    rules.claim(conn, family["sam"].id, SAMS, now=NOW_ISO)
    sam = members.get(conn, family["sam"].id)
    pat = rules.add(conn, "Pat", "admin", telegram_id=None, now=NOW_ISO)
    for active, role in ((False, "admin"), (True, "member")):
        with pytest.raises(rules.FamilyError, match="only admin who can sign in"):
            rules.change(
                conn,
                sam.id,
                name="Sam",
                role=role,
                active=active,
                telegram_id="1001",
                seen=rules.revision(sam),
                now=NOW_ISO,
            )
    with pytest.raises(rules.FamilyError, match="only admin who can sign in"):
        rules.remove_login(conn, sam.id)
    # With another admin who can sign in, either may go.
    rules.give_starting_password(conn, pat.id, by=sam.id, now=NOW_ISO)
    assert rules.remove_login(conn, sam.id).id == sam.id
    assert [admin.id for admin in logins.admins_signing_in(conn)] == [pat.id]


# -- signing in ------------------------------------------------------------------------------------


def test_the_first_admin_s_own_password_ends_the_shared_one(app, family) -> None:
    before = _as_family(app)  # somebody else, still signed in with the family password
    claimer = _as_family(app)
    form = {**_tokens(claimer, "/you"), "member": str(family["sam"].id), "new": SAMS, "again": SAMS}
    done = claimer.post("/you", data=form)
    assert done.headers["Location"] == "/"
    home = claimer.get("/")
    assert home.status_code == 200 and "You sign in as Sam from now on" in _said(home)

    # The other browser is signed out, and the way in asks for a name now.
    assert before.get("/ideas").headers["Location"].startswith("/login")
    page = before.get("/login").text
    assert '<label for="name">Your name</label>' in page and "Family password" not in page
    nameless = before.post("/login", data={"password": SHARED})
    assert nameless.status_code == 400 and "Type your name" in nameless.text
    wrong = before.post("/login", data={"name": "Sam", "password": SHARED})
    assert wrong.status_code == 401 and "That name and password do not go together." in wrong.text
    assert _as(app, "  sAM ", SAMS).get("/settings").status_code == 200  # any case or spacing


def test_a_name_that_is_nobody_is_refused_the_same_way_and_as_slowly(app, sam, monkeypatch):
    checked: list[str] = []
    real = passwords.hash_matches
    monkeypatch.setattr(passwords, "hash_matches", lambda s, g: checked.append(s) or real(s, g))
    browser = _browser(app)
    stranger = browser.post("/login", data={"name": "Nobody", "password": SAMS})
    kid = browser.post("/login", data={"name": "the girls", "password": SAMS})
    wrong = browser.post("/login", data={"name": "Sam", "password": "not sam's at all"})
    for answer in (stranger, kid, wrong):
        assert answer.status_code == 401
        assert "That name and password do not go together." in answer.text
    assert len(checked) == 3  # a real scrypt check every time, whether or not the name is anybody


def test_guessing_somebody_s_password_is_locked_out(app, sam) -> None:
    browser = _browser(app)
    for _ in range(MAX_ATTEMPTS):
        browser.post("/login", data={"name": "Sam", "password": "a wrong guess, again"})
    locked = browser.post("/login", data={"name": "Sam", "password": SAMS})
    assert locked.status_code == 429


def test_a_browser_that_signed_in_as_somebody_is_not_kept_out_by_strangers(app, sam) -> None:
    web = create_app(app)  # one page, so one table of failures, however many browsers
    known = web.test_client()
    assert known.post("/login", data={"name": "Sam", "password": SAMS}).status_code == 302
    assert known.get_cookie(DEVICE_COOKIE) is not None
    known.post("/logout")
    lockout, now = web.config["FAMILYDB_LOCKOUT"], app.clock.now()
    for number in range(GLOBAL_ATTEMPTS):
        lockout.failed(f"203.0.113.{number}", now)  # guesses from everywhere at once
    stranger = web.test_client().post("/login", data={"name": "Sam", "password": SAMS})
    assert stranger.status_code == 429
    assert known.post("/login", data={"name": "Sam", "password": SAMS}).status_code == 302


# -- starting passwords ----------------------------------------------------------------------------


def test_a_starting_password_is_shown_once_and_must_be_replaced(app, sam, family) -> None:
    made = _start(sam, family["alex"].id)
    assert len(made) == passwords.STARTING_LENGTH
    again = sam.get(f"/family/{family['alex'].id}").text
    assert made not in again and "Has a starting password they have not used yet." in again

    alex = _browser(app)
    signed_in = alex.post("/login", data={"name": "Alex", "password": made, "next": "/ideas"})
    assert signed_in.headers["Location"] == "/you"  # a starting password is for choosing with
    assert alex.get("/ideas").headers["Location"] == "/you"
    assert "Choose your own password" in alex.get("/you").text
    assert alex.post("/chat", data={"text": "hello"}).status_code == 403

    form = {**_tokens(alex, "/you"), "new": ALEXS, "again": ALEXS}  # no current one to type
    assert alex.post("/you", data=form).headers["Location"] == "/"
    assert alex.get("/ideas").status_code == 200
    assert _browser(app).post("/login", data={"name": "Alex", "password": made}).status_code == 401
    assert "Signs in with a password of their own." in sam.get(f"/family/{family['alex'].id}").text


def test_an_admin_does_not_give_themselves_one_nor_a_kid(app, sam, family) -> None:
    for member_id, said in ((family["sam"].id, "That is you"), (family["girls"].id, "kids do")):
        form = {**_tokens(sam, f"/family/{member_id}"), "action": "start"}
        sam.post(f"/family/{member_id}/password", data=form)
        assert said in _said(sam.get(f"/family/{member_id}"))
    with closing(app.connect()) as conn:
        assert set(logins.by_member(conn)) == {family["sam"].id}


def test_while_the_family_shares_a_password_nobody_is_given_one(app, family) -> None:
    browser = _as_family(app)
    page = browser.get(f"/family/{family['alex'].id}").text
    assert "Choose your own password first" in page and "Make a starting password" not in page
    form = {**_tokens(browser, f"/family/{family['alex'].id}"), "action": "start"}
    browser.post(f"/family/{family['alex'].id}/password", data=form)
    with closing(app.connect()) as conn:
        assert logins.by_member(conn) == {}


def test_a_new_starting_password_or_taking_it_away_signs_them_out(app, sam, alex, family) -> None:
    _start(sam, family["alex"].id)
    assert alex.get("/ideas").headers["Location"].startswith("/login")

    again = _as(app, "Alex", _start(sam, family["alex"].id))
    form = {**_tokens(sam, f"/family/{family['alex'].id}"), "action": "remove"}
    sam.post(f"/family/{family['alex'].id}/password", data=form)
    assert "can no longer sign in" in _said(sam.get(f"/family/{family['alex'].id}"))
    assert again.get("/ideas").headers["Location"].startswith("/login")


def test_switching_somebody_off_or_making_them_a_kid_signs_them_out(app, sam, family) -> None:
    for update in ({"active": False}, {"role": "kid"}):
        with closing(app.connect()) as conn:
            rules.change(
                conn,
                family["alex"].id,
                **{
                    "name": "Alex",
                    "role": "member",
                    "active": True,
                    "telegram_id": "1002",
                    "seen": rules.revision(members.get(conn, family["alex"].id)),
                    "now": NOW_ISO,
                },
            )
            made = rules.give_starting_password(
                conn, family["alex"].id, by=family["sam"].id, now=NOW_ISO
            )
        alex = _as(app, "Alex", made)
        with closing(app.connect()) as conn:
            current = members.get(conn, family["alex"].id)
            rules.change(
                conn,
                current.id,
                name="Alex",
                role=update.get("role", "member"),
                active=update.get("active", True),
                telegram_id="1002",
                seen=rules.revision(current),
                now=NOW_ISO,
            )
        assert alex.get("/you").headers["Location"].startswith("/login")
        refused = _browser(app).post("/login", data={"name": "Alex", "password": made})
        assert refused.status_code == 401


# -- what each person may reach --------------------------------------------------------------------


def test_a_member_uses_the_bot_and_an_admin_looks_after_it(app, sam, alex, family) -> None:
    for path in ("/", "/chat", "/ideas", "/ideas/new", "/plans", "/tasks", "/status", "/you"):
        assert alex.get(path).status_code == 200, path
    for path in ("/settings", "/settings/personality", "/family", "/family/1", "/setup"):
        refused = alex.get(path)
        assert refused.status_code == 403 and "For an admin" in refused.text, path
    assert alex.post("/settings", data=_tokens(alex, "/you")).status_code == 403
    nav = alex.get("/").text
    assert 'href="/settings"' not in nav and 'href="/family"' not in nav
    assert 'href="/you"' in nav and "Alex" in nav
    admin_nav = sam.get("/").text
    assert 'href="/settings"' in admin_nav and 'href="/family"' in admin_nav


def test_the_chat_speaks_as_whoever_is_signed_in(app, sam, family, conn) -> None:
    replies = [fakes.message([fakes.text("Saturday looks dry.")])]
    with closing(app.connect()) as other:
        made = rules.give_starting_password(other, family["alex"].id, by=None, now=NOW_ISO)
        rules.choose_password(other, family["alex"].id, ALEXS, now=NOW_ISO)
    assert made  # replaced straight away
    alex = _as(app, "Alex", ALEXS, api=fakes.FakeMessagesAPI(*replies))
    page = alex.get("/chat").text
    assert "From <strong>Alex</strong>" in page and 'name="who"' not in page
    form = {**_tokens(alex, "/chat"), "text": "what should we do?", "who": "Sam"}
    assert alex.post("/chat", data=form).status_code == 302
    assert alex.chat.wait(10)
    asked = messages.last_for_chat(conn, "web", limit=5)[0]
    assert asked.member_id == family["alex"].id  # not whoever the form claimed


def test_a_form_records_whoever_is_signed_in(app, alex, family, conn) -> None:
    form = {**_tokens(alex, "/ideas/new"), "title": "Ramen place", "kind": "restaurant"}
    assert 'name="who"' not in alex.get("/ideas/new").text
    sent = alex.post("/ideas/new", data={**form, "who": "Sam"})
    assert sent.status_code == 302
    assert ideas.get(conn, 1).suggested_by_name == "Alex"


# -- your own password, and the settings page ------------------------------------------------------


def test_changing_your_password_needs_the_one_in_use_and_keeps_this_browser(app, sam) -> None:
    elsewhere = _as(app, "Sam", SAMS)
    new = "sam changed it on purpose"
    form = {**_tokens(sam, "/you"), "new": new, "again": new}
    missing = sam.post("/you", data=form)
    assert missing.status_code == 401 and "Type the password you use now" in missing.text
    wrong = sam.post("/you", data={**form, **_tokens(sam, "/you"), "current": "not it at all"})
    assert wrong.status_code == 401 and "That password is not right." in wrong.text
    done = sam.post("/you", data={**form, **_tokens(sam, "/you"), "current": SAMS})
    assert done.headers["Location"] == "/"
    assert sam.get("/settings").status_code == 200  # still signed in here
    assert elsewhere.get("/settings").headers["Location"].startswith("/login")  # not there
    assert _browser(app).post("/login", data={"name": "Sam", "password": new}).status_code == 302


def test_showing_a_key_and_signing_everyone_out_ask_for_your_own(app, sam) -> None:
    page = sam.get("/settings").text
    assert '<label for="reveal-password">Your password</label>' in page
    assert "Everybody signs in as themselves" in page and "New family password" not in page
    form = {**_tokens(sam, "/settings"), "key": "anthropic_api_key"}
    assert sam.post("/settings/reveal", data={**form, "password": SHARED}).status_code == 401
    shown = sam.post("/settings/reveal", data={**form, "password": SAMS})
    assert shown.status_code == 200 and "test-key" in shown.text
    family_one = {**_tokens(sam, "/settings"), "new": "a family one again", "again": "x"}
    assert sam.post("/settings/password", data=family_one).status_code == 409


def test_the_settings_history_says_who_changed_what(app, sam, conn) -> None:
    form = {**_tokens(sam, "/settings"), "web_title": "The Hendersons"}
    sam.post("/settings", data=form)
    [latest] = settings_store.history(conn, limit=1)
    assert latest["key"] == "web_title" and latest["changed_by_name"] == "Sam"


def test_the_family_page_says_who_signs_in(app, sam, alex, family) -> None:
    page = sam.get("/family").text
    assert page.count('<span class="tag">signs in</span>') == 2  # Sam and Alex, not the girls


def test_a_stale_family_session_cannot_take_an_admin_afterwards(app, family) -> None:
    late = _as_family(app)
    form = {**_tokens(late, "/you"), "member": str(family["sam"].id), "new": SAMS, "again": SAMS}
    with closing(app.connect()) as conn:
        rules.claim(conn, family["sam"].id, "somebody got there first", now=NOW_ISO)
    assert late.post("/you", data=form).status_code == 401  # signed out before it is looked at


# -- starting up, and the server -----------------------------------------------------------------


def test_a_page_where_people_sign_in_as_themselves_needs_no_shared_password(settings, conn, family):
    public = settings.model_copy(update={"web_host": "0.0.0.0", "web_trust_proxy": True})
    with pytest.raises(Exception, match="WEB_PASSWORD is empty"):
        check_configuration(public)
    check_configuration(public, own_passwords=True)
    rules.claim(conn, family["sam"].id, SAMS, now=NOW_ISO)
    create_app(App(public))  # starts: everybody signs in with their own


def test_familydb_password_lets_the_admin_back_in(settings, conn, family, monkeypatch) -> None:
    from familydb import cli

    rules.claim(conn, family["sam"].id, SAMS, now=NOW_ISO)
    monkeypatch.setattr(cli, "build_app", lambda: App(settings))
    result = CliRunner().invoke(cli.app, ["password"])
    assert result.exit_code == 0, result.output
    made = re.search(r"Sam's password is now: (\S+)", result.output).group(1)
    stored = logins.get(conn, family["sam"].id)
    assert stored.temporary and passwords.hash_matches(stored.password_hash, made)

    named = CliRunner().invoke(cli.app, ["password", "alex"])
    assert named.exit_code == 0 and "Alex's password is now:" in named.output
    kid = CliRunner().invoke(cli.app, ["password", "the girls"])
    assert kid.exit_code != 0 and "kids do not sign in" in kid.output


def test_familydb_password_for_a_member_waits_for_an_admin(settings, conn, family, monkeypatch):
    from familydb import cli

    monkeypatch.setattr(cli, "build_app", lambda: App(settings))
    refused = CliRunner().invoke(cli.app, ["password", "Alex"])
    assert refused.exit_code != 0 and "must be an admin" in refused.output
    assert logins.by_member(conn) == {}
