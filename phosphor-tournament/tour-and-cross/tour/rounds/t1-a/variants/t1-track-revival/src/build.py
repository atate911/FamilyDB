"""Build palettes/t1-track-revival.json: Track Diagram's tokens (screen now #6dff9c, the light at
1.0, no corner wash) and src/relaid.css, squeezed to fit the 60,000-character budget."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]


def squeeze(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r"(?<=[:(\s,/-])0\.(\d)", r".\1", css)
    css = re.sub(r";}", "}", css)
    css = re.sub(r":\s+", ":", css)
    return css.strip()


css = squeeze((HERE / "relaid.css").read_text())
palette = {
    "id": "t1-track-revival",
    "name": "Signal Box Relaid",
    "tagline": "The family's week drawn as a signal box draws its track: steel lines on slate, straight runs and 45-degree turns, a lamp at every stop and a buffer where each line ends, and #6dff9c lit only where something is now.",
    "tokens": {
        "bg": "#0b0e0c", "surface": "#161c20", "surface-2": "#1b2227", "surface-3": "#212a30",
        "field": "#0c1114", "line": "#20272b", "line-2": "#2e343b", "edge": "#6a757e",
        "ink": "#d6d1c6", "ink-2": "#b6b1a7", "dim": "#a09c93", "faint": "#938f86",
        "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c", "outing": "#b5c87d",
        "lit": "#86d9a6", "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78",
        "people": "#ffb850", "shows": "#ff9fd0", "seasons": "#c3a85d", "danger": "#ff6b6b",
        "on-bright": "#07130c",
        "accent": "#a7c4d8", "wash": "#4f66e0", "heading": "#ebe6da", "label": "#a3b3bf",
        "secondary": "#b4c3cf", "card-edge": "#2e343b", "bar": "#0f1519", "bezel": "#3a3f45",
        "bubble": "#111712", "bubble-them": "#1c252b",
    },
    "quietFilter": True,
    "glow": 1.0, "screenGlow": 1.0, "topGlow": 1.0, "washGlow": 0,
    "css": css,
}
extra = HERE / "notes.json"
if extra.exists():
    notes = json.loads(extra.read_text())
    notes.pop("id", None)
    palette.update(notes)
(ROUND / "palettes" / "t1-track-revival.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
