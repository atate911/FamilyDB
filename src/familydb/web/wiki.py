"""The guide: how FamilyDB works and how to run it, for parents and admins (`/wiki`).

Pages are Markdown in `src/familydb/wiki/`, laid out by `_nav.json` (the sidebar, each page's
audience and depth, what to read next). They are read from disk and rendered here, cached by
modification time, so an edit shows on the next view with no restart. Search reads the same
folder. Nothing here touches a table or a model: a page view costs nothing, and what is shown is
the project's own writing, never anything a family member or a fetched page said.

Who may read it is `auth.NEEDS` (`browse`: parents and admins, never a kid). Files and folders
whose names begin with an underscore are the guide's machinery or its notes, and are never served.
"""

from __future__ import annotations

import json
import logging
import re
from html import unescape
from pathlib import Path
from typing import Any

import markdown
from flask import Blueprint, render_template, request, url_for
from markupsafe import Markup, escape
from werkzeug.security import safe_join

import familydb

log = logging.getLogger(__name__)
bp = Blueprint("wiki", __name__)

CONTENT_DIR = Path(familydb.__file__).resolve().parent / "wiki"

_MD_EXTENSIONS = ["fenced_code", "tables", "toc", "sane_lists", "attr_list", "abbr"]
_MD_EXTENSION_CONFIGS = {"toc": {"toc_depth": "2-3"}}

# Badge words live here so the templates stay free of logic. "grownups" is a parent or an admin.
AUDIENCE_LABELS = {
    "admin": "For admins",
    "parent": "For parents",
    "grownups": "For parents and admins",
}
DEPTH_LABELS = {"overview": "Overview", "howto": "How-to", "deep": "Deep dive"}

# Keyed by absolute path, with the file's mtime: a racing re-render is harmless.
_render_cache: dict[str, tuple[float, str, str]] = {}
_nav_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_text_cache: dict[str, tuple[float, str, list[str]]] = {}

# `?q=` is shown back to the reader, never acted on, so it is bounded rather than validated.
QUERY_MAX_CHARS = 80
TERMS_MAX = 6
TERM_MIN_CHARS = 2
SNIPPET_RADIUS = 90

_TAG = re.compile(r"<[^>]+>")
_HEADING = re.compile(r"<h([1-4])[^>]*>(.*?)</h\1>", re.S)

NOT_FOUND = (
    "<p>That page is not in the guide (yet). It may have moved, or the link may be old.</p>"
    '<p>Use the sections on the left, or <a href="{home}">start from the guide home</a>.</p>'
)


def _no_meta() -> dict[str, str]:
    return {"title": "", "audience": "", "depth": "", "audience_label": "", "depth_label": ""}


def _resolve(slug: str) -> Path | None:
    """The Markdown file for a slug, or None: missing, an underscore part (the guide's own
    machinery), or a path `safe_join` refuses (traversal)."""
    if any(part.startswith("_") for part in slug.split("/")):
        return None
    for relative in (f"{slug}.md", f"{slug}/index.md"):
        found = safe_join(str(CONTENT_DIR), relative)
        if found and Path(found).is_file():
            return Path(found)
    return None


def _render(path: Path) -> tuple[str, str]:
    """A page as (html, table of contents), cached by modification time."""
    mtime = path.stat().st_mtime
    cached = _render_cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1], cached[2]
    reader = markdown.Markdown(extensions=_MD_EXTENSIONS, extension_configs=_MD_EXTENSION_CONFIGS)
    html = reader.convert(path.read_text("utf-8"))
    toc = getattr(reader, "toc", "") or ""
    _render_cache[str(path)] = (mtime, html, toc)
    return html, toc


def _load_nav() -> list[dict[str, Any]]:
    """The sidebar tree from `_nav.json`, cached by modification time. Empty when it is missing
    or does not parse, which shows as a guide with no sidebar rather than an error page."""
    path = CONTENT_DIR / "_nav.json"
    if not path.is_file():
        return []
    mtime = path.stat().st_mtime
    cached = _nav_cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        tree = json.loads(path.read_text("utf-8")).get("tree", [])
    except (json.JSONDecodeError, OSError) as error:
        log.warning("the guide's _nav.json could not be read: %s", error)
        return []
    _nav_cache[str(path)] = (mtime, tree)
    return tree


def _flatten(nodes: list[dict[str, Any]], into: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """slug -> node, for titles, badges and see-also."""
    for node in nodes:
        into[node["slug"]] = node
        _flatten(node.get("children", []), into)
    return into


def _url(slug: str) -> str:
    return url_for("wiki.home") if slug in ("", "index") else url_for("wiki.page", page=slug)


def _decorate(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A copy of the tree with each node's address ready to use."""
    return [
        {
            "slug": node["slug"],
            "title": node["title"],
            "url": _url(node["slug"]),
            "children": _decorate(node.get("children", [])),
        }
        for node in nodes
    ]


def _title(slug: str, flat: dict[str, Any]) -> str:
    node = flat.get(slug)
    if node:
        return node["title"]
    return slug.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()


def _trail(slug: str) -> list[str]:
    """Each slug on the way down to this one, itself included: 'a/b' gives 'a', 'a/b'."""
    out, so_far = [], ""
    for part in slug.split("/"):
        so_far = part if not so_far else f"{so_far}/{part}"
        out.append(so_far)
    return out


def _crumbs(slug: str, flat: dict[str, Any]) -> list[dict[str, str]]:
    crumbs = [{"title": "Guide", "url": _url("index")}]
    if slug not in ("", "index"):
        crumbs += [{"title": _title(s, flat), "url": _url(s)} for s in _trail(slug)]
    return crumbs


def _open_branch(slug: str) -> set[str]:
    """The slug and every parent, so the sidebar opens the branch the reader is in."""
    return {"index"} if slug in ("", "index") else set(_trail(slug))


def _meta(slug: str, flat: dict[str, Any]) -> dict[str, str]:
    node = flat.get(slug) or {}
    audience, depth = node.get("audience", ""), node.get("depth", "")
    return {
        "title": _title(slug, flat),
        "audience": audience,
        "depth": depth,
        "audience_label": AUDIENCE_LABELS.get(audience, ""),
        "depth_label": DEPTH_LABELS.get(depth, ""),
    }


def _see_also(slugs: list[str] | None, flat: dict[str, Any]) -> list[dict[str, str]]:
    return [{"title": _title(s, flat), "url": _url(s)} for s in slugs or []]


def _frame(**context: Any) -> dict[str, Any]:
    """What every guide page shares: the sidebar, and the reader's place in it."""
    return {"nav_tree": _decorate(_load_nav()), "search_query": "", **context}


def _page_text(path: Path) -> tuple[str, list[str]]:
    """A page's plain text and its headings' text, cached by modification time."""
    mtime = path.stat().st_mtime
    cached = _text_cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1], cached[2]
    html, _ = _render(path)
    headings = [unescape(_TAG.sub(" ", m.group(2))).strip() for m in _HEADING.finditer(html)]
    text = re.sub(r"\s+", " ", unescape(_TAG.sub(" ", html))).strip()
    _text_cache[str(path)] = (mtime, text, headings)
    return text, headings


def _pages() -> list[tuple[str, Path]]:
    """Every served page as (slug, file), in a stable order. Underscored names are skipped."""
    found = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        relative = path.relative_to(CONTENT_DIR).with_suffix("")
        if any(part.startswith("_") for part in relative.parts):
            continue
        slug = "/".join(relative.parts)
        found.append((slug.removesuffix("/index"), path))
    return found


def _terms(query: str) -> list[str]:
    """The words worth looking for: lowercase, no repeats, at most a few."""
    out: list[str] = []
    for word in query.casefold().split():
        if len(word) >= TERM_MIN_CHARS and word not in out:
            out.append(word)
        if len(out) >= TERMS_MAX:
            break
    return out


def _snippet(text: str, terms: list[str]) -> Markup:
    """A word-aligned window around the earliest hit, each hit in <mark>."""
    low = text.casefold()
    hit, length = -1, 0
    for term in terms:
        at = low.find(term)
        if at != -1 and (hit == -1 or at < hit):
            hit, length = at, len(term)
    if hit == -1:  # only the title or a heading matched: open on the page's first words
        start, end = 0, min(len(text), 2 * SNIPPET_RADIUS)
    else:
        start = max(0, hit - SNIPPET_RADIUS)
        end = min(len(text), hit + length + SNIPPET_RADIUS)
    if start > 0 and (space := text.find(" ", start, end)) != -1:
        start = space + 1
    if end < len(text) and (space := text.rfind(" ", start, end)) > start:
        end = space
    window = text[start:end]
    # Longest term first, so "timezone" is marked whole when "time" is a term too.
    pattern = re.compile("|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)), re.I)
    parts, last = [], 0
    for found in pattern.finditer(window):
        parts += [escape(window[last : found.start()]), Markup("<mark>%s</mark>") % found.group(0)]
        last = found.end()
    parts.append(escape(window[last:]))
    return (
        (Markup("… ") if start > 0 else Markup(""))
        + Markup("").join(parts)
        + (Markup(" …") if end < len(text) else Markup(""))
    )


def _search(flat: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    """Every page that has all the terms, best first: a hit in the title counts most, then a
    heading, then the body."""
    scored: list[tuple[int, dict[str, Any]]] = []
    for slug, path in _pages():
        title = _title(slug, flat)
        text, headings = _page_text(path)
        low_title, low_text = title.casefold(), text.casefold()
        low_heads = [h.casefold() for h in headings]
        score = 0
        for term in terms:
            in_title = term in low_title
            in_heads = sum(1 for h in low_heads if term in h)
            in_body = low_text.count(term)
            if not (in_title or in_heads or in_body):
                score = 0
                break
            score += 12 * in_title + 4 * in_heads + min(in_body, 20)
        if score:
            meta = _meta(slug, flat)
            above = [_title(s, flat) for s in _trail(slug)[:-1]] if slug != "index" else []
            scored.append(
                (
                    score,
                    {
                        **meta,
                        "url": _url(slug),
                        "crumbs": above,
                        "snippet": _snippet(text, terms),
                    },
                )
            )
    scored.sort(key=lambda found: (-found[0], found[1]["title"].casefold()))
    return [found for _, found in scored]


def _serve(slug: str) -> Any:
    flat = _flatten(_load_nav(), {})
    path = _resolve(slug)
    if path is None:
        crumbs = [{"title": "Guide", "url": _url("index")}, {"title": "Not found", "url": ""}]
        return render_template(
            "wiki.html",
            **_frame(
                wiki_html=Markup(NOT_FOUND.format(home=_url("index"))),  # our own words, above
                wiki_toc="",
                breadcrumbs=crumbs,
                page_meta={**_no_meta(), "title": "Page not found"},
                current_slug=slug,
                active_slugs=set(),
                see_also=[],
            ),
        ), 404
    html, toc = _render(path)
    node = flat.get(slug) or {}
    return render_template(
        "wiki.html",
        **_frame(
            wiki_html=Markup(html),  # the guide's own pages, from disk: never anyone's words
            wiki_toc=Markup(toc),
            breadcrumbs=_crumbs(slug, flat),
            page_meta=_meta(slug, flat),
            current_slug=slug,
            active_slugs=_open_branch(slug),
            see_also=_see_also(node.get("see_also"), flat),
        ),
    )


@bp.get("/wiki")
def home() -> Any:
    return _serve("index")


@bp.get("/wiki/_search")
def search() -> Any:
    """The search box's results, drawn on the server so it works with scripts off. A fixed rule,
    so it wins over the page catch-all below."""
    flat = _flatten(_load_nav(), {})
    query = (request.args.get("q") or "").strip()[:QUERY_MAX_CHARS]
    terms = _terms(query)
    results = _search(flat, terms) if terms else []
    if not query:
        state, headline = "intro", ""
    elif not terms:
        state, headline = "short", ""
    elif not results:
        state, headline = "empty", f"Nothing in the guide matches “{query}”"
    else:
        many = len(results)
        state = "results"
        headline = f"1 page matches “{query}”" if many == 1 else f"{many} pages match “{query}”"
    crumbs = [{"title": "Guide", "url": _url("index")}, {"title": "Search", "url": ""}]
    return render_template(
        "wiki_search.html",
        **_frame(
            breadcrumbs=crumbs,
            page_meta={**_no_meta(), "title": "Search"},
            current_slug="_search",
            active_slugs=set(),
            see_also=[],
            search_query=query,
            search_state=state,
            search_headline=headline,
            results=results,
        ),
    )


@bp.get("/wiki/<path:page>")
def page(page: str) -> Any:
    return _serve(page.strip("/") or "index")
