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


def test_a_quiet_count_carries_its_own_ground() -> None:
    """A count is a dot with its own fill, so it reads the same on the current item's faint fill as
    on the page: --ink-2 on --paper-2, never the dim ink that fell to 1.1 to 2:1 on a fill."""
    css = (WEB / "static" / "style.css").read_text()
    assert ".badge--quiet { background: var(--paper-2); color: var(--ink-2); }" in css


def test_a_kids_frame_is_marked_on_the_wrapper_so_the_stylesheet_can_size_it() -> None:
    """The body class is a page's; a kid's bigger box and words come from the frame's own mark."""
    css = (WEB / "static" / "style.css").read_text()
    frame = (WEB / "templates" / "frame.html").read_text()
    assert "nf--kid" in frame and ".nf--kid .box" in css


def test_the_chat_room_is_window_high_on_a_desktop_too() -> None:
    css = (WEB / "static" / "style.css").read_text()
    wide = css[css.index("@media (min-width: 821px) and (min-height: 600px)") :][:600]
    assert (
        ".chat { height:" in wide
        and ".scroller { flex: 1 1 0;" in wide
        and "overflow-y: auto" in wide
    )
