#!/usr/bin/env python3
"""Check every look in themes.css against what Kitchen Table's layout needs, and draw a palette
sheet for each.

    python3 _kit/looks-check.py            # every look; exit 1 if any fails a floor
    python3 _kit/looks-check.py --sheets   # also write palette/<look>.html

It reads themes.css as the built app's tests do (one [data-theme="…"] block per look, each colour
written light-dark(day, night) or once for both). Tokens a look doesn't name come from the
[data-theme] block of derived defaults, worked out from the look's own tokens, exactly as the page
does (color-mix in sRGB and var() are evaluated here too).

Three sets of checks:
  A. The built floors, as tests/test_look.py holds them (4.5:1 words, 4:1 a colour on a well,
     3:1 edges and focus, words on each colour as a fill, a colour on its 10 % tint).
  B. The pairs Kitchen Table's layout draws that the built pages don't: the panel's links and
     its current item, Vera's box and its Send, each meaning on its wash, the late plate, words on
     Vera's fills, each person's name, mark and letter.
  C. The eight people and late red, under simulated colour blindness (Machado 2009, CIEDE2000).
     Kitchen Table's three known shortfalls are recorded, not failed (HANDOFF.md §9).
No dependencies beyond Python 3. In the app: tests/test_look.py gains B and C (HANDOFF.md §7).
"""
import math, os, re, sys, html as H

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT, WELL, NONTEXT = 4.5, 4.0, 3.0
PEOPLE_FLOOR, RED_FLOOR = 6.0, 6.0
KNOWN = {"kitchen": {"people": 1.1, "red": 2.1}}   # recorded, as measured; worse fails

# ---------------------------------------------------------------- colour maths
def rgb(h):
    h = h.lstrip("#"); h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def hexs(c): return "#" + "".join(f"{round(max(0, min(1, x)) * 255):02X}" for x in c)
def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def unlin(c): c = min(1, max(0, c)); return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
def lum(c): r, g, b = (lin(x) for x in c); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(a, b): x, y = sorted((lum(a), lum(b)), reverse=True); return (x + 0.05) / (y + 0.05)
MACHADO = {"protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
           "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
           "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900))}
def sim(c, k):
    if k == "normal": return c
    l = [lin(x) for x in c]; m = MACHADO[k]
    return tuple(unlin(sum(m[i][j] * l[j] for j in range(3))) for i in range(3))
def lab(c):
    r, g, b = (lin(x) for x in c)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047; y = 0.2126 * r + 0.7152 * g + 0.0722 * b; z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))
def de(c1, c2):
    L1, a1, b1 = lab(c1); L2, a2, b2 = lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))); a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1 = math.degrees(math.atan2(b1, a1p)) % 360; h2 = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2 - h1 if abs(h2 - h1) <= 180 else h2 - h1 - 360 if h2 > h1 else h2 - h1 + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2)); Lb = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    hb = h1 + h2 if C1p * C2p == 0 else ((h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2)
    T = 1 - .17 * math.cos(math.radians(hb - 30)) + .24 * math.cos(math.radians(2 * hb)) + .32 * math.cos(math.radians(3 * hb + 6)) - .2 * math.cos(math.radians(4 * hb - 63))
    Sl = 1 + .015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2); Sc = 1 + .045 * Cbp; Sh = 1 + .015 * Cbp * T
    Rt = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))

# ---------------------------------------------------------------- reading themes.css
def blocks(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        toks = dict((k, v.strip()) for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body))
        for one in sel.split(","):
            m = re.fullmatch(r'\s*\[data-theme(?:="([a-z-]+)")?\]\s*', one)
            if m: out.setdefault(m.group(1) or "*", {}).update(toks)   # later blocks add to a look, as CSS does
    return out

def split_ld(v):
    m = re.fullmatch(r"light-dark\((.*)\)", v.strip())
    if not m: return v, v
    depth, parts, cur = 0, [], ""
    for ch in m.group(1):
        if ch == "(": depth += 1
        if ch == ")": depth -= 1
        if ch == "," and depth == 0: parts.append(cur); cur = ""
        else: cur += ch
    parts.append(cur)
    return parts[0].strip(), parts[1].strip()

def name_is_paper(v): return False

def evaluate(tokens, mode):
    """Every token of a look as a colour (r, g, b) in one mode, or None when it isn't one."""
    memo = {}
    def val(name, depth=0):
        if name in memo: return memo[name]
        raw = tokens.get(name)
        memo[name] = None if raw is None or depth > 12 else expr(split_ld(raw)[0 if mode == "day" else 1], depth)
        return memo[name]
    def expr(v, depth):
        v = v.strip()
        if re.fullmatch(r"#[0-9A-Fa-f]{3,6}", v): return rgb(v)
        m = re.fullmatch(r"rgb\((\d+) (\d+) (\d+)(?: / ([\d.]+))?\)", v)
        if m:
            c = tuple(int(m[i]) / 255 for i in (1, 2, 3)); a = float(m[4]) if m[4] else 1
            if a >= 1 or name_is_paper(v): return c
            under = val("--paper", depth + 1) or (0, 0, 0)
            return tuple(c[i] * a + under[i] * (1 - a) for i in range(3))
        m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", v)
        if m: return val(m[1], depth + 1)
        m = re.fullmatch(r"light-dark\(.*\)", v)
        if m: return expr(split_ld(v)[0 if mode == "day" else 1], depth)
        m = re.fullmatch(r"color-mix\(in srgb, (.+?) (\d+(?:\.\d+)?)%, (.+)\)", v)
        if m:
            a, b = expr(m[1], depth), expr(m[3], depth)
            if a is None or b is None: return None
            p = float(m[2]) / 100
            return tuple(a[i] * p + b[i] * (1 - p) for i in range(3))
        return None
    return {k: val(k) for k in tokens}

def looks():
    css = open(os.path.join(HERE, "themes.css")).read()
    bl = blocks(css)
    derived = bl.pop("*", {})
    out = {}
    for key, toks in bl.items():
        full = dict(derived); full.update(toks)
        out[key] = (toks, full)
    return out, derived

# ---------------------------------------------------------------- the checks
BUILT_TEXT = ("ink", "ink-2", "ink-3", "link", "red", "amber", "ok", "vera", "lilac", "cyan", "lemon", "pink", "orange")
def built_pairs(c):
    p = []
    for n in BUILT_TEXT:
        p += [(f"{n} on paper", n, "paper", TEXT), (f"{n} on card", n, "card", TEXT)]
    for n in ("red", "ok", "vera", "cyan", "lilac"): p.append((f"{n} on a well", n, "paper-2", WELL))
    p += [("on-band", "on-band", "band", TEXT), ("on-band-2", "on-band-2", "band", TEXT), ("on-band on a hover", "on-band", "band-hi", TEXT),
          ("on-here", "on-here", "here", TEXT), ("on-primary", "on-primary", "primary", TEXT), ("on-today", "on-today", "today", TEXT),
          ("today-rule", "today-rule", "paper", TEXT), ("today-rule on its wash", "today-rule", "today-wash", TEXT), ("ink on today's wash", "ink", "today-wash", TEXT),
          ("on-person", "on-person", "person", TEXT), ("edge on a card", "edge", "card", NONTEXT), ("edge on a field", "edge", "field", NONTEXT), ("focus", "focus", "paper", NONTEXT)]
    for n in ("lilac", "cyan", "lemon", "pink", "orange", "amber", "red", "ok", "vera"): p.append((f"on-bright on {n}", "on-bright", n, TEXT))
    return p
KT_PAIRS = (
    [("the panel's links on its current item", "band-link", "band-hi", TEXT), ("the panel's mark on its current item", "here-icon", "here", NONTEXT),
     ("Vera's words in her box", "ask-ink", "ask-bg", TEXT), ("Vera's quiet words in her box", "ask-ink-2", "ask-bg", TEXT),
     ("Send", "on-send", "send", TEXT),
     ("words on Vera's fill", "on-vera", "vera-bg", TEXT), ("Vera on her wash (the pill)", "vera", "vera-soft", TEXT),
     ("the late plate", "on-red", "red", TEXT)]
    + [(f"{m} on its wash", m, f"{m}-soft", TEXT) for m in ("ok", "amber", "red")]
    + [(f"p{i}'s name on its wash", f"p{i}-ink", f"p{i}-soft", TEXT) for i in range(1, 9)]
    + [(f"p{i}'s name on a card", f"p{i}-ink", "card", TEXT) for i in range(1, 9)]
    + [(f"p{i}'s letter", f"p{i}-on", f"p{i}", TEXT) for i in range(1, 9)]
    + [(f"p{i}'s mark on a card", f"p{i}-mark", "card", NONTEXT) for i in range(1, 9)]
)

def check(key, own, full):
    problems, notes, rows, seps = [], [], {}, {}
    own_people = "--p1" in own or key == "kitchen"   # the people in the [data-theme] block are Kitchen Table's
    night_only = key == "phosphor"   # a green screen has no day (looks.py: has_day=False)
    for mode in (("night",) if night_only else ("day", "night")):
        c = evaluate(full, mode)
        rows[mode] = []
        kt_pairs = KT_PAIRS if own_people else [x for x in KT_PAIRS if not re.match(r"p\d", x[1])]
        for group, pairs in (("built", built_pairs(c)), ("Kitchen Table's layout", kt_pairs)):
            for what, fg, bg, floor in pairs:
                a, b = c.get("--" + fg), c.get("--" + bg)
                if a is None or b is None:
                    problems.append(f"{mode}: --{fg} or --{bg} isn't a colour"); continue
                r = contrast(a, b); rows[mode].append((group, what, fg, bg, r, floor))
                if r < floor - 0.005: problems.append(f"{mode}: {what} (--{fg} on --{bg}) is {r:.2f}:1, under {floor}:1 [{group}]")
        for kind in ("normal", "protanopia", "deuteranopia", "tritanopia"):
            s = {k: sim(v, kind) for k, v in c.items() if v is not None}
            for g, keys in ((("avatars", [f"--p{i}" for i in range(1, 9)]), ("marks", [f"--p{i}-mark" for i in range(1, 9)])) if own_people else ()):
                best = min((de(s[a], s[b]), a, b) for i, a in enumerate(keys) for b in keys[i + 1:])
                seps[(mode, g, kind)] = best
                if best[0] < PEOPLE_FLOOR:
                    known = KNOWN.get(key, {}).get("people")
                    msg = f"{mode}, {kind}: {best[1]} and {best[2]} are {best[0]:.1f} apart (floor {PEOPLE_FLOOR})"
                    if known is not None and kind != "normal" and best[0] >= known - .05: notes.append("known: " + msg)
                    else: problems.append(msg)
            others = ([f"--p{i}{v}" for i in range(1, 9) for v in ("", "-mark")] if own_people else []) + ["--ok", "--primary", "--link", "--today"]
            near = min((de(s["--red"], s[o]), o) for o in others)
            seps[(mode, "red", kind)] = near
            if near[0] < RED_FLOOR:
                known = KNOWN.get(key, {}).get("red")
                msg = f"{mode}, {kind}: late red is {near[0]:.1f} from {near[1]} (floor {RED_FLOOR})"
                if known is not None and kind != "normal" and near[0] >= known - .05: notes.append("known: " + msg)
                else: problems.append(msg)
    return problems, notes, rows, seps

SHEET_CSS = """body { margin: 0; padding: 24px; background: #FFFFFF; color: #1D2526; font: 400 15px/1.45 "Atkinson Hyperlegible", Arial, sans-serif; }
h1 { font: 600 32px/1.1 Georgia, serif; margin: 0 0 4px; } h2 { font: 600 20px/1.2 Georgia, serif; margin: 24px 0 8px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.mode { padding: 16px; border-radius: 12px; background: var(--paper); color: var(--ink); }
.mode h2 { margin-top: 0; color: var(--ink); }
.sws { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.sw { display: grid; grid-template-columns: 36px 1fr; gap: 8px; align-items: center; font-size: 13px; }
.sw i { display: block; width: 36px; height: 36px; border-radius: 8px; box-shadow: 0 0 0 1px rgba(127, 127, 127, .35); }
table { border-collapse: collapse; width: 100%; font-size: 13px; } td, th { text-align: left; padding: 3px 6px; border-top: 1px solid #DDD; }
.bad { color: #B3381F; font-weight: 700; } .ok { color: #2B7148; }
"""
def sheet(key, full, problems, rows, seps, toks):
    sw = "".join(f'<div class="sw"><i class="t{toks.index(t)}"></i><b>{t}</b></div>' for t in toks)
    def table(mode):
        tr = "".join(f'<tr><td>{H.escape(w)}</td><td>{g}</td><td class="{"ok" if r >= fl - .005 else "bad"}">{r:.2f}:1</td><td>{fl}:1</td></tr>' for g, w, fg, bg, r, fl in rows[mode])
        sp = "".join(f'<tr><td>{g}</td><td>{k}</td><td>{v[0]:.1f}</td><td>{" and ".join(v[1:])}</td></tr>' for (m, g, k), v in sorted(seps.items()) if m == mode)
        return f'<h2>{mode.capitalize()}</h2><table><tr><th>Pair</th><th>Set</th><th>Measured</th><th>Floor</th></tr>{tr}</table><h2>{mode.capitalize()}: closest pairs</h2><table><tr><th>Group</th><th>Vision</th><th>ΔE</th><th>Pair</th></tr>{sp}</table>'
    verdict = "Passes every floor." if not problems else "Fails: " + "; ".join(H.escape(p) for p in problems)
    page = f'''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{key} · palette</title><link rel="stylesheet" href="../themes.css"><link rel="stylesheet" href="palette.css"></head><body>
<h1>{key}</h1><p class="{"ok" if not problems else "bad"}">{verdict}</p>
<div class="cols"><section class="mode" data-theme="{key}" data-mode="light"><h2>Day</h2><div class="sws">{sw}</div></section>
<section class="mode" data-theme="{key}" data-mode="dark"><h2>Night</h2><div class="sws">{sw}</div></section></div>
<div class="cols">{"".join(f"<div>{table(m)}</div>" for m in ("day", "night") if m in rows)}</div></body></html>
'''
    os.makedirs(os.path.join(HERE, "palette"), exist_ok=True)
    open(os.path.join(HERE, "palette", f"{key}.html"), "w").write(page)
    css = SHEET_CSS + "".join(f".t{i} {{ background: var({t}); }}\n" for i, t in enumerate(toks))
    return css

if __name__ == "__main__":
    all_looks, derived = looks()
    failed = 0; css = SHEET_CSS
    for key, (own, full) in all_looks.items():
        problems, notes, rows, seps = check(key, own, full)
        uses = sorted(k for k in derived if k not in own)
        print(f"{key}: {'PASS' if not problems else 'FAIL'}" + (f"  (takes {len(uses)} derived roles)" if uses and key != "kitchen" else ""))
        for p in problems: print("  FAIL", p)
        for n in notes: print("  note", n)
        failed += bool(problems)
        if "--sheets" in sys.argv:
            toks = [k for k in all_looks["kitchen"][1] if evaluate(all_looks["kitchen"][1], "day").get(k) is not None]
            css = sheet(key, full, problems, rows, seps, toks)
    if "--sheets" in sys.argv: open(os.path.join(HERE, "palette", "palette.css"), "w").write(css)
    sys.exit(1 if failed else 0)
