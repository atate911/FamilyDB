"""Minify the palette's css sources into palettes/r9-idea-4.json ("css")."""
import json, re, sys
from pathlib import Path
here = Path(__file__).resolve().parent
pal = here.parents[2] / "palettes" / "r9-idea-4.json"
parts = [here / n for n in ("galley.css", "lines.css")]
css = "\n".join(p.read_text() for p in parts if p.exists())
css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
css = re.sub(r"\s+", " ", css)
css = re.sub(r"\s*([{};,])\s*", r"\1", css)
css = re.sub(r":\s+", ":", css)
css = css.replace(";}", "}").replace("transparent", "#0000").strip()
names = {"--rule-bar": "--rb", "--pewter": "--pw", "--steel": "--st", "--glow-c": "--gc", "--strip": "--sp",
         "--facts": "--fa", "--breath": "--br", "--desig": "--dg", "--tray": "--ty",
         "--lead": "--ld", "--tint": "--tn", "--label": "--lb", "--heading": "--hd", "--afterglow": "--afterglow",
         "--hair": "--hr", "--mark": "--mk", "--cell": "--cl", "--well": "--wl", "--lift": "--lf",
         "--turn": "--tu"}
for long, short in names.items():
    css = re.sub(re.escape(long) + r"(?![\w-])", short, css)
# Tokens that are the same on every page are written as their values (the per-page ones, the
# accent and the section colours, stay variables).
for var, val in {"--brand": "#6dff9c", "--lit": "#86d9a6", "--surface-3": "#1d252b", "--surface-2": "#1a2125", "--bg": "#0b0e0c"}.items():
    css = css.replace("var(" + var + ")", val)
# A calc() of two plain lengths is written as the length it comes to (1rem = 16px).
def fold(m):
    a = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
    c = float(m.group(4)) * (16 if m.group(5) == "rem" else 1)
    v = round(a + c if m.group(3) == "+" else a - c, 2)
    s = ("%g" % v).replace("0.", ".", 1) if abs(v) < 1 else "%g" % v
    return s + "px"
css = re.sub(r"calc\((-?[\d.]+)(rem|px) ([+-]) (-?[\d.]+)(rem|px)\)", fold, css)
p = json.loads(pal.read_text())
p["css"] = css
pal.write_text(json.dumps(p, indent=2) + "\n")
print(len(css), "chars of css", "brace balance", css.count("{") - css.count("}"))
