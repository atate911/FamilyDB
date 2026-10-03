"""Build palettes/r13-idea-1.json and its sheet (run from the round folder: python3 variants/r13-idea-1/build.py).

The sheet is today's stylesheet as the harness themes it for these tokens (the phosphor re-tinted,
the glow numbers applied, so E1-E22 are all there), with every font size moved onto this design's
six steps (12 / 15 / 17 / 22 / 32 / 40), followed by the design's own rules (palette.css). A clean
sheet only because the size rewrite has to happen in place (Tuning Dock's method).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent
ID = "x14b-desk-cross"
NAME = "Desk Terminal, Wired"
TAGLINE = ("One cased terminal wired into the family's desk: Home's glass says 'Give Vera something to plan.', a lit lead runs to Coming up's NOW lamp, every dated list leads with one day numeral, and each band has exactly one light.")

tokens = json.loads((here / "tokens.json").read_text())
tmp_pal = here / ".base-palette.json"
tmp_css = here / ".base-themed.css"
tmp_pal.write_text(json.dumps({"id": ID + "-base", "name": NAME, "tagline": TAGLINE, **tokens}))
subprocess.run([sys.executable, "theme.py", str(tmp_pal), str(tmp_css)], check=True)
base = tmp_css.read_text()
base = re.sub(r"@font-face \{.*?\}\n?", "", base, flags=re.S)

# six steps: 12 note, 15 small, 17 text, 22 head, 32 title, 40 page
BOUNDS = [(0.8, "--fs-note"), (0.99, "--fs-small"), (1.2, "--fs-text"), (1.7, "--fs-head"), (2.3, "--fs-title")]
KEEP_PX = {"4px", "6px", "6.5px", "7px", "8.5px", "10px"}
report = []


def step(rem: float) -> str:
    for bound, name in BOUNDS:
        if rem < bound:
            return f"var({name})"
    return "var(--fs-page)"


def size_token(tok: str, where: str) -> str:
    tok = tok.strip()
    if tok.startswith("var(--fs-") or tok in ("inherit", "1em", "100%") or tok in KEEP_PX:
        return tok
    m = re.fullmatch(r"clamp\(\s*([\d.]+)rem\s*,[^,]+,\s*([\d.]+)rem\s*\)", tok)
    if m:
        return step(float(m.group(2)))
    m = re.fullmatch(r"([\d.]+)rem", tok)
    if m:
        return step(float(m.group(1)))
    m = re.fullmatch(r"([\d.]+)em", tok)
    if m:
        v = float(m.group(1))
        if 0.8 <= v <= 1.2:
            return "1em"
        report.append(f"em size left: {tok} in {where}")
        return tok
    m = re.fullmatch(r"([\d.]+)px", tok)
    if m:
        return step(float(m.group(1)) / 16)
    report.append(f"size left: {tok} in {where}")
    return tok


def rescale(css: str, label: str) -> str:
    def fs(m):
        return m.group(1) + size_token(m.group(2), label) + m.group(3)
    css = re.sub(r"(font-size\s*:\s*)([^;}!]+?)(\s*(?:!important)?\s*[;}])", fs, css)

    def font(m):
        val = m.group(2)
        mm = re.match(r"(\s*(?:(?:normal|italic|\d{3}|bold|small-caps)\s+)*)"
                      r"(clamp\([^)]*\)|var\(--[\w-]+\)|[\d.]+(?:rem|em|px))(\s*/\s*[\d.]+(?:rem|px)?)?(\s+.*)$", val)
        if not mm:
            return m.group(0)
        return (m.group(1) + mm.group(1) + size_token(mm.group(2), label) + (mm.group(3) or "")
                + mm.group(4) + m.group(3))
    css = re.sub(r"(\bfont\s*:\s*)([^;}]+?)(\s*[;}])", font, css)
    return css


base = rescale(base, "base")
# Desk Terminal, Joined: the drawing is the order, so no rule reorders anything. Today's sheet moves
# "Send where I am" under Send on a phone with `order`; the ledge already draws it there.
base = base.replace("  .ask .locate { order: 3; flex-basis: 100%; }\n", "  .ask .locate { flex-basis: 100%; }\n")
assert "order:" not in re.sub(r"/\*.*?\*/", "", base, flags=re.S).replace("border:", "").replace("-order:", ""), "an order rule is left in the base"
own = (here / "palette.css").read_text()
strip = lambda c: re.sub(r"\n{2,}", "\n", re.sub(r"/\*.*?\*/", "", c, flags=re.S))
base = strip(base)
own = strip(own)
for line in report:
    print("  !", line)
sheet = base + "\n" + own


def tighten(css: str) -> str:
    """Spaces a browser does not need, outside quoted strings: the budget is characters."""
    parts = re.split(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', css)
    for i in range(0, len(parts), 2):
        p = re.sub(r"\n[ \t]+", "\n", parts[i])
        for a, b in (("; ", ";"), (": ", ":"), (", ", ","), ("{ ", "{"), (" }", "}"), (" {", "{"), (";}", "}")):
            p = p.replace(a, b)
        parts[i] = p
    return "".join(parts)


sheet = tighten(sheet)
(here / "sheet.css").write_text(sheet)
CONCEPT = ("One cased terminal stands at the left of the family's desk on every page (a 6px case, a 2px bezel) and is wired into it: a lit lead leaves a socket on the case and lands in Coming up's NOW lamp, lighting from the socket as the tube warms. Home's glass is a real terminal's: 'Vera, Friday 2 October', Next up beside a small radar, then 'Give Vera something to plan.' in bone with only 'plan.' white-hot before the site's one block cursor, and the box as the tube's last rows. Every dated list leads with one day numeral, and the next plan's numeral carries one lit mark (screen ink, a tight halo, a 1px phosphor underbar) in Coming up's NOW row, on the dial and in the month, every list hangs from a steel rail whose stops are lamps, the square box beside each is the tick, and each band has exactly one light: NOW on Coming up and To do, 'newest' on Lately added.")
COMPANIONS = ("Wheat (#d8c38a) caps every band and edges setup; grounded kind inks in the ring and the kind word only (clay restaurants, straw activities, moss outings, dusk trips, heather shows and events, clay-orange seasons), also marking where each way to start usually lands; bone for the family's words and dates; steel for rails and stops; graphite keys with a phosphor LED and underline for 'here' (no steel slab); pewter for upcoming and off lamps; sage for hover and a ticked box; amber only for late and 'needs a look'; denim for links.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
