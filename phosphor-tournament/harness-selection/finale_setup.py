"""Set up the finale (round 21): bring the championship field into one folder, write its arguments,
a screen.json with no screen (the field goes straight to the eight lenses) and final-K.json."""
import json, sys
from pathlib import Path
import breed, stages
H = Path(__file__).parent
FIELD = [
 ("r20-mut-2", "Lit Index, Ledger Rail", "Lit Index"),
 ("r20-mut-3", "Grid Console Keyed", "Grid Console"),
 ("r20-mut-1", "Desk Terminal, Even Dock", "Desk Terminal"),
 ("r19-mut-2", "Track Diagram Rail Keys", "Track Diagram"),
 ("r18-mut-7", "Blueprint, Lit Scale", "Blueprint"),
 ("r18-wild-1", "Green Desk", "Green Desk (wild)"),
 ("r17-wild-1", "Patch Bay", "Patch Bay (wild)"),
 ("r13-idea-1", "Desk Terminal, Joined", "the bar"),
]
dst = H / "rounds" / "r21"
for pid, _, _ in FIELD:
    breed.bring(pid, dst)
a = json.loads((H / "rounds/r20/args.json").read_text())
a.update(round="r21", roundNo=21, mode="selection", panel="final", mutants=[], wild=[], merges=[], wildMutants=[], seeds=[])
a["carried"] = [{"id": p, "name": n, "summary": f"Hall of fame: {f}."} for p, n, f in FIELD]
(dst / "args.json").write_text(json.dumps(a, indent=1))
st = dst / "stage"; st.mkdir(exist_ok=True)
(st / "designs.json").write_text("[]")
rows = [{"id": p, "name": n, "mean": 0, "plainMean": 0, "top4": 0, "promise": 0, "byLens": {}, "origin": "carried",
         "beatToday": True, "n": 0} for p, n, _ in FIELD]
ids = sorted(p for p, _, _ in FIELD)
(st / "screen.json").write_text(json.dumps({"judges": [], "ranking": rows, "todayMean": None,
                                            "finalists": ids, "forPromise": []}))
for k, lenses in enumerate(stages.LENS_GROUPS, 1):
    f = st / f"final-{k}.json"
    f.write_text(json.dumps({**stages.common(a), "stage": "final", "lenses": lenses, "ids": ids, "nField": len(FIELD)}))
    print(f)
