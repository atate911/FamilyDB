# Side tour and crossing rounds: what they found

Two sub-tasks ran before the main tournament's round 14.

- **The side tour** took six lineages the main rounds had passed over (the track series, Night Timetable, Pocket Timeline, Figure Ground, Flight Console, Videotex Switchboard). Each went through three rounds of planned designs, dice mutants and grafts from a feature ledger. A landing panel then judged the seven best against the main camp.
- **The crossing rounds, 14a and 14b,** put the main camp's six round-14 entrants beside the tour's seven finals, as thirteen LINES. In each round every line got one CROSS: its own judges' fixes plus two to four features taken from the other camp, then a studio crit and one revision. Each line carried its better design forward. Two heats shared three fixed anchors (today's page, Desk Terminal, Joined and Trued, Relit), so heat b could be put on heat a's scale. A final panel then judged every line's best in one heat with eight lenses.

Every cross beat its parent in both rounds (13 of 13 each time).

## Final ranking (one heat, 8 lenses, mean)

| # | Design | id | Camp | Mean | Top-4 votes | Promise votes |
|---|---|---|---|---|---|---|
| 1 | Lit Manual, Dialled | x14b-manual-cross | tour | 8.05 | 6 | 5 |
| 2 | Waypoint, Patched | x14b-waypoint-cross | tour | 7.99 | 6 | 3 |
| 3 | Trued, Yard Lit | x14b-trued-cross | tour | 7.96 | 5 | 0 |
| 4 | Folio, Fastext | x14b-folio-cross | main | 7.90 | 4 | 5 |
| 5 | Desk Terminal, Wired | x14b-desk-cross | main | 7.89 | 4 | 0 |
| 6 | Dessau, Dialled | x14b-dessau-cross | main | 7.86 | 2 | 6 |
| 7 | Sill Line, Wired | x14b-sill-cross | tour | 7.75 | 2 | 0 |
| 8 | Quote Board, Lit | x14b-quote-cross | main | 7.58 | 1 | 0 |
| 9 | Departures, Terminus | x14b-departures-cross | tour | 7.56 | 0 | 0 |
| 10 | Pocket Diary, Bound | x14b-pocket-cross | tour | 7.54 | 0 | 3 |
| 11 | Listing, Dropped Through | x14b-listing-cross | main | 7.49 | 1 | 2 |
| 12 | Switchboard, Patched | x14b-settled-cross | tour | 7.46 | 1 | 0 |
| — | *Trued, Relit (anchor)* | t3-track-refine2 | | 7.37 | | |
| 13 | Plate, Channelled | x14b-plate-cross | main | 7.32 | 0 | 0 |
| — | *Desk Terminal, Joined (anchor; the round-13 entrant)* | r13-idea-1 | | 7.26 | | |
| — | *Today's page (anchor)* | 00-current | | 4.91 | | |

Scores by lens are in `../cross/results/final-results.json` (`ranking[].byLens`), and every judge's notes and fixes are under `judges`.

How far to trust the numbers:
- The top six sit within 0.19 of each other, so their order is close to noise.
- The final judges looked more quickly than the round judges did: about 2 minutes and 19-30 tool uses each, for 16 designs.
- The judges grew stricter round by round. In 14b the anchors and the carried 14a designs scored 0.1-0.3 lower than in 14a. Compare a design with others in the same round, not across rounds.

## The six recommended for round 14

Lit Manual, Dialled; Waypoint, Patched; Trued, Yard Lit; Folio, Fastext; Desk Terminal, Wired; Dessau, Dialled. That is three tour, three main.

- Sill Line should merge into Trued. The skeptic found them nearly the same page.
- Switchboard now borrows from everyone (Desk's glass, Folio's radar, Waypoint's title) and has little of its own left.

## Features worth carrying, whichever lines go on

- **One lit lead from the screen into the list's NOW marker.** It began as Desk's patch lead and was the most-praised feature. Lit Manual's dial-to-NOW leader is the best version, though it is too long (about 245px beside empty ground).
- **A readout strip** (Today · Plans 4 · To do 4 · Late 3 · Ideas 12), from Waypoint. Lit Manual, Dessau and Folio took it.
- **A round dial that draws real days** (Lit Manual, Dessau). Put the days at true angles; the skeptic found Lit Manual's later days still sit at clock positions that mean nothing.
- **The day numeral set large, with the month and weekday stacked beside it,** as Desk sets Coming up. The type judge called it the best list typesetting in the field.
- **Folio's type pairing:** Plex Serif heads, light serif figures, small-caps units, dotted leaders and a mono running head. Type's top pick.
- **Trued's rule head with an end mark on every section.** System's top pick; keep the T buffer only where a rail really ends.
- **Listing's head column, one big figure per band.** The skeptic: "the standard to adopt".
- **The glass status line:** "4 plans · 3 late · Vera is listening".
- **Smaller pieces:** Switchboard's household row, and Waypoint's Whose filter on To do.

## Open fixes

- **Waypoint's Ideas sort (`?sort`) and To do's Whose filter (`:target`) are built only in the template and are not wired.** Usability called a control that looks latched and does nothing the worst state error.
- **A dark footer lamp at rest** (Trued, and others): every page should keep one live light, breathing only while answering.
- **Footer shape legends** (Waypoint, Dessau, Sill): drop them.
- **Desk's title sits under Next up on the glass.** Asked in 14a and again in 14b.
- **Small targets:** Trued's yard links, Desk's Ideas kind chips and Pocket's toggles are under 44px.
- **The kids' wishes** is an empty heading on Waypoint and a hole on Lit Manual and Desk.
- **Duplicate titles:** "Send Vera anything to plan." (Waypoint, Switchboard) and "What should Vera plan?" (Quote Board, Plate). "Tell Vera what to *plan*." was the judges' suggested fix for Folio, Lit Manual and Waypoint. Style liked Dessau's "Tell Vera. / Let's *plan*." best.

## Lines and where each started

| Line | Camp | Started from | Idea |
|---|---|---|---|
| desk | main | r13-idea-1 Desk Terminal, Joined | a docked terminal column, Home's question typed on its glass |
| quote | main | r13-mut-3 | a count board: each section led by one big figure |
| dessau | main | r13-wild-3 Dessau Phosphor | Bauhaus display type around the green screens |
| plate | main | r13-idea-2 | a cut matte plate over one lit screen |
| listing | main | r12-idea-1 | a programme listing: bands with a head column |
| folio | main | r13-wmut-1 | a videotex service read as a teletext magazine |
| trued | tour | t3-track-refine2 Trued, Relit | the family's week as a signal box's lit track diagram |
| manual | tour | t3-figure-refine Lit Manual, Relit Rails | the operator manual: rails with one lit NOW, figures from data |
| departures | tour | t3-timetable-refine Departures, Platformed | a station at night, a dot-matrix departures board |
| settled | tour | t3-switchboard-refine Switchboard, Settled Light | Home as a two-tier map of the service |
| sill | tour | t3-track-graft Sill Line, Ticked | the track series' bolder Home, the tube's wire onto Coming up |
| pocket | tour | t3-pocket-refine Pocket Diary, Kept | one steel line of time from Now to Later |
| waypoint | tour | t3-console-graft Waypoint Lamps | a 1969 flight console: readout strip, weeks as a flight plan |

### The tour's design languages (the six lineages)

| Key | Lineage | Origins | Idea |
|---|---|---|---|
| track | the track series (Track Diagram) | r10-idea-3, r13-mut-4 | the family's week as a signal box's illuminated track diagram (began as Signal Box, round 7) |
| timetable | Night Timetable | r10-wild-3 | a station at night: Vera's conversation the line the page hangs from, Next up a dot-matrix board |
| pocket | Pocket Timeline | r11-wild-1 | Home as time on one spine: NOW, NEXT, Coming up, LATER |
| figure | Figure Ground | r10-wild-4 | the operator manual: every section led by a figure drawn from its own data |
| console | Flight Console | r11-wild-3 | a 1969 flight console: readout strip, flight plan, annunciator, crew board |
| switchboard | Videotex Switchboard | r12-wmut-1 | Home as the map of the whole service, a videotex sommaire |

The donors the grafts could take from, each with what it offered, are in `scripts/tour.py` (`DONORS`) and `donors/`.

## Every design's id and name

Crossing rounds (`x14a-<line>-cross`, `x14b-<line>-cross`):

| Line | 14a | 14b |
|---|---|---|
| desk | Desk Terminal, Patched | Desk Terminal, Wired |
| quote | Quote Board, Posted | Quote Board, Lit |
| dessau | Dessau, Wired Through | Dessau, Dialled |
| plate | Plate, Engraved | Plate, Channelled |
| listing | Listing, Lit Through | Listing, Dropped Through |
| folio | Folio, Railed Contents | Folio, Fastext |
| trued | Trued, Headlamp | Trued, Yard Lit |
| manual | Lit Manual, Slotted | Lit Manual, Dialled |
| departures | Departures, Signalled | Departures, Terminus |
| settled | Switchboard, Quoted | Switchboard, Patched |
| sill | Sill Line, Squared | Sill Line, Wired |
| pocket | Pocket Diary, Lit | Pocket Diary, Bound |
| waypoint | Waypoint, Ruled | Waypoint, Patched |

Side tour (`t<round>-<lineage>-<slot>`):

| id | Name | id | Name |
|---|---|---|---|
| t1-track-mut | Track Diagram, Tube Lit | t2-track-mut | Branch Lines, Condensed |
| t1-timetable-mut | Night Timetable, Typeset | t2-timetable-mut | Night Departures, Surveyed |
| t1-pocket-mut | Pocket Timeline, Instruments | t2-pocket-mut | Pocket Traced, Restacked |
| t1-figure-mut | Figure Ground, Cyanotype | t2-figure-mut | Lit Manual, Relit |
| t1-console-mut | Flight Console, Aglow | t2-console-mut | Ladders, Reset |
| t1-switchboard-mut | Switchboard, Retyped | t2-switchboard-mut | Switchboard, Metered |
| t1-track-refine | Track Diagram, Trued | t2-track-refine | Branch Lines, Trued |
| t1-track-revival | Signal Box Relaid | t2-track-refine2 | Relaid, Finished |
| t1-track-graft | Track Diagram, Branch Lines | t2-track-graft | Lit Sill Line |
| t1-timetable-refine | Timetable Relit | t2-timetable-refine | Departures, Posted |
| t1-timetable-graft | Night Departures | t2-timetable-graft | Night Interchange |
| t1-pocket-refine | Pocket Timeline, Relit | t2-pocket-refine | Pocket Timeline, Trimmed |
| t1-pocket-graft | Pocket Timeline, Traced | t2-pocket-graft | Pocket Diary |
| t1-figure-refine | Lit Manual | t2-figure-refine | Lit Manual, Railed |
| t1-figure-graft | Live Figures | t2-figure-graft | Gauged Manual |
| t1-console-refine | Flight Console, Go | t2-console-refine | Lamps and Legs |
| t1-console-graft | Lamps and Ladders | t2-console-graft | Master Caution |
| t1-switchboard-refine | Switchboard, Trued | t2-switchboard-refine | Switchboard, Settled |
| t1-switchboard-graft | Switchboard, Lamp-lit | t2-switchboard-graft | Switchboard, Patched |

| id | Name |
|---|---|
| t3-track-mut | Sill Line, Instrumented |
| t3-timetable-mut | Departures, Hung |
| t3-pocket-mut | Pocket Diary, Lit |
| t3-figure-mut | Lit Manual, Magazine |
| t3-console-mut | Master Caution, Drawn |
| t3-switchboard-mut | Switchboard, Squared |
| t3-track-refine | Sill Line, Trued |
| t3-track-refine2 | Trued, Relit |
| t3-track-graft | Sill Line, Ticked |
| t3-timetable-refine | Departures, Platformed |
| t3-timetable-graft | Departures, Printed |
| t3-pocket-refine | Pocket Diary, Kept |
| t3-pocket-graft | Diary in Ink |
| t3-figure-refine | Lit Manual, Relit Rails |
| t3-figure-graft | Wired Household |
| t3-console-refine | Caution, Cleared |
| t3-console-graft | Waypoint Lamps |
| t3-switchboard-refine | Switchboard, Settled Light |
| t3-switchboard-graft | Switchboard, Patched Through |

Each design's full record (name, tagline, concept, companions, decisions, title, measures, strengths, weaknesses, revisions, crit, first draft) is in its round's `stage/designs.json`, and for the 13 finalists in `cross/final/<id>/record.json`.

## Folder layout

```
tour-and-cross/
  README.md, HANDOFF.md, harness/      (already here: the cheaper-round harness; not changed)
  cross/
    final/<id>/                        the 13 finalists: palette.json, variant/ (templates, static, sheet.css), record.json
    results/                           final-results.json (ranking, byLens, judges), final-candidates.md, final-table.md,
                                       x14a-results.json, x14b-results.json (heats, lines, judges, shift)
    lessons.md, titles.md, owner_judge.md, dossiers/<line>.md
    ledger.md, ledger-index.md, ledgers/ledger-for-<line>.md
    rounds/x14a, x14b, x14f            args.json, results.json, stage/ (design records, judge args, candidates)
    rounds/x14a-a, -b, x14b-a, -b      each heat's palettes/ and variants/ (every design judged in it)
    scripts/                           cross.py, make_stage.py, framing.txt, cross_stage.js, the contact-sheet scripts, pack.py
  tour/
    README.md                          this file
    lessons.md, titles.md, owner_judge.md, dossiers/, ledger.md, ledger-index.md, ledger.json
    rounds/t1..t3, t1-a..t3-b, landing as above
    donors/                            the donor designs the grafts drew on
    scripts/                           tour.py, tour_stage.js
```

Screenshots (`out/`), the venv and caches are left out. Re-render a design with the harness to see it.

## Paths the scripts assume

The scripts were written for a harness at:

```
H = /tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
```

- `cross.py` and `tour.py` find each other and the harness relative to their own folders: `X = cross/`, `H = X.parent`, `TOUR = H/tour`. `cross.py` imports `tour` from `H/tour`.
- Main-camp designs are read from `H/rounds/r<NN>/` (`tour.born()`).
- Each heat folder (`H/tour/t1-a`, `H/cross/x14b-a` and the others) is a copy of the old harness (`render.js`, `check.sh`, `metrics.py`, `colorlib.py`, `contact.py` and the rest) with `palettes/`, `variants/` and `out/`. Only `palettes/`, `variants/` and the round files are saved here.
- `cross_stage.js` (built from `tour_stage.js` by `make_stage.py`) has `H` and the scratchpad paths written into its prompts. The `dir` fields in every `args.json` and `stage/*.json` are absolute paths under `H`.
- Renders need the demo server at `http://127.0.0.1:8099` (`H/serve.sh`) and `H/venv` with Playwright and PIL.
- The contact-sheet scripts write to `/tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad/`.

To reuse them in a new container, set `H` to the new harness root, or recreate it at the same path, and search-and-replace the old path in `args.json`, `stage/*.json` and `cross_stage.js`. These scripts predate the cheaper-round harness in `../harness/`; for round 14, use that harness's `stage.js` and `stages.py` and take only the designs and notes from here.
