"""What is new in the running code, from the CHANGELOG.md shipped with it (whatsnew.py)."""

from __future__ import annotations

from pathlib import Path

from familydb import whatsnew

SAMPLE = """# Changelog

## v0.3.0 — in progress

Still being built.

### New since v0.2.0

- **Looks.** Each browser can choose
  how the page looks.
- **A new Home**, the first page of
  the new layout, with **bold** words.

## v0.2.0 — second alpha (2026-10-05)

### New since v0.1.0

- **Older.** Not shown.
"""


def test_the_top_section_is_what_is_new(tmp_path: Path) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(SAMPLE)
    new = whatsnew.latest(path)
    assert new is not None and new.heading == "v0.3.0 — in progress"
    assert new.items == (
        ("Looks", "Each browser can choose how the page looks."),
        ("A new Home", "the first page of the new layout, with bold words."),
    )
    assert whatsnew.latest(tmp_path / "missing.md") is None


def test_the_status_page_says_it(settings, clock, conn) -> None:
    from tests.test_web import _signed_in

    page = _signed_in(settings, clock).get("/status").text
    shipped = whatsnew.latest()
    assert shipped is not None  # the repository's own changelog
    assert "What\u2019s new" in page and f"In the version running now: {shipped.heading}." in page
    assert f"<dt>{shipped.items[0][0]}</dt>" in page
