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
