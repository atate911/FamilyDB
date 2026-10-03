"""Build palettes/r12-mut-2.json (Long Persistence, Metered) from palette.css and the tokens here.

The css is written for people in palette.css; this squeezes it (comments and runs of space out,
the rule at its head kept) and adds the rules that key a legend's rows to their marks, one per key,
since CSS cannot match two elements by a shared value."""

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "palettes" / "r12-mut-2.json"

TOKENS = {
    "bg": "#0b0e0c", "surface": "#14191c", "surface-2": "#1a1f23", "surface-3": "#20272c",
    "field": "#0b0f11", "line": "#1f2529", "line-2": "#2b3237", "edge": "#68737b",
    "ink": "#d5cfc3", "ink-2": "#b6b0a5", "dim": "#9f9a90", "faint": "#918c83",
    "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c", "outing": "#9fcfb6",
    "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78", "people": "#ffb850",
    "shows": "#ff9fd0", "seasons": "#ff956c", "danger": "#ff6b6b", "on-bright": "#07130c",
    "lit": "#86d9a6", "accent": "#84a0c4", "wash": "#4f60e6",
    "heading": "#ece6d8", "label": "#a8b2bc", "secondary": "#b9c3cf", "card-edge": "#2d3439",
    "bar": "#0f1316", "bezel": "#2c3135", "bubble": "#111712", "bubble-them": "#1d2429",
}


def keyed() -> str:
    """Pointing at a row lights its mark: on at once, fading over the afterglow."""
    keys = [f"k{n}" for n in range(28)] + ["kfar"] + [f"r{n}" for n in range(1, 41)]
    sel = ",".join(f"main:has(.{k}:is(:hover,:focus-within)) .mark.{k} .lit" for k in keys)
    return sel + "{opacity:1;transition-duration:var(--glow-in)}"


def delays() -> str:
    """Each mark flares as the beam passes it: its place across the glass, in fortieths."""
    return "".join(f".t{k}{{--at:calc(var(--sweep)*{k}/40)}}" for k in range(41))


def squeeze(css: str) -> str:
    head = "/* The phosphor draws; the page prints. */\n"
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = css.replace(";}", "}")
    # Put back the spaces some values need.
    css = re.sub(r"\band\(", "and (", css)
    return head + css.strip()


def main() -> None:
    css = squeeze((HERE / "palette.css").read_text()) + keyed() + delays()
    palette = {
        "id": "r12-mut-2",
        "name": "Long Persistence, Metered",
        "tagline": "Long Persistence with its measures drawn as instruments: today's spend swings a phosphor needle on the tube, the month's cost turns printed registers and meters on Status and Settings, and one engraved scale rule divides the parts of every page.",
        "tokens": TOKENS,
        "quietFilter": True,
        "glow": 0.9,
        "screenGlow": 1.0,
        "topGlow": 1.0,
        "washGlow": 2.2,
        "css": css,
    }
    OUT.write_text(json.dumps(palette, indent=1) + "\n")
    print(f"{OUT.name}: css {len(css)} characters")


if __name__ == "__main__":
    main()
