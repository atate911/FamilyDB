# The Phosphor Interface tournament, from round 8 with more variation

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

## What changed from round 8

Random entrants had advanced only about 13% of the time from round 3 on, against about 100% for
informed ones. Every round winner was informed. So the owner asked for more room for random
ideas and a higher mutation rate:

- **A protected slot.** The best random entrant of each round is carried on when it passed its
  floors, beat today's page and is more than a near-duplicate of the leader.
- **A second draft.** Each random entrant and each crossover gets a studio crit and one
  revision before judging.
- **Wildcards.** They do not read `lessons.md`, and the roll is only a spark.
- **Structure dice.** Every random seed also rolls a layout, a type system, controls, icons,
  motion and pacing.
- **Markup.** Every entrant may change the markup.
- **Mutants.** Each mutant makes two or three changes, one of them structural. From three
  mutants on, one is a crossover: one winner's structure with another's colours.
- **The css budget** is 25,000 characters, and `justify-content` and `align-content` now pass
  the check.

The changed scripts and round 8's setup are in `harness-round8-changes/`. The tar parts still
hold the harness as it was after round 7.

Carried into round 8:

- **Galley Rack** (8.23, ruled composing room). What you read sits in slate trays under Oxford
  rules. Every list in them is a rack of flat strips, each with a designator, a body and a
  tabular facts column. What you act in is a raised box. The machine speaks on green-black glass
  in a pewter case.
- **Indigo Bindery** (5.70, indigo cloth and green glass), in the protected random slot. The
  family's things are bound in indigo cloth and set in ivory Newsreader, beside a green
  phototypesetter's screen.
- **Radar Room** (7.01, flight-strip bays). Every row is a slate flight strip racked in a bay,
  with the scopes set flush into the console.
- **Signal Box** (6.99, mimic-line track). The week hangs from one blue-pewter track, each stop a
  slate plate with a lamp and a timetable time.

Slate Proof (7.46) sat out as Galley Rack's same-family sibling. Front Panel (6.09) stepped out
for the protected slot. Both stay in the hall of fame for the finale.

Round 8 has 3 random entrants: an old radio (wildcard), a tidepool, and an arcade after hours
(wildcard). It has 3 mutants: Indigo Bindery with hanging section heads, Signal Box with Home
rearranged, and a crossover of Radar Room's structure with Galley Rack's colours. It also has 2
informed entrants.

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

The scripts are `stage.js` and `stages.py` (a round run as stage workflows side by side),
`round.js` (a round as one workflow, as rounds 2-7 ran), `advance.py` (between rounds),
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
# The round-8 changes, over the harness as it was after round 7:
H="$S/harness"
cp phosphor-tournament/harness-round8-changes/*.py phosphor-tournament/harness-round8-changes/*.js \
   phosphor-tournament/harness-round8-changes/*.md "$H/"
mv "$H/rounds/r8" "$S/r8-first-setup"   # round 8 as first set up, before the changes
( cd "$H" && python3 advance.py open r7 r8 8 3 2 3 explore 2 )
cp phosphor-tournament/harness-round8-changes/rounds/r8/*.json "$H/rounds/r8/"
```

The last two lines set round 8 up again and then put back its recorded seeds and mutants.
`open` also appends a "Carried into round 8" line to `lessons.md`. The copied `lessons.md`
already has that line, so delete the duplicate.

It also needs Node 22 with `playwright` installed globally (`render.js` finds it through
`npm root -g`) and Chromium. A Claude Code cloud container has both already.

Resume from this branch as it is. The entrants' templates are checked and rendered against
this checkout's templates, and today's page (`out/00-current`) was rendered from it. If main is
merged in first and the templates have moved, re-render today's page from the harness root
before round 8: `./check.sh palettes/00-current.json`.

## Resuming

1. Start the demo page that the renders use:
   `"$S/harness/serve.sh"`, left running on port 8099.
2. Run the round in stages, several workflows side by side. A workflow runs only two agents
   at once (the machine's cores less two), so one workflow per round left the cores idle.
   From `"$S/harness"`:
   - `python3 stages.py split rN` writes `rounds/rN/stage/design-K.json`. Launch the
     workflow `stage.js` once per file, all at once, each with that file's contents as its
     arguments.
   - When every design stage is done, run
     `python3 stages.py prepare rN <each design workflow's output file>`. It renders what is
     missing or stale (four at a time), draws the sheets and writes `judge-K.json`. Launch
     `stage.js` once per judge file, all at once.
   - When every judge is done, run `python3 stages.py tally rN <each judge output file>`,
     then launch `stage.js` with `finish.json`.
   - When that is done, run `python3 stages.py assemble rN <its output file>`. This writes
     `rounds/rN/stage/output.json`.

   To hand over a round that `round.js` (the older single workflow) was running, stop that
   workflow, then run `python3 takeover.py rN <its journal.jsonl>` and
   `python3 stages.py split rN rounds/rN/stage/resume.json`. Its finished agents are not run
   again. Round 8 was handed over this way.
3. After each round, from `"$S/harness"`:
   - `python3 advance.py close rounds/rN/stage/output.json rN`
   - Check that `families.json` did not lump distinct looks into one family. Members should
     be within about 3.5 of each other.
   - `python3 archive.py`
   - `python3 advance.py choose rN`, as a dry run.
   - `python3 advance.py open rN rN+1 N+1 N_RANDOM N_INFORMED N_MUTANTS MODE N_WILDCARDS`
     (see the schedule below). This draws the sheets, sets up the next round and writes its
     `args.json`.
   - Send the owner the two new sheets from `mockups/`.
   - Launch the next round.

The owner's schedule from here: nine rounds with mutants, 8 to 16, then the finale. The owner
extended the exploratory rounds by three, from 9-10 to 9-13, ahead of the three refine rounds.

| Round | Carried | Random (wildcards) | Mutants (one a crossover) | Informed | `open` arguments |
|---|---|---|---|---|---|
| 8 | 4, one protected | 3 (2) | 3 | 2 | `r7 r8 8 3 2 3 explore 2` |
| 9 to 13 | 4 | 2 (2) | 3 | 3 | `r8 r9 9 2 3 3 refine 2` |
| 14, 15, 16 | 4 | 1 (1) | 3 | 4 | `r13 r14 14 1 4 3 refine 1` |

Round 9 has a fourth informed entrant, "Signal Lines", briefed at the owner's request
(`extraBriefs` in its `args.json`): Signal Galley with all of Signal Box's line art, on every
page. The judges are not told it was requested.

- **Finale**:
  1. A championship across the hall of fame: the best of each family, plus each round's
     carried.
  2. Four chosen for score and variety.
  3. Complete mockups of every page, on desktop and phone.
  4. A draft of the Phosphor Interface standard.
  5. Then stop, for the owner to decide what happens next.

The owner's feedback on the sheets goes into `owner_judge.md` only. It is one judge's input,
not guidance for the designers or the other judges.
