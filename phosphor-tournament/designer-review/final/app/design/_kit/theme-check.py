#!/usr/bin/env python3
"""Check every theme against the theme contract, and write a palette sheet for each.

    python3 _kit/theme-check.py                  # every themes/*.css; exit 1 if any fails
    python3 _kit/theme-check.py themes/rail.css  # one theme
    python3 _kit/theme-check.py --sheets         # also write palette/<theme>.html

In the app this is tests/test_themes.py: the same checks, one parametrised test per theme file, so
a theme that misses a token or fails a floor can't be merged. No dependencies beyond Python 3.

What it checks (HANDOFF.md, "Themes"):
  1. The file is colour only: custom properties and color-scheme inside the theme's own selectors,
     a header with @theme name / line / first / theme-color, and nothing else.
  2. Every contract token is defined, by day and by night; none of the fixed tokens is.
  3. The two copies of the second mode (device-chosen and person-chosen) are identical.
  4. Contrast floors (WCAG 2.x): 4.5:1 for words, 3:1 for controls, marks and edges.
  5. The eight people stay apart for colour-blind eyes (Machado 2009, CIEDE2000), and late red is
     never confused with a person, with "needs a look" or with "done".
  6. Phosphor green is Vera's: only her tokens, today and Send may come near it.
"""
import math, re, sys, glob, os, html as H

CONTRACT = [
  # surfaces, words, rules
  "paper", "paper-2", "card", "field", "ink", "ink-2", "ink-3", "line", "line-2", "edge",
  # the panel (sidebar, phone top bar)
  "side", "side-ink", "side-ink-2", "side-hi", "side-line", "side-mark", "side-link",
  # the family's action, focus, today
  "link", "primary", "primary-2", "on-primary", "focus", "today-bg", "on-today",
  # Vera, her Ask box and its Send
  "vera", "vera-bg", "on-vera", "vera-soft", "vera-line",
  "ask-bg", "ask-ink", "ask-ink-2", "ask-rim", "ask-edge", "send", "send-2", "on-send",
  # meanings: done, needs a look, late
  "ok", "ok-soft", "ok-line", "warn", "warn-soft", "warn-line", "alert", "alert-soft", "alert-line", "on-alert",
  # depth
  "shadow", "shadow-lift", "shadow-up",
] + [f"p{i}{v}" for i in range(1, 9) for v in ("", "-soft", "-ink", "-mark", "-on")] \
  + [f"everyone{v}" for v in ("", "-soft", "-ink", "-mark", "-on")]
FIXED = ("glass", "phosphor", "cursor", "vs-halo", "mark-glass", "ask-rule", "ask-fill", "font-", "t-", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "r-", "av-", "tile-", "target", "topbar-h", "tabbar")
PHOSPHOR = "#6DFF9C"
NEAR_PHOSPHOR_OK = {"vera", "vera-bg", "today-bg", "send", "send-2", "ok", "side-mark"}

TEXT = 4.5; NONTEXT = 3.0
SURFACES = ["paper", "paper-2", "card", "field"]
PAIRS = (
  [(fg, bg, TEXT, "words") for fg in ("ink", "ink-2", "ink-3") for bg in SURFACES]
  + [("link", bg, TEXT, "links") for bg in ("paper", "card")]
  + [("on-primary", "primary", TEXT, "the primary button"), ("on-today", "today-bg", TEXT, "today's date"),
     ("on-vera", "vera-bg", TEXT, "Vera's filled things"), ("on-send", "send", TEXT, "Send"), ("on-alert", "alert", TEXT, "a late plate")]
  + [("vera", bg, TEXT, "Vera's words") for bg in ("card", "paper", "vera-soft")]
  + [(t, bg, TEXT, "meanings") for t in ("ok", "warn", "alert") for bg in (t + "-soft", "card")] + [("alert", "paper", TEXT, "late")]
  + [("ask-ink", "ask-bg", TEXT, "the Ask box"), ("ask-ink-2", "ask-bg", TEXT, "the Ask box")]
  + [(fg, bg, TEXT, "the panel") for fg in ("side-ink", "side-ink-2") for bg in ("side", "side-hi")] + [("side-link", "side-hi", TEXT, "the panel's links")]
  + [(f"p{i}-ink", bg, TEXT, "names") for i in range(1, 9) for bg in (f"p{i}-soft", "card")]
  + [(f"p{i}-on", f"p{i}", TEXT, "avatar letters") for i in range(1, 9)]
  + [("everyone-ink", "everyone-soft", TEXT, "Everyone's name"), ("everyone-on", "everyone", NONTEXT, "Everyone's house glyph")]
  + [("edge", bg, NONTEXT, "control edges") for bg in ("field", "card", "paper")]
  + [("focus", bg, NONTEXT, "the focus ring") for bg in ("paper", "card")]
  + [("primary", "paper", NONTEXT, "the primary button's shape"), ("send", "ask-bg", NONTEXT, "Send on the Ask box"), ("side-mark", "side-hi", NONTEXT, "you are here, on the panel")]
  + [(f"p{i}-mark", bg, NONTEXT, "a person's mark") for i in range(1, 9) for bg in ("card", "paper")]
  + [("everyone-mark", "card", NONTEXT, "Everyone's mark")]
)
PEOPLE_FLOOR = 6.0     # CIEDE2000 between any two avatars, and any two marks, under every vision
RED_FLOOR = 6.0        # late red against every person, done, the action colour and today, under every vision.
                       # Not against "needs a look" (amber): red and amber meet for red-green colour-blind
                       # eyes in every palette tried, so the system tells them apart by shape instead
                       # (late: a red rule and "N days late"; a look: the warning sign and its words).
PHOSPHOR_FLOOR = 12.0  # how far any other token must stay from phosphor green
# Kitchen Table's people were chosen before this check existed, and fall under the colour-blind floor.
# Recorded here, as measured, until the family decides (HANDOFF.md, open questions): a change that
# makes it worse still fails, and no other theme may be listed.
KNOWN = {"kitchen-table": {"people": 1.1, "red": 2.1}}

# ---------------------------------------------------------------- colour maths
def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def unlin(c): c = min(1, max(0, c)); return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
def lum(rgb): r, g, b = (lin(c) for c in rgb); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)
MACHADO = {  # severity 1.0, on linear RGB
  "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
  "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
  "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}
def simulate(rgb, kind):
    if kind == "normal": return rgb
    l = [lin(c) for c in rgb]; m = MACHADO[kind]
    return tuple(unlin(sum(m[i][j] * l[j] for j in range(3))) for i in range(3))
def lab(rgb):
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047; y = 0.2126 * r + 0.7152 * g + 0.0722 * b; z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)
def de2000(c1, c2):
    L1, a1, b1 = lab(c1); L2, a2, b2 = lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL = L2 - L1; dC = C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    hb = h1p + h2p if C1p * C2p == 0 else ((h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2)
    T = 1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb)) + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63))
    Sl = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2); Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))

# ---------------------------------------------------------------- reading a theme file
def parse(path):
    text = open(path).read()
    head = dict(re.findall(r"@theme ([a-z-]+):\s*([^\n]+)", text))
    name = os.path.basename(path)[:-4]
    body = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    blocks = []  # (selector, media, {token: value}, other declarations)
    for m in re.finditer(r"(@media[^{]+)\{\s*([^{}]+)\{([^{}]*)\}\s*\}|([^{}@]+)\{([^{}]*)\}", body):
        media, sel, decl = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (None, m.group(4), m.group(5))
        toks = dict((k, v.strip()) for k, v in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", decl))
        other = [d.strip() for d in decl.split(";") if d.strip() and not d.strip().startswith("--") and not d.strip().startswith("color-scheme")]
        blocks.append((" ".join(sel.split()), media and " ".join(media.split()), toks, other))
    return name, head, blocks

def modes(name, head, blocks, problems):
    first = head.get("first", "light")
    second = "dark" if first == "light" else "light"
    base = [b for b in blocks if not b[1] and "data-mode" not in b[0]]
    dev = [b for b in blocks if b[1]]
    chosen = [b for b in blocks if not b[1] and f'data-mode="{second}"' in b[0]]
    if len(base) != 1 or len(dev) != 1 or len(chosen) != 1:
        problems.append(f"expected three blocks (the {first} base, the {second} for the device, the {second} chosen); found {len(base)}, {len(dev)}, {len(chosen)}")
        return {}, {}
    if f'[data-theme="{name}"]' not in base[0][0]:
        problems.append(f'the base block must be keyed on [data-theme="{name}"]')
    if dev[0][2] != chosen[0][2]:
        diff = sorted(set(dev[0][2].items()) ^ set(chosen[0][2].items()))
        problems.append(f"the two {second} blocks differ: {diff[:4]}")
    for b in blocks:
        if b[3]: problems.append(f"not colour only, in {b[0]}: {b[3][:3]}")
    one = dict(base[0][2]); two = dict(one); two.update(dev[0][2])
    return (one, two) if first == "light" else (two, one)

def resolve(tokens, k):
    v = tokens.get(k, "")
    seen = 0
    while v.startswith("var(") and seen < 10:
        v = tokens.get(v[6:].split(")")[0].split(",")[0].strip(), ""); seen += 1
    return v

def check(path):
    name, head, blocks = parse(path)
    problems, notes = [], []
    for field in ("name", "line", "first", "theme-color"):
        if field not in head: problems.append(f"the header has no @theme {field}")
    light, dark = modes(name, head, blocks, problems)
    results = {}
    for mode, tok in (("light", light), ("dark", dark)):
        if not tok: continue
        missing = [t for t in CONTRACT if t not in tok]
        if missing: problems.append(f"{mode}: missing {', '.join(missing)}")
        extra = [t for t in tok if t.startswith(FIXED)]
        if extra: problems.append(f"{mode}: sets fixed tokens {', '.join(extra)} (the glass, phosphor, type and space are not a theme's)")
        unknown = [t for t in tok if t not in CONTRACT and not t.startswith(FIXED)]
        if unknown: notes.append(f"{mode}: tokens outside the contract, unused: {', '.join(unknown)}")
        col = {}
        for t in CONTRACT:
            v = resolve(tok, t)
            if re.fullmatch(r"#[0-9A-Fa-f]{3,6}", v or ""): col[t] = hex_rgb(v)
        rows = []
        for fg, bg, floor, what in PAIRS:
            if fg in col and bg in col:
                r = contrast(col[fg], col[bg]); rows.append((fg, bg, r, floor, what))
                if r < floor - 1e-9: problems.append(f"{mode}: {fg} on {bg} is {r:.2f}:1, under {floor}:1 ({what})")
        sep = {}
        for kind in ("normal", "protanopia", "deuteranopia", "tritanopia"):
            sim = {t: simulate(c, kind) for t, c in col.items()}
            for group, keys in (("avatars", [f"p{i}" for i in range(1, 9)]), ("marks", [f"p{i}-mark" for i in range(1, 9)])):
                best = min(((de2000(sim[a], sim[b]), a, b) for i, a in enumerate(keys) for b in keys[i + 1:] if a in sim and b in sim), default=None)
                if best:
                    sep[(group, kind)] = best
                    if best[0] < PEOPLE_FLOOR:
                        msg = f"{mode}, {kind}: {best[1]} and {best[2]} are only {best[0]:.1f} apart (floor {PEOPLE_FLOOR})"
                        known = KNOWN.get(name, {}).get("people")
                        (notes if known is not None and kind != "normal" and best[0] >= known - 0.05 else problems).append(("known, waiting on the family: " if known is not None and kind != "normal" and best[0] >= known - 0.05 else "") + msg)
            others = [f"p{i}-mark" for i in range(1, 9)] + [f"p{i}" for i in range(1, 9)] + ["ok", "primary", "link", "side-mark", "today-bg"]
            near = min(((de2000(sim["alert"], sim[o]), o) for o in others if o in sim and "alert" in sim), default=None)
            if near:
                sep[("red", kind)] = near
                if near[0] < RED_FLOOR:
                    msg = f"{mode}, {kind}: late red is only {near[0]:.1f} from {near[1]} (floor {RED_FLOOR})"
                    known = KNOWN.get(name, {}).get("red")
                    ok = known is not None and kind != "normal" and near[0] >= known - 0.05
                    (notes if ok else problems).append(("known, waiting on the family: " if ok else "") + msg)
        ph = hex_rgb(PHOSPHOR)
        for t, c in col.items():
            if t in NEAR_PHOSPHOR_OK: continue
            d = de2000(c, ph)
            if d < PHOSPHOR_FLOOR: problems.append(f"{mode}: {t} is {d:.1f} from phosphor green, which is Vera's alone")
        results[mode] = (tok, col, rows, sep)
    return name, head, problems, notes, results

# ---------------------------------------------------------------- the palette sheet
SHEET_CSS = """/* palette sheets: generated by _kit/theme-check.py --sheets; each swatch reads its theme's token */
body { margin: 0; padding: 24px; background: #FFFFFF; color: #1D2526; font: 400 15px/1.45 "Atkinson Hyperlegible", Arial, sans-serif; }
h1 { font: 600 32px/1.1 Fraunces, Georgia, serif; margin: 0 0 4px; } h2 { font: 600 20px/1.2 Fraunces, Georgia, serif; margin: 24px 0 8px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.mode { padding: 16px; border-radius: 12px; background: var(--paper); color: var(--ink); }
.mode h2 { margin-top: 0; color: var(--ink); }
.sws { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.sw { display: grid; grid-template-columns: 36px 1fr; gap: 8px; align-items: center; font-size: 13px; }
.sw i { display: block; width: 36px; height: 36px; border-radius: 8px; box-shadow: 0 0 0 1px rgba(127, 127, 127, .35); }
.sw b { display: block; font-weight: 700; }
.people { display: grid; grid-template-columns: repeat(9, 1fr); gap: 6px; margin-top: 12px; }
.av { display: grid; place-items: center; height: 40px; border-radius: 50%; font-weight: 700; }
table { border-collapse: collapse; width: 100%; font-size: 13px; } td, th { text-align: left; padding: 3px 6px; border-top: 1px solid #DDD; }
.bad { color: #B3381F; font-weight: 700; } .ok { color: #2B7148; }
"""
def sheet(name, head, problems, results, out):
    def swatches():
        return "".join(f'<div class="sw"><i class="t--{t}"></i><span><b>--{t}</b></span></div>' for t in CONTRACT if not t.startswith(("shadow", "ask-rim")))
    people = "".join(f'<span class="av t--p{i} on--p{i}">{"SAMT"[i - 1] if i <= 4 else i}</span>' for i in range(1, 9)) + '<span class="av t--everyone on--everyone">E</span>'
    def table(mode):
        tok, col, rows, sep = results[mode]
        tr = "".join(f'<tr><td>--{fg} on --{bg}</td><td>{what}</td><td class="{"ok" if r >= fl else "bad"}">{r:.2f}:1</td><td>{fl}:1</td></tr>' for fg, bg, r, fl, what in rows)
        sp = "".join(f'<tr><td>{g}</td><td>{k}</td><td>{v[0]:.1f}</td><td>{" and ".join(v[1:])}</td></tr>' for (g, k), v in sorted(sep.items()))
        return (f'<h2>{mode.capitalize()}: contrast</h2><table><tr><th>Pair</th><th>For</th><th>Measured</th><th>Floor</th></tr>{tr}</table>'
                f'<h2>{mode.capitalize()}: separation (CIEDE2000, closest pair)</h2><table><tr><th>Group</th><th>Vision</th><th>ΔE</th><th>Closest</th></tr>{sp}</table>')
    verdict = "Passes every floor." if not problems else "Fails: " + "; ".join(H.escape(p) for p in problems)
    page = f'''<!doctype html>
<html lang="en-GB">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(head.get("name", name))} · palette</title>
<link rel="stylesheet" href="../themes/{name}.css"><link rel="stylesheet" href="palette.css"></head>
<body>
<h1>{H.escape(head.get("name", name))}</h1>
<p>{H.escape(head.get("line", ""))} First: {head.get("first", "?")}. theme-color: {head.get("theme-color", "?")}.</p>
<p class="{"ok" if not problems else "bad"}">{verdict}</p>
<div class="cols">
  <section class="mode" data-theme="{name}" data-mode="light"><h2>Day</h2><div class="sws">{swatches()}</div><div class="people">{people}</div></section>
  <section class="mode" data-theme="{name}" data-mode="dark"><h2>Night</h2><div class="sws">{swatches()}</div><div class="people">{people}</div></section>
</div>
<div class="cols"><div>{table("light") if "light" in results else ""}</div><div>{table("dark") if "dark" in results else ""}</div></div>
</body></html>
'''
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, f"{name}.html"), "w").write(page)
    css = SHEET_CSS + "".join(f".t--{t} {{ background: var(--{t}); }}\n" for t in CONTRACT if not t.startswith(("shadow", "ask-rim")))
    css += "".join(f".on--p{i} {{ color: var(--p{i}-on); }}\n" for i in range(1, 9)) + ".on--everyone { color: var(--everyone-on); }\n"
    open(os.path.join(out, "palette.css"), "w").write(css)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = args or sorted(glob.glob(os.path.join(here, "themes", "*.css")))
    failed = 0
    for f in files:
        name, head, problems, notes, results = check(f)
        print(f"{name}: {'PASS' if not problems else 'FAIL'}")
        for mode in ("light", "dark"):
            if mode in results:
                rows, sep = results[mode][2], results[mode][3]
                low = min(rows, key=lambda r: r[2] / r[3]) if rows else None
                if low: print(f"  {mode}: weakest contrast {low[0]} on {low[1]} {low[2]:.2f}:1 (floor {low[3]})", end="; ")
                for g in ("avatars", "marks", "red"):
                    w = min((v for (gg, k), v in sep.items() if gg == g), default=None)
                    if w: print(f"{g} {w[0]:.1f}", end="  ")
                print()
        for p in problems: print("  FAIL", p)
        for n in notes: print("  note", n)
        failed += bool(problems)
        if "--sheets" in sys.argv:
            sheet(name, head, problems, results, os.path.join(here, "palette"))
    sys.exit(1 if failed else 0)
