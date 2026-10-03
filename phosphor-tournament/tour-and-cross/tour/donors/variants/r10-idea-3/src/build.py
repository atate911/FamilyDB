"""Build palettes/r10-idea-3.json from the tokens here and src/track.css."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]
css = (HERE / "track.css").read_text()
palette = {
    "id": "r10-idea-3",
    "name": "Track Diagram",
    "tagline": "The family's week drawn as a signal box's illuminated diagram: steel-cyan lines painted on green-black slate boards, a lamp at every stop, times hung in a timetable margin, and #6dff9c lit only for now and live.",
    "tokens": {
        "bg": "#0b0e0c", "surface": "#161c20", "surface-2": "#1b2227", "surface-3": "#212a30",
        "field": "#0c1114", "line": "#20272b", "line-2": "#2e343b", "edge": "#6a757e",
        "ink": "#d6d1c6", "ink-2": "#b6b1a7", "dim": "#a09c93", "faint": "#938f86",
        "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#74f0a3", "outing": "#86d9a6",
        "lit": "#86d9a6", "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78",
        "people": "#ffb850", "shows": "#ff9fd0", "seasons": "#ff956c", "danger": "#ff6b6b",
        "on-bright": "#07130c",
        "accent": "#a7c4d8", "wash": "#4f66e0", "heading": "#ebe6da", "label": "#a3b3bf",
        "secondary": "#b4c3cf", "card-edge": "#2e343b", "bar": "#0f1519", "bezel": "#3a3f45",
        "bubble": "#111712", "bubble-them": "#1c252b",
    },
    "quietFilter": True,
    "glow": 0.9, "screenGlow": 0.8, "topGlow": 1.0, "washGlow": 2.4,
    "css": css,
}
extra = HERE / "notes.json"
if extra.exists():
    palette.update(json.loads(extra.read_text()))
(ROUND / "palettes" / "r10-idea-3.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
