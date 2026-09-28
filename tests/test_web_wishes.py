"""The wish lists on the page (docs/WISHES.md): a kid's own, a parent's answers, and nothing of
one kid's shown to another."""

from __future__ import annotations

import re
from contextlib import closing

import pytest

from familydb.store import db, members, wishes
from tests.test_web_logins import KIDS, _as, _start, _tokens, app, sam  # noqa: F401

CHLOES = "chloe chooses hers too"


def _form(client, path: str) -> dict[str, str]:
    """A fresh CSRF and once-only token, from a page that has a form."""
    return _tokens(client, path)


@pytest.fixture
def girls(app, sam, family):  # noqa: F811
    """The girls (a kid) signed in as herself, and a sister, Chloe, signed in too."""
    kid = _as(app, "the girls", _start(sam, family["girls"].id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    with closing(app.connect()) as conn, db.transaction(conn):
        chloe = members.add(conn, "Chloe", "kid", now="2026-09-20T00:00:00Z")
    sister = _as(app, "Chloe", _start(sam, chloe.id))
    sister.post("/you", data={**_tokens(sister, "/you"), "new": CHLOES, "again": CHLOES})
    return {"mine": kid, "sister": sister, "chloe": chloe}


def _said(response) -> str:
    return " ".join(re.findall(r'class="said"[^>]*>\s*([^<]+)', response.text))


def _add(client, title, which="everyday", **extra):
    form = {**_form(client, "/wishes"), "title": title, "list": which, **extra}
    return client.post("/wishes", data=form, follow_redirects=True)


def _open(served, member_id, occasion=None):
    with closing(served.connect()) as conn:
        return wishes.open_list(conn, member_id, occasion)


def test_a_kid_keeps_her_own_list_on_the_page(app, family, girls) -> None:  # noqa: F811
    kid = girls["mine"]
    page = kid.get("/wishes")
    assert page.status_code == 200 and "My wishes" in page.text
    assert 'href="/wishes"' in kid.get("/").text  # in her bar, and on her Home
    assert "On your list: Lego." in _said(_add(kid, "Lego"))
    _add(kid, "Kite")
    _add(kid, "Roller skates", "birthday")
    mine = _open(app, family["girls"].id)
    assert [w.title for w in mine] == ["Lego", "Kite"]
    # Kite to the top, with the button's form.
    kite = mine[1]
    kid.post(f"/wish/{kite.id}/move", data={**_form(kid, "/wishes"), "position": "1"})
    assert [w.title for w in _open(app, family["girls"].id)] == ["Kite", "Lego"]
    # Lego flagged for Christmas.
    lego = mine[0]
    kid.post(f"/wish/{lego.id}/move", data={**_form(kid, "/wishes"), "list": "christmas"})
    assert [w.title for w in _open(app, family["girls"].id, "christmas")] == ["Lego"]
    kid.post(f"/wish/{kite.id}/withdraw", data=_form(kid, "/wishes"))
    assert _open(app, family["girls"].id) == []
    home = kid.get("/").text
    assert "My wishes" in home and "Roller skates" in home


def test_a_sister_sees_none_of_it_and_cannot_touch_it(app, family, girls) -> None:  # noqa: F811
    _add(girls["mine"], "A secret diary")
    wish = _open(app, family["girls"].id)[0]
    sister = girls["sister"]
    assert "A secret diary" not in sister.get("/wishes").text
    assert "A secret diary" not in sister.get("/").text
    assert sister.get(f"/wishes?who={family['girls'].id}").status_code == 200  # her own, still
    assert "A secret diary" not in sister.get(f"/wishes?who={family['girls'].id}").text
    moved = sister.post(
        f"/wish/{wish.id}/withdraw", data=_form(sister, "/wishes"), follow_redirects=True
    )
    assert "somebody else" in _said(moved)
    assert _open(app, family["girls"].id)[0].status == "open"
    answered = sister.post(
        f"/wish/{wish.id}/answer", data={**_form(sister, "/wishes"), "status": "granted"}
    )
    assert answered.status_code == 403


def test_a_parent_sees_every_kid_and_answers(app, family, sam, girls) -> None:  # noqa: F811
    _add(girls["mine"], "A cat")
    _add(girls["sister"], "Slime")
    overview = sam.get("/wishes").text
    assert "A cat" in overview and "Slime" in overview and "Wishes" in overview
    home = sam.get("/").text
    assert "The kids' wishes" in home and "A cat" in home
    cat = _open(app, family["girls"].id)[0]
    hers = sam.get(f"/wishes?who={family['girls'].id}").text
    assert "A cat" in hers and "Slime" not in hers
    no = sam.post(
        f"/wish/{cat.id}/answer",
        data={
            **_form(sam, f"/wishes?who={family['girls'].id}"),
            "status": "declined",
            "note": "The allergies, love.",
            "kid": str(family["girls"].id),
        },
        follow_redirects=True,
    )
    assert "Not this time: A cat." in _said(no)
    page = girls["mine"].get("/wishes").text
    assert "Not this time." in page and "The allergies, love." in page
    assert "Ask again after 4 October" in page
    # Her conversation says so too, worded by code.
    chat = girls["mine"].get("/chat").text
    assert "not this time for A cat" in chat
    # Asking again on the page is held to the lockout, as in the chat.
    again = _add(girls["mine"], "A cat")
    assert "You can ask again after 4 October" in _said(again)
    # A Christmas list is welcome instead.
    assert "On your list: A cat." in _said(_add(girls["mine"], "A cat", "christmas"))


def test_ask_a_parent_is_a_button_where_it_was_offered(app, family, girls) -> None:  # noqa: F811
    from familydb import wish_service

    with closing(app.connect()) as conn:
        kid = members.get(conn, family["girls"].id)
        turned = wish_service.turn_away(
            conn,
            app.settings,
            owner=kid,
            summary="more internet time",
            concern="rule",
            reviewable=True,
            now=app.clock.now(),
        )
    page = girls["mine"].get("/wishes").text
    assert "more internet time" in page and "Ask a parent" in page
    # Said to her as what to do next, not as the grown-ups' word for it.
    assert "a house rule: ask a parent" in page
    asked = girls["mine"].post(
        f"/wish/{turned.wish.id}/ask", data=_form(girls["mine"], "/wishes"), follow_redirects=True
    )
    assert "Sent to a parent." in _said(asked)
    assert "Ask a parent</button>" not in girls["mine"].get("/wishes").text  # once


def test_a_kid_home_speaks_to_her_and_offers_only_what_she_may(app, family, sam, girls) -> None:  # noqa: F811
    """Her ways to start say "I wish", never the "we should" Vera nudges her away from, and no
    empty list sends her to a form she would be refused (docs/STYLE.md, "A kid's screen")."""
    from familydb.web.chat import KID_HOME_PROMPT

    home = girls["mine"].get("/").text
    assert "I wish for…" in home and "We should try" not in home
    assert f'placeholder="{KID_HOME_PROMPT}"' in home
    assert 'href="/ideas/new"' not in home and "plan an idea" not in home
    assert "Add a wish" in home
    assert girls["mine"].get("/ideas/new").status_code == 403
    # A grown-up's Home is as it was.
    assert "We should try…" in sam.get("/").text and 'href="/ideas/new"' in sam.get("/").text
