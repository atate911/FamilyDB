"""The instrument drawings for Pocket Timeline, Instruments: every green glass is set in a drawn
period instrument, a pocket scope in the handheld's slate plastic. One hand draws them all:
light from above and a little left, slate faces, a hard dark rim, bone pointers, indigo on the one
selector, nickel only on the jacks. Writes static/*.svg beside the sprite.

  bezel.svg     the moulded surround of every glass (a 9-slice, drawn by border-image)
  handle.svg    the carry handle over a free-standing instrument
  deck-l.svg    the deck's left: two input jacks and the power toggle
  deck-m.svg    the deck's middle: the range selector and two trim knobs, on their scales
  deck-r.svg    the deck's right: the speaker slots and the lamp's bezel
  deck-lamp.svg the lamp's bezel alone, for a narrow deck
  feet.svg      one rubber foot (placed twice)
  case-mini.svg her screen's case: the mark's instrument, in slate, at 36px (pixels)
"""
from math import cos, sin, radians, pi
from pathlib import Path

OUT = Path(__file__).resolve().parent / "static"

SLATE = "#232631"
SLATE_HI = "#2d3140"
SLATE_EDGE = "#3b4152"
DEEP = "#0b0d13"
TICK = "#8b91a8"
BONE = "#e9ead0"
INDIGO = "#464f8c"


def svg(w, h, body, defs="", k=1.0):
    """`k` draws the picture larger on the page without changing its drawing (the deck is drawn at
    54 units and shown at 64px)."""
    W, H = round(w * k), round(h * k)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {w} {h}">'
            f'<defs>{defs}</defs>{body}</svg>\n')


DECK = 64 / 54


def pt(cx, cy, r, deg):
    """A point at `deg` clockwise from twelve o'clock."""
    a = radians(deg - 90)
    return cx + r * cos(a), cy + r * sin(a)


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def tick(cx, cy, r1, r2, deg, width=1.0, color=TICK, opacity=0.8):
    x1, y1 = pt(cx, cy, r1, deg)
    x2, y2 = pt(cx, cy, r2, deg)
    return (f'<path d="M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" opacity="{opacity}"/>')


KNOB_DEFS = (
    '<linearGradient id="skirt" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#454b5f"/><stop offset=".45" stop-color="#262a36"/>'
    '<stop offset="1" stop-color="#12141b"/></linearGradient>'
    '<radialGradient id="cap" cx=".38" cy=".3" r=".8">'
    '<stop offset="0" stop-color="#3d4256"/><stop offset=".55" stop-color="#1c1f29"/>'
    '<stop offset="1" stop-color="#101218"/></radialGradient>'
    '<radialGradient id="capi" cx=".38" cy=".3" r=".8">'
    '<stop offset="0" stop-color="#6f78bd"/><stop offset=".5" stop-color="#454e8a"/>'
    '<stop offset="1" stop-color="#2a3059"/></radialGradient>'
    '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%">'
    '<feGaussianBlur stdDeviation="1.1"/></filter>'
)


def knob(cx, cy, r, point, ridges=24, cap="url(#cap)", rc=None):
    rc = rc or r * 0.64
    c = 2 * pi * (r - 1.3)
    step = c / ridges
    out = [
        f'<circle cx="{f(cx + 0.8)}" cy="{f(cy + 2.2)}" r="{f(r + 0.6)}" fill="#030406" opacity=".7" filter="url(#soft)"/>',
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#skirt)"/>',
        # knurling: dark ridges, and the light catching the one beside each
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r - 1.3)}" fill="none" stroke="#07080c" stroke-width="2.4" '
        f'stroke-dasharray="{f(step * 0.45)} {f(step * 0.55)}" opacity=".85"/>',
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r - 1.3)}" fill="none" stroke="#5a6176" stroke-width="2.4" '
        f'stroke-dasharray="{f(step * 0.18)} {f(step * 0.82)}" stroke-dashoffset="{f(-step * 0.5)}" opacity=".35"/>',
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r - 0.4)}" fill="none" stroke="#05060a" stroke-width=".8"/>',
        # the cap, a shallow dish lit from the upper left
        f'<circle cx="{f(cx)}" cy="{f(cy + 0.6)}" r="{f(rc + 0.8)}" fill="#07080c" opacity=".7"/>',
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(rc)}" fill="{cap}"/>',
    ]
    # a rim of light on the cap's upper left
    x1, y1 = pt(cx, cy, rc - 0.7, 250)
    x2, y2 = pt(cx, cy, rc - 0.7, 355)
    out.append(f'<path d="M{f(x1)} {f(y1)}A{f(rc - 0.7)} {f(rc - 0.7)} 0 0 1 {f(x2)} {f(y2)}" fill="none" '
               f'stroke="#fff" stroke-width=".9" stroke-linecap="round" opacity=".16"/>')
    # the pointer, a bone line from the cap's centre across the skirt
    xa, ya = pt(cx, cy, rc * 0.2, point)
    xb, yb = pt(cx, cy, r - 0.9, point)
    out.append(f'<path d="M{f(xa)} {f(ya)}L{f(xb)} {f(yb)}" stroke="#06070a" stroke-width="2.6" stroke-linecap="round" opacity=".6"/>')
    out.append(f'<path d="M{f(xa)} {f(ya)}L{f(xb)} {f(yb)}" stroke="{BONE}" stroke-width="1.5" stroke-linecap="round"/>')
    return "".join(out)


def scale_arc(cx, cy, r, start, end, n, major=()):
    out = []
    for i in range(n):
        d = start + (end - start) * i / (n - 1)
        big = i in major or i in (0, n - 1)
        out.append(tick(cx, cy, r + 1.6, r + (5 if big else 3.4), d, 1.0 if big else 0.8, opacity=0.8 if big else 0.55))
    return "".join(out)


def deck_mid():
    w, h = 156, 54
    body = []
    # The range selector: three detents (a week, two, four), the pointer on the last, as the scope
    # above it is set. Its cap is the handheld's indigo, the one coloured knob on the deck.
    cx, cy, r = 30, 27, 17
    for d, pips in ((-60, 1), (0, 2), (60, 4)):
        body.append(tick(cx, cy, r + 2, r + 6, d, 1.3, opacity=0.9))
        # pips past each detent, one for each week the scope reaches: 1, 2 and 4, as its rings say
        ox, oy = pt(cx, cy, r + 8.6, d)
        tx, ty = cos(radians(d)), sin(radians(d))          # along the scale, clockwise
        for k in range(pips):
            o = (k - (pips - 1) / 2) * 2.5
            body.append(f'<circle cx="{f(ox + tx * o)}" cy="{f(oy + ty * o)}" r=".85" fill="{TICK}" opacity=".9"/>')
    body.append(knob(cx, cy, r, 60, ridges=30, cap="url(#capi)", rc=10.5))
    # two trim knobs, intensity and focus, on sweeping scales
    for (x, p) in ((84, 35), (126, -25)):
        body.append(scale_arc(x, cy, 10.5, -135, 135, 11, major=(5,)))
        body.append(knob(x, cy, 10.5, p, ridges=18, rc=6.6))
    return svg(w, h, "".join(body), KNOB_DEFS, DECK)


def jack(cx, cy):
    """A BNC input: a hex nut, the nickel barrel with its two bayonet pins, the white insulator,
    the pin."""
    hexa = " ".join(f"{f(x)},{f(y)}" for x, y in (pt(cx, cy, 10.2, 30 + 60 * i) for i in range(6)))
    return (
        f'<circle cx="{f(cx + 0.8)}" cy="{f(cy + 2)}" r="10" fill="#030406" opacity=".6" filter="url(#soft)"/>'
        f'<polygon points="{hexa}" fill="url(#nut)" stroke="#07080c" stroke-width=".8"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="6.9" fill="url(#nickel)" stroke="#0a0b10" stroke-width=".8"/>'
        f'<rect x="{f(cx - 8.9)}" y="{f(cy - 1.1)}" width="2.4" height="2.2" rx=".6" fill="#8c92a4"/>'
        f'<rect x="{f(cx + 6.5)}" y="{f(cy - 1.1)}" width="2.4" height="2.2" rx=".6" fill="#6b7184"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="4.4" fill="#07080b"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="3.1" fill="#c9c4b0"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy + 0.3)}" r="1.1" fill="#6d6a5e"/>'
        f'<path d="M{f(cx - 5.6)} {f(cy - 2.4)}A6 6 0 0 1 {f(cx + 1.5)} {f(cy - 5.8)}" fill="none" stroke="#fff" stroke-width=".8" opacity=".3" stroke-linecap="round"/>'
    )


def deck_left():
    w, h = 104, 54
    defs = KNOB_DEFS + (
        '<linearGradient id="nickel" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9aa0b1"/><stop offset=".5" stop-color="#5d6375"/>'
        '<stop offset="1" stop-color="#2c303d"/></linearGradient>'
        '<linearGradient id="nut" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#4a5063"/><stop offset="1" stop-color="#1b1e27"/></linearGradient>'
        '<linearGradient id="bat" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#5d6375"/><stop offset=".45" stop-color="#b4b9c7"/>'
        '<stop offset="1" stop-color="#454b5d"/></linearGradient>'
    )
    body = [jack(18, 27), jack(50, 27)]
    # the power toggle, thrown up (on): a nickel bat on its bushing
    x, y = 86, 32
    body.append(tick(x, y, 0, 0, 0))
    body.append(f'<path d="M{x - 6} {y - 19}h12" stroke="{TICK}" stroke-width="1.2" stroke-linecap="round" opacity=".8"/>')
    body.append(f'<path d="M{x - 6} {y + 13}h12" stroke="{TICK}" stroke-width=".8" stroke-linecap="round" opacity=".5"/>')
    body.append(f'<circle cx="{x + 0.8}" cy="{y + 2}" r="7" fill="#030406" opacity=".6" filter="url(#soft)"/>')
    hexa = " ".join(f"{f(a)},{f(b)}" for a, b in (pt(x, y, 7.2, 30 + 60 * i) for i in range(6)))
    body.append(f'<polygon points="{hexa}" fill="url(#nut)" stroke="#07080c" stroke-width=".8"/>')
    body.append(f'<circle cx="{x}" cy="{y}" r="4.6" fill="url(#nickel)" stroke="#0a0b10" stroke-width=".7"/>')
    body.append(f'<path d="M{x - 2.2} {y}L{x - 1.4} {y - 14}h2.8L{x + 2.2} {y}z" fill="url(#bat)" stroke="#0a0b10" stroke-width=".6"/>')
    body.append(f'<circle cx="{x}" cy="{y - 14.2}" r="2.3" fill="url(#bat)" stroke="#0a0b10" stroke-width=".6"/>')
    return svg(w, h, "".join(body), defs, DECK)


def deck_right():
    w, h = 116, 54
    body = []
    # the speaker: six slots pressed into the plastic at the handheld's angle
    for i in range(6):
        x = 10 + i * 9.5
        body.append(f'<g transform="rotate(-28 {x + 2} 27)">'
                    f'<rect x="{x}" y="11" width="4.4" height="32" rx="2.2" fill="#07080c"/>'
                    f'<path d="M{x + 0.4} 41.5h3.6" stroke="#434a5d" stroke-width="1" stroke-linecap="round" opacity=".7"/>'
                    f'<path d="M{x + 0.8} 13v27" stroke="#000" stroke-width="1.2" opacity=".5"/></g>')
    # the power lamp's bezel: a chrome ring round a dark lens (the lamp itself is lit by the sheet)
    x, y = 94, 27
    body.append(f'<circle cx="{x + 0.6}" cy="{y + 1.6}" r="8" fill="#030406" opacity=".6" filter="url(#soft)"/>')
    body.append(f'<circle cx="{x}" cy="{y}" r="7.6" fill="url(#ring)" stroke="#07080c" stroke-width=".8"/>')
    body.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#16070b" stroke="#07080c" stroke-width=".8"/>')
    defs = KNOB_DEFS + (
        '<linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#8c92a4"/><stop offset=".5" stop-color="#454b5d"/>'
        '<stop offset="1" stop-color="#1b1e27"/></linearGradient>'
    )
    return svg(w, h, "".join(body), defs, DECK)


def deck_lamp():
    """The lamp's ring alone, for a deck too narrow for the speaker."""
    w, h = 26, 54
    x, y = 13, 27
    body = (f'<circle cx="{x + 0.6}" cy="{y + 1.6}" r="8" fill="#030406" opacity=".6" filter="url(#soft)"/>'
            f'<circle cx="{x}" cy="{y}" r="7.6" fill="url(#ring)" stroke="#07080c" stroke-width=".8"/>'
            f'<circle cx="{x}" cy="{y}" r="5" fill="#16070b" stroke="#07080c" stroke-width=".8"/>')
    defs = KNOB_DEFS + (
        '<linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#8c92a4"/><stop offset=".5" stop-color="#454b5d"/>'
        '<stop offset="1" stop-color="#1b1e27"/></linearGradient>'
    )
    return svg(w, h, body, defs, DECK)


def handle():
    w, h = 212, 26
    defs = (
        '<linearGradient id="tube" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1a1d26"/><stop offset=".22" stop-color="#565d72"/>'
        '<stop offset=".42" stop-color="#343948"/><stop offset="1" stop-color="#11131a"/></linearGradient>'
        '<linearGradient id="grip" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#101217"/><stop offset=".3" stop-color="#2b2f3b"/>'
        '<stop offset="1" stop-color="#0a0b0f"/></linearGradient>'
        '<linearGradient id="post" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#3a3f50"/><stop offset=".35" stop-color="#2a2e3b"/>'
        f'<stop offset="1" stop-color="{SLATE}"/></linearGradient>'
        '<radialGradient id="pivot" cx=".35" cy=".3" r=".8">'
        '<stop offset="0" stop-color="#9ea4b5"/><stop offset=".6" stop-color="#555b6d"/>'
        '<stop offset="1" stop-color="#262a35"/></radialGradient>'
    )
    body = [
        # the bar, a tube, and its rubber grip
        f'<rect x="18" y="3" width="{w - 36}" height="9" rx="4.5" fill="url(#tube)" stroke="#07080c" stroke-width="1"/>',
        f'<rect x="62" y="2" width="{w - 124}" height="11" rx="3" fill="url(#grip)" stroke="#05060a" stroke-width="1"/>',
    ]
    for i in range(22):
        x = 66 + i * ((w - 132) / 21)
        body.append(f'<path d="M{f(x)} 4v7" stroke="#3b4050" stroke-width=".8" opacity=".55"/>')
    # the two posts that hold it, moulded into the case top
    for x0, flip in ((6, 1), (w - 34, -1)):
        body.append(f'<path d="M{x0} 26V11a8 8 0 0 1 8-8h12a8 8 0 0 1 8 8V26z" fill="url(#post)" stroke="{DEEP}" stroke-width="1.4"/>')
        body.append(f'<path d="M{x0 + 3} 10a6 6 0 0 1 5-5h12" fill="none" stroke="#fff" stroke-width="1" opacity=".1" stroke-linecap="round"/>')
        body.append(f'<circle cx="{x0 + 14}" cy="12" r="5.2" fill="url(#pivot)" stroke="#07080c" stroke-width=".9"/>')
        body.append(f'<circle cx="{x0 + 14}" cy="12" r="1.6" fill="#1b1e27"/>')
    return svg(w, h, "".join(body), defs)


def bezel():
    """The moulded surround of a glass, drawn once at 36px and sliced 12px from each side, so it
    stretches to any glass. Light from above: the top chamfer faces down into shadow, the bottom
    one faces up and catches the light; a lip along the outside; a black gasket at the glass."""
    s, b = 36, 12
    defs = (
        f'<clipPath id="c"><rect width="{s}" height="{s}" rx="9"/></clipPath>'
        '<linearGradient id="lip" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#555c71"/><stop offset=".5" stop-color="#2a2e3a"/>'
        '<stop offset="1" stop-color="#07080c"/></linearGradient>'
        '<linearGradient id="top" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1b1e27"/><stop offset="1" stop-color="#090a0e"/></linearGradient>'
        '<linearGradient id="bot" x1="0" y1="1" x2="0" y2="0">'
        '<stop offset="0" stop-color="#262a36"/><stop offset="1" stop-color="#363b4c"/></linearGradient>'
        '<linearGradient id="lft" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#1c1f29"/><stop offset="1" stop-color="#101218"/></linearGradient>'
        '<linearGradient id="rgt" x1="1" y1="0" x2="0" y2="0">'
        '<stop offset="0" stop-color="#1e2130"/><stop offset="1" stop-color="#1a1d28"/></linearGradient>'
    )
    i, o = b, s - b
    body = (
        f'<g clip-path="url(#c)">'
        f'<rect width="{s}" height="{s}" fill="#15171f"/>'
        f'<polygon points="0,0 {s},0 {o},{i} {i},{i}" fill="url(#top)"/>'
        f'<polygon points="0,{s} {s},{s} {o},{o} {i},{o}" fill="url(#bot)"/>'
        f'<polygon points="0,0 {i},{i} {i},{o} 0,{s}" fill="url(#lft)"/>'
        f'<polygon points="{s},0 {o},{i} {o},{o} {s},{s}" fill="url(#rgt)"/>'
        # the chamfer's creases, faint
        f'<path d="M1.5 1.5L{i} {i}M{s - 1.5} 1.5L{o} {i}" stroke="#000" stroke-width=".6" opacity=".35"/>'
        f'<path d="M1.5 {s - 1.5}L{i} {o}M{s - 1.5} {s - 1.5}L{o} {o}" stroke="#4a5063" stroke-width=".6" opacity=".35"/>'
        # light on the lower lip of the opening, shadow along its top
        f'<path d="M{i - 1} {o + 0.6}H{o + 1}" stroke="#4e5569" stroke-width="1.1"/>'
        f'<path d="M{i - 1} {i - 0.7}H{o + 1}" stroke="#000" stroke-width="1.2" opacity=".6"/>'
        f'</g>'
        f'<rect x=".6" y=".6" width="{s - 1.2}" height="{s - 1.2}" rx="8.4" fill="none" stroke="url(#lip)" stroke-width="1.2"/>'
        f'<rect x="{i - 0.5}" y="{i - 0.5}" width="{o - i + 1}" height="{o - i + 1}" fill="none" stroke="#020303" stroke-width="1"/>'
    )
    return svg(s, s, body, defs)


def foot():
    w, h = 30, 8
    return svg(w, h,
               '<path d="M0 0h30l-3 6.5a2 2 0 0 1-1.8 1.2H4.8A2 2 0 0 1 3 6.5z" fill="#07080b"/>'
               '<path d="M3.2 1.2h23.6" stroke="#2b2f3b" stroke-width="1" stroke-linecap="round"/>')


MINI = """
.....HHHHHHHH.....
....H........H....
.KKKKKKKKKKKKKKKK.
KHHHHHHHHHHHHHHHHK
KSDDDDDDDDDDDDDDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSDGGGGGGGGGGGGDSK
KSLLLLLLLLLLLLLLSK
KSSSSSSSSSSSSSSSSK
KSooSooSSSSSSbbSSK
KSSSSSSSSSSSSSSSK.
.KKKKKKKKKKKKKKK..
..KKK.......KKK..."""
MINI_INK = {"K": DEEP, "H": "#4a5063", "S": SLATE_HI, "D": "#15171f", "L": "#454b5f",
            "G": "#050706", "o": "#101218", "b": "#e57694"}


def case_mini():
    """Her screen's case: the mark's own instrument (the sprite's 18 cells, 2px each at 36px) in
    slate, with the glass left dark for her glyphs, which the page draws over it: the handle, the
    case with its one round corner, the moulded rim, two knobs and the power lamp in the chin."""
    rows = MINI.strip("\n").split("\n")
    d = {}
    for y, row in enumerate(rows):
        x = 0
        while x < 18:
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            s0 = x
            while x < 18 and row[x] == ch:
                x += 1
            d.setdefault(ch, []).append(f"M{s0} {y}h{x - s0}v1h-{x - s0}z")
    body = "".join(f'<path fill="{MINI_INK[ch]}" d="{"".join(p)}"/>' for ch, p in d.items())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 18 18" '
            f'shape-rendering="crispEdges">{body}</svg>\n')


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, fn in (("bezel", bezel), ("handle", handle), ("deck-l", deck_left), ("deck-m", deck_mid),
                     ("deck-r", deck_right), ("deck-lamp", deck_lamp), ("foot", foot), ("case-mini", case_mini)):
        (OUT / f"{name}.svg").write_text(fn())
    print("drawn")
