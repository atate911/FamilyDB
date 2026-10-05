#!/usr/bin/env python3
"""Usage: python3 _kit/palette-check.py [style.css] [--json]

Reads the colour tokens from style.css (:root, and :root inside prefers-color-scheme: dark),
then checks, in both themes:
  - contrast: text pairs need 4.5:1 (WCAG AA), controls, stripes and plates need 3:1;
  - the eight people under simulated colour-blindness (Machado 2009, severity 1, in linear RGB),
    measured with CIEDE2000: the closest pair of avatars and of route stripes, for normal vision,
    protanopia, deuteranopia and tritanopia;
  - each person's distance from late red and from Vera's greens, and brass's from copper.
Exits 1 if any contrast floor fails."""
import re, sys, json, math, itertools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colour import contrast, simulate, de2000, tokens, resolve

css = open(next((a for a in sys.argv[1:] if not a.startswith("--")), "style.css")).read()

LIGHT, DARK = tokens(css)
val = resolve

P = [f"p{i}" for i in range(1, 9)]
NAMES = {"p1": "Sam", "p2": "Alex", "p3": "Maya", "p4": "Theo", "p5": "slot 5", "p6": "slot 6", "p7": "slot 7", "p8": "slot 8"}

def pairs():
    T = [
        ("ink", "paper", 4.5, "text"), ("ink", "paper-2", 4.5, "text on wells"), ("ink", "card", 4.5, "text on cards"),
        ("ink-2", "paper", 4.5, "secondary text"), ("ink-2", "paper-2", 4.5, "secondary on wells"),
        ("ink-3", "paper", 4.5, "quiet text"), ("ink-3", "paper-2", 4.5, "quiet on wells"), ("ink-3", "field", 4.5, "placeholder"),
        ("edge", "paper", 3, "control edges"), ("edge", "field", 3, "field edges"), ("edge", "paper-2", 3, "edges on wells"),
        ("link", "paper", 4.5, "links"), ("link-line", "paper", 3, "link underline"),
        ("on-primary", "primary", 4.5, "primary button text"), ("primary", "paper", 3, "primary button edge"),
        ("on-primary", "primary-2", 4.5, "primary hover"),
        ("focus", "paper", 3, "focus ring"), ("focus", "paper-2", 3, "focus ring on wells"),
        ("on-band", "band", 4.5, "panel text"), ("on-band-2", "band", 4.5, "panel quiet text"), ("on-band-2", "band-hi", 4.5, "panel quiet on raised"),
        ("on-band", "band-hi", 4.5, "panel hover"),
        ("brass-lit", "band", 3, "brass on panel"), ("band-focus", "band", 3, "focus on panel"),
        ("here-bg", "band", 3, "you-are-here plate on panel"), ("on-here", "here-bg", 4.5, "you-are-here text"),
        ("alert-plate", "band", 3, "late plate on panel"), ("on-alert-plate", "alert-plate", 4.5, "late plate text"),
        ("on-today", "today-bg", 4.5, "today stamp text"),
        ("today-ink", "paper", 4.5, "today date (greeting)"), ("ink", "today-wash", 4.5, "text in today's cell"),
        ("brass-ink", "paper", 4.5, "brass printed"),
        ("vera", "paper", 4.5, "Vera's green text"), ("on-vera", "vera-bg", 4.5, "on Vera's green"), ("vera-bg", "paper", 3, "done tick"),
        ("ok", "ok-soft", 4.5, "ok text"), ("ok", "paper", 4.5, "ok text on paper"),
        ("warn", "warn-soft", 4.5, "setup text"), ("warn", "paper", 4.5, "warn on paper"), ("ink", "warn-soft", 4.5, "text in setup panel"),
        ("ink-2", "warn-soft", 4.5, "secondary in setup panel"),
        ("alert", "alert-soft", 4.5, "late text on wash"), ("alert", "paper", 4.5, "late text"),
        ("ask-ink", "ask-bg", 4.5, "Vera's glass text"), ("ask-ink-2", "ask-bg", 4.5, "glass quiet text"),
        ("on-send", "send", 4.5, "Send"), ("phosphor", "glass", 4.5, "phosphor on glass"), ("send", "ask-bg", 3, "Send on glass"),
        ("everyone-ink", "everyone-soft", 4.5, "Everyone name"), ("everyone-on", "everyone", 4.5, "Everyone icon"),
        ("everyone-mark", "paper", 3, "Everyone stripe"),
    ]
    for p in P:
        T += [(f"{p}-on", p, 4.5, f"{p} avatar letter"), (f"{p}-ink", f"{p}-soft", 4.5, f"{p} name on wash"),
              (f"{p}-ink", "paper", 4.5, f"{p} name on paper"), (f"{p}-mark", "paper", 3, f"{p} stripe"),
              (f"{p}-mark", f"{p}-soft", 3, f"{p} rule on wash"), ("ink", f"{p}-soft", 4.5, f"text on {p} wash")]
    return T

report = {"contrast": {}, "cvd": {}, "fail": []}
for tname, th in (("light", LIGHT), ("dark", DARK)):
    rows = []
    for fg, bg, floor, what in pairs():
        c = contrast(val(th, "--" + fg), val(th, "--" + bg))
        rows.append((what, fg, bg, round(c, 2), floor))
        if c < floor: report["fail"].append(f"{tname}: {what} {fg} on {bg} = {c:.2f} < {floor}")
    report["contrast"][tname] = rows
    for set_name, suffix in (("avatars", ""), ("stripes", "-mark")):
        cols = {p: val(th, f"--{p}{suffix}") for p in P}
        for kind in ("normal", "protan", "deutan", "tritan"):
            best = min(((de2000(simulate(cols[a], kind), simulate(cols[b], kind)), a, b) for a, b in itertools.combinations(P, 2)))
            fam = min(((de2000(simulate(cols[a], kind), simulate(cols[b], kind)), a, b) for a, b in itertools.combinations(P[:4], 2)))
            red = min(((de2000(simulate(cols[a], kind), simulate(val(th, "--alert"), kind)), a) for a in P))
            green = min(((de2000(simulate(cols[a], kind), simulate(val(th, g), kind)), a, g) for a in P for g in ("--vera", "--phosphor", "--vera-bg")))
            report["cvd"][f"{tname} {set_name} {kind}"] = {
                "closest": [round(best[0], 1), best[1], best[2]], "family4": [round(fam[0], 1), fam[1], fam[2]],
                "nearest_red": [round(red[0], 1), red[1]], "nearest_vera": [round(green[0], 1), green[1], green[2]]}
    for kind in ("normal", "protan", "deutan", "tritan"):
        report["cvd"][f"{tname} brass vs copper {kind}"] = round(de2000(simulate(val(th, "--brass"), kind), simulate(val(th, "--warn"), kind)), 1)
        report["cvd"][f"{tname} copper vs red {kind}"] = round(de2000(simulate(val(th, "--warn"), kind), simulate(val(th, "--alert"), kind)), 1)

if "--json" in sys.argv:
    print(json.dumps(report, indent=1)); sys.exit(1 if report["fail"] else 0)

for tname in ("light", "dark"):
    rows = report["contrast"][tname]
    weakest = sorted(rows, key=lambda r: r[3] - r[4])[:6]
    print(f"{tname}: {len(rows)} pairs, {sum(r[3] >= r[4] for r in rows)} pass. Tightest: " + "; ".join(f"{w[0]} {w[3]}" for w in weakest))
    letters = [r for r in rows if r[0].endswith("avatar letter")]
    w = min(letters, key=lambda r: r[3]); print(f"  weakest avatar letter: {w[0]} {w[3]}:1")
for k, v in report["cvd"].items():
    if isinstance(v, dict):
        print(f"{k:28s} closest {v['closest'][0]:5} ({NAMES[v['closest'][1]]}/{NAMES[v['closest'][2]]})  family {v['family4'][0]:5} ({NAMES[v['family4'][1]]}/{NAMES[v['family4'][2]]})  red {v['nearest_red'][0]:5} ({NAMES[v['nearest_red'][1]]})  vera {v['nearest_vera'][0]:5} ({NAMES[v['nearest_vera'][1]]})")
    else:
        print(f"{k:28s} {v}")
print("FAILS:\n  " + "\n  ".join(report["fail"]) if report["fail"] else "All contrast floors pass in both themes.")
sys.exit(1 if report["fail"] else 0)
