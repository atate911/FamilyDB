"""The example household's pages as static HTML (examples/__init__.py).

Each person signs in to the real page through Flask's test client and every page they can reach
from where they start is fetched, as far as a few clicks go, then written as a file with its links
pointing at the other files. What the example does not carry (the settings, the guide, editing by
hand) is linked to a page that says so. Forms are kept but answered in the page by `demo.js`,
which says what they would have done; nothing is sent anywhere. The product's look attribute is
renamed in the copies (`data-theme` to `data-look`), so a viewer that sets its own `data-theme`
on the page cannot unset the look.
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
import tempfile
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from flask.testing import FlaskClient

from examples import household
from familydb.web import create_app

STATIC = Path(__file__).resolve().parents[1] / "src" / "familydb" / "web" / "static"
HERE = Path(__file__).resolve().parent
# What the example leaves out: the back office's forms and the guide, editing by hand, downloads.
SKIP_PREFIXES = (
    "/static/",
    "/logout",
    "/export/",
    "/sw.js",
    "/manifest",
    "/healthz",
    "/api/",
    "/wiki",
    "/settings",
    "/setup",
    "/family",
    "/status/activity",
    "/look",
    "/you",
    "/ideas/new",
    "/tasks/new",
    "/memory/",
    "/plans/new",
)
SKIP_SUFFIXES = ("/edit",)
NOT_HERE = "not-here.html"


@dataclass(frozen=True)
class Person:
    """Who the example is drawn for, where they start, and how far it follows their links."""

    key: str
    title: str
    line: str
    who: str | None
    start: tuple[str, ...]
    depth: int
    most: int
    empty: bool = False
    shared: bool = False


PEOPLE = (
    Person(
        key="sam",
        title="Sam, who runs it",
        line="Sam, an admin",
        who="Sam",
        start=(
            "/",
            "/about",
            "/eat",
            "/do",
            "/week",
            "/kids",
            "/soon",
            "/lists",
            "/did",
            "/chat",
            "/more",
            "/status",
            "/memory",
            "/tasks",
            "/plans/month",
        ),
        depth=2,
        most=170,
    ),
    Person(
        key="maya",
        title="Maya, eleven",
        line="Maya, 11",
        who="Maya",
        start=("/", "/kids", "/week", "/do", "/more"),
        depth=3,
        most=80,
    ),
    Person(
        key="board",
        title="The kitchen board",
        line="The kitchen tablet",
        who=None,
        start=("/board",),
        depth=1,
        most=40,
        shared=True,
    ),
    Person(
        key="first-day",
        title="The first day",
        line="A new install",
        who="Sam",
        start=("/", "/about", "/eat", "/do", "/week", "/soon", "/lists", "/did", "/more"),
        depth=0,
        most=14,
        empty=True,
    ),
)

# What each kind of form would have done, said in the example instead of doing it.
DOES = (
    ("/chat", "send this to Vera, and her answer would come back under the box"),
    ("/done", "tick it off, with Undo"),
    ("/reopen", "open it again"),
    ("/snooze", "snooze the reminder"),
    ("/lists/change", "change the list"),
    ("/outcome", "record how it went"),
    ("/answer", "answer her, and she would be told in her own conversation"),
    ("/ask", "ask a parent"),
    ("/status", "change the idea"),
    ("/lookup", "look it up on the next run"),
    ("/ideas/new", "save it as an idea"),
    ("/plans/new", "put it on the calendar"),
    ("/move", "move the plan"),
    ("/cancel", "take the plan off the calendar"),
    ("/later", "put the pitch off for a week on this device"),
    ("/good", "remember what made it good"),
    ("/undo", "take the change back"),
    ("/wish", "change the list"),
    ("/memory", "remember or forget it"),
    ("/mine", "make it yours: I'll handle it"),
    ("/unpin", "take her reply off your pinned ones"),
    ("/pin", "keep her reply at hand, pinned beside the box and at the top of Chat"),
)


@dataclass
class Site:
    person: Person
    pages: dict[str, str] = field(default_factory=dict)  # address -> page
    names: dict[str, str] = field(default_factory=dict)  # address -> file


def file_for(address: str, taken: Iterable[str] = ()) -> str:
    """The file an address is written to: / is index.html, /idea/12 idea-12.html, /do?kind=outing
    do--kind-outing.html; a long or clashing one is shortened with a hash."""
    path, _, query = address.partition("?")
    base = "index" if path == "/" else path.strip("/").replace("/", "-")
    if query:
        base += "--" + re.sub(r"[^A-Za-z0-9]+", "-", unquote(query)).strip("-")
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "page"
    if len(base) > 60 or f"{base}.html" in taken:
        base = f"{base[:48]}-{hashlib.sha1(address.encode()).hexdigest()[:8]}"
    return f"{base}.html"


def _wanted(address: str) -> bool:
    path = address.split("?", 1)[0]
    if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    return not any(path.endswith(suffix) for suffix in SKIP_SUFFIXES)


def _links(page: str) -> list[str]:
    found = []
    for raw in re.findall(r'href="([^"]+)"', page):
        address = html.unescape(raw).split("#", 1)[0]
        if address.startswith("/") and not address.startswith("//") and address:
            found.append(address)
    return found


def _signed_in(person: Person, folder: Path) -> tuple[FlaskClient, household.Family | None]:
    app, family = household.build(folder, empty=person.empty, shared=person.shared)
    client = create_app(app).test_client()
    if person.who is None:
        data = {"password": app.settings.web_password or ""}
    else:
        data = {"name": person.who, "password": household.PASSWORDS[person.who]}
    answered = client.post("/login", data=data)
    if answered.status_code != 302:
        raise RuntimeError(f"{person.key} could not sign in to the example")
    return client, family if isinstance(family, household.Family) else None


def crawl(person: Person, folder: Path) -> Site:
    """Every page this person reaches from where they start, as far as `depth` clicks."""
    client, family = _signed_in(person, folder)
    site = Site(person)
    starts = list(person.start)
    if family is not None and person.key == "sam":
        # Her reply over a page, and a receipt under the box, as a message would leave them.
        starts += [f"/eat?asked={family.reply_on_eat}", f"/do?asked={family.receipt_on_do}"]
    queue = deque((address, 0) for address in starts)
    seen = set(starts)
    while queue and len(site.pages) < person.most:
        address, depth = queue.popleft()
        answer = client.get(address)
        if answer.status_code != 200 or not answer.content_type.startswith("text/html"):
            continue
        page = answer.get_data(as_text=True)
        site.pages[address] = page
        site.names[address] = file_for(address, site.names.values())
        if depth >= person.depth:
            continue
        for link in _links(page):
            if link not in seen and _wanted(link):
                seen.add(link)
                queue.append((link, depth + 1))
    return site


def _does(action: str) -> str:
    for part, words in DOES:
        if part in action:
            return f"In the example nothing is saved. On your FamilyDB this would {words}."
    return "In the example nothing is saved or sent."


def rewrite(page: str, site: Site, address: str) -> str:
    """One page as a file of the example: its links to the other files, the static files from
    the shared folder, its forms answered by demo.js, and the example's bar along its top."""

    def link(found: re.Match[str]) -> str:
        attribute, raw = found.group(1), found.group(2)
        target = html.unescape(raw)
        if target.startswith("/static/"):
            name, _, fragment = target[len("/static/") :].partition("#")
            name = name.split("?", 1)[0]
            return f'{attribute}="../static/{name}{"#" + fragment if fragment else ""}"'
        if not target.startswith("/") or target.startswith("//"):
            return found.group(0)
        bare, _, fragment = target.partition("#")
        name = site.names.get(bare) or (NOT_HERE if bare else site.names.get(address, ""))
        return f'{attribute}="{html.escape(name)}{"#" + fragment if fragment else ""}"'

    page = re.sub(r'(href|src)="([^"]*)"', link, page)

    def form(found: re.Match[str]) -> str:
        tag = found.group(0)
        action = re.search(r'action="([^"]*)"', tag)
        if 'method="get"' in tag:
            said = "Searching works on your own FamilyDB. Here, try the chips."
        else:
            said = html.escape(_does(html.unescape(action.group(1)) if action else ""))
        tag = re.sub(r'\saction="[^"]*"', ' action="#"', tag)
        return tag[:-1] + f' data-demo="{said}">'

    page = re.sub(r"<form\b[^>]*>", form, page)
    page = re.sub(r'\sdata-find="[^"]*"', "", page)
    page = re.sub(r'\sdata-refresh="[^"]*"', "", page)
    page = re.sub(r'<link rel="manifest"[^>]*>\s*', "", page)
    page = re.sub(r'<meta http-equiv="refresh"[^>]*>', "", page)
    page = page.replace("data-theme=", "data-look=")
    bar = (
        '<div class="demo-bar" role="note"><span class="demo-bar__what">Example</span>'
        f"<span>{html.escape(site.person.line)} · Fri 16 Oct 2026, 5:02 pm</span>"
        '<a href="../index.html">All examples</a></div>'
    )
    page = re.sub(r"(<body\b[^>]*>)", lambda m: m.group(1) + bar, page, count=1)
    page = page.replace("</head>", '<link rel="stylesheet" href="../demo/demo.css" />\n</head>', 1)
    return page.replace("</body>", '<script src="../demo/demo.js" defer></script>\n</body>', 1)


def _not_here(person: Person) -> str:
    return f"""<!doctype html>
<html lang="en-US"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>Not in the example</title>
<link rel="stylesheet" href="../demo/demo.css" /></head>
<body class="demo-page"><main class="demo-not-here">
<p class="demo-kicker">{html.escape(person.title)}</p>
<h1>That page is not in the example</h1>
<p>The example carries the pages the family uses day to day. The settings, the guide, the family
list, editing by hand and the downloads are on your own FamilyDB once it is running.</p>
<p><a href="index.html">Back to Now</a> · <a href="../index.html">All the examples</a></p>
</main></body></html>
"""


def _static_used(pages: Iterable[str]) -> set[str]:
    used: set[str] = set()
    for page in pages:
        used.update(re.findall(r'"\.\./static/([^"#?]+)', page))
    for sheet in [name for name in used if name.endswith(".css")]:
        text = (STATIC / sheet).read_text("utf-8")
        for found in re.findall(r'url\("?([^")]+)"?\)', text):
            if not found.startswith(("data:", "http", "#")):
                used.add(str((Path(sheet).parent / found).as_posix()))
    return used


def export(
    out: Path, people: Iterable[Person] = PEOPLE, *, most: int | None = None
) -> dict[str, int]:
    """Write every person's example into `out`, with the static files they use and the start
    page. Returns how many pages each got. `most` caps each person, for a quick run."""
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, str]] = {}
    everything: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        for person in people:
            if most is not None:
                person = Person(**{**person.__dict__, "most": min(person.most, most)})
            site = crawl(person, Path(scratch) / person.key)
            folder = out / person.key
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True)
            for address, page in site.pages.items():
                text = rewrite(page, site, address)
                everything.append(text)
                (folder / site.names[address]).write_text(text, "utf-8")
            (folder / NOT_HERE).write_text(_not_here(person), "utf-8")
            written[person.key] = dict(site.names)
    for name in sorted(_static_used(everything)):
        source = STATIC / name
        if not source.is_file():
            continue
        target = out / "static" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix in (".css", ".html", ".js"):
            text = source.read_text("utf-8")
            target.write_text(text.replace("[data-theme", "[data-look"), "utf-8")
        else:
            shutil.copyfile(source, target)
    demo = out / "demo"
    demo.mkdir(exist_ok=True)
    for name in ("demo.css", "demo.js"):
        shutil.copyfile(HERE / name, demo / name)
    write_start(out, written)
    return {key: len(names) for key, names in written.items()}


def write_start(out: Path, written: dict[str, dict[str, str]]) -> None:
    """The page the examples open on, as a whole document (index.html, for a browser) and as the
    body alone (start.html, for a host that wraps a page in its own document)."""
    from examples import start

    pictures = {key for key in written if (out / "pictures" / f"{key}.png").exists()}
    (out / "index.html").write_text(start.page(written, pictures), "utf-8")
    (out / "start.html").write_text(start.page(written, pictures, whole=False), "utf-8")
