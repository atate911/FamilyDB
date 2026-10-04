"""Colour maths for the palette check: WCAG contrast, CVD simulation (Machado et al. 2009, severity 1.0), CIEDE2000."""
import math
def hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
def lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
def delin(c):
    c = min(max(c, 0), 1)
    return 12.92*c if c <= 0.0031308 else 1.055*c**(1/2.4)-0.055
def lum(h):
    r, g, b = (lin(c) for c in hex2rgb(h)); return 0.2126*r+0.7152*g+0.0722*b
def contrast(a, b):
    la, lb = lum(a), lum(b); hi, lo = max(la, lb), min(la, lb); return (hi+0.05)/(lo+0.05)
MACHADO = {
 'protanopia':   [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
 'deuteranopia': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
 'tritanopia':   [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}
def simulate(h, kind):
    if kind == 'normal': return h
    r, g, b = (lin(c) for c in hex2rgb(h)); m = MACHADO[kind]
    out = [m[i][0]*r+m[i][1]*g+m[i][2]*b for i in range(3)]
    return '#' + ''.join('%02X' % round(delin(c)*255) for c in out)
def lab(h):
    r, g, b = (lin(c) for c in hex2rgb(h))
    x = (0.4124*r+0.3576*g+0.1805*b)/0.95047; y = 0.2126*r+0.7152*g+0.0722*b; z = (0.0193*r+0.1192*g+0.9505*b)/1.08883
    f = lambda t: t**(1/3) if t > 216/24389 else (24389/27*t+16)/116
    fx, fy, fz = f(x), f(y), f(z); return (116*fy-16, 500*(fx-fy), 200*(fy-fz))
def de2000(h1, h2):
    L1, a1, b1 = lab(h1); L2, a2, b2 = lab(h2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1+C2)/2
    G = 0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7))); a1p, a2p = (1+G)*a1, (1+G)*a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2-L1, C2p-C1p
    dh = 0 if C1p*C2p == 0 else (h2p-h1p if abs(h2p-h1p) <= 180 else (h2p-h1p-360 if h2p > h1p else h2p-h1p+360))
    dH = 2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Lbp, Cbp = (L1+L2)/2, (C1p+C2p)/2
    if C1p*C2p == 0: hbp = h1p+h2p
    elif abs(h1p-h2p) <= 180: hbp = (h1p+h2p)/2
    else: hbp = (h1p+h2p+360)/2 if h1p+h2p < 360 else (h1p+h2p-360)/2
    T = 1-0.17*math.cos(math.radians(hbp-30))+0.24*math.cos(math.radians(2*hbp))+0.32*math.cos(math.radians(3*hbp+6))-0.20*math.cos(math.radians(4*hbp-63))
    dth = 30*math.exp(-((hbp-275)/25)**2); Rc = 2*math.sqrt(Cbp**7/(Cbp**7+25**7))
    Sl = 1+0.015*(Lbp-50)**2/math.sqrt(20+(Lbp-50)**2); Sc = 1+0.045*Cbp; Sh = 1+0.015*Cbp*T; Rt = -math.sin(math.radians(2*dth))*Rc
    return math.sqrt((dL/Sl)**2+(dC/Sc)**2+(dH/Sh)**2+Rt*(dC/Sc)*(dH/Sh))
def closest(cols, kind):
    best = None; names = list(cols)
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            d = de2000(simulate(cols[names[i]], kind), simulate(cols[names[j]], kind))
            if best is None or d < best[0]: best = (d, names[i], names[j])
    return best
def lch2hex(L, C, h):
    """CIE LCh (D65) to hex; None when out of sRGB gamut."""
    a, b = C*math.cos(math.radians(h)), C*math.sin(math.radians(h))
    fy = (L+16)/116; fx = fy+a/500; fz = fy-b/200
    finv = lambda t: t**3 if t**3 > 216/24389 else (116*t-16)/(24389/27)
    x, y, z = finv(fx)*0.95047, finv(fy), finv(fz)*1.08883
    rgb = (3.2406*x-1.5372*y-0.4986*z, -0.9689*x+1.8758*y+0.0415*z, 0.0557*x-0.2040*y+1.0570*z)
    if min(rgb) < -0.001 or max(rgb) > 1.001: return None
    return '#'+''.join('%02X' % round(delin(c)*255) for c in rgb)
def lch(h):
    L, a, b = lab(h); return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)
