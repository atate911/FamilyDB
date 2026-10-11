"""The family's lists (the shopping list and any other), kept by the `shopping_list` tool."""

from __future__ import annotations

from contextlib import closing

from flask import (
    abort,
    request,
    url_for,
)

from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.web import (
    chat,
    views,
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
        names = list_store.names(conn)
        order = ["shopping", *(other for other in names if other != "shopping")]
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
        chat.page_box(
            app,
            conn,
            people,
            scope={"label": current["title"], "text": f"About the {current['title'].lower()}:"},
        )
    chips = [
        {
            "label": one["title"].removesuffix(" list").capitalize(),
            "href": url_for("web.lists_page", name=one["name"]),
            "on": one["name"] == wanted,
            "n": len(one["to_get"]),
        }
        for one in shown
    ]
    return answer(
        "lists.html",
        shown=current,
        lists=shown,
        chips=chips if len(shown) > 1 else [],
        summary=views.lists_summary(shown),
    )
