"""The files the Kitchen Table stylesheet needs sit in `static/` beside the page's own, and the
rules the page keeps (no colour but a token, no inline script or style) hold for them."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import familydb.web as package
from familydb.app import App
from familydb.web import create_app

WEB = Path(package.__file__).parent
STATIC = WEB / "static"
KITCHEN = STATIC / "style.css"


@pytest.fixture
def client(settings, clock, conn):
    return create_app(App(settings, clock)).test_client()


def test_the_new_files_are_served(client) -> None:
    for name in (
        "style.css",
        "icons.svg",
        "brand/favicon.svg",
        "brand/favicon-32.png",
        "brand/favicon-16.png",
        "brand/apple-touch-icon.png",
        "brand/icon-512.png",
        "fonts/atkinson-400.woff2",
        "fonts/fraunces-soft-600.woff2",
    ):
        assert client.get(f"/static/{name}").status_code == 200, name


def test_every_font_the_stylesheet_names_is_here() -> None:
    css = KITCHEN.read_text("utf-8")
    names = re.findall(r'url\("([^"]+)"\)', css)
    assert names
    for name in names:
        assert (STATIC / name).is_file(), name


def test_the_stylesheet_has_no_colour_of_its_own_outside_the_fixed_layer() -> None:
    """Every colour but the brand's (the glass, the phosphor, her mark) is a token a look sets in
    themes.css, so a look can never be the reason one page is different."""
    css = re.sub(r"/\*.*?\*/", "", KITCHEN.read_text("utf-8"), flags=re.S)
    root = re.search(r"^:root \{.*?^\}", css, re.S | re.M)
    assert root
    outside = css[: root.start()] + css[root.end() :]
    assert not re.findall(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(", outside)


def test_the_sprite_has_what_the_scripts_ask_for() -> None:
    sprite = (STATIC / "icons.svg").read_text("utf-8")
    have = set(re.findall(r'<symbol id="i-([a-z0-9]+)"', sprite))
    drawings = set(re.findall(r'<symbol id="d-([a-z0-9]+)"', sprite))
    assert "mic" in have  # dictate.js draws it
    assert drawings == {"plans", "todos", "ideas", "wish", "yes"}  # docs/STYLE.md, "Drawings"
    assert len(have) + len(drawings) == len(re.findall(r"<symbol ", sprite))  # no name twice


def test_no_page_has_an_inline_script_or_style() -> None:
    """The content policy is `script-src 'self'` and `style-src 'self'`: a template that wrote
    either inline would work in a test and be blocked in a browser."""
    found = []
    for path in sorted((WEB / "templates").rglob("*.html")):
        text = path.read_text("utf-8")
        for pattern in (r"<script(?![^>]*\bsrc=)[^>]*>", r'\sstyle="', r"\son[a-z]+=\""):
            for hit in re.finditer(pattern, text):
                found.append(f"{path.relative_to(WEB)}: {hit.group(0).strip()}")
    assert not found, "\n".join(found)
