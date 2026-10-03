import itertools, sys
sys.path.insert(0, ".")
from colorlib import contrast, de, hex_to_rgb, rgb_to_hex, oklch_to_rgb, rgb_to_oklch
def ok(L, C, h): return rgb_to_hex(oklch_to_rgb(L, C, h))
P = {
 "bg": ok(0.165, 0.008, 160),
 "surface": ok(0.2, 0.009, 150),
 "surface-2": ok(0.225, 0.010, 145),
 "surface-3": ok(0.255, 0.011, 140),
 "field": ok(0.18, 0.008, 155),
 "line": ok(0.29, 0.010, 130),
 "line-2": ok(0.34, 0.012, 120),
 "edge": ok(0.56, 0.02, 110),
 "ink": ok(0.925, 0.012, 100),
 "ink-2": ok(0.80, 0.014, 100),
 "dim": ok(0.70, 0.016, 100),
 "faint": ok(0.64, 0.016, 100),
 "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c",
 "accent": ok(0.87, 0.10, 95),
 "outing": ok(0.80, 0.11, 138),
 "ideas": ok(0.76, 0.09, 300),
 "plans": ok(0.78, 0.08, 245),
 "todo": ok(0.80, 0.08, 195),
 "people": ok(0.78, 0.11, 62),
 "shows": ok(0.80, 0.09, 355),
 "seasons": ok(0.72, 0.12, 30),
 "danger": ok(0.68, 0.16, 25),
 "on-bright": ok(0.18, 0.02, 150),
 "lit": ok(0.84, 0.11, 152),
 "label": ok(0.76, 0.05, 95),
 "heading": ok(0.93, 0.04, 95),
}
for k, v in P.items(): print(f'"{k}": "{v}",')
KINDS = {"restaurant": "people","activity": "todo","outing": "outing","trip": "plans","show": "shows","seasonal": "seasons","event": "ideas"}
SECTIONS = {"home": "accent", "ideas": "ideas", "plans": "plans", "todo": "todo", "wishes": "shows", "family": "people"}
for name, group in [("kinds", KINDS), ("sections", SECTIONS)]:
    for vision in ["typical", "deutan", "protan"]:
        w = min(((de(P[a], P[b], vision), x, y) for (x, a), (y, b) in itertools.combinations(group.items(), 2)))
        print(name, vision, round(w[0], 1), w[1], w[2])
for k in ["ink", "ink-2", "dim", "label", "heading", "accent", "brand"]:
    print(k, [round(contrast(P[k], P[g]), 2) for g in ["bg", "surface", "surface-3"]])
print("faint", round(contrast(P["faint"], P["field"]), 2), round(contrast(P["faint"], P["surface"]), 2))
print("edge", round(contrast(P["edge"], P["surface"]), 2), round(contrast(P["edge"], P["field"]), 2))
for k in ["brand","ideas","plans","todo","people","shows","seasons","outing","screen","lit","accent"]:
    print("on-bright on", k, round(contrast(P["on-bright"], P[k]), 2), " text on s3", round(contrast(P[k], P["surface-3"]), 2))
print("danger on s3", round(contrast(P["danger"], P["surface-3"]), 2))
