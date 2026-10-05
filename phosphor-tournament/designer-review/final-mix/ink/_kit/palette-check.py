# python3 _kit/palette-check.py [style.css] [--json out.json]
# Reads the colour tokens from style.css (:root, and the dark block), then checks:
#  1. every contrast pair the pages use (text 4.5:1, controls, stripes and plates 3:1), light and dark;
#  2. the eight people under normal vision and simulated protanopia, deuteranopia and tritanopia
#     (Machado 2009, severity 1, CIEDE2000): avatars, day stripes and night stripes, closest pair;
#  3. how close any person comes to late red, Vera's green, phosphor and Everyone's grey.
# Exits 1 if any floor fails.
import sys, re, json, itertools, os
sys.path.insert(0, os.path.dirname(__file__))
from colour import contrast, de2000, simulate, KINDS

path = next((a for a in sys.argv[1:] if a.endswith(".css")), os.path.join(os.path.dirname(__file__), "..", "style.css"))
css = open(path).read()

def block(src):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b", src))

root_start = css.index(":root {")
light = block(css[root_start:css.index("}", root_start)])
dm = css.index("@media (prefers-color-scheme: dark)")
dark = dict(light); dark.update(block(css[dm:css.index("/* ---------- 3. Base", dm)]))
THEMES = {"light": light, "dark": dark}
PEOPLE = range(1, 9)

PAIRS = [  # (fg, bg, floor, use)
    ("ink", "paper", 4.5, "body text, heads, rules"),
    ("ink-2", "paper", 4.5, "secondary text, margin times"),
    ("ink-3", "paper", 4.5, "quiet text, labels"),
    ("ink-3", "paper-2", 4.5, "quiet text on a well"),
    ("ink-3", "card", 4.5, "placeholders"),
    ("ink-3", "today-wash", 4.5, "today's cell"),
    ("edge", "paper", 3, "control edges"),
    ("edge", "card", 3, "field edges"),
    ("edge", "paper-2", 3, "control edges on a well"),
    ("vera", "paper", 4.5, "Vera's name and rule"),
    ("vera", "vera-soft", 4.5, "the ready pill"),
    ("on-vera", "vera-bg", 4.5, "Vera's tile"),
    ("on-today", "today-bg", 4.5, "today's stamp"),
    ("today-bg", "today-wash", 3, "today's rule on its cell"),
    ("ok", "ok-soft", 4.5, "tag Working"),
    ("ok-line", "paper", 1, "(decorative)"),
    ("warn", "warn-soft", 4.5, "setup panel, Needs a look"),
    ("warn", "paper", 4.5, "step numbers"),
    ("warn-line", "warn-soft", 3, "Needs a look badge edge"),
    ("alert", "alert-soft", 4.5, "Not working, late badge"),
    ("alert", "paper", 4.5, "late text, OVERDUE"),
    ("alert", "paper-2", 4.5, "late text on a well"),
    ("on-done", "done", 4.5, "done tick, Yes stamp"),
    ("done", "paper", 3, "done tick box, strike, meter"),
    ("on-band", "band", 4.5, "panel text"),
    ("on-band-2", "band", 4.5, "panel quiet text"),
    ("on-band-2", "band-hi", 4.5, "account plate"),
    ("band", "on-band", 4.5, "you are here plate"),
    ("on-alert-plate", "alert-plate", 4.5, "late count on the panel"),
    ("alert-plate", "band", 3, "late plate against the panel"),
    ("ask-ink", "ask-bg", 4.5, "Ask text"),
    ("ask-ink-2", "ask-bg", 4.5, "Vera's line on the hero"),
    ("send", "ask-bg", 3, "Send against the glass"),
    ("on-send", "send", 4.5, "Send label"),
    ("phosphor", "glass", 4.5, "phosphor on glass"),
    ("glass-ink", "glass", 4.5, "pane text"),
    ("glass-alert", "glass", 4.5, "can't answer pill"),
    ("cursor", "paper", 3, "wordmark cursor"),
    ("everyone-mark", "paper", 3, "Everyone's stripe"),
    ("everyone-ink", "everyone", 4.5, "the house avatar"),
    ("everyone-ink", "everyone-soft", 4.5, "Everyone's wash"),
    ("paper", "ink", 4.5, "picked choice, Tomorrow stamp"),
    ("on-primary", "primary", 4.5, "primary button"),
    ("link", "paper", 4.5, "links"),
    ("focus", "paper", 3, "focus ring"),
]
for i in PEOPLE:
    PAIRS += [
        (f"p{i}-on", f"p{i}", 4.5, f"p{i} avatar letter"),
        (f"p{i}-ink", f"p{i}-soft", 4.5, f"p{i} name on wash"),
        (f"p{i}-ink", "paper", 4.5, f"p{i} name on paper"),
        ("ink", f"p{i}-soft", 4.5, f"words on p{i}'s event"),
        ("ink-2", f"p{i}-soft", 4.5, f"event time on p{i}"),
        (f"p{i}-mark", "paper", 3, f"p{i} stripe and rule"),
        (f"p{i}-mark", "paper-2", 1, f"p{i} stripe on a well (reported, not a floor)"),
    ]
# a kid's tab: her base under her letter; her ruling on the panel is decoration (the plate says where)

results, fails = [], 0
for theme, t in THEMES.items():
    for fg, bg, floor, use in PAIRS:
        r = contrast(t[fg], t[bg])
        ok = r >= floor
        fails += not ok
        results.append({"theme": theme, "fg": fg, "bg": bg, "ratio": round(r, 2), "floor": floor, "use": use, "ok": ok})

def closest(cols, names):
    out = {}
    for k in KINDS:
        sim = [simulate(c, k) for c in cols]
        d, i, j = min((de2000(sim[i], sim[j]), i, j) for i, j in itertools.combinations(range(len(cols)), 2))
        out[k] = (round(d, 1), names[i], names[j])
    return out

names = [f"p{i}" for i in PEOPLE]
cvd = {
    "avatars": closest([light[f"p{i}"] for i in PEOPLE], names),
    "stripes, day": closest([light[f"p{i}-mark"] for i in PEOPLE], names),
    "stripes, night": closest([dark[f"p{i}-mark"] for i in PEOPLE], names),
    "family of four, avatars": closest([light[f"p{i}"] for i in range(1, 5)], names[:4]),
}
signals = {}
for label, theme, key in (("avatars", light, ""), ("stripes, day", light, "-mark"), ("stripes, night", dark, "-mark")):
    for sig in ("alert", "vera", "vera-bg", "phosphor", "everyone-mark"):
        best = min((de2000(simulate(theme[f"p{i}{key}"], k), simulate(theme[sig], k)), f"p{i}", k) for i in PEOPLE for k in KINDS)
        signals[f"{label} vs {sig}"] = (round(best[0], 1), best[1], best[2])

if "--json" in sys.argv:
    json.dump({"light": light, "dark": dark, "pairs": results, "cvd": cvd, "signals": signals}, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)

for theme in THEMES:
    print(f"\n== {theme}")
    for r in results:
        if r["theme"] == theme and (not r["ok"] or "-v" in sys.argv):
            print(f"  {'FAIL' if not r['ok'] else 'ok  '} {r['fg']:>15} on {r['bg']:<14} {r['ratio']:5.2f} (≥{r['floor']})  {r['use']}")
    low = min((r for r in results if r["theme"] == theme and r["floor"] >= 4.5 and "avatar letter" in r["use"]), key=lambda r: r["ratio"])
    print(f"  lowest avatar letter: {low['fg']} {low['ratio']}")
print(f"\n{len(results)} pairs, {fails} below their floor")
print("\nColour-blind check, closest pair (CIEDE2000):")
for set_, o in cvd.items():
    print(f"  {set_:24} " + "  ".join(f"{k[:5]} {v[0]:>4} ({v[1]}/{v[2]})" for k, v in o.items()))
print("\nNearest any person comes to a signal (all four visions):")
for k, v in signals.items():
    print(f"  {k:34} {v[0]:>5}  {v[1]}, {v[2]}")
sys.exit(1 if fails else 0)
