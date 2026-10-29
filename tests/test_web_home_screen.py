"""The page kept on a phone's home screen: the manifest, the icons and the tags that point at them.

A phone asks for these without the page's cookie, so they are served before sign-in.
The icons are the brand's own (static/brand); these hold the manifest and the tags to them.

"""

import json
import re
import struct
import zlib
from pathlib import Path

from familydb.app import App
from familydb.store import db
from familydb.store import settings as settings_store
from familydb.web import create_app

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "familydb" / "web" / "static"
PASSWORD = "open sesame please"


def _client(settings, clock, **overrides):
    return create_app(App(settings.model_copy(update=overrides), clock)).test_client()


def _manifest(client) -> dict:
    return json.loads(client.get("/manifest.webmanifest").text)


def _png(data: bytes) -> tuple[int, int, int, bytes]:
    """A PNG's width, height, colour type and pixels (each row after its filter byte)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    header, pixels, at = b"", b"", 8
    while at < len(data):
        length, kind = struct.unpack(">I4s", data[at : at + 8])
        body = data[at + 8 : at + 8 + length]
        header = body if kind == b"IHDR" else header
        pixels += body if kind == b"IDAT" else b""
        at += 12 + length
    width, height, depth, colour = struct.unpack(">IIBB", header[:10])
    assert depth == 8
    return width, height, colour, zlib.decompress(pixels)


def _rows(width: int, height: int, colour: int, data: bytes) -> list[bytes]:
    """The pixels row by row, each row's PNG filter (none, sub, up, average, Paeth) undone."""
    bpp = {2: 3, 6: 4}[colour]
    stride, at, rows, above = width * bpp, 0, [], bytearray(width * bpp)
    for _ in range(height):
        kind, row = data[at], bytearray(data[at + 1 : at + 1 + stride])
        at += 1 + stride
        for i in range(stride):
            a, b = (row[i - bpp] if i >= bpp else 0), above[i]
            c = above[i - bpp] if i >= bpp else 0
            if kind == 1:
                row[i] = (row[i] + a) & 255
            elif kind == 2:
                row[i] = (row[i] + b) & 255
            elif kind == 3:
                row[i] = (row[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(row))
        above = row
    return rows


def test_a_phone_reads_the_manifest_before_signing_in(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD, web_title="The Tates")
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response.mimetype == "application/manifest+json"
    manifest = json.loads(response.text)
    assert manifest["name"] == manifest["short_name"] == "The Tates"
    assert manifest["display"] == "standalone"  # without the browser's bars
    assert manifest["start_url"] == manifest["scope"] == manifest["id"] == "/"
    assert client.get("/ideas").status_code == 302  # the manifest is open, the pages are not


def test_the_manifest_follows_the_title_the_family_gives_it(settings, clock, conn) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    assert _manifest(client)["name"] == "FamilyDB"
    with db.transaction(conn):
        settings_store.set_many(conn, {"web_title": "The Tate family"})
    assert _manifest(client)["name"] == "The Tate family"


def test_every_icon_a_phone_is_pointed_at_is_there(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    listed = _manifest(client)["icons"]
    assert all(icon["type"] == "image/png" for icon in listed)
    assert any(icon.get("purpose") == "maskable" for icon in listed)  # for Android's round masks
    wanted = [(icon["src"], icon["sizes"]) for icon in listed]
    touch = re.search(r'rel="apple-touch-icon" href="([^"]+)"', client.get("/login").text)
    wanted.append((touch.group(1), "180x180"))  # the one an iPhone asks for
    for src, sizes in wanted:
        response = client.get(src)  # before signing in, as a phone asks
        assert response.status_code == 200 and response.mimetype == "image/png"
        width, height, colour, _ = _png(response.data)
        assert f"{width}x{height}" == sizes
        assert colour == 2  # RGB with nothing transparent, which a phone would fill with black


def test_an_iphone_finds_the_icon_where_it_looks_on_its_own(settings, clock) -> None:
    """Safari asks for /apple-touch-icon.png (and -precomposed) by itself when it did not take the
    page's link to it; sent to sign in instead, it drew the first letter of the title."""
    client = _client(settings, clock, web_password=PASSWORD)
    icon = (STATIC / "brand" / "apple-touch-icon.png").read_bytes()
    for path in ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
        response = client.get(path)  # before signing in, as a phone asks
        assert response.status_code == 200 and response.mimetype == "image/png", path
        assert response.data == icon
        assert "no-store" not in response.headers["Cache-Control"]  # a phone may keep it


def test_the_maskable_icon_keeps_the_mark_inside_the_mask() -> None:
    """Android cuts a maskable icon to a circle (or rounder): nothing lit outside the inner 80 %
    (W3C's safe zone), only the ground and its glow."""
    width, height, colour, data = _png((STATIC / "brand" / "icon-maskable-512.png").read_bytes())
    assert (width, height, colour) == (512, 512, 2)
    rows, safe = _rows(width, height, colour, data), 0.4 * width
    lit_outside = [
        (x, y)
        for y, row in enumerate(rows)
        for x in range(width)
        if row[x * 3 + 1] > 128  # the green of the phosphor
        and ((x + 0.5 - 256) ** 2 + (y + 0.5 - 256) ** 2) ** 0.5 > safe
    ]
    assert not lit_outside, lit_outside[:5]
    assert any(row[256 * 3 + 1] > 128 for row in rows)  # and the mark is there to keep inside


def test_every_page_points_a_phone_at_the_manifest_and_the_icon(
    settings, clock, conn, family
) -> None:
    client = _client(settings, clock, web_password=PASSWORD, web_title="The Tates")
    login = client.get("/login").text
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    ideas = client.get("/ideas").text
    for page in (login, ideas):
        assert '<link rel="manifest" href="/manifest.webmanifest" />' in page
        assert re.search(
            r'<link rel="apple-touch-icon" href="/static/brand/apple-touch-icon\.png'
            r'(?:\?v=\w+)?" />',
            page,
        )
        assert '<meta name="apple-mobile-web-app-title" content="The Tates" />' in page
        assert '<meta name="apple-mobile-web-app-capable" content="yes" />' in page


def test_the_manifest_s_colours_are_the_icon_s() -> None:
    """The home screen opens in one colour from the icon to the manifest's splash."""
    from familydb.web.routes import ICON_GROUND

    width, height, colour, data = _png((STATIC / "brand" / "icon-512.png").read_bytes())
    rows = _rows(width, height, colour, data)
    corners = {rows[0][:3], rows[0][-3:], rows[-1][:3], rows[-1][-3:]}
    assert corners == {bytes.fromhex(ICON_GROUND[1:])}


def test_the_manifest_carries_the_icon_s_colour(settings, clock) -> None:
    from familydb.web.routes import ICON_GROUND

    manifest = _manifest(_client(settings, clock, web_password=PASSWORD))
    assert manifest["theme_color"] == manifest["background_color"] == ICON_GROUND
