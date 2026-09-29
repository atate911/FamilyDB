"""Turn a palette JSON into a themed copy of FamilyDB's style.css.

Usage: python theme.py palettes/NN-name.json out/NN-name/style.css

A palette names colours by what they are for (see palettes/00-current.json, which reproduces
today's stylesheet). The stylesheet writes the brand green, the amber and a few others out by
hand as rgb() literals; this maps every one of them to the palette too, and re-tints the dark
glass of the green screens and the monitor's plastic to the palette's own hues.
"""

import json
import re
import sys
from pathlib import Path

from colorlib import hex_to_rgb, mix, rgb255, rgb_to_hex, rgb_to_oklch, oklch_to_rgb

CSS = Path("/home/user/FamilyDB/src/familydb/web/static/style.css")

# Semantic key -> the stylesheet's own custom property.
TOKEN_VARS = {
    "bg": "--bg",
    "surface": "--surface",
    "surface-2": "--surface-2",
    "surface-3": "--surface-3",
    "field": "--field",
    "line": "--line",
    "line-2": "--line-2",
    "edge": "--edge",
    "ink": "--ink",
    "ink-2": "--ink-2",
    "dim": "--dim",
    "faint": "--faint",
    "brand": "--green",
    "brand-hover": "--green-hover",
    "ideas": "--lilac",
    "plans": "--cyan",
    "todo": "--lemon",
    "people": "--amber",
    "shows": "--pink",
    "seasons": "--orange",
    "danger": "--red",
    "on-bright": "--on-bright",
}
REQUIRED = list(TOKEN_VARS) + ["screen", "outing"]

ORIG = {
    "bg": "#0b0e0d",
    "surface": "#121615",
    "field": "#0e1211",
    "brand": "#6dff9c",
}
BRAND_RGB = "109 255 156"
LITERAL_TOKENS = {  # rgb() literals that are simply a token written out
    "255 184 80": "people",
    "108 212 255": "plans",
    "247 220 120": "todo",
    "255 107 107": "danger",
    "11 14 13": "bg",
    "14 18 17": "field",
    "18 22 21": "surface",
}
# Hex literals that are the brand green lightened towards white (share of white).
LIGHT_OF_SCREEN = {"#a9ffc7": None, "#e4fff0": None, "#dcffe8": None}
LIGHT_RGB = {"146 255 184", "210 255 225"}
# Dark literals tinted green: the glass of the screens, its shadows and the ink on a lit bar.
SCREEN_DARKS = {
    "#07120c", "#060a08", "#07100b", "#030705", "#020403", "#04100a",
    "#10271a", "#0a1811", "#060e0a", "#06110b",
}
SCREEN_DARK_RGB = {"2 5 3", "3 7 5"}
BRAND_DARKS = {"#173022", "#0e1512"}
NEUTRAL_LITERALS = {
    "#1d2321", "#151a18", "#101412", "#2c3431",
    "#dde4e0", "#c3ccc7", "#a7b2ac", "#3a4541", "#56625c", "#9fb0a6",
}
NEUTRAL_RGB = {"9 12 11"}

# Lines where the green is an everyday "lit" thing rather than the signature itself: the box
# being typed in, checkboxes, done and OK badges, meters, setup steps, a ticked task. A palette
# may give these a calmer green (`lit`); the signature (the mark, the primary button, the key
# word, selection and focus, live lights, the mic) always stays `brand`.
LIT_LINES = {601, 612, 636, 706, 735, 795, 877, 928, 931, 1452, 1616, 1779, 1862, 1876,
             1907, 1914, 1919, 1920, 1921, 1935, 1952, 1971, 1983, 1988}

WASH_LINE = 898  # .welcome: the second, cooler light in the greeting's top right corner

# Where the screens are drawn: the green screens and radar, and her screen beside her lines.
SCREEN_LINES = [(1122, 1349), (1367, 1414)]
PRINT_FROM, PRINT_TO = 2130, 2173  # the printed page keeps its own green-bar paper


def white_share(orig_hex: str) -> float:
    o, g = hex_to_rgb(orig_hex), hex_to_rgb(ORIG["brand"])
    return ((o[0] - g[0]) / (1 - g[0]) + (o[2] - g[2]) / (1 - g[2])) / 2


def lighter(lit, orig_hex: str):
    """The screen's colour lightened as far towards white as orig_hex is from today's green."""
    if rgb_to_hex(lit) == ORIG["brand"]:
        return hex_to_rgb(orig_hex)
    return mix(lit, (1, 1, 1), white_share(orig_hex))


class Theme:
    def __init__(self, palette: dict):
        t = palette["tokens"]
        missing = [k for k in REQUIRED if k not in t]
        if missing:
            raise SystemExit(f"palette is missing tokens: {missing}")
        self.t = t
        self.p = palette
        self.glow = float(palette.get("glow", 1.0))
        self.screen_glow = float(palette.get("screenGlow", 1.0))
        self.top_glow = float(palette.get("topGlow", 1.0))
        self.top_color = t.get("top-glow", t["brand"])
        self.lit = t.get("lit", t["brand"])
        self.accent = t.get("accent")
        self.halo = t.get("halo")
        self.wash = t.get("wash")  # the second light in Home's greeting (top right); plans' cyan today
        self.wash_glow = float(palette.get("washGlow", 1.0))
        self.rgb = {k: hex_to_rgb(v) for k, v in t.items() if isinstance(v, str)}
        # Hue and chroma to re-tint the fixed darks by.
        ref_green = rgb_to_oklch(hex_to_rgb(ORIG["brand"]))
        scr = rgb_to_oklch(self.rgb["screen"])
        brd = rgb_to_oklch(self.rgb["brand"])
        # Each fixed dark is turned by how far the new hue is from the old green's, so the
        # palette of today comes out exactly as it is.
        self.screen_hc = (scr[2] - ref_green[2], min(1.4, scr[1] / ref_green[1]))
        self.brand_hc = (brd[2] - ref_green[2], min(1.4, brd[1] / ref_green[1]))
        ref_s = rgb_to_oklch(hex_to_rgb(ORIG["surface"]))
        new_s = rgb_to_oklch(self.rgb["surface"])
        self.neutral = (new_s[2] - ref_s[2], new_s[1] / max(ref_s[1], 1e-4), new_s[0] - ref_s[0])
        self.screen_glass = t.get("screen-glass")  # optional: the glass colour, by hand

    def rehue(self, orig, turn: float, cscale: float, dL: float = 0.0):
        rgb = hex_to_rgb(orig) if isinstance(orig, str) else orig
        if abs(turn) < 1e-6 and abs(cscale - 1) < 1e-6 and abs(dL) < 1e-6:
            return rgb
        L, C, h = rgb_to_oklch(rgb)
        return oklch_to_rgb(max(0, L + dL), C * cscale, (h + turn) % 360)

    def neutral_hex(self, orig: str) -> str:
        hue, k, dL = self.neutral
        return rgb_to_hex(self.rehue(orig, hue, min(k, 3.0), dL))

    def screen_dark(self, orig: str) -> str:
        hue, k = self.screen_hc
        return rgb_to_hex(self.rehue(orig, hue, k))

    def brand_dark(self, orig: str) -> str:
        hue, k = self.brand_hc
        return rgb_to_hex(self.rehue(orig, hue, k))

    def line(self, text: str, n: int) -> str:
        on_screen = any(a <= n <= b for a, b in SCREEN_LINES)
        if on_screen:
            lit = self.rgb["screen"]
        elif self.halo:
            lit = hex_to_rgb(self.halo)
        elif n in LIT_LINES:
            lit = hex_to_rgb(self.lit)
        else:
            lit = self.rgb["brand"]
        mult = self.screen_glow if on_screen else self.glow
        if n in (129,):  # the afterglow at the top of the page
            lit, mult = hex_to_rgb(self.top_color), self.top_glow

        def brand_rgba(m):
            alpha = float(m.group(1))
            return f"rgb({rgb255(lit)} / {min(1.0, round(alpha * mult, 3))})"

        text = re.sub(rf"rgb\({BRAND_RGB} / ([0-9.]+)\)", brand_rgba, text)

        def other_rgb(m):
            body, alpha = m.group(1), m.group(2)
            if n == WASH_LINE and body == "108 212 255":
                colour = hex_to_rgb(self.wash) if self.wash else self.rgb["plans"]
                return f"rgb({rgb255(colour)} / {min(1.0, round(float(alpha) * self.wash_glow, 3))})"
            if body in LITERAL_TOKENS:
                new = rgb255(self.rgb[LITERAL_TOKENS[body]])
            elif body in LIGHT_RGB:
                new = rgb255(lighter(lit, rgb_to_hex(tuple(int(x) / 255 for x in body.split()))))
            elif body in SCREEN_DARK_RGB:
                new = rgb255(hex_to_rgb(self.screen_dark(rgb_to_hex(tuple(int(x) / 255 for x in body.split())))))
            elif body in NEUTRAL_RGB:
                new = rgb255(hex_to_rgb(self.neutral_hex(rgb_to_hex(tuple(int(x) / 255 for x in body.split())))))
            else:
                return m.group(0)
            if body in LIGHT_RGB and alpha:
                alpha = f"{min(1.0, round(float(alpha) * mult, 3))}"
            return f"rgb({new}" + (f" / {alpha})" if alpha else ")")

        text = re.sub(r"rgb\(([0-9]+ [0-9]+ [0-9]+)(?: / ([0-9.]+))?\)", other_rgb, text)

        def hex_lit(m):
            h = m.group(0).lower()
            if h in LIGHT_OF_SCREEN:
                return rgb_to_hex(lighter(lit, h))
            if h in SCREEN_DARKS:
                if h in ("#07100b", "#060a08") and self.screen_glass:
                    return self.screen_glass if h == "#060a08" else self.screen_dark(h)
                return self.screen_dark(h)
            if h in BRAND_DARKS:
                return self.brand_dark(h)
            if h in NEUTRAL_LITERALS:
                return self.neutral_hex(h)
            if h == "#ffd6d6" and self.t["danger"].lower() != "#ff6b6b":
                return rgb_to_hex(mix(self.rgb["danger"], (1, 1, 1), 0.72))
            return m.group(0)

        if not re.match(r"\s*--[a-z0-9-]+:\s*#", text):  # token lines are done below
            text = re.sub(r"#[0-9a-fA-F]{6}\b", hex_lit, text)

        if on_screen:
            def bloom(m):
                pct = float(m.group(1))
                return f"color-mix(in srgb, var(--phosphor) {min(100, round(pct * self.screen_glow))}%, transparent)"
            text = re.sub(r"color-mix\(in srgb, var\(--phosphor\) ([0-9.]+)%, transparent\)", bloom, text)
        if n in LIT_LINES:
            text = text.replace("var(--green)", "var(--lit)")
        text = text.replace("--phosphor: var(--green);", "--phosphor: var(--screen);")
        text = text.replace(".kind-outing { --kind: var(--green); }", ".kind-outing { --kind: var(--outing); }")
        text = text.replace(":has(.kind-outing) { --accent: var(--green); }", ":has(.kind-outing) { --accent: var(--outing); }")
        return text

    def neutrals_only(self, text: str) -> str:
        return re.sub(
            r"#[0-9a-fA-F]{6}\b",
            lambda m: self.neutral_hex(m.group(0).lower()) if m.group(0).lower() in NEUTRAL_LITERALS else m.group(0),
            text,
        )

    def tokens(self, text: str) -> str:
        for key, var in TOKEN_VARS.items():
            text = re.sub(rf"(\n  {re.escape(var)}: )#[0-9a-fA-F]{{6}};", rf"\g<1>{self.t[key]};", text, count=1)
        extra = (f"\n  --screen: {self.t['screen']};\n  --outing: {self.t['outing']};"
                 f"\n  --lit: {self.lit};\n"
                 # The README's role names, so a palette's own css can say var(--brand) and mean it.
                 "  --brand: var(--green);\n  --brand-hover: var(--green-hover);\n"
                 "  --ideas: var(--lilac);\n  --plans: var(--cyan);\n  --todo: var(--lemon);\n"
                 "  --people: var(--amber);\n  --shows: var(--pink);\n  --seasons: var(--orange);\n"
                 "  --danger: var(--red);\n")
        accent = self.accent or "var(--green)"
        return text.replace("\n  --accent: var(--green);", extra + f"\n  --accent: {accent};", 1)

    def extras(self) -> str:
        """Roles that reach more of the page. Each is emitted only when the palette sets it, so a
        palette without them is exactly today's page."""
        t, rules = self.t, []

        def mix(colour, pct, other="transparent"):
            return f"color-mix(in srgb, {colour} {pct}%, {other})"

        if "heading" in t:
            rules.append(f"h1, h2, .section-head h2, .panel > h2, .panel > summary {{ color: {t['heading']}; }}")
        if "label" in t:
            rules.append(f".eyebrow, .speaker time, .said-by, .said-by strong, .chip-dow, .card-id, .event small {{ color: {t['label']}; }}")
        if "card-edge" in t:
            rules.append(f".panel, .card, .said-bot .bubble, .tabs {{ border-color: {t['card-edge']}; }}")
        if "secondary" in t:
            c = t["secondary"]
            rules.append(f".starters a, .button.secondary, button.quiet, .button.ghost {{ color: {c}; background: {mix(c, 7)}; border-color: {mix(c, 42, 'var(--line-2)')}; }}")
            rules.append(f".starters a:hover, .button.secondary:hover, button.quiet:hover, .button.ghost:hover {{ color: var(--ink); background: {mix(c, 14)}; border-color: {c}; }}")
            if self.p.get("quietFilter"):
                rules.append(f".filters button {{ color: {c}; background: {mix(c, 10, 'var(--surface-2)')}; border-color: {mix(c, 55)}; box-shadow: none; }}")
                rules.append(f".filters button:hover {{ color: var(--ink); background: {mix(c, 18, 'var(--surface-2)')}; border-color: {c}; box-shadow: none; }}")
        if "bubble" in t:
            rules.append(f".said-bot .bubble {{ background: {t['bubble']}; }}")
        if "bubble-them" in t:
            rules.append(f".said-them .bubble {{ background: {t['bubble-them']}; }}")
        if "bezel" in t:
            b = t["bezel"]
            rules.append(f".crt {{ background: linear-gradient(180deg, {mix(b, 90, '#fff')}, {b} 45%, {mix(b, 72, '#000')}); border-color: {mix(b, 82, '#fff')}; }}")
        if "bar" in t:
            rules.append(f".bar {{ background: {mix(t['bar'], 88)}; }}")
        if "ambient" in t:
            a = hex_to_rgb(t["ambient"])
            alpha = min(1.0, round(0.06 * float(self.p.get("ambientGlow", 1.0)), 3))
            top = f"radial-gradient(60% 38% at 50% -10%, rgb({rgb255(hex_to_rgb(self.top_color))} / {min(1.0, round(0.075 * self.top_glow, 3))}), transparent 70%)"
            rules.append(f"html {{ background: {top}, radial-gradient(70% 40% at 100% 30%, rgb({rgb255(a)} / {alpha}), transparent 72%), radial-gradient(60% 35% at 0% 85%, rgb({rgb255(a)} / {round(alpha * 0.6, 3)}), transparent 72%), var(--bg); background-repeat: no-repeat; }}")
        if not rules:
            return ""
        return "\n\n/* ---- Palette roles that reach more of the page (harness) ---- */\n" + "\n".join(rules) + "\n"

    @staticmethod
    def refused(text: str, what: str, budget: int) -> None:
        """Nothing is off the table for a design except what would make the page unsafe: loading
        from outside, scripts in a stylesheet. Everything else is the panel's to vote on."""
        problems = []
        if len(text) > budget:
            problems.append(f"{what} is {len(text)} characters; keep it under {budget}")
        lowered = re.sub(r"\s+", " ", text.lower())
        for bad, why in [("@import", "no imports: everything comes from the page itself"),
                         ("expression(", "no expressions"), ("javascript:", "no scripts in a stylesheet")]:
            if bad in lowered:
                problems.append(f"'{bad}': {why}")
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]*)", lowered):
            target = m.group(1).strip()
            if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", target):
                problems.append(f"url({target[:40]}): only the page's own files (a relative path or /static/...)")
        if problems:
            raise SystemExit(f"{what} refused: " + "; ".join(problems))

    def refinements(self) -> str:
        """The palette's own css, appended after everything else so it wins."""
        extra = self.p.get("css", "")
        if isinstance(extra, list):
            extra = "\n".join(extra)
        if not extra.strip():
            return ""
        self.refused(extra, "css", 60000)
        return self.font_faces(extra) + "\n\n/* ---- The palette's own refinements (harness) ---- */\n" + extra.strip() + "\n"

    def root_tokens(self) -> str:
        """Every token as a custom property, for a design that brings its own stylesheet."""
        t = self.t
        lines = [f"  {var}: {t[key]};" for key, var in TOKEN_VARS.items() if key in t]
        lines += [f"  --screen: {t['screen']};", f"  --outing: {t['outing']};", f"  --lit: {self.lit};",
                  "  --brand: var(--green);", "  --brand-hover: var(--green-hover);", "  --ideas: var(--lilac);",
                  "  --plans: var(--cyan);", "  --todo: var(--lemon);", "  --people: var(--amber);",
                  "  --shows: var(--pink);", "  --seasons: var(--orange);", "  --danger: var(--red);",
                  f"  --accent: {self.accent or 'var(--green)'};"]
        for role in ("heading", "label", "card-edge", "secondary", "bubble", "bubble-them", "bezel", "bar", "halo", "wash"):
            if role in t:
                lines.append(f"  --{role}: {t[role]};")
        return ":root {\n" + "\n".join(lines) + "\n}\n"

    @staticmethod
    def font_faces(extra: str) -> str:
        """The @font-face rules of the library faces this css names (fonts/extra.css, at the
        harness root), served from the site as static/fonts would serve them."""
        root = next((d for d in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
                     if (d / "fonts" / "index.json").exists()), None)
        if root is None:
            return ""
        families = json.loads((root / "fonts" / "index.json").read_text())
        wanted = [f for f in families if f.lower() in extra.lower()]
        if not wanted:
            return ""
        blocks = re.findall(r"@font-face \{.*?\}", (root / "fonts" / "extra.css").read_text(), re.S)
        keep = [b for b in blocks if any(f"'{f}'" in b for f in wanted)]
        return "\n\n/* ---- Library faces this palette uses (harness) ---- */\n" + "\n".join(keep)

    def render(self, css: str) -> str:
        sheet = self.p.get("sheet")
        if sheet:  # a clean sheet: the design's own stylesheet replaces today's entirely
            own = Path(sheet).read_text()
            self.refused(own, f"the stylesheet {sheet}", 200000)
            return (self.font_faces(own + str(self.p.get("css", ""))) + "\n/* ---- The design's tokens (harness) ---- */\n"
                    + self.root_tokens() + "\n/* ---- The design's own stylesheet ---- */\n" + own + "\n" + self.refinements())
        lines = css.split("\n")
        out = []
        for i, text in enumerate(lines, start=1):
            if 2099 <= i < PRINT_FROM:  # more contrast, forced colours: only the neutrals move
                out.append(self.neutrals_only(text))
            elif PRINT_FROM <= i <= PRINT_TO:  # the printed page keeps its green-bar paper
                out.append(text)
            else:
                out.append(self.line(text, i))
        return self.tokens("\n".join(out)) + self.extras() + self.refinements()


def main() -> None:
    palette = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(Theme(palette).render(CSS.read_text()))


if __name__ == "__main__":
    main()
