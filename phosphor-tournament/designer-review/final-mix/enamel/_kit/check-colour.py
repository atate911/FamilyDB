#!/usr/bin/env python3
# python3 _kit/check-colour.py [style.css]: contrast floors and colour-blind separation, measured from the tokens in style.css §2.
import math

def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def rgb2hex(c):
    return '#' + ''.join('%02X' % max(0, min(255, round(x * 255))) for x in c)

def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def delin(c): return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

def lum(h):
    r, g, b = (lin(x) for x in hex2rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def cr(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def blend(fg, bg, a):
    f, b = hex2rgb(fg), hex2rgb(bg)
    return rgb2hex(tuple(a * x + (1 - a) * y for x, y in zip(f, b)))

# OKLab / OKLCH
def lrgb2oklab(r, g, b):
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l, m, s = (math.copysign(abs(x) ** (1/3), x) for x in (l, m, s))
    return (0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
            1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
            0.0259040371*l + 0.7827717662*m - 0.8086757660*s)

def oklab2lrgb(L, a, b):
    l = (L + 0.3963377774*a + 0.2158037573*b) ** 3
    m = (L - 0.1055613458*a - 0.0638541728*b) ** 3
    s = (L - 0.0894841775*a - 1.2914855480*b) ** 3
    return (4.0767416621*l - 3.3077115913*m + 0.2309699292*s,
            -1.2684380046*l + 2.6097574011*m - 0.3413193965*s,
            -0.0041960863*l - 0.7034186147*m + 1.7076147010*s)

def in_gamut(c): return all(-1e-4 <= x <= 1 + 1e-4 for x in c)

def oklch(L, C, H):
    """OKLCH -> hex, reducing chroma until in sRGB gamut."""
    while True:
        a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        c = oklab2lrgb(L, a, b)
        if in_gamut(c) or C <= 0: break
        C -= 0.002
    return rgb2hex(tuple(delin(max(0, min(1, x))) for x in c))

def hex2oklch(h):
    L, a, b = lrgb2oklab(*(lin(x) for x in hex2rgb(h)))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360

# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB
MACHADO = {
    'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}

def sim(h, kind):
    if kind == 'normal': return h
    c = [lin(x) for x in hex2rgb(h)]
    M = MACHADO[kind]
    o = [sum(M[i][j] * c[j] for j in range(3)) for i in range(3)]
    return rgb2hex(tuple(delin(max(0, min(1, x))) for x in o))

# CIEDE2000
def hex2lab(h):
    r, g, b = (lin(x) for x in hex2rgb(h))
    X = (0.4124*r + 0.3576*g + 0.1805*b) / 0.95047
    Y = (0.2126*r + 0.7152*g + 0.0722*b)
    Z = (0.0193*r + 0.1192*g + 0.9505*b) / 1.08883
    f = lambda t: t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116
    return 116*f(Y) - 16, 500*(f(X) - f(Y)), 200*(f(Y) - f(Z))

def de2000(h1, h2):
    L1, a1, b1 = hex2lab(h1); L2, a2, b2 = hex2lab(h2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb**7 / (Cb**7 + 25**7)))
    a1p, a2p = (1+G)*a1, (1+G)*a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0: hb = h1p + h2p
    elif abs(h1p - h2p) <= 180: hb = (h1p + h2p) / 2
    elif h1p + h2p < 360: hb = (h1p + h2p + 360) / 2
    else: hb = (h1p + h2p - 360) / 2
    T = (1 - 0.17*math.cos(math.radians(hb-30)) + 0.24*math.cos(math.radians(2*hb))
         + 0.32*math.cos(math.radians(3*hb+6)) - 0.20*math.cos(math.radians(4*hb-63)))
    dth = 30 * math.exp(-((hb - 275) / 25) ** 2)
    RC = 2 * math.sqrt(Cbp**7 / (Cbp**7 + 25**7))
    SL = 1 + 0.015 * (Lb - 50)**2 / math.sqrt(20 + (Lb - 50)**2)
    SC = 1 + 0.045 * Cbp
    SH = 1 + 0.015 * Cbp * T
    RT = -math.sin(math.radians(2 * dth)) * RC
    return math.sqrt((dL/SL)**2 + (dC/SC)**2 + (dH/SH)**2 + RT*(dC/SC)*(dH/SH))

KINDS = ['normal', 'protan', 'deutan', 'tritan']

def closest(cols, kinds=KINDS):
    """cols: {name: hex}. Returns {kind: (dE, a, b)} for the closest pair under each vision."""
    out = {}
    names = list(cols)
    for k in kinds:
        s = {n: sim(cols[n], k) for n in names}
        best = None
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                d = de2000(s[names[i]], s[names[j]])
                if best is None or d < best[0]: best = (d, names[i], names[j])
        out[k] = best
    return out

import re, sys
css = open(sys.argv[1] if len(sys.argv) > 1 else 'style.css').read()
def block(src):
    return {k: v.upper() for k, v in re.findall(r'--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b', src)}
dark_at = css.index('@media (prefers-color-scheme: dark)')
L = block(css[css.index(':root {'):dark_at])
D = dict(L); D.update(block(css[dark_at:css.index('/* ---------- 3. Base')]))
fails, n = [], 0
def need(th, t, fg, bg, floor):
    global n; n += 1
    r = cr(t.get(fg, fg), t.get(bg, bg))
    if r < floor: fails.append(f'{th}: --{fg} on --{bg} {r:.2f} < {floor}')
for th, t in (('day', L), ('night', D)):
    for bg in ('paper', 'paper-2', 'card'):
        for fg in ('ink', 'ink-2', 'ink-3', 'alert', 'warn', 'ok', 'vera', 'link'): need(th, t, fg, bg, 4.5)
        need(th, t, 'edge', bg, 3); need(th, t, 'focus', bg, 3)
    for fg, bg in (('warn', 'warn-soft'), ('alert', 'alert-soft'), ('ok', 'ok-soft'), ('vera', 'vera-soft'), ('ink', 'warn-soft'), ('ink-3', 'warn-soft'),
                   ('on-primary', 'primary'), ('on-today', 'today-bg'), ('on-vera', 'vera-bg'), ('on-band', 'band'), ('on-band-2', 'band'),
                   ('on-band-2', 'band-hi'), ('band', 'on-band'), ('on-alert-plate', 'alert-plate'), ('ink', 'today-wash'), ('everyone-ink', 'everyone-soft'), ('everyone-ink', 'everyone')):
        need(th, t, fg, bg, 4.5)
    need(th, t, 'today-bg', 'paper', 3); need(th, t, 'everyone-mark', 'paper', 3)
    for i in range(1, 9):
        p = f'p{i}'
        need(th, t, 'on-p', p, 4.5)
        for bg in (p + '-soft', 'paper', 'paper-2', 'card'): need(th, t, p + '-ink', bg, 4.5)
        need(th, t, 'ink', p + '-soft', 4.5); need(th, t, p + '-mark', 'paper', 3); need(th, t, p + '-mark', p + '-soft', 3)
print(f'{n} pairs checked, {len(fails)} below the floor'); [print('  FAIL', f) for f in fails]
for th, t in (('day', L), ('night', D)):
    for v, what in (('', 'avatars'), ('-mark', 'route stripes')):
        cols = {f'p{i}': t[f'p{i}{v}'] for i in range(1, 9)}; cols['everyone'] = t['everyone' + v]
        print(f'{th} {what}: closest pair (CIEDE2000) ' + ', '.join(f'{k} {d:.1f} ({a}/{b})' for k, (d, a, b) in closest(cols).items()))
