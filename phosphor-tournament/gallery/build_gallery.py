#!/usr/bin/env python3
"""Build a browsable web page of every round's screenshots and the judges' comments.

    python3 build_gallery.py HARNESS OUT [--rounds 1-13] [--cap 500]

HARNESS is the tournament harness folder and OUT is a folder to build into (an earlier build is
cleared; anything else is refused). An artifact can hold only 511 files, so the pictures are
split over several sites, each a run of rounds with at most --cap files: OUT/site-K/ holds
index.html (built from index.template.html; every site carries all the text, the judges'
comments included) and img/<design>/<page>.webp for the rounds it hosts. Publish each folder as
its own artifact, then replace the placeholders @SITE1@, @SITE2@ ... in every index.html with the
published links (relink.py does it), so each page can point to the others.

Round 1 is read from HARNESS/results.json and HARNESS/round1/out; round N from
HARNESS/rounds/rN/. A design carried into later rounds keeps its id, so its pictures are made once
(from the run that captured the most pages) and shown in every round it was judged in. The designs
going on from a round are read from the next round's args.json. The small detail shots (controls,
keyboard focus, the afterglow's frames, the screen switching on) are joined into one labelled sheet
each so the page stays at a few thousand files.
"""

import json
import re
import shutil
import sys
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
PLAIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GROUND = (11, 14, 12)
DIM = (154, 165, 159)

# (key, label, kind). A phone shot is drawn at half its pixel width.
PAGES = [
    ("home", "Home", "desk"),
    ("home-phone", "Home on a phone", "phone"),
    ("chat", "Chat", "desk"),
    ("chat-phone", "Chat on a phone", "phone"),
    ("ideas", "Ideas", "desk"),
    ("plans", "Plans", "desk"),
    ("todo", "To do", "desk"),
    ("status", "Status", "desk"),
    ("settings", "Settings", "desk"),
    ("general", "Settings: General", "desk"),
    ("form", "New idea", "desk"),
    ("login", "Sign in", "desk"),
    ("lost", "Page not found", "desk"),
]
DETAILS = [
    ("controls", "Controls", "A ticked checkbox, a text field, the bar's menu opened and an open select."),
    ("focus", "Keyboard focus", "Where the keyboard lands on Home: the 1st, 4th, 14th and 17th press of Tab."),
    ("afterglow", "Afterglow", "An idea card with the pointer on it, then the pointer leaves: how the light fades over 900 ms."),
    ("switchon", "Switch-on", "The Next up screen coming on after the page loads: 60, 220, 450 and 900 ms in."),
]
LENSES = {
    "feedback": "Owner's judge",
    "soul": "Phosphor soul",
    "style": "Style",
    "system": "Design system",
    "interaction": "Interaction",
    "type": "Typography",
    "usability": "Usability",
    "product": "Product",
    "skeptic": "Skeptic",
}


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
    small = font(PLAIN, 13)
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


def convert(job):
    """Turn one design's screenshots into webp files; return its picture sizes."""
    pid, shots, base = job
    shots, base = Path(shots), Path(base)
    sizes = {}
    for key, _label, _kind in PAGES:
        f = shots / f"{key}.png"
        if f.exists():
            w, h = webp(Image.open(f), base / f"{key}.webp")
            sizes[key] = {"w": w, "h": h}
    return pid, sizes, details(shots, base)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    harness, out = Path(args[0]), Path(args[1])
    lo, hi, cap = 1, 13, 500
    if "--cap" in sys.argv:
        cap = int(sys.argv[sys.argv.index("--cap") + 1])
    if "--rounds" in sys.argv:
        lo, hi = map(int, sys.argv[sys.argv.index("--rounds") + 1].split("-"))
    fams = read(harness / "families.json")

    def round_dir(n):
        return harness / "rounds" / f"r{n}"

    def results_path(n):
        return harness / "results.json" if n == 1 else round_dir(n) / "results.json"

    def out_dir(n):
        return harness / "round1" / "out" if n == 1 else round_dir(n) / "out"

    def palette(pid):
        for f in [harness / "round1" / "palettes" / f"{pid}.json", harness / "palettes" / f"{pid}.json",
                  *sorted((harness / "rounds").glob(f"*/palettes/{pid}.json"))]:
            if f.exists():
                return read(f)
        return {}

    if out.exists():
        extra = {p.name for p in out.iterdir() if p.name != "img" and not p.name.startswith("site-")}
        if extra:
            sys.exit(f"{out} holds files a build does not make ({', '.join(sorted(extra)[:3])}); give an empty folder or an earlier build")
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)

    rounds, best = [], {}
    order = {k: i for i, k in enumerate(LENSES)}
    for n in range(lo, hi + 1):
        if not results_path(n).exists():
            print(f"round {n}: no results, skipped")
            continue
        res = read(results_path(n))
        nxt = round_dir(n + 1) / "args.json"
        going = read(nxt) if nxt.exists() else {}
        main_lane = {c["id"] if isinstance(c, dict) else c for c in going.get("carried", [])}
        wild_lane = {c["id"] if isinstance(c, dict) else c for c in going.get("wildCarried", [])}
        judges = sorted(res.get("judges", []), key=lambda j: order.get(j["lens"], 99))
        top4 = {j["lens"]: set(j.get("top4") or []) for j in judges}

        def comments(pid):
            rows = []
            for j in judges:
                mine = [s for s in j["scores"] if s["id"] == pid]
                if not mine:
                    continue
                fix = next((f.get("suggestion", "") for f in (j.get("fixes") or []) if f.get("id") == pid), "")
                rows.append({"l": j["lens"], "s": mine[0]["score"], "w": mine[0].get("why", ""), "f": fix, "t": pid in top4[j["lens"]]})
            return rows

        today = res.get("todayMean")
        if today is None:
            marks = [r["s"] for r in comments("00-current")]
            today = round(sum(marks) / len(marks), 2) if marks else None
        entries = [{"id": "00-current", "name": "Today's page", "rank": 0, "score": today, "lane": "today",
                    "judges": comments("00-current")}]
        for i, r in enumerate(res["ranking"], 1):
            pid = r["id"]
            lane = "main" if pid in main_lane else "wild" if pid in wild_lane else "other"
            entries.append({"id": pid, "name": r["name"], "rank": i, "score": r["mean"], "lane": lane,
                            "origin": r.get("origin", ""), "top4": r.get("top4"), "promise": r.get("promise"),
                            "judges": comments(pid)})
        notes = [{"l": j["lens"], "t": j.get("notes", "")} for j in judges if j.get("notes")]
        rounds.append({"n": n, "mode": res.get("mode", ""), "judges": len(judges), "weights": res.get("lensWeights"),
                       "margin": res.get("margin"), "today": today, "winners": res.get("top4") or [],
                       "lessons": res.get("lessons", ""), "notes": notes, "entries": entries})
        # the run that captured the most pages of a design is the one shown
        for e in entries:
            shots = out_dir(n) / e["id"] / "shots"
            if shots.exists():
                count = len(list(shots.glob("*.png")))
                if count >= best.get(e["id"], (0, None))[0]:
                    best[e["id"]] = (count, shots)
        print(f"round {n}: {len(entries) - 1} designs")

    jobs = [(pid, str(shots), str(out / "img" / pid)) for pid, (_c, shots) in best.items()]
    with Pool() as pool:
        made = {pid: (sizes, det) for pid, sizes, det in pool.imap_unordered(convert, jobs)}

    designs = {}
    for rd in rounds:
        for e in rd["entries"]:
            pid = e["id"]
            if pid in designs or pid not in made:
                continue
            p = palette(pid)
            designs[pid] = {"tagline": re.sub(r"\s+", " ", p.get("tagline", "")).strip(),
                            "family": (fams.get(pid) or {}).get("family", ""),
                            "shots": made[pid][0], "details": made[pid][1]}
    # split the rounds into runs whose pictures fit one artifact
    def cost(ids):
        return sum(len(list((out / "img" / i).glob("*.webp"))) for i in ids) + 1

    groups, cur, first = [], set(), None
    for rd in rounds:
        ids = {e["id"] for e in rd["entries"] if e["id"] in made}
        if cur and cost(cur | ids) > cap:
            groups.append((first, last, cur))
            cur, first = set(), None
        if first is None:
            first = rd["n"]
        cur |= ids
        last = rd["n"]
    groups.append((first, last, cur))
    sites = [{"lo": a, "hi": b, "url": f"@SITE{k}@"} for k, (a, b, _ids) in enumerate(groups, 1)]

    template = (HERE / "index.template.html").read_text(encoding="utf-8")
    for k, (a, b, ids) in enumerate(groups, 1):
        site = out / f"site-{k}"
        for pid in sorted(ids):
            for f in (out / "img" / pid).glob("*.webp"):
                dest = site / "img" / pid / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        data = {
            "pages": [{"key": k_, "label": l, "kind": kind} for k_, l, kind in PAGES],
            "details": [{"key": k_, "label": l, "note": n} for k_, l, n in DETAILS],
            "lenses": LENSES,
            "rounds": rounds,
            "designs": {pid: d for pid, d in designs.items() if pid in ids},
            "site": k,
            "sites": sites,
        }
        payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
        (site / "index.html").write_text(template.replace('"__DATA__"', payload), encoding="utf-8")
        files = [p for p in site.rglob("*") if p.is_file()]
        print(f"site {k}: rounds {a}-{b}, {len(files)} files, {round(sum(p.stat().st_size for p in files) / 1e6, 1)} MB")
    shutil.rmtree(out / "img")


if __name__ == "__main__":
    main()
