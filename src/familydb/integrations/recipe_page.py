"""A recipe link the family pasted, read by this server with no model (docs/RECIPES.md): nearly
every recipe site carries a schema.org `Recipe` in JSON-LD, which gives the name, ingredients,
steps, times and yield as data. A page without one is left to the paid lookup.

The address came from a person's message, so it is treated as the calendar reader treats a feed's
(ical.py): only http and https, never a host that resolves to this machine or the home network,
every redirect checked the same way, nothing of the family in the request, HTML only and no more
than a page could be.
"""

from __future__ import annotations

import contextlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import urlsplit

from familydb.integrations import address

TIMEOUT = 20
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "familydb/0.1 (self-hosted family planning bot)"
MOST_INGREDIENTS = 40
MOST_STEPS = 30
MOST_STEP = 300
MOST_TAGS = 5
# A recipe taking more than a day is not one a page means.
LONGEST = 24 * 60


class PageError(Exception):
    """A recipe page could not be fetched; the message says why, in a few words."""


class PageAPI(Protocol):
    def read(self, url: str) -> str: ...


def check_address(url: str) -> None:
    """Refuse an address this server should not read. Raises PageError saying why."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PageError("not a web address")
    if not address.is_public(parts.hostname):
        raise PageError("not a public address")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        check_address(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RecipePages:
    """Pages read over HTTP(S), once each."""

    def read(self, url: str) -> str:
        check_address(url)
        opener = urllib.request.build_opener(_CheckedRedirects)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        try:
            with opener.open(request, timeout=TIMEOUT) as response:
                kind = response.headers.get_content_type()
                if kind not in ("text/html", "application/xhtml+xml"):
                    raise PageError(f"not a web page ({kind})")
                body = response.read(MAX_BYTES + 1)
                charset = response.headers.get_content_charset() or "utf-8"
        except urllib.error.HTTPError as exc:
            raise PageError(f"the site answered {exc.code}") from exc
        except PageError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PageError("the site could not be reached") from exc
        # Past the cap, what was read is still read: the recipe block is usually near the top.
        return body[:MAX_BYTES].decode(charset, errors="replace")


class _Scripts(HTMLParser):
    """The text of every `<script type="application/ld+json">`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []
        self._inside = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            kind = dict(attrs).get("type") or ""
            self._inside = kind.split(";")[0].strip().casefold() == "application/ld+json"
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._inside:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside:
            self.found.append("".join(self._parts))
            self._inside = False


def blocks(html: str) -> list[Any]:
    """Every JSON-LD block on the page that is JSON; one that is not is passed over."""
    reader = _Scripts()
    with contextlib.suppress(Exception):  # a page broken past reading: whatever was found
        reader.feed(html)
    found = []
    for text in reader.found:
        try:
            found.append(json.loads(text.strip()))
        except (ValueError, TypeError):
            continue
    return found


def _is_recipe(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(isinstance(one, str) and one.rsplit("/", 1)[-1] == "Recipe" for one in kinds)


def find_recipe(found: Any, depth: int = 0) -> dict[str, Any] | None:
    """The first `Recipe` in a block: the block itself, in a list, or in `@graph`."""
    if depth > 4:
        return None
    if _is_recipe(found):
        return found
    if isinstance(found, list):
        for one in found:
            recipe = find_recipe(one, depth + 1)
            if recipe is not None:
                return recipe
    if isinstance(found, dict):
        for key in ("@graph", "mainEntity", "mainEntityOfPage", "itemListElement", "item"):
            if key in found:
                recipe = find_recipe(found[key], depth + 1)
                if recipe is not None:
                    return recipe
    return None


DURATION = re.compile(
    r"^P(?:(?P<d>\d+(?:\.\d+)?)D)?(?:T(?:(?P<h>\d+(?:\.\d+)?)H)?(?:(?P<m>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<s>\d+(?:\.\d+)?)S)?)?$",
    re.IGNORECASE,
)


def minutes(value: Any) -> int | None:
    """An ISO 8601 duration as minutes ("PT1H30M" is 90); None for nothing, nonsense or over a
    day."""
    if not isinstance(value, str):
        return None
    found = DURATION.match(value.strip())
    if not found or not any(found.groupdict().values()):
        return None
    days, hours, mins, secs = (float(found.group(k) or 0) for k in "dhms")
    total = round(days * 1440 + hours * 60 + mins + secs / 60)
    return total if 0 < total <= LONGEST else None


def first_number(value: Any) -> int | None:
    """How many it serves, from "4", "4 servings", ["4", "4 servings"] or 4."""
    if isinstance(value, list):
        for one in value:
            number = first_number(one)
            if number is not None:
                return number
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value) if 0 < value <= 100 else None
    if isinstance(value, str):
        found = re.search(r"\d+", value)
        if found and 0 < int(found.group()) <= 100:
            return int(found.group())
    return None


TAGS = re.compile(r"<[^>]+>")


def plain(text: Any) -> str:
    """Words without markup or runs of space."""
    if not isinstance(text, str):
        return ""
    words = " ".join(unescape(TAGS.sub(" ", text)).split())
    return re.sub(r"\s+([.,;:!?])", r"\1", words)


def _cut(text: str) -> str:
    return text if len(text) <= MOST_STEP else text[: MOST_STEP - 1].rstrip() + "…"


def steps_of(value: Any) -> list[str]:
    """The steps in order: a string, a list of strings, `HowToStep`s, or `HowToSection`s of
    them, flattened."""
    found: list[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 4 or len(found) >= MOST_STEPS:
            return
        if isinstance(node, str):
            for line in re.split(r"\n+|(?<=\.)\s{2,}", node):
                text = plain(line)
                if text:
                    found.append(_cut(text))
            return
        if isinstance(node, list):
            for one in node:
                walk(one, depth + 1)
            return
        if isinstance(node, dict):
            if "itemListElement" in node:
                walk(node["itemListElement"], depth + 1)
                return
            text = plain(node.get("text") or node.get("name") or "")
            if text:
                found.append(_cut(text))

    walk(value)
    return found[:MOST_STEPS]


def ingredients_of(value: Any) -> list[str]:
    lines = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    found = [plain(line) for line in lines if isinstance(line, str)]
    return [line[:MOST_STEP] for line in found if line][:MOST_INGREDIENTS]


def tags_of(*values: Any) -> list[str]:
    found: list[str] = []
    for value in values:
        parts = value if isinstance(value, list) else str(value or "").split(",")
        for part in parts:
            text = plain(part).casefold()
            if text and len(text) <= 30 and text not in found:
                found.append(text)
    return found[:MOST_TAGS]


@dataclass
class ReadRecipe:
    """What a page's recipe block says, and only that."""

    name: str | None = None
    ingredients: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    active_minutes: int | None = None
    total_minutes: int | None = None
    serves: int | None = None
    tags: list[str] = field(default_factory=list)


def recipe_in(html: str) -> ReadRecipe | None:
    """The first recipe block on the page, read; None when it has none worth keeping."""
    for block in blocks(html):
        node = find_recipe(block)
        if node is None:
            continue
        prep, cook, total = (minutes(node.get(k)) for k in ("prepTime", "cookTime", "totalTime"))
        if total is None and (prep or cook):
            total = (prep or 0) + (cook or 0)
        found = ReadRecipe(
            name=plain(node.get("name")) or None,
            ingredients=ingredients_of(node.get("recipeIngredient") or node.get("ingredients")),
            steps=steps_of(node.get("recipeInstructions")),
            active_minutes=prep,
            total_minutes=total,
            serves=first_number(node.get("recipeYield")),
            tags=tags_of(node.get("recipeCuisine"), node.get("keywords")),
        )
        if found.ingredients or found.steps:
            return found
    return None


def read(url: str, pages: PageAPI) -> ReadRecipe | None:
    """The recipe at a link, or None when its page has no recipe block. Raises PageError when
    the page could not be read."""
    return recipe_in(pages.read(url))
