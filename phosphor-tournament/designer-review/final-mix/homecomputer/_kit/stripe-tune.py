# python3 _kit/stripe-tune.py light|dark [pull]
# Searches route-stripe shades (the -mark tokens) near each person's colour that keep 3:1 on the page
# and on fields, and pushes the eight as far apart as possible under every colour-blind simulation,
# and away from late red, Vera's green and the orange key. Prints candidate tokens to paste.
import sys, os, itertools, random
sys.path.insert(0, os.path.dirname(__file__))
from colour import *
import importlib.util
spec = importlib.util.spec_from_file_location('pc', os.path.join(os.path.dirname(__file__), 'palette-check.py'))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
theme = sys.argv[1] if len(sys.argv) > 1 else 'light'
W = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02  # pull towards the avatar colour
T = pc.tokens(open('style.css').read())[theme]
bgs = [T['paper'], T['card']] if theme == 'light' else [T['paper'], T['card'], T['paper-2']]
avoid = [T['alert'], T['vera-bg'], T['signal']] + ([T['phosphor']] if theme == 'dark' else [])
P = [f'p{i}' for i in range(1, 9)]
fixed = {p: T[p + '-mark'] for p in P}
sims = lambda h: [simulate(h, k) for k in KINDS]
def score(marks):
    S = {p: sims(h) for p, h in marks.items()}
    A = [sims(a) for a in avoid]
    d = min(de2000(S[a][k], S[b][k]) for a, b in itertools.combinations(P, 2) for k in range(4))
    e = min(de2000(S[p][k], a[k]) for p in P for a in A for k in range(4))
    return min(d, e * 1.4)
def cands(p):
    L0, C0, H0 = to_oklch(T[p])
    out = []
    for dh in range(-24, 25, 4):
        for cf in (0.6, 0.8, 1.0, 1.2):
            for L in [x / 100 for x in range(30, 92, 2)]:
                h = from_oklch(L, C0 * cf, H0 + dh)
                ok = all(contrast(h, b) >= 3.05 for b in bgs)
                if ok: out.append(h)
    # keep, per hue/chroma, the shade closest to the base in lightness (stripe stays recognisably the pen)
    return out
C = {p: cands(p) for p in P}
random.seed(1)
cur = dict(fixed); best = score(cur)
for it in range(6):
    for p in P:
        for h in random.sample(C[p], min(len(C[p]), 160)):
            trial = dict(cur); trial[p] = h
            s = score(trial)
            # small preference for staying near the avatar colour
            s -= W * de2000(h, T[p])
            if s > best: best, cur = s, trial
print(theme, 'min distance', round(score(cur), 1))
for p in P: print(f'  --{p}-mark: {cur[p]};   was {fixed[p]}  base {T[p]}  dE to base {de2000(cur[p], T[p]):.1f}')
