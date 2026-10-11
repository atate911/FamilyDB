"""The kids' wish lists (docs/WISHES.md): each kid's lists for a parent, a kid's own for her."""

from __future__ import annotations

from contextlib import closing
from datetime import date

from flask import (
    abort,
    request,
    url_for,
)

from familydb.base import roles
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.web import (
    auth,
    chat,
    views,
    wishes_view,
)
from familydb.web.answers import answer
from familydb.web.pages import bp, familydb_app


@bp.get("/kids/<name>")
@bp.get("/wishes")
@bp.get("/kids")
def wishes(name: str | None = None) -> str:
    """The kids (docs/INTERFACE.md section 4): for a parent each kid as a section, what waits
    first; one kid at her own address (`/kids/maya`), with her pitches and her thread to read
    along; a kid's own wish lists, in her order."""
    app = familydb_app()
    today = app.clock.today()
    visitor = auth.visitor()
    wanted = request.args.get("who", "")
    waiting_only = request.args.get("waiting") == "1"
    with closing(app.connect()) as conn:
        if name is not None:
            named = next(
                (
                    kid
                    for kid in wishes_view.kids(conn)
                    if views.slug(kid.display_name) == name.casefold()
                ),
                None,
            )
            me = visitor.member
            mine = me is not None and named is not None and named.id == me.id
            if named is None or not (visitor.may("decide") or mine):
                abort(404)
            wanted = str(named.id) if visitor.may("decide") else ""
        if visitor.may("decide"):
            kids = wishes_view.kids(conn)
            if wanted:
                chosen = next((k for k in kids if str(k.id) == wanted), None)
                if chosen is None:
                    abort(404)
                kids = [chosen]
            shown = [wishes_view.lists(conn, kid, today) for kid in kids]
        elif visitor.member is not None:
            shown = [wishes_view.lists(conn, visitor.member, today)]
        else:
            abort(404)
        people = member_store.list_all(conn)
        everyone = wishes_view.kids(conn) if visitor.may("decide") else []
        pronouns = {
            person.id: {"female": "her", "male": "his"}.get(person.gender or "", "their")
            for person in people
        }
        talk = chat.page_box(  # kept for `talk`: a kid's add form shows only without the box
            app,
            conn,
            people,
            prompt=chat.KID_LIST_PROMPT if not visitor.may("decide") else chat.DEST_PROMPT,
            scope=(
                {"label": "The kids", "text": "About the kids:"}
                if visitor.may("decide")
                else {"label": "My list", "text": "About my list:"}
            ),
        )
    names = {member.id: member.display_name for member in people}
    parents = [m.display_name for m in people if m.active and roles.may(m.role, "decide")]
    if wanted and visitor.may("decide"):
        with closing(app.connect()) as conn:
            pitched = [
                idea
                for idea in idea_store.list_all(conn)
                if idea.suggested_by == shown[0]["id"] and not idea_store.is_gift(idea)
            ]
        shown[0]["pitches"] = [
            {
                "id": idea.id,
                "title": idea.title,
                "state": views.idea_state(idea, [], today),
                "when": views.day_short(
                    date.fromisoformat(views.local_day(idea.created_at, app.settings.tzinfo))
                ),
            }
            for idea in sorted(pitched, key=lambda idea: idea.created_at, reverse=True)[:8]
        ]
        shown[0]["thread"] = url_for("chat.show", **{"with": shown[0]["id"]}, _anchor="latest")
    for kid in shown:
        kid["pronoun"] = pronouns.get(kid["id"], "their")
        kid["turned"] = (
            [row for row in kid["turned"] if row["to_decide"]]
            if visitor.may("decide")
            else kid["turned"]
        )
    waiting = sum(len(kid["turned"]) for kid in shown) if visitor.may("decide") else 0
    if waiting_only:
        shown = [kid for kid in shown if kid["turned"]]
    chips = []
    if visitor.may("decide") and len(everyone) > 1:
        chips = [
            {
                "label": kid.display_name,
                "href": url_for("web.wishes", name=views.slug(kid.display_name)),
                "on": str(kid.id) == wanted,
            }
            for kid in everyone
        ]
        chips.append(
            {
                "label": "Waiting on you",
                "href": url_for("web.wishes", waiting="1"),
                "on": waiting_only,
            }
        )
        if wanted or waiting_only:
            chips.insert(0, {"label": "Everyone", "href": url_for("web.wishes"), "on": False})
    return answer(
        "kids.html",
        talk=not talk.get("no_box"),
        kids=shown,
        names=names,
        parents_text=views.names_text([{"name": name} for name in parents]),
        parent=visitor.may("decide"),
        one=bool(wanted) or not visitor.may("decide"),
        choices=[(value or "everyday", name) for value, name, _ in views.WISH_LISTS],
        chips=chips,
        summary=views.kids_summary(shown, waiting)
        if visitor.may("decide")
        else views.my_list_summary(shown[0]),
    )
