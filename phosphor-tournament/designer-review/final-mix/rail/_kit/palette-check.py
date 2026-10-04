#!/usr/bin/env python3
"""Measure the palette from the tokens in style.css: every contrast pair the standard promises,
in light and dark, and how far apart the eight people stay under protanopia, deuteranopia and
tritanopia (Machado 2009 at full severity, distance as CIEDE2000).
Usage: python3 _kit/palette-check.py [style.css]"""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from colourlib import contrast, closest, simulate, de2000

css = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "style.css")).read()
def block(start):
    i = css.index(start); i = css.index("{", i) + 1; depth = 1; j = i
    while depth:
        depth += {"{": 1, "}": -1}.get(css[j], 0); j += 1
    return css[i:j - 1]
def tokens(text):
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", text)}
light = tokens(block(":root {"))
dark = dict(light); dark.update(tokens(block("@media (prefers-color-scheme: dark)")))
def val(t, name):
    v = t[name]
    while v.startswith("var("): v = t[v[6:-1]]
    return v

# (front, back, floor, use)
PAIRS = [
    ("ink", "paper", 4.5, "body text, heads, rules"),
    ("ink-2", "paper", 4.5, "secondary text, margin times"),
    ("ink-3", "paper", 4.5, "quiet text, labels"),
    ("ink-3", "paper-2", 4.5, "quiet text on a well, the weekend wash"),
    ("ink-3", "card", 4.5, "placeholders"),
    ("ink-3", "today-wash", 4.5, "quiet text in today's cell"),
    ("edge", "paper", 3, "control edges, tick boxes"),
    ("edge", "card", 3, "field edges"),
    ("link", "paper", 4.5, "links"),
    ("link-line", "paper", 3, "a link's underline"),
    ("focus", "paper", 3, "the focus ring"),
    ("on-primary", "primary", 4.5, "the primary button"),
    ("primary", "paper", 3, "the primary button's edge"),
    ("on-signal", "signal", 4.5, "today's stamp, Leave by plate, greeting date"),
    ("signal-rule", "today-wash", 3, "today's rule on its cell"),
    ("on-today", "today-bg", 4.5, "the calendar's today number"),
    ("vera", "paper", 4.5, "Vera's name and rule"),
    ("vera", "vera-soft", 4.5, "the calm pill"),
    ("on-vera", "vera-bg", 4.5, "done tick, Yes! stamp"),
    ("ok", "ok-soft", 4.5, "tag Working"),
    ("ok", "paper", 4.5, "ok text"),
    ("warn", "warn-soft", 4.5, "tag Needs a look, setup panel"),
    ("warn", "paper", 4.5, "step numbers, Could be better"),
    ("alert", "alert-soft", 4.5, "tag Not working, late badge"),
    ("alert", "paper", 4.5, "late text, OVERDUE, errors"),
    ("on-band", "band", 4.5, "panel text, inverted plate"),
    ("on-band-2", "band", 4.5, "panel quiet text"),
    ("on-band-2", "band-hi", 4.5, "the account plate"),
    ("on-alert-plate", "alert-plate", 4.5, "late count on the panel"),
    ("on-band", "band", 3, "the late plate's white rim on the panel"),
    ("signal", "band", 3, "you-are-here edge against the panel"),
    ("everyone-mark", "paper", 3, "Everyone's stripe"),
    ("everyone-ink", "everyone", 4.5, "the house avatar"),
    ("paper", "ink", 4.5, "picked choice, Tomorrow stamp"),
    ("phosphor", "glass", 4.5, "phosphor on glass"),
    ("glass-ink", "glass", 4.5, "pane text"),
    ("ask-ink", "ask-bg", 4.5, "Ask text"),
    ("ask-ink-2", "ask-bg", 4.5, "Vera's line on the hero"),
    ("ask-field-ink", "ask-field", 4.5, "words typed in Vera's box"),
    ("ask-edge", "ask-field", 3, "Vera's box edge at night (by day the white box is its own edge)"),
    ("on-send", "send", 4.5, "Send"),
]
PEOPLE = [f"p{i}" for i in range(1, 9)]
fails = 0
print("Contrast (WCAG 2.2)                                 light    dark   floor")
for f, b, floor, use in PAIRS:
    r = [contrast(val(t, f), val(t, b)) if val(t, f).startswith("#") else None for t in (light, dark)]
    bad = [x is not None and x < floor for x in r]; fails += sum(bad)
    cell = lambda x, b: "     —  " if x is None else f"{x:6.2f}{'!' if b else ' '} "
    print(f"  {('--'+f+' on --'+b):46s} {cell(r[0], bad[0])}{cell(r[1], bad[1])} {floor}   {use}")
print("\nPeople (lowest of eight; each person's own figure in palette.html)")
for f, b, floor, use in [("{p}-on", "{p}", 4.5, "avatar letter"), ("{p}-ink", "{p}-soft", 4.5, "name on own wash"),
                          ("{p}-ink", "paper", 4.5, "name on paper"), ("ink", "{p}-soft", 4.5, "words on own wash"),
                          ("ink-2", "{p}-soft", 4.5, "event time on own wash"), ("{p}-mark", "paper", 3, "route stripe, rule"),
                          ("{p}-mark", "{p}-soft", 3, "event rule on own wash"), ("{p}-lit", "band", 3, "a kid's rule on the panel")
                          ]:
    out = []
    for t in (light, dark):
        rs = [(contrast(val(t, f.format(p=p)), val(t, b.format(p=p))), p) for p in PEOPLE]
        out.append(min(rs))
    bad = [o[0] < floor for o in out]; fails += sum(bad)
    print(f"  {f.format(p='pN')+' on '+b.format(p='pN'):30s} light {out[0][0]:5.2f} ({out[0][1]}){'!' if bad[0] else ' '}  dark {out[1][0]:5.2f} ({out[1][1]}){'!' if bad[1] else ' '}  {use}")

print("\nColour-blind check: closest pair of the eight (CIEDE2000; under ~5 risks confusion, 10+ is clear)")
for label, t, suffix in [("avatars, light", light, ""), ("stripes, light", light, "-mark"), ("stripes, dark", dark, "-mark")]:
    cols = {p: val(t, p + suffix) for p in PEOPLE}
    row = []
    for kind in ["normal", "protanopia", "deuteranopia", "tritanopia"]:
        d, a, b = closest(cols, kind); row.append(f"{kind[:5]} {d:5.1f} {a}/{b}")
    print(f"  {label:16s} " + "  ".join(row))
print("\nPeople against the signals (closest, normal vision, CIEDE2000)")
for s in ["alert", "signal", "warn", "vera-bg", "phosphor", "everyone-mark"]:
    d = min((de2000(val(light, p), val(light, s)), p) for p in PEOPLE)
    n = min((de2000(val(dark, p + "-mark"), val(dark, s)), p) for p in PEOPLE)
    print(f"  --{s:14s} light {d[0]:5.1f} ({d[1]})   dark stripes {n[0]:5.1f} ({n[1]})")
print("\n" + ("All pairs pass." if not fails else f"{fails} pair(s) under their floor (marked !)."))
