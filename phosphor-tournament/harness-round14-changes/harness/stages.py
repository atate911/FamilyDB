"""Run a round as several stage workflows side by side (stage.js), so every core is used.

Each workflow runs at most two agents at once, so a round is split: design stages (two chains of
random entrants or mutants each, and one stage with the planner and the informed entrants), then
judge stages, then one finish stage (curate and learn together). Between them, this script does
the plain work on every core: renders, cards and sheets, the tally.

From round 14 a round's args carry "panel": "screen", and it is judged in two panels (the older
"full" panel, eight lenses over the whole field, still works for a round without it):
- the SCREEN: five lenses (the owner's judge, soul, style, systemuse and the skeptic) score the
  whole field, each from one card per design (contact.py), in three workflows;
- the CUT: the seven best by the screen's weighted mean go to the final, with the two designs the
  screen most wants developed (two promise votes or more) that are not already among them;
- the FINAL: all eight lenses score the finalists and put them in a strict order, in four
  workflows. The finalists rank first, by their weighted order (Borda: a judge's first of n gets
  n-1 points, times its weight), then the rest by the screen's mean.
In rounds 9 to 13 the eight lenses agreed closely (system and skeptic .93, interaction and
usability .87; only style stood apart), and this screen with a cut at seven kept every round's
top four (`python3 stages.py replay`), while the 4th and 5th places were 0.01 apart in four of
those five rounds: closer than eight judges' scores can tell apart, which the final's order can.

  python3 stages.py split rN [RESUME.json]   write rounds/rN/stage/design-K.json, one per workflow,
                                             and stage/brief-pack.md for the planner
  python3 stages.py prepare rN OUT...        merge the design outputs, render what is missing or
                                             stale (in parallel), draw the cards and sheets, write
                                             the table and candidates, and stage/screen-K.json
                                             (or judge-K.json for a "full" panel)
  python3 stages.py cut rN OUT...            merge the screen's outputs, choose the finalists,
                                             write stage/final-K.json
  python3 stages.py tally rN OUT...          merge the final's (or the full panel's) outputs, rank,
                                             write finish.json
  python3 stages.py assemble rN OUT          write rounds/rN/stage/output.json, which
                                             `advance.py close` reads like a whole round's output
  python3 stages.py replay [FIRST LAST]      the screen and cut replayed on earlier rounds' scores
  python3 stages.py usage DIR...             tokens by agent from workflow transcript folders

OUT is a workflow's output file (the path its completion notice gives).
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
# The shots every render must have (render.js; from round 14 Sign in, 404, General settings, the
# whole form and the phone's Chat are no longer shot), and the cards drawn from them.
SHOTS = ["home", "ideas", "chat", "status", "home-phone", "plans", "todo", "settings", "controls-field"]
CARD_KINDS = ["home", "lists", "use", "close"]
LENS_GROUPS = [["feedback", "soul"], ["style", "system"], ["interaction", "type"], ["skeptic", "usability"]]
SCREEN_GROUPS = [["feedback", "soul"], ["style", "systemuse"], ["skeptic"]]
FINALISTS, PROMISE_PICKS, PROMISE_MIN = 7, 2, 2
# How much each judge counts in an entrant's mean; a lens not named counts 1. From round 10 the
# owner asked for the phosphor soul (the CRT's glow, halos, scanlines and live dots) to weigh
# slightly more than the others.
LENS_WEIGHTS = {"soul": 1.5}
# The fields a later stage needs from a finished design; its tokens stay in its palette file.
KEEP = ["id", "name", "tagline", "concept", "companions", "decisions", "floorsFailed", "measures",
        "strengths", "weaknesses", "revisions", "crit", "firstDraft", "secondDraft"]


def result_of(out_file):
    raw = Path(out_file).read_text()
    return json.loads(raw[raw.find("{"):])["result"]


def rdir(rnd):
    return HERE / "rounds" / rnd


def common(a):
    return {"round": a["round"], "roundNo": a["roundNo"], "mode": a["mode"], "panel": a.get("panel", "full"),
            "carried": [{"id": c["id"], "name": c["name"]} for c in a["carried"]],
            "wildCarried": [{"id": c["id"], "name": c["name"]} for c in a.get("wildCarried", [])],
            "mutants": a["mutants"], "wildMutants": a.get("wildMutants", []), "nWild": len(a.get("wild", [])),
            "nRandom": len(a["seeds"]), "nInformed": a["nInformed"]}


def entrant_ids(a):
    """Every new entrant of a round, in a fixed order."""
    r = a["round"]
    return ([f"{r}-rand-{i}" for i in range(1, len(a["seeds"]) + 1)]
            + [f"{r}-mut-{i}" for i in range(1, len(a["mutants"]) + 1)]
            + [f"{r}-wild-{w['slot']}" for w in a.get("wild", [])]
            + [f"{r}-wmut-{m['slot']}" for m in a.get("wildMutants", [])]
            + [f"{r}-idea-{i}" for i in range(1, a["nInformed"] + 1)])


def field_ids(a):
    """Every design judged in a round: the carried, the wild lane's carried, then the newcomers."""
    return [c["id"] for c in a["carried"] + a.get("wildCarried", [])] + entrant_ids(a)


def origin_of(a, pid):
    r = a["round"]
    if pid.startswith(f"{r}-rand"):
        return "random"
    if pid.startswith(f"{r}-mut"):
        m = a["mutants"][int(pid.split("-")[-1]) - 1]
        return {"crossover": "crossover", "type": "type mutant", "graphics": "graphics mutant",
                "phosphor": "phosphor mutant"}.get(m.get("kind"), "mutant")
    if pid.startswith(f"{r}-wild"):
        return "wild"
    if pid.startswith(f"{r}-wmut"):
        return "wild mutant"
    if pid in {c["id"] for c in a.get("wildCarried", [])}:
        return "wild carried"
    return "informed" if pid.startswith(f"{r}-idea") else "carried"


def weight(lens):
    return LENS_WEIGHTS.get(lens.removeprefix("screen-"), 1)


def score_table(judges, names, a):
    """Each design's weighted mean over these judges, its plain mean, scores by lens, top-four and
    promise votes, and today's weighted mean."""
    t = {pid: {"id": pid, "name": n, "total": 0, "weights": 0, "plain": 0, "n": 0, "top4": 0, "promise": 0,
               "byLens": {}, "origin": origin_of(a, pid)}
         for pid, n in names.items()}
    today = [(s["score"], weight(j["lens"])) for j in judges for s in j["scores"] if s["id"] == "00-current"]
    today_mean = round(sum(s * w for s, w in today) / sum(w for _, w in today), 2) if today else None
    for j in judges:
        for s in j["scores"]:
            if s["id"] in t:
                x = t[s["id"]]
                x["total"] += s["score"] * weight(j["lens"])
                x["weights"] += weight(j["lens"])
                x["plain"] += s["score"]
                x["n"] += 1
                x["byLens"][j["lens"].removeprefix("screen-")] = s["score"]
        for pid in j.get("top4", []):
            if pid in t:
                t[pid]["top4"] += 1
        for pid in j.get("promise", []):
            if pid in t:
                t[pid]["promise"] += 1
    rows = [{**x, "mean": round(x["total"] / x["weights"], 2) if x["n"] else 0,
             "plainMean": round(x["plain"] / x["n"], 2) if x["n"] else 0} for x in t.values()]
    for x in rows:
        x["beatToday"] = today_mean is None or x["mean"] > today_mean
    return rows, today_mean


def names_of(a, ds):
    return {c["id"]: c["name"] for c in a["carried"] + a.get("wildCarried", [])} | {x["id"]: x["name"] for x in ds}


def judges_from(outs):
    judges = {}
    for o in outs:
        for j in result_of(o).get("judges", []):
            judges[j["lens"]] = j
    return list(judges.values())


def brief_pack(a):
    """What the planner reads in place of three whole results files (each some 90,000 tokens): the
    last three rounds' rankings with their promise votes, and the last round's judges on every
    design carried into this round."""
    hist = [Path(h) for h in a.get("history", []) if Path(h).exists() and Path(h).parent.parent.name == "rounds"]
    out = ["# Brief pack for the planner", "",
           "Made by stages.py from the last three rounds' results. Search the files themselves (python or jq) for more."]
    for h in hist[-3:]:
        res = json.loads(h.read_text())
        out += ["", f"## {h.parent.name}: the ranking ({h})", "",
                "| # | id | name | origin | mean | top 4s | promise |", "|---|---|---|---|---|---|---|"]
        for i, x in enumerate(res["ranking"], 1):
            out.append(f"| {i} | {x['id']} | {x['name']} | {x.get('origin', '')} | {x['mean']} | {x.get('top4', '')} | {x.get('promise', 0)} |")
    if hist:
        res = json.loads(hist[-1].read_text())
        carried = [c["id"] for c in a["carried"] + a.get("wildCarried", [])]
        out += ["", f"## {hist[-1].parent.name}: what each judge said", ""]
        for j in res.get("judges", []):
            out += [f"### {j['lens']}", "", j.get("notes", "").strip(), ""]
            for pid in carried:
                why = [x["why"] for x in j.get("scores", []) if x["id"] == pid]
                fix = [x["suggestion"] for x in j.get("fixes", []) if x["id"] == pid]
                if why or fix:
                    out.append(f"- {pid}: {' '.join(why)}" + (f" FIX: {' '.join(fix)}" if fix else ""))
            out.append("")
    return "\n".join(out) + "\n"


def short_text(text, limit):
    """At most `limit` characters, cut at the end of a sentence where there is one."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:end + 1] if end > limit // 2 else cut.rstrip() + "...")


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
        chains.append((3 if m.get("kind") in ("crossover", "phosphor") else 1, "mut", i, f"{r}-mut-{i}"))
    for w in a.get("wild", []):
        chains.append((3, "wild", w, f"{r}-wild-{w['slot']}"))
    for m in a.get("wildMutants", []):
        chains.append((3, "wmut", m["slot"], f"{r}-wmut-{m['slot']}"))
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
                "wildHere": [c[2] for c in g if c[1] == "wild"],
                "wildMutantSlots": [c[2] for c in g if c[1] == "wmut"],
                "plan": False,
                "resume": {i: by_file(i, resume[i]) for i in ids if i in resume}}
        files.append(stage_dir / f"design-{k}.json")
        files[-1].write_text(json.dumps(args))
    extra = [x for x in a.get("extraBriefs", []) if not (resume.get(f"{r}-idea-{x['slot']}") or {}).get("final")]
    if extra:  # entrants briefed at the owner's request, beside the planner's
        args = {**common(a), "stage": "design", "seeds": [], "mutantSlots": [], "plan": False,
                "briefs": [{k: x[k] for k in ("slot", "secondDraft", "brief")} for x in extra],
                "resume": {i: by_file(i, resume[i]) for i in (f"{r}-idea-{x['slot']}" for x in extra) if i in resume}}
        files.append(stage_dir / f"design-{len(files) + 1}.json")
        files[-1].write_text(json.dumps(args))
    planned = a["nInformed"] - len(a.get("extraBriefs", []))
    informed_done = all((resume.get(f"{r}-idea-{i}") or {}).get("final") for i in range(1, planned + 1))
    if planned and not informed_done:
        args = {**common(a), "stage": "design", "seeds": [], "mutantSlots": [], "plan": True, "nPlanned": planned,
                "history": a["history"],
                "resume": {i: v for i, v in resume.items() if "-idea-" in i}}
        files.append(stage_dir / f"design-{len(files) + 1}.json")
        files[-1].write_text(json.dumps(args))
    (stage_dir / "brief-pack.md").write_text(brief_pack(a))
    for f in files:
        print(f)
    print(stage_dir / "brief-pack.md")


def needs_render(d, pid):
    shots = d / "out" / pid / "shots"
    if any(not (shots / f"{s}.png").exists() for s in SHOTS):
        return True
    if any(not (d / "cards" / f"{pid}-{k}.png").exists() for k in CARD_KINDS):
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
    order = entrant_ids(a)
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

    def removed(pid):  # what a design took off the page (lint_variant.py lists it), for the judges
        f = d / "variants" / pid / "removed.txt"
        text = f.read_text().strip() if f.exists() else ""
        return f"\nRemoved from the page (weigh what the family loses against what the page gains): {text}" if text else ""
    notes = [f"### {c['id']} {c['name']} (carried)\n{c['summary']}{removed(c['id'])}" for c in a["carried"] + a.get("wildCarried", [])]
    notes += [f"### {x['id']} {x['name']}\n{x['tagline']}\nConcept: {x['concept']}\nCompanions: {x['companions']}\n"
              f"Designer's own weaknesses: {' | '.join(x['weaknesses'])}{removed(x['id'])}" for x in ds]
    (stage_dir / "candidates.md").write_text("\n\n".join(notes) + "\n")
    # The short version every judge reads (the long one stays, for one design a judge wants more on).
    short = [f"### {c['id']} {c['name']} (carried)\n{short_text(c['summary'], 700)}{short_text(removed(c['id']), 400)}"
             for c in a["carried"] + a.get("wildCarried", [])]
    short += [f"### {x['id']} {x['name']}\n{short_text(x['tagline'], 200)} {short_text(x['concept'], 500)}\n"
              f"Weaknesses: {' | '.join(short_text(w, 160) for w in x['weaknesses'][:3])}{short_text(removed(x['id']), 400)}" for x in ds]
    (stage_dir / "candidates-short.md").write_text("\n\n".join(short) + "\n")

    for old in [*stage_dir.glob("judge-*.json"), *stage_dir.glob("screen-*.json"), *stage_dir.glob("final-*.json")]:
        old.unlink()
    if a.get("panel") == "screen":
        missing = [pid for pid in ["00-current", *field_ids(a)] for k in CARD_KINDS
                   if not (d / "cards" / f"{pid}-{k}.png").exists()]
        if missing and not os.environ.get("STAGES_DRY"):
            print("NO CARD:", ", ".join(missing))
        for k, lenses in enumerate(SCREEN_GROUPS, 1):
            f = stage_dir / f"screen-{k}.json"
            f.write_text(json.dumps({**common(a), "stage": "screen", "lenses": lenses, "ids": field_ids(a)}))
            print(f)
        return
    for k, lenses in enumerate(LENS_GROUPS, 1):
        f = stage_dir / f"judge-{k}.json"
        f.write_text(json.dumps({**common(a), "stage": "judge", "lenses": lenses}))
        print(f)


def choose_finalists(rows):
    """The cut: the FINALISTS best by the screen's mean, then up to PROMISE_PICKS more, by promise
    votes (at least PROMISE_MIN), so the ideas the screen most wants developed are looked at closely."""
    by_mean = sorted(rows, key=lambda x: (-x["mean"], -x["top4"], -x["promise"]))
    finalists = [x["id"] for x in by_mean[:FINALISTS]]
    extra = [x for x in sorted(rows, key=lambda x: (-x["promise"], -x["mean"]))
             if x["id"] not in finalists and x["promise"] >= PROMISE_MIN][:PROMISE_PICKS]
    return finalists + [x["id"] for x in extra], [x["id"] for x in extra]


def cut(rnd, *outs):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    ds = json.loads((stage_dir / "designs.json").read_text())
    judges = judges_from(outs)
    rows, today_mean = score_table(judges, names_of(a, ds), a)
    finalists, for_promise = choose_finalists(rows)
    (stage_dir / "screen.json").write_text(json.dumps(
        {"judges": judges, "ranking": sorted(rows, key=lambda x: -x["mean"]), "todayMean": today_mean,
         "finalists": finalists, "forPromise": for_promise}))
    for old in stage_dir.glob("final-*.json"):
        old.unlink()
    for k, lenses in enumerate(LENS_GROUPS, 1):
        f = stage_dir / f"final-{k}.json"
        # The finalists in a fixed order that is not the screen's, so no judge reads the screen's
        # ranking into the order of the cards.
        f.write_text(json.dumps({**common(a), "stage": "final", "lenses": lenses, "ids": sorted(finalists),
                                 "nField": len(rows)}))
        print(f)
    print(f"screen by {', '.join(j['lens'] for j in judges)}: today {today_mean}")
    for x in sorted(rows, key=lambda x: -x["mean"]):
        mark = "FINAL" if x["id"] in finalists else "     "
        print(f"  {mark} {x['id']:12} {x['name']:28} {x['mean']:5} top4 {x['top4']} promise {x['promise']} {x['origin']}"
              + (" (for its promise votes)" if x["id"] in for_promise else ""))


def tally_final(rnd, *outs):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    ds = json.loads((stage_dir / "designs.json").read_text())
    screen = json.loads((stage_dir / "screen.json").read_text())
    finalists = screen["finalists"]
    names = names_of(a, ds)
    judges = judges_from(outs)
    final_rows, today_mean = score_table(judges, {pid: names[pid] for pid in finalists}, a)
    screen_rows = {x["id"]: x for x in screen["ranking"]}
    # The order: a judge's first of n gets n-1 points, its last none, times its weight.
    points = {pid: 0.0 for pid in finalists}
    for j in judges:
        order = [pid for pid in j.get("order", []) if pid in points]
        for i, pid in enumerate(order):
            points[pid] += (len(finalists) - 1 - i) * weight(j["lens"])
    for x in final_rows:
        sx = screen_rows[x["id"]]
        x.update({"panel": "final", "orderPoints": round(points[x["id"]], 2), "promise": sx["promise"],
                  "screenMean": sx["mean"], "screenByLens": sx["byLens"]})
    final_rows.sort(key=lambda x: (-x["orderPoints"], -x["mean"], -x["screenMean"]))
    rest = [{**x, "panel": "screen", "screenMean": x["mean"], "screenByLens": x["byLens"]}
            for x in screen["ranking"] if x["id"] not in finalists]
    rest.sort(key=lambda x: (-x["mean"], -x["promise"]))
    ranking = final_rows + rest
    margin = round(ranking[0]["mean"] - today_mean, 2) if today_mean is not None else None
    screen_judges = [{**j, "lens": f"screen-{j['lens']}"} for j in screen["judges"]]
    all_judges = judges + screen_judges
    (stage_dir / "judges.json").write_text(json.dumps(
        [{"lens": j["lens"], "panel": "screen" if j["lens"].startswith("screen-") else "final", "notes": j["notes"],
          "top4": j.get("top4", []), "order": j.get("order"), "promise": j.get("promise", []), "scores": j["scores"],
          "fixes": j["fixes"]} for j in all_judges]))
    (stage_dir / "ranking.json").write_text(json.dumps(
        {"ranking": ranking, "todayMean": today_mean, "margin": margin, "judges": all_judges,
         "screenTodayMean": screen["todayMean"], "finalists": finalists, "forPromise": screen["forPromise"],
         "lensWeights": {j["lens"]: weight(j["lens"]) for j in all_judges}}))
    (stage_dir / "finish.json").write_text(json.dumps({
        **common(a), "stage": "finish",
        "ranking": [{"id": x["id"], "name": x["name"], "origin": x["origin"], "mean": x["mean"], "panel": x["panel"],
                     "top4": x["top4"], "promise": x["promise"]} for x in ranking],
        "newPalettes": [f"{x['id']} ({x['name']})" for x in ds]}))
    print(f"final by {', '.join(j['lens'] for j in judges)} ({len(judges)} of {sum(len(g) for g in LENS_GROUPS)}); "
          f"today {today_mean} (screen {screen['todayMean']}), best {ranking[0]['mean']} (margin {margin})")
    for x in ranking:
        print(f"  {x['panel']:6} {x['id']:12} {x['name']:28} {x['mean']:5} order {x.get('orderPoints', '-'):>5} "
              f"top4 {x['top4']} promise {x['promise']} {x['origin']}")
    print(stage_dir / "finish.json")


def tally(rnd, *outs):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    if a.get("panel") == "screen":
        return tally_final(rnd, *outs)
    stage_dir = d / "stage"
    r = a["round"]
    ds = json.loads((stage_dir / "designs.json").read_text())
    judges = {}
    for o in outs:
        for j in result_of(o).get("judges", []):
            judges[j["lens"]] = j
    judges = list(judges.values())
    names = {c["id"]: c["name"] for c in a["carried"] + a.get("wildCarried", [])} | {x["id"]: x["name"] for x in ds}
    wild_carried = {c["id"] for c in a.get("wildCarried", [])}

    def origin(pid):
        if pid.startswith(f"{r}-rand"):
            return "random"
        if pid.startswith(f"{r}-mut"):
            m = a["mutants"][int(pid.split("-")[-1]) - 1]
            return {"crossover": "crossover", "type": "type mutant", "graphics": "graphics mutant",
                    "phosphor": "phosphor mutant"}.get(m.get("kind"), "mutant")
        if pid.startswith(f"{r}-wild"):
            return "wild"
        if pid.startswith(f"{r}-wmut"):
            return "wild mutant"
        if pid in wild_carried:
            return "wild carried"
        return "informed" if pid.startswith(f"{r}-idea") else "carried"

    def weight(lens):
        return LENS_WEIGHTS.get(lens, 1)

    t = {pid: {"id": pid, "name": n, "total": 0, "weights": 0, "plain": 0, "n": 0, "top4": 0, "promise": 0,
               "byLens": {}, "origin": origin(pid)}
         for pid, n in names.items()}
    today = [(s["score"], weight(j["lens"])) for j in judges for s in j["scores"] if s["id"] == "00-current"]
    today_mean = round(sum(s * w for s, w in today) / sum(w for _, w in today), 2) if today else None
    for j in judges:
        for s in j["scores"]:
            if s["id"] in t:
                x = t[s["id"]]
                x["total"] += s["score"] * weight(j["lens"])
                x["weights"] += weight(j["lens"])
                x["plain"] += s["score"]
                x["n"] += 1
                x["byLens"][j["lens"]] = s["score"]
        for pid in j["top4"]:
            if pid in t:
                t[pid]["top4"] += 1
        for pid in j.get("promise", []):
            if pid in t:
                t[pid]["promise"] += 1
    # "mean" is weighted by LENS_WEIGHTS and is what ranks and carries; "plainMean" counts every judge once.
    ranking = [{**x, "mean": round(x["total"] / x["weights"], 2) if x["n"] else 0,
                "plainMean": round(x["plain"] / x["n"], 2) if x["n"] else 0} for x in t.values()]
    ranking.sort(key=lambda x: (-x["mean"], -x["top4"], -x["byLens"].get("skeptic", 0)))
    margin = round(ranking[0]["mean"] - today_mean, 2) if today_mean is not None else None
    thin = [f"{x['id']} ({x['n']})" for x in ranking if x["n"] < len(judges)]
    (stage_dir / "judges.json").write_text(json.dumps(
        [{"lens": j["lens"], "notes": j["notes"], "top4": j["top4"], "promise": j.get("promise", []), "scores": j["scores"], "fixes": j["fixes"]}
         for j in judges]))
    (stage_dir / "ranking.json").write_text(json.dumps(
        {"ranking": ranking, "todayMean": today_mean, "margin": margin, "judges": judges,
         "lensWeights": {j["lens"]: weight(j["lens"]) for j in judges}}))
    (stage_dir / "finish.json").write_text(json.dumps({
        **common(a), "stage": "finish",
        "ranking": [{"id": x["id"], "name": x["name"], "origin": x["origin"], "mean": x["mean"], "top4": x["top4"], "promise": x["promise"]}
                    for x in ranking],
        "newPalettes": [f"{x['id']} ({x['name']})" for x in ds]}))
    lenses = [j["lens"] if weight(j["lens"]) == 1 else f"{j['lens']} x{weight(j['lens'])}" for j in judges]
    print(f"judges: {', '.join(lenses)} ({len(judges)} of {sum(len(g) for g in LENS_GROUPS)})")
    if thin:
        print("scored by fewer judges:", ", ".join(thin))
    print(f"today {today_mean}, best {ranking[0]['mean']} (margin {margin})")
    for x in ranking:
        print(f"  {x['id']:12} {x['name']:24} {x['mean']:5} (plain {x['plainMean']}) top4 {x['top4']} promise {x['promise']} {x['origin']}")
    print(stage_dir / "finish.json")


def assemble(rnd, out):
    d = rdir(rnd)
    a = json.loads((d / "args.json").read_text())
    stage_dir = d / "stage"
    fin = result_of(out)
    rk = json.loads((stage_dir / "ranking.json").read_text())
    result = {"round": a["round"], "mode": a["mode"], "ranking": rk["ranking"],
              "top4": [x["id"] for x in rk["ranking"][:4]], "todayMean": rk["todayMean"], "margin": rk["margin"],
              "lensWeights": rk.get("lensWeights"), "panel": a.get("panel", "full"),
              "finalists": rk.get("finalists"), "screenTodayMean": rk.get("screenTodayMean"),
              "judges": rk["judges"], "designs": json.loads((stage_dir / "designs.json").read_text()),
              "plan": json.loads((stage_dir / "plan.json").read_text()),
              "table": (stage_dir / "table.md").read_text(),
              "curated": fin.get("curated"), "lessons": fin.get("lessons")}
    (stage_dir / "output.json").write_text(json.dumps({"result": result}))
    print(stage_dir / "output.json")


def replay(first="9", last="13"):
    """The screen and the cut replayed on earlier rounds' eight-lens scores: systemuse is taken as the
    mean of system, interaction and usability, and each round's real top four should reach the final."""
    screen = {"feedback": 1, "soul": LENS_WEIGHTS.get("soul", 1), "style": 1, "systemuse": 1, "skeptic": 1}
    for n in range(int(first), int(last) + 1):
        res = json.loads((rdir(f"r{n}") / "results.json").read_text())
        rk = [x for x in res["ranking"] if all(k in x["byLens"] for k in ("system", "interaction", "usability"))]
        rows = []
        for x in rk:
            by = {**x["byLens"], "systemuse": sum(x["byLens"][k] for k in ("system", "interaction", "usability")) / 3}
            mean = sum(by[k] * w for k, w in screen.items() if k in by) / sum(w for k, w in screen.items() if k in by)
            rows.append({"id": x["id"], "mean": mean, "top4": 0, "promise": x.get("promise", 0)})
        finalists, extra = choose_finalists(rows)
        top = [x["id"] for x in rk[:4]]
        lost = [f"{pid} (#{top.index(pid) + 1}, {rk[top.index(pid)]['mean']}; #5 {rk[4]['mean']})" for pid in top if pid not in finalists]
        print(f"r{n}: {len(rk)} designs, {len(finalists)} finalists ({len(extra)} for promise); "
              f"the real top four all in: {'yes' if not lost else 'no, lost ' + ', '.join(lost)}")


def usage(*dirs):
    """Tokens by agent, from workflow transcript folders (journal.jsonl names each agent; each
    agent-<id>.jsonl holds its messages with their usage). Run it on a round's folders to see what
    each stage cost; input counts cached reads and cache writes apart from fresh input."""
    totals = {}
    for folder in map(Path, dirs):
        labels = {}
        journal = folder / "journal.jsonl"
        if journal.exists():
            for line in journal.read_text().splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("type") == "started" and e.get("agentId"):
                    labels[e["agentId"]] = e.get("label") or e["agentId"]
        for f in folder.rglob("agent-*.jsonl"):
            aid = f.stem.removeprefix("agent-")
            label = labels.get(aid, aid)
            t = totals.setdefault(label, {"input": 0, "cacheRead": 0, "cacheWrite": 0, "output": 0, "messages": 0})
            seen = set()
            for line in f.read_text().splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                msg = e.get("message") if isinstance(e.get("message"), dict) else {}
                u = msg.get("usage")
                if not u or (msg.get("id") and msg["id"] in seen):  # a reply split over lines counts once
                    continue
                seen.add(msg.get("id"))
                t["input"] += u.get("input_tokens", 0)
                t["cacheRead"] += u.get("cache_read_input_tokens", 0)
                t["cacheWrite"] += u.get("cache_creation_input_tokens", 0)
                t["output"] += u.get("output_tokens", 0)
                t["messages"] += 1
    if not totals:
        print("no agent transcripts found")
        return
    rows = sorted(totals.items(), key=lambda kv: -(kv[1]["input"] + kv[1]["cacheRead"] + kv[1]["cacheWrite"]))
    print(f"{'agent':40} {'msgs':>5} {'input':>10} {'cache read':>11} {'cache write':>11} {'output':>8}")
    for label, t in rows:
        print(f"{label[:40]:40} {t['messages']:5} {t['input']:10} {t['cacheRead']:11} {t['cacheWrite']:11} {t['output']:8}")
    s = {k: sum(t[k] for _, t in rows) for k in ("messages", "input", "cacheRead", "cacheWrite", "output")}
    print(f"{'all':40} {s['messages']:5} {s['input']:10} {s['cacheRead']:11} {s['cacheWrite']:11} {s['output']:8}")


if __name__ == "__main__":
    {"split": split, "prepare": prepare, "cut": cut, "tally": tally, "assemble": assemble,
     "replay": replay, "usage": usage}[sys.argv[1]](*sys.argv[2:])
