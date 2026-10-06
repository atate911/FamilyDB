"""The page kept on a phone's home screen: the manifest, the icons and the tags that point at them.

A phone asks for these without the page's cookie, so they are served before sign-in.
scripts/icons.py draws the icons; these hold the files to it.

"""

import importlib.util
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


def _icons_script():
    spec = importlib.util.spec_from_file_location("icons_script", ROOT / "scripts" / "icons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            r'<link rel="apple-touch-icon" href="/static/apple-touch-icon.png\?v=\w+" />', page
        )
        assert '<meta name="apple-mobile-web-app-title" content="The Tates" />' in page
        assert '<meta name="apple-mobile-web-app-capable" content="yes" />' in page


def test_the_app_s_colours_are_the_page_s(settings, clock) -> None:
    """The home screen opens charcoal, from the icon to the manifest's splash, and Phosphor, the
    look that is charcoal, wears the same: the manifest's colour, the browser bar's and the page's
    own. (The page's default is Kitchen Table, held to its CSS in test_look.py; the icon and the
    manifest follow it when the brand's own icons replace these, in the clean-up.)
    """
    manifest = _manifest(_client(settings, clock, web_password=PASSWORD))
    client = _client(settings, clock, web_password=PASSWORD)
    client.set_cookie("fdb_look", "phosphor.auto")
    page = client.get("/login").text
    theme = re.search(r'<meta name="theme-color" content="(#[0-9a-f]{6})"', page)
    block = re.search(
        r'\[data-theme="phosphor"\] \{.*?--paper: (#[0-9a-f]{6});',
        (STATIC / "themes.css").read_text(),
        re.S,
    )
    assert theme and block
    assert manifest["theme_color"] == manifest["background_color"] == theme[1] == block[1]
    # The icon's ground too, so opening the app is one colour from the icon to the page.
    _, _, _, pixels = _png((STATIC / "apple-touch-icon.png").read_bytes())
    assert pixels[1:4] == bytes.fromhex(block[1][1:])


def test_the_icons_are_the_ones_the_script_draws() -> None:
    icons = _icons_script()
    for name, size in icons.APP_ICONS.items():
        # The pixels rather than the bytes: another zlib may pack the same picture differently.
        drawn = _png(icons.app_icon(size))
        assert _png((STATIC / name).read_bytes()) == drawn, f"run scripts/icons.py again: {name}"
