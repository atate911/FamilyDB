"""Open the next generation of the natural-selection tournament.

  python3 breed.py open r14 r15

From the finished round (its ranking, stage/parts.json from selection.py, lineages.json):
1. Each LINEAGE (a head design and its history) takes what survived. A child that won its slots as a
   whole becomes the head; otherwise the changes that won are MERGED into the head (a merge task,
   run before the children); a lineage with nothing kept stays as it was and notes what was culled.
2. The weakest lineages, two rounds running, are retired and replaced by an ALL-STAR: the round's best
   head with the parts bin's best elements merged in, in the slots where it is weakest.
3. Every head spawns CHILDREN: three changes each, one per slot, from three sources: the parts bin
   (informed), a push of what just survived (exploit), a blind tweak from tweaks.json (explore).
4. One wild newcomer from the dice; it joins the lineages next round if it places in the top half.
"""
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SL = json.loads((HERE / "slots.json").read_text())
SLOTS = [s["key"] for s in SL["slots"]]
TWEAKS = json.loads((HERE / "tweaks.json").read_text())
WEIGHT = {s["key"]: s["weight"] for s in SL["slots"]}
TH = SL["thresholds"]
LINEAGES = HERE / "lineages.json"
MAX_LINEAGES, RETIRE_AFTER, CHILDREN, CHANGES = 6, 2, 2, 3


def find(pid):
    """The round directory that holds a design's files (the newest that has it)."""
    for d in sorted((HERE / "rounds").iterdir(), key=lambda p: (len(p.name), p.name), reverse=True):
        if (d / "palettes" / f"{pid}.json").exists():
            return d
    raise SystemExit(f"no files for {pid}")


def bring(pid, dst, shots=True):
    """Put a design's palette, markup, cards (and shots) in a round's folder, if it is not there."""
    src = find(pid)
    dst.mkdir(exist_ok=True)
    for sub in ("palettes", "variants", "out", "cards"):
        (dst / sub).mkdir(exist_ok=True)
    f = dst / "palettes" / f"{pid}.json"
    if not f.exists():
        shutil.copy2(src / "palettes" / f"{pid}.json", f)
    if (src / "variants" / pid).exists() and not (dst / "variants" / pid).exists():
        shutil.copytree(src / "variants" / pid, dst / "variants" / pid)
    if shots and (src / "out" / pid).exists() and not (dst / "out" / pid).exists():
        shutil.copytree(src / "out" / pid, dst / "out" / pid)
    for c in (src / "cards").glob(f"{pid}-*.png"):
        if not (dst / "cards" / c.name).exists():
            shutil.copy2(c, dst / "cards" / c.name)


def read_lineages(prev):
    if LINEAGES.exists():
        return json.loads(LINEAGES.read_text())
    hosts = []
    for m in prev["mutants"]:
        if m.get("kind") == "step" and m["parent"] not in [h["head"] for h in hosts]:
            hosts.append({"key": m["parent"], "head": m["parent"], "name": m["parentName"], "stale": 0, "culled": [], "kept": []})
    return {"gen": prev["roundNo"], "lineages": hosts, "bars": ["r13-idea-1"]}


def slot_pick(rng, L, exclude):
    """A slot for a blind tweak: by how much it matters to the family, less for a slot this lineage has
    already won more than once (it has found what it wants there; look elsewhere)."""
    pool = [s for s in SLOTS if s not in exclude]
    w = [WEIGHT[s] * TH["saturate"] ** L.get("won", {}).get(s, 0) for s in pool]
    return rng.choices(pool, weights=w)[0]


def open_round(prev_name, name):
    prev_dir, dst = HERE / "rounds" / prev_name, HERE / "rounds" / name
    prev = json.loads((prev_dir / "args.json").read_text())
    st = prev_dir / "stage"
    P = json.loads((st / "parts.json").read_text())
    screen = json.loads((st / "screen.json").read_text())
    mean = {x["id"]: x["mean"] for x in screen["ranking"]}
    nameof = {x["id"]: x["name"] for x in screen["ranking"]}
    state = read_lineages(prev)
    rng = random.Random(name)
    no = int(name[1:])
    verdicts = {v["id"]: v for v in P["verdicts"]}
    children_of = {}
    for v in P["verdicts"]:
        children_of.setdefault(v["parent"], []).append(v)

    # 1. what each lineage takes
    merges, heads = [], []
    for L in state["lineages"]:
        kids = children_of.get(L["head"], [])
        kept = [(v, s) for v in kids for s in v["slots"] if s["slot"] in v["kept"]]
        L["culled"] += [s["text"] for v in kids for s in v["slots"] if s["slot"] not in v["kept"]]
        L.setdefault("won", {})
        if kept:
            picked, used = [], set()
            for v, s in sorted(kept, key=lambda x: -(x[0]["delta"] if x[0]["delta"] is not None else 0)):
                if s["slot"] not in used:  # one change per slot: the better child's wins
                    used.add(s["slot"])
                    picked.append({"slot": s["slot"], "child": v["id"], "childName": nameof.get(v["id"], v["id"]), "text": s["text"]})
            sources = {x["child"] for x in picked}
            only = next(iter(sources)) if len(sources) == 1 else None
            if only and not any(x["verdict"] == "lost" for x in verdicts[only]["slots"]):
                # one child contributed and none of its changes lost (the rest only went unseen): it is the next head, free
                L["kept"] = [{"slot": x["slot"], "text": x["text"]} for x in picked]
                L["head"], L["name"] = only, nameof.get(only, only)
            else:
                mid = f"{name}-head-{len(merges) + 1}"
                merges.append({"id": mid, "base": L["head"], "baseName": L["name"], "lifts": picked, "lineage": L["key"]})
                L["kept"] = [{"slot": x["slot"], "text": x["text"]} for x in picked]
                L["head"], L["name"] = mid, f"{L['name']}, merged"
        else:
            whole = [v for v in kids if v["survives"] and not any(x["verdict"] == "lost" for x in v["slots"])]
            if whole:  # nothing won a slot, but a child's whole page beat its parent's with nothing lost: it becomes the head
                best = max(whole, key=lambda v: v["delta"])
                L["kept"] = [{"slot": x["slot"], "text": x["text"]} for x in best["slots"]]
                L["head"], L["name"] = best["id"], nameof.get(best["id"], best["id"])
            else:
                L["kept"] = []
        for k in L["kept"]:
            L["won"][k["slot"]] = L["won"].get(k["slot"], 0) + 1
        heads.append(L)

    wanted_allstar = []
    # 2. the weakest lineage, two rounds running, is replaced by an all-star
    ranked = sorted(state["lineages"], key=lambda L: -mean.get(L["head"], mean.get(L["key"], 0)))
    for L in ranked[-2:]:
        L["stale"] += 1
    for L in ranked[:-2]:
        L["stale"] = 0
    retire = [L for L in ranked[-2:] if L["stale"] >= RETIRE_AFTER]
    leader = ranked[0]
    if retire and len(ranked) >= 4:
        L = retire[-1]
        bin_ = json.loads((HERE / "parts-bin.json").read_text())
        lifts = []
        for slot in SLOTS:
            top = next((r for r in bin_.get(slot, []) if r["id"] not in (leader["head"], "00-current")), None)
            if top and top["share"] >= TH["bin_share"]:
                lifts.append((top["share"] * WEIGHT[slot], {"slot": slot, "child": top["id"], "childName": top["name"], "text": "; ".join(top.get("what", [])[:2]) or f"{slot} element of {top['name']}"}))
        lifts = [x for _, x in sorted(lifts, key=lambda t: -t[0])[:3]]
        for l in lifts:
            wanted_allstar.append({"slot": l["slot"], "id": l["child"], "name": l["childName"], "what": [l["text"]]})
        if lifts:
            mid = f"{name}-head-{len(merges) + 1}"
            merges.append({"id": mid, "base": leader["head"], "baseName": leader["name"], "lifts": lifts, "lineage": "allstar"})
            L.update({"key": f"allstar-{no}", "head": mid, "name": f"{leader['name']}, all-star", "stale": 0, "culled": [], "kept": []})

    # 3. children
    bin_ = json.loads((HERE / "parts-bin.json").read_text())
    mutants, wanted = [], {}
    for L in state["lineages"]:
        head = L["head"]
        for n in range(CHILDREN):
            changes, used = [], set()
            informed = [r | {"slot": s} for s in SLOTS for r in bin_.get(s, [])[:2]
                        if r["id"] not in (head, "00-current") and r["share"] >= TH["bin_share"] and r.get("what")]
            while informed and len(changes) < 1:   # one informed change, drawn by share and by the slot's weight
                r = rng.choices(informed, weights=[x["share"] * WEIGHT[x["slot"]] for x in informed])[0]
                informed.remove(r)
                if r["slot"] in used:
                    continue
                used.add(r["slot"])
                spec = f"{{D}}/parts/{r['slot']}--{r['id']}.md"
                changes.append({"slot": r["slot"], "text": "; ".join(r["what"][:2]), "donor": r["id"], "donorName": r["name"], "spec": spec})
                wanted.setdefault((r["slot"], r["id"]), {"slot": r["slot"], "id": r["id"], "name": r["name"], "what": r["what"]})
            if n == 0 and L["kept"]:  # exploit: push what has just survived one step further
                k = rng.choice(L["kept"])
                if k["slot"] not in used:
                    used.add(k["slot"])
                    changes.append({"slot": k["slot"], "text": f"push this one step further, as the same idea made more of: {k['text']}"})
            while len(changes) < CHANGES:
                slot = slot_pick(rng, L, used)
                used.add(slot)
                pool = [t for t in TWEAKS[slot] if t not in L["culled"]] or TWEAKS[slot]
                changes.append({"slot": slot, "text": rng.choice(pool)})
            mutants.append({"kind": "step", "parent": head, "parentName": L["name"], "parentMean": mean.get(head, mean.get(L["key"], 0)), "changes": changes})

    # 4. the folder, with every design it needs
    if dst.exists():
        raise SystemExit(f"{dst} exists already")
    subprocess.run(["python3", str(HERE / "setup_round.py"), name, f"rounds/{prev_name}"], check=True, cwd=HERE)
    (dst / "cards").mkdir(exist_ok=True); (dst / "variants").mkdir(exist_ok=True)
    for pid in ["00-current"]:
        bring(pid, dst)
    bars = state.setdefault("bars", [])
    carried_ids = [L["head"] for L in state["lineages"] if not L["head"].startswith(f"{name}-head")] + bars
    donor_ids = {c["donor"] for m in mutants for c in m["changes"] if c.get("donor")}
    for pid in carried_ids:
        bring(pid, dst)
    for pid in donor_ids:
        bring(pid, dst)
    for m in merges:
        bring(m["base"], dst)
        for l in m["lifts"]:
            bring(l["child"], dst)
    # the lineages' heads, merged ones included, are carried; the merged are built before the children
    summary = lambda L: f"Lineage {L['key']}: head of the line, entered as the bar its children are measured against." + (f" Last round it kept: {', '.join(k['slot'] for k in L['kept'])}." if L["kept"] else "")
    carried = [{"id": L["head"], "name": L["name"], "summary": summary(L)} for L in state["lineages"]]
    for b in bars:  # a reference design: in the field as a bar, with no children
        carried.append({"id": b, "name": json.loads((HERE / "rounds" / name / "palettes" / f"{b}.json").read_text())["name"],
                        "summary": "A reference from the early rounds, entered unchanged as a bar for the whole field; it has no children."})
    sys.path.insert(0, str(HERE))
    import seeds as dice
    past = {}
    for f in (HERE / "rounds").glob("*/args.json"):
        for w in json.loads(f.read_text()).get("wild", []):
            past[w["language"]] = past.get(w["language"], 0) + 1
    wild = [{**w, "slot": i} for i, w in enumerate(dice.wild_seeds(1, past), 1)]
    args = {"round": name, "roundNo": no, "mode": "selection", "carried": carried, "wildCarried": [], "seeds": [],
            "mutants": mutants, "wild": wild, "wildMutants": [], "nInformed": 0, "history": [], "panel": "screen",
            "merges": merges}
    (dst / "args.json").write_text(json.dumps(args, indent=1))
    # Specs are written only for the parts this round will use, and never twice: earlier rounds' are carried over.
    (dst / "parts").mkdir(exist_ok=True)
    for old in sorted((HERE / "rounds").glob("r*/parts/*.md")):
        if not (dst / "parts" / old.name).exists():
            shutil.copy2(old, dst / "parts" / old.name)
    need = [w for w in list(wanted.values()) + wanted_allstar if not (dst / "parts" / f"{w['slot']}--{w['id']}.md").exists()
            and not w["id"].startswith(f"{name}-head")]
    (dst / "stage").mkdir(exist_ok=True)
    (dst / "stage" / "extract.json").write_text(json.dumps({"round": name, "roundNo": no, "stage": "extract", "parts": need,
                                                          "slotsJson": json.dumps({"slots": [{"key": x["key"], "what": x["what"]} for x in SL["slots"]]}, separators=(",", ":"))}))
    state["gen"] = no
    LINEAGES.write_text(json.dumps(state, indent=1))
    (dst / "lineages.json").write_text(json.dumps(state, indent=1))
    print(f"round {name}: {len(state['lineages'])} lineages, {len(merges)} merges, {len(mutants)} children, {len(wild)} wild, {len(need)} specs to write")
    for L in state["lineages"]:
        print(f"  {L['key']:14} head {L['head']} ({L['name']}) kept {[k['slot'] for k in L['kept']]} stale {L['stale']}")
    for m in merges:
        print(f"  merge {m['id']}: {m['base']} + {[(l['slot'], l['child']) for l in m['lifts']]}")


if __name__ == "__main__":
    {"open": open_round}[sys.argv[1]](*sys.argv[2:])
