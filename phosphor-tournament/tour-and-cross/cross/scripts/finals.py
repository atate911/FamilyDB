import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
L = Path("/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/tour/landing")
OUT = Path("/tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad/landing")
r = json.load(open(L / "results.json"))
rank = {x["id"]: (i + 1, x["mean"], x["name"]) for i, x in enumerate(r["ranking"])}
ids = [x["id"] for x in r["ranking"] if x["id"] in r["finals"] or x["id"] in ("r13-idea-1", "00-current")]
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
W, H, cols = 760, 534, 3
for page in ("home", "todo", "status"):
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W + 16) + 16, rows * (H + 96) + 16), (18, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, pid in enumerate(ids):
        im = Image.open(L / "out" / pid / "shots" / f"{page}.png").convert("RGB")
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * 900 / 1280)))).resize((W, H))
        x, y = 16 + (i % cols) * (W + 16), 16 + (i // cols) * (H + 96)
        n, m, nm = rank[pid]
        tag = "" if pid in r["finals"] else "  (yardstick)"
        d.text((x, y), f"#{n}  {nm}  ·  {m}{tag}", fill=(220, 214, 200), font=b)
        d.text((x, y + 36), pid, fill=(150, 160, 155), font=f)
        sheet.paste(im, (x, y + 76))
    sheet.save(OUT / f"landing-{page}.png", optimize=True)
print(ids)
