"""Round 14 as a feature-crossing round: every round-13 design takes on the best features of the
crossing rounds (14a/14b). Writes rounds/r14/args.json (the refine setup is kept beside it as
args.refine.json), puts each parent's palette and markup in r14 and one fixes file per parent."""
import json, shutil, re
from pathlib import Path

H = Path(__file__).parent
R13, R14 = H / "rounds/r13", H / "rounds/r14"
res = json.loads((R13 / "results.json").read_text())
args = json.loads((R14 / "args.json").read_text())
if not (R14 / "args.refine.json").exists():
    shutil.copy(R14 / "args.json", R14 / "args.refine.json")
    args = json.loads((R14 / "args.refine.json").read_text())
args = json.loads((R14 / "args.refine.json").read_text())

FEATURES = {
 1: "ONE LIT LINE: a single lit line from the screen (the tube, the typed question) down into the list's 'now' marker, a real wire from the live thing to the next thing due. The judges praised it most (Desk's patch lead; Lit Manual's dial-to-now wire was the best version).",
 2: "A COUNT STRIP under the page head, 'Today · Plans 4 · To do 4 · Late 3 · Ideas 12', each count a link to its page (from Waypoint; Lit Manual, Dessau and Folio took it too).",
 3: "A ROUND DIAL THAT SHOWS REAL DAYS: this week's days at their true positions with today lit (Lit Manual, Dessau). Trap: the skeptic found Lit Manual's dial set later days at clock positions that mean nothing; every mark must mean something.",
 4: "LARGE DAY NUMBERS with the month and weekday stacked beside them, as in Desk's Coming up list (the type judge called it the best list typesetting in the field).",
 5: "FOLIO'S TYPE PAIRING: serif headings, light serif figures and small-caps units (the type judge's top pick).",
 6: "A SECTION-HEAD RULE WITH AN END MARK on every page, from Trued (the system judge's top pick).",
 7: "ONE BIG FIGURE LEADING EACH SECTION, from Listing (the skeptic: 'the standard to adopt').",
 8: "A STATUS LINE ON THE GLASS: '4 plans · 3 late · Vera is listening' (a line of facts, in the machine's words).",
 9: "SMALL PIECES: Switchboard's row of household pages, and Waypoint's Whose filter on To do (both must really work; a control that looks switched on and does nothing is the worst error).",
}
EVERY = ("Fixes asked of many designs: keep one lamp lit in the page footer at rest; drop footer legend strips; "
         "bring every control up to 44px; give The kids' wishes real rows; put Desk's title above Next up; "
         "the page's title line may say 'Tell Vera what to plan.' (the judges' suggested fix); and every "
         "filter, sort or toggle you draw must really work.")

DONORS = {  # the crossing rounds' final heat: id -> (name, score, what it is the donor of)
 "x14b-manual-cross": ("Lit Manual, Dialled", 8.05, "the dial-to-now wire and the real-days dial"),
 "x14b-waypoint-cross": ("Waypoint, Patched", 7.99, "the count strip and the Whose filter"),
 "x14b-trued-cross": ("Trued, Yard Lit", 7.96, "the section-head rule with its end mark"),
 "x14b-folio-cross": ("Folio, Fastext", 7.90, "the type pairing: serif heads, light serif figures, small caps"),
 "x14b-desk-cross": ("Desk Terminal, Wired", 7.89, "the patch lead into now and the large day numbers"),
 "x14b-dessau-cross": ("Dessau, Dialled", 7.86, "the dial and the count strip on Bauhaus posters"),
 "x14b-sill-cross": ("Sill Line, Wired", 7.75, "a wired sill line (near-twin of Trued)"),
 "x14b-quote-cross": ("Quote Board, Lit", 7.58, "titles with their figures, lit"),
}
SEE = {1: ["x14b-manual-cross", "x14b-desk-cross"], 2: ["x14b-waypoint-cross"], 3: ["x14b-manual-cross", "x14b-dessau-cross"],
       4: ["x14b-desk-cross"], 5: ["x14b-folio-cross"], 6: ["x14b-trued-cross"], 7: ["x14b-quote-cross"], 8: ["x14b-desk-cross"],
       9: ["x14b-waypoint-cross"]}
for k, v in SEE.items():
    FEATURES[k] += " (donor: " + ", ".join(v) + "; translate it, never copy its colours or its page)"
# The limited run: the round-13 designs the side-quest never crossed that have the most to gain,
# each with the features that fit it (feature numbers above).
HOSTS = {
 "r13-mut-2": [1, 2, 4, 6, 8],   # Desk Terminal, Mapped: keeps its four signals and Ideas map
 "r13-mut-4": [1, 2, 3, 5, 7],   # Track Diagram Aglow: the owner's judge's first pick; needs page-scale change
 "r11-idea-2": [1, 2, 4, 5, 6],  # Long Persistence: a lit instrument per page
 "r13-wild-1": [2, 3, 5, 6, 8],  # Phosphor Blueprint: drafting sheets, title blocks
 "r13-wild-4": [1, 2, 3, 5, 6],  # Grid Console: cells and a lit rail
 "r13-wild-2": [2, 4, 5, 6, 7],  # Signal Catalogue: brass tags and catalogue cards
}
ranking = [e for e in res["ranking"] if e["id"] in HOSTS]
(R14 / "palettes").mkdir(exist_ok=True); (R14 / "variants").mkdir(exist_ok=True)
(R14 / "parent-fixes").mkdir(exist_ok=True)
mutants = []
for i, e in enumerate(ranking):
    pid = e["id"]
    if not (R14 / "palettes" / f"{pid}.json").exists():
        shutil.copy(R13 / "palettes" / f"{pid}.json", R14 / "palettes" / f"{pid}.json")
    if (R13 / "variants" / pid).exists() and not (R14 / "variants" / pid).exists():
        shutil.copytree(R13 / "variants" / pid, R14 / "variants" / pid)
    fx = []
    for j in res["judges"]:
        for f in j.get("fixes", []):
            if f["id"] == pid:
                fx.append(f"## {j['lens']}\n{f['suggestion']}")
    (R14 / "parent-fixes" / f"{pid}.md").write_text(
        f"# Round 13's judges' fixes for {pid} ({e['name']}, {e['mean']})\n\n" + "\n\n".join(fx) + "\n")
    ids = HOSTS[pid]
    mutants.append({
        "kind": "features", "parent": pid, "parentName": e["name"], "parentMean": e["mean"],
        "todayMean": res["todayMean"],
        "parentFixes": f"the round-13 judges' fixes for it are in {R14}/parent-fixes/{pid}.md; read them. {EVERY}",
        "donors": sorted({d for k in ids for d in SEE.get(k, [])}),
        "changes": [FEATURES[k] for k in ids]})
byid = {e["id"]: e for e in res["ranking"]}
def entry(pid, why):
    e = byid[pid]
    return {"id": pid, "name": e["name"], "summary": f"Round 13: {e['mean']} by score, {e['top4']} top-four votes, {e['promise']} promise votes. Entered unchanged as the parent of a feature cross: {why}"}
wild_ids = [h for h in HOSTS if h.startswith("r13-wild")]
args["wildCarried"] = [entry(h, "the cross is measured against it") for h in wild_ids]
args["carried"] = [entry("r13-idea-1", "the round-13 winner, the bar for everything here")] + [
    entry(h, "the cross is measured against it") for h in HOSTS if h not in wild_ids] + [
    {"id": d, "name": n, "summary": f"Crossing rounds 14a/14b final heat: {sc}; the donor of {what}. Not a round-13 entrant: a cross of the tour's and the main lines' best, entered as the bar the feature crosses are measured against."}
    for d, (n, sc, what) in DONORS.items()]
args.update({"mutants": mutants, "seeds": [], "wild": [], "wildMutants": [], "nInformed": 0,
             "mode": "cross", "panel": "screen"})
(R14 / "args.json").write_text(json.dumps(args, indent=1))
print(len(mutants), "feature crosses;", len(args["carried"]), "carried,", len(args.get("wildCarried", [])), "wild carried")
