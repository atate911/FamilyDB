# The Phosphor tournament as natural selection, from round 14

Rounds 1 to 13 carried whole designs: four winners went on and mutants were made of them. This
changes what survives. A design is a set of ELEMENTS, one for each aspect the judges evaluate (a
slot), and the elements are what is selected, mutated and recombined. Whole designs still compete,
as lineages, but a lineage's head is built from the elements that won.

Based on the earlier system (judges' lenses, a screen, a final, dice for blind mutations, a wild
lane, a hall of fame). Not the same: the unit of selection, how a mutation is made, and what is kept.

## The plan

- **Rounds 14 to 18: five rounds of selection.** Each is a generation.
- **Rounds 19 and 20: two refinement rounds.** The survivors only: no blind mutations; each head
  gets the full eight-lens final and fixes from the judges' notes, and the finale follows as in the
  older plan (complete mockups of every page, desktop and phone, and the draft standard).
- Rounds 15 to 17 may skip the final (`selection.py settle`): the screen's votes are enough to
  select on, and it saves the final's eight judges. Rounds 14 and 18 keep it.

## Slots (`slots.json`)

head, glass, list, figure, rule, signal, type, colour, controls, chat, light, foot. Each has a
description, the lenses expert in it, and a WEIGHT for how much it matters to the family and to the
owner's stated priorities (content over corners, typesetting, the light, calm colour): list 1.3,
type 1.2, light 1.1, head, glass, figure, signal, colour and chat 1.0, rule and controls 0.8, foot 0.6.
Each screen lens sees one card, so it votes only on the slots that card shows (`visible`: at most six
each, every slot visible to at least two lenses); the final's lenses vote on at most six of any.

The weight steers EFFORT, not verdicts: it shapes which slot a blind tweak is rolled for, which bin
part is drawn for an informed change and which parts an all-star takes. A slot a lineage has won more
than once is sampled half as often for each win (`saturate`), so effort moves on to slots not yet
settled.

## One generation

1. **Lineages** (`lineages.json`). Six heads, each a design and its history of what was kept and
   culled. Round 14 starts from six designs the earlier rounds passed over (the owner's judge's first
   pick, the strongest uncrossed lines and three wild ones); Desk Terminal, Joined is entered as the bar.
2. **Children.** Each head spawns two children. A child changes three slots, at most one change per
   slot, from three sources:
   - **informed**: a part from the parts bin (the best element in a slot, lifted from the design that
     had it), or in round 14 a feature the crossing rounds found;
   - **exploit**: a push, one step further, of what just survived in this lineage;
   - **blind**: a tweak rolled from `tweaks.json`, which has four small changes for every slot, and
     skips what this lineage has already culled.
   A child is made in one careful edit (`kind: "step"` in `stage.js`), no critic and no second draft.
3. **Screen.** Five lenses score every design as before, and also vote on elements: for each slot
   their card shows, the best design's element and a runner-up (`parts` in the judges' answer).
4. **Selection** (`selection.py`). Votes are tallied per slot (best 2 points, runner 1; a slot's
   expert lens counts 1.5 times; a final judge 1.5 times) and expressed as a SHARE of what the slot
   could have earned from the judges able to vote on it, so a slot few lenses see is not starved.
   Each child is compared with its parent slot by slot: a change WINS its slot when its share beats
   the parent's by 0.15, LOSES when the parent's beats it by 0.15, and a tie is kept only when the
   child's whole page beat the parent's by 0.15 on the screen. The round's best elements go in the
   parts bin (`parts-bin.json`: three per slot, earlier rounds' shares at half weight; an element
   needs a 0.25 share to be drawn from). `stage/parts.json` and `parts.md` say what happened.
5. **Extraction, on demand.** `breed.py` knows which parts it will use (informed changes, all-star
   lifts), so only those are extracted, only once (specs carry from round to round in `parts/`), by
   a cheap agent: `parts/<slot>--<design>.md` with what the element is, its markup and CSS copied from
   the design, what it needs and how to lift it. A child designer reads the spec instead of searching.
6. **Breeding** (`breed.py open rN rM`). Each lineage takes what survived: a child that won as a whole
   becomes the head; otherwise the winning changes are MERGED into the head (`stage: "merge"`, run
   before the children); a lineage with nothing kept stays as it was. A lineage in the bottom two for
   two rounds is retired and replaced by an ALL-STAR: the round's best head with the bin's best
   elements merged in where it is weakest. One wild newcomer from the dice (3 agents with crit and
   revision, as before) joins the lineages the next round if it places in the top half.

## Why this order of selection

- A change is judged where it is made: the slot's lens and votes, not only the page's mean. A page's
  mean moves about 0.2 for noise, so a single child cannot be told apart by it. Votes in the slot can.
- Several changes per child spend fewer agents per change and keep the page coherent; the slot
  boundary is what keeps them attributable.
- Everything lifted out is a copy of what was built, not a description, so a part carried over three
  generations is still exactly itself and does not drift.

## Running a round

From the harness root, round `rN` set up by `breed.py open` (round 14 by `steps_args.py`):

1. If `merges` is non-empty: `python3 stages.py split rN` writes `merge-K.json`; launch `stage.js`
   with each, then render each merged head (`./check.sh palettes/<id>.json` in `rounds/rN`).
2. Launch the design workflows from `design-K.json` (about four at a time on four cores).
3. `python3 stages.py prepare rN OUT...`, the screen (`screen-K.json`), then `python3 stages.py cut rN OUT...`.
4. Either the final (`final-K.json`, `stages.py tally`) and `python3 selection.py select rN`,
   or `python3 selection.py settle rN` for a screen-only round.
5. Launch `stage.js` with `extract.json` and with `finish.json`; `stages.py assemble rN OUT`.
6. `python3 breed.py open rN rM`.

## Files

`stage.js` (new stages `merge` and `extract`, the `step` kind, element votes in the screen and final),
`stages.py` (merge files; step in the origin names), `selection.py`, `breed.py`, `slots.json`,
`tweaks.json`, `steps_args.py` (round 14's setup), `cross_args.py` (the first, abandoned set-up of
round 14: 17 feature crosses, then six; kept for the record), `rounds/r14/` (the three argument
files). They go over the harness restored as in `../README.md`, after `../tour-and-cross/harness/`.
