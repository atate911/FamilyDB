"""One table of every palette's measures, for judging side by side.

Usage: venv/bin/python summary.py [--json]
"""

import json
import sys
from pathlib import Path

from metrics import character, floors, shots

HERE = Path(__file__).parent

rows = []
for f in sorted((HERE / "palettes").glob("*.json")):
    p = json.loads(f.read_text())
    checks, dist = floors(p)
    ch = character(p)
    sh = shots(p) or {}
    avg = lambda k: round(sum(v[k] for v in sh.values()) / len(sh), 3) if sh else None  # noqa: E731
    rows.append({
        "id": p["id"],
        "name": p["name"],
        "floors_failed": sum(c["level"] == "fail" for c in checks),
        "guidelines_missed": sum(c["level"] == "guideline" for c in checks),
        "min_text_contrast": min(c["value"] for c in checks if "text" in c["check"] or c["check"].startswith(("ink", "dim", "faint"))),
        "kinds_dE_typ/deu/pro": f"{dist['kinds/typical']['min']}/{dist['kinds/deutan']['min']}/{dist['kinds/protan']['min']}",
        "brand": p["tokens"]["brand"],
        "screen": p["tokens"]["screen"],
        "brand_LCh": f"{ch['brand']['L']}/{ch['brand']['C']}/{ch['brand']['h']}",
        "brand_neon_vs_today": ch["brand_neon_vs_today"],
        "screen_neon_vs_today": ch["screen_neon_vs_today"],
        "ink/brand_on_bg": f"{ch['ink_on_bg']}/{ch['brand_on_bg']}",
        "neutral_h/C": f"{ch['neutral']['h']}/{ch['neutral']['C']}",
        "glow/screenGlow/topGlow": f"{ch['glow']}/{ch['screenGlow']}/{ch['topGlow']}",
        "green_share_of_colour_pct": avg("green_share_of_colour_pct"),
        "bright_green_px_permille": avg("bright_green_px_permille"),
        "other_colour_neon_pct": avg("other_colour_neon_share_pct"),
        "hue_entropy": avg("hue_entropy"),
        "lit_brightness": avg("lit_brightness"),
        "mean_luminance": avg("mean_luminance"),
        "colourfulness": avg("colourfulness"),
        "targets_under_44_home": (lambda h: f"{h['home']['targetsUnder44']}/{h['home']['targets']}" if h and 'home' in h and 'targets' in h['home'] else None)(
            json.loads((HERE / "out" / p["id"] / "shots" / "health.json").read_text()) if (HERE / "out" / p["id"] / "shots" / "health.json").exists() else None),
    })

if "--json" in sys.argv:
    print(json.dumps(rows, indent=1))
else:
    keys = list(rows[0])
    print("| " + " | ".join(keys) + " |")
    print("|" + "---|" * len(keys))
    for r in rows:
        print("| " + " | ".join(str(r[k]) for k in keys) + " |")
