"""Natural selection at the level of elements.

After a screen (and a final, when there is one), the judges' element votes ("parts": the best design
for each slot they can see) are tallied per slot, each child is compared with its parent slot by slot,
the winning elements go into the parts bin, and the changes that survived are listed per lineage
(heirs.json) for the next generation to build in.

  python3 selection.py settle rN SCREEN_OUT...   a screen-only round: ranking.json, finish.json, then select
  python3 selection.py select rN                 element tallies, verdicts, the bin, heirs, extract.json
"""
import json
import sys
from pathlib import Path

import stages
from stages import rdir, result_of

H = Path(__file__).parent
SL = json.loads((H / "slots.json").read_text())
SLOTS = [s["key"] for s in SL["slots"]]
EXPERTS = {s["key"]: set(s["experts"]) for s in SL["slots"]}
PTS = SL["points"]
WIN_MIN = 1.5          # a change wins its slot with at least this many points more than its parent has
KEEP_DELTA = 0.15      # a child's whole page beats its parent by this much on the screen's mean
BIN = H / "parts-bin.json"
DECAY = 0.5


def parts_tally(judges, names):
    """slot -> rows [{id, name, points, voters, what}], best first. Best 2, runner-up 1; the slot's expert
    lenses count 1.5 times, and a final judge 1.5 times (it looked at fewer, closer designs)."""
    t = {s: {} for s in SLOTS}
    for j in judges:
        lens = j["lens"]
        final = not lens.startswith("screen-") and "order" in j
        lens = lens.removeprefix("screen-")
        for p in j.get("parts", []) or []:
            slot = p.get("slot")
            if slot not in t:
                continue
            for pid, base in ((p.get("best"), PTS["best"]), (p.get("runner"), PTS["runner"])):
                if not pid:
                    continue
                w = base * (PTS["expert"] if lens in EXPERTS[slot] else 1) * (PTS["final"] if final else 1)
                r = t[slot].setdefault(pid, {"id": pid, "name": names.get(pid, pid), "points": 0.0, "voters": [], "what": []})
                r["points"] = round(r["points"] + w, 2)
                r["voters"].append(lens)
                if p.get("what") and p["what"] not in r["what"] and pid == p.get("best"):
                    r["what"].append(p["what"])
    return {s: sorted(rows.values(), key=lambda r: -r["points"]) for s, rows in t.items()}


def pts(parts, slot, pid):
    return next((r["points"] for r in parts.get(slot, []) if r["id"] == pid), 0.0)


def verdicts(a, means, parts):
    """For every child: its overall change against its parent on the screen's mean, and each changed
    slot's element votes against the parent's."""
    out = []
    for i, m in enumerate(a["mutants"], 1):
        if m.get("kind") != "step":
            continue
        cid, pid = f"{a['round']}-mut-{i}", m["parent"]
        delta = round(means.get(cid, 0) - means.get(pid, 0), 2) if cid in means and pid in means else None
        slots = []
        for c in m["changes"]:
            cp, pp = pts(parts, c["slot"], cid), pts(parts, c["slot"], pid)
            v = "won" if cp - pp >= WIN_MIN else "lost" if pp > cp else "tied" if cp or pp else "unseen"
            slots.append({"slot": c["slot"], "child": cp, "parent": pp, "verdict": v, "graft": c.get("donor"), "text": c["text"]})
        kept = [s for s in slots if s["verdict"] == "won" or (s["verdict"] == "tied" and delta is not None and delta >= KEEP_DELTA)]
        out.append({"id": cid, "parent": pid, "parentName": m["parentName"], "delta": delta, "slots": slots,
                    "kept": [s["slot"] for s in kept],
                    "survives": bool(kept) or (delta is not None and delta >= KEEP_DELTA)})
    return out


def update_bin(rnd_no, parts):
    """The parts bin: per slot the best elements seen, this round's votes laid over the earlier ones at half weight."""
    old = json.loads(BIN.read_text()) if BIN.exists() else {}
    new = {}
    for s in SLOTS:
        rows = {}
        for r in old.get(s, []):
            rows[r["id"]] = {**r, "points": round(r["points"] * DECAY, 2), "age": r.get("age", 0) + 1}
        for r in parts.get(s, []):
            if r["points"] <= 0:
                continue
            prev = rows.get(r["id"], {})
            rows[r["id"]] = {"id": r["id"], "name": r["name"], "points": round(r["points"] + prev.get("points", 0), 2),
                             "round": rnd_no, "what": r["what"] or prev.get("what", []), "age": 0}
        new[s] = sorted(rows.values(), key=lambda r: -r["points"])[:4]
    BIN.write_text(json.dumps(new, indent=1))
    return new


def select(rnd):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    st = d / "stage"
    screen = json.loads((st / "screen.json").read_text())
    ds = json.loads((st / "designs.json").read_text())
    names = stages.names_of(a, ds) | {"00-current": "Today's page"}
    rk = st / "ranking.json"
    judges = json.loads(rk.read_text())["judges"] if rk.exists() else screen["judges"]
    parts = parts_tally(judges, names)
    means = {x["id"]: x["mean"] for x in screen["ranking"]}   # the screen's scale, for every design alike
    vd = verdicts(a, means, parts)
    bin_ = update_bin(a["roundNo"], parts)
    heirs = {}
    for v in vd:
        h = heirs.setdefault(v["parent"], {"parent": v["parent"], "parentName": v["parentName"], "kept": [], "culled": []})
        for s in v["slots"]:
            (h["kept"] if s["slot"] in v["kept"] else h["culled"]).append({"slot": s["slot"], "child": v["id"], "verdict": s["verdict"], "text": s["text"], "graft": s["graft"]})
    (st / "parts.json").write_text(json.dumps({"parts": parts, "verdicts": vd, "heirs": heirs, "bin": bin_}, indent=1))
    lines = [f"# Round {a['roundNo']}: elements\n", "## The best element in each slot (points: best 2, runner 1, expert lens x1.5, final x1.5)\n"]
    for s in SLOTS:
        rows = parts[s][:3]
        lines.append(f"- **{s}**: " + ("; ".join(f"{r['id']} ({r['name']}) {r['points']}: {'; '.join(r['what'][:2])}" for r in rows) or "no votes"))
    lines += ["", "## Children against their parents (screen mean delta; per changed slot the element votes, child vs parent)\n"]
    for v in vd:
        lines.append(f"- {v['id']} ({v['parentName']}) delta {v['delta']}: " + ", ".join(f"{s['slot']} {s['verdict']} ({s['child']} v {s['parent']})" for s in v["slots"]) + (" -> survives" if v["survives"] else " -> culled"))
    (st / "parts.md").write_text("\n".join(lines) + "\n")
    top = [{"slot": s, **{k: r[k] for k in ("id", "name", "what")}} for s in SLOTS for r in parts[s][:2] if r["points"] > 0 and r["id"] != "00-current"]
    (st / "extract.json").write_text(json.dumps({"round": a["round"], "roundNo": a["roundNo"], "stage": "extract", "parts": top}))
    print("\n".join(lines))
    print(st / "extract.json")


def settle(rnd, *outs):
    """A screen-only round: the screen's ranking stands as the round's, then select."""
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    st = d / "stage"
    ds = json.loads((st / "designs.json").read_text())
    screen = json.loads((st / "screen.json").read_text())
    ranking = [{**x, "panel": "screen", "screenMean": x["mean"], "screenByLens": x["byLens"]} for x in screen["ranking"]]
    ranking.sort(key=lambda x: (-x["mean"], -x["top4"], -x["promise"]))
    today = screen["todayMean"]
    judges = [{**j, "lens": f"screen-{j['lens']}"} if not j["lens"].startswith("screen-") else j for j in screen["judges"]]
    (st / "ranking.json").write_text(json.dumps(
        {"ranking": ranking, "todayMean": today, "margin": round(ranking[0]["mean"] - today, 2) if today else None,
         "judges": judges, "screenTodayMean": today, "finalists": [], "forPromise": [],
         "lensWeights": {j["lens"]: stages.weight(j["lens"]) for j in judges}}))
    (st / "judges.json").write_text(json.dumps(
        [{"lens": j["lens"], "panel": "screen", "notes": j["notes"], "top4": j.get("top4", []), "promise": j.get("promise", []),
          "scores": j["scores"], "fixes": j["fixes"]} for j in judges]))
    (st / "finish.json").write_text(json.dumps({
        **stages.common(a), "stage": "finish",
        "ranking": [{"id": x["id"], "name": x["name"], "origin": x["origin"], "mean": x["mean"], "panel": "screen",
                     "top4": x["top4"], "promise": x["promise"]} for x in ranking],
        "newPalettes": [f"{x['id']} ({x['name']})" for x in ds]}))
    print(f"screen-only round {a['roundNo']}: best {ranking[0]['id']} {ranking[0]['mean']}, today {today}")
    for x in ranking:
        print(f"  {x['id']:12} {x['name']:30} {x['mean']:5} top4 {x['top4']} promise {x['promise']} {x['origin']}")
    select(rnd)


if __name__ == "__main__":
    {"select": select, "settle": settle}[sys.argv[1]](*sys.argv[2:])
