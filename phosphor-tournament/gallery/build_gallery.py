#!/usr/bin/env python3
"""Build a browsable web page of one round's screenshots.

    python3 build_gallery.py HARNESS ROUND OUT [--left ID,ID]

HARNESS is the tournament harness folder, ROUND is the round whose field to show (for example
r13), and OUT is an empty folder to build into. OUT then holds index.html (built from
index.template.html with the round's data written into it) and img/<design>/<page>.webp.

The screenshots come from HARNESS/rounds/ROUND/out/<design>/shots/. The designs going on into the
next round are read from HARNESS/rounds/<next>/args.json; --left names designs that left the main
lane even though they scored well. The small detail shots (controls, keyboard focus, the
afterglow's frames and the screen switching on) are joined into one labelled sheet each so the
page stays at a few hundred files.
"""

import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PLAIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GROUND = (11, 14, 12)
INK = (229, 234, 230)
DIM = (154, 165, 159)

# (key, label, kind, screenshot name). A phone shot is drawn at half its pixel width.
PAGES = [
    ("home", "Home", "desk", "home"),
    ("home-phone", "Home on a phone", "phone", "home-phone"),
    ("chat", "Chat", "desk", "chat"),
    ("chat-phone", "Chat on a phone", "phone", "chat-phone"),
    ("ideas", "Ideas", "desk", "ideas"),
    ("plans", "Plans", "desk", "plans"),
    ("todo", "To do", "desk", "todo"),
    ("status", "Status", "desk", "status"),
    ("settings", "Settings", "desk", "settings"),
    ("general", "Settings: General", "desk", "general"),
    ("form", "New idea", "desk", "form"),
    ("login", "Sign in", "desk", "login"),
    ("lost", "Page not found", "desk", "lost"),
]
DETAILS = [
    ("controls", "Controls", "A ticked checkbox, a text field, the bar's menu opened and an open select."),
    ("focus", "Keyboard focus", "Where the keyboard lands on Home: the 1st, 4th, 14th and 17th press of Tab."),
    ("afterglow", "Afterglow", "An idea card with the pointer on it, then the pointer leaves: how the light fades over 900 ms."),
    ("switchon", "Switch-on", "The Next up screen coming on after the page loads: 60, 220, 450 and 900 ms in."),
]


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def webp(im, path, quality=84):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(path, "WEBP", quality=quality, method=6)
    return im.size


def sheet(parts, cols, path, pad=18, gap=18, label_h=26):
    """Lay labelled images out in a grid on the dark ground and save the sheet."""
    label, small = font(BOLD, 14), font(PLAIN, 13)
    cells = [(t, Image.open(p).convert("RGB")) for t, p in parts if p.exists()]
    if not cells:
        return None
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    col_w = [max((r[c][1].width for r in rows if c < len(r)), default=0) for c in range(cols)]
    row_h = [max(im.height for _, im in r) + label_h for r in rows]
    canvas = Image.new("RGB", (pad * 2 + sum(col_w) + gap * (cols - 1), pad * 2 + sum(row_h) + gap * (len(rows) - 1)), GROUND)
    draw = ImageDraw.Draw(canvas)
    y = pad
    for r, rh in zip(rows, row_h):
        x = pad
        for c, (title, im) in enumerate(r):
            draw.text((x, y), title, fill=DIM, font=small)
            canvas.paste(im, (x, y + label_h))
            x += col_w[c] + gap
        y += rh + gap
    return webp(canvas, path, 90)


def details(shots, out):
    """Join the small detail shots of one design into four labelled sheets."""
    g = lambda n: shots / f"{n}.png"
    made = {}
    made["controls"] = sheet([("checkbox, ticked", g("controls-checkbox")), ("text field", g("controls-field")),
                              ("open select", g("controls-select")), ("the bar's menu", g("controls-menu"))],
                             2, out / "controls.webp")
    made["focus"] = sheet([(f"Tab stop {i}", g(f"focus-{i}")) for i in (1, 4, 14, 17)], 4, out / "focus.webp")
    made["afterglow"] = sheet([("pointer on the card", g("motion-glow-0")), ("120 ms after it leaves", g("motion-glow-1")),
                               ("380 ms", g("motion-glow-2")), ("900 ms", g("motion-glow-3"))], 1, out / "afterglow.webp")
    made["switchon"] = sheet([(f"{ms} ms after load", g(f"motion-on-{i}")) for i, ms in enumerate((60, 220, 450, 900))],
                             2, out / "switchon.webp")
    return {k: {"w": v[0], "h": v[1]} for k, v in made.items() if v}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    left = set()
    for i, a in enumerate(sys.argv):
        if a == "--left" and i + 1 < len(sys.argv):
            left = set(sys.argv[i + 1].split(","))
    harness, rnd, out = Path(args[0]), args[1], Path(args[2])
    nxt = f"r{int(rnd[1:]) + 1}"
    rdir = harness / "rounds" / rnd
    result = json.loads((rdir / "results.json").read_text())
    fams = json.loads((harness / "families.json").read_text())
    fams = fams.get("palettes", fams)
    args_next = json.loads((harness / "rounds" / nxt / "args.json").read_text())
    main_lane = {c["id"] for c in args_next["carried"]}
    wild_lane = {c["id"] for c in args_next.get("wildCarried", [])}

    def palette(pid):
        for f in [rdir / "palettes" / f"{pid}.json", *sorted((harness / "rounds").glob(f"*/palettes/{pid}.json"))]:
            if f.exists():
                return json.loads(f.read_text())
        return {}

    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)
    ranked = [{**r, "rank": i} for i, r in enumerate(result["ranking"], 1)]
    designs = []
    for r in [{"id": "00-current", "name": "Today's page", "rank": 0, "mean": result["todayMean"]}, *ranked]:
        pid = r["id"]
        shots = rdir / "out" / pid / "shots"
        if not shots.exists():
            print("no shots for", pid)
            continue
        base = out / "img" / pid
        sizes = {}
        for key, _label, _kind, name in PAGES:
            f = shots / f"{name}.png"
            if f.exists():
                w, h = webp(Image.open(f), base / f"{key}.webp")
                sizes[key] = {"w": w, "h": h}
        det = details(shots, base)
        if pid == "00-current":
            lane, lane_label = "today", "Today's page, the yardstick"
        elif pid in main_lane:
            lane, lane_label = "main", "Going on: main lane"
        elif pid in wild_lane:
            lane, lane_label = "wild", "Going on: wild lane"
        elif pid in left:
            lane, lane_label = "left", "Left the main lane"
        else:
            lane, lane_label = "other", "Not carried on"
        p = palette(pid)
        designs.append({
            "id": pid, "name": r["name"], "rank": r["rank"], "score": r["mean"], "lane": lane, "laneLabel": lane_label,
            "top4": r.get("top4"), "promise": r.get("promise"),
            "family": (fams.get(pid) or {}).get("family", ""),
            "tagline": re.sub(r"\s+", " ", p.get("tagline", "")).strip(),
            "shots": sizes, "details": det,
        })
        print(f"{pid:12s} {len(sizes)} pages, {len(det)} detail sheets")
    data = {
        "round": int(rnd[1:]), "count": len([d for d in designs if d["id"] != "00-current"]),
        "today": result["todayMean"], "judges": len(result["judges"]),
        "pages": [{"key": k, "label": l, "kind": kind} for k, l, kind, _ in PAGES],
        "details": [{"key": k, "label": l, "note": n} for k, l, n in DETAILS],
        "designs": designs,
    }
    template = (HERE / "index.template.html").read_text()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    (out / "index.html").write_text(template.replace('"__DATA__"', payload))
    files = [p for p in out.rglob("*") if p.is_file()]
    print(len(files), "files,", round(sum(p.stat().st_size for p in files) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
