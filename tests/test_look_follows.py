# ruff: noqa: F811
"""A person's look follows them to every phone and computer they sign in on (`members.look`)."""

from __future__ import annotations

from tests.test_look import PASSWORD, _cookies, _token, _wearing, looks, page  # noqa: F401
from tests.test_web_logins import alex, app, sam  # noqa: F401


def _choose(browser, theme: str, mode: str = "auto"):
    return browser.post(
        "/look", data={"csrf": _token(browser), "theme": theme, "mode": mode}, follow_redirects=True
    )


def test_choosing_a_look_keeps_it_for_this_person_and_tells_them_so(app, sam, family, conn) -> None:
    from familydb.store import members

    saved = _choose(sam, "rail", "dark")
    assert "Saved. You&#39;ll see Rail yellow on every phone and computer you sign in on." in (
        saved.text
    )
    assert members.get(conn, family["sam"].id).look == "rail.dark"
    assert _wearing(sam) == ("rail", "dark")


def test_signing_in_somewhere_else_brings_their_look_with_it(app, sam, family, conn) -> None:
    from tests.test_web_logins import SAMS, _as

    _choose(sam, "ink", "light")
    fresh = _as(app, "Sam", SAMS)  # another phone, which has never worn it
    assert _wearing(fresh) == ("ink", "light")
    assert "fdb_look=ink.light" in _cookies(fresh.get("/look")) or fresh.get_cookie("fdb_look")
    assert fresh.get_cookie("fdb_look").value == "ink.light"


def test_two_people_on_one_browser_each_keep_their_own(app, sam, alex, family, conn) -> None:
    from tests.test_web_logins import ALEXS, SAMS, _as

    _choose(sam, "ink")
    shared = _as(app, "Sam", SAMS)
    assert _wearing(shared) == ("ink", None)
    shared.post("/logout", data={"csrf": _token(shared, "/look")})
    again = shared.post("/login", data={"name": "Alex", "password": ALEXS})
    assert again.status_code == 302
    assert _wearing(shared)[0] == "kitchen"  # Alex chose none: not Sam's left on the browser
    _choose(shared, "fjord")
    assert _wearing(_as(app, "Sam", SAMS))[0] == "ink"  # and Sam's is still Sam's


def test_while_the_family_shares_one_password_the_look_stays_in_the_browser(
    page, conn, family
) -> None:
    from familydb.store import members

    saved = _choose(page, "fjord", "dark")
    assert "This browser wears Fjord from now on." in saved.text
    assert all(member.look is None for member in members.list_all(conn))
    assert _wearing(page) == ("fjord", "dark")


def test_a_stored_look_that_names_no_look_is_the_default(app, sam, family, conn) -> None:
    from familydb.store import db, members

    with db.transaction(conn):
        members.set_look(conn, family["sam"].id, "nothing.dark")
    assert _wearing(sam) == ("kitchen", None)
    assert looks.parse("nothing.dark")[0].key == looks.DEFAULT


def test_nobody_sets_another_person_s_look(app, sam, alex, family, conn) -> None:
    from familydb.store import members

    _choose(alex, "midnight")
    assert members.get(conn, family["alex"].id).look == "midnight.auto"
    assert members.get(conn, family["sam"].id).look is None
    assert "member" not in {"theme", "mode", "csrf"}  # the form names no person to change
