"""Build palettes/x14a-plate-cross.json and its sheet (run from the round folder:
python3 variants/x14a-plate-cross/build.py).

Backlit Plate. The sheet is today's stylesheet as the harness themes it for these tokens (the
phosphor re-tinted, the glow numbers applied, so every effect of the phosphor kit, E1-E22, is
there), with every font size outside the glass moved onto this design's six steps
(12 / 15 / 17 / 22 / 30 / 44), followed by the design's own rules (plate.css). The glass keeps its
own sizes: VT323 is set for the tube, never on the scale. A clean sheet only because the size
rewrite has to happen in place (Desk Terminal's method).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent
ID = "x14a-plate-cross"
NAME = "Plate, Engraved"
TAGLINE = ('A matte slate plate with a lit edge, engraved seams and one live screen behind it: light only where the plate is cut, and every cut spills its light onto the plate.')

tokens = json.loads((here / "tokens.json").read_text())
tmp_pal = here / ".base-palette.json"
tmp_css = here / ".base-themed.css"
tmp_pal.write_text(json.dumps({"id": ID + "-base", "name": NAME, "tagline": TAGLINE, **tokens}))
subprocess.run([sys.executable, "theme.py", str(tmp_pal), str(tmp_css)], check=True)
base = tmp_css.read_text()
base = re.sub(r"@font-face \{.*?\}\n?", "", base, flags=re.S)

# six steps: 12 legend, 15 facts, 17 text, 22 head, 30 figure, 44 page
BOUNDS = [(0.84, "--fs-note"), (0.99, "--fs-small"), (1.2, "--fs-text"), (1.62, "--fs-head"),
          (2.2, "--fs-title")]
KEEP_PX = {"4px", "6px", "6.5px", "7px", "8.5px", "10px"}
# The glass sets its own type (VT323 at the tube's sizes), so its rules are left as they were.
GLASS = re.compile(r"crt|radar|presence|readout|next-|lost-readout|signin-ready|on-radar|glyph|tube")
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


def rescale_body(css: str, label: str) -> str:
    def fs(m):
        return m.group(1) + size_token(m.group(2), label) + m.group(3)
    css = re.sub(r"(font-size\s*:\s*)([^;}!]+?)(\s*(?:!important)?\s*(?:;|$))", fs, css)

    def font(m):
        val = m.group(2)
        mm = re.match(r"(\s*(?:(?:normal|italic|\d{3}|bold|small-caps)\s+)*)"
                      r"(clamp\([^)]*\)|var\(--[\w-]+\)|[\d.]+(?:rem|em|px))(\s*/\s*[\d.]+(?:rem|px)?)?(\s+.*)$", val)
        if not mm:
            return m.group(0)
        return (m.group(1) + mm.group(1) + size_token(mm.group(2), label) + (mm.group(3) or "")
                + mm.group(4) + m.group(3))
    css = re.sub(r"(\bfont\s*:\s*)([^;}]+?)(\s*(?:;|$))", font, css)
    return css


def rescale(css: str) -> str:
    """Each innermost rule's declarations are moved onto the steps, unless its selector is the
    glass's."""
    def rule(m):
        sel, body = m.group(1), m.group(2)
        if GLASS.search(sel) or sel.strip().startswith("@"):
            return m.group(0)
        return sel + "{" + rescale_body(body, sel.strip()[:40]) + "}"
    return re.sub(r"([^{}]*)\{([^{}]*)\}", rule, css)


base = rescale(base)
# Room for the cross's own rules: the themed base loses its comments and indentation (never a
# space inside a value, since her screen's glyphs are strings that keep theirs).
base = re.sub(r"/\*.*?\*/", "", base, flags=re.S)
base = "\n".join(line.strip() for line in base.splitlines() if line.strip())
own = (here / "plate.css").read_text() + "\n" + (here / "cross.css").read_text()
# Where a mark stands in a slot: one class to a day, so no inline style is needed.
own += "\n/* A slot's days (generated). */\n" + "".join(f".at-{i}{{--x:{i}}}" for i in range(43)) + "\n"
for line in report:
    print("  !", line)
sheet = ("/* Plate, Engraved (x14a-plate-cross), from Backlit Plate: today's stylesheet as themed for this palette, every size off\n"
         "   the glass moved onto six steps, then the design's own rules. Built by\n"
         "   variants/x14a-plate-cross/build.py. */\n"
         + base + "\n\n/* ==== Backlit Plate: the design's own rules ==== */\n" + own)
(here / "sheet.css").write_text(sheet)
CONCEPT = ("Backlit Plate made physical. The page is one matte slate plate over a live phosphor screen, and now the plate shows: a lit top edge and rim light, an anodised grain, engraved seams cut edge to edge between bands, a status foot engraved into its bottom edge. Light still shows only through cuts, at the original tube's full strength, and every cut now has a bevel that takes the glass's light and a pool that spills it onto the plate: 'plan' is a stencil with a hot core whose leak slot throws E7's scanlined pool over the box's lip; Next up is a screen sized to its words with a round radar window cut over its corner; Status opens on a spend screen beside a 30-day trace slot, over a strip of pinhole lamps. The shape of a cut still says what it shows (slot = time, round = range, square = Vera, screen = the screen proper, pinhole = lamp), and what the cuts show is joined to the rows by one engraved day numeral and named by one engraved placard.")
COMPANIONS = ("Slate (#13181b) is the plate and graphite (#192024) its keys; steel (#6b8396 with a #9cc4dc cap) is structure: seams, lips, rings, the latched key and 'here'; brass (#ad9b78, a low-chroma warm) is everything ENGRAVED: placards, the starters' destinations, the lamps' names, the model in the foot, role words; bone (#d4cfc4) reads and linen (#ebe6da) heads; denim (#9db6d6) is links; amber only for late and the one next setup step; each section's own ink, mixed half toward steel, notches its starter key and its month chips. The bright #6dff9c stays in the cuts: the stencil, Send, focus, live pinholes, the glass.")
NOTES = ("Built from r13-idea-2's files: the themed base (comments stripped to make room), plate.css, then cross.css, this cross's own rules. glow, screenGlow and topGlow stay 1.0; washGlow 0, since a corner wash would be light with no cut. --shadow is 0 0 #0000, never none. Brass lives in the sheet's :root (--brass), as tokens.json takes only the README's roles. Removed, with reasons, in variants/x14a-plate-cross/removed-why.txt. Revision 2 (the critic's notes) is the last block of cross.css: the starters three across, Next up's name a step down and linked by the whole window, the leak a square cut, working windows without outer bloom, Status's two windows in one bevel, settings states under their names, the Ideas filters in two columns, square chat windows and a square mic, larger month chips.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, "notes": NOTES,
           **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
