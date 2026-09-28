# The Phosphor Interface tournament, paused after round 7

This folder saves an experiment, not a change to FamilyDB. Nothing under `src/` is touched. It
holds the palette-and-layout tournament that is choosing the "Phosphor Interface" design standard
for the web page. The owner asked to calm today's bright, monochrome green-on-black: keep the
phosphor `#6dff9c` on green-black as the signature, light it only where it means something, and
give everything else a grounded colour that supports the green.

Each round has twelve entrants: the four carried from the round before, six random entrants drawn
from steered dice, and two built from the judges' notes. Seven judges score each entrant, each
through its own lens: the owner's judge, soul, style, system, interaction, type and a skeptic.
Four go on, chosen for score *and* variety, so the field does not narrow into one idea.

## Where it stands

| Round | Winner | Its score | Today's page | Lead over today |
|------:|--------|----------:|-------------:|----------------:|
| 1 | Aurora, after polishing (Mint and Lilac led the first scoring, 7.1) | 7.7 | | |
| 2 | Evening Study | 6.90 | | |
| 3 | Plum Ink | 6.74 | | |
| 4 | Slate Console | 6.96 | 3.97 | 2.99 |
| 5 | Slate Galley | 7.67 | 3.81 | 3.86 |
| 6 | Slate Proof | 7.84 | 3.76 | 4.08 |
| 7 | Galley Rack | 8.23 | 3.90 | 4.33 |

Before round 4, today's page was not scored alongside the entrants. "Lead over today" is the
winner's score minus today's page's score. Each round has its own panel and field, so a score
compares best within its round. From round 4 on, the lead over today is the steadier measure
across rounds.

Carried into round 8, which is **set up but not launched**:

- **Galley Rack** (8.23, ruled composing room). What you read sits in slate trays under Oxford
  rules. Every list in them is a rack of flat strips, each with a designator, a body and a
  tabular facts column. What you act in is a raised box. The machine speaks on green-black glass
  in a pewter case.
- **Radar Room** (7.01, flight-strip bays). Every row is a slate flight strip racked in a bay,
  with the scopes set flush into the console.
- **Signal Box** (6.99, mimic-line track). The week hangs from one blue-pewter track, each stop a
  slate plate with a lamp and a timetable time.
- **Front Panel** (6.09, silk-screened front panel). A 1980s bench instrument: legends set into
  the line, graphite modules, blue-grey keys.

Slate Proof (7.46) sat out round 8 because Galley Rack is its descendant and in the same family.
It stays in the hall of fame for the finale.

Round 8's six random seeds are a planetarium, a forest after rain, a jazz club, a mountain hut,
a desert night and an arcade after hours. The last two are wildcards, free to change the
markup.

## What is here

- `mockups/`: each round's four winners (`round-N-winners.png`) and, from round 3 on, their type
  at 100% (`round-N-type.png`).
- `harness.tar.gz.part-NN`: the whole harness, a gzipped tar split into parts under GitHub's
  file limit. It holds every round's palettes, page variants, scores, judges' notes and
  screenshots, plus the scripts.
- `harness-venv-requirements.txt`: the harness's own Python packages.
- `SHA256SUMS`: a checksum for each part.

Inside the harness, the files that carry the thinking are:

- `lessons.md`: the owner's direction, then each round's lessons and candidate principles.
- `owner_judge.md`: the owner's own notes. Only the owner's judge reads them.
- `families.json`: the motif families.
- `archive.json` and `archive_distances.json`: the hall of fame and the look-distances.
- `rounds/rN/results.json`: each round's full result.
- `README.md`: the designers' brief.

The scripts are `round.js` (one round, run as a workflow), `advance.py` (between rounds),
`seeds.py`, `check.sh`, `render.js`, `metrics.py`, `diversity.py`, `winners.py` and
`contact.py`.

Three things are left out. The venv is rebuilt from the requirements. The Python caches are
dropped. The demo server's session key, `web_secret`, is made again on first start. The
agents' own transcripts lived outside the harness and are not kept; each round's
`results.json` holds everything the round returned.

## Restoring it

The scripts and each round's arguments name the harness's absolute path, so put it back at
exactly that path:

```sh
S=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad
mkdir -p "$S"
cd phosphor-tournament
sha256sum -c SHA256SUMS
cat harness.tar.gz.part-* | tar -xzf - -C "$S"
python3 -m venv "$S/harness/venv"
"$S/harness/venv/bin/pip" install -r harness-venv-requirements.txt
cd .. && uv sync            # the demo and variant servers run FamilyDB from its .venv
```

It also needs Node 22 with `playwright` installed globally (`render.js` finds it through
`npm root -g`) and Chromium. A Claude Code cloud container has both already.

Resume from this branch as it is. The entrants' templates are checked and rendered against
this checkout's templates, and today's page (`out/00-current`) was rendered from it. If main is
merged in first and the templates have moved, re-render today's page from the harness root
before round 8: `./check.sh palettes/00-current.json`.

## Resuming

1. Start the demo page that the renders use:
   `"$S/harness/serve.sh"`, left running on port 8099.
2. Launch round 8: run the workflow `"$S/harness/round.js"` with the contents of
   `"$S/harness/rounds/r8/args.json"` as its arguments, passed verbatim.
3. After each round, from `"$S/harness"`:
   - `python3 advance.py close <the workflow's output file> rN`
   - Check that `families.json` did not lump distinct looks into one family. Members should
     be within about 3.5 of each other.
   - `python3 archive.py`
   - `python3 advance.py choose rN`, as a dry run.
   - `python3 advance.py open rN rN+1 N+1 6 2 0 explore`. This draws the sheets, sets up
     the next round and writes its `args.json`.
   - Send the owner the two new sheets from `mockups/`.
   - Launch the next round.

The owner's schedule from here:

- **Round 8**: explore, as above.
- **Rounds 9 and 10**: refine, with 4 carried, 1 random, 1 mutant and 6 informed:
  `python3 advance.py open r8 r9 9 1 6 1 refine`, and the same from r9 to r10.
- **Up to three more refine rounds** while the lead over today keeps growing by at least 0.2 a
  round. Stop early if it is flat for two rounds.
- **Finale**:
  1. A championship across the hall of fame: the best of each family, plus each round's
     carried.
  2. Four chosen for score and variety.
  3. Complete mockups of every page, on desktop and phone.
  4. A draft of the Phosphor Interface standard.
  5. Then stop, for the owner to decide what happens next.

The owner's feedback on the sheets goes into `owner_judge.md` only. It is one judge's input,
not guidance for the designers or the other judges.
