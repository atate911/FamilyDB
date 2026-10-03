"""Geometry of the spend meter's scale (a square-root scale, opened at the low end as a VU
meter's is), printed as SVG path data to paste into _ui.html. The scale is in shares of the day's
limit, so it never changes with the limit; only the labels do, and those the template writes."""
from math import sin, cos, radians, sqrt

CX, CY, R = 130, 156, 120
A0, A1 = -50, 50


def ang(f):
    return A0 + (A1 - A0) * sqrt(f)


def pt(a, r):
    t = radians(a)
    return CX + r * sin(t), CY - r * cos(t)


def f2(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


major = [0, 0.1, 0.25, 0.5, 1]
minor = [0.025, 0.05, 0.075, 0.15, 0.2, 0.3, 0.35, 0.4, 0.45, 0.6, 0.7, 0.8, 0.9]


def ticks(fs, r0, r1):
    out = []
    for f in fs:
        x0, y0 = pt(ang(f), r0)
        x1, y1 = pt(ang(f), r1)
        out.append(f"M{f2(x0)} {f2(y0)}L{f2(x1)} {f2(y1)}")
    return "".join(out)


def arc(a0, a1, r):
    x0, y0 = pt(a0, r)
    x1, y1 = pt(a1, r)
    large = 1 if (a1 - a0) > 180 else 0
    return f"M{f2(x0)} {f2(y0)}A{r} {r} 0 {large} 1 {f2(x1)} {f2(y1)}"


print("scale arc :", arc(A0, A1, R))
print("major     :", ticks(major, R, R + 13))
print("minor     :", ticks(minor, R, R + 7))
print("amber band:", arc(ang(0.75), A1, R - 5))
print("labels    :", [(f, f2(pt(ang(f), R + 26)[0]), f2(pt(ang(f), R + 26)[1] + 5)) for f in major])
print("angles    :", [(f, round(ang(f), 1)) for f in major])
# the dome over the pivot
r = 46
dy = CY - 128
dx = sqrt(r * r - dy * dy)
print("dome      :", f"M{f2(CX - dx)} 128A{r} {r} 0 0 1 {f2(CX + dx)} 128Z")
# the compact edgewise meter: a straight scale 8..232 at y=14
print("edge major:", "".join(f"M{f2(8 + 224 * sqrt(f))} 8V20" for f in major))
print("edge minor:", "".join(f"M{f2(8 + 224 * sqrt(f))} 11V20" for f in minor))
print("edge amber:", f"M{f2(8 + 224 * sqrt(0.75))} 22H232")
