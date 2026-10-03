import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
L = Path("/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/cross/x14f")
OUT = Path("/tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad/cross")
r = json.load(open(L / "results.json"))
rank = [(i + 1, x["id"], x["name"], x["mean"]) for i, x in enumerate(r["ranking"])]
yard = {"00-current", "r13-idea-1", "t3-track-refine2"}
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
W, H, cols = 760, 534, 4
def sheet(page, items, name, phone=False):
    w, h = (380, 822) if phone else (W, H)
    rows = (len(items) + cols - 1) // cols
    s = Image.new("RGB", (cols * (w + 16) + 16, rows * (h + 96) + 16), (18, 20, 20))
    d = ImageDraw.Draw(s)
    for i, (n, pid, nm, m) in enumerate(items):
        im = Image.open(L / "out" / pid / "shots" / f"{page}.png").convert("RGB")
        if phone:
            im = im.crop((0, 0, im.width, min(im.height, int(im.width * 844 / 390)))).resize((w, h))
        else:
            im = im.crop((0, 0, im.width, min(im.height, int(im.width * 900 / 1280)))).resize((w, h))
        x, y = 16 + (i % cols) * (w + 16), 16 + (i // cols) * (h + 96)
        tag = " (yardstick)" if pid in yard else ""
        d.text((x, y), f"#{n} {nm} · {m}{tag}"[:58 if not phone else 30], fill=(220, 214, 200), font=b if not phone else f)
        d.text((x, y + 36), pid, fill=(150, 160, 155), font=f)
        s.paste(im, (x, y + 76))
    s.save(OUT / f"{name}.png", optimize=True)
top = [x for x in rank if x[1] not in yard][:8]
ys = [x for x in rank if x[1] in yard]
for p in ("home", "todo", "plans", "status"):
    sheet(p, top, f"final-top8-{p}")
sheet("home", [x for x in rank if x[1] not in yard][8:] + ys, "final-rest-home")
sheet("home-phone", top, "final-top8-phone", phone=True)
print([x[2] for x in top])
