"""The stylesheet's page hooks match the classes the templates give each page's body."""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "src" / "familydb" / "web"


def test_every_page_class_the_stylesheet_names_is_one_a_template_sets() -> None:
    css = (WEB / "static" / "style.css").read_text()
    templates = " ".join(path.read_text() for path in (WEB / "templates").rglob("*.html"))
    named = set(re.findall(r"\.(page-[a-z]+)\b", css)) - {
        "page-head"
    }  # a part of a page, not a page
    given = set(re.findall(r"block body_class %\}([^{]*)\{%", templates))
    classes = {name for each in given for name in each.split()}
    assert named - classes == set(), "the stylesheet names a page class no page wears"


def test_a_quiet_count_on_the_current_item_reads_in_that_items_ink() -> None:
    """--ink-3 was drawn for the page; on the current item's own fill it fell to 1.1 to 2:1 in six
    looks. The item's ink (`--on-here`, held to 4.5:1 by test_look) is what it must wear."""
    css = (WEB / "static" / "style.css").read_text()
    assert re.search(
        r'\.nav a\[aria-current="page"\] \.badge--quiet \{ color: var\(--on-here\); \}', css
    )


def test_a_kids_line_about_who_reads_her_chat_stays_on_the_phone() -> None:
    css = (WEB / "static" / "style.css").read_text()
    home = (WEB / "templates" / "home.html").read_text()
    assert "composer__foot--kid" in home
    assert ".ask .composer__foot:not(.composer__foot--kid)" in css


def test_the_chat_room_is_window_high_on_a_desktop_too() -> None:
    css = (WEB / "static" / "style.css").read_text()
    wide = css[css.index("@media (min-width: 821px) and (min-height: 600px)") :][:600]
    assert (
        ".chat { height:" in wide
        and ".scroller { flex: 1 1 0;" in wide
        and "overflow-y: auto" in wide
    )
