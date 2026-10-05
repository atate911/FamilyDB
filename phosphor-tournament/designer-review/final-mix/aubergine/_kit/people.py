#!/usr/bin/env python3
"""Usage: python3 _kit/people.py [--write]

The eight people's colours, chosen by hand (guided by _kit/people-search.py) and finished by rule:
  base   the avatar, under white or aubergine ink, whichever passes AA best
  mark   the day stripe and rule on stone (>= 3:1)
  night  the night stripe and rule on plum-graphite (>= 3:1)
  soft   a wash: base mixed into the pale stone of --card (day 14 %, night 20 %)
  ink    the name: the same hue, darkened (day) or lightened (night) until it reads >= 5:1 on its wash
Prints the CSS; --write puts it into style.css (day lines in :root, night lines in the dark block)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colour import contrast, rgb

PAPER, PAPER_N, CARD, INK, WHITE = "#E9E6E4", "#141115", "#F6F4F3", "#1E1220", "#FFFFFF"
PEOPLE = [  # slot, jewel, base, day mark, night mark (from people-search.py seed 21, then trimmed by eye)
    ("p1", "sapphire",    "#2F5CDA", "#3F6EEB", "#4E7EF8"),
    ("p2", "amethyst",    "#61318B", "#62239A", "#D9BEF9"),
    ("p3", "peacock",     "#0BAEAF", "#0E8A8B", "#18BDBF"),
    ("p4", "topaz",       "#C06E08", "#B06A00", "#F38E12"),
    ("p5", "peridot",     "#8FAB54", "#6F8640", "#A6C367"),
    ("p6", "cerulean",    "#0B6B88", "#05546B", "#3199C0"),
    ("p7", "tiger's eye", "#86501C", "#6A3A12", "#A8683C"),
    ("p8", "tanzanite",   "#7E7FCB", "#5A50C6", "#9FA1FD"),
]

def hexs(c): return "#" + "".join(f"{round(min(max(x, 0), 1) * 255):02X}" for x in c)
def mix(a, b, t): return hexs([x * t + y * (1 - t) for x, y in zip(rgb(a), rgb(b))])
def toward(c, target, floor, against):
    t = 0.0
    while contrast(mix(target, c, t), against) < floor and t < 1: t += 0.01
    return mix(target, c, t)

def lines():
    day, night = [], []
    for slot, name, base, mark, nmark in PEOPLE:
        on = WHITE if contrast(base, WHITE) >= contrast(base, INK) else INK
        soft, nsoft = mix(base, CARD, .14), mix(base, PAPER_N, .2)
        ink = toward(mark, "#000000", 5.0, soft)
        nink = toward(nmark, "#FFFFFF", 6.0, nsoft)
        day.append(f"  --{slot}: {base}; --{slot}-on: {on}; --{slot}-soft: {soft}; --{slot}-ink: {ink}; --{slot}-mark: {mark};   /* {name} */")
        night.append(f"    --{slot}-soft: {nsoft}; --{slot}-ink: {nink}; --{slot}-mark: {nmark};")
    return day, night

day, night = lines()
if "--write" in sys.argv:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style.css")
    css = open(path).read()
    css = re.sub(r"(  --p1: .*?\n)(?:  --p\d: .*?\n){7}", lambda m: "\n".join(day) + "\n", css, count=1, flags=re.S)
    css = re.sub(r"(    --p1-soft: .*?\n)(?:    --p\d-soft: .*?\n){7}", lambda m: "\n".join(night) + "\n", css, count=1, flags=re.S)
    open(path, "w").write(css)
print("\n".join(day)); print("\n".join(night))
