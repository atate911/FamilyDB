"""r20-mut-1: palettes/r20-mut-1.json = r19-mut-1's palette css + this folder's r20.css (the three rolled changes)."""
import json, pathlib
here = pathlib.Path(__file__).resolve().parent
rounds = here.parent.parent
src = json.load(open(rounds / "palettes" / "r19-mut-1.json"))
p = json.load(open(rounds / "palettes" / "r20-mut-1.json"))
p["css"] = src["css"] + (here / "r20.css").read_text()
p["id"] = "r20-mut-1"
p["sheet"] = "variants/r20-mut-1/sheet.css"
json.dump(p, open(rounds / "palettes" / "r20-mut-1.json", "w"), indent=1)
