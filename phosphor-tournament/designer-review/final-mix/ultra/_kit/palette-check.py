#!/usr/bin/env python3
# Usage: python3 _kit/palette-check.py [style.css] [--quiet]
# Reads the light and dark token blocks from style.css, resolves var() references, and checks:
#   1. contrast: text pairs at AA (4.5:1) and controls, stripes and plates at 3:1, in both themes;
#   2. the eight people (+ Everyone) under normal vision and simulated protanopia, deuteranopia and
#      tritanopia (Machado 2009, severity 1), CIEDE2000: the closest pair of avatars and of stripes,
#      and each person's distance from late red, Vera's green and the ultramarine.
# Exits 1 if any contrast pair fails.
import os, re, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colour import contrast, de, mix

KINDS = ["normal", "protan", "deutan", "tritan"]

def blocks(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    light = re.search(r"(?m)^:root\s*\{(.*?)\n\}", css, re.S).group(1)
    dark = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\}", css, re.S).group(1)
    parse = lambda b: dict(re.findall(r"--([\w-]+):\s*([^;]+);", b))
    L = parse(light); D = dict(L); D.update(parse(dark))
    return L, D

def resolve(t, name, seen=()):
    v = t[name].strip()
    m = re.fullmatch(r"var\(--([\w-]+)\)", v)
    if m: return resolve(t, m.group(1), seen + (name,))
    return v.upper() if v.startswith("#") else v

def tokens(css):
    out = []
    for t in blocks(css):
        out.append({k: resolve(t, k) for k in t if re.fullmatch(r"#[0-9A-Fa-f]{6}|var\(--[\w-]+\)", t[k].strip())})
    return out

PEOPLE = [f"p{i}" for i in range(1, 9)]

def pairs(t):
    """(label, fg, bg, floor). fg/bg are token names; bg may be 'name@over' for a translucent mix."""
    P = []
    txt = lambda f, b: P.append((f"{f} on {b}", f, b, 4.5))
    ui = lambda f, b, why="": P.append((f"{f} on {b}" + (f" ({why})" if why else ""), f, b, 3.0))
    for f in ("ink", "ink-2", "ink-3"):
        for b in ("paper", "paper-2", "card", "field"): txt(f, b)
    for b in ("paper", "paper-2", "card", "warn-soft", "act-soft"): txt("link", b)
    txt("link-2", "paper"); txt("act", "paper"); txt("act", "paper-2")
    txt("on-primary", "primary"); txt("on-primary", "primary-2"); txt("on-act", "act-bg"); txt("on-act", "act-bg-2")
    txt("on-today", "today-bg"); txt("ink", "today-wash")
    for f in ("on-band", "on-band-2"):
        for b in ("band", "band-hi"): txt(f, b)
    txt("band", "on-band")
    txt("on-alert-plate", "alert-plate")
    for b in ("paper", "paper-2", "alert-soft"): txt("alert", b)
    for b in ("paper", "warn-soft"): txt("warn", b)
    txt("ink", "warn-soft"); txt("ink-2", "warn-soft"); txt("ink-3", "warn-soft")
    for b in ("paper", "ok-soft"): txt("ok", b)
    for b in ("paper", "vera-soft"): txt("vera", b)
    txt("on-vera", "vera-bg")
    txt("everyone-ink", "everyone-soft"); txt("everyone-ink", "paper")
    for p in PEOPLE:
        txt(f"{p}-on", p)                       # the avatar letter, and a kid's current tab
        txt(f"{p}-ink", f"{p}-soft"); txt(f"{p}-ink", "paper")
        txt("ink", f"{p}-soft")                 # calendar event titles on the wash
        ui(f"{p}-mark", "paper", "stripe, rule")
        ui(f"{p}-mark", f"{p}-soft", "event stripe on its wash")
    ui("everyone-mark", "paper", "stripe"); ui("everyone-ink", "everyone", "house icon")
    for b in ("paper", "paper-2", "field"): ui("edge", b, "control edge")
    ui("primary", "paper", "button"); ui("act-bg", "paper-2"); ui("today-bg", "paper", "today stamp")
    ui("focus", "paper", "focus ring"); ui("focus", "paper-2", "focus ring")
    ui("act-bg", "on-band", "you-are-here edge")
    ui("alert-plate", "band", "late plate on the panel")
    ui("phosphor", "band", "wordmark cursor on the panel")
    ui("rule", "paper", "section rail")
    # Vera's glass
    txt("ask-ink", "ask-bg"); txt("ask-ink-2", "ask-bg"); txt("on-send", "send")
    txt("phosphor", "glass"); txt("glass-ink", "glass"); ui("send", "ask-bg", "Send on glass")
    return P

def check(css_path, quiet=False):
    L, D = tokens(open(css_path).read())
    fails, n, worst = [], 0, {}
    for name, t in (("day", L), ("night", D)):
        for label, f, b, floor in pairs(t):
            c = contrast(t[f], t[b]); n += 1
            if c < floor: fails.append(f"{name}: {label} {t[f]} / {t[b]} = {c:.2f} (needs {floor})")
            key = (name, floor)
            if key not in worst or c < worst[key][0]: worst[key] = (c, label)
    print(f"Contrast: {n} pairs, {len(fails)} below their floor.")
    for k, (c, label) in sorted(worst.items()):
        print(f"  lowest {k[0]} {'text' if k[1] == 4.5 else 'control'} pair: {c:.2f}  {label}")
    for f in fails: print("  FAIL", f)
    # A kid's colour also edges her you-are-here plate and the phone's top bar. It is decoration there (the
    # plate itself, white on the panel, says where you are), so it is reported, not held to 3:1.
    low = min((contrast(t[p], t[b]), n, p, b) for n, t in (("day", L), ("night", D)) for p in PEOPLE for b in ("band", "on-band"))
    print(f"  (decorative: a kid's edge on the panel or plate, lowest {low[0]:.2f}, {low[1]} {low[2]} on {low[3]})")
    print("\nAvatar letters:", ", ".join(f"{p} {contrast(L[p + '-on'], L[p]):.1f}/{contrast(D[p + '-on'], D[p]):.1f}" for p in PEOPLE), "(day/night)")
    print("\nColour-blind check (CIEDE2000 after simulation; bigger is further apart):")
    report = {}
    for name, t in (("day", L), ("night", D)):
        for what, suf in (("avatars", ""), ("stripes", "-mark")):
            cols = {p: t[p + suf] for p in PEOPLE}
            cols["everyone"] = t["everyone" + ("-mark" if suf else "")]
            row = []
            for k in KINDS:
                best = min((de(cols[a], cols[b], k), a, b) for a, b in itertools.combinations(cols, 2))
                row.append(best)
            report[(name, what)] = row
            print(f"  {name:5} {what:8} " + "  ".join(f"{k}: {d:4.1f} ({a}/{b})" for k, (d, a, b) in zip(KINDS, row)))
        sig = {"late": t["alert"], "Vera": t["vera"], "phosphor": t["phosphor"], "ultramarine": t["act-bg"]}
        near = min((min(de(t[p + suf], v, k) for k in KINDS), p + suf, s) for p in PEOPLE for suf in ("", "-mark") for s, v in sig.items())
        print(f"  {name:5} nearest person to a signal: {near[0]:.1f} ({near[1]} / {near[2]})")
    fam = ["p1", "p2", "p3", "p4"]
    for name, t in (("day", L), ("night", D)):
        d = min((min(de(t[a], t[b], k) for k in KINDS), a, b) for a, b in itertools.combinations(fam, 2))
        print(f"  {name:5} closest pair among the family's four (p1–p4): {d[0]:.1f} ({d[1]}/{d[2]})")
    print("\nPanel and glass side by side: day %.2f:1, night %.2f:1 (hue keeps them apart: midnight blue against green-black)."
          % (contrast(L["band"], L["glass"]), contrast(D["band"], D["glass"])))
    return not fails

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style.css")
    sys.exit(0 if check(path, "--quiet" in sys.argv) else 1)
