"""Build the web page's icon sprite and favicon.

The icons are Lucide's (https://lucide.dev, ISC licence, see static/LICENSE-icons.txt), taken
from one pinned release so they never shift under the page, plus the page's own mark: a little
monitor with a smile. Each becomes a <symbol> in static/icons.svg, drawn in the colour of the
words around it. Add a name to ICONS and run this again; never edit the .svg files by hand.

    uv run python scripts/icons.py

It downloads the pinned release from the npm registry the first time and keeps it in the
system's temporary folder.
"""

from __future__ import annotations

import io
import re
import tarfile
import tempfile
import urllib.request
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "familydb" / "web" / "static"
LUCIDE = "1.48.0"
TARBALL = f"https://registry.npmjs.org/lucide-static/-/lucide-static-{LUCIDE}.tgz"
STROKE = "1.75"
GREEN = "#6dff9c"
INK = "#0b0e0d"

# The page's name for an icon, and Lucide's.
ICONS = {
    "activity": "bike",
    "bell": "bell",
    "check": "check",
    "chat": "message-circle",
    "clock": "clock",
    "coin": "coins",
    "day_trip": "car",
    "edit": "pencil",
    "event": "party-popper",
    "family": "users",
    "grid": "calendar",
    "heart": "heart",
    "home": "house",
    "hourglass": "hourglass",
    "idea": "lightbulb",
    "key": "key-round",
    "left": "arrow-left",
    "link": "external-link",
    "list": "list",
    "locate": "locate-fixed",
    "outing": "trees",
    "person_plus": "user-plus",
    "pin": "map-pin",
    "plans": "calendar-days",
    "plug": "plug",
    "plus": "plus",
    "restaurant": "utensils",
    "right": "arrow-right",
    "search": "search",
    "seasonal": "leaf",
    "send": "send-horizontal",
    "settings": "settings",
    "show": "ticket",
    "signout": "log-out",
    "spark": "sparkle",
    "sparkles": "sparkles",
    "star": "star",
    "status": "activity",
    "sun": "sun",
    "todo": "list-checks",
    "trip": "luggage",
    "undo": "undo-2",
    "user": "user",
    "warning": "triangle-alert",
    "x": "x",
}

# The mark: a monitor with two eyes and a smile, on the same 24 grid and stroke as the rest.
MARK = (
    '<rect x="2.5" y="3" width="19" height="13.5" rx="3.5"/>'
    '<path d="M12 16.5V21"/><path d="M8.5 21h7"/>'
    '<path d="M9 8.25v1.25"/><path d="M15 8.25v1.25"/>'
    '<path d="M9 12.25c1.7 1.35 4.3 1.35 6 0"/>'
)


def lucide_folder() -> Path:
    """The pinned release, unpacked once into the temporary folder."""
    folder = Path(tempfile.gettempdir()) / f"lucide-static-{LUCIDE}"
    if not (folder / "package" / "icons").is_dir():
        with urllib.request.urlopen(TARBALL, timeout=60) as response:
            data = response.read()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(folder, filter="data")
    return folder / "package"


def shapes(svg: str) -> str:
    """What is inside an icon's <svg>, on one line."""
    inner = svg[svg.index(">", svg.index("<svg")) + 1 : svg.rindex("</svg>")]
    return re.sub(r"\s+", " ", inner).replace("> <", "><").replace(" />", "/>").strip()


def sprite(package: Path) -> str:
    symbols = [f'<symbol id="i-mark" viewBox="0 0 24 24"><g>{MARK}</g></symbol>']
    for name, source in sorted(ICONS.items()):
        drawn = shapes((package / "icons" / f"{source}.svg").read_text())
        symbols.append(f'<symbol id="i-{name}" viewBox="0 0 24 24"><g>{drawn}</g></symbol>')
    return (
        f"<!-- Lucide {LUCIDE} (ISC), see LICENSE-icons.txt. Built by scripts/icons.py. -->\n"
        '<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" '
        f'stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round">\n'
        + "\n".join(symbols)
        + "\n</svg>\n"
    )


def favicon() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        f'<rect width="32" height="32" rx="8" fill="{INK}"/>'
        f'<g transform="translate(4 4)" fill="none" stroke="{GREEN}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{MARK}</g></svg>\n'
    )


def main() -> None:
    package = lucide_folder()
    outputs = {
        STATIC / "icons.svg": sprite(package),
        STATIC / "favicon.svg": favicon(),
        STATIC / "LICENSE-icons.txt": (package / "LICENSE").read_text(),
    }
    for path, text in outputs.items():
        path.write_text(text)
        print(f"{path.relative_to(STATIC.parents[3])}: {len(text):,} bytes")


if __name__ == "__main__":
    main()
