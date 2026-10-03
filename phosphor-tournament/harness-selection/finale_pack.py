"""Pack the finale's page shots: a JPEG of every page (desktop and phone) and a contact sheet of each.
Usage: venv/bin/python finale_pack.py ID... -> /home/user/FamilyDB/phosphor-tournament/finale/mockups/<ID>/"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).parent / "rounds/r21/finale-shots"
DST = Path("/home/user/FamilyDB/phosphor-tournament/finale/mockups")
NAMES = {"r20-mut-3": "Grid Console, Keyed", "r20-mut-1": "Desk Terminal, Even Dock",
         "r19-mut-2": "Track Diagram, Rail Keys", "r20-mut-2": "Lit Index, Ledger Rail"}
ORDER = ["login", "home", "chat", "ideas", "idea", "idea-new", "plans", "plans-month", "todo", "memory", "restaurants",
         "wishes", "family", "status", "you", "settings", "setup", "lost"]


def font(size):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def key(name):
    base = name.split("--")[0]
    head = next((i for i, o in enumerate(ORDER) if base == o or base.startswith(o + "-")), 99)
    return (head, base)


def sheet(files, kind, title, out, cols, tile_w, crop_h):
    tiles = []
    for f in files:
        im = Image.open(f).convert("RGB")
        r = tile_w / im.width
        im = im.resize((tile_w, max(1, int(im.height * r))), Image.LANCZOS)
        full = im.height
        if im.height > crop_h:
            im = im.crop((0, 0, tile_w, crop_h))
        tiles.append((f.name.split("--")[0], im, full > crop_h))
    pad, lab = 14, 26
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    heights = [max(t[1].height for t in r) + lab for r in rows]
    W = cols * (tile_w + pad) + pad
    H = sum(heights) + pad * (len(rows) + 1) + 54
    canvas = Image.new("RGB", (W, H), (14, 16, 16))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 14), f"{title} - {kind}", fill=(210, 230, 215), font=font(22))
    y = 54
    for r, h in zip(rows, heights):
        for i, (name, im, cut) in enumerate(r):
            x = pad + i * (tile_w + pad)
            d.text((x, y), name + ("  (top shown)" if cut else ""), fill=(150, 175, 160), font=font(14))
            canvas.paste(im, (x, y + lab))
        y += h + pad
    canvas.save(out, quality=82, optimize=True)


for ID in sys.argv[1:]:
    root = DST / ID
    for kind in ("desktop", "phone"):
        (root / kind).mkdir(parents=True, exist_ok=True)
        files = sorted(SRC.glob(f"{ID}/*--{kind}.png"), key=lambda p: key(p.name))
        for f in files:
            im = Image.open(f).convert("RGB")
            if kind == "phone":  # 390 css px at 1.5x
                im = im.resize((585, int(im.height * 585 / im.width)), Image.LANCZOS)
            im.save(root / kind / (f.name.split("--")[0] + ".jpg"), quality=78, optimize=True)
        if kind == "desktop":
            sheet(files, kind, NAMES[ID], root / "sheet-desktop.jpg", 5, 440, 760)
        else:
            sheet(files, kind, NAMES[ID], root / "sheet-phone.jpg", 9, 215, 700)
    print(ID, "done")
