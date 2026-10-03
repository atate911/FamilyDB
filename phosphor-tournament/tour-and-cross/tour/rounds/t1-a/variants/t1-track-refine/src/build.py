"""Build palettes/t1-track-refine.json (Track Diagram, Trued) from the tokens here and src/trued.css.

trued.css is the lineage's whole sheet in one file: Track Diagram's line language (r10-idea-3's
track.css), the tube's light from Track Diagram Aglow (r13-mut-4's phosphor.css and relight.css)
and this refinement's rows, keys, cases and type scale, with every rule they replaced deleted.
Comments and spare whitespace are stripped to keep inside the 60,000-character budget."""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]


def squeeze(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    # Leave quoted strings alone; squeeze everything between them.
    for i, part in enumerate(re.split(r'("(?:[^"\\]|\\.)*")', css)):
        if i % 2:
            out.append(part)
            continue
        part = re.sub(r"\s+", " ", part)
        part = re.sub(r"\s*([{};,>])\s*", r"\1", part)
        part = re.sub(r":\s+", ":", part)
        part = part.replace(";}", "}")
        out.append(part)
    return "".join(out).strip()


css = squeeze((HERE / "trued.css").read_text())
palette = {
    "id": "t1-track-refine",
    "name": "Track Diagram, Trued",
    "tagline": "The family's week as a signal box's lit track diagram, trued: three lines on Home, every other list a one-line row on slate, and the tube's own light back on the lamps, the run from now, the key word and the monitors.",
    "tokens": {
        "bg": "#0b0e0c", "surface": "#161c20", "surface-2": "#1b2227", "surface-3": "#212a30",
        "field": "#0c1114", "line": "#20272b", "line-2": "#2e343b", "edge": "#6a757e",
        "ink": "#d6d1c6", "ink-2": "#b6b1a7", "dim": "#a09c93", "faint": "#938f86",
        "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c", "outing": "#86d9a6",
        "lit": "#86d9a6", "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78",
        "people": "#ffb850", "shows": "#ff9dd6", "seasons": "#ff956c", "danger": "#ff6b6b",
        "on-bright": "#07130c",
        "accent": "#9fc2da", "heading": "#ebe6da", "label": "#a3b3bf",
        "secondary": "#b4c3cf", "card-edge": "#2e343b", "bar": "#0f1519", "bezel": "#2a3035",
        "bubble": "#111712", "bubble-them": "#1c252b",
    },
    "quietFilter": True,
    "glow": 1.0, "screenGlow": 1.0, "topGlow": 1.0, "washGlow": 0,
    "css": css,
}
extra = HERE / "notes.json"
if extra.exists():
    notes = json.loads(extra.read_text())
    for key in ("id", "name", "tagline", "tokens", "css"):
        notes.pop(key, None)
    palette.update(notes)
(ROUND / "palettes" / "t1-track-refine.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
