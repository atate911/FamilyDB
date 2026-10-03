# The harness from round 14: cheaper rounds

The files in `harness/` replace their namesakes in the harness restored from
`harness-rounds-8-13/harness-rounds-8-13.tar.gz` (`cp -r harness/. "$H/"`; see "Restoring it" in
`../README.md`). They
make a round cost far fewer tokens. The judging still tells the designs apart, at the cut where it
matters, better than before. The design lanes and the wild lane are unchanged.

| File | What changed |
|---|---|
| `render.js` | Shoots 8 pages instead of 13. It drops Sign in, the 404, General settings, the whole new-idea form and the phone's Chat. The form is still visited for its controls, and Sign in is still visited and health-checked. |
| `contact.py` | Draws four **cards** per palette (`cards/<id>-home.png`, `-lists.png`, `-use.png`, `-close.png`). Each is at the size a model reads without shrinking, about 1,500 tokens. `--cards ID` draws one palette's. |
| `check.sh` | Draws the palette's cards after a full render. |
| `stage.js` | New `screen` and `final` stages. Designers, critics and the planner read cards and the digest instead of full-size shots and `lessons.md`. The planner reads a brief pack instead of three whole results files. Agents read images several to a message. The curator and the "you left some out" re-asks run on a cheaper model. The learn agent also rewrites the digest. The old `judge` stage stays for a round with `"panel": "full"`. |
| `stages.py` | `split` also writes `stage/brief-pack.md`. `prepare` writes `candidates-short.md` and `screen-K.json`. New `cut` command; `tally` handles the final; new `replay` and `usage` commands. |
| `advance.py` | `open` writes `"panel": "screen"` (`--panel full` for the old panel). Carry rules read `beatToday`, so a design cut at the screen is compared with today on the screen's own scale. The "Carried into" line also goes to the digest. |
| `harness/README.md` | The designers' brief, updated for the cards and the shorter page list. |
| `lessons-digest.md` | About 4,000 words in place of `lessons.md`'s 92 KB (about 23,000 tokens, growing every round). It holds the owner's words verbatim, the candidate principles, pitfalls, failed reaches, what wins by kind of entrant, and the carried designs with their fixes. |
| `rounds/r14/args.json` | Round 14's setup as saved, with `"panel": "screen"` added. |

`../gallery/build_gallery.py` also learnt the screen's lens names.

## Why: where the tokens went

No per-agent token counts were kept for rounds 1 to 13, so this is an estimate. `python3 stages.py
usage <workflow transcript folders>` measures it from round 14 on.

- **Judging was the bulk of it.** Each of eight judges was told to open about 70 images: 17
  designs × 3 strips, about 11 contact sheets and zoomed shots. A contact sheet of 17 pages
  reaches a model at about 114 px a page, which is too small to read, so judges zoomed into
  everything. Images were opened one per message, and every message sends again everything
  already read. So a judge's cost grew with the square of the images it opened, around 5M input
  tokens each.
- **Every agent read all of `lessons.md`**, which kept it in context for every message after.
- **The planner read three results files in full**, about 90,000 tokens each.
- **Designers opened five full-size shots at least twice**, and critics opened every page.

## Why the judging still tells designs apart

From rounds 9 to 13's stored scores (`python3 stages.py replay`, and the analysis behind it):

- **The lenses agree closely.** Average rank agreement (Spearman): system and skeptic .93,
  interaction and usability .87, system and interaction .86. Any two of system, interaction and
  skeptic picked the same winner in all five rounds.
- **Style is the odd one out.** It agrees with the others at only .1 to .4, and dropping it never
  changed a top four. It is the creativity signal, and the eight-lens mean drowned it out. In the
  screen it is one of five.
- **The cut was a coin flip.** The 4th and 5th places were 0.02, 0.22, 0.01, 0.01 and 0.01 apart.
  A mean of eight judges has a margin of error of about 0.2. The final's forced order separates
  what absolute scores cannot.
- **The screen keeps the real top four.** With a cut at seven (and two more for promise votes),
  every round's real top four reached the final.

## The round, in stages

1. `stages.py split rN`, then a `stage.js` design workflow per `design-K.json`. These are as
   before, except for what the agents read.
2. `stages.py prepare rN OUT...` renders and draws the cards, then writes `screen-1..3.json`.
   Launch `stage.js` with each, all at once.
3. `stages.py cut rN OUT...` merges the screen and chooses the finalists (seven by score, plus
   up to two with two or more promise votes). It writes `final-1..4.json`. Launch `stage.js`
   with each.
4. `stages.py tally rN OUT...` puts the finalists first by their weighted order (soul still
   counts 1.5), then the rest by the screen's mean. Then the finish stage and `assemble`, as
   before.

What each lens reads (`CARDS` in `stage.js`): in the screen, one card per design. The owner's
judge and style read `home`, soul reads `close`, systemuse reads `use` and the skeptic reads
`lists`, so the five together see every page. In the final, two or three cards per finalist.
Promise votes, and so the wild lane, come from the screen, which sees the whole field.
