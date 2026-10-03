import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
T = Path("/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/tour")
OUT = Path("/tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad/landing")
HEAT = {"track": "a", "timetable": "a", "pocket": "a", "figure": "b", "console": "b", "switchboard": "b"}
ORIG = {"track": "r13-mut-4", "timetable": "r10-wild-3", "pocket": "r11-wild-1", "figure": "r10-wild-4", "console": "r11-wild-3", "switchboard": "r12-wmut-1"}
res = {n: json.load(open(T / f"t{n}" / "results.json")) for n in (1, 2, 3)}
def find(pid, dirs):
    for d in dirs:
        p = T / d / "out" / pid / "shots" / "home.png"
        if p.exists(): return p
def name(pid, d):
    try: return json.load(open(T / d / "palettes" / f"{pid}.json"))["name"]
    except Exception: return pid
def score(pid, n):
    for h in res[n]["heats"].values():
        for x in h["ranking"]:
            if x["id"] == pid: return x["mean"]
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except Exception:
    font = bold = ImageFont.load_default()
W, CROP = 640, 900
for k, h in HEAT.items():
    cells = [("Origin", ORIG[k], find(ORIG[k], ["landing", "donors"]), name(ORIG[k], "landing"), "")]
    for n in (1, 2, 3):
        pid = res[n]["lineages"][k]["carried"][0]["id"]
        cells.append((f"After round {n}", pid, find(pid, [f"t{n}-{h}", f"t{n+1}-{h}", "landing"]), name(pid, f"t{n}-{h}"), f"{score(pid, n)}"))
    ims = []
    for lab, pid, p, nm, sc in cells:
        im = Image.open(p).convert("RGB")
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * CROP / 1280))))
        im = im.resize((W, int(im.height * W / im.width)))
        ims.append((lab, pid, nm, sc, im))
    hh = max(i[4].height for i in ims)
    sheet = Image.new("RGB", (len(ims) * (W + 16) + 16, hh + 110), (18, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (lab, pid, nm, sc, im) in enumerate(ims):
        x = 16 + i * (W + 16)
        d.text((x, 14), lab + (f"  ·  {sc}" if sc else ""), fill=(220, 214, 200), font=bold)
        d.text((x, 52), f"{nm}  ({pid})", fill=(160, 170, 165), font=font)
        sheet.paste(im, (x, 94))
    sheet.save(OUT / f"journey-{k}.png", optimize=True)
    print(k, [c[1] for c in cells])
