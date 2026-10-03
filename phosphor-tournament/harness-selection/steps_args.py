"""Generation 1 of the natural-selection tournament (round 14): each host spawns children that each
make ONE small change: two grafts of a feature the 14b winners found (informed mutation) and one
random tweak rolled from tweaks.json (blind mutation). The parents stay in the field as the bar.
Writes rounds/r14/args.json (the earlier setups are kept as args.refine.json and args.cross.json)."""
import json, random, shutil
from pathlib import Path

H = Path(__file__).parent
R13, R14 = H / "rounds/r13", H / "rounds/r14"
res = json.loads((R13 / "results.json").read_text())
byid = {e["id"]: e for e in res["ranking"]}
tweaks = json.loads((H / "tweaks.json").read_text())
args = json.loads((R14 / "args.refine.json").read_text())

# feature -> (slot, text, donors)
GRAFTS = {
 "lit-line": ("signal", "ONE LIT LINE: a single lit line from the screen (the tube, the typed question) down into the list's 'now' marker, a real wire from the live thing to the next thing due.", ["x14b-manual-cross", "x14b-desk-cross"]),
 "count-strip": ("head", "A COUNT STRIP under the page head, 'Today · Plans 4 · To do 4 · Late 3 · Ideas 12', each count a link to its page.", ["x14b-waypoint-cross"]),
 "dial": ("figure", "A ROUND DIAL THAT SHOWS REAL DAYS: this week's days at their true positions with today lit. Every mark must mean something (the skeptic faulted a dial whose later days sat at meaningless clock positions).", ["x14b-manual-cross", "x14b-dessau-cross"]),
 "day-numerals": ("list", "LARGE DAY NUMBERS in the list rows, with the month and weekday stacked beside them.", ["x14b-desk-cross"]),
 "type-pairing": ("type", "FOLIO'S TYPE PAIRING: serif headings, light serif figures and small-caps units.", ["x14b-folio-cross"]),
 "rule-end": ("rule", "A SECTION-HEAD RULE WITH AN END MARK on every page.", ["x14b-trued-cross"]),
 "big-figure": ("figure", "ONE BIG FIGURE LEADING EACH SECTION (the section's count or its next date, set large).", ["x14b-quote-cross"]),
 "status-line": ("glass", "A STATUS LINE ON THE GLASS: '4 plans · 3 late · Vera is listening', in the machine's words.", ["x14b-desk-cross"]),
}
DONOR_NAME = {"x14b-manual-cross": "Lit Manual, Dialled", "x14b-waypoint-cross": "Waypoint, Patched", "x14b-trued-cross": "Trued, Yard Lit",
              "x14b-folio-cross": "Folio, Fastext", "x14b-desk-cross": "Desk Terminal, Wired", "x14b-dessau-cross": "Dessau, Dialled",
              "x14b-quote-cross": "Quote Board, Lit"}
HOSTS = {  # host -> its two informed grafts
 "r13-mut-2": ["lit-line", "day-numerals"],
 "r13-mut-4": ["dial", "type-pairing"],
 "r11-idea-2": ["count-strip", "rule-end"],
 "r13-wild-1": ["rule-end", "status-line"],
 "r13-wild-4": ["lit-line", "type-pairing"],
 "r13-wild-2": ["day-numerals", "big-figure"],
}
FIXES = ("the round-13 judges' fixes for it are in {d}/parent-fixes/{p}.md (read them only if the change touches what they say)")

if not (R14 / "args.cross.json").exists() and (R14 / "args.json").exists():
    shutil.copy(R14 / "args.json", R14 / "args.cross.json")
mutants = []
for host, grafts in HOSTS.items():
    e = byid[host]
    rng = random.Random(host)
    # three children per host, each changing a few slots, one change per slot: A and B take one informed
    # graft each and two blind tweaks; C is three blind tweaks. The slots of a child never repeat.
    plans = [[grafts[0]], [grafts[1]], []]
    for n, gs in enumerate(plans):
        changes, used = [], set()
        for g in gs:
            slot, text, donors = GRAFTS[g]
            d = donors[0]
            changes.append({"slot": slot, "text": text, "donor": d, "donorName": DONOR_NAME[d]})
            used.add(slot)
        while len(changes) < 3:
            slot = rng.choice([x for x in tweaks if x not in used])
            used.add(slot)
            changes.append({"slot": slot, "text": rng.choice(tweaks[slot])})
        mutants.append({"kind": "step", "parent": host, "parentName": e["name"], "parentMean": e["mean"], "changes": changes})

def entry(pid, why):
    e = byid[pid]
    return {"id": pid, "name": e["name"], "summary": f"Round 13: {e['mean']} by score, {e['top4']} top-four votes, {e['promise']} promise votes. {why}"}
wild = [h for h in HOSTS if h.startswith("r13-wild")]
args["wildCarried"] = [entry(h, "Entered unchanged: the parent of three one-change steps, the bar they are measured against.") for h in wild]
args["carried"] = [entry("r13-idea-1", "The round-13 winner, entered unchanged as the bar for the whole field.")] + [
    entry(h, "Entered unchanged: the parent of three one-change steps, the bar they are measured against.") for h in HOSTS if h not in wild]
args.update({"mutants": mutants, "seeds": [], "wild": [], "wildMutants": [], "nInformed": 0, "mode": "selection", "panel": "screen"})
(R14 / "args.json").write_text(json.dumps(args, indent=1))
for m in mutants:
    print(m["parent"], [(c["slot"], "graft" if c.get("donor") else "tweak") for c in m["changes"]])
