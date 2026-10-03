"""Build palettes/t1-track-graft.json (Track Diagram, Branch Lines).

The lineage's sheet, in the order it is appended: Track Diagram's line language (track.css, from
r10-idea-3, with the rules the branch lines replace deleted), the tube's light from Track Diagram
Aglow (phosphor.css and relight.css, from r13-mut-4), then this graft's branch lines (branch.css):
Chat's double-track main line, Status's indication panel, Ideas' line from home, the month as
week tracks, and the lineage's fixes. Comments and spare whitespace are stripped to keep inside
the 60,000-character budget."""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]


FIXED = {"brand": "6dff9c", "screen": "6dff9c", "lit": "86d9a6", "steel": "a7c4d8"}
# Tokens that no rule re-scopes and more-contrast does not lift: written out in the minified copy.
CONST = {"brand": "6dff9c", "steel": "a7c4d8", "heading": "ebe6da", "rail": "58697a", "label": "a3b3bf",
         "tray": "0f1519", "lit": "86d9a6", "bg": "0b0e0c", "amber": "ffb850", "cyan": "70dcf4",
         "lemon": "f7dc78", "pink": "ff9fd0", "red": "ff6b6b", "pewter": "7a8590", "past": "2e343b",
         "well": "080c0d", "vera": "111712", "sage": "86d9a6", "rail-hi": "7d8fa0", "tray-edge": "182026",
         "plate-edge": "262e35"}
# The sheet's own properties (never the page's or the theme's), shortened in the minified copy.
SHORT = {"lamp-core": "lk", "lamp-glow": "lg", "lamp-swell": "ls", "run-bloom": "rb", "run-v": "rv",
         "run-h": "rz", "key-lit": "kl", "key-ink": "ki", "row-glow": "rg", "nowgap": "ng",
         "ph-tight": "pt", "ph-wide": "pw", "glass-edge": "ge", "halo-at": "ha"}


def hexa(r, g, b, a=1.0):
    h = "#%02x%02x%02x" % (round(r), round(g), round(b))
    if a < 1:
        h += "%02x" % round(a * 255)
    # #aabbcc -> #abc where it can
    if len(h) == 7 and h[1] == h[2] and h[3] == h[4] and h[5] == h[6]:
        h = "#" + h[1] + h[3] + h[5]
    return h


def parse_hex(h):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a


def mix(m):
    """color-mix(in srgb, A p%, B) of two written-out colours, done here (premultiplied)."""
    a, p, b = m.group(1), float(m.group(2)) / 100, m.group(3)
    r1, g1, b1, a1 = parse_hex(a)
    r2, g2, b2, a2 = parse_hex(b)
    al = a1 * p + a2 * (1 - p)
    if al == 0:
        return "#0000"
    c = [(x * a1 * p + y * a2 * (1 - p)) / al for x, y in ((r1, r2), (g1, g2), (b1, b2))]
    return hexa(*c, al)


def squeeze(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for i, part in enumerate(re.split(r'("(?:[^"\\]|\\.)*")', css)):
        if i % 2:
            out.append(part)
            continue
        part = re.sub(r"\s+", " ", part)
        part = re.sub(r"\s*([{};,>])\s*", r"\1", part)
        part = re.sub(r"([:(])\s+", r"\1", part)
        part = re.sub(r"\s+\)", ")", part)
        part = part.replace(";}", "}")
        part = re.sub(r"(?<![\w.#])0\.(\d)", r".\1", part)
        part = part.replace("transparent", "#0000").replace(" / ", "/")
        # The palette's fixed colours, faded, as hex with alpha (the source keeps the var()s).
        part = re.sub(r"color-mix\(in srgb,var\(--(brand|screen|lit|steel)\) ([\d.]+)%,#0000\)",
                      lambda m: "#" + FIXED[m.group(1)] + "%02x" % round(float(m.group(2)) * 2.55), part)
        part = re.sub(r"var\(--(" + "|".join(sorted(CONST, key=len, reverse=True)) + r")\)", lambda m: "#" + CONST[m.group(1)], part)
        part = re.sub(r"rgb\((\d+) (\d+) (\d+)(?:/([\d.]+))?\)", lambda m: hexa(int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4) or 1)), part)
        part = re.sub(r"#([0-9a-f]{3,8})\b", lambda m: "#" + m.group(1), part)
        for _ in range(2):
            part = re.sub(r"color-mix\(in srgb,(#[0-9a-f]{3,8}) ([\d.]+)%,(#[0-9a-f]{3,8})\)", mix, part)
        part = re.sub(r"--(" + "|".join(sorted(SHORT, key=len, reverse=True)) + r")\b", lambda m: "--" + SHORT[m.group(1)], part)
        part = part.replace("var(--sq)", "4px")
        out.append(part)
    return "".join(out).strip()


def dedupe(css: str) -> str:
    """Drop a declaration that a later rule with the same selector, in the same @media, sets again:
    same selector, same context, later wins, so the earlier one never shows (unless it is
    !important and the later one is not)."""
    out, i, ctx, spans = [], 0, [], []
    tokens = re.split(r"([{}])", css)
    # Walk the text, recording (context, selector, start, end) of each plain rule's body.
    pos, sel_stack, plain = 0, [], []
    buf = ""
    for tok in tokens:
        if tok == "{":
            sel = buf.strip().split("}")[-1].strip()
            sel_stack.append(sel)
            if not sel.startswith("@"):
                plain.append([tuple(s for s in sel_stack[:-1]), sel, pos + 1, None])
            buf = ""
        elif tok == "}":
            if sel_stack:
                top = sel_stack.pop()
                if not top.startswith("@") and plain and plain[-1][3] is None:
                    plain[-1][3] = pos
            buf = ""
        else:
            buf += tok
        pos += len(tok)
    plain = [p for p in plain if p[3] is not None and not any(x.startswith("@keyframes") for x in p[0])]
    last = {}
    for idx, (c, sel, a, b) in enumerate(plain):
        last.setdefault((c, sel), []).append(idx)
    drop = {}
    for key, idxs in last.items():
        if len(idxs) < 2:
            continue
        later = set()
        for idx in reversed(idxs):
            c, sel, a, b = plain[idx]
            decls = css[a:b].split(";")
            keep = []
            for d in decls:
                prop = d.split(":", 1)[0].strip()
                if ":" in d and prop in later and "!important" not in d:
                    continue
                keep.append(d)
                if ":" in d and "!important" not in d:
                    later.add(prop)
            drop[idx] = ";".join(k for k in keep if k.strip())
    pieces, cur = [], 0
    for idx in sorted(drop):
        c, sel, a, b = plain[idx]
        pieces.append(css[cur:a]); pieces.append(drop[idx]); cur = b
    pieces.append(css[cur:])
    css = "".join(pieces)
    return re.sub(r"(^|[{}])[^{}@]+\{\}", r"\1", css)


css = dedupe("\n".join(squeeze((HERE / name).read_text()) for name in ("track.css", "phosphor.css", "relight.css", "branch.css")))
# Generated rules. On Ideas, pointing at or focusing a row lights its station on the line from
# home, one :has() per place in the list (the list's own order, so an idea's number never has to
# be known in advance): on in 0.12s, fading over 1.2s.
ROWS = 16
css += "\n" + ",".join(f":has(.r{n}:hover,.r{n}:focus-within) .s{n}" for n in range(1, ROWS + 1)) + "{--on:1}"
palette = {
    "id": "t1-track-graft",
    "name": "Track Diagram, Branch Lines",
    "tagline": "The family's week as a signal box's lit track diagram, with branch lines drawn from each page's own data: Chat on a double-track main line, Status's lamps banked on one indication shelf, Ideas as the line out of home, and the month's weeks as lit track.",
    "tokens": {
        "bg": "#0b0e0c", "surface": "#161c20", "surface-2": "#1b2227", "surface-3": "#212a30",
        "field": "#0c1114", "line": "#20272b", "line-2": "#2e343b", "edge": "#6a757e",
        "ink": "#d6d1c6", "ink-2": "#b6b1a7", "dim": "#a09c93", "faint": "#938f86",
        "brand": "#6dff9c", "brand-hover": "#92ffb8", "screen": "#6dff9c", "outing": "#86d9a6",
        "lit": "#86d9a6", "ideas": "#b58cec", "plans": "#70dcf4", "todo": "#f7dc78",
        "people": "#ffb850", "shows": "#ff9fd0", "seasons": "#ff956c", "danger": "#ff6b6b",
        "on-bright": "#07130c",
        "accent": "#a7c4d8", "wash": "#4f66e0", "heading": "#ebe6da", "label": "#a3b3bf",
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
    notes.pop("id", None)
    palette.update(notes)
(ROUND / "palettes" / "t1-track-graft.json").write_text(json.dumps(palette, indent=1, ensure_ascii=False) + "\n")
print("css chars:", len(css))
