"""Each person signing in as themselves: the rules, the gate, and the pages that lean on them."""

from __future__ import annotations

import re
from contextlib import closing

import pytest
from typer.testing import CliRunner

from familydb import family as rules
from familydb import passwords, roles
from familydb.app import App
from familydb.store import db, ideas, logins, members, messages, plans, tasks
from familydb.store import settings as settings_store
from familydb.web import check_configuration, create_app, fields
from familydb.web.auth import DEVICE_COOKIE, GLOBAL_ATTEMPTS, MAX_ATTEMPTS
from tests import fakes
from tests.conftest import NOW_ISO

SHARED = "installer-made-password-1"  # what WEB_PASSWORD holds after an install
SAMS = "sam likes long sentences"
ALEXS = "alex chose this one today"
KIDS = "a kid can choose one too"


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
    """What the last form said: the older pages' line, or the new frame's flash."""
    return " ".join(re.findall(r'class="(?:said|banner__text)"[^>]*>\s*([^<]+)', response.text))


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
    return re.search(r'<code class="code made__pw">([^<]+)</code>', page).group(1)


@pytest.fixture
def alex(app, sam, family):
    """Alex, a member, signed in with a password of their own, chosen from a starting one."""
    browser = _as(app, "Alex", _start(sam, family["alex"].id))
    form = {**_tokens(browser, "/you"), "new": ALEXS, "again": ALEXS}
    assert browser.post("/you", data=form).headers["Location"] == "/"
    return browser


# -- the rules


def test_a_password_is_kept_hashed_and_apart_from_the_member(conn, family) -> None:
    rules.choose_password(conn, family["alex"].id, ALEXS, now=NOW_ISO)
    stored = logins.get(conn, family["alex"].id)
    assert stored.password_hash.startswith("scrypt$") and ALEXS not in stored.password_hash
    assert passwords.hash_matches(stored.password_hash, ALEXS) and not stored.temporary
    # The member record, which goes as far as the model's prompt, carries none of it.
    assert "password" not in str(members.get(conn, family["alex"].id).model_dump())


def test_nobody_switched_off_is_given_one_and_kids_are_for_now(conn, family) -> None:
    # A kid signs in as herself (roles.py), so she is given a password as anybody is.
    made = rules.give_starting_password(conn, family["girls"].id, by=None, now=NOW_ISO)
    assert passwords.hash_matches(logins.get(conn, family["girls"].id).password_hash, made)
    members.set_active(conn, family["alex"].id, False)
    with pytest.raises(rules.FamilyError, match="switched off"):
        rules.choose_password(conn, family["alex"].id, ALEXS, now=NOW_ISO)
    with pytest.raises(rules.FamilyError, match="at least 12"):
        rules.choose_password(conn, family["sam"].id, "too short", now=NOW_ISO)
    assert set(logins.by_member(conn)) == {family["girls"].id}


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
    for active, role in ((False, "admin"), (True, "parent")):
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


# -- signing in


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
    assert re.search(r'<label[^>]*for="name">Your name</label>', page)
    assert "Family password" not in page
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


# -- starting passwords


def test_a_starting_password_is_shown_once_and_must_be_replaced(app, sam, family) -> None:
    made = _start(sam, family["alex"].id)
    assert len(made) == passwords.STARTING_LENGTH
    again = sam.get(f"/family/{family['alex'].id}").text
    assert made not in again and "Has a starting password they haven\u2019t used yet." in again

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


def test_an_admin_does_not_give_themselves_one(app, sam, family) -> None:
    form = {**_tokens(sam, f"/family/{family['sam'].id}"), "action": "start"}
    sam.post(f"/family/{family['sam'].id}/password", data=form)
    assert "That is you" in _said(sam.get(f"/family/{family['sam'].id}"))
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


def _rewrite(app, member_id: int, **changes) -> None:
    """Change somebody the way the Family page would."""
    with closing(app.connect()) as conn:
        current = members.get(conn, member_id)
        rules.change(
            conn,
            member_id,
            name=changes.get("name", current.display_name),
            role=changes.get("role", current.role),
            active=changes.get("active", current.active),
            telegram_id=current.channel_user_id,
            seen=rules.revision(current),
            now=NOW_ISO,
        )


def test_switching_somebody_off_signs_them_out(app, sam, alex, family) -> None:
    _rewrite(app, family["alex"].id, active=False)
    assert alex.get("/you").headers["Location"].startswith("/login")
    refused = _browser(app).post("/login", data={"name": "Alex", "password": ALEXS})
    assert refused.status_code == 401


def test_a_parent_made_a_kid_stays_signed_in_and_reads_the_ideas(
    app, sam, alex, family, monkeypatch
) -> None:
    _rewrite(app, family["alex"].id, role="kid")
    assert alex.get("/ideas").status_code == 200  # a kid reads the ideas
    # Were kids ever to lose signing in, the table in roles.py is all it would take.
    monkeypatch.setitem(roles.PERMISSIONS, "kid", frozenset())
    assert alex.get("/ideas").headers["Location"].startswith("/login")
    refused = _browser(app).post("/login", data={"name": "Alex", "password": ALEXS})
    assert refused.status_code == 401


# -- what each person may reach


def test_a_member_uses_the_bot_and_an_admin_looks_after_it(app, sam, alex, family) -> None:
    for path in ("/", "/chat", "/ideas", "/ideas/new", "/plans", "/tasks", "/status", "/you"):
        assert alex.get(path).status_code == 200, path
    every_settings_page = [f"/settings/{section.name}" for section in fields.SECTIONS]
    for path in ("/settings", *every_settings_page, "/family", "/family/1", "/setup"):
        refused = alex.get(path)
        assert refused.status_code == 403 and "For an admin" in refused.text, path
        assert (
            "Sam is the admin in this family." in refused.text and 'href="/status"' in refused.text
        )
    assert alex.post("/settings", data=_tokens(alex, "/you")).status_code == 403
    # Who she is is an admin's to change, the form as much as the page.
    for path in ("/settings/personality", "/settings/personality/restore"):
        form = {**_tokens(alex, "/you"), "persona": "none", "persona_name": "X"}
        sent = alex.post(path, data=form)
        assert sent.status_code == 403, path
    assert app.settings.persona == "default" and app.settings.persona_name == ""
    nav = alex.get("/").text
    assert 'href="/settings"' not in nav and 'href="/family"' not in nav
    assert 'href="/you"' in nav and "Alex" in nav
    admin_nav = sam.get("/").text
    assert 'href="/settings"' in admin_nav and 'href="/family"' in admin_nav


def test_every_settings_page_is_beside_its_page_and_the_account_corner_holds_the_rest(
    app, sam, alex
) -> None:
    """Settings lists each of its pages beside the one you are on; the account corner of the sidebar
    holds Look, Your password and Sign out, and an admin's menu is the only one with Settings."""
    here = sam.get("/settings/spending").text
    nav = re.search(r'<nav class="settings-nav".*?</nav>', here, re.S)
    assert nav is not None
    links = re.findall(r'<a[^>]* href="([^"]+)"', nav.group(0))
    assert links == [f"/settings/{section.name}" for section in fields.SECTIONS]
    assert re.search(r'href="/settings/spending" aria-current="page"', here)  # beside its page
    assert re.search(r'href="/settings" aria-current="page"', here)  # and Settings in the sidebar

    # On the new frame the same things sit in the account corner of the sidebar.
    side = re.search(r'<aside class="side".*?</aside>', alex.get("/").text, re.S)
    assert side is not None and "/settings" not in side.group(0)
    theirs = side.group(0).split('<div class="me">')[1]
    assert re.findall(r'<a[^>]* href="([^"]+)"', theirs) == ["/look", "/you"]
    assert "<b>Alex</b>" in theirs and 'action="/logout"' in theirs


def test_the_chat_speaks_as_whoever_is_signed_in(app, sam, family, conn) -> None:
    replies = [fakes.message([fakes.text("Saturday looks dry.")])]
    with closing(app.connect()) as other:
        made = rules.give_starting_password(other, family["alex"].id, by=None, now=NOW_ISO)
        rules.choose_password(other, family["alex"].id, ALEXS, now=NOW_ISO)
    assert made  # replaced straight away
    alex = _as(app, "Alex", ALEXS, api=fakes.FakeMessagesAPI(*replies))
    page = alex.get("/chat").text
    assert "Writing as <b>Alex</b>" in page and 'name="who"' not in page
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


# -- your own password, and the settings page


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
    page = sam.get("/settings/security").text
    assert re.search(r'<label[^>]*for="reveal-password">Your password</label>', page)
    assert "Everybody signs in as themselves" in page and "New family password" not in page
    form = {**_tokens(sam, "/settings/security"), "key": "anthropic_api_key"}
    assert sam.post("/settings/reveal", data={**form, "password": SHARED}).status_code == 401
    shown = sam.post("/settings/reveal", data={**form, "password": SAMS})
    assert shown.status_code == 200 and "test-key" in shown.text
    family_one = {**_tokens(sam, "/settings/security"), "new": "a family one again", "again": "x"}
    assert sam.post("/settings/password", data=family_one).status_code == 409


def test_the_settings_history_says_who_changed_what(app, sam, conn) -> None:
    form = {**_tokens(sam, "/settings/general"), "web_title": "The Hendersons"}
    sam.post("/settings", data=form)
    [latest] = settings_store.history(conn, limit=1)
    assert latest["key"] == "web_title" and latest["changed_by_name"] == "Sam"


def test_a_stale_family_session_cannot_take_an_admin_afterwards(app, family) -> None:
    late = _as_family(app)
    form = {**_tokens(late, "/you"), "member": str(family["sam"].id), "new": SAMS, "again": SAMS}
    with closing(app.connect()) as conn:
        rules.claim(conn, family["sam"].id, "somebody got there first", now=NOW_ISO)
    assert late.post("/you", data=form).status_code == 401  # signed out before it is looked at


# -- starting up, and the server


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
    kid = CliRunner().invoke(cli.app, ["password", "the girls"])  # as a parent may, for now
    assert kid.exit_code == 0 and "the girls's password is now:" in kid.output


def test_familydb_password_for_a_member_waits_for_an_admin(settings, conn, family, monkeypatch):
    from familydb import cli

    monkeypatch.setattr(cli, "build_app", lambda: App(settings))
    refused = CliRunner().invoke(cli.app, ["password", "Alex"])
    assert refused.exit_code != 0 and "must be an admin" in refused.output
    assert logins.by_member(conn) == {}


# -- the three roles


def test_three_roles_and_what_a_kid_may_do() -> None:
    assert roles.ROLES == ("admin", "parent", "kid")
    assert roles.PERMISSIONS["admin"] > roles.PERMISSIONS["parent"] > roles.PERMISSIONS["kid"]
    assert roles.PERMISSIONS["admin"] - roles.PERMISSIONS["parent"] == {"manage"}
    # A kid reads, talks to the bot, keeps her own wishes and ticks off her own things to do; she
    # changes nothing else, sees none of the household's pages, and answers nobody's wishes.
    assert roles.PERMISSIONS["kid"] == {"sign_in", "chat", "wish", "own_tasks"}
    assert roles.may("parent", "chat") and not roles.may("parent", "manage")
    assert not roles.may("member", "sign_in")  # a role that is not one of the three may do nothing


def test_a_kid_signs_in_reads_and_talks_but_changes_nothing(app, sam, family) -> None:
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    form = {**_tokens(girls, "/you"), "new": KIDS, "again": KIDS}
    assert girls.post("/you", data=form).headers["Location"] == "/"
    for path in ("/", "/chat", "/ideas", "/plans", "/tasks"):
        assert girls.get(path).status_code == 200, path
    for path in ("/ideas/new", "/status", "/memory"):
        assert girls.get(path).status_code == 403, path
    assert "For a parent" in girls.get("/status").text
    refused = girls.get("/settings")
    assert refused.status_code == 403 and "This part is for grown-ups" in refused.text
    assert "ask Sam if something here needs to change" in refused.text
    nav = girls.get("/").text
    assert 'href="/status"' not in nav and 'href="/memory"' not in nav
    assert "Add an idea" not in girls.get("/ideas").text
    assert '<span class="tag tag--ok">Signs in</span>' in sam.get("/family").text


def test_a_permission_taken_from_kids_is_kept_everywhere(app, sam, family, monkeypatch) -> None:
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    form = {**_tokens(girls, "/you"), "new": KIDS, "again": KIDS}
    girls.post("/you", data=form)
    monkeypatch.setitem(roles.PERMISSIONS, "kid", frozenset({"sign_in"}))
    home = girls.get("/")
    assert home.status_code == 200 and 'href="/chat#latest"' not in home.text
    chat = girls.get("/chat")
    assert chat.status_code == 403 and "Not yet" in chat.text
    assert "Talking to Vera here" in chat.text  # her place goes by her name, as its tab does
    idea = {**_tokens(girls, "/you"), "title": "Ramen place", "kind": "restaurant"}
    assert girls.post("/ideas/new", data=idea).status_code == 403
    assert girls.get("/ideas").status_code == 200  # reading needs nothing more than signing in
    with closing(app.connect()) as conn:
        assert ideas.list_all(conn) == []


def test_home_offers_only_what_a_role_may_do(app, sam, family, monkeypatch) -> None:
    """Home's box, its ways to start and how the conversation stands are the chat's, and a tick
    is a change: a role without those is shown the rest of Home and no way into a refusal."""
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    with closing(app.connect()) as conn, db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="u1",
            chat_id="web",
            member_id=family["sam"].id,
            text="anything on tonight?",
            now=NOW_ISO,
        )
        messages.mark_processed(conn, asked.id, [], now=NOW_ISO)
        messages.insert_out(
            conn,
            channel="web",
            chat_id="web",
            text="The park is free.",
            reply_to=asked.id,
            now=NOW_ISO,
        )
        towels = tasks.insert(
            conn,
            title="Buy paper towels",
            notes="",
            owner_id=family["girls"].id,
            due_at=None,
            preferred_window="",
            operation_key="test-towels",
            channel="web",
            chat_id="web",
            now=NOW_ISO,
        )
    home = girls.get("/").text  # a kid talks to the bot but changes nothing
    # Her Home is her own conversation, never the family's.
    assert 'action="/chat"' in home and "The park is free." not in home
    with closing(app.connect()) as conn, db.transaction(conn):
        mine = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="u2",
            chat_id=f"member:{family['girls'].id}",
            member_id=family["girls"].id,
            text="can we go to the park?",
            now=NOW_ISO,
        )
        messages.mark_processed(conn, mine.id, [], now=NOW_ISO)
        messages.insert_out(
            conn,
            channel="web",
            chat_id=f"member:{family['girls'].id}",
            text="The swings are waiting.",
            reply_to=mine.id,
            now=NOW_ISO,
        )
    home = girls.get("/").text
    assert "The swings are waiting." in home and "The park is free." not in home
    # Her own things to do she ticks off herself (roles.py `own_tasks`).
    assert "Buy paper towels" in home and f'action="/task/{towels}/done"' in home

    monkeypatch.setitem(roles.PERMISSIONS, "kid", frozenset({"sign_in"}))
    home = girls.get("/")
    assert home.status_code == 200
    assert "/chat" not in home.text  # no box, no ways to start, no way into the conversation
    assert "The swings are waiting." not in home.text and "ask.js" not in home.text
    assert '<h1 class="sr">' in home.text  # a heading still, with the box's label gone
    assert "Buy paper towels" in home.text and "/done" not in home.text
    listed = girls.get("/tasks").text
    assert "Buy paper towels" in listed and f"/task/{towels}/done" not in listed
    tick = {**_tokens(girls, "/you"), "revision": "1"}
    assert girls.post(f"/task/{towels}/done", data=tick).status_code == 403
    with closing(app.connect()) as conn:
        assert tasks.get(conn, towels).status == "open"


def test_a_kid_is_never_shown_a_present_or_its_plan(app, sam, family) -> None:
    """Presents are kept from anybody who may not decide what the kids are given (WISHES.md)."""
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    with closing(app.connect()) as conn, db.transaction(conn):
        gift = ideas.insert(conn, title="Roller skates", kind="gift", now=NOW_ISO)
        ideas.insert(conn, title="Zoo lights", kind="outing", now=NOW_ISO)
        plans.insert(
            conn,
            title="Pick up the skates",
            start="2026-09-28T10:00:00Z",
            end=None,
            all_day=False,
            idea_id=gift.id,
        )
    for path in ("/", "/ideas", "/ideas?kind=gift", "/plans", "/plans/month"):
        page = girls.get(path).text
        assert "Roller skates" not in page and "Pick up the skates" not in page, path
    assert "Zoo lights" in girls.get("/ideas").text
    assert girls.get(f"/idea/{gift.id}").status_code == 404
    assert "Roller skates" in sam.get("/ideas").text
    assert "Pick up the skates" in sam.get("/plans").text
    assert sam.get(f"/idea/{gift.id}").status_code == 200


def test_a_kid_talks_to_the_bot_on_her_own_and_a_parent_reads_along(app, sam, family) -> None:
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    with closing(app.connect()) as conn, db.transaction(conn):
        for chat_id, who, text in (
            ("web", family["sam"].id, "the grown-ups plans"),
            (f"member:{family['girls'].id}", family["girls"].id, "I want a hamster"),
        ):
            said = messages.insert_in(
                conn,
                channel="web",
                channel_update_id=chat_id,
                chat_id=chat_id,
                member_id=who,
                text=text,
                now=NOW_ISO,
            )
            messages.mark_processed(conn, said.id, [], now=NOW_ISO)
    hers = girls.get("/chat").text
    assert "I want a hamster" in hers and "the grown-ups plans" not in hers
    assert "Just you and Vera" in hers
    # She may read nobody else's, not even by asking for it.
    assert girls.get(f"/chat?with={family['girls'].id}").status_code == 404
    shared = sam.get("/chat").text
    assert "the grown-ups plans" in shared and "I want a hamster" not in shared
    assert f'href="/chat?with={family["girls"].id}#latest"' in shared
    read = sam.get(f"/chat?with={family['girls'].id}").text
    assert "I want a hamster" in read and 'action="/chat"' not in read  # read, not written
    assert sam.get(f"/chat?with={family['sam'].id}").status_code == 404  # only a kid's


# What a kid is never shown: how the bot works, or what is wrong with it.
MACHINERY = re.compile(
    r"Version v|Google Calendar|Times use|Waiting for delivery|Telegram chat|restart|retry job|"
    r"settings page|How it was looked up|worker:|error:",
    re.IGNORECASE,
)


def _words(page: str) -> str:
    """What a page says, without its markup, scripts or styles."""
    return re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S))


def test_a_kid_is_never_shown_how_it_works(app, sam, family) -> None:
    """No calendar notes, lookup errors, reminder delivery, time zone or version for a kid; the
    grown-ups still see them all."""
    girls_id = family["girls"].id
    with closing(app.connect()) as conn, db.transaction(conn):
        idea = ideas.insert(conn, title="Ramen place", kind="restaurant", now=NOW_ISO)
        failed = {"enrichment": "failed", "enrichment_note": "worker: the web search tool is off"}
        ideas.update(conn, idea.id, failed, now=NOW_ISO)
        task_id = tasks.insert(
            conn,
            title="Pack the swim bag",
            notes="",
            owner_id=girls_id,
            due_at=None,
            preferred_window="",
            operation_key="swim",
            channel="telegram",
            chat_id="-100",
            now=NOW_ISO,
        )
        tasks.add_reminder(conn, task_id, "2026-09-26T16:00:00Z")
    girls = _as(app, "the girls", _start(sam, girls_id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    pages = ("/", "/chat", "/ideas", f"/idea/{idea.id}", "/plans", "/plans/month", "/tasks")
    for path in (*pages, "/wishes", "/you"):
        page = girls.get(path)
        assert page.status_code == 200, path
        shown = MACHINERY.findall(_words(page.text))
        assert not shown, (path, shown)
    assert "Pack the swim bag" in girls.get("/tasks").text  # her own things to do, all the same
    grown_up = " ".join(_words(sam.get(path).text) for path in pages)
    for said in ("Version v", "Google Calendar", "Times use", "worker:", "Scheduled"):
        assert said in grown_up, said


def test_the_health_pill_and_status_follow_what_is_wrong(app, sam, family, alex):
    """Quiet while all is well, "needs a look" while something only an admin can fix goes on, and
    "can't answer" while nobody can be answered: the pill and the page say the same. Status is for
    every grown-up, a parent included, and a kid has neither."""
    from familydb.store import alerts as alert_store
    from familydb.web import status as status_page

    def note(kind: str) -> None:
        with closing(app.connect()) as conn, db.transaction(conn):
            alert_store.note(conn, kind, "", "test", now=NOW_ISO, keep_after="2026-01-01T00:00:00Z")

    def pill(browser) -> str:
        found = re.search(
            r'<a class="pill-health[^"]*"[^>]*>.*?</a>', browser.get("/status").text, re.S
        )
        return re.sub(r"<[^>]+>", " ", found.group(0)) if found else ""

    assert "is ready" in pill(sam) and 'id="attention"' not in sam.get("/status").text
    note("price")  # news, not trouble: the pill stays quiet
    assert "is ready" in pill(sam)
    note("calendar")
    assert "is ready" in pill(sam) and 'id="attention"' in sam.get("/status").text
    note("key")
    assert "can\u2019t answer right now" in pill(sam)
    assert "can\u2019t answer right now" in sam.get("/status").text
    assert "can\u2019t answer right now" in pill(
        alex
    )  # a parent reads the same, and cannot change it
    assert alex.get("/status").status_code == 200
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    refused = girls.get("/status")
    assert refused.status_code == 403 and "pill-health" not in refused.text
    with closing(app.connect()) as conn:
        assert status_page.light(app, conn) == "bad"


# -- plans and to-dos, as each person sees them


def _swim_bag(conn, family) -> int:
    with db.transaction(conn):
        return tasks.insert(
            conn,
            title="Pack the swim bag",
            notes="",
            owner_id=family["girls"].id,
            due_at=None,
            preferred_window="",
            operation_key="swim-bag",
            channel="telegram",
            chat_id="-100",
            now=NOW_ISO,
        )


def test_plans_open_as_a_month_for_a_grown_up_and_a_list_for_a_kid(app, sam, family) -> None:
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    assert "How to show the plans" in sam.get("/plans").text
    page = girls.get("/plans").text
    assert "How to show the plans" not in page and "What the family is doing next." in page


def test_a_kid_cannot_open_the_edit_page(app, sam, family, conn) -> None:
    task_id = _swim_bag(conn, family)
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    assert girls.get(f"/task/{task_id}/edit").status_code == 403
    assert f"/task/{task_id}/edit" not in girls.get("/tasks").text


def test_a_kid_is_told_who_set_her_a_to_do_but_not_what_she_set_herself(
    app,
    sam,
    family,
    conn,
) -> None:
    form = {**_tokens(sam, "/tasks"), "title": "Pack the swim bag", "owner": "the girls"}
    assert sam.post("/tasks/new", data=form).status_code == 302
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    girls.post("/you", data={**_tokens(girls, "/you"), "new": KIDS, "again": KIDS})
    page = girls.get("/tasks").text
    assert "Pack the swim bag" in page and "Set by Sam" in page
    assert "Set by" not in sam.get("/tasks").text  # Sam set it, and reads their own list
    with db.transaction(conn):
        conn.execute("UPDATE tasks SET created_by_member_id = ?", (family["girls"].id,))
    assert "Set by" not in girls.get("/tasks").text


def _kid_signed_in(app, sam, member):
    kid = _as(app, member.display_name, _start(sam, member.id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    return kid


def _two_kids_and_a_present(app, sam, conn):
    from familydb.store import ideas as idea_store
    from familydb.store import members as member_store

    with db.transaction(conn):
        maya = member_store.add(conn, "Maya", "kid", now=NOW_ISO)
        theo = member_store.add(conn, "Theo", "kid", now=NOW_ISO)
        lego = idea_store.insert(
            conn, title="Lego set", kind="gift", participants=["Theo"], now=NOW_ISO
        )
    return maya, theo, lego


def test_a_kid_sees_no_present_anywhere_and_a_grown_up_is_told_whom_it_is_kept_from(
    app, sam, family, conn
) -> None:
    maya, theo, lego = _two_kids_and_a_present(app, sam, conn)
    mayas, theos = _kid_signed_in(app, sam, maya), _kid_signed_in(app, sam, theo)
    for kid in (mayas, theos):  # his, hers or anyone's: a kid is kept from every present
        assert "Lego set" not in kid.get("/ideas").text
        assert kid.get(f"/idea/{lego.id}").status_code == 404
        for path in ("/", "/plans", "/restaurants", "/tasks"):
            assert "Lego set" not in kid.get(path).text, path
    assert "hidden from the kids" in sam.get("/ideas").text.lower()
    assert "Lego set" in sam.get("/").text


def test_a_grown_up_can_have_a_present_kept_from_them_too(app, sam, alex, family, conn) -> None:
    from familydb.store import ideas as idea_store

    with db.transaction(conn):
        scarf = idea_store.insert(
            conn, title="Silk scarf", kind="gift", participants=["Alex"], now=NOW_ISO
        )
    assert "Silk scarf" in sam.get("/ideas").text
    assert "Silk scarf" not in alex.get("/ideas").text
    assert alex.get(f"/idea/{scarf.id}").status_code == 404
    assert alex.get(f"/idea/{scarf.id}/edit").status_code == 404


def test_the_idea_form_chooses_which_grown_ups_a_present_is_kept_from(
    app, sam, alex, family, conn
) -> None:
    from familydb.store import ideas as idea_store

    maya, theo, lego = _two_kids_and_a_present(app, sam, conn)
    page = sam.get(f"/idea/{lego.id}/edit").text
    assert f'name="hidden_from" value="{family["alex"].id}"' in page  # a grown-up can be chosen
    assert f'name="hidden_from" value="{theo.id}"' not in page  # kids are kept from by role
    form = {
        **_tokens(sam, f"/idea/{lego.id}/edit"),
        "revision": re.search(r'name="revision" value="([^"]+)"', page).group(1),
        "title": "Lego set",
        "kind": "gift",
        "participants": "Theo",
        "hidden_shown": "1",
        "hidden_from": [str(family["alex"].id), str(maya.id)],  # a kid in the list is ignored
    }
    saved = sam.post(f"/idea/{lego.id}/edit", data=form, follow_redirects=True)
    assert "Hidden from the kids and Alex." in saved.text  # the flash says whom
    assert idea_store.chosen_hidden_from(conn, [lego.id]) == {lego.id: [family["alex"].id]}
    assert "Lego set" not in alex.get("/ideas").text
    assert "Lego set" not in _kid_signed_in(app, sam, maya).get("/ideas").text


def test_a_new_present_is_kept_from_the_kids_and_the_grown_up_it_names(
    app, sam, family, conn
) -> None:
    from familydb.store import ideas as idea_store

    _two_kids_and_a_present(app, sam, conn)
    form = {
        **_tokens(sam, "/ideas/new"),
        "title": "Bike bell",
        "kind": "Present",  # any way of saying it
        "participants": "Maya",
        "hidden_shown": "1",
    }
    saved = sam.post("/ideas/new", data=form, follow_redirects=True)
    assert "Hidden from the kids." in saved.text
    bell = idea_store.find_similar_title(conn, "Bike bell")
    assert bell.kind == "gift"
    assert idea_store.chosen_hidden_from(conn, [bell.id]) == {bell.id: None}  # nobody chose


def test_a_form_without_the_boxes_leaves_a_present_as_it_was(app, sam, family, conn) -> None:
    from familydb.store import ideas as idea_store

    maya, _, lego = _two_kids_and_a_present(app, sam, conn)
    with db.transaction(conn):
        idea_store.set_hidden_from(conn, lego.id, [maya.id])
    page = sam.get(f"/idea/{lego.id}/edit").text
    form = {
        **_tokens(sam, f"/idea/{lego.id}/edit"),
        "revision": re.search(r'name="revision" value="([^"]+)"', page).group(1),
        "title": "Lego set!",
        "kind": "gift",
    }
    assert sam.post(f"/idea/{lego.id}/edit", data=form).status_code == 302
    assert idea_store.chosen_hidden_from(conn, [lego.id]) == {lego.id: [maya.id]}


def test_a_to_do_for_a_present_is_kept_from_whoever_the_present_is(app, sam, alex, family, conn):
    """ "Order Alex's watch" is on Sam's To do and Home, and on neither of Alex's."""
    from familydb.store import ideas as idea_store
    from familydb.store import tasks as task_store

    with db.transaction(conn):
        watch = idea_store.insert(
            conn, title="A watch", kind="gift", participants=["Alex"], now=NOW_ISO
        )
        task_store.insert(
            conn,
            title="Order the watch",
            notes="",
            owner_id=family["sam"].id,
            due_at=None,
            preferred_window="",
            operation_key="watch",
            channel="web",
            chat_id="c",
            now=NOW_ISO,
            idea_id=watch.id,
        )
    for path in ("/tasks", "/"):
        assert "Order the watch" in sam.get(path).text, path
        assert "Order the watch" not in alex.get(path).text, path
    assert alex.get("/task/1/edit").status_code == 404
    assert sam.get("/task/1/edit").status_code == 200
