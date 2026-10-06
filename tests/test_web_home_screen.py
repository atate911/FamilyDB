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

    _, _, _, pixels = _png((STATIC / "brand" / "icon-512.png").read_bytes())
    assert pixels[1:4] == bytes.fromhex(ICON_GROUND[1:])


def test_the_manifest_carries_the_icon_s_colour(settings, clock) -> None:
    from familydb.web.routes import ICON_GROUND

    manifest = _manifest(_client(settings, clock, web_password=PASSWORD))
    assert manifest["theme_color"] == manifest["background_color"] == ICON_GROUND
