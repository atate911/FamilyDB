"""Contact sheets for comparing palettes.

  sheets/<page>.png  every palette's <page> side by side, labelled
  strips/<id>.png    one palette's Home (top), Ideas, 404 and Sign in in a 2x2, 1600 wide

Usage: venv/bin/python contact.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "out"
FONT = "/home/user/FamilyDB/src/familydb/web/static/fonts/dm-mono-500.woff2"


def font(size):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def palettes():
    found = []
    for p in sorted((HERE / "palettes").glob("*.json")):
        data = json.loads(p.read_text())
        if (OUT / data["id"] / "shots").exists():
            found.append(data)
    return found


def shot(pid, page, crop_h=900):
    f = OUT / pid / "shots" / f"{page}.png"
    if not f.exists():
        return None
    img = Image.open(f).convert("RGB")
    if img.height > crop_h and not page.endswith("phone"):
        img = img.crop((0, 0, img.width, crop_h))
    return img


def label(img, text, sub=""):
    bar = 44
    canvas = Image.new("RGB", (img.width, img.height + bar), (24, 24, 24))
    canvas.paste(img, (0, bar))
    d = ImageDraw.Draw(canvas)
    d.text((12, 8), text, fill=(240, 240, 240), font=font(22))
    if sub:
        d.text((12 + d.textlength(text, font=font(22)) + 14, 12), sub, fill=(160, 160, 160), font=font(16))
    return canvas


def sheet(page, cols=4, width=560):
    tiles = []
    for p in palettes():
        img = shot(p["id"], page, crop_h=1500 if page == "home" else 900)
        if img is None:
            continue
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
        tiles.append(label(img, p["id"], p["name"]))
    if not tiles:
        return
    h = max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * width + (cols + 1) * 8, rows * h + (rows + 1) * 8), (40, 40, 40))
    for i, t in enumerate(tiles):
        canvas.paste(t, (8 + (i % cols) * (width + 8), 8 + (i // cols) * (h + 8)))
    (HERE / "sheets").mkdir(exist_ok=True)
    canvas.save(HERE / "sheets" / f"{page}.png", optimize=True)


def strip(p):
    # The pages with the most content, where a palette has to show: Home down to its lists,
    # Chat, Ideas and Status (404 and Sign in are the monitor in every palette).
    parts = [shot(p["id"], "home", 1500), shot(p["id"], "chat"), shot(p["id"], "ideas"), shot(p["id"], "status"),
             shot(p["id"], "plans"), shot(p["id"], "todo")]
    parts = [x for x in parts if x is not None]
    if not parts:
        return
    w = 800
    parts = [x.resize((w, round(x.height * w / x.width)), Image.LANCZOS) for x in parts]
    rows = [max(x.height for x in parts[r * 2:r * 2 + 2]) for r in range((len(parts) + 1) // 2)]
    canvas = Image.new("RGB", (2 * w + 12, sum(rows) + 4 * (len(rows) + 1)), (40, 40, 40))
    y = 4
    for r, rh in enumerate(rows):
        for c, x in enumerate(parts[r * 2:r * 2 + 2]):
            canvas.paste(x, (4 + c * (w + 4), y))
        y += rh + 4
    canvas = label(canvas, p["id"], p["name"])
    (HERE / "strips").mkdir(exist_ok=True)
    canvas.save(HERE / "strips" / f"{p['id']}.png", optimize=True)


def row(images, height, gap=8):
    images = [im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS) for im in images if im]
    if not images:
        return None
    canvas = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) + 1), height + gap * 2), (40, 40, 40))
    x = gap
    for im in images:
        canvas.paste(im, (x, gap))
        x += im.width + gap
    return canvas


def frames(pid, names):
    out = []
    for n in names:
        f = OUT / pid / "shots" / f"{n}.png"
        out.append(Image.open(f).convert("RGB") if f.exists() else None)
    return out


def cells(images, cw, ch, cols=4, gap=8):
    """Each image fitted inside a cw x ch cell (never enlarged past 1.5x), cols to a row."""
    images = [im for im in images if im]
    if not images:
        return None
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cw + (cols + 1) * gap, rows * ch + (rows + 1) * gap), (40, 40, 40))
    for i, im in enumerate(images):
        scale = min(cw / im.width, ch / im.height, 1.5)
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        x = gap + (i % cols) * (cw + gap) + (cw - im.width) // 2
        y = gap + (i // cols) * (ch + gap) + (ch - im.height) // 2
        canvas.paste(im, (x, y))
    return canvas


def details(p):
    """The small parts and the motion: controls, focus, the glow fading, a monitor switching on."""
    pid = p["id"]
    rows = [
        ("Controls: a field being typed in, a box ticked, a select focused, the bar's menu open",
         cells(frames(pid, ["controls-field", "controls-checkbox", "controls-select", "controls-menu"]), 560, 300, cols=2)),
        ("Keyboard: focus on the 1st, 4th, 14th and 17th Tab stop on Home",
         cells(frames(pid, ["focus-1", "focus-4", "focus-14", "focus-17"]), 276, 120)),
        ("Afterglow: a card hovered, then 120, 380 and 900 ms after the pointer leaves",
         cells(frames(pid, ["motion-glow-0", "motion-glow-1", "motion-glow-2", "motion-glow-3"]), 276, 170)),
        ("Power on: Next up's monitor 60, 220, 450 and 900 ms after the page opens",
         cells(frames(pid, ["motion-on-0", "motion-on-1", "motion-on-2", "motion-on-3"]), 276, 170)),
    ]
    rows = [(t, r) for t, r in rows if r]
    if not rows:
        return
    w = max(r.width for _, r in rows)
    canvas = Image.new("RGB", (w, sum(r.height + 30 for _, r in rows)), (24, 24, 24))
    d, y = ImageDraw.Draw(canvas), 0
    for t, r in rows:
        d.text((10, y + 6), t, fill=(200, 200, 196), font=font(16))
        canvas.paste(r, (0, y + 30))
        y += r.height + 30
    label(canvas, pid, p["name"] + " · details").save(HERE / "strips" / f"{pid}-details.png", optimize=True)


def squint(p):
    """The squint test: Home, Ideas and Chat blurred, to see what the eye finds first."""
    from PIL import ImageFilter
    parts = [shot(p["id"], "home", 1500), shot(p["id"], "ideas"), shot(p["id"], "chat")]
    parts = [x.resize((400, round(x.height * 400 / x.width)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3.2))
             for x in parts if x is not None]
    r = row(parts, 460)
    if r:
        label(r, p["id"], p["name"] + " · squint").save(HERE / "strips" / f"{p['id']}-squint.png", optimize=True)


if __name__ == "__main__":
    for page in ["home", "ideas", "lost", "login", "chat", "status", "home-phone", "plans", "todo", "settings"]:
        sheet(page, cols=5 if page == "home-phone" else 4, width=300 if page == "home-phone" else 560)
    for p in palettes():
        strip(p)
        details(p)
        squint(p)
    squints = [Image.open(HERE / "strips" / f"{p['id']}-squint.png") for p in palettes()
               if (HERE / "strips" / f"{p['id']}-squint.png").exists()]
    if squints:
        w = max(i.width for i in squints)
        sheet_img = Image.new("RGB", (w, sum(i.height + 8 for i in squints)), (40, 40, 40))
        y = 0
        for i in squints:
            sheet_img.paste(i, (0, y))
            y += i.height + 8
        sheet_img.save(HERE / "sheets" / "squint.png", optimize=True)
    print("sheets:", sorted(x.name for x in (HERE / "sheets").glob("*.png")))
    print("strips:", sorted(x.name for x in (HERE / "strips").glob("*.png")))
