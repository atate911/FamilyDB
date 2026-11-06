"""The family's lists (the shopping list and any other), kept by the `shopping_list` tool."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from flask import (
    abort,
    request,
    url_for,
)

from familydb import presents
from familydb.store import ideas as idea_store
from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.web import (
    auth,
    chat,
    views,
    wishes_view,
)
from familydb.web.answers import answer
from familydb.web.pages import bp, familydb_app


@bp.get("/lists/<name>")
@bp.get("/lists")
def lists_page(name: str | None = None) -> str:
    """Lists (docs/INTERFACE.md section 4): the list in use, big ticks that need no conversation;
    the other lists are chips, each at its own address (`/lists/costco`). Every tick and add is
    the shopping_list tool (edits.change_list). The shopping list is always there."""
    app = familydb_app()
    wanted = list_store.name_of(name or request.args.get("list", "")) or "shopping"
    with closing(app.connect()) as conn:
        order = _list_order(conn)
        if wanted not in order:
            abort(404)
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        named = {person.id: person.display_name for person in people}
        shown = []
        for name in order:
            ref = list_store.find(conn, name)
            held = list_store.items(conn, ref) if ref is not None else []
            shown.append(
                {
                    "name": name,
                    "title": views.list_title(name),
                    # Each with who put it there, as section 4 has it: "who asked".
                    "to_get": [
                        {
                            "text": item.text,
                            # How much the recipes that put it there want (groceries.py).
                            "note": item.note,
                            "by": views.person_of(named[item.added_by], slots)
                            if item.added_by in named
                            else None,
                        }
                        for item in held
                        if item.ticked_at is None
                    ],
                    "ticked": [item.text for item in held if item.ticked_at is not None],
                }
            )
        current = next(one for one in shown if one["name"] == wanted)
        # By the section of the store, once there are two (groceries.section_of).
        current["groups"] = views.list_groups(current["to_get"])
        chat.page_box(
            app,
            conn,
            people,
            scope={"label": current["title"], "text": f"About the {current['title'].lower()}:"},
        )
        chips = _chips(conn, shown, wanted)
    return answer(
        "lists.html",
        shown=current,
        lists=shown,
        chips=chips,
        summary=views.lists_summary(shown, current),
    )


def _chips(conn: Any, shown: list[dict[str, Any]], here: str) -> list[dict[str, Any]]:
    """Lists' chips: each list, then the presents and each kid's wishes for a grown-up who may
    see them, all things to get. Nothing to choose between is no chips at all."""
    visitor = auth.visitor()
    chips = [
        {
            "label": one["title"].removesuffix(" list").capitalize(),
            "href": url_for("web.lists_page", name=one["name"]),
            "on": one["name"] == here,
            "n": len(one["to_get"]),
        }
        for one in shown
    ]
    if visitor.may("browse"):
        chips.append({"label": "Presents", "href": url_for("web.presents"), "on": here == PRESENTS})
    if visitor.may("decide"):
        chips += [
            {
                "label": f"{kid.display_name}\u2019s wishes",
                "href": url_for("web.wishes", name=views.slug(kid.display_name)),
                "on": False,
            }
            for kid in wishes_view.kids(conn)
        ]
    return chips if len(chips) > 1 else []


# Lists' chip for the presents; never a list's own name, which `list_store.name_of` folds.
PRESENTS = "presents:"


@bp.get("/presents", endpoint="presents")
def presents_page() -> str:
    """The presents, under Lists' chips (docs/INTERFACE.md section 4): every gift idea this person
    may see, whom it is for and whom it is kept from. One kept from the visitor is not here at
    all, and a kid never reaches the page (presents.py, auth.NEEDS_HERE)."""
    app = familydb_app()
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, visitor.member)
        gifts = [
            idea
            for idea in idea_store.list_all(conn, include_dropped=False)
            if idea_store.is_gift(idea) and idea.id not in kept and idea.status != "done"
        ]
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        hidden = presents.of_presents(conn, gifts, people)
        names = {person.id: person.display_name for person in people}
        rows = []
        for idea in sorted(gifts, key=lambda one: one.created_at, reverse=True):
            row = views.idea_row(
                idea,
                app.settings.tzinfo,
                hidden=hidden[idea.id].words if idea.id in hidden else None,
            )
            people_for = views.people_for(idea, slots)
            parts = [f"for {row['who']}" if row["who"] else "a present"]
            if idea.suggested_by in names:
                parts.append(f"{names[idea.suggested_by]}\u2019s idea")
            if row["hidden"]:
                parts.append(f"hidden from {row['hidden']}")
            rows.append(
                {
                    **row,
                    "line": " · ".join(parts),
                    "people": people_for,
                    "who_words": views.names_text(people_for),
                }
            )
        shown = [
            {"name": name, "title": views.list_title(name), "to_get": _open_items(conn, name)}
            for name in _list_order(conn)
        ]
        chips = _chips(conn, shown, PRESENTS)
        chat.page_box(app, conn, people, scope={"label": "Presents", "text": "About the presents:"})
    return answer("presents.html", rows=rows, chips=chips, summary=_presents_summary(len(rows)))


def _list_order(conn: Any) -> list[str]:
    names = list_store.names(conn)
    return ["shopping", *(other for other in names if other != "shopping")]


def _open_items(conn: Any, name: str) -> list[Any]:
    ref = list_store.find(conn, name)
    held = list_store.items(conn, ref) if ref is not None else []
    return [item for item in held if item.ticked_at is None]


def _presents_summary(count: int) -> str:
    if not count:
        return "None yet."
    return (
        f"{count} present idea{'' if count == 1 else 's'}, each kept from whom it is for and "
        "from every kid."
    )
