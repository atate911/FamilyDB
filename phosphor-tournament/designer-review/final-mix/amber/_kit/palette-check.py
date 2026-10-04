#!/usr/bin/env python3
# Usage: python3 _kit/palette-check.py [style.css]
# Reads the colour tokens from style.css (:root, and the dark block), then checks, in both themes:
#  - text pairs: WCAG AA, 4.5:1;  - controls, stripes and plates: 3:1
#  - the eight people under normal vision and simulated protanopia, deuteranopia and tritanopia
#    (Machado 2009, CIEDE2000): the closest pair of avatars and of route stripes, and how far each
#    person sits from late red, the amber signal, Vera's green and the copper warning
#  - the signals against each other (amber vs copper vs red), so the three never read as one.
# Exits 1 if any floor fails.
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colourlib import contrast, de2000, simulate, min_pair, KINDS

css = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "style.css")).read()
light_src = css[css.index(":root {"):css.index("@media (prefers-color-scheme: dark)")]
dark_src = css[css.index("@media (prefers-color-scheme: dark)"):]
dark_src = dark_src[:dark_src.index("\n}\n")]
tok = lambda src: dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b", src))
LIGHT = tok(light_src)
DARK = {**LIGHT, **tok(dark_src)}
P = [f"p{i}" for i in range(1, 9)]

TEXT = [("ink", "paper"), ("ink", "paper-2"), ("ink", "card"), ("ink-2", "paper"), ("ink-2", "paper-2"), ("ink-3", "paper"),
        ("ink-3", "paper-2"), ("ink-3", "card"), ("link", "paper"), ("ink", "today-wash"), ("ink", "signal-wash"),
        ("on-band", "band"), ("on-band", "band-hi"), ("on-band-2", "band"), ("on-band-2", "band-hi"),
        ("on-signal", "signal"), ("signal", "screen"), ("signal", "band"), ("on-today", "today-bg"),
        ("on-primary", "primary"), ("on-primary", "primary-2"),
        ("vera", "paper"), ("vera", "vera-soft"), ("on-vera", "vera-bg"), ("ok", "paper"), ("ok", "ok-soft"),
        ("warn", "paper"), ("warn", "warn-soft"), ("alert", "paper"), ("alert", "alert-soft"), ("alert", "card"),
        ("on-alert-plate", "alert-plate"), ("everyone-ink", "everyone"), ("everyone-ink", "everyone-soft"),
        ("glass-ink", "glass"), ("glass-ink-2", "glass"), ("phosphor", "glass"), ("on-send", "send"), ("ask-ink-2", "ask-bg")]
TEXT += [(f"{p}-on", p) for p in P] + [(f"{p}-ink", b) for p in P for b in ("paper", f"{p}-soft", "card")] + [("ink", f"{p}-soft") for p in P]
EDGE = [("edge", "paper"), ("edge", "card"), ("edge", "paper-2"), ("focus", "paper"), ("focus", "card"), ("vera-bg", "paper"),
        ("primary", "paper"), ("signal", "band"), ("everyone-mark", "paper"), ("everyone-mark", "card")]
EDGE += [(f"{p}-mark", b) for p in P for b in ("paper", "card", "paper-2")]
# reported, not floors: decorative rules and plates whose words carry them
NOTE = [("signal-rule", "paper"), ("alert-plate", "band"), ("screen", "paper"), ("band", "paper"), ("ask-bg", "band"), ("glass", "band")]

fails = 0
def run(name, T):
    global fails
    print(f"\n== {name} ==")
    for floor, pairs in ((4.5, TEXT), (3.0, EDGE)):
        worst, bad = None, []
        for a, b in pairs:
            c = contrast(T[a], T[b])
            if worst is None or c < worst[0]: worst = (c, a, b)
            if c < floor: bad.append(f"{a} on {b} {c:.2f}")
        fails += len(bad)
        print(f"{'text AA' if floor == 4.5 else 'controls 3:1'}: {len(pairs) - len(bad)}/{len(pairs)} pass; lowest {worst[1]} on {worst[2]} {worst[0]:.2f}" + ("".join("\n  FAIL " + x for x in bad)))
    print("notes: " + "; ".join(f"{a} on {b} {contrast(T[a], T[b]):.2f}" for a, b in NOTE))
    print("avatar letters: " + ", ".join(f"{p} {contrast(T[p + '-on'], T[p]):.1f}" for p in P))
    for label, key in (("avatars", ""), ("stripes", "-mark")):
        cols = [T[p + key] for p in P]
        print(f"closest {label}: " + "; ".join("%s %.1f (%s/%s)" % ((k,) + tuple(min_pair(cols, P, (k,))[i] for i in (0, 2, 3))) for k in KINDS))
    sig = {"late": T["alert"], "amber": T["signal"], "vera": T["vera-bg"], "phosphor": T["phosphor"], "copper": T["warn"]}
    near = min((de2000(simulate(T[p + key], k), simulate(v, k)), k, p + key, n) for p in P for key in ("", "-mark") for n, v in sig.items() for k in KINDS)
    print("nearest person to a signal: %.1f (%s, %s vs %s)" % near)
    for a, b in (("signal", "warn"), ("warn", "alert"), ("signal", "alert"), ("signal", "vera-bg")):
        print(f"{a} vs {b}: " + ", ".join(f"{k} {de2000(simulate(T[a], k), simulate(T[b], k)):.1f}" for k in KINDS))

run("light", LIGHT)
run("dark", DARK)
print("\nall floors pass" if not fails else f"\n{fails} FAIL")
sys.exit(1 if fails else 0)
