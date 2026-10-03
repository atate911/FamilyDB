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
ID = "r13-idea-1"
NAME = "Desk Terminal, Joined"
TAGLINE = ("Desk Terminal made whole: every page opens on one head row, the terminal beside the desk "
           "fits, sticks or folds to a line, Home's question is its headline typed at the foot of the "
           "glass with the box as the tube's last rows, and the light reaches the desk and Status as data.")

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
for line in report:
    print("  !", line)
sheet = ("/* Desk Terminal, Joined (r13-idea-1): today's stylesheet as themed for this palette, every size\n"
         "   moved onto six steps, then the design's own rules. Built by variants/r13-idea-1/build.py. */\n"
         + base + "\n\n/* ==== Desk Terminal: the design's own rules ==== */\n" + own)
(here / "sheet.css").write_text(sheet)
CONCEPT = ("One real terminal still stands at the left of the family's desk, the only cased, rounded, lit "
           "thing on the page, and now it joins the page instead of crowding it. On Home it reads like a real "
           "terminal: scrollback at the top of the glass (Next up and the radar), her question at its foot as the "
           "page's headline, and the box to answer in as the tube's last rows over a graphite keyboard ledge. "
           "Everywhere else a head row names the page first; the terminal fits the screen and sticks, or folds "
           "to one lit line where nothing is live. The phosphor now carries data on the desk too: a white-hot "
           "NOW lamp with a lit stretch of rail, a lit NOW tick in To do, and a moving-coil spend meter on Status.")
COMPANIONS = ("Steel reverse (--rev #6b8396 with a #9cc4dc cap) for 'here', the latched key, the band rings and "
              "the rails, and the afterglow's 12% wash; denim (#9db6d6) for links only, so the months are bone; "
              "sage (#86d9a6) for lit states, the LED on a latched key and the afterglow's edge; a cobalt wash "
              "(#4f60e6 at 2.2) at the terminal's top right; graphite for the machine's body, bezel and ledge; "
              "slate trays for the desk; amber only as words, rings and the late bar on the glass; each kind's own "
              "colour named in words mixed 72% toward the ink, and the bar's section icons 40% toward it.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
