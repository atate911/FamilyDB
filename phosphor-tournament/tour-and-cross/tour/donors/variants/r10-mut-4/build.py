"""Build palettes/r10-mut-4.json from tokens.json and palette.css (kept beside the variant)."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent
css = (HERE / "palette.css").read_text()
# Squeeze: the source's comments (after the first) stay in the source; whitespace runs collapse.
head, rest = css.split("*/", 1)
css = head + "*/" + re.sub(r"/\*.*?\*/", "", rest, flags=re.S)
css = re.sub(r"\n\s*\n", "\n", css).strip()
css = re.sub(r"[ \t]+", " ", css)
css = re.sub(r"\s*([{};])\s*", r"\1", css)
css = css.replace(";}", "}")
meta = json.loads((HERE / "tokens.json").read_text())
meta["css"] = css
(ROUND / "palettes" / "r10-mut-4.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
print("css", len(css), "chars")
