# The Phosphor Interface tournament, from round 8 with more variation

This folder saves an experiment, not a change to FamilyDB. Nothing under `src/` is touched. It
holds the palette-and-layout tournament that is choosing the "Phosphor Interface" design standard
for the web page. The owner asked to calm today's bright, monochrome green-on-black: keep the
phosphor `#6dff9c` on green-black as the signature, light it only where it means something, and
give everything else a grounded colour that supports the green.

Each round has a main lane and, from round 10, a wild lane. The main lane has the four carried
from the round before, mutants of them, and entrants built from the judges' notes. The wild lane
has new designs made from a clean sheet on a radical design language, plus the two the judges
most want developed. Eight judges score each entrant, each through its own lens: the owner's
judge, soul, style, system, interaction, type, usability and a skeptic. Four go on in the main
lane, chosen for score *and* variety, so the field does not narrow into one idea.

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
| 8 | Signal Galley | 7.87 | 3.61 | 4.26 |
| 9 | Programme Guide | 8.11 | 4.00 | 4.11 |
| 10 | Evening Listing | 7.90 | 4.29 | 3.61 |
| 11 | Evening Listing, Relit | 8.04 | 4.71 | 3.33 |
| 12 | Desk Terminal | 8.34 | 4.84 | 3.50 |
| 13 | Desk Terminal, Joined | 8.33 | 4.72 | 3.61 |

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

## Paused for the owner's review before the refine rounds

The owner asked to pause and review before the refine rounds. Round 14 had been set up and its
design stage launched; the design workflows were stopped and their half-written files moved
aside, so nothing of round 14 is judged or kept. Its setup (`rounds/r14/args.json`) is saved and
can be launched as it is or changed after the review. Review sheets for the six designs going
into the refine rounds, and for the Signal Box line that left the main lane, are in
`mockups/review-before-refine/`.

## Cheaper rounds from round 14

The rounds had come to cost too many tokens to carry on. Before round 14 the harness was changed
to spend far less per round while still telling the designs apart and keeping the creative lanes.
The changed files and the reasons, with the evidence from rounds 9 to 13, are in
`harness-round14-changes/README.md`. In short:

- **Judging is a screen, then a final.** Five lenses (the owner's judge, soul, style, the
  skeptic, and one "system and use" judge for the three that agreed most closely) score the
  whole field. The seven best, and up to two the screen most wants developed, go to a final.
  There all eight lenses score them and put them in a strict order. Replayed on rounds 9 to 13,
  every round's real top four reached the final. The 4th and 5th places, 0.01 apart in four of
  those rounds, are now decided by the final's order.
- **Judges and designers read cards.** Each palette gets four images, each sized to what a model
  reads without shrinking it, read several to a message. They replace dozens of strips, sheets
  and full-size shots opened one at a time.
- **Fewer pages are shot**: 8 instead of 13 (no Sign in, 404, General settings, whole form or
  phone Chat; together they were under 3% of what the judges wrote about).
- **A digest of the lessons** (about 4,000 words, rewritten each round) replaces the 92 KB
  `lessons.md` for every agent. The planner reads a brief pack instead of three results files.
- **Bookkeeping agents** (the curator, re-asks for a missed score) run on a cheaper model.
- `python3 stages.py usage <transcript folders>` reports each agent's tokens, so round 14
  measures what the change saved.

## Carried into round 14

Round 13 was the last exploratory round. **Desk Terminal, Joined** (8.33, in seven top fours)
won. It is the leader made whole: a head row on every inner page, and the message box on Home
inside the tube, under the question typed on the glass. The terminal folds to one "Ready" line
where nothing is live. The owner's judge ranked the phosphor mutant, **Track Diagram Aglow**,
first (8.9), but every other lens called it a near-duplicate of its parent, and it came 7th.
So the Signal Box line (the mimic-line track) leaves the main lane. It stays in the hall of fame
for the finale. Round 13's lessons: a mutation has to change a structure the family reads. The
four one-meaning signals (lit lamp on, steel dot waiting, pewter ring off, amber bar needs a
look) and Quote Board's title-with-figure head are wanted in the standard.

Main lane: **Desk Terminal, Joined** (8.33), **Backlit Plate** (7.80, 5 promise votes; light
shows only through cuts in a matte plate), **Quote Board at Evening** (7.76; each title carries
its figure) and **Evening Listing, Traced** (7.62). Wild lane: **Dessau Phosphor** (4 promise
votes; Bauhaus posters with a round phosphor screen for each page's live figure) and **Folio
Switchboard** (large serif figures on the switchboard).

Rounds 14 to 16 refine: 4 carried, type, graphics, crossover and phosphor mutants, 3 informed,
and a wild lane of 2 carried, 2 new and 1 mutant. Round 14's wild designs are a hand-drawn
sketch and a 1980s cockpit dashboard.

## Carried into round 13

Round 12 was restarted once. The container restarted during its design stage, before any design
had finished. The partly written files were moved aside and the six design workflows ran again
from the start.

**Desk Terminal** (8.34) won, in all eight judges' top fours, with 7 promise votes. The judges
called it the first entrant that is a page template rather than a palette. One cased, lit
graphite terminal stands at the left of every page. It holds the tube, the question typed on the
glass under a cursor, a deck of one-tap latched filter keys and a lit "Ready" foot. A square
matte slate desk beside it holds only the family's rows. It won both the owner's judge (8.6) and
usability (9.0). **Evening Listing, Traced** (8.09) was second. It is the leader with its light
put to work: a trace of the coming weeks on Next up, rails lit from now, and a figure in every
head column.

The phosphor mutant, Evening Listing, Afterglow (7.38), scored below its parent for the first
time. Its scanlined afterglow over each page head read as "a wash in the corner". So round 12
refined round 11's "light as data": a lit thing has to do a job on every page, and page-scale
haze does not register.

Main lane: **Desk Terminal**, **Evening Listing, Traced**, **Long Persistence** (7.50) and
**Track Diagram Relit** (7.05). Wild lane: **Videotex Switchboard** (7 promise votes), which
makes Home a sommaire of equal page cells with counts, and **Single Quote** (6 votes), which sets
each title with its figure in the section's colour.

Round 13, the last exploratory round, has four wild languages never tried before: an
architectural blueprint, a library card catalogue, Bauhaus, and Tron's neon grid. The wild dice
now choose untried languages first.

## Carried into round 12

In round 11 every relit design beat its unlit parent. Evening Listing, Relit was in all eight
judges' top fours. It keeps the programme listing, and each head column now does a job: counts
and "late", the kind filter, Open/Done. The tube's light is back on the short list of live
things. Long Persistence was second, with the joint-most promise votes: each page has one lit
instrument that draws the family's own weeks, due dates or spending, over quiet graphite tables.
Round 11's lessons add "light as data": the judges prefer a tube that draws something to one
that only glows brighter.

Main lane: **Evening Listing, Relit** (8.04), **Long Persistence** (7.88), **Track Diagram
Relit** (7.52; it won the owner's judge, 8.8, and the soul judge, 8.2) and **Signal Legend
Relit** (6.91). Wild lane: **Flight Console** (7 promise votes), a 1969 flight console with
violet flight-plan drawings and rows of lamps, and **Videotex Sommaire** (5 votes), which types
the question on the glass and opens on a numbered contents page.

Round 12 has a phosphor mutant of the leader pushing the tubes and the page's own light further,
a type mutant of Signal Legend Relit (width as hierarchy), a graphics mutant of Long Persistence
(Status as an instrument panel), and a crossover of Flight Console's structure with the leader's
colours. The wild designs are a zine, Teletext, a planetarium desk and a trading terminal (a
repeated Minitel roll was re-drawn to a language not yet tried).

## Carried into round 11

Round 10 was scored with the soul judge counting 1.5 times. The informed entrants took first and
second place, and the two phosphor mutants took third and fourth, each above its parent. Relit
scored 7.48 against Signal Legend's 7.04, and Lit 7.47 against Flight Deck's 6.76. The soul judge
and the owner's judge ranked those two top. The blind Signal Box, Track Diagram, won the owner's
judge outright (9.1). Round 10's lessons turn the owner's latest word into a candidate principle:
"Light is a list, not a level." What is live glows at full strength and everything else is
matte, so calm comes from how short the list is, never from dimming the tube.

Main lane:

- **Evening Listing** (7.90, programme listing). Programme Guide finished: heads on one line,
  steel reverse video for "here", underlined links, facts in true columns, a breathing now lamp.
- **Track Diagram** (7.57, mimic-line track). The improved Signal Box, entered blind: steel-cyan
  lines on slate boards with a lamp at each stop, drawn only where there is an order.
- **Signal Legend Relit** (7.48, ruled composing room). Signal Legend with the tube light back.
- **Flight Deck, Lit** (7.47, glass cockpit). Flight Deck with its instruments lit and
  everything else matte.

Wild lane, by promise votes:

- **Docked Terminal** (6.85, 7 votes, the most of the round). The machine docked in one lit glass
  column beside a slate desk. It was an informed entrant; the wild lane now takes any idea the
  judges most want developed whose family is not already carried.
- **Figure Ground** (6.41, 5 votes). An operator's manual in which every section is a numbered
  plate led by a figure drawn from its own data.

Round 11 has a type mutant and a phosphor mutant of Track Diagram (the lowest soul score of the
four), a graphics mutant of Relit with no icons at all, and a crossover of Docked Terminal's
structure with Figure Ground's colours. The four wild designs are a Game Boy handheld, a museum
exhibition, 1969 mission control and a Minitel service.

## Carried into round 10 (from round 9)

Main lane:

- **Programme Guide** (8.11, programme listing). A TV programme guide on slate: banded parts
  with head columns, one-line rows across dotted leaders, and a denim needle for "here".
- **Signal Legend** (7.51, ruled composing room). Signal Galley's slate trays, each head set into
  its rail, with reverse video for the current item.
- **Flight Deck** (7.44, glass cockpit). A 1980s glass cockpit: matte instrument plates inside
  demarcation lines, and flush display units in screwed faceplates.
- **Reverse Video** (7.09, text-mode windows). Green-screen software grammar: steel-framed
  windows, double-framed dialogs, a highlight bar.

Wild lane, chosen by the judges' promise votes (3 each):

- **Attract Mode** (5.04, teal-tinted ground). An arcade after hours in graphite-teal.
- **Porcelain Atlas** (5.00, porcelain star atlas). A star atlas as a book: a centred serif
  column, porcelain ink, cobalt hairlines.

Signal Galley (7.10) sat out as Signal Legend's same-family parent. The sheets are
`mockups/round-9-winners.png`, `round-9-type.png`, `round-9-wild.png` and `round-9-wild-type.png`.
Round 10's third informed entrant was briefed at the owner's request and is judged blind.

## What is here

- `mockups/`: each round's four winners (`round-N-winners.png`) and, from round 3 on, their type
  at 100% (`round-N-type.png`).
- `harness.tar.gz.part-NN`: the whole harness, a gzipped tar split into parts under GitHub's
  file limit. It holds every round's palettes, page variants, scores, judges' notes and
  screenshots, plus the scripts.
- `harness-venv-requirements.txt`: the harness's own Python packages.
- `SHA256SUMS`: a checksum for each part.
- `gallery/`: builds the screenshot gallery, one page per round plus an index page. Each round page
  has every design's screenshots (by page or by design, with a large view), what each judge said
  (with their suggested fixes) and the round's notes. `python3 gallery/build_gallery.py HARNESS OUT`
  needs Pillow (the harness venv has it); OUT then holds `index/` and `round-1/` .. `round-13/`, each
  an `index.html` with its `img/` (an artifact holds at most 511 files, which is why a round is a
  page). Publish each folder as its own artifact, then `gallery/relink.py OUT links.json` puts the
  published links in place of the `@INDEX@` and `@ROUND<n>@` placeholders, and the pages are
  published again. All 13 rounds and the index were published this way as private artifacts.

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

## The design files for rounds 8 to 14

`harness.tar.gz.part-NN` holds the harness as it was after round 7. Every palette, page template
and stylesheet made since then (rounds 8 to 13, and round 14's setup) is in
`harness-rounds-8-13/harness-rounds-8-13.tar.gz` (30 MB, checksum in its `SHA256SUMS`). It also
holds the scripts as they are now, each round's results, args, judges' records and design
records, the hall of fame, `lessons.md`, `owner_judge.md`, the phosphor kit and audit, the font
library and the demo household's database. It leaves out three things you can make again: the
virtual environment (from `harness-venv-requirements.txt`), the screenshots and contact sheets
(run `./check.sh palettes/<id>.json` on a palette, or `python3 stages.py prepare rN ...`), and the
demo config `demo.env` (copy `demo.env.example` and choose a password). `serve.sh` still carries
the demo login, `palette-demo-pass`, and a fake API key, `sk-fake`; both are made-up values for a
local server with fake data.

To put it back, restore the older tar as below, then extract the newer one over it at the same
path: `tar -xzf harness-rounds-8-13/harness-rounds-8-13.tar.gz -C "$S/harness"`. The older
`harness-round8-changes/` folder is now only a history of what changed; the newer archive
supersedes it. Then copy the round-14 changes over both. With the demo server running, re-render
round 14's carried designs so their cards exist (the archive leaves out screenshots):

```sh
H="$S/harness"
cp -r phosphor-tournament/harness-round14-changes/harness/. "$H/"
( cd "$H" && cp README.md render.js contact.py check.sh rounds/r14/ )
( cd "$H/rounds/r14" && for p in palettes/*.json; do ./check.sh "$p"; done )
```

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
     missing or stale (four at a time), draws the cards and sheets, and writes `screen-K.json`
     (or `judge-K.json` for a round with `"panel": "full"`). Launch `stage.js` once per file,
     all at once.
   - When every screen judge is done, run `python3 stages.py cut rN <each screen output file>`.
     It chooses the finalists and writes `final-K.json`. Launch `stage.js` once per file, all
     at once.
   - When every final judge is done, run `python3 stages.py tally rN <each final output file>`,
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

From round 10 the owner asked for more entropy in the design system: "nothing should be off the
table ... extreme ideas tried and voted either up or down". So the harness changed:
- **Only integrity and safety are refused.** Every form, field and link must still work, nothing
  may load from outside, and the render must succeed. Contrast, text size, the green signature,
  the page's words and sideways scroll are measured and shown to the judges, not refused.
- **A wild lane beside the main one.** Each round has four new designs built from a clean sheet
  on a radical design language rolled by the dice (Teletext, a Swiss grid, Bauhaus, a
  vector-arcade display, mission control, a split-flap board and so on). They start from their
  own stylesheet with none of today's, and do not see the other designs or `lessons.md`. The
  two designs the judges most want developed carry on in their own lane, and one wild mutant
  makes two big leaps from them.
- **Judges reward new ideas.** They judge each design on its own merits, give constructive fixes
  for bold ideas that fall short, and cast up to three "promise" votes for the ideas most worth
  developing. The wild lane is chosen by those votes. `lessons.md` records failed reaches as
  information, not rules.
- **Type and graphics mutants.** Each round has a type-only and a graphics-only mutant, and the
  crossover may cross the two lanes. There are no point mutants.
- **The phosphor soul counts a little more.** The owner asked for the soul judge (the CRT's glow,
  halos, scanlines and glowing dots) to weigh slightly more than the others, so from round 10 it
  counts 1.5 times in each entrant's mean (`LENS_WEIGHTS` in `stages.py`), today's page included.
  That mean ranks and carries. Each result also keeps `plainMean`, with every judge counted once,
  and `lensWeights`. Replayed on round 9, it moves no entrant's place and no mean by more than
  0.05. The finale uses the same weights.

| Round | Main lane | Wild lane | `open` options |
|---|---|---|---|
| 10 | 4 carried, type, graphics and crossover mutants, 2 phosphor mutants, 3 informed (the last the blind improved Signal Box) | 2 carried, 4 new, 1 mutant | `--informed 3 --wild 4`, with the phosphor mutants added after |
| 11 to 13 | 4 carried, the 4 mutants, 2 informed | 2 carried, 4 new, 1 mutant | `--informed 2 --wild 4` |
| 14 to 16 | 4 carried, the 4 mutants, 3 informed | 2 carried, 2 new, 1 mutant | `--informed 3 --wild 2` |

The full command is `python3 advance.py open rN rM M --informed I --wild W` with the defaults
`--point 0 --cross 1 --type 1 --graphics 1 --phosphor 1 --wild-carried 2 --wild-mutants 1 --mode refine
--panel screen` (from round 14; `--panel full` judges the old way, eight lenses over the whole field).

**Bringing the original's light back.** During round 10 the owner said: "in the goal of great
interface design we've gained a lot but also lost a little of the unique effect of the original
phosphor interface. I'd suggest bringing some of that back." So:
- `phosphor_kit.md` catalogues the original page's CRT effects, each with its exact CSS and how a
  design re-creates it: the layered halo on lit words and marks, the green screens' blur, bloom
  and scanlines, the glowing live dots, the highlights and the afterglow. A second agent checked
  it against the original stylesheet.
- `phosphor_audit.md` records what each of the six designs carried into round 10 kept and lost of
  those effects.
- The owner's words are now in the brief every designer and judge reads, and the designers'
  README has a section on the light.
- Each round has a **phosphor mutant**: a carried winner with the original's light brought back
  and nothing else changed. It goes to the carried design with the lowest soul score, and the dice
  choose two effects for it to push furthest. It gets a crit and a revision. Round 10 has two,
  added while it was designing, on the two the owner singled out: Flight Deck and Signal Legend.

The finale's championship includes the wild lane's best.

- **Finale**:
  1. A championship across the hall of fame: the best of each family, plus each round's
     carried.
  2. Four chosen for score and variety.
  3. Complete mockups of every page, on desktop and phone.
  4. A draft of the Phosphor Interface standard.
  5. Then stop, for the owner to decide what happens next.

The owner's feedback on the sheets goes into `owner_judge.md` only. It is one judge's input,
not guidance for the designers or the other judges.
