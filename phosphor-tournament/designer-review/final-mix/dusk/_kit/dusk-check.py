# Dusk's checks, measured from the tokens in style.css (python3 _kit/dusk-check.py [--quiet]).
# 1. Contrast floors in both themes: text 4.5:1 (AA), controls, stripes and plates 3:1.
# 2. Colour-blind: the eight people's avatars and route stripes under Machado 2009 protanopia,
#    deuteranopia and tritanopia (severity 1), CIEDE2000; the closest pair, and how near any person
#    comes to late red, the apricot signal and Vera's green.
import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colourlib import contrast, simulate, de2000, read_tokens

here = os.path.dirname(os.path.abspath(__file__))
light, dark = read_tokens(open(os.path.join(here, "..", "style.css")).read())
quiet = "--quiet" in sys.argv
TEXT, UI = 4.5, 3.0

def pairs(t):
    P = [  # (foreground, background, floor, what)
        ("ink", "paper", TEXT, "body text"), ("ink-2", "paper", TEXT, "meta"), ("ink-3", "paper", TEXT, "quiet text"),
        ("ink-3", "paper-2", TEXT, "quiet text on a well"), ("ink-2", "card", TEXT, "meta on a field"),
        ("ink", "signal-soft", TEXT, "text on today's wash"), ("ink-3", "signal-soft", TEXT, "quiet text on today's wash"),
        ("edge", "paper", UI, "control edge"), ("edge", "paper-2", UI, "control edge on a well"), ("edge", "card", UI, "field edge"),
        ("focus", "paper", UI, "focus ring"), ("focus", "card", UI, "focus ring on a field"), ("focus", "paper-2", UI, "focus ring on a well"),
        ("link", "paper", TEXT, "link"),
        ("on-primary", "primary", TEXT, "primary button label"), ("primary-edge", "paper", UI, "primary button edge"),
        ("on-signal", "signal", TEXT, "Tomorrow stamp, today stamp"), ("on-today", "today-bg", TEXT, "today's day number"),
        ("today-ink", "paper", TEXT, "today's date in the greeting"), ("signal-mark", "paper", UI, "Leave by rule"),
        ("on-band", "band", TEXT, "panel lettering (top)"), ("on-band", "band-2", TEXT, "panel lettering (foot)"),
        ("on-band-2", "band", TEXT, "panel quiet text (top)"), ("on-band-2", "band-2", TEXT, "panel quiet text (foot)"),
        ("on-band-2", "band-hi", TEXT, "account plate text"), ("on-band", "band-hi", TEXT, "account plate name"),
        ("band", "on-band", TEXT, "you are here plate"), ("on-alert-plate", "alert-plate", TEXT, "late count plate"),
        ("phosphor", "band", UI, "focus ring on the panel"), ("phosphor", "band-2", UI, "focus ring on the panel's foot"),
        ("alert", "paper", TEXT, "late"), ("alert", "alert-soft", TEXT, "error banner"),
        ("warn", "paper", TEXT, "setup"), ("warn", "warn-soft", TEXT, "setup panel"),
        ("ok", "paper", TEXT, "working"), ("ok", "ok-soft", TEXT, "ok banner"),
        ("vera", "paper", TEXT, "Vera's green text"), ("on-vera", "vera-bg", TEXT, "done tick, Yes! stamp"),
        ("vera-bg", "paper", UI, "done tick box"),
        ("ink-3", "everyone-soft", TEXT, "quiet text on Everyone's wash"), ("everyone-ink", "everyone-soft", TEXT, "Everyone's name on wash"),
        ("everyone-mark", "paper", UI, "Everyone's stripe"), ("everyone-ink", "everyone", UI, "Everyone's house icon"),
        ("send", "glass", TEXT, "Send on the glass"), ("glass-ink", "glass", TEXT, "glass text"),
    ]
    for i in range(1, 9):
        P += [("on-p", f"p{i}", TEXT, f"p{i} avatar letter"),
              (f"p{i}-ink", "paper", TEXT, f"p{i} name on paper"), (f"p{i}-ink", f"p{i}-soft", TEXT, f"p{i} name on its wash"),
              ("ink", f"p{i}-soft", TEXT, f"text on p{i}'s wash"), ("ink-2", f"p{i}-soft", TEXT, f"meta on p{i}'s wash"),
              (f"p{i}-mark", "paper", UI, f"p{i} route stripe, rule"), (f"p{i}-mark", "paper-2", UI, f"p{i} stripe on the weekend wash")]
    return P

fails, total, worst = 0, 0, {}
for name, t in (("light", light), ("dark", dark)):
    for fg, bg, floor, what in pairs(t):
        if fg not in t or bg not in t: print("  missing token", fg, bg); continue
        r = contrast(t[fg], t[bg]); total += 1
        if r < floor: fails += 1; print(f"  FAIL {name:5} {what}: --{fg} {t[fg]} on --{bg} {t[bg]} = {r:.2f} (needs {floor})")
        elif not quiet and r < floor + .4: print(f"  near {name:5} {what}: {r:.2f}")
        key = "avatar letters" if "avatar" in what else None
        if key: worst[(name, key)] = min(worst.get((name, key), 99), r)
print(f"Contrast: {total - fails} of {total} pairs pass in both themes.", "Weakest avatar letter: %.2f:1" % min(worst.values()))

KINDS = ["normal", "protan", "deutan", "tritan"]
def closest(cols, label):
    out = []
    for k in KINDS:
        S = {n: simulate(h, k) for n, h in cols.items()}
        d, a, b = min((de2000(S[a], S[b]), a, b) for a, b in itertools.combinations(S, 2))
        out.append((d, k, a, b))
    lo = min(out)
    print(f"{label}: closest pair " + ", ".join(f"{k} {d:.1f} ({a}/{b})" for d, k, a, b in out) + f"  -> worst {lo[0]:.1f}")
    return lo
NAMES = ["p1 evening blue", "p2 sea", "p3 heather", "p4 sun gold", "p5 sky", "p6 olive", "p7 dusk cloud", "p8 sandstone"]
av = {NAMES[i]: light[f"p{i+1}"] for i in range(8)}
sd = {NAMES[i]: light[f"p{i+1}-mark"] for i in range(8)}
sn = {NAMES[i]: dark[f"p{i+1}-mark"] for i in range(8)}
print("Colour-blind check (Machado 2009, CIEDE2000):")
closest(av, "  avatars"); closest(sd, "  day stripes"); closest(sn, "  night stripes")
fam = {k: v for k, v in av.items() if k[:2] in ("p1", "p2", "p3", "p4")}
closest(fam, "  the family's four avatars")
for th, t, cols in (("day", light, {**av, **sd}), ("night", dark, {**av, **sn})):
    for ref, rn in (("alert", "late red"), ("signal", "apricot signal"), ("phosphor", "Vera's phosphor"), ("vera", "Vera's green text"), ("vera-bg", "done green")):
        m = min((de2000(simulate(h, k), simulate(t[ref], k)), k, n) for n, h in cols.items() for k in KINDS)
        print(f"  {th:5} nearest person to {rn}: {m[0]:.1f} ({m[2]}, {m[1]})")
for th, t in (("day", light), ("night", dark)):
    m = min((de2000(simulate(t["alert"], k), simulate(t["signal"], k)), k) for k in KINDS)
    print(f"  {th:5} late red vs apricot signal: {m[0]:.1f} at worst ({m[1]})")
    m = min((de2000(simulate(t["warn"], k), simulate(t["alert"], k)), k) for k in KINDS)
    print(f"  {th:5} setup honey vs late red (text): {m[0]:.1f} at worst ({m[1]})")

if "--table" in sys.argv:  # the table for STANDARD.md §7
    ROWS = [("ink", "paper", "body text, heads, rules"), ("ink-2", "paper", "secondary text, margin times"),
            ("ink-3", "paper", "quiet text, labels, entry numbers"), ("ink-3", "paper-2", "quiet text on a well or the weekend wash"),
            ("ink-3", "card", "placeholders"), ("ink-3", "today-wash", "today's cell"),
            ("edge", "paper", "control edges, tick boxes (3:1)"), ("edge", "card", "field edges (3:1)"),
            ("focus", "paper", "the focus ring (3:1)"), ("cursor", "paper", "the wordmark's lit cursor (non-text, 3:1)"),
            ("vera", "paper", "Vera's name and rule"), ("vera", "vera-soft", "the calm pill"),
            ("on-vera", "vera-bg", "done tick, \"Yes!\" stamp, flash check"),
            ("on-today", "today-bg", "today's stamp and calendar number"), ("today-ink", "paper", "today's date in the greeting"),
            ("on-signal", "signal", "the \"Tomorrow\" stamp"), ("on-primary", "primary", "the primary button's label"),
            ("primary-edge", "paper", "the primary button's edge (3:1)"), ("signal-mark", "paper", "Leave by's rule, link underlines (3:1)"),
            ("ok", "ok-soft", "tag Working"), ("warn", "warn-soft", "tag Needs a look, setup panel"), ("warn", "paper", "step numbers, Could be better"),
            ("alert", "alert-soft", "tag Not working, late badge"), ("alert", "paper", "late text, \"OVERDUE\" head, errors"),
            ("on-band", "band", "panel lettering (top of the panel)"), ("on-band", "band-2", "panel lettering (its foot)"),
            ("on-band-2", "band-2", "panel quiet text (weakest point)"), ("on-band-2", "band-hi", "the account plate"),
            ("band", "on-band", "you are here: the inverted plate"), ("on-alert-plate", "alert-plate", "the late count on the panel"),
            ("phosphor", "band", "focus on the panel (3:1)"),
            ("everyone-mark", "paper", "Everyone's rule (3:1)"), ("everyone-ink", "everyone", "the house avatar"),
            ("phosphor", "glass", "phosphor on glass"), ("glass-ink", "glass", "pane text"), ("ask-ink", "ask-bg", "Ask text")]
    print("| Pair | Use | Light | Dark |\n|---|---|---:|---:|")
    for fg, bg, use in ROWS:
        print(f"| `--{fg}` on `--{bg}` | {use} | {contrast(light[fg], light[bg]):.1f} | {contrast(dark[fg], dark[bg]):.1f} |")
    for lab, fg, bg in (("`--on-p` on `--p1…p8`", "on-p", "p{}"), ("`--pN-ink` on `--pN-soft`", "p{}-ink", "p{}-soft"),
                        ("`--pN-ink` on `--paper`", "p{}-ink", "paper"), ("`--pN-mark` on `--paper`", "p{}-mark", "paper"),
                        ("`--pN-mark` on `--paper-2`", "p{}-mark", "paper-2"), ("`--ink` on `--pN-soft`", "ink", "p{}-soft"),
                        ("`--ink-2` on `--pN-soft`", "ink-2", "p{}-soft")):
        lo = [min(contrast(th[fg.format(i)], th[bg.format(i)]) for i in range(1, 9)) for th in (light, dark)]
        print(f"| {lab} | lowest of the eight | {lo[0]:.1f} | {lo[1]:.1f} |")
sys.exit(1 if fails else 0)
