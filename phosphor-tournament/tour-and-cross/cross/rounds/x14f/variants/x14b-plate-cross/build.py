"""Build palettes/x14a-plate-cross.json and its sheet (run from the round folder:
python3 variants/x14b-plate-cross/build.py).

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
ID = "x14b-plate-cross"
NAME = "Plate, Channelled"
TAGLINE = ('A matte slate plate over one lit screen, its cuts carrying their light down engraved channels to the rows they report, lit only from now to next.')

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
own = (here / "plate.css").read_text() + "\n" + (here / "cross.css").read_text() + "\n" + (here / "channel.css").read_text()
# Where a mark stands in a slot: one class to a day, so no inline style is needed.
own += "\n/* A slot's days (generated). */\n" + "".join(f".at-{i}{{--x:{i}}}" for i in range(43)) + "\n"
# A row pointed at lights its node, its drop and its tick together (generated: one index a row).
_H = ":is(.coming,.coming-list)"
_on = lambda i: f"{_H}:has(.r-{i}:hover,.r-{i}:focus-within)"
own += ("/* A row and its tick light together (generated). */\n"
        + ",".join(f"{_on(i)} .mk.m-{i}" for i in range(10)) + "{--hot:1;opacity:1;width:2px;background:color-mix(in srgb,var(--phosphor) 30%,#fff);box-shadow:0 0 0 1px color-mix(in srgb,var(--phosphor) 55%,transparent),0 0 8px var(--phosphor),0 0 20px color-mix(in srgb,var(--phosphor) 50%,transparent)}\n"
        + ",".join(f"{_on(i)} .mk-n.m-{i}" for i in range(10)) + "{color:var(--phosphor-bright);opacity:1;text-shadow:0 0 0.45em rgb(109 255 156/.45),0 0 1.3em rgb(109 255 156/.22)}\n")
# Room for the channels: the design's own rules lose their comments and indentation too (the
# readable sources are plate.css, cross.css and channel.css beside this file).
own = re.sub(r"/\*.*?\*/", "", own, flags=re.S)
own = "\n".join(line.strip() for line in own.splitlines() if line.strip())
own = re.sub(r";\s*\n\s*", ";", own)
own = re.sub(r"\{\s*\n\s*", "{", own)
own = re.sub(r"\n\s*\}", "}", own)
own = re.sub(r"\s*([{};,>])\s*", r"\1", own)
own = re.sub(r":\s+", ":", own)
own = own.replace(";}", "}")
for line in report:
    print("  !", line)
sheet = ("/* Plate, Channelled (x14b-plate-cross), from Backlit Plate: today's stylesheet as themed for this palette, every size off\n"
         "   the glass moved onto six steps, then the design's own rules. Built by\n"
         "   variants/x14b-plate-cross/build.py. */\n"
         + base + "\n\n/* ==== Backlit Plate: the design's own rules ==== */\n" + own)
(here / "sheet.css").write_text(sheet)
CONCEPT = ("Plate, Engraved with its light routed into the lists. The page is still one matte slate plate over a live phosphor screen, light showing only where the plate is cut, at the original tube's full strength, and the shape of a cut still saying what it shows (slot = time, round = range, square = Vera, screen = the screen proper, pinhole = lamp). It adds one cut: the CHANNEL, a 2px groove engraved into the slate that carries a cut's light to the row it reports, lit only from now to the next thing. Coming up's slot drops one channel straight from its Now edge through the bevel, and the rows hang from it, a square node at each day numeral, lit down to Next's; To do's channel runs through the tick column, amber at dim strength while things are late, crossed by a lit NOW with a pinhole lamp; Status's spend is a round cut, a square-root dial with an amber limit tick, a dashed ghost at the busiest day and a pinhole hub, overlapping the 30-day trace, and the dial throws a channel down onto a groove over the lamp strip, lit only over the lamps that work; each busy day in the month is a small lit window; on Settings each part has its pinhole and the part that needs a look an amber channel into its arrow; a focused field is lit along its top lip only. 'plan' is lit by E1's halo alone and its light falls as an edgeless scanlined pool on the box, whose ways to start are plate keys cut flush to its foot. Calm, machined, and now the light visibly goes somewhere.")
COMPANIONS = ("Slate (#13181b) is the plate and graphite (#192024) its keys; steel (#6b8396, #9cc4dc cap) is structure: seams, the starters' one edge, the month's 'here' ring, the latched key; brass (#ad9b78) is every engraved word: placards in plain words, the starters' 'lands in' lines, lamp names, the model in the foot; bone (#d4cfc4) reads and linen (#ebe6da) heads; denim (#9db6d6) is links; amber (#f7b955) only for late (the late channel, 'was due', the 3 LATE tag) and 'needs a look' (the setup lead rule, the Status tally); each kind's own ink lives in a 22px square cut whose floor is that ink mixed 70% toward slate (activity lemon, restaurant amber-orange, outing sage, trip cyan, show pink on the kids' wishes), colour in solid things with no glow. The bright #6dff9c stays in the cuts: the stencil 'plan', Send, focus and the focused field's top lip, live pinholes and the NOW lamp, Next's tick and the lit channel segments, the glass.")
NOTES = ("Built from x14a-plate-cross's files: the themed base, plate.css, cross.css, then channel.css, this cross's own rules (all three minified into the sheet by build.py to stay under the 200,000-character budget; the readable sources sit beside it). New markup: _ask.html (the question, the box wrapper, starters flush inside it), _ui.html (marks carry their row's index, channel_bus, the radar's ring labels on a diagonal, the head tally's unit span), home.html, plans.html, plans_month.html, tasks.html, status.html (the round dial), ideas.html (visible selects). glow, screenGlow and topGlow stay 1.0. Removed, with reasons, in removed-why.txt. Revision: build.py also strips the spaces round braces, semicolons, commas and colons in the design's own rules (no rule has a string with those in it), which made room for the revision block at the end of channel.css.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, "notes": NOTES,
           **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
