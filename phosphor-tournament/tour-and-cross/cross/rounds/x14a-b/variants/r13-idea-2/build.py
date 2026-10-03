"""Build palettes/r13-idea-2.json and its sheet (run from the round folder:
python3 variants/r13-idea-2/build.py).

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
ID = "r13-idea-2"
NAME = "Backlit Plate"
TAGLINE = ("One live phosphor screen lies behind the whole page and a matte slate plate is laid over "
           "it: light shows only where the plate is cut, and the plate is cut only where the "
           "machine is live.")

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
own = (here / "plate.css").read_text()
# Where a mark stands in a slot: one class to a day, so no inline style is needed.
own += "\n/* A slot's days (generated). */\n" + "".join(f".at-{i}{{--x:{i}}}" for i in range(43)) + "\n"
for line in report:
    print("  !", line)
sheet = ("/* Backlit Plate (r13-idea-2): today's stylesheet as themed for this palette, every size off\n"
         "   the glass moved onto six steps, then the design's own rules. Built by\n"
         "   variants/r13-idea-2/build.py. */\n"
         + base + "\n\n/* ==== Backlit Plate: the design's own rules ==== */\n" + own)
(here / "sheet.css").write_text(sheet)
CONCEPT = ("A backlit faceplate: one live phosphor screen lies behind the whole page, and the page is a "
           "matte slate plate laid over it. Light is seen only where the plate is cut, and it is cut only "
           "where the machine is live, so every effect of the original tube has a physical cause: 'mind' "
           "is stencilled through the plate, Send is a backlit key whose light pools out of its gap, a "
           "field lights round its cut edge while you type, every lamp is a pinhole, and the screens are "
           "windows whose light spills onto their bevels and the plate. The shape of a cut says what it "
           "shows, on every page: a slot is time, a round window is place, a square window is Vera, a "
           "4:3 window is the screen proper, a pinhole is live or not. Where nothing is live the plate "
           "stays whole, so the page is calm and the light is exactly where attention belongs.")
COMPANIONS = ("Cool slate (#13181b) is the plate itself and graphite (#192024) its keys; steel reverse "
              "(#6b8396 with a #9cc4dc cap and a pinhole LED) is 'here' and the latched key; steel "
              "(#82a4b5) is the accent of the pages with no colour of their own and denim (#9db6d6) the "
              "links; pewter (#47535b) leads every engraved rule; bone (#d4cfc4) is the reading ink and "
              "linen (#ebe6da) the heads; amber only as words and rings for late and needs a look; each "
              "kind named in its own colour mixed 72% toward the ink. The green stays in the cuts.")
NOTES = ("THE RULE: one screen, one plate. Nothing on the page glows by itself; light shows only where the plate "
         "is cut, and the plate is cut only where the machine is live. washGlow is 0 on purpose: a coloured corner "
         "wash would be light with no cut. glow, screenGlow and topGlow stay at 1.0, so every kit effect (E1-E22) is "
         "at full strength where it has a cause, and --shadow is 0 0 #0000, never none. Removed, with reasons, in "
         "variants/r13-idea-2/removed-why.txt: every monitor case (replaced by the plate's cut), the Ideas Kind "
         "select and Restaurants tab (replaced by the kind keys), the filter selects (keys), and the cobalt wash.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, "notes": NOTES,
           **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
