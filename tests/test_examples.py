"""The example sites (examples/): the household builds, every person's pages are written, and a
written page links only to files that are there. A few pages each, so it stays quick."""

from __future__ import annotations

import re
from pathlib import Path

from examples import export, household


def test_the_examples_are_written_with_links_that_hold(tmp_path: Path) -> None:
    counts = export.export(tmp_path, most=6)
    assert set(counts) == {"sam", "maya", "board", "first-day"} and all(counts.values())
    for person in export.PEOPLE:
        folder = tmp_path / person.key
        pages = sorted(folder.glob("*.html"))
        assert (folder / export.NOT_HERE) in pages
        for page in pages:
            text = page.read_text("utf-8")
            for target in re.findall(r'(?:href|src)="([^"#:]+)', text):
                assert (folder / target).exists(), f"{person.key}/{page.name} -> {target}"
            assert "data-theme=" not in text  # the look survives a viewer's own theme
            for form in re.findall(r"<form\b[^>]*>", text):
                assert 'action="#"' in form and "data-demo=" in form
            # Nothing of the household's made-up secrets is ever drawn.
            assert "sk-example" not in text and "example-token" not in text
    start = (tmp_path / "index.html").read_text("utf-8")
    for target in re.findall(r'href="([^"#]+)"', start):
        assert (tmp_path / target).exists(), target
    assert (tmp_path / "start.html").read_text("utf-8").startswith("<title>")
    assert (tmp_path / "static" / "style.css").exists()
    assert (tmp_path / "demo" / "demo.js").exists()


def test_each_person_starts_where_they_would(tmp_path: Path) -> None:
    sam = export.crawl(export.PEOPLE[0], tmp_path / "sam")
    now = sam.pages["/"]
    assert "How did Riverside Science Center go?" in now and "Maya asked for" in now
    assert "said-sheet" in sam.pages[f"/eat?asked={household.REPLY_ON_EAT}"]
    assert 'class="rcpt"' in sam.pages[f"/do?asked={household.RECEIPT_ON_DO}"]
    first = export.crawl(export.PEOPLE[3], tmp_path / "first")
    assert "Hi, I&#39;m Vera." in first.pages["/"]


def test_a_file_name_for_every_address() -> None:
    assert export.file_for("/") == "index.html"
    assert export.file_for("/idea/12") == "idea-12.html"
    assert export.file_for("/do?kind=outing") == "do--kind-outing.html"
    long = export.file_for("/eat?asked=" + "a" * 64)
    assert long.endswith(".html") and len(long) < 70
