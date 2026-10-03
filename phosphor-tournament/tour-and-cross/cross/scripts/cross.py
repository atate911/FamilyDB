"""The crossing rounds, 14a and 14b, run before the main tournament's round 14.

The six designs the main tournament carries into round 14 meet the side tour's seven finals. Each of
the thirteen is a LINE of its own. Every round each line gets one new design, its CROSS: its own
judges' fixes, plus features taken from the other camp (a main entrant takes from the tour finals, a
tour final from the main entrants). Every line carries its better design into the next round. Two
heats of mixed camps share fixed anchors, so their scores can be put on one scale. After 14b a final
panel ranks every line's best together, the field for round 14.

  python3 cross.py prep                 build the folder: dossiers, lessons, owner judge, links
  python3 cross.py open ROUND           ROUND is 14a or 14b: heat folders, renders, design stages
  python3 cross.py prepare ROUND OUT..  the design workflows' outputs: renders, candidates, judge stages
  python3 cross.py tally ROUND OUT..    the judge workflows' outputs: rankings, carried, dossiers
  python3 cross.py final                the final panel's folder, renders and judge stages
  python3 cross.py final-tally OUT..
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tour"))
import tour as tr  # noqa: E402  (the tour's helpers: bring, render_all, sheets, rank_heat, dossiers)

X = Path(__file__).resolve().parent
H = X.parent
TOUR = H / "tour"
LENSES = tr.LENSES

# Each line: its id at the start, its camp, its heat, where its files are, and its family's history
# (for the main entrants' dossiers) or the tour dossier it continues.
LINES = {
    "desk":       {"id": "r13-idea-1", "camp": "main", "heat": "a", "history": ["r12-idea-2", "r13-mut-2", "r13-idea-1"],
                   "idea": "a docked terminal column: one real cased terminal beside the family's desk, Home's question typed at the foot of its glass"},
    "quote":      {"id": "r13-mut-3", "camp": "main", "heat": "a", "history": ["r12-wild-4", "r13-mut-3"],
                   "idea": "a count board: each section led by one big quote or figure, read at a glance"},
    "dessau":     {"id": "r13-wild-3", "camp": "main", "heat": "a", "history": ["r13-wild-3"],
                   "idea": "Bauhaus display type: a modernist poster's hierarchy and geometry around the green screens"},
    "plate":      {"id": "r13-idea-2", "camp": "main", "heat": "b", "history": ["r13-idea-2"],
                   "idea": "a long-persistence instrument: a cut matte plate over one lit screen"},
    "listing":    {"id": "r12-idea-1", "camp": "main", "heat": "b", "history": ["r10-idea-1", "r11-idea-1", "r12-mut-4", "r12-idea-1"],
                   "idea": "a programme listing: the family's evening set as a TV listings page, bands with a head column"},
    "folio":      {"id": "r13-wmut-1", "camp": "main", "heat": "b", "history": ["r12-wmut-1", "r13-wmut-1"],
                   "idea": "a videotex service as a folio: numbered pages of one service, read like a teletext magazine"},
    "trued":      {"id": "t3-track-refine2", "camp": "tour", "heat": "a", "tour": "track", "src": "t3-a",
                   "idea": "the track series: the family's week as a signal box's lit track diagram; the greeting its own lit board with the ways to start on a steel branch, Next up as the line's first stop"},
    "manual":     {"id": "t3-figure-refine", "camp": "tour", "heat": "a", "tour": "figure", "src": "t3-b",
                   "idea": "the family's operator manual: every list in time hangs from a rail with one lit NOW, every section led by a figure drawn from its own data"},
    "departures": {"id": "t3-timetable-refine", "camp": "tour", "heat": "a", "tour": "timetable", "src": "t3-a",
                   "idea": "a station at night: Vera's line down the left with the box as its first stop, a dot-matrix departures board beside it"},
    "settled":    {"id": "t3-switchboard-refine", "camp": "tour", "heat": "a", "tour": "switchboard", "src": "t3-b",
                   "idea": "the videotex sommaire settled: Home as a two-tier map of the service, every inner page on one rack with its own sized tube"},
    "sill":       {"id": "t3-track-graft", "camp": "tour", "heat": "b", "tour": "track", "src": "t3-a",
                   "idea": "the track series' bolder Home: the question as the board's headline, the tube's lit wire dropping onto the Coming up rail, To do's stops the ticks you press"},
    "pocket":     {"id": "t3-pocket-refine", "camp": "tour", "heat": "b", "tour": "pocket", "src": "t3-a",
                   "idea": "the family's pocket diary: one steel line of time from Now to Later, every date set as a diary sets a day"},
    "waypoint":   {"id": "t3-console-graft", "camp": "tour", "heat": "b", "tour": "console", "src": "t3-b",
                   "idea": "a 1969 flight console: a readout strip, the weeks as a flight plan whose waypoint rings carry the day numerals that lead the rows"},
}
HEATS = {"a": [k for k, v in LINES.items() if v["heat"] == "a"], "b": [k for k, v in LINES.items() if v["heat"] == "b"]}
# Fixed in both heats of every round and in the final, so heats and rounds share one scale.
ANCHORS = {"00-current": "today's page", "r13-idea-1": "Desk Terminal, Joined (the main tournament's leader)",
           "t3-track-refine2": "Trued, Relit (the side tour's winner)"}
ROUNDS = ["x14a", "x14b"]
LABEL = {"x14a": "14a", "x14b": "14b", "x14f": "14 (final panel)"}


def src_of(k):
    v = LINES[k]
    return TOUR / v["src"] if v["camp"] == "tour" else H / "rounds" / "r14"


def heat_dir(r, h):
    return X / f"{r}-{h}"


def prep():
    X.mkdir(exist_ok=True)
    (X / "dossiers").mkdir(exist_ok=True)
    for name in ["ledger.md", "ledger-index.md", "gallery", "donors"]:
        if not (X / name).exists():
            (X / name).symlink_to(TOUR / name)
    recs = tr.main_records()
    names = {x["id"]: x["name"] for res in recs.values() for x in res["ranking"]}
    landing = tr.load(TOUR / "landing" / "results.json")
    land = {"ranking": landing["ranking"], "judges": landing["judges"], "todayMean": None,
            "designs": tr.load(TOUR / "t3" / "stage" / "designs.json")}
    for k, v in LINES.items():
        head = (f"# Dossier: {k} ({v['camp']} camp)\n\nThe line's idea: {v['idea']}.\n\nEvery judge's words on this "
                f"line, oldest first. Scores compare best within their round.\n")
        if v["camp"] == "tour":
            body = (TOUR / "dossiers" / f"{v['tour']}.md").read_text()
            body += "\n## The side tour's landing panel (every final beside its origin and both yardsticks, one scale)\n\n"
            body += tr.dossier_entry("landing panel", land, v["id"])
        else:
            parts = []
            for pid in v["history"]:
                for n, res in recs.items():
                    e = tr.dossier_entry(f"main round {n}", res, pid)
                    if e:
                        parts.append(e)
            ls = tr.lesson_lines([names.get(p, p) for p in v["history"]])
            if ls:
                parts.append("## What the main tournament's lessons.md recorded about this family\n\n" + "\n\n".join(ls) + "\n")
            if v["id"] == "r13-idea-1":
                parts.append("## The side tour's landing panel\n\n" + tr.dossier_entry("landing panel", land, v["id"]))
            body = "\n".join(parts)
        (X / "dossiers" / f"{k}.md").write_text(head + "\n" + body)
        target = TOUR / f"ledger-for-{v['tour']}.md" if v["camp"] == "tour" else None
        p = X / f"ledger-for-{k}.md"
        if not p.exists():
            if target:
                p.symlink_to(target)
            else:
                p.write_text(f"# Ledger shortlist for {k}\n\nNo shortlist was scouted for the main entrants: search "
                             f"ledger-index.md for features that suit this line's idea ({v['idea']}).\n")
    own = (TOUR / "owner_judge.md").read_text()
    (X / "owner_judge.md").write_text(own + """
## On the crossing rounds (14a and 14b, before round 14)

After the side tour landed, the owner asked: "Let's find a good way to evaluate these as a sub-task before
round 14, so that we can compare these mutants to the established tournament entries, and see if we can
take the best features of each." The six round-14 entrants of the main tournament and the tour's seven
finals now meet in mixed heats, and each is crossed with the other camp's best features.
""")
    if not (X / "lessons.md").exists():
        (X / "lessons.md").write_text(
            "# What the crossing rounds' judges have learned\n\nThe crossing rounds (14a, 14b) put the main "
            "tournament's round-14 entrants beside the side tour's finals. Their lessons follow, round by round. "
            f"The side tour's lessons are in {TOUR}/lessons.md; the main tournament's in {H}/lessons.md.\n")
    if not (X / "titles.md").exists():
        shutil.copy2(TOUR / "titles.md", X / "titles.md")
    print("prepared", X)


def carried_now(r):
    """Each line's current design and the folder it is in."""
    i = ROUNDS.index(r)
    if i == 0:
        return {k: (v["id"], src_of(k)) for k, v in LINES.items()}
    prev = tr.load(X / ROUNDS[i - 1] / "results.json")
    return {k: (prev["lines"][k]["carried"]["id"], heat_dir(ROUNDS[i - 1], LINES[k]["heat"])) for k in LINES}


def anchor_src(pid):
    return TOUR / "landing"


def open_(r):
    rd = X / r
    (rd / "stage").mkdir(parents=True, exist_ok=True)
    cur = carried_now(r)
    lines = {}
    for h, ks in HEATS.items():
        d = heat_dir(r, h)
        tr.make_dir(d)
        for pid in ANCHORS:
            if pid != "00-current":
                tr.bring(pid, anchor_src(pid), d)
        for k in ks:
            pid, src = cur[k]
            tr.bring(pid, src, d)
    others = {"main": [], "tour": []}
    for k, v in LINES.items():
        pid, _ = cur[k]
        d = heat_dir(r, v["heat"])
        name = tr.load(d / "palettes" / f"{pid}.json")["name"]
        lines[k] = {"key": k, "camp": v["camp"], "idea": v["idea"], "heat": v["heat"], "dir": str(d),
                    "carried": [{"id": pid, "name": name}],
                    "briefs": [{"slot": "cross", "parent": pid, "parentName": name}],
                    "entrants": [f"{r}-{k}-cross"]}
        others[v["camp"]].append({"key": k, "id": pid, "name": name, "dir": str(d)})
    for k in lines:
        lines[k]["otherCamp"] = others["tour" if lines[k]["camp"] == "main" else "main"]
    a = {"round": r, "label": LABEL[r], "lines": lines, "anchors": ANCHORS,
         "heats": {h: {"dir": str(heat_dir(r, h)), "lines": ks} for h, ks in HEATS.items()}}
    tr.dump(rd / "args.json", a)
    jobs = [(heat_dir(r, h), pid) for h in HEATS for pid in [*[cur[k][0] for k in HEATS[h]], *[p for p in ANCHORS if p != "00-current"]]
            if tr.needs_render(heat_dir(r, h), pid, same_day=True)]
    tr.render_all(sorted(set(jobs)))
    for old in (rd / "stage").glob("design-*.json"):
        old.unlink()
    for i, (k, lin) in enumerate(lines.items(), 1):
        f = {"stage": "design", "round": r, "label": LABEL[r], "roundNo": ROUNDS.index(r) + 1, "key": k, "cross": True,
             "lin": {"name": f"{k} ({lin['carried'][0]['name']})", "dir": lin["dir"], "carried": lin["carried"],
                     "briefs": lin["briefs"], "idea": lin["idea"], "camp": lin["camp"], "otherCamp": lin["otherCamp"],
                     "mutant": None},
             "plan": True, "mutant": False}
        tr.dump(rd / "stage" / f"design-{i}.json", f)
    print(r, "open:", {k: lin["carried"][0]["id"] for k, lin in lines.items()})


def prepare(r, *outs):
    rd = X / r
    a = tr.load(rd / "args.json")
    designs = {}
    if (rd / "stage" / "designs.json").exists():
        designs = {x["id"]: x for x in tr.load(rd / "stage" / "designs.json")}
    for o in outs:
        res = tr.result_of(o)
        for x in res.get("designs", []):
            designs[x["id"]] = {k: x[k] for k in tr.KEEP if k in x}
        for k, plan in (res.get("plans") or {}).items():
            tr.dump(rd / "stage" / f"plan-{k}.json", plan)
    tr.dump(rd / "stage" / "designs.json", list(designs.values()))
    older = {}
    for f in [*TOUR.glob("t[0-9]/stage/designs.json"), *X.glob("x14*/stage/designs.json")]:
        for x in tr.load(f):
            older.setdefault(x["id"], x)
    jobs = []
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        if tr.needs_render(d, "00-current", same_day=True):
            if (d / "out" / "00-current").is_symlink():
                (d / "out" / "00-current").unlink()
            tr.render_all([(d, "00-current")])
        jobs += [(d, p.stem) for p in (d / "palettes").glob("*.json")
                 if p.stem != "00-current" and tr.needs_render(d, p.stem, same_day=True)]
    tr.render_all(jobs)
    heats = {}
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        tr.sheets(d)
        present = {p.stem for p in (d / "palettes").glob("*.json")}
        notes = [f"# The candidates of heat {h}, crossing round {a['label']}\n\nThe main tournament's round-14 entrants "
                 "(MAIN camp) and the side tour's finals (TOUR camp) meet here, each line with this round's CROSS of it: "
                 "its own judges' fixes plus features taken from the other camp. ANCHORS (score them; they are "
                 "yardsticks, not candidates unless a line below lists them): " +
                 "; ".join(f"{p} ({w})" for p, w in a["anchors"].items()) + ".\n"]
        lins = []
        for k in heat["lines"]:
            lin = a["lines"][k]
            c = lin["carried"][0]
            ids = [c["id"]] + [e for e in lin["entrants"] if e in present]
            lins.append({"name": f"{k}: {c['name']} ({lin['camp']} camp)", "idea": lin["idea"], "ids": ids})
            x = designs.get(c["id"]) or older.get(c["id"]) or {}
            notes.append(f"## Line {k} ({lin['camp']} camp): {lin['idea']}\n### {c['id']} {c['name']} (carried)\n"
                         f"{x.get('tagline', '')} {x.get('concept', '')}" + (f"\nTitle: {x['title']}" if x.get('title') else ""))
            for e in lin["entrants"]:
                x = designs.get(e)
                if x:
                    notes.append(f"### {e} {x['name']} (CROSS of {c['id']}: its fixes, and features from the "
                                 f"{'tour' if lin['camp'] == 'main' else 'main'} camp)\n{x['tagline']}\nTitle: {x.get('title', '')}\n"
                                 f"Concept: {x['concept']}\nWhat it took and why: {' | '.join(x.get('decisions', []))}\n"
                                 f"Designer's own weaknesses: {' | '.join(x.get('weaknesses', []))}")
        (d / "stage" / "candidates.md").write_text("\n\n".join(notes) + "\n")
        cand = [i for x in lins for i in x["ids"]]
        yard = [p for p in a["anchors"] if p not in cand]
        heats[h] = {"dir": heat["dir"], "lineages": lins, "yardsticks": yard, "ids": yard + cand}
    for old in (rd / "stage").glob("judge-*.json"):
        old.unlink()
    for i, lens in enumerate(LENSES, 1):
        tr.dump(rd / "stage" / f"judge-{i}.json", {"stage": "judge", "cross": True, "round": r, "label": a["label"],
                                                   "roundNo": ROUNDS.index(r) + 1 if r in ROUNDS else 3,
                                                   "lens": lens, "heats": heats})
    print(r, "judge stages:", {h: len(x["ids"]) for h, x in heats.items()})


def linked(heats_rk):
    """Put heat b on heat a's scale: shift it by the anchors' mean difference (each anchor is judged in both)."""
    a = {x["id"]: x["mean"] for x in heats_rk["a"]}
    b = {x["id"]: x["mean"] for x in heats_rk.get("b", [])}
    common = [p for p in ANCHORS if p in a and p in b]
    return round(sum(a[p] - b[p] for p in common) / len(common), 2) if common else 0.0


def tally(r, *outs):
    rd = X / r
    a = tr.load(rd / "args.json")
    judged = {}
    for o in outs:
        for j in tr.result_of(o).get("judges", []):
            judged.setdefault(j["heat"], {})[j["lens"]] = j
    designs = {x["id"]: x for x in tr.load(rd / "stage" / "designs.json")}
    out = {"round": r, "label": a["label"], "heats": {}, "lines": {}, "judges": {}}
    rks = {}
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        js = list(judged.get(h, {}).values())
        names = {p.stem: tr.load(p)["name"] for p in (d / "palettes").glob("*.json")}
        rks[h] = tr.rank_heat(js, list(names), names)
        out["judges"][h] = [{k: j.get(k) for k in ("lens", "notes", "top4", "promise", "scores", "fixes", "titles")} for j in js]
    shift = linked(rks)
    for h, rk in rks.items():
        for x in rk:
            x["linked"] = round(x["mean"] + (shift if h == "b" else 0), 2)
            x["line"] = next((k for k in a["heats"][h]["lines"] if x["id"] in
                              [a["lines"][k]["carried"][0]["id"], *a["lines"][k]["entrants"]]), "anchor")
        out["heats"][h] = {"ranking": rk, "judges": [j["lens"] for j in judged.get(h, {}).values()]}
        print(f"\nHEAT {h} ({len(judged.get(h, {}))} lenses){'; heat b shifted by ' + str(shift) + ' onto heat a' if h == 'b' else ''}")
        for x in rk:
            print(f"  {x['id']:24} {x['name'][:30]:30} {x['mean']:5} linked {x['linked']:5} top4 {x['top4']} promise {x['promise']}  {x['line']}")
    out["shift"] = shift
    for k, lin in a["lines"].items():
        rk = rks[lin["heat"]]
        mine = [x for x in rk if x["line"] == k and designs.get(x["id"], {}).get("floorsFailed", 0) == 0]
        best = mine[0]
        out["lines"][k] = {"carried": {"id": best["id"], "name": best["name"], "mean": best["mean"], "linked": best["linked"]},
                           "ranking": [{"id": x["id"], "mean": x["mean"], "linked": x["linked"]} for x in mine],
                           "camp": lin["camp"], "heat": lin["heat"]}
    tr.dump(rd / "results.json", out)
    print("\nEVERY LINE'S BEST, on heat a's scale:")
    for k, v in sorted(out["lines"].items(), key=lambda kv: -kv[1]["carried"]["linked"]):
        c = v["carried"]
        print(f"  {k:11} {v['camp']:5} {c['id']:24} {c['name'][:30]:30} {c['linked']}")
    # Dossiers and the titles board.
    for h in a["heats"]:
        res = {"ranking": rks[h], "judges": out["judges"][h], "todayMean": next((x["mean"] for x in rks[h] if x["id"] == "00-current"), None),
               "designs": list(designs.values())}
        for k in a["heats"][h]["lines"]:
            lin = a["lines"][k]
            parts = [f"\n## Crossing round {a['label']} (heat {h})\n"]
            for pid in [lin["carried"][0]["id"], *lin["entrants"]]:
                parts.append(tr.dossier_entry(f"crossing round {a['label']}", res, pid, "; its CROSS" if pid in lin["entrants"] else "; carried"))
            with open(X / "dossiers" / f"{k}.md", "a") as f:
                f.write("\n".join(parts))
    with open(X / "titles.md", "a") as f:
        f.write(f"\n## Crossing round {a['label']}: titles tried\n\n")
        for x in designs.values():
            f.write(f"- {x['id']}: {x.get('title', '')[:160]}\n")
        f.write("\nWhat the judges said:\n")
        for h in a["heats"]:
            for j in out["judges"][h]:
                if j.get("titles"):
                    f.write(f"- heat {h}, {j['lens']}: {j['titles']}\n")
    tr.dump(rd / "stage" / "finish.json", {"stage": "finish", "cross": True, "round": r, "label": a["label"], "roundNo": ROUNDS.index(r) + 1})
    print(rd / "results.json")


def final():
    r = "x14f"
    d = X / r
    tr.make_dir(d)
    prev = tr.load(X / ROUNDS[-1] / "results.json")
    ids = []
    for k, v in prev["lines"].items():
        pid = v["carried"]["id"]
        tr.bring(pid, heat_dir(ROUNDS[-1], v["heat"]), d)
        ids.append(pid)
    for pid in ANCHORS:
        if pid != "00-current" and pid not in ids:
            tr.bring(pid, anchor_src(pid), d)
    if tr.needs_render(d, "00-current", same_day=True):
        if (d / "out" / "00-current").is_symlink():
            (d / "out" / "00-current").unlink()
        tr.render_all([(d, "00-current")])
    tr.render_all([(d, p.stem) for p in (d / "palettes").glob("*.json") if p.stem != "00-current" and tr.needs_render(d, p.stem, same_day=True)])
    tr.sheets(d)
    older = {}
    for f in [*TOUR.glob("t[0-9]/stage/designs.json"), *X.glob("x14*/stage/designs.json")]:
        for x in tr.load(f):
            older[x["id"]] = x
    notes = ["# The final panel before round 14\n\nEvery line's best after the two crossing rounds: the field the main "
             "tournament's round 14 could start from. 00-current is today's page (a yardstick).\n"]
    lins = []
    for k, v in prev["lines"].items():
        c = v["carried"]
        x = older.get(c["id"], {})
        notes.append(f"## {c['id']} {c['name']} (line {k}, {v['camp']} camp)\n{x.get('tagline', '')} {x.get('concept', '')}"
                     + (f"\nTitle: {x['title']}" if x.get('title') else ""))
        lins.append({"name": f"{k}: {c['name']} ({v['camp']} camp)", "idea": LINES[k]["idea"], "ids": [c["id"]]})
    (d / "stage").mkdir(exist_ok=True)
    (d / "stage" / "candidates.md").write_text("\n\n".join(notes) + "\n")
    yard = [p for p in ANCHORS if p not in ids]
    heats = {"f": {"dir": str(d), "lineages": lins, "yardsticks": yard, "ids": yard + ids}}
    (X / r).mkdir(exist_ok=True)
    tr.dump(X / r / "args.json", {"round": r, "label": LABEL[r], "heats": heats})
    for i, lens in enumerate(LENSES, 1):
        tr.dump(d / "stage" / f"judge-{i}.json", {"stage": "judge", "cross": True, "final": True, "round": r, "label": LABEL[r],
                                                  "roundNo": 3, "lens": lens, "heats": heats})
    print("final panel:", ids)


def final_tally(*outs):
    d = X / "x14f"
    js = [j for o in outs for j in tr.result_of(o).get("judges", [])]
    names = {p.stem: tr.load(p)["name"] for p in (d / "palettes").glob("*.json")}
    rk = tr.rank_heat(js, list(names), names)
    camp = {v["id"]: v["camp"] for v in LINES.values()}
    prev = tr.load(X / ROUNDS[-1] / "results.json")
    line_of = {v["carried"]["id"]: k for k, v in prev["lines"].items()}
    tr.dump(X / "x14f" / "results.json", {"ranking": rk, "judges": js})
    for x in rk:
        k = line_of.get(x["id"])
        print(f"  {x['id']:24} {x['name'][:30]:30} {x['mean']:5} top4 {x['top4']} promise {x['promise']}  "
              f"{(k + ' / ' + prev['lines'][k]['camp']) if k else 'yardstick'}")


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    {"prep": prep, "open": lambda r: open_("x" + r if not r.startswith("x") else r),
     "prepare": lambda r, *o: prepare("x" + r if not r.startswith("x") else r, *o),
     "tally": lambda r, *o: tally("x" + r if not r.startswith("x") else r, *o),
     "final": final, "final-tally": final_tally}[cmd](*rest)
