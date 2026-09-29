"""Measure a palette: the accessibility floors docs/STYLE.md keeps, and how bright, green and
one-hued it is (from the palette and, when rendered, from its screenshots).

Usage: venv/bin/python metrics.py palettes/NN-name.json [--json]
Exit status 1 when a floor is not met.
"""

import itertools
import json
import math
import sys
from pathlib import Path

from colorlib import contrast, de, hex_to_rgb, mix, rgb_to_hex, rgb_to_oklch
from theme import Theme

HERE = Path(__file__).parent
MATRIX_GREEN_HUE = rgb_to_oklch(hex_to_rgb("#00ff41"))[2]  # ~142 degrees

# Colours that share a page: the kinds on a grid of ideas.
KINDS = {
    "restaurant": "people",
    "activity": "todo",
    "outing": "outing",
    "trip": "plans",
    "show": "shows",
    "seasonal": "seasons",
    "event": "ideas",
}
# And the parts of the site, in the bar together.
SECTIONS = {"home": "brand", "ideas": "ideas", "plans": "plans", "todo": "todo",
            "wishes": "shows", "family": "people"}
FILLS = ["brand", "ideas", "plans", "todo", "people", "shows", "seasons", "outing", "screen"]
TEXT_ON_SURFACE3 = ["brand", "screen", "outing", "ideas", "plans", "todo", "people", "shows",
                    "seasons", "danger"]


def floors(p: dict) -> tuple[list[dict], dict]:
    t = dict(p["tokens"])
    for role in ("lit", "accent", "halo"):
        t.setdefault(role, t["brand"])
    checks = []

    # The owner: design constraints written in README and the other .md files are loose
    # guidelines for this experiment, not rules. So each check has a GUIDELINE (reported, may be
    # missed when the page is better for it) and, only where it guards the owner's own asks, the
    # page's integrity or plain legibility, a lower HARD level that the check refuses below.
    # From round 10 the owner put nothing off the table: every check here is a guideline. A
    # design below the old hard level is reported as "below the old floor", for the panel to
    # weigh, never refused. What still refuses a design is its integrity and safety (the forms,
    # fields and links, nothing from outside: lint_variant.py and theme.py) and a render that fails.
    def need(name, value, guide, hard=None):
        v = round(value, 2)
        if v >= guide - 1e-9:
            level = "ok"
        else:
            level = "guideline"
            if hard is not None and v < hard - 1e-9:
                name = f"{name} [below the old floor {hard}]"
        checks.append({"check": name, "value": v, "floor": guide, "hard": hard, "level": level, "ok": level != "fail"})

    for ink in ["ink", "ink-2", "dim"]:
        for ground in ["bg", "surface", "surface-3"]:
            # Body and secondary text stay plainly legible (4.5:1 hard); quiet text is a guideline.
            need(f"{ink} on {ground}", contrast(t[ink], t[ground]), 4.5, 4.5 if ink != "dim" else 3.0)
    need("faint on field", contrast(t["faint"], t["field"]), 4.5, 3.0)
    need("faint on surface", contrast(t["faint"], t["surface"]), 4.5, 3.0)
    need("edge on surface (3:1)", contrast(t["edge"], t["surface"]), 3.0, 1.8)
    need("edge on field (3:1)", contrast(t["edge"], t["field"]), 3.0, 1.8)
    for key in TEXT_ON_SURFACE3 + ["lit", "accent"]:
        need(f"{key} text on surface-3", contrast(t[key], t["surface-3"]), 4.5, 3.0)
    for key in FILLS + ["lit"]:
        need(f"on-bright on {key} fill", contrast(t["on-bright"], t[key]), 4.5, 4.5 if key == "brand" else 3.0)
    # Words on a green screen: dim phosphor on the glass at its brightest (docs say 5.8:1 today).
    th = Theme(p)
    scr = hex_to_rgb(t["screen"])
    dim = mix(scr, hex_to_rgb(th.screen_dark("#07120c")), 0.36)
    glass = mix(scr, hex_to_rgb(t.get("screen-glass") or th.screen_dark("#060a08")), 0.91)
    need("screen dim text on glass", contrast(dim, glass), 4.5, 3.0)
    need("screen text on glass", contrast(scr, glass), 7.0, 4.5)
    ink_on_bar = hex_to_rgb(th.screen_dark("#04100a"))
    need("inverse text on screen bar", contrast(ink_on_bar, scr), 4.5, 3.0)

    # The signature the family keeps: a bright green phosphor on a green-black ground.
    def within(name, ok, detail, hard=True):
        level = "ok" if ok else "guideline"
        checks.append({"check": f"signature: {name} ({detail})", "value": 1.0 if ok else 0.0, "floor": 1.0,
                       "level": level, "ok": level != "fail"})

    bL, bC, bh = rgb_to_oklch(hex_to_rgb(t["brand"]))
    within("brand is a bright green phosphor", 140 <= bh <= 165 and bL >= 0.82 and bC >= 0.15,
           f"OKLCH L {bL:.3f}>=0.82, C {bC:.3f}>=0.15, h {bh:.1f} in 140-165; today 0.897/0.186/151.4")
    sL, sC, sh = rgb_to_oklch(hex_to_rgb(t["screen"]))
    within("the monitors glow green", 125 <= sh <= 170 and sL >= 0.78 and sC >= 0.13,
           f"OKLCH L {sL:.3f}>=0.78, C {sC:.3f}>=0.13, h {sh:.1f} in 125-170")
    gL, gC, gh = rgb_to_oklch(hex_to_rgb(t["bg"]))
    within("bg is green-black", gL <= 0.26 and gC >= 0.004 and 115 <= gh <= 200,
           f"OKLCH L {gL:.3f}<=0.26, C {gC:.4f}>=0.004, h {gh:.1f} in 115-200")
    # Cards may carry a tint of a companion now; the page's ground stays green-black.
    sL, sC, _ = rgb_to_oklch(hex_to_rgb(t["surface"]))
    within("surface is dark, a tint at most", sL <= 0.28 and sC <= 0.05,
           f"OKLCH L {sL:.3f}<=0.28, C {sC:.4f}<=0.05", hard=False)
    within("surface is still a dark page", sL <= 0.36, f"OKLCH L {sL:.3f}<=0.36")

    # The roles that reach more of the page, when a palette sets them.
    if "heading" in t:
        for g in ("bg", "surface", "surface-3"):
            need(f"heading on {g}", contrast(t["heading"], t[g]), 4.5, 3.0)
    if "label" in t:
        for g in ("bg", "surface", "surface-3"):
            need(f"label on {g}", contrast(t["label"], t[g]), 4.5, 3.0)
    if "secondary" in t:
        for g in ("surface", "surface-2"):
            need(f"secondary text on {g}", contrast(t["secondary"], t[g]), 4.5, 3.0)
    for role in ("bubble", "bubble-them"):
        if role in t:
            need(f"ink on {role}", contrast(t["ink"], t[role]), 4.5, 4.5)
            need(f"{'label' if 'label' in t else 'dim'} on {role}", contrast(t.get("label", t["dim"]), t[role]), 4.5, 3.0)
    if "bar" in t:
        need("dim (the bar's links) on bar", contrast(t["dim"], t["bar"]), 4.5, 3.0)
        need("ink on bar", contrast(t["ink"], t["bar"]), 4.5, 4.5)

    # Page health, measured on the rendered pages (render.js): nothing scrolls sideways, and no
    # words a person reads are smaller than today's smallest (11.52px).
    health_file = HERE / "out" / p["id"] / "shots" / "health.json"
    if health_file.exists():
        health = {k: v for k, v in json.loads(health_file.read_text()).items() if "overflow" in v}
        worst_over = max(health.items(), key=lambda kv: kv[1]["overflow"])
        need(f"no sideways scroll (worst: {worst_over[0]}, {worst_over[1]['overflow']}px over)",
             1.0 if worst_over[1]["overflow"] <= 1 else 0.0, 1.0, 1.0)
        # The page's words are its own: every page must show today's words (a palette's markup
        # may move them, restyle them, never drop or rewrite them). Dates and times move with the
        # clock, so words with digits and the calendar's own words are left out of the count.
        today_file = HERE / "out" / "00-current" / "shots" / "health.json"
        if p["id"] != "00-current" and today_file.exists():
            import re as _re
            from collections import Counter
            today = json.loads(today_file.read_text())
            skip = _re.compile(r"\d|^(today|tomorrow|yesterday|overdue|ago|in|days?|weeks?|months?|mon|tue|wed|thu|fri|sat|sun|"
                               r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|"
                               r"august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)$")
            def words(t):
                return Counter(w for w in _re.findall(r"[a-z']+|\S*\d\S*", t.lower()) if not skip.search(w))
            worst, where = 0.0, ""
            for page, h in health.items():
                if page not in today or "text" not in h or "text" not in today[page]:
                    continue
                a, b = words(today[page]["text"]), words(h["text"])
                total = max(sum(a.values()), 1)
                changed = (sum((a - b).values()) + sum((b - a).values())) / total
                if changed > worst:
                    worst, where = changed, page
            need(f"the page's words unchanged (worst: {where or '-'}, {round(worst * 100, 1)}% of words differ)",
                 1.0 if worst <= 0.04 else 0.0, 1.0, 1.0)
        smallest = min(health.items(), key=lambda kv: kv[1]["minFont"])
        need(f"smallest text px (on {smallest[0]}: {smallest[1]['minFontAt']})", smallest[1]["minFont"], 11.5, 10.0)

    distances = {}
    for vision in ["typical", "deutan", "protan", "tritan"]:
        worst = min(
            ((de(t[a_key], t[b_key], vision), a, b)
             for (a, a_key), (b, b_key) in itertools.combinations(KINDS.items(), 2)),
            key=lambda x: x[0],
        )
        distances[f"kinds/{vision}"] = {"min": round(worst[0], 1), "pair": f"{worst[1]}~{worst[2]}"}
        # Home, Vera, Status and Settings take `accent` in the bar and the tab bar, beside the
        # sections' own colours.
        places = dict(SECTIONS, home="accent")
        worst_s = min(
            ((de(t[a_key], t[b_key], vision), a, b)
             for (a, a_key), (b, b_key) in itertools.combinations(places.items(), 2)),
            key=lambda x: x[0],
        )
        distances[f"sections/{vision}"] = {"min": round(worst_s[0], 1), "pair": f"{worst_s[1]}~{worst_s[2]}"}
    # Kinds and places always carry their icon and name too, so colour distance is a guideline;
    # only two kinds in (nearly) the same colour for typical sight is refused.
    for key, floor, hard in [("kinds/typical", 12.0, 5.0), ("kinds/deutan", 5.0, None), ("kinds/protan", 5.0, None),
                             ("sections/typical", 12.0, 5.0), ("sections/deutan", 5.0, None), ("sections/protan", 5.0, None)]:
        need(f"CIEDE2000 {key} ({distances[key]['pair']})", distances[key]["min"], floor, hard)
    return checks, distances


def character(p: dict) -> dict:
    """How bright, how green, how one-hued, from the tokens alone."""
    t = p["tokens"]
    out = {}
    for key in ["brand", "screen", "outing"]:
        L, C, h = rgb_to_oklch(hex_to_rgb(t[key]))
        hue_gap = abs((h - MATRIX_GREEN_HUE + 180) % 360 - 180)
        out[key] = {"L": round(L, 3), "C": round(C, 3), "h": round(h, 1),
                    "matrix_hue_gap_deg": round(hue_gap, 1)}
    L, C, h = rgb_to_oklch(hex_to_rgb(t["surface"]))
    out["neutral"] = {"L": round(L, 3), "C": round(C, 4), "h": round(h, 1)}
    # How hard the contrast is: today's ink and green against the page.
    out["ink_on_bg"] = round(contrast(t["ink"], t["bg"]), 2)
    out["brand_on_bg"] = round(contrast(t["brand"], t["bg"]), 2)
    out["glow"] = p.get("glow", 1.0)
    out["screenGlow"] = p.get("screenGlow", 1.0)
    out["topGlow"] = p.get("topGlow", 1.0)
    # A "neon" figure: chroma times lightness of the brand, today's green is the yardstick.
    base = rgb_to_oklch(hex_to_rgb("#6dff9c"))
    out["brand_neon_vs_today"] = round((out["brand"]["C"] * out["brand"]["L"]) / (base[1] * base[0]), 2)
    out["screen_neon_vs_today"] = round((out["screen"]["C"] * out["screen"]["L"]) / (base[1] * base[0]), 2)
    return out


def shots(p: dict) -> dict | None:
    """From the screenshots: how much of the colour on the page is green, how varied the hues are,
    how bright the lit parts are."""
    folder = HERE / "out" / p["id"] / "shots"
    if not folder.exists():
        return None
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    result = {}
    for name in ["home", "ideas", "chat", "status"]:
        f = folder / f"{name}.png"
        if not f.exists():
            continue
        img = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255
        hsv = np.asarray(Image.open(f).convert("HSV")).astype(np.float32) / 255
        h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
        chroma = (s > 0.28) & (v > 0.22)
        n = max(int(chroma.sum()), 1)
        green = chroma & (h >= 85) & (h <= 175)
        bright_green = green & (v > 0.78) & (s > 0.35)
        # Grounded or glowing: how neon is the colour that is NOT the green motif?
        other = chroma & ~green
        neon_other = other & (v > 0.8) & (s > 0.55)
        bins = np.histogram(h[chroma], bins=18, range=(0, 360))[0].astype(np.float64)
        prob = bins / max(bins.sum(), 1)
        entropy = float(-(prob[prob > 0] * np.log2(prob[prob > 0])).sum() / math.log2(18))
        lum = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
        rg = img[..., 0] - img[..., 1]
        yb = 0.5 * (img[..., 0] + img[..., 1]) - img[..., 2]
        colourfulness = float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()))
        result[name] = {
            "coloured_share_pct": round(100 * n / chroma.size, 2),
            "green_share_of_colour_pct": round(100 * float(green.sum()) / n, 1),
            "bright_green_px_permille": round(1000 * float(bright_green.sum()) / chroma.size, 2),
            "other_colour_mean_sat": round(float(s[other].mean()) if other.any() else 0, 3),
            "other_colour_neon_share_pct": round(100 * float(neon_other.sum()) / max(int(other.sum()), 1), 1),
            "hue_entropy": round(entropy, 3),
            "lit_brightness": round(float(v[chroma].mean()) if chroma.any() else 0, 3),
            "mean_luminance": round(float(lum.mean()), 4),
            "colourfulness": round(colourfulness * 100, 2),
        }
    return result


def main() -> None:
    p = json.loads(Path(sys.argv[1]).read_text())
    checks, distances = floors(p)
    report = {
        "id": p["id"],
        "name": p["name"],
        "floors_failed": [c for c in checks if c["level"] == "fail"],
        "guidelines_missed": [c for c in checks if c["level"] == "guideline"],
        "checks": checks,
        "distances": distances,
        "character": character(p),
        "shots": shots(p),
    }
    if "--json" in sys.argv:
        print(json.dumps(report, indent=1))
    else:
        print(f"{p['id']}  {p['name']}")
        for c in checks:
            tag = {"ok": "ok  ", "guideline": "WARN", "fail": "FAIL"}[c["level"]]
            extra = f", hard {c['hard']}" if c.get("hard") is not None and c["level"] != "ok" else ""
            print(f"  {tag} {c['check']}: {c['value']} (guideline {c['floor']}{extra})")
        print("  distances:", json.dumps(distances))
        print("  character:", json.dumps(report["character"]))
        if report["shots"]:
            for k, v in report["shots"].items():
                print(f"  shots/{k}:", json.dumps(v))
        print(f"  => {len(report['floors_failed'])} hard check(s) failed; {len(report['guidelines_missed'])} guideline(s) missed (allowed)")
    sys.exit(1 if report["floors_failed"] else 0)


if __name__ == "__main__":
    main()
