"""THE FAMILY LIST for the library (fonts_full.py builds the files; this API fetcher is kept only as
the fallback it was). A library of open-licence faces a palette may use, served the way static/fonts would serve
them (the page's policy lets fonts come from the site itself, so any face shipped there works).

Downloads the Latin subset of each family from Google Fonts into fonts/extra/ and writes
fonts/extra.css (the @font-face rules, pointing at fonts/extra/<file>, relative to the page's
stylesheet). theme.py adds the rules for the families a palette's css names.

Usage: python3 fonts.py
"""

import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "fonts" / "extra"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

FAMILIES = [
    # period and terminal faces
    ("IBM Plex Mono", "ital,wght@0,400;0,500;0,600;1,400"),
    ("IBM Plex Sans", "wght@300;400;500;600;700"),
    ("JetBrains Mono", "wght@100..800"),
    ("Recursive", "slnt,wght,CASL,CRSV,MONO@-15..0,300..1000,0..1,0..1,0..1"),
    ("Martian Mono", "wdth,wght@75..112.5,100..800"),
    ("Space Mono", "wght@400;700"),
    ("Share Tech Mono", ""),
    ("Chivo Mono", "wght@100..900"),
    ("Silkscreen", "wght@400;700"),
    # friendly and readable sans
    ("Atkinson Hyperlegible", "wght@400;700"),
    ("Nunito", "wght@200..1000"),
    ("Manrope", "wght@200..800"),
    ("Figtree", "wght@300..900"),
    ("Outfit", "wght@100..900"),
    ("Lexend", "wght@100..900"),
    ("Instrument Sans", "wdth,wght@75..100,400..700"),
    # warm serifs
    ("Fraunces", "opsz,wght,SOFT,WONK@9..144,100..900,0..100,0..1"),
    ("Newsreader", "opsz,wght@6..72,200..800"),
    # added for round 10's type dice: grotesques, condensed and wide faces, text serifs, more
    # monos, and CRT faces whose BLED and SCAN axes draw phosphor bleed and scanlines
    ("Inter", "opsz,wght@14..32,100..900"),
    ("Geist", "wght@100..900"),
    ("Space Grotesk", "wght@300..700"),
    ("Hanken Grotesk", "wght@100..900"),
    ("Red Hat Text", "wght@300..700"),
    ("Archivo", "wdth,wght@62..125,100..900"),
    ("Bricolage Grotesque", "opsz,wdth,wght@12..96,75..100,200..800"),
    ("IBM Plex Sans Condensed", "wght@300;400;500;600;700"),
    ("Barlow Condensed", "wght@300;400;500;600;700"),
    ("Source Serif 4", "opsz,wght@8..60,200..900"),
    ("Literata", "opsz,wght@7..72,200..900"),
    ("IBM Plex Serif", "wght@300;400;500;600;700"),
    ("Geist Mono", "wght@100..900"),
    ("Red Hat Mono", "wght@300..700"),
    ("Spline Sans Mono", "wght@300..700"),
    ("Azeret Mono", "wght@100..900"),
    ("Fira Code", "wght@300..700"),
    ("Victor Mono", "wght@100..700"),
    ("Workbench", "BLED,SCAN@0..100,-53..100"),
    ("Sixtyfour", "BLED,SCAN@0..100,-53..100"),
    ("Doto", "wght,ROND@100..900,0..100"),
    ("Pixelify Sans", "wght@400..700"),
]


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode()


def main(add_only=False):
    """With --add, fetch only the families not in the library yet and keep every existing file
    untouched, so renders running at the time never read a half-written font."""
    OUT.mkdir(parents=True, exist_ok=True)
    rules, index = [], {}
    if add_only:
        index = json.loads((HERE / "fonts" / "index.json").read_text())
        rules = [(HERE / "fonts" / "extra.css").read_text().rstrip("\n")]
    for family, axes in FAMILIES:
        if family in index:
            continue
        q = family.replace(" ", "+") + (f":{axes}" if axes else "")
        try:
            css = fetch(f"https://fonts.googleapis.com/css2?family={q}&display=swap")
        except Exception as exc:  # noqa: BLE001
            print("skip", family, exc)
            continue
        blocks = re.findall(r"/\* (\S+) \*/\s*(@font-face \{.*?\})", css, re.S)
        slug = family.lower().replace(" ", "-")
        n = 0
        for subset, block in blocks:
            if subset != "latin":
                continue
            url = re.search(r"url\((https://[^)]+)\)", block).group(1)
            n += 1
            name = f"{slug}-{n}.woff2"
            tmp = OUT / (name + ".part")
            tmp.write_bytes(fetch(url, binary=True))
            tmp.replace(OUT / name)
            rules.append(block.replace(url, f"fonts/extra/{name}"))
        index[family] = n
        print(f"{family}: {n} file(s)")
    for name, text in (("extra.css", "\n".join(rules) + "\n"), ("index.json", json.dumps(index, indent=1))):
        tmp = HERE / "fonts" / (name + ".part")
        tmp.write_text(text)
        tmp.replace(HERE / "fonts" / name)
    size = sum(f.stat().st_size for f in OUT.glob("*.woff2"))
    print(f"{len(index)} families, {size // 1024} kB")


if __name__ == "__main__":
    import sys
    main(add_only="--add" in sys.argv)
