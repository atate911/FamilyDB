"""The greeting's one texture: the airglow off the lit run as a phosphor halftone.

A dot screen at 45 degrees, pitch 7px, each dot's radius the light at that point: brightest in a
band just over the sill where the lit run is (from the now lamp to the first stop), falling off
upwards and away along the board. Drawn at the page's own pixel size (1px = 1 CSS px) so the dots
stay round at any width; placed at the board's bottom left by the sheet. Written to
static/halftone-sill.svg (desktop, the run along the foot) and static/halftone-gutter.svg (phone,
the run down the left gutter)."""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "static"


def screen(w, h, light, pitch=7.0, rmax=2.1, rmin=0.4):
    dots = []
    row = 0
    y = h - pitch / 2
    while y > 0:
        off = (pitch / 2) if row % 2 else 0.0
        x = off + pitch / 2
        while x < w:
            v = light(x, h - y)  # distance up from the foot
            r = rmax * v
            if r >= rmin:
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
            x += pitch
        y -= pitch / 2
        row += 1
    return dots


def write(name, w, h, light):
    dots = screen(w, h, light)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<g fill="#6dff9c" fill-opacity=".34">{"".join(dots)}</g></svg>\n')
    (OUT / name).write_text(svg)
    print(name, len(dots), "dots", len(svg), "bytes")


# Desktop: the lit run lies along the foot from about x=40 (now) to x=390 (the first stop).
def sill(x, up):
    along = 1.0 if 40 <= x <= 380 else math.exp(-((x - 380) / 46.0) ** 2) if x > 380 else math.exp(-((40 - x) / 24.0) ** 2)
    rise = math.exp(-(up / 56.0) ** 1.5)
    return along * rise


# Phone: the run goes down the left gutter; the light spreads right, and up from the foot.
def gutter(x, up):
    across = math.exp(-(max(0.0, x - 12) / 70.0) ** 1.5)
    rise = 0.35 + 0.65 * math.exp(-(up / 260.0) ** 2)
    return across * rise


write("halftone-sill.svg", 600, 150, sill)
write("halftone-gutter.svg", 220, 520, gutter)
