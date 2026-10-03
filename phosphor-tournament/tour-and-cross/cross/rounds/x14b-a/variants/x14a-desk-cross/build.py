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
ID = "x14a-desk-cross"
NAME = "Desk Terminal, Patched"
TAGLINE = ("One cased terminal patched into the family's desk: a lit lead runs from Next up into Coming up's rail, Home asks the family to give Vera something to plan, and every list hangs from a rail whose stops are its controls.")

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
(here / "sheet.css").write_text(sheet)
CONCEPT = ("One cased terminal still stands at the left of the family's desk, now thinner (a 6px case, a 2px "
           "graphite bezel) and patched into it: a lit lead leaves a socket on the case at Next up's row and "
           "lands in the NOW lamp of Coming up's rail, so machine and desk are one drawing. Home's glass is a "
           "real terminal's: scrollback, Next up beside a small radar, then the page's headline, 'Give Vera "
           "something to plan.', with only 'plan' white-hot, and the box as the tube's last rows behind a lit "
           "prompt. Every list hangs from a steel rail whose stops are its controls: Coming up's stops, setup's "
           "three ring stops, To do's tick line under a sans due margin. Each tube draws its page: a round "
           "countdown dial on Plans, a map of numbered, linked blips on Ideas, late bars on To do, a needle on Status.")
COMPANIONS = ("Bone (#d4cfc4) for the family's words, dates and the 2px cap over each band; steel (#58697a line, "
              "#6b8396 reverse with a #9cc4dc cap) for rails, stops, 'here' and the latched key; pewter (#7a8590) "
              "for off and unset rings; sage (#86d9a6) for hover edges and a ticked box; amber only for late and "
              "'needs a look' (words, ring stops, a 2px bar), never a section; denim (#9db6d6) for links only; "
              "graphite for the machine, slate for the desk, a warmer slate (#141b20) for the month's weekends; "
              "each kind's colour only in the ring of its icon.")
palette = {"id": ID, "name": NAME, "tagline": TAGLINE, "concept": CONCEPT, "companions": COMPANIONS, **tokens, "sheet": f"variants/{ID}/sheet.css"}
Path(f"palettes/{ID}.json").write_text(json.dumps(palette, indent=1) + "\n")
tmp_pal.unlink()
tmp_css.unlink()
print(len(sheet), "characters in the sheet;", len(own), "of them the design's own")
