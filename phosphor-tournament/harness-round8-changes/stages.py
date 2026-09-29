"""Run a round as several stage workflows side by side (stage.js), so every core is used.

Each workflow runs at most two agents at once, so a round is split: design stages (two chains of
random entrants or mutants each, and one stage with the planner and the informed entrants), then
judge stages (two lenses each), then one finish stage (curate and learn together). Between them,
this script does the plain work on every core: renders, contact sheets, the tally.

  python3 stages.py split rN [RESUME.json]   write rounds/rN/stage/design-K.json, one per workflow
  python3 stages.py prepare rN OUT...        merge the design outputs, render what is missing or
                                             stale (in parallel), draw the sheets, write the table
                                             and candidates, and rounds/rN/stage/judge-K.json
  python3 stages.py tally rN OUT...          merge the judge outputs, rank, write finish.json
  python3 stages.py assemble rN OUT          write rounds/rN/stage/output.json, which
                                             `advance.py close` reads like a whole round's output

OUT is a workflow's output file (the path its completion notice gives).
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
SHOTS = ["home", "ideas", "lost", "login", "chat", "status", "home-phone", "plans", "todo", "settings",
         "form", "general", "controls-field"]
LENS_GROUPS = [["feedback", "soul"], ["style", "system"], ["interaction", "type"], ["skeptic"]]
# The fields a later stage needs from a finished design; its tokens stay in its palette file.
KEEP = ["id", "name", "tagline", "concept", "companions", "decisions", "floorsFailed", "measures",
        "strengths", "weaknesses", "revisions", "crit", "firstDraft", "secondDraft"]


def result_of(out_file):
    raw = Path(out_file).read_text()
    return json.loads(raw[raw.find("{"):])["result"]


def rdir(rnd):
    return HERE / "rounds" / rnd


def common(a):
    return {"round": a["round"], "roundNo": a["roundNo"], "mode": a["mode"],
            "carried": [{"id": c["id"], "name": c["name"]} for c in a["carried"]],
            "mutants": a["mutants"], "nRandom": len(a["seeds"]), "nInformed": a["nInformed"]}


def slim(d):
    return {k: d[k] for k in KEEP if k in d}


def split(rnd, resume_file=None):
    a = json.loads((rdir(rnd) / "args.json").read_text())
    resume = json.loads(Path(resume_file).read_text()) if resume_file else {}
    r = a["round"]
    # A chain is one entrant's agents in a row: design, then crit and revision where it has them.
    chains = []
    for i, s in enumerate(a["seeds"], 1):
        chains.append((3, "seed", {**s, "slot": i}, f"{r}-rand-{i}"))
    for i, m in enumerate(a["mutants"], 1):
        chains.append((3 if m.get("kind") == "crossover" else 1, "mut", i, f"{r}-mut-{i}"))
    chains = [c for c in chains if not (resume.get(c[3]) or {}).get("final")]
    chains.sort(key=lambda c: -c[0])
    stage_dir = rdir(rnd) / "stage"
    stage_dir.mkdir(exist_ok=True)
    for old in stage_dir.glob("design-*.json"):
        old.unlink()
    files = []

    def by_file(pid, v):
        f = stage_dir / f"resume-{pid}.json"
        f.write_text(json.dumps({"draft": v.get("draft"), "crit": v.get("crit")}, indent=1))
        return {"file": str(f), "critInFile": bool(v.get("crit")), "name": v["draft"]["name"]}
    # Two chains to a workflow, the longest first, so every chain starts at once.
    groups = [chains[k:k + 2] for k in range(0, len(chains), 2)]
    informed_done = all((resume.get(f"{r}-idea-{i}") or {}).get("final") for i in range(1, a["nInformed"] + 1))
    for k, g in enumerate(groups, 1):
        ids = [c[3] for c in g]
        args = {**common(a), "stage": "design",
                "seeds": [c[2] for c in g if c[1] == "seed"],
                "mutantSlots": [c[2] for c in g if c[1] == "mut"],
                "plan": False,
                "resume": {i: by_file(i, resume[i]) for i in ids if i in resume}}
        files.append(stage_dir / f"design-{k}.json")
        files[-1].write_text(json.dumps(args))
    if a["nInformed"] and not informed_done:
        args = {**common(a), "stage": "design", "seeds": [], "mutantSlots": [], "plan": True,
                "history": a["history"],
                "resume": {i: v for i, v in resume.items() if "-idea-" in i}}
        files.append(stage_dir / f"design-{len(files) + 1}.json")
        files[-1].write_text(json.dumps(args))
    for f in files:
        print(f)


def needs_render(d, pid):
    shots = d / "out" / pid / "shots"
    if any(not (shots / f"{s}.png").exists() for s in SHOTS):
        return True
    oldest = min((p.stat().st_mtime for p in shots.glob("*.png")), default=0)
    sources = [d / "palettes" / f"{pid}.json", *(d / "variants" / pid).rglob("*")]
    return any(p.is_file() and p.stat().st_mtime > oldest for p in sources)


def prepare(rnd, *outs):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    designs, plan = {}, None
    # Work finished by an earlier run of this round (takeover.py), and its plan.
    resume_file = stage_dir / "resume.json"
    resumed = json.loads(resume_file.read_text()) if resume_file.exists() else {}
    for pid, v in resumed.items():
        if v.get("final"):
            designs[pid] = slim(v["final"])
    if resumed and (stage_dir / "plan.json").exists():
        plan = json.loads((stage_dir / "plan.json").read_text())
    for o in outs:
        res = result_of(o)
        for x in res.get("designs", []):
            designs[x["id"]] = slim(x)
        if res.get("plan"):
            plan = res["plan"]
    for pid, v in resumed.items():  # a crit passed by file comes back without its notes
        if pid in designs and not designs[pid].get("crit") and v.get("crit"):
            designs[pid]["crit"] = v["crit"]["notes"]
    order = [f"{a['round']}-rand-{i}" for i in range(1, len(a["seeds"]) + 1)] + \
            [f"{a['round']}-mut-{i}" for i in range(1, len(a["mutants"]) + 1)] + \
            [f"{a['round']}-idea-{i}" for i in range(1, a["nInformed"] + 1)]
    missing = [i for i in order if i not in designs]
    if missing:
        print("NO DESIGN RECORD FOR", ", ".join(missing), "(judged from its files if it has them)")
    ds = [designs[i] for i in order if i in designs]
    (stage_dir / "designs.json").write_text(json.dumps(ds, indent=1))
    (stage_dir / "plan.json").write_text(json.dumps(plan, indent=1))

    ids = sorted(p.stem for p in (d / "palettes").glob("*.json") if p.stem != "00-current")
    todo = [pid for pid in ids if needs_render(d, pid)]
    print("rendering", todo or "nothing")

    def render(pid):
        run = subprocess.run(["./check.sh", f"palettes/{pid}.json"], cwd=d, capture_output=True, text=True)
        return pid, (run.stdout.strip().splitlines() or [run.stderr.strip()[-200:]])[-1]

    if os.environ.get("STAGES_DRY"):  # a dry run of the plumbing: no renders
        table = "| (dry run) |\n"
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for pid, last in pool.map(render, todo):
                print("RENDERED", pid, last)
        subprocess.run([str(d / "venv/bin/python"), "contact.py"], cwd=d, check=True, capture_output=True)
        table = subprocess.run([str(d / "venv/bin/python"), "summary.py"], cwd=d, check=True,
                               capture_output=True, text=True).stdout
    (stage_dir / "table.md").write_text(table)

    notes = [f"### {c['id']} {c['name']} (carried)\n{c['summary']}" for c in a["carried"]]
    notes += [f"### {x['id']} {x['name']}\n{x['tagline']}\nConcept: {x['concept']}\nCompanions: {x['companions']}\n"
              f"Designer's own weaknesses: {' | '.join(x['weaknesses'])}" for x in ds]
    (stage_dir / "candidates.md").write_text("\n\n".join(notes) + "\n")

    for old in stage_dir.glob("judge-*.json"):
        old.unlink()
    for k, lenses in enumerate(LENS_GROUPS, 1):
        f = stage_dir / f"judge-{k}.json"
        f.write_text(json.dumps({**common(a), "stage": "judge", "lenses": lenses}))
        print(f)


def tally(rnd, *outs):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    r = a["round"]
    ds = json.loads((stage_dir / "designs.json").read_text())
    judges = {}
    for o in outs:
        for j in result_of(o).get("judges", []):
            judges[j["lens"]] = j
    judges = list(judges.values())
    names = {c["id"]: c["name"] for c in a["carried"]} | {x["id"]: x["name"] for x in ds}

    def origin(pid):
        if pid.startswith(f"{r}-rand"):
            return "random"
        if pid.startswith(f"{r}-mut"):
            m = a["mutants"][int(pid.split("-")[-1]) - 1]
            return "crossover" if m.get("kind") == "crossover" else "mutant"
        return "informed" if pid.startswith(f"{r}-idea") else "carried"

    t = {pid: {"id": pid, "name": n, "total": 0, "n": 0, "top4": 0, "byLens": {}, "origin": origin(pid)}
         for pid, n in names.items()}
    today = [s["score"] for j in judges for s in j["scores"] if s["id"] == "00-current"]
    today_mean = round(sum(today) / len(today), 2) if today else None
    for j in judges:
        for s in j["scores"]:
            if s["id"] in t:
                t[s["id"]]["total"] += s["score"]
                t[s["id"]]["n"] += 1
                t[s["id"]]["byLens"][j["lens"]] = s["score"]
        for pid in j["top4"]:
            if pid in t:
                t[pid]["top4"] += 1
    ranking = [{**x, "mean": round(x["total"] / x["n"], 2) if x["n"] else 0} for x in t.values()]
    ranking.sort(key=lambda x: (-x["mean"], -x["top4"], -x["byLens"].get("skeptic", 0)))
    margin = round(ranking[0]["mean"] - today_mean, 2) if today_mean is not None else None
    thin = [f"{x['id']} ({x['n']})" for x in ranking if x["n"] < len(judges)]
    (stage_dir / "judges.json").write_text(json.dumps(
        [{"lens": j["lens"], "notes": j["notes"], "top4": j["top4"], "scores": j["scores"], "fixes": j["fixes"]}
         for j in judges]))
    (stage_dir / "ranking.json").write_text(json.dumps(
        {"ranking": ranking, "todayMean": today_mean, "margin": margin, "judges": judges}))
    (stage_dir / "finish.json").write_text(json.dumps({
        **common(a), "stage": "finish",
        "ranking": [{"id": x["id"], "name": x["name"], "origin": x["origin"], "mean": x["mean"], "top4": x["top4"]}
                    for x in ranking],
        "newPalettes": [f"{x['id']} ({x['name']})" for x in ds]}))
    print(f"judges: {', '.join(j['lens'] for j in judges)} ({len(judges)} of 7)")
    if thin:
        print("scored by fewer judges:", ", ".join(thin))
    print(f"today {today_mean}, best {ranking[0]['mean']} (margin {margin})")
    for x in ranking:
        print(f"  {x['id']:12} {x['name']:24} {x['mean']:5} top4 {x['top4']} {x['origin']}")
    print(stage_dir / "finish.json")


def assemble(rnd, out):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    fin = result_of(out)
    rk = json.loads((stage_dir / "ranking.json").read_text())
    result = {"round": a["round"], "mode": a["mode"], "ranking": rk["ranking"],
              "top4": [x["id"] for x in rk["ranking"][:4]], "todayMean": rk["todayMean"], "margin": rk["margin"],
              "judges": rk["judges"], "designs": json.loads((stage_dir / "designs.json").read_text()),
              "plan": json.loads((stage_dir / "plan.json").read_text()),
              "table": (stage_dir / "table.md").read_text(),
              "curated": fin.get("curated"), "lessons": fin.get("lessons")}
    (stage_dir / "output.json").write_text(json.dumps({"result": result}))
    print(stage_dir / "output.json")


if __name__ == "__main__":
    {"split": split, "prepare": prepare, "tally": tally, "assemble": assemble}[sys.argv[1]](*sys.argv[2:])
