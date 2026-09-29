"""Between two rounds, keeping the tournament from narrowing into one idea.

  python3 advance.py close OUTPUT rN
      Save round N's results from the workflow's output file, then rebuild the hall of fame
      (archive.py) and the look-distances between every palette (diversity.py archive).
  python3 advance.py open rN rM M N_RANDOM N_INFORMED [N_MUTANTS MODE N_WILDCARDS]
      Choose the four carried from round N for score AND variety, draw their mockup sheet, set up
      round M with them, draw its random seeds (steered toward what the hall of fame has tried
      least), its mutants (from three on, the last a crossover) and write its args.

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


def choose(rnd):
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
    if ranking[0].get("origin") != "random":
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
    return result, chosen, why, passed, fam


def open_(rnd, nxt, nxt_no, n_random, n_informed, n_mutants="0", mode="explore", n_wild=None):
    result, chosen, why, passed, fam = choose(rnd)
    prev_dir = HERE / "rounds" / rnd
    prev_args = json.loads((prev_dir / "args.json").read_text())
    carried_summary = {c["id"]: c["summary"] for c in prev_args["carried"]}
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
    subprocess.run(["python3", str(HERE / "setup_round.py"), nxt, f"rounds/{rnd}", *[r["id"] for r in chosen]],
                   check=True, cwd=HERE)
    # Re-render the carried four with this round's harness, so every page, check and frame is
    # made the same way as the newcomers'.
    for r in chosen:
        run = subprocess.run(["./check.sh", f"palettes/{r['id']}.json"], cwd=HERE / "rounds" / nxt,
                             capture_output=True, text=True)
        print("RERENDERED", r["id"], (run.stdout.strip().splitlines() or ["?"])[-1])
    wild = str(n_wild) if n_wild is not None else ("2" if mode == "explore" and int(n_random) >= 4 else "0")
    seeds =json.loads(subprocess.run(["python3", str(HERE / "seeds.py"), n_random, "--steer", "--wildcards", wild], check=True,
                                      capture_output=True, text=True, cwd=HERE).stdout)
    history = [str(HERE / "round1" / "results.json"), str(HERE / "final.json")]
    history += [str(p / "results.json") for p in sorted((HERE / "rounds").iterdir(), key=lambda p: int(p.name[1:]))
                if (p / "results.json").exists()]
    sys.path.insert(0, str(HERE))
    import seeds as dice
    # A random entrant carried on (in the protected slot, or as the leader) gets the first mutant.
    protected = next((r["id"] for r in chosen if r.get("origin") == "random"), None)
    muts = dice.mutants([{"id": r["id"], "name": r["name"], "family": fam(r["id"])} for r in chosen],
                        int(n_mutants), protected)
    args = {"round": nxt, "roundNo": int(nxt_no), "mode": mode,
            "carried": [{"id": r["id"], "name": r["name"], "summary": summary(r, i)} for i, r in enumerate(chosen)],
            "seeds": seeds, "mutants": muts, "nInformed": int(n_informed), "history": history}
    (HERE / "rounds" / nxt / "seeds.json").write_text(json.dumps(seeds, indent=1))
    (HERE / "rounds" / nxt / "args.json").write_text(json.dumps(args, indent=1))
    (HERE / "rounds" / nxt / "carried.json").write_text(json.dumps(
        {"chosen": [{"id": r["id"], "name": r["name"], "mean": r["mean"], "why": why[r["id"]]} for r in chosen],
         "passed_over": passed}, indent=1))
    # lessons.md names the round's top four by score; record the four actually carried on.
    with open(HERE / "lessons.md", "a") as f:
        f.write(f"\nCarried into round {nxt_no} (chosen by advance.py for score and variety): "
                + "; ".join(f"{r['id']} {r['name']} {r['mean']} ({why[r['id']].split(':')[0].split(' (')[0]})" for r in chosen) + ".\n")
    print("SHEET", sheet)
    for r in chosen:
        print("CARRIED", r["id"], r["name"], r["mean"], "|", why[r["id"]])
    for p in passed:
        print("PASSED", p)


if __name__ == "__main__":
    if sys.argv[1] == "close":
        close(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "choose":
        _, chosen, why, passed, _ = choose(sys.argv[2])
        for r in chosen:
            print("CARRIED", r["id"], r["name"], r["mean"], "|", why[r["id"]])
        for p in passed:
            print("PASSED", p)
    else:
        open_(*sys.argv[2:])
