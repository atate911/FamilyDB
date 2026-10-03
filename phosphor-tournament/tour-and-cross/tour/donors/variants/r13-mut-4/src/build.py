"""Build palettes/r13-mut-4.json (from r11-mut-4): Track Diagram's tokens and css (track.css, unchanged but for
comments and whitespace, which are stripped to leave room in the 60,000-character budget), with
the tube's light brought back (phosphor.css, relight.css) appended after it."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]


def squeeze(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    return re.sub(r"\s*([{};])\s*", r"\1", css).strip()


css = squeeze((HERE / "track.css").read_text()) + "\n" + squeeze((HERE / "phosphor.css").read_text()) + "\n" + squeeze((HERE / "relight.css").read_text())
palette = {
    "id": "r13-mut-4",
    "name": "Track Diagram Aglow",
    "tagline": "Track Diagram Relit with the tube's light back on the live things: the mark, 'mind', Send, the lamps and the lit run of track glow in the tube's layered halo over steel, while the slate, steel and plates stay matte.",
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
    notes = json.loads(extra.read_text())
    notes.pop("id", None)
    palette.update(notes)
(ROUND / "palettes" / "r13-mut-4.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
