"""The side tour: six ideas the tournament passed over, brought back as lineages and refined over
three rounds the way the tournament refines its winners, then judged side by side on landing.

Each round has two heats (three lineages each), so no judge faces more than about sixteen designs;
every lens judges both heats, and both heats carry the same two yardsticks (today's page and the
main tournament's leader after round 13), so their scores can be read together. Each lineage
carries on its best design (the track series its best two) and gets, every round, a refinement
(its own judges' fixes), a graft (the best features of the other lineages and of donor designs,
feature by feature) and a dice mutant (the tournament's dice). Round 1 adds a revival of the
track series' first line language.

  python3 tour.py prep                 donors dir, renders, dossiers, owner notes, lessons header
  python3 tour.py open N               set up round N's two heats, roll the dice, write the
                                       design-stage args (tour/tN/stage/design-*.json)
  python3 tour.py prepare N OUT...     merge the design outputs, render what is missing or stale,
                                       draw the sheets, write candidates and the judge args
  python3 tour.py tally N OUT...       merge the judges, rank each heat, choose each lineage's
                                       carried, append the round to the dossiers, finish args
  python3 tour.py landing              set up the landing panel: finals, originals, yardsticks
  python3 tour.py landing-tally OUT... rank the landing panel
"""

import json
import random
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

T = Path(__file__).resolve().parent
H = T.parent
PY = str(H / "venv/bin/python")
LENSES = ["feedback", "soul", "style", "system", "interaction", "type", "usability", "skeptic"]
LENS_WEIGHTS = {"soul": 1.5}
SHOTS = ["home", "ideas", "lost", "login", "chat", "status", "home-phone", "plans", "todo", "settings",
         "form", "general", "controls-field"]
HARNESS_FILES = ["colorlib.py", "theme.py", "metrics.py", "check.sh", "contact.py", "summary.py",
                 "diversity.py", "render.js", "README.md"]
KEEP = ["id", "name", "tagline", "concept", "companions", "decisions", "title", "floorsFailed", "measures",
        "strengths", "weaknesses", "revisions", "crit", "firstDraft", "secondDraft"]

# Where a main-tournament design's files live: the round it was born in.
def born(pid):
    return H / "rounds" / pid.split("-")[0]

LINEAGES = {
    "track": {
        "name": "the track series (Track Diagram)", "heat": "a", "carry": 2,
        "origins": ["r10-idea-3", "r13-mut-4"],
        "history": ["r7-idea-2", "r8-mut-2", "r9-idea-4", "r10-idea-3", "r11-mut-1", "r11-mut-4",
                    "r13-mut-1", "r13-mut-4"],
        "idea": "the family's week drawn as a signal box's illuminated track diagram: steel lines on slate "
                "boards with a lamp at each stop, drawn only where there is an order (Coming up, To do, the "
                "setup steps, the chat); the series began as Signal Box (round 7) and its mimic-line language",
    },
    "timetable": {
        "name": "Night Timetable", "heat": "a", "carry": 1, "origins": ["r10-wild-3"],
        "history": ["r10-wild-3"],
        "idea": "a station at night: Vera's conversation is the line the page hangs from (the question the "
                "first stop, the ways to start stops, 'Continue with Vera' the terminus), the chat a timetable "
                "with times in the margin, the Next up screen a dot-matrix departure board",
    },
    "pocket": {
        "name": "Pocket Timeline", "heat": "a", "carry": 1, "origins": ["r11-wild-1"],
        "history": ["r11-wild-1"],
        "idea": "Home ordered as time on one spine: NOW (the question), then NEXT (the tube), then Coming up, "
                "then LATER, with the lists beside it; every page strung along a timeline",
    },
    "figure": {
        "name": "Figure Ground", "heat": "b", "carry": 1, "origins": ["r10-wild-4"],
        "history": ["r10-wild-4", "r11-mut-3"],
        "idea": "the family's operator manual: every section led by a figure drawn from its own data (Status "
                "as the wiring of keys and connections with lit ports, the chat as a sequence diagram, To do's "
                "due dates on a line with NOW, Home's family tree to Vera to its counts)",
    },
    "console": {
        "name": "Flight Console", "heat": "b", "carry": 1, "origins": ["r11-wild-3"],
        "history": ["r11-wild-3", "r12-mut-3"],
        "idea": "a 1969 flight console: a readout strip across the top (TODAY, PLANS, TO DO, LATE, IDEAS), the "
                "coming weeks drawn as a flight plan of hops between stops, an annunciator of lit lamps on "
                "Status, a crew board of lamps on To do, a T-minus countdown for setup, a flight-log chat",
    },
    "switchboard": {
        "name": "Videotex Switchboard", "heat": "b", "carry": 1, "origins": ["r12-wmut-1"],
        "history": ["r11-wild-4", "r12-wmut-1", "r13-wmut-1"],
        "idea": "Home as the map of the whole service: every page a cell with its number, a lamp and a count "
                "(a videotex sommaire), the question typed on the glass under a cursor, each page opening on "
                "the same rack with its own green summary screen",
    },
}
HEATS = {"a": ["track", "timetable", "pocket"], "b": ["figure", "console", "switchboard"]}
# Designs whose best features the grafts may take (beside the other lineages' current designs).
DONORS = {
    "r7-idea-2": "Signal Box: the mimic-line track (the chat hung from Vera's mark, "
                 "the ring round the page icon, To do's timetable margin, the dot under the current page)",
    "r9-idea-4": "Signal Lines: Signal Box's rings and tracks on every page, and a page head that holds its "
                 "title, tabs and actions in one bracket",
    "r7-idea-1": "Galley Rack: the Coming up strips the owner said look far better than any other (a date "
                 "designator block, the title and time, a tabular 'in 3 days' facts column)",
    "r10-mut-4": "Flight Deck, Lit: a glass cockpit's colour code (cyan entered, bone data, amber caution, green "
                 "on), thin screwed faceplates, legends set into the breaks of fine demarcation lines",
    "r10-wild-2": "Bench Scope: the coming weeks drawn as glowing pulses on a scope, Ideas in XY mode",
    "r12-wild-4": "Single Quote: a title set with its figure in the section's colour and a stacked mono "
                  "legend, a command path with a blinking cursor, an LED on the current key",
    "r12-mut-2": "Long Persistence, Metered: today's spend as a phosphor moving-coil needle meter",
    "r13-wild-1": "Phosphor Blueprint: the footer as a drawing's title block, dimension lines for 'in 2 days', "
                  "a 24px baseline grid",
    "r13-wild-3": "Dessau Phosphor: a round phosphor screen holding each page's one live figure, four shapes "
                  "with four jobs and their legend in the footer, a huge scanlined glowing 'mind'",
    "r13-wild-4": "Grid Console: a lit spine down the gutter with a node at each section, section-coloured "
                  "trails, the only afterglow the judges could see",
    "r13-wild-2": "Signal Catalogue: a scope pulse per plan and LED countdown meters",
    "r9-rand-1": "Attract Mode: the power-on roll bar (the best tube behaviour of its round), keys and wells "
                 "with the clearest affordance",
    "r11-wild-2": "Night Gallery: a picture light hung over each monitor, wall labels",
}
YARDSTICKS = {"00-current": "today's page", "r13-idea-1": "Desk Terminal, Joined, the main tournament's leader after round 13"}
# The dice mutant's kind turns each round, so every lineage meets three different kinds.
KINDS = ["phosphor", "type", "graphics", "point"]


def load(p):
    return json.loads(Path(p).read_text())


def dump(p, x):
    Path(p).write_text(json.dumps(x, indent=1))


def result_of(out_file):
    raw = Path(out_file).read_text()
    return json.loads(raw[raw.find("{"):])["result"]


def make_dir(d):
    """A folder the harness runs in, like a round: its own copy of the scripts, today in place."""
    (d / "palettes").mkdir(parents=True, exist_ok=True)
    (d / "out").mkdir(exist_ok=True)
    (d / "variants").mkdir(exist_ok=True)
    for f in HARNESS_FILES:
        shutil.copy2(H / f, d / f)
    if not (d / "venv").exists():
        (d / "venv").symlink_to(H / "venv")
    shutil.copy2(H / "palettes" / "00-current.json", d / "palettes" / "00-current.json")
    if not (d / "out" / "00-current").exists():
        shutil.copytree(H / "out" / "00-current", d / "out" / "00-current")


def bring(pid, src, dst, with_out=True):
    """Copy a design (palette, own markup, and its render when it has one) from folder src to dst."""
    shutil.copy2(src / "palettes" / f"{pid}.json", dst / "palettes" / f"{pid}.json")
    if (src / "variants" / pid).exists() and not (dst / "variants" / pid).exists():
        shutil.copytree(src / "variants" / pid, dst / "variants" / pid)
    if with_out and (src / "out" / pid / "shots").exists() and not (dst / "out" / pid).exists():
        shutil.copytree(src / "out" / pid, dst / "out" / pid)


def needs_render(d, pid, same_day=False):
    """A render is stale when a shot is missing, a source changed after it, or (same_day) it was
    taken on another day: the demo's plans are dated, so "in 2 days" and Next up move with the
    clock, and every design judged in a round must show the same day."""
    shots = d / "out" / pid / "shots"
    if any(not (shots / f"{s}.png").exists() for s in SHOTS):
        return True
    if same_day:
        # The demo keeps the family's time (FAMILY_TZ in demo.env), so a day is theirs, not UTC's.
        import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Vancouver")
        today = datetime.datetime.now(tz).date()
        if any(datetime.datetime.fromtimestamp(p.stat().st_mtime, tz).date() != today for p in shots.glob("*.png")):
            return True
    oldest = min((p.stat().st_mtime for p in shots.glob("*.png")), default=0)
    sources = [d / "palettes" / f"{pid}.json", *(d / "variants" / pid).rglob("*")]
    return any(p.is_file() and p.stat().st_mtime > oldest for p in sources)


def render_all(jobs):
    """jobs: [(folder, id)], rendered four at a time (one per core)."""
    def one(job):
        d, pid = job
        run = subprocess.run(["./check.sh", f"palettes/{pid}.json"], cwd=d, capture_output=True, text=True)
        last = (run.stdout.strip().splitlines() or [run.stderr.strip()[-300:]])[-1]
        return d.name, pid, run.returncode, last
    with ThreadPoolExecutor(max_workers=4) as pool:
        for dn, pid, rc, last in pool.map(one, jobs):
            print("RENDERED" if rc == 0 else "RENDER FAILED", dn, pid, last)


def sheets(d):
    subprocess.run([PY, "contact.py"], cwd=d, check=True, capture_output=True)
    table = subprocess.run([PY, "summary.py"], cwd=d, check=True, capture_output=True, text=True).stdout
    (d / "stage").mkdir(exist_ok=True)
    (d / "stage" / "table.md").write_text(table)


# ---- The dossiers: every judge's words on every design of a lineage, in every round ---------------
def main_records():
    recs = {}
    for n in range(7, 14):
        f = H / "rounds" / f"r{n}" / "results.json"
        if f.exists():
            recs[n] = load(f)
    return recs


def lesson_lines(names):
    text = (H / "lessons.md").read_text()
    paras = re.split(r"\n(?=- |## )", text)
    return [p.strip() for p in paras if any(n in p for n in names)]


def dossier_entry(label, res, pid, extra=""):
    rk = res["ranking"]
    r = next((x for x in rk if x["id"] == pid), None)
    if not r:
        return ""
    design = next((x for x in res.get("designs", []) if x["id"] == pid), None)
    out = [f"### {pid} {r['name']}: {label}, #{rk.index(r) + 1} of {len(rk)}, mean {r['mean']} "
           f"(today's page {res.get('todayMean')}; in {r.get('top4', 0)} judges' top fours, {r.get('promise', 0)} promise votes){extra}"]
    if design:
        out.append(f"What it set out to be: {design.get('tagline', '')} {design.get('concept', '')}")
        if design.get("weaknesses"):
            out.append("Its designer's own weaknesses: " + " | ".join(design["weaknesses"]))
    for j in res["judges"]:
        s = next((x for x in j["scores"] if x["id"] == pid), None)
        if s:
            out.append(f"- [{j['lens']} {s['score']}] {s['why']}")
    fixes = [f"- {j['lens']}: {f['suggestion']}" for j in res["judges"] for f in j.get("fixes", []) if f["id"] == pid]
    if fixes:
        out.append("Fixes the judges asked for:")
        out += fixes
    return "\n".join(out) + "\n"


def build_dossiers():
    (T / "dossiers").mkdir(exist_ok=True)
    recs = main_records()
    names = {}
    for res in recs.values():
        for x in res["ranking"]:
            names.setdefault(x["id"], x["name"])
    for key, lin in LINEAGES.items():
        parts = [f"# Dossier: {lin['name']}\n\nThe idea: {lin['idea']}.\n\nEvery judge's words on every design of "
                 f"this lineage, in every round it was judged, oldest first (main tournament rounds, then the tour's). "
                 f"Scores compare best within their round; 'today's page' is the yardstick.\n"]
        for pid in lin["history"]:
            for n, res in recs.items():
                e = dossier_entry(f"main round {n}", res, pid)
                if e:
                    parts.append(e)
        ls = lesson_lines([names.get(p, p) for p in lin["history"]])
        if ls:
            parts.append("## What lessons.md recorded about this lineage\n\n" + "\n\n".join(ls) + "\n")
        (T / "dossiers" / f"{key}.md").write_text("\n".join(parts))
    parts = ["# Dossier: the donors\n\nDesigns whose best features the grafts may take. Every judge's words on "
             "each, in every round it was judged.\n"]
    for pid, what in DONORS.items():
        parts.append(f"## {pid}: {what}\n")
        for n, res in recs.items():
            e = dossier_entry(f"main round {n}", res, pid)
            if e:
                parts.append(e)
    (T / "dossiers" / "donors.md").write_text("\n".join(parts))
    print("dossiers:", sorted(p.name for p in (T / "dossiers").glob("*.md")))


def prep():
    T.mkdir(exist_ok=True)
    d = T / "donors"
    make_dir(d)
    everyone = [p for lin in LINEAGES.values() for p in lin["origins"]] + list(DONORS) + ["r13-idea-1"]
    for pid in everyone:
        bring(pid, born(pid), d, with_out=False)
    render_all([(d, pid) for pid in everyone if needs_render(d, pid)])
    sheets(d)
    build_dossiers()
    own = (H / "owner_judge.md").read_text()
    (T / "owner_judge.md").write_text(own + """
## On the side tour (after round 13)

The owner asked for a side tour: the designs a review of the whole history found passed over are
brought back and refined over three rounds. When it was set up, the owner added: "The track series,
in particular Track Diagram, deserves a second look." (Track Diagram, r10-idea-3: the family's week
drawn as a signal box's illuminated diagram, steel lines on slate boards with a lamp at each stop;
it won this lens in round 10 at 9.1.)
""")
    if not (T / "lessons.md").exists():
        (T / "lessons.md").write_text("# What the side tour's judges have learned\n\nThe side tour's own lessons, "
                                      "round by round. The main tournament's are in ../lessons.md.\n")


# ---- A round -------------------------------------------------------------------------------------
def heat_dir(n, h):
    return T / f"t{n}-{h}"


def mutant_for(key, lin_i, n, parent, rng):
    """The dice: the kind turns each round; the changes come from the tournament's own dice."""
    sys.path.insert(0, str(H))
    import seeds as dice
    kind = KINDS[(lin_i + n - 1) % len(KINDS)]
    pid, pname = parent
    if kind == "phosphor":
        return dice.phosphor_mutants([{"id": pid, "name": pname}], 1)[0]
    if kind == "type":
        return {"kind": "type", "parent": pid, "parentName": pname,
                "changes": [rng.choice(dice.TYPE_MAJOR), *rng.sample(dice.TYPE_MINOR, 2)]}
    if kind == "graphics":
        return {"kind": "graphics", "parent": pid, "parentName": pname,
                "changes": [rng.choice(dice.GRAPHICS_MAJOR), *rng.sample(dice.GRAPHICS_MINOR, rng.choice([1, 2]))]}
    return {"kind": "point", "parent": pid, "parentName": pname,
            "changes": [rng.choice(dice.COLOUR_MUTATIONS), rng.choice(dice.STRUCTURE_MUTATIONS), dice.type_change()]}


def open_(n):
    n = int(n)
    rd = T / f"t{n}"
    (rd / "stage").mkdir(parents=True, exist_ok=True)
    rng = random.Random()
    if n == 1:
        carried = {k: [{"id": p, "name": None, "src": str(T / "donors")} for p in lin["origins"]]
                   for k, lin in LINEAGES.items()}
    else:
        prev = load(T / f"t{n - 1}" / "results.json")
        carried = {k: [{"id": c["id"], "name": c["name"], "src": str(heat_dir(n - 1, LINEAGES[k]["heat"]))}
                       for c in prev["lineages"][k]["carried"]] for k in LINEAGES}
    for h in HEATS:
        d = heat_dir(n, h)
        make_dir(d)
        src_y = T / "donors" if n == 1 else heat_dir(n - 1, h)
        bring("r13-idea-1", src_y, d)
        for k in HEATS[h]:
            for c in carried[k]:
                bring(c["id"], Path(c["src"]), d)
                c["name"] = load(d / "palettes" / f"{c['id']}.json")["name"]
    lineages = {}
    for i, (k, lin) in enumerate(LINEAGES.items()):
        cs = carried[k]
        briefs = [{"slot": "refine", "parent": cs[0]["id"], "parentName": cs[0]["name"]}]
        if k == "track":
            if n == 1:
                briefs.append({"slot": "revival", "parent": "r10-idea-3", "parentName": "Track Diagram"})
            elif len(cs) > 1:
                briefs.append({"slot": "refine2", "parent": cs[1]["id"], "parentName": cs[1]["name"]})
        briefs.append({"slot": "graft", "parent": cs[0]["id"], "parentName": cs[0]["name"]})
        # The dice mutant takes the lineage's best; for the track series in round 1, Track Diagram itself.
        mp = next((c for c in cs if c["id"] == "r10-idea-3"), cs[0]) if (k == "track" and n == 1) else cs[0]
        mut = mutant_for(k, i, n, (mp["id"], mp["name"]), rng)
        lineages[k] = {"name": lin["name"], "idea": lin["idea"], "heat": lin["heat"], "dir": str(heat_dir(n, lin["heat"])),
                       "carried": [{"id": c["id"], "name": c["name"]} for c in cs], "briefs": briefs,
                       "mutant": {**mut, "id": f"t{n}-{k}-mut"},
                       "entrants": [f"t{n}-{k}-{b['slot']}" for b in briefs] + [f"t{n}-{k}-mut"]}
    args = {"round": f"t{n}", "roundNo": n, "lineages": lineages,
            "heats": {h: {"dir": str(heat_dir(n, h)), "lineages": ks} for h, ks in HEATS.items()},
            "yardsticks": YARDSTICKS, "donors": DONORS, "tour": str(T)}
    dump(rd / "args.json", args)
    # Carried designs without a render (round 1's come from the donors folder, rendered at prep).
    jobs = [(heat_dir(n, h), c["id"]) for h in HEATS for k in HEATS[h] for c in carried[k]
            if needs_render(heat_dir(n, h), c["id"])]
    jobs += [(heat_dir(n, h), "r13-idea-1") for h in HEATS if needs_render(heat_dir(n, h), "r13-idea-1")]
    render_all(jobs)
    # The design stages: one workflow per lineage (its planner and briefs, and its mutant), and the
    # track series' mutant on its own, since that lineage has three briefs.
    for old in (rd / "stage").glob("design-*.json"):
        old.unlink()
    files = []
    everyone = {k: {"name": l["name"], "idea": l["idea"], "dir": l["dir"], "carried": l["carried"]} for k, l in lineages.items()}
    for k, lin in lineages.items():
        base = {"stage": "design", "round": f"t{n}", "roundNo": n, "key": k,
                "lin": {x: lin[x] for x in ("name", "dir", "carried", "briefs", "mutant")} | {"idea": lin["idea"]}}
        files.append({**base, "plan": True, "mutant": False})
        files.append({**base, "plan": False, "mutant": True})
    for i, f in enumerate(files, 1):
        dump(rd / "stage" / f"design-{i}.json", f)
        print(rd / "stage" / f"design-{i}.json", f["key"], "plan" if f["plan"] else "", "mutant" if f["mutant"] else "")
    for k, lin in lineages.items():
        m = lin["mutant"]
        print(f"{k}: carried {[c['id'] for c in lin['carried']]}; briefs {[b['slot'] for b in lin['briefs']]}; "
              f"mutant {m['kind']} of {m['parent']}: {' | '.join(m['changes'])}")


def prepare(n, *outs):
    n = int(n)
    rd = T / f"t{n}"
    a = load(rd / "args.json")
    designs = {}
    for f in [rd / "stage" / "designs.json"]:
        if f.exists():
            for x in load(f):
                designs[x["id"]] = x
    for o in outs:
        res = result_of(o)
        for x in res.get("designs", []):
            designs[x["id"]] = {k: x[k] for k in KEEP if k in x}
        for k, plan in (res.get("plans") or {}).items():
            dump(rd / "stage" / f"plan-{k}.json", plan)
    dump(rd / "stage" / "designs.json", list(designs.values()))
    jobs = []
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        ids = sorted(p.stem for p in (d / "palettes").glob("*.json"))
        missing = [e for k in heat["lineages"] for e in a["lineages"][k]["entrants"] if e not in ids]
        if missing:
            print("NO PALETTE FOR", ", ".join(missing))
        # Today's page first: it is the words baseline the others' checks compare with.
        if needs_render(d, "00-current", same_day=True):
            if (d / "out" / "00-current").is_symlink():
                (d / "out" / "00-current").unlink()
            render_all([(d, "00-current")])
        jobs += [(d, pid) for pid in ids if pid != "00-current" and needs_render(d, pid, same_day=True)]
    render_all(jobs)

    def removed(d, pid):
        f = d / "variants" / pid / "removed.txt"
        text = f.read_text().strip() if f.exists() else ""
        return f"\nRemoved from the page (weigh what the family loses against what the page gains): {text}" if text else ""

    kinds = {"refine": "REFINEMENT (its own judges' fixes)", "refine2": "REFINEMENT of the lineage's second carried design",
             "graft": "GRAFT (the best features of other lineages and donor designs, made its own)",
             "revival": "REVIVAL (the track series' first line language, Signal Box's, on Track Diagram)"}
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        sheets(d)
        notes = ["# The candidates of this heat\n\nYardsticks (score them, but they are not candidates): "
                 "00-current (today's page) and r13-idea-1 (Desk Terminal, Joined: the main tournament's leader after "
                 "round 13, for reference).\n"]
        for k in heat["lineages"]:
            lin = a["lineages"][k]
            notes.append(f"## Lineage: {lin['name']}\nThe idea: {lin['idea']}.\n")
            for c in lin["carried"]:
                x = designs.get(c["id"]) or {}
                prior = f"carried as the lineage's best so far" if n > 1 else "brought back as it was when the tournament passed it over"
                notes.append(f"### {c['id']} {c['name']} (carried: {prior})\n{x.get('tagline', '')} {x.get('concept', '')}"
                             + (f"\nTitle: {x['title']}" if x.get('title') else "") + removed(d, c['id']))
            for b in lin["briefs"]:
                pid = f"t{n}-{k}-{b['slot']}"
                x = designs.get(pid)
                if not x:
                    continue
                notes.append(f"### {pid} {x['name']} ({kinds[b['slot']]} of {b['parent']})\n{x['tagline']}\nTitle: {x.get('title', '(not given)')}\nConcept: {x['concept']}\n"
                             f"Companions: {x['companions']}\nDesigner's own weaknesses: {' | '.join(x['weaknesses'])}{removed(d, pid)}")
            m = lin["mutant"]
            x = designs.get(m["id"])
            if x:
                notes.append(f"### {m['id']} {x['name']} (DICE MUTANT, {m['kind']}, of {m['parent']}: {'; '.join(m['changes'])})\n"
                             f"{x['tagline']}\nTitle: {x.get('title', 'as its parent')}\nConcept: {x['concept']}\nDesigner's own weaknesses: {' | '.join(x['weaknesses'])}{removed(d, m['id'])}")
        (d / "stage" / "candidates.md").write_text("\n\n".join(notes) + "\n")
    for old in (rd / "stage").glob("judge-*.json"):
        old.unlink()
    heats = {}
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        present = {p.stem for p in (d / "palettes").glob("*.json")}
        lins = []
        for k in heat["lineages"]:
            lin = a["lineages"][k]
            ids = [c["id"] for c in lin["carried"]] + [e for e in lin["entrants"] if e in present]
            lins.append({"name": lin["name"], "idea": lin["idea"], "ids": ids})
        heats[h] = {"dir": heat["dir"], "lineages": lins,
                    "ids": ["00-current", "r13-idea-1"] + [i for x in lins for i in x["ids"]]}
    for i, lens in enumerate(LENSES, 1):
        dump(rd / "stage" / f"judge-{i}.json", {"stage": "judge", "round": f"t{n}", "roundNo": n, "lens": lens, "heats": heats})
        print(rd / "stage" / f"judge-{i}.json", lens, {h: len(x["ids"]) for h, x in heats.items()})


def rank_heat(judges, ids, names):
    t = {pid: {"id": pid, "name": names.get(pid, pid), "total": 0, "weights": 0, "plain": 0, "n": 0, "top4": 0,
               "promise": 0, "byLens": {}} for pid in ids}
    for j in judges:
        w = LENS_WEIGHTS.get(j["lens"], 1)
        for s in j["scores"]:
            if s["id"] in t:
                x = t[s["id"]]
                x["total"] += s["score"] * w
                x["weights"] += w
                x["plain"] += s["score"]
                x["n"] += 1
                x["byLens"][j["lens"]] = s["score"]
        for pid in j.get("top4", []):
            if pid in t:
                t[pid]["top4"] += 1
        for pid in j.get("promise", []):
            if pid in t:
                t[pid]["promise"] += 1
    rk = [{**x, "mean": round(x["total"] / x["weights"], 2) if x["n"] else 0,
           "plainMean": round(x["plain"] / x["n"], 2) if x["n"] else 0} for x in t.values()]
    rk.sort(key=lambda x: (-x["mean"], -x["top4"], -x["byLens"].get("skeptic", 0)))
    return rk


def distance(d, a, b):
    run = subprocess.run([PY, "diversity.py", "between", str(d), a, str(d), b], cwd=d, capture_output=True, text=True)
    try:
        return json.loads(run.stdout)[0]
    except Exception:
        return 99


def tally(n, *outs):
    n = int(n)
    rd = T / f"t{n}"
    a = load(rd / "args.json")
    designs = {x["id"]: x for x in load(rd / "stage" / "designs.json")}
    judged = {}  # heat -> lens -> record
    for o in outs:
        for j in result_of(o).get("judges", []):
            judged.setdefault(j["heat"], {})[j["lens"]] = j
    results = {"round": f"t{n}", "heats": {}, "lineages": {}, "judges": {}}
    for h, heat in a["heats"].items():
        d = Path(heat["dir"])
        js = list(judged.get(h, {}).values())
        names = {pid: load(d / "palettes" / f"{pid}.json")["name"]
                 for pid in [p.stem for p in (d / "palettes").glob("*.json")]}
        ids = list(names)
        rk = rank_heat(js, ids, names)
        lineage_of = {}
        for k in heat["lineages"]:
            lin = a["lineages"][k]
            for c in lin["carried"]:
                lineage_of[c["id"]] = k
            for e in lin["entrants"]:
                lineage_of[e] = k
        for x in rk:
            x["lineage"] = lineage_of.get(x["id"], "yardstick")
        results["heats"][h] = {"ranking": rk, "judges": [j["lens"] for j in js],
                               "today": next((x["mean"] for x in rk if x["id"] == "00-current"), None),
                               "leader": next((x["mean"] for x in rk if x["id"] == "r13-idea-1"), None)}
        results["judges"][h] = [{"lens": j["lens"], "notes": j["notes"], "top4": j["top4"], "promise": j.get("promise", []),
                                 "scores": j["scores"], "fixes": j["fixes"], "titles": j.get("titles")} for j in js]
        print(f"\nHEAT {h}: judged by {', '.join(j['lens'] for j in js)} ({len(js)} of 8); "
              f"today {results['heats'][h]['today']}, Desk Terminal, Joined {results['heats'][h]['leader']}")
        for x in rk:
            print(f"  {x['id']:22} {x['name'][:30]:30} {x['mean']:5} (plain {x['plainMean']}) n {x['n']} top4 {x['top4']} "
                  f"promise {x['promise']}  {x['lineage']}")
        for k in heat["lineages"]:
            lin = a["lineages"][k]
            mine = [x for x in rk if x["lineage"] == k and designs.get(x["id"], {}).get("floorsFailed", 0) == 0
                    or (x["lineage"] == k and x["id"] in {c["id"] for c in lin["carried"]})]
            chosen = [mine[0]]
            if LINEAGES[k]["carry"] > 1:
                for x in mine[1:]:
                    if distance(d, x["id"], chosen[0]["id"]) >= 1.5:
                        chosen.append(x)
                        break
                else:
                    if len(mine) > 1:
                        chosen.append(mine[1])
            results["lineages"][k] = {
                "carried": [{"id": x["id"], "name": x["name"], "mean": x["mean"]} for x in chosen],
                "ranking": [{"id": x["id"], "name": x["name"], "mean": x["mean"], "top4": x["top4"], "promise": x["promise"]}
                            for x in rk if x["lineage"] == k],
                "best": chosen[0]["mean"], "today": results["heats"][h]["today"], "leader": results["heats"][h]["leader"]}
            print(f"  -> {k} carries {[(x['id'], x['mean']) for x in chosen]}")
    dump(rd / "results.json", results)
    # Append the round's words to each lineage's dossier (and the donors' stay as they were).
    for h, heat in a["heats"].items():
        res = {"ranking": results["heats"][h]["ranking"], "judges": results["judges"][h],
               "todayMean": results["heats"][h]["today"], "designs": list(designs.values())}
        for k in heat["lineages"]:
            lin = a["lineages"][k]
            parts = [f"\n## Tour round {n} (heat {h}; Desk Terminal, Joined scored {results['heats'][h]['leader']} here)\n"]
            for pid in [c["id"] for c in lin["carried"]] + lin["entrants"]:
                kind = next((b["slot"] for b in lin["briefs"] if f"t{n}-{k}-{b['slot']}" == pid), None)
                extra = (f"; the {kind} of {next(b['parent'] for b in lin['briefs'] if b['slot'] == kind)}" if kind
                         else f"; the dice mutant ({lin['mutant']['kind']}: {'; '.join(lin['mutant']['changes'])})" if pid == lin["mutant"]["id"]
                         else "; carried")
                parts.append(dossier_entry(f"tour round {n}", res, pid, extra))
            ts = [f"- {j['lens']}: {j['titles']}" for j in results["judges"][h] if j.get("titles")]
            if ts:
                parts.append("What the judges said of this heat's greeting titles:\n" + "\n".join(ts) + "\n")
            with open(T / "dossiers" / f"{k}.md", "a") as f:
                f.write("\n".join(parts))
    write_titles()
    dump(rd / "stage" / "finish.json", {"stage": "finish", "round": f"t{n}", "roundNo": n})
    print(rd / "results.json")


def write_titles():
    """Every greeting title the tour has tried, which designs carried it, how they scored, and what
    the judges said of the titles, round by round: the planners' starting point for the next."""
    rows, notes = {}, []
    for rd in sorted(T.glob("t[0-9]")):
        if not (rd / "results.json").exists():
            continue
        res = load(rd / "results.json")
        means = {x["id"]: x["mean"] for h in res["heats"].values() for x in h["ranking"]}
        for x in load(rd / "stage" / "designs.json"):
            t = (x.get("title") or "").strip()
            if not t:
                continue
            t = t.replace("’", "'").replace("“", '"').replace("”", '"').replace("‘", "'").lstrip('"\' ')
            m = re.match(r"(.+?[?.!])(?=[\"'\s]|$)", t)
            key = (m.group(1) if m else t[:60]).strip('"\' ')
            rows.setdefault(key, []).append(f"{x['id']} ({rd.name}, {means.get(x['id'], '?')})")
        for h, js in res["judges"].items():
            for j in js:
                if j.get("titles"):
                    notes.append(f"- {rd.name} heat {h}, {j['lens']}: {j['titles']}")
    parts = ["# The greeting's titles the tour has tried\n\nThe owner: \"I don't really like the title of 'What's on your "
             "mind?' as it really doesn't relate that well to the job the application is trying to do. Please iterate on "
             "better titles as well.\"\n\n## Titles, with the designs that carried them (round, mean score)\n"]
    parts += [f"- **{k}**: {', '.join(v)}" for k, v in sorted(rows.items(), key=lambda kv: -len(kv[1]))]
    parts.append("\n## What the judges said of the titles\n")
    parts += notes
    (T / "titles.md").write_text("\n".join(parts) + "\n")
    print("titles:", len(rows), "tried;", len(notes), "judges' notes")


# ---- Landing: every lineage's final beside where it started, in one panel ------------------------
def landing():
    d = T / "landing"
    make_dir(d)
    last = max(int(p.name[1:]) for p in T.glob("t[0-9]") if (p / "results.json").exists())
    res = load(T / f"t{last}" / "results.json")
    finals = []
    for k, lin in LINEAGES.items():
        for c in res["lineages"][k]["carried"]:
            bring(c["id"], heat_dir(last, lin["heat"]), d)
            finals.append(c["id"])
    origins = [p for lin in LINEAGES.values() for p in lin["origins"]]
    for pid in origins + ["r13-idea-1"]:
        bring(pid, T / "donors", d)
    if needs_render(d, "00-current", same_day=True):
        render_all([(d, "00-current")])
    render_all([(d, pid) for pid in finals + origins + ["r13-idea-1"] if needs_render(d, pid, same_day=True)])
    sheets(d)
    dump(d / "stage" / "landing.json", {"finals": finals, "origins": origins, "from": f"t{last}"})
    which = []
    for k, lin in LINEAGES.items():
        fs = [c["id"] for c in res["lineages"][k]["carried"]]
        which.append(f"{lin['name']}: final {', '.join(fs)}, origin {', '.join(lin['origins'])}")
    names = {p.stem: load(p)["name"] for p in (d / "palettes").glob("*.json")}
    notes = ["# The landing panel\n\nYardsticks: 00-current (today's page) and r13-idea-1 (Desk Terminal, Joined, the main "
             "tournament's leader after round 13).\n"]
    designs = {}
    for f in T.glob("t[0-9]/stage/designs.json"):
        for x in load(f):
            designs[x["id"]] = x
    for k, lin in LINEAGES.items():
        notes.append(f"## {lin['name']}\nThe idea: {lin['idea']}.\n")
        for pid in [c["id"] for c in res["lineages"][k]["carried"]]:
            x = designs.get(pid, {})
            notes.append(f"### {pid} {names.get(pid)} (FINAL, after the tour)\n{x.get('tagline', '')} {x.get('concept', '')}"
                         + (f"\nTitle: {x['title']}" if x.get('title') else ""))
        for pid in lin["origins"]:
            notes.append(f"### {pid} {names.get(pid)} (ORIGIN, as the tournament passed it over)")
    (d / "stage" / "candidates.md").write_text("\n\n".join(notes) + "\n")
    ids = ["00-current", "r13-idea-1"] + finals + origins
    groups = [LENSES[i:i + 2] for i in range(0, len(LENSES), 2)]
    for i, g in enumerate(groups, 1):
        dump(d / "stage" / f"judge-{i}.json", {"stage": "landing", "lenses": g, "finals": finals, "origins": origins,
                                               "ids": ids, "n": len(ids), "lineages": "; ".join(which)})
    print("landing ready:", finals, origins)


def landing_tally(*outs):
    d = T / "landing"
    js = [j for o in outs for j in result_of(o).get("judges", [])]
    names = {p.stem: load(p)["name"] for p in (d / "palettes").glob("*.json")}
    rk = rank_heat(js, list(names), names)
    info = load(d / "stage" / "landing.json")
    dump(d / "results.json", {"ranking": rk, "judges": js, **info})
    for x in rk:
        tag = "FINAL" if x["id"] in info["finals"] else "origin" if x["id"] in info["origins"] else "yardstick"
        print(f"  {x['id']:22} {x['name'][:30]:30} {x['mean']:5} (plain {x['plainMean']}) top4 {x['top4']} promise {x['promise']} {tag}")


SCOUT_GROUPS = [[1, 2], [3, 4], [5, 6], [7], [8], [9], [10], [11], [12], [13]]


def ledger():
    (T / "stage").mkdir(exist_ok=True)
    for old in (T / "stage").glob("ledger-*.json"):
        old.unlink()
    for i in range(0, len(SCOUT_GROUPS), 2):
        f = T / "stage" / f"ledger-{i // 2 + 1}.json"
        dump(f, {"stage": "ledger", "groups": [{"rounds": g} for g in SCOUT_GROUPS[i:i + 2]]})
        print(f)


KEYS = {"track": ["track", "signal box", "track diagram"], "timetable": ["timetable"], "pocket": ["pocket"],
        "figure": ["figure"], "console": ["console", "flight console"], "switchboard": ["switchboard", "videotex"]}


def ledger_write(*outs):
    feats = [x for o in outs for x in result_of(o).get("features", [])]
    ranks = {}
    for n in range(1, 14):
        res = load(H / ("round1" if n == 1 else f"rounds/r{n}") / "results.json")
        rk = [r for r in res["ranking"] if r["id"] != "00-current"]
        ranks[n] = {r["id"]: (i + 1, len(rk)) for i, r in enumerate(rk)}

    def low(x):
        pos = ranks.get(x.get("round"), {}).get(x["source"])
        return bool(pos and pos[0] > pos[1] / 2)
    feats.sort(key=lambda x: (not low(x), x["kind"], x.get("round", 0), x["source"]))
    for i, x in enumerate(feats, 1):
        x["n"] = f"L{i:03d}"
        x["gem"] = low(x)
    dump(T / "ledger.json", feats)

    def entry(x):
        return (f"### {x['n']} {x['feature']} ({x['kind']}{', GEM' if x['gem'] else ''})\nFrom **{x['source']} {x['sourceName']}**, "
                f"round {x['round']} ({x['standing']}).\n- What: {x['what']}\n- Files: {x['files']}\n- Shot: {x['shot']}"
                f"\n- Praise: {x['praise']}\n- Caveats: {x['caveats']}\n- Suits: {x['suits']}\n")
    gems = [x for x in feats if x["gem"]]
    head = (f"{len(feats)} features from {len({x['source'] for x in feats})} designs of the main tournament's thirteen rounds, "
            "found by scouts who looked at every design's pages and read every judge. GEMS come from designs that finished "
            f"in the lower half of their round ({len(gems)}): the small good ideas lost with their package. Each lineage's "
            "graft takes at least one gem every round. A design's files and screenshots are in tour/gallery/index.json.")
    (T / "ledger.md").write_text("# The feature ledger, in full\n\n" + head + " Find an entry by its number (L001...).\n\n"
                                 + "\n".join(entry(x) for x in feats))
    idx = ["# The feature ledger: index\n\n" + head + " One line per feature; the full entry (files, shot, praise, caveats) "
           "is in ledger.md under its number, and each lineage's shortlist in ledger-for-<lineage>.md.\n"]
    for part, xs in (("Gems (lower half)", gems), ("Upper half", [x for x in feats if not x["gem"]])):
        idx.append(f"\n## {part}\n")
        kind = None
        for x in xs:
            if x["kind"] != kind:
                kind = x["kind"]
                idx.append(f"\n### {kind}\n")
            what = x["what"].split(". ")[0][:220]
            idx.append(f"- {x['n']} **{x['feature']}**, {x['source']} {x['sourceName']} (r{x['round']}, {x['standing']}): {what}")
    (T / "ledger-index.md").write_text("\n".join(idx) + "\n")
    for k, words in KEYS.items():
        mine = [x for x in feats if any(w in x["suits"].lower() for w in words)]
        (T / f"ledger-for-{k}.md").write_text(
            f"# Ledger shortlist for {LINEAGES[k]['name']}\n\nThe {len(mine)} features the scouts said would suit this lineage "
            f"({sum(1 for x in mine if x['gem'])} of them gems), in full. The whole menu is ledger-index.md.\n\n"
            + "\n".join(entry(x) for x in mine))
        print(k, len(mine), "suited,", sum(1 for x in mine if x["gem"]), "gems")
    print(len(feats), "features,", len(gems), "gems")


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    {"prep": prep, "open": open_, "prepare": prepare, "tally": tally, "landing": landing,
     "landing-tally": landing_tally, "dossiers": build_dossiers,
     "ledger": ledger, "ledger-write": ledger_write}[cmd](*rest)
