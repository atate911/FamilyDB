"""Rebuild the font library from the upstream font files, every OpenType feature kept.

The Google Fonts CSS API serves files stripped of their stylistic features (tabular and oldstyle
figures, small caps, slashed zero, stylistic sets) and of glyphs outside a language subset
(arrows, box drawing, blocks). This fetches each family's TTFs from the google/fonts repository,
italics included, subsets them locally with every layout feature kept and those glyph ranges
added, and writes fonts/full/*.woff2 with fonts/extra-full.css and fonts/index-full.json.
`--swap` then makes them the library (fonts/extra.css, fonts/index.json), keeping the old ones
as *-api.* beside them.

Usage: venv/bin/python fonts_full.py [--swap]
"""

import io
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
OUT = HERE / "fonts" / "full"
RAW = "https://raw.githubusercontent.com/google/fonts/main"
# Latin with its extensions, punctuation, currency, and the marks designs draw with: arrows,
# box drawing, block elements and shades, geometric shapes, the check mark.
UNICODES = ("U+0000-024F,U+02B0-02FF,U+0300-036F,U+1E00-1EFF,U+2000-206F,U+20A0-20CF,U+2100-214F,"
            "U+2190-21FF,U+2200-22FF,U+2300-23FF,U+2500-257F,U+2580-259F,U+25A0-25FF,U+2600-26FF,"
            "U+2713-2714,U+FB00-FB06,U+FEFF,U+FFFD")
# The page's own three, so a design can reach their full features and italics too.
EXTRA = ["DM Sans", "DM Mono", "VT323"]


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fonts_full"}), timeout=60) as r:
        return r.read()


def families():
    sys.path.insert(0, str(HERE))
    from fonts import FAMILIES
    return [f for f, _ in FAMILIES] + EXTRA


def manifest(family):
    slug = re.sub(r"[^a-z0-9]", "", family.lower())
    for licence in ("ofl", "apache", "ufl"):
        try:
            meta = fetch(f"{RAW}/{licence}/{slug}/METADATA.pb").decode()
            return licence, slug, re.findall(r'filename: "([^"]+)"', meta)
        except Exception:  # noqa: BLE001
            continue
    return None, slug, []


def build(family):
    licence, slug, files = manifest(family)
    if not files:
        return family, [], "no upstream files"
    rules = []
    for name in files:
        data = fetch(f"{RAW}/{licence}/{slug}/{urllib.parse.quote(name)}")
        font = TTFont(io.BytesIO(data))
        axes = {a.axisTag: (a.minValue, a.maxValue) for a in font["fvar"].axes} if "fvar" in font else {}
        italic = "italic" in name.lower() or bool(font["OS/2"].fsSelection & 1)
        weight = (f"{int(axes['wght'][0])} {int(axes['wght'][1])}" if "wght" in axes
                  else str(font["OS/2"].usWeightClass))
        stretch = f"{axes['wdth'][0]:g}% {axes['wdth'][1]:g}%" if "wdth" in axes else None
        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.name_languages = ["*"]
        opts.notdef_outline = True
        opts.flavor = "woff2"
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=subset.parse_unicodes(UNICODES))
        sub.subset(font)
        out = OUT / (re.sub(r"[^A-Za-z0-9]+", "-", Path(name).stem).strip("-").lower() + ".woff2")
        tmp = out.with_suffix(".part")
        font.flavor = "woff2"
        font.save(tmp)
        tmp.replace(out)
        rules.append("@font-face {\n"
                     f"  font-family: '{family}';\n"
                     f"  font-style: {'italic' if italic else 'normal'};\n"
                     f"  font-weight: {weight};\n"
                     + (f"  font-stretch: {stretch};\n" if stretch else "")
                     + "  font-display: swap;\n"
                     f"  src: url(fonts/full/{out.name}) format('woff2');\n"
                     "}")
    return family, rules, f"{len(files)} file(s)"


def main():
    if "--swap" in sys.argv:
        f = HERE / "fonts"
        for name in ("extra.css", "index.json"):
            (f / name).replace(f / name.replace(".", "-api."))
        (f / "extra-full.css").replace(f / "extra.css")
        (f / "index-full.json").replace(f / "index.json")
        print("the full library is now in use; the API one is kept as extra-api.css and index-api.json")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    rules, index = [], {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for family, rs, note in pool.map(build, families()):
            print(f"{family}: {note}")
            if rs:
                rules += rs
                index[family] = len(rs)
    (HERE / "fonts" / "extra-full.css").write_text("\n".join(rules) + "\n")
    (HERE / "fonts" / "index-full.json").write_text(json.dumps(index, indent=1))
    size = sum(p.stat().st_size for p in OUT.glob("*.woff2"))
    print(f"{len(index)} families, {size // 1024} kB")


if __name__ == "__main__":
    main()
