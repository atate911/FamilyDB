"""Hand an interrupted single-workflow round (round.js) over to the stages: read its journal and
write rounds/rN/stage/resume.json (what each entrant finished) and stage/plan.json.

Usage: python3 takeover.py rN JOURNAL.jsonl
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
rnd, journal = sys.argv[1], sys.argv[2]
a = json.loads((HERE / "rounds" / rnd / "args.json").read_text())
label, result = {}, {}
for line in open(journal):
    e = json.loads(line)
    if e.get("type") == "started":
        label[e["agentId"]] = e["label"]
    elif e.get("type") == "result" and e.get("result") is not None:
        result[label.get(e["agentId"], e["agentId"])] = e["result"]
stage = HERE / "rounds" / rnd / "stage"
stage.mkdir(exist_ok=True)
r = a["round"]
if f"plan:{r}" in result:
    (stage / "plan.json").write_text(json.dumps(result[f"plan:{r}"], indent=1))
second = {f"{r}-rand-{i}" for i in range(1, len(a["seeds"]) + 1)} | \
         {f"{r}-mut-{i}" for i, m in enumerate(a["mutants"], 1) if m.get("kind") == "crossover"}
ids = sorted(second | {f"{r}-mut-{i}" for i in range(1, len(a["mutants"]) + 1)} |
             {f"{r}-idea-{i}" for i in range(1, a["nInformed"] + 1)})
resume = {}
for pid in ids:
    draft, crit, rev = result.get(f"design:{pid}"), result.get(f"crit:{pid}"), result.get(f"revise:{pid}")
    if draft is None:
        continue
    draft = {k: v for k, v in draft.items() if k != "tokens"}
    if pid not in second:
        resume[pid] = {"final": draft}
    elif rev is not None:
        resume[pid] = {"final": {**{k: v for k, v in rev.items() if k != "tokens"}, "id": pid, "crit": crit["notes"],
                                 "firstDraft": {"name": draft["name"], "concept": draft["concept"]}}}
    elif crit is not None:
        resume[pid] = {"draft": draft, "crit": crit}
    else:
        resume[pid] = {"draft": draft}
(stage / "resume.json").write_text(json.dumps(resume, indent=1))
for pid, v in resume.items():
    print(pid, "+".join(v))
print("plan" if f"plan:{r}" in result else "NO PLAN", "| still to do:", [p for p in ids if "final" not in resume.get(p, {})])
