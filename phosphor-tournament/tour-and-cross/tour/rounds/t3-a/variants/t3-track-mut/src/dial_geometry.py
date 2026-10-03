"""The spend meter's fixed drawing: the scale arc, its ticks, the caution hatching and the
buffer, as SVG path data for templates/status.html. Only the needle, the lit run and the bug
move with the data, by rotate() and a dash on a pathLength of 100, so no trig is needed in
Jinja."""
import math
CX, CY, R, SPAN = 160.0, 158.0, 122.0, 50.0

def pt(r, deg):
    a = math.radians(deg)
    return CX + r * math.sin(a), CY - r * math.cos(a)

def f(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s

def arc(r, a0, a1):
    x0, y0 = pt(r, a0); x1, y1 = pt(r, a1)
    large = 1 if abs(a1 - a0) > 180 else 0
    return f"M{f(x0)} {f(y0)}A{f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"

def ang(p):  # share 0..100 -> degrees
    return -SPAN + 2 * SPAN * p / 100

minor, major = [], []
for i in range(0, 21):
    p = i * 5
    a = ang(p)
    if p % 25 == 0:
        x0, y0 = pt(R + 2, a); x1, y1 = pt(R + 13, a)
        major.append(f"M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}")
    else:
        x0, y0 = pt(R + 2, a); x1, y1 = pt(R + 8, a)
        minor.append(f"M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}")
hatch = []
a = ang(75)
while a < ang(100) - 0.5:
    x0, y0 = pt(R - 11, a); x1, y1 = pt(R - 1.5, a + 2.2)
    hatch.append(f"M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}")
    a += 2.6
print("scale", arc(R, -SPAN, SPAN))
print("minor", "".join(minor))
print("major", "".join(major))
print("hatch", "".join(hatch))
bx0, by0 = pt(R - 12, SPAN); bx1, by1 = pt(R + 14, SPAN)
print("buffer", f"M{f(bx0)} {f(by0)}L{f(bx1)} {f(by1)}")
for p in (0, 50, 100):
    x, y = pt(R + 27, ang(p))
    print("label", p, f(x), f(y + 5))
print("terminus", *[f(v) for v in pt(R, -SPAN)])
print("needle tip y", f(CY - (R + 6)), "bug", f(CY - R + 4), f(CY - R + 13))
