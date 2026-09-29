"""Between two rounds, keeping the tournament from narrowing into one idea.

  python3 advance.py close OUTPUT rN
      Save round N's results from the workflow's output file, then rebuild the hall of fame
      (archive.py) and the look-distances between every palette (diversity.py archive).
  python3 advance.py open rN rM M [--informed 2 --point 0 --cross 1 --type 1 --graphics 1
                                 --wild 3 --wild-carried 2 --wild-mutants 1 --random 0 --wildcards 0 --mode refine]
      Choose the four carried from round N for score AND variety, draw their mockup sheet, set up
      round M with them, draw its random seeds (steered toward what the hall of fame has tried
      least), its mutants (from three on, the last a crossover), N_TYPE type mutants (default 1:
      a carried winner with typographic changes only), N_GRAPHICS graphics mutants (default 1: its
      pictures and icons changed only) and write its args.

How the four are chosen: the best-scoring palette carries on. The next place is protected for
the best of the round's random entrants, when it passed its floors, beat today's page and is
more than a near-duplicate of the leader. Each further place goes to the
best-scoring palette from a motif family not yet carried that is more than a near-duplicate of
every one already carried (look-distance at least 40% of the round's median). If places are
left, a palette from a family already carried may take one when it looks clearly different (60%
of the median), then the near-duplicate line alone, then plain score. Scores say
how good; families and distances say how alike. Two palettes can score alike and look nothing
alike, and the other way round.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PY = str(HERE / "venv/bin/python")
TAU, TAU_EASED = 1.5, 1.0


def close(out_file, rnd):
    raw = Path(out_file).read_text()
    result = json.loads(raw[raw.find("{"):])["result"]
    (HERE / "rounds" / rnd / "results.json").write_text(json.dumps(result, indent=1))
    subprocess.run(["python3", str(HERE / "archive.py")], check=True, cwd=HERE, capture_output=True)
    subprocess.run([PY, str(HERE / "diversity.py"), "archive"], check=True, cwd=HERE)
    print("closed", rnd, "top by score:", [(r["id"], r["mean"]) for r in result["ranking"][:6]])


WILD_ORIGINS = {"wild", "wild mutant", "wild carried", "random"}


def choose(rnd, protected_random=False):
    result = json.loads((HERE / "rounds" / rnd / "results.json").read_text())
    arc = json.loads((HERE / "archive.json").read_text())["palettes"]
    dist = json.loads((HERE / "archive_distances.json").read_text())
    fams = json.loads((HERE / "families.json").read_text())
    n = rnd[1:]

    def key(pid):  # the archive key of a palette as entered in this round
        for k, p in arc.items():
            if p["id"] == pid and any(s["round"] == n for s in p["scores"]):
                return k
        return pid

    def fam(pid):
        f = fams.get(key(pid)) or fams.get(pid) or {}
        return f.get("family", f"(unsorted: {pid})")

    def d(a, b):
        return dist.get(key(a), {}).get(key(b), [99])[0]

    ranking = result["ranking"]
    # "Clearly different" scales with the round: since palettes change the whole page, every
    # pair sits further apart than when they changed a corner. A pair under 60% of the round's
    # median look-distance counts as siblings (never under 1.5, the near-duplicate line).
    ids = [r["id"] for r in ranking]
    pairs = sorted(d(a, b) for i, a in enumerate(ids) for b in ids[i + 1:] if d(a, b) < 99)
    median = pairs[len(pairs) // 2] if pairs else TAU
    tau = max(TAU, round(0.6 * median, 2))
    tau_eased = max(TAU_EASED, round(0.4 * median, 2))
    chosen, why = [ranking[0]], {ranking[0]["id"]: f"the best score of the round (clearly different here means {tau} or more apart; the round's median is {median})"}
    # The protected slot: the best of this round's random entrants goes on when it passed its
    # floors, beat today's page and is more than a near-duplicate of the leader, so a random idea
    # lives long enough to be refined instead of meeting polished winners on its first draft.
    floors = {x["id"]: x.get("floorsFailed", 0) for x in result.get("designs", [])}
    today = result.get("todayMean")
    if protected_random and ranking[0].get("origin") != "random":
        for c in ranking:
            if (c.get("origin") == "random" and floors.get(c["id"], 0) == 0
                    and (today is None or c["mean"] > today)
                    and d(c["id"], ranking[0]["id"]) >= tau_eased):
                chosen.append(c)
                why[c["id"]] = (f"the protected random slot, the best of round {n}'s random entrants "
                                f"(#{ranking.index(c) + 1} by score, today {today}): {fam(c['id'])}; "
                                f"{d(c['id'], ranking[0]['id'])} from {ranking[0]['name']}")
                break
    passes = [
        # A different idea (the curator's family, which sees layout and type as well as colour)
        # only has to be more than a near-duplicate in the pictures; the same idea has to look
        # clearly different to earn a second place.
        ("new family, not a near-duplicate", lambda c: fam(c["id"]) not in {fam(x["id"]) for x in chosen}
         and min(d(c["id"], x["id"]) for x in chosen) >= tau_eased),
        ("clearly different, family repeats", lambda c: min(d(c["id"], x["id"]) for x in chosen) >= tau),
        ("different enough (distance eased)", lambda c: min(d(c["id"], x["id"]) for x in chosen) >= tau_eased),
        ("score alone", lambda c: True),
    ]
    for label, ok in passes:
        for c in ranking:
            if len(chosen) == 4:
                break
            if c in chosen or not ok(c):
                continue
            chosen.append(c)
            near = min(chosen[:-1], key=lambda x: d(c["id"], x["id"]))
            why[c["id"]] = f"{label}: {fam(c['id'])}; nearest carried {near['name']} at {d(c['id'], near['id'])}"
    passed = []
    lowest = min(x["mean"] for x in chosen)
    for c in ranking:
        if c in chosen or c["mean"] < lowest:
            continue
        near = min(chosen, key=lambda x: d(c["id"], x["id"]))
        passed.append(f"{c['name']} ({c['mean']}, {fam(c['id'])}): {d(c['id'], near['id'])} from {near['name']}"
                      + (", same family" if fam(c["id"]) == fam(near["id"]) else ""))
    # The wild lane: two more places, for the ideas the judges most want developed. Entrants not
    # already carried above are ranked by the judges' "promise" votes, then by score. A wild,
    # random or wild-carried one goes on when it has a promise vote or beat today's page; any other
    # (an informed entrant or a mutant) when it has promise votes and its family is not already
    # carried in the main lane, so an idea the judges want developed is not lost for its score.
    # The second comes from a different family where there is one.
    wild = []
    main_fams = {fam(x["id"]) for x in chosen}
    pool = [c for c in ranking if c not in chosen
            and (c.get("promise", 0) > 0 or (c.get("origin") in WILD_ORIGINS and (today is None or c["mean"] > today)))
            and (c.get("origin") in WILD_ORIGINS or fam(c["id"]) not in main_fams)]
    pool.sort(key=lambda c: (-c.get("promise", 0), -c["mean"]))
    for c in pool:
        if len(wild) == 2:
            break
        if wild and fam(c["id"]) == fam(wild[0]["id"]) and any(fam(x["id"]) != fam(wild[0]["id"]) for x in pool[pool.index(c):]):
            continue
        wild.append(c)
        why[c["id"]] = (f"the wild lane, for the ideas the judges most want developed ({c.get('promise', 0)} promise "
                        f"votes, #{ranking.index(c) + 1} by score, today {today}): {fam(c['id'])}")
    return result, chosen, why, passed, fam, wild


def open_(rnd, nxt, nxt_no, *, random_n=0, wildcards=0, informed=2, point=0, cross=1, type_n=1, graphics=1,
          wild_n=3, wild_carried=2, wild_mutants=1, phosphor=1, mode="refine"):
    result, chosen, why, passed, fam, wild = choose(rnd)
    wild = wild[:wild_carried]
    prev_dir = HERE / "rounds" / rnd
    prev_args = json.loads((prev_dir / "args.json").read_text())
    carried_summary = {c["id"]: c["summary"] for c in prev_args["carried"] + prev_args.get("wildCarried", [])}
    designs = {x["id"]: x for x in result["designs"]}
    prev_no = prev_args["roundNo"]

    def summary(r, i):
        where = (f"Round {prev_no}: #{result['ranking'].index(r) + 1} by score (mean {r['mean']}, in {r['top4']} "
                 f"judges' top fours); carried as {why[r['id']]}. Family: {fam(r['id'])}.")
        if r["id"] in designs:
            x = designs[r["id"]]
            return f"{where} Born in round {prev_no} ({r['origin']}). {x['tagline']} {x['concept']}"
        return f"{where} {carried_summary.get(r['id'], '')}"

    labels = [f"{r['id']}|{r['name']}|{r['mean']}|#{result['ranking'].index(r) + 1} by score · {fam(r['id'])}" for r in chosen]
    sheet = HERE.parent / "mockups" / f"round-{prev_no}-winners.png"
    subprocess.run([PY, str(HERE / "winners.py"), str(prev_dir), str(sheet),
                    f"Round {prev_no}: the four carried into round {nxt_no} (score and variety)", *labels], check=True)
    if wild:
        subprocess.run([PY, str(HERE / "winners.py"), str(prev_dir), str(sheet.with_name(f"round-{prev_no}-wild.png")),
                        f"Round {prev_no}: the wild lane carried into round {nxt_no} (the ideas the judges most want developed)",
                        *[f"{r['id']}|{r['name']}|{r['mean']}|{r.get('promise', 0)} promise votes · {fam(r['id'])}" for r in wild]],
                       check=True)
    subprocess.run(["python3", str(HERE / "setup_round.py"), nxt, f"rounds/{rnd}", *[r["id"] for r in chosen + wild]],
                   check=True, cwd=HERE)
    # Re-render the carried four with this round's harness, so every page, check and frame is
    # made the same way as the newcomers'.
    def rerender(r):
        run = subprocess.run(["./check.sh", f"palettes/{r['id']}.json"], cwd=HERE / "rounds" / nxt,
                             capture_output=True, text=True)
        return r["id"], (run.stdout.strip().splitlines() or ["?"])[-1]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:  # one render per core
        for pid, last in pool.map(rerender, chosen + wild):
            print("RERENDERED", pid, last)
    seeds = json.loads(subprocess.run(["python3", str(HERE / "seeds.py"), str(random_n), "--steer", "--wildcards", str(wildcards)],
                                      check=True, capture_output=True, text=True, cwd=HERE).stdout) if random_n else []
    history = [str(HERE / "round1" / "results.json"), str(HERE / "final.json")]
    history += [str(p / "results.json") for p in sorted((HERE / "rounds").iterdir(), key=lambda p: int(p.name[1:]))
                if (p / "results.json").exists()]
    sys.path.insert(0, str(HERE))
    import seeds as dice
    # A random entrant carried on (in the protected slot, or as the leader) gets the first mutant.
    protected = next((r["id"] for r in chosen if r.get("origin") == "random"), None)
    def colours(pid):
        t = json.loads((HERE / "rounds" / nxt / "palettes" / f"{pid}.json").read_text())["tokens"]
        return {k: t[k] for k in dice.COLOUR_ROLES if k in t}
    def parent(r):
        return {"id": r["id"], "name": r["name"], "family": fam(r["id"]), "colours": colours(r["id"])}
    # The main lane's mutants; the crossover may take a parent from either lane, so wild traits can
    # breed into the main line.
    muts = dice.mutants([parent(r) for r in chosen], point + cross, protected, type_n, graphics,
                        n_cross=cross, cross_pool=[parent(r) for r in chosen + wild])
    # Phosphor mutants go last, on the carried that the soul judge found kept least of the original's
    # light (its lowest scores first), so the light comes back where it was lost.
    by_soul = sorted(chosen, key=lambda r: (r.get("byLens", {}).get("soul", 10), -r["mean"]))
    muts += dice.phosphor_mutants([parent(r) for r in by_soul], phosphor)
    past = {}
    for f in (HERE / "rounds").glob("*/args.json"):
        for w in json.loads(f.read_text()).get("wild", []):
            past[w["language"]] = past.get(w["language"], 0) + 1
    wild_new = [{**w, "slot": i} for i, w in enumerate(dice.wild_seeds(wild_n, past), 1)]
    wild_muts = [{**m, "slot": i} for i, m in enumerate(dice.wild_mutants([parent(r) for r in wild], wild_mutants), 1)]
    args = {"round": nxt, "roundNo": int(nxt_no), "mode": mode,
            "carried": [{"id": r["id"], "name": r["name"], "summary": summary(r, i)} for i, r in enumerate(chosen)],
            "wildCarried": [{"id": r["id"], "name": r["name"], "summary": summary(r, i)} for i, r in enumerate(wild)],
            "seeds": seeds, "mutants": muts, "wild": wild_new, "wildMutants": wild_muts,
            "nInformed": int(informed), "history": history}
    (HERE / "rounds" / nxt / "seeds.json").write_text(json.dumps(seeds, indent=1))
    (HERE / "rounds" / nxt / "args.json").write_text(json.dumps(args, indent=1))
    (HERE / "rounds" / nxt / "carried.json").write_text(json.dumps(
        {"chosen": [{"id": r["id"], "name": r["name"], "mean": r["mean"], "why": why[r["id"]]} for r in chosen],
         "wild": [{"id": r["id"], "name": r["name"], "mean": r["mean"], "promise": r.get("promise", 0), "why": why[r["id"]]} for r in wild],
         "passed_over": passed}, indent=1))
    # lessons.md names the round's top four by score; record the four actually carried on.
    with open(HERE / "lessons.md", "a") as f:
        f.write(f"\nCarried into round {nxt_no} (chosen by advance.py for score and variety): "
                + "; ".join(f"{r['id']} {r['name']} {r['mean']} ({why[r['id']].split(':')[0].split(' (')[0]})" for r in chosen) + "."
                + (" Carried in the wild lane: " + "; ".join(f"{r['id']} {r['name']} {r['mean']}" for r in wild) + "." if wild else "") + "\n")
    print("SHEET", sheet)
    for r in chosen:
        print("CARRIED", r["id"], r["name"], r["mean"], "|", why[r["id"]])
    for r in wild:
        print("WILD", r["id"], r["name"], r["mean"], "|", why[r["id"]])
    for p in passed:
        print("PASSED", p)


if __name__ == "__main__":
    if sys.argv[1] == "close":
        close(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "choose":
        _, chosen, why, passed, _, wild = choose(sys.argv[2])
        for r in chosen:
            print("CARRIED", r["id"], r["name"], r["mean"], "|", why[r["id"]])
        for r in wild:
            print("WILD", r["id"], r["name"], r["mean"], "|", why[r["id"]])
        for p in passed:
            print("PASSED", p)
    else:
        import argparse
        ap = argparse.ArgumentParser(prog="advance.py open")
        ap.add_argument("cmd"), ap.add_argument("rnd"), ap.add_argument("nxt"), ap.add_argument("nxt_no")
        for flag, default in (("random", 0), ("wildcards", 0), ("informed", 2), ("point", 0), ("cross", 1),
                              ("type", 1), ("graphics", 1), ("wild", 3), ("wild-carried", 2), ("wild-mutants", 1),
                              ("phosphor", 1)):
            ap.add_argument(f"--{flag}", type=int, default=default)
        ap.add_argument("--mode", default="refine")
        o = ap.parse_args()
        open_(o.rnd, o.nxt, o.nxt_no, random_n=o.random, wildcards=o.wildcards, informed=o.informed, point=o.point,
              cross=o.cross, type_n=o.type, graphics=o.graphics, wild_n=o.wild, wild_carried=o.wild_carried,
              wild_mutants=o.wild_mutants, phosphor=o.phosphor, mode=o.mode)
