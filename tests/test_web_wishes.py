"""The wish lists on the page (docs/WISHES.md): a kid's own, a parent's answers, and nothing of
one kid's shown to another."""

from __future__ import annotations

import re
from contextlib import closing
from pathlib import Path

import pytest

from familydb.store import db, members, tasks, wishes
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
    return " ".join(re.findall(r'class="(?:said|banner__text)"[^>]*>\s*([^<]+)', response.text))


def _add(client, title, which="everyday", **extra):
    form = {**_form(client, "/wishes"), "title": title, "list": which, **extra}
    return client.post("/wishes", data=form, follow_redirects=True)


def _open(served, member_id, occasion=None):
    with closing(served.connect()) as conn:
        return wishes.open_list(conn, member_id, occasion)


def test_a_kid_keeps_her_own_list_on_the_page(app, family, girls) -> None:  # noqa: F811
    kid = girls["mine"]
    page = kid.get("/wishes")
    assert page.status_code == 200 and "My list" in page.text
    assert 'href="/wishes"' in kid.get("/").text  # in her bar, and on her Home
    assert "On your list: Lego." in _said(_add(kid, "Lego"))
    _add(kid, "Kite")
    _add(kid, "Roller skates", "birthday")
    mine = _open(app, family["girls"].id)
    assert [w.title for w in mine] == ["Lego", "Kite"]
    # One line to a wish, which opens to its buttons, with a grip to drag it by.
    listed = kid.get("/wishes").text
    assert listed.count('<details class="wish__open">') == 3 and 'class="wish__grip"' in listed
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
    # Home shows her everyday top three, and how far off the occasions are.
    assert "My list" in home and "Christmas in" in home


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
    assert "A cat" in overview and "Slime" in overview and "The kids\u2019 lists" in overview
    home = sam.get("/").text
    assert "The kids\u2019 lists" in home and "A cat" in home
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
    """Her box is the one natural place to say anything: no ways to start put in her mouth (least of
    all the "we should" Vera nudges her away from), and no empty list sending her to a form she
    would be refused (docs/STYLE.md, "A kid's screen").
    """
    from familydb.web.chat import KID_HOME_PROMPT

    home = girls["mine"].get("/").text
    assert 'class="starters"' not in home and "We should try" not in home
    assert f'placeholder="{KID_HOME_PROMPT}"' in home
    assert 'href="/ideas/new"' not in home and "plan an idea" not in home
    assert "Tell Vera anything" not in home and 'href="/wishes"' in home
    assert girls["mine"].get("/ideas/new").status_code == 403
    # A grown-up's Home has no ways to start either, but can add an idea from it.
    assert "We should try" not in sam.get("/").text and 'href="/ideas/new"' in sam.get("/").text


def test_her_list_opens_on_one_box_for_anything(app, family, sam, girls) -> None:  # noqa: F811
    """Where she lands on her list: one box, the chat's own, posting to her conversation, where
    Vera sorts what she says; no second form to choose between. A parent's view of her list has
    the add form and no chat box."""
    page = girls["mine"].get("/wishes").text
    assert 'action="/chat"' in page and "Tell Vera anything" in page
    assert 'id="wish-add"' not in page and "Add to my list" not in page
    parent = sam.get(f"/wishes?who={family['girls'].id}").text
    assert 'action="/chat"' not in parent and "Tell Vera anything" not in parent
    assert 'id="wish-add"' in parent


def test_a_kid_sees_the_pages_simply(app, family, girls) -> None:  # noqa: F811
    """Things to do, Plans and Ideas for a kid: what is hers or the family's, with nothing to
    filter, count or choose between, and no workings (docs/STYLE.md, "A kid's screen")."""
    kid = girls["mine"]
    todo = kid.get("/tasks").text
    assert "My to-dos" in todo and 'role="search"' not in todo and "shown (up to" not in todo
    plans = kid.get("/plans").text
    assert (
        "What the family is doing next." in plans and "plans/month" not in plans.split("<main")[-1]
    )
    ideas = kid.get("/ideas").text
    assert 'role="search"' not in ideas and "details not looked up" not in ideas
    home = kid.get("/").text
    assert "Lately added" not in home


def test_a_kid_ticks_off_her_own_things_to_do_and_nobody_else_s(app, family, girls) -> None:  # noqa: F811
    """The family decided the girls tick off their own (roles.py `own_tasks`): the tick is hers,
    and update_task, which the page and the chat both go through, refuses anybody else's."""
    kid = girls["mine"]
    with closing(app.connect()) as conn, db.transaction(conn):

        def task(title, owner):
            return tasks.insert(
                conn,
                title=title,
                notes="",
                owner_id=owner,
                due_at=None,
                preferred_window="",
                operation_key=f"test-{title}",
                channel="web",
                chat_id="web",
                now="2026-09-20T00:00:00Z",
            )

        swim = task("Pack swim bag", family["girls"].id)
        car = task("Renew car registration", family["sam"].id)
    page = kid.get("/tasks").text
    assert f'action="/task/{swim}/done"' in page and "Renew car registration" not in page
    tick = {**_tokens(kid, "/you"), "revision": "1"}
    ticked = kid.post(f"/task/{swim}/done", data=tick, follow_redirects=True)
    assert "Done: Pack swim bag!" in ticked.text  # no number: that is the workings
    tick = {**_tokens(kid, "/you"), "revision": "1"}
    refused = kid.post(f"/task/{car}/done", data=tick, follow_redirects=True)
    assert "only your own things to do" in refused.text
    with closing(app.connect()) as conn:
        assert tasks.get(conn, swim).status == "done"
        assert tasks.get(conn, car).status == "open"


def test_one_line_to_a_wish_and_the_hooks_the_script_looks_for(app, family, sam, girls) -> None:  # noqa: F811
    """wishes.js drags by `.wish__grip` and sends the line's `form.wish__move`: both are in the
    markup, so the move goes through the same token and tool as a button."""
    script = (Path(__file__).parents[1] / "src/familydb/web/static/wishes.js").read_text()
    assert '".wish__grip"' in script and "form.wish__move" in script
    _add(girls["mine"], "Lego")
    page = girls["mine"].get("/wishes").text
    line = re.search(r'<li class="wish wish--line".*?</li>', page, re.S).group(0)
    assert 'class="wish__grip"' in line and 'class="wish__move"' in line
    assert "Number 1: </span>Lego" in line and 'class="wish__n wish__n--first"' in line
    # Her line has no answer: only a parent's does.
    assert "wish__answer" not in line
    parent = sam.get(f"/wishes?who={family['girls'].id}").text
    assert 'class="wish__answer"' in parent and "Not this time</button>" in parent


def test_what_each_person_is_told_about_whom_a_list_is_not_secret_from(
    app,  # noqa: F811
    family,
    sam,  # noqa: F811
    girls,
) -> None:
    kid = girls["mine"].get("/wishes").text
    assert "can see it." in kid and "Sam" in kid.split("can see it.")[0].rsplit("secret", 1)[-1]
    assert "Planning a present?" in sam.get("/wishes").text
    assert "Planning a present?" not in kid


def test_home_counts_what_waits_on_each_kid(app, family, sam, girls) -> None:  # noqa: F811
    """The card on a parent's Home says "1 to decide" against the kid it waits on, whatever the
    wish's own number is."""
    from familydb import wish_service

    with closing(app.connect()) as conn:
        for number in range(4):  # so the wish's id is not the kid's
            turned = wish_service.turn_away(
                conn,
                app.settings,
                owner=members.get(conn, family["girls"].id),
                summary=f"a thing {number}",
                concern="rule",
                reviewable=number == 3,  # only the last can be asked about
                now=app.clock.now(),
            )
    girls["mine"].post(
        f"/wish/{turned.wish.id}/ask", data=_form(girls["mine"], "/wishes"), follow_redirects=True
    )
    home = sam.get("/").text
    card = home[home.index('id="h-wish"') :].split("</section>")[0]
    hers, chloes = (
        next(entry for entry in card.split("<li>") if name in entry)
        for name in (family["girls"].display_name, "Chloe")
    )
    assert "1 to decide" in hers and "to decide" not in chloes  # not on whoever has that number


def test_a_kid_never_sees_the_tools_a_turn_ran(app, family, sam, girls) -> None:  # noqa: F811
    """The log keeps a turn's tool calls against the question; a kid reading her chat never sees
    how it works (docs/DESIGN.md section 16)."""
    from familydb.store import messages

    chat = wish_service_chat(family["girls"].id)
    with closing(app.connect()) as conn, db.transaction(conn):
        asked = messages.insert_in(
            conn,
            channel="web",
            channel_update_id=None,
            chat_id=chat,
            member_id=family["girls"].id,
            text="can I have a cat",
        )
        messages.mark_processed(conn, asked.id, [{"tool": "add_wish", "input": {}}])
        messages.insert_out(
            conn, channel="web", chat_id=chat, text="On your list: a cat.", reply_to=asked.id
        )
    page = girls["mine"].get("/chat").text
    assert "On your list: a cat." in page
    assert "Added a wish" not in page and "add_wish" not in page


def wish_service_chat(member_id: int) -> str:
    from familydb.web import chat

    return chat.private_chat(member_id)
