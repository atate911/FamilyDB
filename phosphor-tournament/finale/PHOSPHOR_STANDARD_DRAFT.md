# The Phosphor Interface standard: draft for the owner

Status: **a draft, for the owner to read and decide on.** Nothing under `src/` has been touched.
Everything here comes from the tournament in this folder (rounds 1 to 21), judged by the panel
and calibrated by the owner's notes (`../harness-selection/owner_judge.md`). Where the draft says
"the panel found" it means measured judgments; where it says "the owner said" it quotes the owner.
Where it is a recommendation, it says so.

`docs/STYLE.md` is the record of the look as it stands. If the owner adopts a design from here,
the change goes in the same pull request as an updated `docs/STYLE.md`, per `CLAUDE.md`
("a change updates it in the same change, and tests that pin today's markup change with it").

## 1. The brief, in the owner's words

- Keep the bright phosphor `#6dff9c` on green-black as the signature, and light it **only where it
  means something**; add grounded supporting colour.
- "The original intent of the phosphor interface was the bright, glowing, and slightly haloed look
  of a green screen CRT monitor. Let's not lose that DNA in an effort to make a clean hyper modern
  design interface." The DNA is "glowing dots on black background, highlights, scan lines".
- Secondary colours should **support** the green, not compete with it. Warm browns, tans and pinks
  read as off-motif; a cool companion is closer, in a measured amount.
- Fine line art that draws structure (tracks, stops, ticks, rings, margins) is "high style", and
  the owner wants it echoed through every page.
- Change should show in the **content** of the pages, not only a corner; "nearly identical" is the
  failure.
- "All things considered, simplicity should be favored over complexity, when simplicity is equally
  effective."

## 2. What the tournament found

Seven rounds of natural selection (14 to 20) over 77 children and wild designs, then a
championship of eight (round 21), each judged by eight lenses (feedback, soul, style, system use,
interaction, type, usability, skeptic). What survived, and why:

1. **Line language as structure wins on every lens that is not purely typographic.** Rails with
   nodes, a lit NOW, a timetable margin, a thread hung from Vera's mark. It was the owner's
   favourite and it was the most-voted signal and list element (53% and 44% of the votes in the
   championship).
2. **Type is the biggest single change a family sees.** A heavy condensed display face over small
   tracked mono kickers, with numbered index heads, scored 83% of the type votes.
3. **Light belongs on four things:** the key word of Home's question, the glass (monitors, the
   typed question), live lamps and the NOW line, and the primary key. Designs that spread it lost
   marks for glare ("the Matrix"); designs that removed it lost marks for the soul lens.
4. **Grounded companions work when each has a job** (a section, a kind, late, now) and sits on a
   cool green-black slate. Cream and brass, walnut, beige monitor cases and pink rails were
   marked down by the owner's judge in every round.
5. **Controls that look like controls**: latched pills instead of selects, a primary key that is
   visibly the primary key, a Send that says Send, 44px targets everywhere.
6. **Overdue must read as words.** "Was due 6 days ago" in amber beat a coloured dot alone on
   usability and skeptic.
7. **What did not survive:** costume systems (the blueprint sheet, the 1984 desktop with pixel type,
   the patch bay with wood and rivets) were the most distinctive and the least usable or the least
   CRT; the judges liked their ideas, not the whole.

## 3. The signature (fixed)

| | |
|---|---|
| Brand / screen green | `#6dff9c` exactly. On the mark, Send, the key word, live lamps, the tubes, focus. |
| Ground | green-black. Hue at or under 200 (OKLCH) so it never reads as navy; roughly `#071211` to `#0a0d0b`. |
| Green share of colour | well under today's 83%. The finalists run 22% to 76% by page; target under about 60% on a content page. |
| Contrast | text on ground at least 4.5:1 (the finalists measure 12.6 to 16:1 for ink, 14.7 to 15.3 for the green). Calm the ink by warming or cooling it a step, not by dimming it below 4.5. |

## 4. Light

Kept from the original page's own marks (`phosphor_kit.md` in the earlier rounds): the layered
halo on lit words, the bloom and scanlines on the green screens, the live lamps, the afterglow.

- **Allowed:** the key word of Home's question (a scanlined face, bright at the top edge,
  deepening a little toward the foot, with a two- or three-layer halo); the glass (Next up,
  the typed question, the Status gauge, the radar); live lamps and the NOW node with its lit run;
  the primary key; focus.
- **Not allowed:** a halo on headings, row titles, icons or every card; scanlines across the page;
  a lit panel in a list; the question mark dimmer than the word it ends (round 19 and 20 found
  this twice).
- **Budget:** a content page has at most one lit word, one glass, a handful of lamps and one lit
  key. If a change adds a lit thing, it removes or justifies another.
- **Motion:** lamps may breathe, screens may switch on, the afterglow fades; everything stops under
  `prefers-reduced-motion`; `forced-colors` and `prefers-contrast: more` drop the bloom.

## 4a. Colour

- **Neutrals:** cool slate plates on the green-black (`surface` about `#0f1718` to `#161c20`),
  card edges a step up, ink a step warm or cool of white. Bone or cream ink is acceptable (the
  Desk Terminal and Track Diagram finalists use `#ddd0bb`); the Lit Index finalist uses a cool
  bone `#e1ebe3`. Nothing browner than that.
- **Sections** (each has one colour, kinds each one colour, never colour alone):
  Ideas lilac `#b58cec`, Plans cyan `#70dcf4` (blue `#9bcafe` in the Grid Console), To do lemon
  `#f7dc78`, Family / people amber `#ffb850`, Wishes pink `#ff9fd0`, Seasons coral `#ff956c`,
  danger `#ff6b6b`. Keep them low in chroma on the page body and let them rise only on a rule, a
  numeral, a lamp or a kind label.
- **Amber is reserved** for late, needs-a-look and today. A design that spends amber elsewhere
  loses the signal.
- **Steel / denim** (`#a0bccb`, `#77ced5`) is the accent for links, latched keys and rail lines,
  so green stays on the live things.

## 5. Line language

- One rail per list: a Coming up track with a lit NOW dot, a To do track with a lamp at each item,
  an amber ring on the overdue one, a timetable margin of due times to its left, a short tick
  from each lamp to its row, and a foot at "All N".
- Chat hangs from one vertical rail under Vera's mark, each speaker a stop, times in the left
  margin, ending in a lit ring at the box.
- Section heads are set into their rails or sit over a ruled cap in the section colour.
- The bar marks the current page with a short rule or dot under it, not a pill.
- A line must mean time, order or belonging. A rail that means nothing, a stranded control or a
  grid behind everything counts against a design (the Blueprint and the Grid Console both lost
  marks for it).

## 6. Type

Three voices, as `docs/STYLE.md` already says, with the display voice changed:

| Voice | Use | Faces the finalists used |
|---|---|---|
| Display | page titles, big figures, the Home question, row titles in ledgers | Archivo at its narrowest and heaviest (condensed, weight 800); a high-contrast serif in the Track Diagram finalist |
| Read | body, rows, buttons | IBM Plex Sans or DM Sans |
| Machine | kickers, folios, times, tabular facts, small caps labels | IBM Plex Mono, DM Mono or Martian Mono |
| Glass | only on the screens | VT323 |

- **Kickers and tab labels are at least 12px** (13.6px worked: the Lit Index finalist). A 9 to 11px
  mono caps label was cited by usability and type in every round it appeared.
- **Numbered index** (00 to 05 in the bar, over each page title, on Home's banks): the panel
  liked it; the usability lens asked for plain words beside the numbers for a first-time visitor.
- **Titles are capped** one step on Settings and To do so a list of settings does not become a
  wall of display type.
- **Figures** are tabular and slashed-zero; a counted figure sits on the title's baseline with a
  small tracked unit.
- No more than four faces on a page (the digest warns at four).

## 7. Page by page (what the finalists agree on)

- **Home:** the question is the first stop; the box with a labelled full-width Send is the
  second; ways to start under it; Coming up and To do as rails. The question may be a poster
  (Lit Index) or a line typed on the glass (Desk Terminal, Grid Console), not both. A "Finish
  setting up" band leads Home while setup is unfinished, as a strip of one line.
- **Chat:** a thread on a rail, sender chips, times in the margin; on a phone the select stays on
  one line and the textarea shows at least three lines (Track Diagram Rail Keys broke this and
  lost marks).
- **Ideas:** a card grid with kind labels in the kind colour and a hatched or ruled swatch;
  filters are keys or pills, not three selects (only To do got pills in the Grid Console finalist;
  carry them to Ideas).
- **Plans:** month with marked days; a list view; the clock dial earned nothing in two rounds.
- **To do:** the ledger: tick well on a fine lit rail, title, dotted leader, who and due in
  tabular columns, amber "was due N days ago", a visible primary Add key, latched Show pills.
- **Status:** one glass with the spend gauge (limit flag, lit needle), a Contents plate,
  lamps for what is connected.
- **Settings:** parts with a lamp and a one-line state; the Personality, model and spending
  pages as a sidebar list; titles capped.
- **Family, Memory, Wishes, You, Setup, Sign in, 404:** rendered for each finalist in
  `mockups/`; the panel judged them only through Home, Ideas, Chat, Status, Plans, To do and
  Settings, so these are checked by eye, not by the panel (see section 12).

## 8. Components

| Part | Standard |
|---|---|
| Primary key | green fill with glow, 44px minimum, one per page, at the right of the title |
| Send | labelled ("Send") plus the icon, full width on a phone, beside a 44px mic |
| Filters | latched pills or keys with a lit dot on the one in force; links, so they work without a script |
| Checkbox | 1.5rem frame that lights and holds a standard tick; radio the same with a dot |
| Select | full border, caret in its own cell, a check on the chosen option, strong focus ring |
| Monitor | thin graphite case, never the dominant pewter slab; one to a page; shows something true (plan scope, spend gauge, radar) |
| Docks | a tube and a Contents plate under the question; ends equal; collapses on narrow pages |
| Bar | labelled, current page marked by a short rule; phone tab bar with icon and label, 44px |
| Foot | a lit UP lamp and a quiet line; optional drawing-sheet block is a Blueprint idea, not required |

## 9. Accessibility and floors (do not move)

From `docs/STYLE.md` "What does not move" and the tournament's measurements: contrast measured;
focus always visible; 44px targets (the finalists report 0 to 2 small targets on Home); no
sideways scroll; smallest text at least 12px (the harness warns below today's 11.52px; the
standard asks 12px); reading, every form and sending a message work without a script; scripts only
from the page itself (`script-src 'self'`); templates escape by default; no page view is a model
call; Vera is never drawn.

## 10. The simplicity rule

The owner's tie-breaker, applied in every round from 14: a part that adds nothing a family
member would notice or use counts against a design; "equally effective" is the condition. In
practice it cut: corner ticks on every cell (kept on the active cell only), hatched empty
plates, plates behind every band (kept on three), a second lit word, the clock dial on Plans.

## 11. The four finalists (championship order)

| # | Design | Final | Character | Best at | Weakest at |
|---|---|---|---|---|---|
| 1 | **Grid Console, Keyed** (`r20-mut-3`) | 7.84 | Teal-black console: lit rails with keyed nodes, a NOW lamp, condensed heads with coloured numerals, a perspective grid floor under the glass, latched pills and a green Add key | consensus (top four on all 8 lenses), light, rule, signal, controls | busy lines; the lit corner is faint at half size; Ideas still uses selects |
| 2 | **Desk Terminal, Even Dock** (`r20-mut-1`) | 7.59 | A glass column with a tube on every page, the question typed on glass with a LISTENING line, a Contents plate, ledger rows | soul, glass, usability, controls | closest to today's structure; setup-first pushes Coming up below the fold |
| 3 | **Track Diagram, Rail Keys** (`r19-mut-2`) | 7.48 | Serif titles with counted figures, the rail from Vera's screen to the box, amber stamps | list, signal, type elegance | phone composer clipped (textarea, wrapped select); full-width Add bar is glare |
| 4 | **Lit Index, Ledger Rail** (`r20-mut-2`) | 7.40 | A poster question with a scanlined lit MIND?, numbered index, a ledger To do, a rail chat | identity, type, head, rule | poster height on a phone; nav letters are cryptic; light mostly on Home |

Scores are the weighted mean of eight lenses (soul 1.5) inside the championship field and are not
comparable with other rounds'. The championship's other four were the bar (Desk Terminal Joined
6.81), Blueprint Lit Scale 6.68, Patch Bay 6.02 and Green Desk 5.90.

## 12. A kit of parts (the best element in each slot)

From the championship's element votes (share of the points the slot could earn):

| Slot | Best element | From |
|---|---|---|
| head | large condensed numbered title over a coloured rule, action beside it | Lit Index (41%) |
| glass | the question typed on a glass strip with a cursor, a LISTENING line and a bar scope | Desk Terminal (89%) |
| list | To do on a lamp rail with the was-due margin and a NOW lamp; Ideas as a ruled table | Track Diagram (44%), Desk Terminal (35%) |
| figure | spend gauge with limit flag; counted figures beside titles | Grid Console (22%), Track Diagram (19%) |
| rule | heavy ruled caps in the section colour with numbered index | Lit Index (33%) |
| signal | rail with amber late dots running to a lit NOW node | Track Diagram (53%), Grid Console (32%) |
| type | condensed heads over mono kickers, numbered keyed numerals | Lit Index (83%) |
| controls | full-width Send, 44px mic, check-marked select, latched pills | Desk Terminal (39%) |
| light | bloom on the key word and gauge, a lit rail with glowing nodes | Grid Console (44%) |
| foot | evenly docked labelled tabs, active underline | Desk Terminal (12%) |
| colour, chat | no consensus; chat had no votes in the championship because its cards show it little | |

## 13. Recommendation (the owner decides)

- **Option A, lowest risk:** adopt the Grid Console Keyed as it stands. It won the championship,
  was in the top four of all eight lenses, and keeps the owner's line language and the glow.
  Fixes to take with it: carry the pills to Ideas, raise the 10 to 11px mono labels to 12px, make
  the lit corner visible at half size or drop it, thin the grid floor.
- **Option B, the composite:** Option A with three transplants the votes support: Desk Terminal's
  typed-question glass with its LISTENING line (glass, 89%), the Lit Index ledger To do (list,
  84% when it was tested), and the was-due words. This is more work and less simple; apply the
  owner's simplicity rule before accepting each.
- **Option C, the boldest:** the Lit Index Ledger Rail, for its identity, with the fixes it was
  given (cap the poster on a phone, plain words by the numbers). It had the strongest type and
  the weakest line language, and its light is mostly on Home.
- Not recommended: the Blueprint, Patch Bay and Green Desk as wholes. Take ideas from them (the
  title block, a thin rail with a NOW scale), not the costume.

## 14. What is not known

- The panel saw Home, Ideas, Chat, Status, Plans, To do and Settings. The other pages are in
  `mockups/` and were never judged.
- Every judgment was on the demo data: one family, short names, no long titles, no empty
  states, no error states, no kid's view, no dictation mic, no Telegram-only member.
- Stills cannot show motion: breathing lamps, the afterglow, the screen switching on. Judges
  scored what they could see.
- The harness renders in one Chromium; real phones and Safari have not been checked, including
  `oklch(from ...)` and `appearance: base-select` used by some finalists.
- Changing the page means changing `src/familydb/web/static/style.css` and templates, the
  tests that pin markup (`tests/test_web.py` and the ones named in `docs/STYLE.md`), and
  `docs/STYLE.md` itself, in one change. The evals are untouched, as no prompt changes.

## 15. How it was made

Rounds 14 to 18 selected on elements as well as designs (twelve slots, votes per slot, children
changed three slots each, a parts bin). Rounds 19 and 20 refined the survivors from the judges'
notes with no blind mutations. Round 21 was the championship. A selection round used about 3.5 to
4M subagent tokens with the cheaper panel; a refinement round about 2M. Details:
`../harness-selection/README.md` and the per-round files in `../harness-selection/rounds/`.
