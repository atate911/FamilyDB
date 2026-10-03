"""Copies the side tour's and crossing rounds' designs, results and notes into the repo, in stages."""
import json, shutil, sys
from pathlib import Path
H = Path("/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness")
X, TOUR = H / "cross", H / "tour"
D = Path("/home/user/FamilyDB/phosphor-tournament/tour-and-cross")
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "out", "venv", "*.png", "node_modules")
TOP8 = ["x14b-manual-cross", "x14b-waypoint-cross", "x14b-trued-cross", "x14b-folio-cross",
        "x14b-desk-cross", "x14b-dessau-cross", "x14b-sill-cross", "x14b-quote-cross"]

def records():
    rec = {}
    for f in list(X.glob("x14*/stage/designs.json")) + list(TOUR.glob("t*/stage/designs.json")):
        for r in json.load(open(f)):
            rec.setdefault(r["id"], r)
    return rec

def copytree(src, dst):
    if src.exists():
        shutil.copytree(src, dst, ignore=SKIP, dirs_exist_ok=True)

def design(i, rec):
    out = D / "cross" / "final" / i
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(X / "x14f" / "palettes" / f"{i}.json", out / "palette.json")
    copytree(X / "x14f" / "variants" / i, out / "variant")
    json.dump(rec[i], open(out / "record.json", "w"), indent=1, ensure_ascii=False)

def round_dir(src, dst):
    """A round's own folder (args, results, stage) and its heats' palettes and variants."""
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("args.json", "results.json", "candidates.md", "table.md"):
        if (src / f).exists():
            shutil.copy(src / f, dst / f)
    copytree(src / "stage", dst / "stage")
    for sub in ("palettes", "variants"):
        copytree(src / sub, dst / sub)

step = sys.argv[1]
rec = records()
if step == "a":
    for i in TOP8:
        design(i, rec)
elif step == "b":
    r = D / "cross" / "results"
    r.mkdir(parents=True, exist_ok=True)
    shutil.copy(X / "x14f" / "results.json", r / "final-results.json")
    for f in ("candidates.md", "table.md"):
        shutil.copy(X / "x14f" / "stage" / f, r / f"final-{f}")
    for k in ("x14a", "x14b"):
        shutil.copy(X / k / "results.json", r / f"{k}-results.json")
    for f in ("lessons.md", "titles.md", "owner_judge.md"):
        shutil.copy(X / f, D / "cross" / f)
    copytree(X / "dossiers", D / "cross" / "dossiers")
    for f in ("lessons.md", "titles.md", "owner_judge.md"):
        shutil.copy(TOUR / f, D / "tour" / f)
    copytree(TOUR / "dossiers", D / "tour" / "dossiers")
elif step == "d":
    for i in json.load(open(X / "x14f" / "results.json"))["ranking"]:
        if i["id"].startswith("x14b") and i["id"] not in TOP8:
            design(i["id"], rec)
    for k in ("x14a", "x14a-a", "x14a-b", "x14b", "x14b-a", "x14b-b"):
        round_dir(X / k, D / "cross" / "rounds" / k)
    round_dir(X / "x14f", D / "cross" / "rounds" / "x14f")
    for k in ("t1", "t1-a", "t1-b", "t2", "t2-a", "t2-b", "t3", "t3-a", "t3-b", "landing"):
        round_dir(TOUR / k, D / "tour" / "rounds" / k)
    copytree(TOUR / "donors", D / "tour" / "donors")
elif step == "e":
    s = D / "cross" / "scripts"
    s.mkdir(parents=True, exist_ok=True)
    for f in ("cross.py", "make_stage.py", "framing.txt", "cross_stage.js"):
        shutil.copy(X / f, s / f)
    for f in ("ledger.md", "ledger-index.md"):
        shutil.copy(X / f, D / "cross" / f)
    for f in X.glob("ledger-for-*.md"):
        shutil.copy(f, D / "cross" / "ledgers" / f.name) if (D / "cross" / "ledgers").mkdir(exist_ok=True) is None else None
    t = D / "tour" / "scripts"
    t.mkdir(parents=True, exist_ok=True)
    for f in ("tour.py", "tour_stage.js"):
        shutil.copy(TOUR / f, t / f)
    for f in ("ledger.md", "ledger-index.md", "ledger.json"):
        shutil.copy(TOUR / f, D / "tour" / f)
    sp = Path("/tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad")
    for f in ("cross_sheets.py", "finals.py", "journey.py", "pack.py"):
        if (sp / f).exists():
            shutil.copy(sp / f, s / f)
print("done", step)
