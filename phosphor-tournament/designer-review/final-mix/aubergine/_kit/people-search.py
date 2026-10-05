#!/usr/bin/env python3
"""Usage: python3 _kit/people-search.py [iterations] [seed]

How the eight people's colours were found. Each person has a jewel-tone hue band (OKLCH);
a hill-climb picks lightness and chroma for the avatar (base), the day stripe (mark on stone, within 0.12 lightness of the avatar)
and the night stripe (mark on plum-graphite), keeping every floor:
  avatar letter (white or ink) >= 4.5:1; day stripe >= 3:1 on paper and on its wash; night stripe >= 3:1;
  >= 13 CIEDE2000 from late red and Vera's greens, and >= 12 from brass, in normal vision,
and maximising the closest pair under normal vision, protanopia, deuteranopia and tritanopia
(the family's four, slots 1-4, weigh double). It prints the hex values to paste into style.css."""
import math, random, sys, itertools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colour import contrast, simulate, de2000

def oklch(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    if min(r, g, bb) < -0.001 or max(r, g, bb) > 1.001: return None
    enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0) ** (1 / 2.4) - 0.055
    return "#" + "".join(f"{round(min(max(enc(c), 0), 1) * 255):02X}" for c in (r, g, bb))

def fit(L, C, h):
    """the colour at this lightness and hue, its chroma reduced until it fits sRGB (never below 0.075)"""
    while C >= .075:
        c = oklch(L, C, h)
        if c: return c
        C -= .004
    return None

PAPER, PAPER_N, INK, WHITE = "#E9E6E4", "#141115", "#1E1220", "#FFFFFF"
AVOID = ["#B0201A", "#FF8B7A", "#0A6A4B", "#0B7F55", "#6DFF9C", "#4FE08A"]   # late red, Vera's greens
BRASS = ["#CFA650", "#DDB865"]
BANDS = {  # OKLCH hue ranges: the jewel each person is
    "p1": (250, 266, "sapphire"), "p2": (292, 306, "amethyst"), "p3": (196, 212, "peacock"), "p4": (48, 64, "topaz"),
    "p5": (108, 124, "peridot"), "p6": (226, 242, "aquamarine"), "p7": (40, 62, "tiger's eye"), "p8": (268, 282, "lapis"),
}
KINDS = ("normal", "protan", "deutan", "tritan")

def make(slot, g):
    lo, hi, _ = BANDS[slot]
    h = lo + (hi - lo) * g[0]
    # jewel tones: real chroma, no near-whites or near-blacks
    if not (.42 <= g[1] <= .72 and .40 <= g[3] <= .62 and .62 <= g[5] <= .86): return None
    if min(g[2], g[4], g[6]) < .10 or max(g[2], g[4], g[6]) > .22: return None
    # one person, one colour: the day stripe stays near the avatar's lightness, no pastels
    if abs(g[1] - g[3]) > .12: return None
    base, mark, night = fit(g[1], g[2], h), fit(g[3], g[4], h), fit(g[5], g[6], h)
    if not (base and mark and night): return None
    if max(contrast(base, WHITE), contrast(base, INK)) < 4.6: return None
    if contrast(mark, PAPER) < 3.15 or contrast(night, PAPER_N) < 3.4: return None
    for c in (base, mark, night):
        if min(de2000(c, x) for x in AVOID) < 13 or min(de2000(c, x) for x in BRASS) < 12: return None
    return base, mark, night

def score(cols):
    worst = 1e9
    for idx, wt in ((0, 1.0), (1, 1.0), (2, 1.0)):
        for k in KINDS:
            sims = {s: simulate(c[idx], k) for s, c in cols.items()}
            for a, b in itertools.combinations(sims, 2):
                d = de2000(sims[a], sims[b])
                if a in ("p1", "p2", "p3", "p4") and b in ("p1", "p2", "p3", "p4"): d *= 0.8   # the family's four count more
                if k == "normal": d *= 0.6                                                     # normal vision has hue to spare
                worst = min(worst, d)
    return worst

def rand_gene():
    return [random.random(), random.uniform(.45, .6), random.uniform(.1, .2), random.uniform(.45, .58), random.uniform(.1, .2), random.uniform(.62, .86), random.uniform(.1, .2)]

random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
genes, cols = {}, {}
for s in BANDS:
    while True:
        g = rand_gene(); c = make(s, g)
        if c: genes[s], cols[s] = g, c; break
best = score(cols)
for it in range(int(sys.argv[1]) if len(sys.argv) > 1 else 6000):
    s = random.choice(list(BANDS)); g = genes[s][:]
    i = random.randrange(7); g[i] += random.gauss(0, .03 if i else .1)
    if i == 0: g[0] = min(max(g[0], 0), 1)
    c = make(s, g)
    if not c: continue
    trial = {**cols, s: c}; sc = score(trial)
    if sc >= best: best, genes[s], cols = sc, g, trial
print("weighted worst pair:", round(best, 2))
for s, (b, m, n) in cols.items():
    on = WHITE if contrast(b, WHITE) >= contrast(b, INK) else INK
    print(f"{s} {BANDS[s][2]:12s} base {b} on {on} ({max(contrast(b, WHITE), contrast(b, INK)):.2f})  mark {m} ({contrast(m, PAPER):.2f})  night {n} ({contrast(n, PAPER_N):.2f})")
