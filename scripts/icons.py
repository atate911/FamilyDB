"""Build the web page's icon sprite, its favicon and its home-screen icons.

The icons are Lucide's (https://lucide.dev, ISC licence, see static/LICENSE-icons.txt), taken
from one pinned release so they never shift under the page, plus the page's own mark: a little
monitor with a smile. Each becomes a <symbol> in static/icons.svg, drawn in the colour of the
words around it. The mark is also the favicon, and the icon a phone shows for the page kept on
its home screen, which has to be a PNG: this draws those too, from the same shapes. Add a name to
ICONS and run this again; never edit the .svg or .png files by hand.

    uv run python scripts/icons.py

It downloads the pinned release from the npm registry the first time and keeps it in the
system's temporary folder.
"""

from __future__ import annotations

import io
import itertools
import math
import re
import struct
import tarfile
import tempfile
import urllib.request
import zlib
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


# The home-screen icons, by file and side in pixels: iPhone's, and the two a manifest names. The
# mark is green on the page's charcoal, filling the square, since a phone rounds the corners
# itself and shows black through anything transparent. The mark's 24 grid takes APP_MARK of the
# side, which leaves the margin Android's round masks cut into.
APP_ICONS = {"apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512}
APP_MARK = 0.625
MARK_STROKE = 2  # on the 24 grid, as the favicon draws it
# How many numbers each kind of path command takes.
ARGUMENTS = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6}


def _rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def _rounded_rect(x: float, y: float, w: float, h: float, r: float) -> list[tuple[float, float]]:
    """The outline of a rounded rectangle, clockwise from the top edge, as a closed polyline."""
    points = []
    corners = ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90))
    for cx, cy, start in ((x + r, y + r, 180), *corners):
        for step in range(9):  # a quarter circle in eight pieces
            angle = math.radians(start + step * 90 / 8)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return [*points, points[0]]


def _path(d: str) -> list[tuple[float, float]]:
    """A path of the kinds the mark uses (M, L, H, V and C, relative or not) as a polyline."""
    tokens = re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)", d)
    points: list[tuple[float, float]] = []
    x = y = 0.0
    command = ""
    while tokens:
        if tokens[0].isalpha():
            command = tokens.pop(0)
        relative = command.islower()
        take = [float(tokens.pop(0)) for _ in range(ARGUMENTS[command.lower()])]
        if command in "Hh":
            x = take[0] + (x if relative else 0)
        elif command in "Vv":
            y = take[0] + (y if relative else 0)
        elif command in "Cc":
            dx, dy = (x, y) if relative else (0.0, 0.0)
            (x1, y1), (x2, y2), (x3, y3) = (
                (take[i] + dx, take[i + 1] + dy) for i in range(0, 6, 2)
            )
            for step in range(1, 25):  # the curve in twenty-four pieces
                t = step / 24
                u = 1 - t
                points.append(
                    (
                        u**3 * x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
                        u**3 * y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3,
                    )
                )
            x, y = x3, y3
            continue
        else:
            x, y = (take[0] + x, take[1] + y) if relative else (take[0], take[1])
        points.append((x, y))
    return points


def _strokes(shapes: str) -> list[tuple[float, float, float, float]]:
    """Every straight piece of the mark's outlines, on its 24 grid."""
    lines = []
    for attributes in re.findall(r"<rect ([^>]*)/>", shapes):
        a = {k: float(v) for k, v in re.findall(r'(\w+)="([^"]+)"', attributes)}
        lines.append(_rounded_rect(a["x"], a["y"], a["width"], a["height"], a.get("rx", 0.0)))
    lines += [_path(d) for d in re.findall(r'<path d="([^"]+)"', shapes)]
    return [(*a, *b) for line in lines for a, b in itertools.pairwise(line)]


def app_icon(size: int) -> bytes:
    """The mark as an opaque, square PNG of this many pixels a side.

    Each pixel takes its distance to the nearest stroke, which draws the round caps and joins
    the mark asks for, and an edge a pixel wide keeps it smooth. The same size always gives the
    same pixels, so the files can be checked against this.
    """
    scale = size * APP_MARK / 24
    offset = size * (1 - APP_MARK) / 2
    half = MARK_STROKE / 2 * scale
    near = [[math.inf] * size for _ in range(size)]
    for x1, y1, x2, y2 in _strokes(MARK):
        ax, ay, bx, by = (offset + v * scale for v in (x1, y1, x2, y2))
        length = (bx - ax) ** 2 + (by - ay) ** 2
        left, right = int(min(ax, bx) - half - 1), int(max(ax, bx) + half + 2)
        top, bottom = int(min(ay, by) - half - 1), int(max(ay, by) + half + 2)
        for py in range(max(top, 0), min(bottom, size)):
            row = near[py]
            for px in range(max(left, 0), min(right, size)):
                cx, cy = px + 0.5, py + 0.5
                t = ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length if length else 0.0
                t = min(1.0, max(0.0, t))
                distance = math.hypot(cx - (ax + t * (bx - ax)), cy - (ay + t * (by - ay)))
                if distance < row[px]:
                    row[px] = distance
    ink, green = _rgb(INK), _rgb(GREEN)
    pixels = bytearray()
    for row in near:
        pixels.append(0)  # no filter on this row
        for distance in row:
            cover = min(1.0, max(0.0, half - distance + 0.5))
            pixels += bytes(round(i + (g - i) * cover) for i, g in zip(ink, green, strict=True))

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB, no transparency
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
        + chunk(b"IEND", b"")
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
    for name, size in APP_ICONS.items():
        data = app_icon(size)
        (STATIC / name).write_bytes(data)
        print(f"{(STATIC / name).relative_to(STATIC.parents[3])}: {len(data):,} bytes")


if __name__ == "__main__":
    main()
