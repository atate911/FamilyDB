"""Plain colours for a browser without light-dark(): the file is what the generator writes."""

from __future__ import annotations

import re

from familydb.web import fallback


def test_the_fallback_file_is_what_the_generator_writes() -> None:
    """After changing themes.css or style.css's tokens: uv run python -m familydb.web.fallback"""
    on_disk = (fallback.STATIC / "themes-fallback.css").read_text("utf-8")
    assert on_disk == fallback.written()


def test_a_pair_is_picked_by_side_even_inside_a_longer_value() -> None:
    assert fallback.pick("light-dark(#fff, #000)", False) == "#fff"
    assert fallback.pick("light-dark(#fff, #000)", True) == "#000"
    shadow = "0 1px 0 light-dark(rgb(1 2 3 / .1), rgb(0 0 0 / .5)), 0 2px light-dark(red, blue)"
    assert fallback.pick(shadow, False) == "0 1px 0 rgb(1 2 3 / .1), 0 2px red"
    assert fallback.pick(shadow, True) == "0 1px 0 rgb(0 0 0 / .5), 0 2px blue"
    nested = "light-dark(var(--a), light-dark(x, y))"
    assert fallback.pick(nested, True) == "y" and fallback.pick(nested, False) == "var(--a)"


def test_every_pair_in_the_looks_has_a_plain_day_and_night_value() -> None:
    css = fallback.written()
    assert "light-dark(" not in css.split("{", 1)[1]  # only the @supports test names it
    for key in ("kitchen", "afterglow"):
        assert f'[data-theme="{key}"]' in css
    # The page's own day and night: the device's setting, then the page's.
    assert "prefers-color-scheme: dark" in css and '[data-mode="dark"]' in css
    # Kitchen Table's paper, by day and by night.
    kitchen = css[css.index('  [data-theme="kitchen"] {') :]
    assert re.search(r"--paper: #F6F1E7;", kitchen) and re.search(r"--paper: #0C100F;", kitchen)


def test_the_page_links_the_fallback_after_the_looks() -> None:
    base = (fallback.STATIC.parent / "templates" / "base.html").read_text("utf-8")
    assert base.index("themes.css") < base.index("themes-fallback.css")
