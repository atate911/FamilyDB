#!/usr/bin/env python3
"""Build a browsable web page of every round's screenshots and the judges' comments.

    python3 build_gallery.py HARNESS OUT [--rounds 1-13]

HARNESS is the tournament harness folder and OUT is a folder to build into (an earlier build is
cleared; anything else is refused; --reuse takes the pictures of an earlier build). An artifact can hold only 511 files, so each round is its own
page: OUT/round-N/ holds index.html (built from round.template.html) and img/<design>/<page>.webp
for the designs judged that round, and OUT/index/ holds the index page (index.template.html) with
a picture of each round's winner. Publish each folder as its own artifact, then replace the
placeholders @INDEX@ and @ROUND1@, @ROUND2@ ... in every index.html with the published links
(relink.py does it) so the pages can point to one another.

Round 1 is read from HARNESS/results.json and HARNESS/round1/out; round N from
HARNESS/rounds/rN/. Each round shows the pictures captured in that round, so a design changed
between rounds is shown as it was judged. The designs going on from a round are read from the next
round's args.json. Rounds whose results carry no lessons take them from HARNESS/lessons.md. The small detail shots (controls,
keyboard focus, the afterglow's frames, the screen switching on) are joined into one labelled sheet
each so a round stays a few hundred files.
"""

import argparse
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
    ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    col_w = [max((max(r[c][1].width, int(ruler.textlength(r[c][0], font=small)) + 1) for r in rows if c < len(r)), default=0)
             for c in range(cols)]
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
    n, pid, shots, base = job
    shots, base = Path(shots), Path(base)
    sizes = {}
    for key, _label, _kind in PAGES:
        f = shots / f"{key}.png"
        if f.exists():
            w, h = webp(Image.open(f), base / f"{key}.webp")
            sizes[key] = {"w": w, "h": h}
    return n, pid, sizes, details(shots, base)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clean(text):
    """Drop sentences that point at the judges' scratch files, and markdown marks the page does not draw."""
    keep = []
    for line in str(text or "").split("\n"):
        parts = re.split(r"(?<=[.!?])\s+", line)
        keep.append(" ".join(p for p in parts if "/tmp/" not in p))
    return "\n".join(keep).replace("`", "").replace("**", "").strip()


def lessons_from(harness, n):
    """A round's section(s) of lessons.md, for rounds whose results hold none."""
    path = harness / "lessons.md"
    if not path.exists():
        return ""
    sections = re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    mine = [sec.split("\n", 1)[1] if "\n" in sec else "" for sec in sections if re.match(rf"Round {n}(\s|$)", sec)]
    return "\n\n".join(m.strip() for m in mine)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("harness", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--rounds", default="1-13")
    ap.add_argument("--reuse", type=Path, help="an earlier build whose pictures are copied instead of made again")
    opts = ap.parse_args()
    harness, out = opts.harness, opts.out
    lo, hi = map(int, opts.rounds.split("-"))
    fams = read(harness / "families.json")

    def round_dir(n):
        return harness / "rounds" / f"r{n}"

    def results_path(n):
        return harness / "results.json" if n == 1 else round_dir(n) / "results.json"

    def out_dir(n):
        return harness / "round1" / "out" if n == 1 else round_dir(n) / "out"

    def palette(n, pid):
        own = harness / "round1" / "palettes" if n == 1 else round_dir(n) / "palettes"
        for f in [own / f"{pid}.json", harness / "palettes" / f"{pid}.json",
                  *sorted((harness / "rounds").glob(f"*/palettes/{pid}.json"))]:
            if f.exists():
                return read(f)
        return {}

    if out.exists():
        extra = {p.name for p in out.iterdir() if p.name not in ("index", "gens") and not p.name.startswith("round-")}
        if extra:
            sys.exit(f"{out} holds files a build does not make ({', '.join(sorted(extra)[:3])}); give an empty folder or an earlier build")
    new = out.with_name(out.name + ".new")
    shutil.rmtree(new, ignore_errors=True)
    new.mkdir(parents=True)

    rounds, jobs, fallback = [], [], {}
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
                fixes = [f.get("suggestion", "") for f in (j.get("fixes") or []) if f.get("id") == pid]
                rows.append({"l": j["lens"], "s": mine[0]["score"], "w": clean(mine[0].get("why", "")),
                             "f": clean("\n\n".join(x for x in fixes if x)), "t": pid in top4[j["lens"]]})
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
        notes = [{"l": j["lens"], "t": clean(j.get("notes", ""))} for j in judges if j.get("notes")]
        winners = res.get("top4") or [e["id"] for e in entries if e["lane"] == "main"][:4]
        rounds.append({"n": n, "mode": res.get("mode", ""), "judges": len(judges), "weights": res.get("lensWeights"),
                       "margin": res.get("margin"), "today": today, "winners": winners,
                       "lessons": clean(res.get("lessons") or lessons_from(harness, n)), "notes": notes, "entries": entries})
        for e in entries:
            shots = out_dir(n) / e["id"] / "shots"
            if shots.exists():
                fallback[e["id"]] = shots
                jobs.append((n, e["id"], str(shots), str(new / f"round-{n}" / "img" / e["id"])))
        print(f"round {n}: {len(entries) - 1} designs")
    # a design listed without pictures in its round is shown as last captured
    have = {(n, pid) for n, pid, _s, _b in jobs}
    for rd in rounds:
        for e in rd["entries"]:
            if (rd["n"], e["id"]) not in have and e["id"] in fallback:
                jobs.append((rd["n"], e["id"], str(fallback[e["id"]]), str(new / f"round-{rd['n']}" / "img" / e["id"])))

    made, todo = {}, []
    for job in jobs:
        n, pid = job[0], job[1]
        old = opts.reuse / f"round-{n}" / "img" / pid if opts.reuse else None
        if old and old.is_dir():
            dest = Path(job[3])
            shutil.copytree(old, dest)
            size = lambda k: dict(zip("wh", Image.open(dest / f"{k}.webp").size))
            made[(n, pid)] = ({k: size(k) for k, _l, _t in PAGES if (dest / f"{k}.webp").exists()},
                              {k: size(k) for k, _l, _n in DETAILS if (dest / f"{k}.webp").exists()})
        else:
            todo.append(job)
    with Pool() as pool:
        for n, pid, sizes, det in pool.imap_unordered(convert, todo):
            made[(n, pid)] = (sizes, det)

    # who was judged where, for the "also judged in" links (a yardstick score of None is not shown)
    seen = {}
    for rd in rounds:
        for e in rd["entries"]:
            if e["score"] is not None:
                seen.setdefault(e["id"], []).append([rd["n"], e["score"], f"@ROUND{rd['n']}@"])
    nav = {"index": "@INDEX@", "gens": "@GENS@", "rounds": [{"n": rd["n"], "url": f"@ROUND{rd['n']}@"} for rd in rounds]}
    unique = len({e["id"] for rd in rounds for e in rd["entries"] if e["id"] != "00-current"})

    template = (HERE / "round.template.html").read_text(encoding="utf-8")
    taglines = {}
    for rd in rounds:
        page = new / f"round-{rd['n']}"
        designs = {}
        for e in rd["entries"]:
            if (rd["n"], e["id"]) not in made:
                continue
            p = palette(rd["n"], e["id"])
            designs[e["id"]] = {"tagline": re.sub(r"\s+", " ", p.get("tagline", "")).strip(),
                                "family": (fams.get(e["id"]) or {}).get("family", ""),
                                "shots": made[(rd["n"], e["id"])][0], "details": made[(rd["n"], e["id"])][1]}
        taglines[rd["n"]] = designs
        data = {
            "pages": [{"key": k_, "label": l, "kind": kind} for k_, l, kind in PAGES],
            "details": [{"key": k_, "label": l, "note": n_} for k_, l, n_ in DETAILS],
            "lenses": LENSES,
            "round": rd,
            "designs": designs,
            "nav": nav,
            "seen": {pid: seen[pid] for pid in designs if pid in seen},
        }
        payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
        html = template.replace("<title>Phosphor Screenshots</title>", f"<title>Phosphor Round {rd['n']}</title>", 1)
        (page / "index.html").write_text(html.replace('"__DATA__"', payload), encoding="utf-8")
        files = [p for p in page.rglob("*") if p.is_file()]
        print(f"round {rd['n']}: {len(files)} files, {round(sum(p.stat().st_size for p in files) / 1e6, 1)} MB")

    # across the rounds: each round's winner and runner-up, and today's page, for comparing generations
    gens = new / "gens"
    entries, gdesigns = [], {}

    def add(rd, e, lane):
        gid = ("today" if e["id"] == "00-current" else f"R{rd['n']:02d}-{e['id']}")
        src = new / f"round-{rd['n']}" / "img" / e["id"]
        if not src.is_dir():
            return
        shutil.copytree(src, gens / "img" / gid)
        entries.append({"id": gid, "name": e["name"], "rank": e["rank"] and (1 if lane == "winner" else 2), "score": e["score"],
                        "lane": lane, "roundNo": rd["n"] if e["id"] != "00-current" else 0, "judges": []})
        gdesigns[gid] = {"tagline": "", "family": "", "shots": made[(rd["n"], e["id"])][0], "details": made[(rd["n"], e["id"])][1]}

    add(rounds[-1], rounds[-1]["entries"][0], "today")
    for rd in rounds:
        for lane, rank in (("winner", 1), ("second", 2)):
            e = next((x for x in rd["entries"] if x["rank"] == rank), None)
            if e:
                add(rd, e, lane)
    gdata = {
        "pages": [{"key": k_, "label": l, "kind": kind} for k_, l, kind in PAGES],
        "details": [{"key": k_, "label": l, "note": n_} for k_, l, n_ in DETAILS],
        "lenses": LENSES,
        "round": {"n": 0, "gens": True, "mode": "", "judges": 0, "weights": None, "margin": None, "today": None,
                  "winners": [], "lessons": "", "notes": [], "entries": entries},
        "designs": gdesigns, "nav": nav, "seen": {},
    }
    payload = json.dumps(gdata, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("<title>Phosphor Screenshots</title>", "<title>Phosphor Across the Rounds</title>", 1)
    (gens / "index.html").write_text(html.replace('"__DATA__"', payload), encoding="utf-8")
    gfiles = [p for p in gens.rglob("*") if p.is_file()]
    print(f"across the rounds: {len(gfiles)} files, {round(sum(p.stat().st_size for p in gfiles) / 1e6, 1)} MB")

    # the index page: a picture of each round's winner on Home
    final = read(harness / "final.json") if (harness / "final.json").exists() else None
    idx = new / "index"
    cards = []
    for rd in rounds:
        winner = next(e for e in rd["entries"] if e["rank"] == 1)
        top = sorted((e for e in rd["entries"] if e["id"] in rd["winners"]), key=lambda e: e["rank"])
        src = new / f"round-{rd['n']}" / "img" / winner["id"] / "home.webp"
        im = Image.open(src).convert("RGB")
        keep = min(im.height, round(im.width * 900 / 1280))
        im = im.crop((0, 0, im.width, keep)).resize((720, round(720 * keep / im.width)), Image.LANCZOS)
        w, h = webp(im, idx / "img" / f"r{rd['n']}.webp", 80)
        card = {"n": rd["n"], "mode": rd["mode"], "judges": rd["judges"], "count": len(rd["entries"]) - 1,
                "today": rd["today"], "url": f"@ROUND{rd['n']}@", "img": f"img/r{rd['n']}.webp", "w": w, "h": h,
                "winner": {"name": winner["name"], "score": winner["score"],
                           "tagline": taglines[rd["n"]].get(winner["id"], {}).get("tagline", "")},
                "top": [{"name": e["name"], "score": e["score"]} for e in top]}
        if rd["n"] == 1 and final:
            best = final["ranking"][0]
            card["note"] = f"First panel, of twelve directions. The five polished finalists went to a final panel, which {best['name']} won ({best['mean']})."
        cards.append(card)
    template = (HERE / "index.template.html").read_text(encoding="utf-8")
    payload = json.dumps({"rounds": cards, "unique": unique, "gens": "@GENS@"}, separators=(",", ":")).replace("</", "<\\/")
    (idx / "index.html").write_text(template.replace('"__DATA__"', payload), encoding="utf-8")
    print("index page:", len([p for p in idx.rglob("*") if p.is_file()]), "files")

    shutil.rmtree(out, ignore_errors=True)
    new.rename(out)


if __name__ == "__main__":
    main()
