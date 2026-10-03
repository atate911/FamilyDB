"""Build palettes/t1-track-mut.json: Track Diagram (r10-idea-3) whole, with the tube's light back.

track.css is the parent's stylesheet layer, unchanged; phosphor.css is this mutant's, appended
after it. The tokens are the parent's except the monitors' phosphor (screen) and the glow numbers.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]
parent = (HERE / "track.css").read_text()
# Both layers are carried whole; only their inner comments and spare whitespace are left out, to
# keep the css under the harness's 60,000 characters (each header stays and says what it is for).


def compact(sheet: str) -> str:
    """The sheet's header comment kept, every other comment dropped and the whitespace between
    rules and declarations taken out, never inside a quoted string (the source stays readable)."""
    head, _, body = sheet.partition("*/")
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    parts = re.split(r'("(?:[^"\\]|\\.)*")', body)
    for i in range(0, len(parts), 2):
        t = re.sub(r"\s+", " ", parts[i])
        t = re.sub(r"\s*([{};])\s*", r"\1", t)
        t = re.sub(r",\s+", ",", t)
        t = re.sub(r":\s+", ":", t)
        parts[i] = t.replace(";}", "}")
    return head + "*/\n" + "".join(parts).strip() + "\n"


css = compact(parent) + compact((HERE / "phosphor.css").read_text())
palette = {
    "id": "t1-track-mut",
    "name": "Track Diagram, Tube Lit",
    "tagline": "Track Diagram with the green-screen tube switched back on: the lamps on the line are glowing points with a lit now on every timetable, the monitors bloom and spill, and the machine's voice is lit while the family's words and plates stay matte.",
    "tokens": {
        "bg": "#0b0e0c", "surface": "#161c20", "surface-2": "#1b2227", "surface-3": "#212a30",
        "field": "#0c1114", "line": "#20272b", "line-2": "#2e343b", "edge": "#6a757e",
        "ink": "#d6d1c6", "ink-2": "#b6b1a7", "dim": "#a09c93", "faint": "#938f86",
        "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c", "outing": "#86d9a6",
        "lit": "#86d9a6", "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78",
        "people": "#ffb850", "shows": "#ff9fd0", "seasons": "#ff956c", "danger": "#ff6b6b",
        "on-bright": "#07130c",
        "accent": "#a7c4d8", "wash": "#4f66e0", "heading": "#ebe6da", "label": "#a3b3bf",
        "secondary": "#b4c3cf", "card-edge": "#2e343b", "bar": "#0f1519", "bezel": "#3a3f45",
        "bubble": "#111712", "bubble-them": "#1c252b",
    },
    "quietFilter": True,
    "glow": 1.0, "screenGlow": 1.0, "topGlow": 1.0, "washGlow": 2.4,
    "css": css,
}
extra = HERE / "notes.json"
if extra.exists():
    palette.update(json.loads(extra.read_text()))
(ROUND / "palettes" / "t1-track-mut.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
