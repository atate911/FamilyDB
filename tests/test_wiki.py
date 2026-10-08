"""The guide at /wiki: who may read it, that it serves what `_nav.json` lists and nothing else,
that its links and anchors resolve, and how it renders and searches."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from familydb.web import wiki
from tests.test_web_logins import (  # noqa: F401
    KIDS,
    _as,
    _as_family,
    _browser,
    _start,
    _tokens,
    app,
    sam,
)


def _nodes(tree):
    for node in tree:
        yield node
        yield from _nodes(node.get("children", []))


def _file(node) -> Path:
    """A page is `slug.md`, or `slug/index.md` for a section."""
    slug = node["slug"]
    for found in (wiki.CONTENT_DIR / f"{slug}.md", wiki.CONTENT_DIR / slug / "index.md"):
        if found.is_file():
            return found
    return wiki.CONTENT_DIR / f"{slug}.md"


def _kid(app, sam, family):  # noqa: F811
    girls = _as(app, "the girls", _start(sam, family["girls"].id))
    form = {**_tokens(girls, "/you"), "new": KIDS, "again": KIDS}
    assert girls.post("/you", data=form).headers["Location"] == "/"
    return girls


# -- who may read it


def test_parents_and_admins_read_it_and_kids_do_not(app, sam, family) -> None:  # noqa: F811
    alex = _as(app, "Alex", _start(sam, family["alex"].id))
    form = {
        **_tokens(alex, "/you"),
        "new": "alex chose this one today",
        "again": "alex chose this one today",
    }
    assert alex.post("/you", data=form).headers["Location"] == "/"
    girls = _kid(app, sam, family)
    for path in ("/wiki", "/wiki/_search?q=start"):
        assert sam.get(path).status_code == 200, path
        assert alex.get(path).status_code == 200, path
        refused = girls.get(path)
        assert refused.status_code == 403 and "For a parent" in refused.text, path
    # The way in is there for the grown-ups and not on a kid's screen.
    assert 'href="/wiki"' in sam.get("/").text and 'href="/wiki"' in sam.get("/more").text
    assert (
        'href="/wiki"' not in girls.get("/").text and 'href="/wiki"' not in girls.get("/more").text
    )


def test_somebody_not_signed_in_is_sent_to_the_sign_in(app) -> None:  # noqa: F811
    stranger = _browser(app)
    for path in ("/wiki", "/wiki/overview", "/wiki/_search?q=start"):
        sent = stranger.get(path)
        assert sent.status_code == 302 and "/login" in sent.headers["Location"], path


# -- what it serves


def test_status_and_each_settings_page_link_to_their_guide_page(app, sam, family) -> None:  # noqa: F811
    from familydb.web import fields, views

    slugs = {
        node["slug"]
        for node in _nodes(json.loads((wiki.CONTENT_DIR / "_nav.json").read_text("utf-8"))["tree"])
    }
    pages = {"/status": "controls/status", "/settings": "controls/settings"}
    for one in fields.SECTIONS:
        pages[f"/settings/{one.name}"] = views.GUIDE_FOR_SETTINGS.get(
            one.name, f"controls/settings/{one.name}"
        )
    for path, slug in pages.items():
        assert slug in slugs, (path, slug)
        assert f'href="/wiki/{slug}"' in sam.get(path).text, path
    # A kid is refused those pages, so the way in is never on a kid's screen.
    girls = _kid(app, sam, family)
    for path in pages:
        assert girls.get(path).status_code == 403, path


def test_the_nav_and_the_files_agree(app) -> None:  # noqa: F811
    tree = json.loads((wiki.CONTENT_DIR / "_nav.json").read_text("utf-8"))["tree"]
    assert tree and tree[0]["slug"] == "index"
    client = _as_family(app)
    listed = set()
    for node in _nodes(tree):
        assert _file(node).is_file(), f"{node['slug']} has no file at {_file(node)}"
        assert node.get("audience") in wiki.AUDIENCE_LABELS, node["slug"]
        assert node.get("depth") in wiki.DEPTH_LABELS, node["slug"]
        url = "/wiki" if node["slug"] == "index" else f"/wiki/{node['slug']}"
        assert client.get(url).status_code == 200, url
        listed.add(node["slug"])
        for other in node.get("see_also", []):
            assert other in {n["slug"] for n in _nodes(tree)}, f"{node['slug']} -> {other}"
    # And the other way: no page is served that the sidebar does not list.
    served = {slug for slug, _ in wiki._pages()}
    assert served == listed, f"not in the nav: {served - listed}; not on disk: {listed - served}"


def test_every_page_is_plain_words_and_its_links_and_anchors_hold() -> None:
    pages = dict(wiki._pages())
    assert pages
    for slug, path in pages.items():
        html, _ = wiki._render(path)
        assert "<script" not in html.lower() and "style=" not in html.lower(), slug
        for target in re.findall(r'href="(/wiki[^"]*)"', html):
            where, _, anchor = target.partition("#")
            other = "index" if where == "/wiki" else where.removeprefix("/wiki/")
            assert other in pages, f"{slug} links to {target}, which is not a page"
            if anchor:
                there, _ = wiki._render(pages[other])
                assert f'id="{anchor}"' in there, f"{slug} links to {target}: no such heading"


def test_the_guides_own_notes_and_machinery_are_never_served(app) -> None:  # noqa: F811
    client = _as_family(app)
    for url in ("/wiki/_nav", "/wiki/_nav.json", "/wiki/_outline", "/wiki/_outline.md"):
        assert client.get(url).status_code == 404, url
    assert not [slug for slug, _ in wiki._pages() if slug.rsplit("/", 1)[-1][:1] == "_"]


def test_a_path_out_of_the_folder_is_a_404_that_leaks_nothing(app) -> None:  # noqa: F811
    client = _as_family(app)
    for url in (
        "/wiki/..%2f..%2fconfig.py",
        "/wiki/..%2f..%2f..%2fetc%2fpasswd",
        "/wiki/%2e%2e%2f%2e%2e%2fapp",
        "/wiki/overview/..%2f..%2f..%2fweb%2fauth",
    ):
        found = client.get(url)
        assert found.status_code == 404, url
        assert "root:" not in found.text and "SECRET" not in found.text.upper(), url


def test_a_page_that_is_not_there_is_a_404_inside_the_guide(app) -> None:  # noqa: F811
    found = _as_family(app).get("/wiki/nope/not-here")
    assert found.status_code == 404
    assert "not in the guide" in found.text and 'class="wiki__nav"' in found.text


def test_pages_say_who_they_are_for_and_how_deep(app) -> None:  # noqa: F811
    body = _as_family(app).get("/wiki").text
    assert "For parents and admins" in body and "Overview" in body
    assert 'class="wiki__nav"' in body and 'aria-current="page"' in body


# -- how it renders


def _guide(tmp_path, monkeypatch, pages: dict[str, str], nav: list[dict]) -> None:
    for name, text in pages.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    (tmp_path / "_nav.json").write_text(json.dumps({"tree": nav}), encoding="utf-8")
    monkeypatch.setattr(wiki, "CONTENT_DIR", tmp_path)


def test_markdown_features_render(tmp_path) -> None:
    page = tmp_path / "feature.md"
    page.write_text(
        "# Title\n\n## One\n\n```bash\necho hi\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n"
        "The *API* is here.\n\n*[API]: Application programming interface\n",
        encoding="utf-8",
    )
    html, toc = wiki._render(page)
    assert "<pre" in html and "<code" in html and "<table" in html and "<abbr" in html
    assert 'id="one"' in html and "#one" in toc


def test_an_edit_shows_on_the_next_view_without_a_restart(app, tmp_path, monkeypatch) -> None:  # noqa: F811
    _guide(
        tmp_path,
        monkeypatch,
        {"index.md": "# Home\n\nbefore\n"},
        [{"slug": "index", "title": "Home", "audience": "admin", "depth": "overview"}],
    )
    client = _as_family(app)
    assert "before" in client.get("/wiki").text
    page = tmp_path / "index.md"
    page.write_text("# Home\n\nafter\n", encoding="utf-8")
    later = time.time() + 5  # two quick writes can share a timestamp
    os.utime(page, (later, later))
    body = client.get("/wiki").text
    assert "after" in body and "before" not in body


def test_a_guide_with_no_nav_still_serves_its_pages(app, tmp_path, monkeypatch) -> None:  # noqa: F811
    (tmp_path / "index.md").write_text("# Alone\n\nstill here\n", encoding="utf-8")
    (tmp_path / "_nav.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(wiki, "CONTENT_DIR", tmp_path)
    found = _as_family(app).get("/wiki")
    assert found.status_code == 200 and "still here" in found.text


# -- how it searches


def _two_pages(tmp_path, monkeypatch) -> None:
    _guide(
        tmp_path,
        monkeypatch,
        {
            "index.md": "# Start here\n\nThe guide. Nothing about money.\n",
            "cost.md": "# Spending\n\nThe daily limit holds the family's spending down.\n",
            "jobs.md": "# Jobs\n\n## Spending check\n\nOnce a day the spending is looked at.\n",
            "_notes.md": "# Notes\n\nspending secrets\n",
        },
        [
            {"slug": "index", "title": "Start here", "audience": "grownups", "depth": "overview"},
            {"slug": "cost", "title": "Spending", "audience": "admin", "depth": "deep"},
            {"slug": "jobs", "title": "Jobs", "audience": "admin", "depth": "deep"},
        ],
    )


def test_search_ranks_the_title_then_the_heading_then_the_body(app, tmp_path, monkeypatch) -> None:  # noqa: F811
    _two_pages(tmp_path, monkeypatch)
    body = _as_family(app).get("/wiki/_search?q=spending").text
    found = re.findall(r'class="wiki__result-title" href="([^"]+)"', body)
    assert found == ["/wiki/cost", "/wiki/jobs"]  # not the notes, whose name begins _
    assert "2 pages match" in body and "<mark>spending</mark>" in body.lower()


def test_search_needs_every_word(app, tmp_path, monkeypatch) -> None:  # noqa: F811
    _two_pages(tmp_path, monkeypatch)
    client = _as_family(app)
    both = client.get("/wiki/_search?q=spending+daily").text
    assert re.findall(r'class="wiki__result-title" href="([^"]+)"', both) == ["/wiki/cost"]
    none = client.get("/wiki/_search?q=spending+zebra").text
    assert "Nothing in the guide matches" in none and "wiki__result-title" not in none


def test_search_states_and_limits(app, tmp_path, monkeypatch) -> None:  # noqa: F811
    _two_pages(tmp_path, monkeypatch)
    client = _as_family(app)
    assert "Type a word or two" in client.get("/wiki/_search").text
    assert "at least two letters" in client.get("/wiki/_search?q=a").text
    long = client.get("/wiki/_search?q=" + "x" * 500).text
    assert "x" * 81 not in long  # shown back no longer than the clamp
    # What was typed comes back escaped, in the box and in the headline.
    shown = client.get("/wiki/_search?q=%3Cscript%3Ealert(1)%3C/script%3E").text
    assert "<script>alert(1)" not in shown and "&lt;script&gt;" in shown


def test_every_guide_page_has_the_search_box(app) -> None:  # noqa: F811
    client = _as_family(app)
    for url in ("/wiki", "/wiki/_search?q=start"):
        assert 'action="/wiki/_search"' in client.get(url).text, url


# -- the settings reference names every setting


def test_every_setting_is_named_on_a_settings_page() -> None:
    """A new setting goes on its page of the guide, in the same change (CLAUDE.md)."""
    from familydb.store.settings import BEHAVIOUR, PROFILE

    text = "\n".join(
        path.read_text("utf-8")
        for path in (wiki.CONTENT_DIR / "controls" / "settings").glob("*.md")
    )
    missing = [key for key in (*BEHAVIOUR, *PROFILE) if f"`{key}`" not in text]
    assert not missing, f"settings the guide does not name: {missing}"
