#!/usr/bin/env python3
"""Put the published links into a built gallery.

    python3 relink.py OUT links.json

links.json maps each placeholder to its URL: {"INDEX": "https://...", "ROUND1": "https://...", ...}.
Every index.html under OUT has @INDEX@, @ROUND1@ ... replaced by them.
"""

import json
import sys
from pathlib import Path

import re

out, links = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
left = 0
for f in sorted(out.glob("*/index.html")):
    text = f.read_text(encoding="utf-8")
    for name, url in links.items():
        text = text.replace(f"@{name}@", url)
    f.write_text(text, encoding="utf-8")
    missing = sorted(set(re.findall(r"@(?:INDEX|GENS|ROUND\d+)@", text)))
    left += len(missing)
    print(f.parent.name, "still to link:", missing or "none")
sys.exit(1 if left else 0)
