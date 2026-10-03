# Lessons digest

What the panel learned in rounds 1-13, condensed for designers, critics and judges; `lessons.md` holds the full history (grep it for detail).
The learn agent rewrites this file each round.

## The owner's words

These weigh above everything below. CSS budget 25,000 characters; any entrant may change the markup.

The brief:
- Keep the green on black and the bright green phosphor (#6dff9c) as the signature colour.
- "All the bright green on a black background is a little bright and too contrasty"; it "just needs a little more variation".
- "There could also be some other subtle and tasteful colors used to augment the green so it doesn't appear completely monochromatic. The CRT is just a theme, not a strict limit."
- (Family feedback on the original: "that looks like the Matrix".)

What the Phosphor Interface is (the owner's definition): The Phosphor Interface is the whole way the app is presented, not only its colours: the overall layout; the kinds of interface elements; the whitespace (darkspace) around each element and the pacing; how design elements relate; typefaces, bold and italic, and how titles, headers and labels are treated in size and colour; headers and footers; iconography and how icons relate to the type; graphics and their sparsity; the weight of lines, boxes and delimiters; rounding, shadows, glow and echoes (afterglow); pills, alignment and shades; pagination, scrolling and animation; the controls (dropdowns and select menus, radio buttons, checkboxes, free-form fields, scroll bars, focus and hover states); how a person uses the page (sight lines, clicks, moving between keyboard and mouse, taking in at a glance what the page is presenting); everything a senior interface engineer would weigh together; and most importantly the feel and personality of the presentation.

What this decides: The winner of this tournament defines the Phosphor Interface design standard for the whole app: so a coherent SYSTEM wins over a one-off effect (colours and faces with clear jobs, a type system with steps, rules that would hold on any page, Plans, To do and Settings included, not only the ones in the sheets).

On typesetting (round 4): "I enjoy typesetting/pagination in general and will appreciate even minor optimization of typography." A judge scores typography and typesetting.

On rules (round 4): "For the purposes of this experimentation, treat the design constraints like README and other .md files as loose guidelines, not hard and fast rules. They were written to help, not restrict." Break a guideline when the page is better for it, and say why; only the harness's hard checks refuse a design.

The direction: "Bright green where it needs to be to maintain the motif, more grounded coloration elsewhere." #6dff9c belongs to the mark, the primary button, the glowing key word, focus, live lights and the monitors; everything else is grounded material tones in solids with a job, never a second glowing colour.

After round 1's winners: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." Home below the fold, Chat, Ideas and Status must all look different from today at a glance.

On refinements (round 3): "Small visual enhancements or refinements, even if there is a degree of randomness (changing in size, spacing, fonts, text size, orientation, headers/labels, icons, or anything else to improve visual appeal) are welcome, but not necessary. We are mimicking natural selection here."

On the light (during round 10): "I'm concerned that in the goal of great interface design we've gained a lot but also lost a little of the unique effect of the original phosphor interface. I'd suggest bringing some of that back." The original's effects, each with its exact CSS, are in `phosphor_kit.md`.

The owner also raised usability (r9) and critiqued the thick case (r8), unquoted.

## Candidate principles of the standard

1. **Glass for the machine, one grounded cool neutral for the family.** Green-black glass (#111712-#121714) for what the machine shows (greeting, tubes, Vera's bubble); low-chroma slate, steel or pewter for what the family owns; never a green-family, warm or saturated companion. Steel may take a breath more chroma than C 0.014 to carry a mood. [r4, r7, r8, r9, r10]
2. **The black ground is never greyed or tinted.** Calm comes from softer ink (about 12-12.5:1); gaps read as a switched-off screen. [r1, r2, r4, r6, r10, r12, r13]
3. **Structure never replaces grounded colour.** Every page, Status and Home below the fold included, shows the companion in a fill, not only in rules on black. [r3, r5, r6, r7]
4. **Every element has one drawing that holds on every page.** Read content in a slate tray, act content in a raised box, told apart by fill and elevation, not only an edge. Recolouring today's components fails. [r5, r6]
5. **Every list is one row read to an aligned facts column.** Title, a leader only where a fact follows, tabular facts in fixed sub-columns, the same on every page; the list names its facts by a head column or column heads (WHO, DUE, STATE). [r6, r9, r10, r11, r12]
6. **Every page opens on one head row.** Title, the page's figure (in its section colour, with a stacked mono unit-and-change line), and the one green primary action. Late shows in the figure as amber words linking to the filtered list. [r11, r12, r13]
7. **Light is a list, not a level.** The live things (mark, "mind", Send, now lamp, status lamps, focus, tubes) glow at full strength: exact #6dff9c, screenGlow 1.0, layered halo, bloom, scanlines, spill. Everything else is matte. Calm comes from a short list, never a dimmed tube; page glow near 0.9. [r10, r11]
8. **Phosphor light is information.** A lit tube draws that page's live data (trace, bars, spend, radar), sized to its content; no empty lit glass. A window's shape says what it shows; its marks are numbered to their rows. [r11, r12, r13]
9. **The machine and the family are laid out apart.** One cased, lit terminal holds tube, deck, contents and status; a square matte desk holds the family's rows. The terminal is sticky, sized to content, and folds to one lit line where nothing is live. [r12, r13]
10. **Only the machine is rounded.** Family surfaces are square, and glass and tubes carry the radius. [r8, r12]
11. **Each colour has one job, stated as a code.** #6dff9c live, amber late or needs a look, steel reverse video "here", denim a link, bone words. No surface is filled with a hue that has a job; amber is an edge, ring or words, never a fill. [r8, r9, r10, r13]
12. **State is coded by shape as well as colour,** one meaning per signal, with a legend: on = lit lamp, waiting = steel dot, off = pewter ring, needs a look = amber bar. Red only for something that has stopped. [r13]
13. **Red and teal are never companions, and selection is never red.** [r5, r6, r8, r9]
14. **A line is drawn only where there is order** (sequence, thread, timetable), ending in a lamp that says where you are; decorative lines read as a git graph. [r7, r9, r10]
15. **Type is a written scale of a few steps.** A head never ranks below its rows. Condensed sans heads, Plex Sans body, Plex Mono for figures, times and dates in fixed columns only, VT323 on the glass only. [r4, r6, r9, r10, r11, r13]
16. **Controls keep the drawing people know.** A box to tick, an underline to follow, a raised key to press, a filled steel cell for "here", a field as a filled bounded box. Controls, links and the bar are sentence-case words; tracked caps only for eyebrows, legends and speakers. [r8, r9, r10, r11]
17. **Each page has one place for its controls.** Every filter is a one-tap latched key showing its state; never a select duplicating a list. [r11, r12]
18. **Every focusable control shows the 2px #6dff9c ring,** open pickers and checkboxes included; visual order matches Tab order; targets at least 44px. [r5, r6, r9]
19. **A container is as tall as its content.** Balance columns by placing sections, never by stretching a tray or lit column. [r7, r12, r13]
20. **The machine speaks on lit glass at the top of Home.** The question is typed on the tube under a block cursor (warm-up from a line), as the page's largest head, with a green pool spilling from the glass. Never remove the lit greeting. [r8, r12, r13]

Overturned traps: calm by dimming (page glow 0.6-0.7, screenGlow 0.72-0.85) lost to principle 7 in round 10; the corner or top wash (later the cobalt "afterglow") is "a wash in the corner": drop it (r13).

## Pitfalls

**Colour and ground**
- Brand exactly #6dff9c (#70ef9d "lost its spark"); ground near #0b0e0d. Lifted or tinted grounds always lost: petrol #091211, teal-graphite (h169), Braun #161a17, instrument grey, walnut or brass (h73), plum-graphite (h304), navy cards #13171e (h259). Lifted #1a2025 panels grey the page; a board 5 dE above black is invisible.
- Warm colour diluted over green-black goes bronze or khaki: amber wash (50,42,23), rose corner (47,34,39)-(55,36,45), rust afterglow (32,22,16), Tea House bubble (56,54,41), kraft #383424, oat edges #473e33. In fills, brown reads coffee, terracotta rust bricks, mulberry wine, oxblood or red-with-green Christmas, orange-green-black Halloween.
- Green-family companions (sage or mint links, sage-leaf trays, jade, sea-glass, turquoise #62bcb8, teal h213, moss, lichen) count as more green. Accent and pill must be a clear non-green, never the brand.
- Borrowed looks: Dracula #bd93f9 (orchid #d797f0 is 6.4 dE off; violet h302-311), Tokyo Night #7aa2f7 (#84a8fd; Flight Deck's cyan about 5 dE), GitHub Dark #161b22 (slate), GitHub blue #4b8efe, Nord (steel ink), Solarized and Oceanic Next (teal), Claude.ai (warm-grey pewter with a serif).
- Green-black slate that worked: tray #0f1519, strip #161c20, surface #151b1e, edge #2e343b. A tray and a box must differ by more than 1.7 dE (tray #11161b, box #161b21, `box-shadow:0 1px 0 #0008`).
- Amber, one job. The setup tray keeps going olive-bronze ((19,22,18), (18,20,16)): keep `.setup,.trouble{background-color:#131612}` with an #644e29 border (edge samples about (100,78,41)); a later `.panel{border-color}` erases it, so use `.setup.setup`. No amber "today" disc (steel reverse instead); a bronze hover fill reads as selected; a yellow count beside amber "was due" blurs both. Section figures in wheat or bone under a 2px section cap.
- Red or rose beside the red off rings reads as alarm; red for now, late and error at once makes today an alarm; a madder #d8577a LED reads as recording (use green or amber).
- Steel "here": #89a2b5 and #7a93a8 too pale, use #5f7689-#7a93a6 with an #a9c4d8 cap; on the phone a tinted solid #26313a with a 2px #a7c2d5 cap, never a glow halo. Paper "here" is the brightest non-green thing (drop to #a9ab9f or steel); greige looks disabled.
- Ink near 12-12.5:1 (#d2ccbf, ink-2 #b3aea2, dim #96938a); smallest text at least 5:1 (4.66-4.92 failed; faint about #90887f).
- Screen at h145-155 (#7af2a8); #7ff3b9 and #58f0ba became a second green. Halo #2eac66 muddies the pool to (21,42,29): lighten to #36b872-#3fc27c. A teal halo round green looks off-register.
- Kind colour: no filled chips (tint `color-mix(in srgb,var(--kind) 14%,<surface>)`); cool kinds 14-16%, warm about 6% or in the ring lamp only; cyan day tiles at 9-10%, not 15% (teal). Pastel bands fail; a 2px cap and a number is "truly grounded".

**Hardware**
- Every leader ships the thick, 30px-rounded, .8rem pewter slab: thin it to a 2-3px bezel with a hairline lip, fine groove, vents and a power LED. Light, putty, navy, brass, brown or walnut cases are the brightest or most off-period thing on the page; keep dark graphite (#3f4449-#4b5055; #2c3135 for videotex). Tubes are 4:3, not 5:1.

**Light**
- Haze does not register: page washes, a scanlined wash under the bar, washes at 1.4-1.6 (invisible (21,28,35)). Lighting what is not live fails (the page title, bubble edges, seven full-brand Status bars), and a relight of lamps already lit is invisible in stills.
- Empty lit glass (a tube past its words, a 930px terminal column, a non-sticky full-height lit column): `align-self:start`, or `position:sticky` with `max-height:calc(100vh - bar)` and no inner scroll.
- Row hover afterglow has been invisible in stills five rounds: a 10-14% steel wash with a 2px sage #86d9a6 edge fading over about 1s, or drop it.
- A needle at zero shows nothing: add a limit tick, a ghost peak and the figure in words. A sweep beam must not cross text; map labels must not collide, dots must be links, never aria-hidden.

**Type**
- VT323 off the glass (heads, labels, input) reads as fuzzy display text; its tall-tick apostrophe shows at 40px in "What's"; a slashed zero in blooming VT323 reads as 8 (slashed zeros on Plex Mono only).
- Faded every time: serif titles (Fraunces or Newsreader, six times; Fraunces for figure-setting only was admired), italic decks, synthetic small caps, a global `"opsz" 40` (scope to `.page-head h1`), mono h1s, four or more faces, Recursive, mono on row names and forms, Figtree, one size for everything, Plex Sans Bold at 3rem, Archivo 400 body, ss01/ss02.
- Mono caps tracked above .05em, legends under .72rem, letterspaced mono phrases ("was due 2 days ago"), caps or icon-only nav and buttons (lost comprehension). Every row title underlined (hover and focus only); denim on non-links (month names); leaders running 600px (cap near 46rem).
- Scale: a 110px poster title (56-64px), 96px thin folios (costume), 10rem head columns that wrap (11.5-12rem, or stack below about 72rem), decks capped at 40-52ch with `text-wrap:balance`.

**Layout and use**
- Small targets sank every random and wild entrant (14-53 under 44px): 2.75rem hit areas, out of the line box by a negative block margin. Home at 2206-3574px (airy pacing, centred column, uniform tiles, empty right column) fails, as do stretched trays and dead voids.
- Ideas Search clipped at about 156px (`minmax(12rem,1.6fr)` floor); the Next up "›" orphan (`.next-up .next-more{display:flex;gap:.5ch;white-space:nowrap}`); nowrap scoped to `.crt .dist`; fixed facts widths (`3.5rem minmax(0,1fr) var(--facts,11.5rem)`), not subgrid; `order` or `display:contents` breaks Tab order.
- Chat: family on the right, date once and each time at its bubble, never a one-sided log, Vera once, the thread first on the phone.
- Duplicate filters (a Kind select beside a kind list) and head summaries that repeat their rows; say "4 more after Next up", not "5 plans" over 4 rows.
- Costume tells the family nothing: screws, hazard stripes, starfields, drafted dimensions, FIG captions, CONSOLE 03, T-minus, odometer wheels, numbered bar keys and Alt footers, wood grain, brass tags, window title bars, bracket buttons, a ring round every icon, a cursor after every h1, ECG pulses, a Tron floor. Raised keys everywhere make selection read backwards; navy keys look Bootstrap; underline-only fields lose the field; dots or needles for "here" are too weak.
- Bugs: `var(--brand)` when the sheet names `--green`; the box's resting edge `.ask{border-color:color-mix(in srgb,var(--brand) 38%,var(--line-2))}`; `input[type=checkbox]:focus-visible,input[type=radio]:focus-visible{outline:2px solid var(--brand);outline-offset:2px}`; `select:open,select:focus-visible{outline:2px solid var(--brand);outline-offset:2px}`; checkbox wells #1b2126 with a 1.5px #5b6570 edge, not black #0d1116, with a tick; `--legend-bg` for legend patches; phone tab-bar height; wrapped date lines; an 8px gap between chips.

## Failed reaches worth trying again

- **EFIS colour code** (Flight Deck, r9): cyan entered by the family, bone data, amber caution, green on, behind thin square faceplates. Again with every action a button (not a caps legend in a frame line), calm Status lamps, cyan near #8fbfdc.
- **Readout strip** (Flight Console, r11-12): zero-padded figures ("LATE 02" in amber was the fastest glance) and lit annunciator tiles on Status. Again as one global row of 44px links (LATE to To do filtered), sentence-case labels, Plex Mono figures, today in steel, no T-minus or HOLDS.
- **Ideas map** (Mapped, r13): home lit at the centre, numbered dots at true bearing and drive time. On Ideas only (keep Home's radar), labels apart, every dot a link.
- **Polar scope** (Zenith Desk, r12): plans as stars, a meridian thread through Chat. Again as a green polar scope on black, labelled stars whose angle is days out, sans type, steel bubbles.
- **Scope pulses and meters** (Bench Scope r10, Signal Catalogue r13): the coming weeks as pulses, Ideas in XY mode, LED countdown meters. On slate, a pulse less like an ECG.
- **Light-trail spine** (Grid Console, r13): section-coloured nodes and a visible afterglow, without the Tron floor, extended caps or outlined cells.
- **Dimension-line dates** (Blueprint, r13): "IN 2 DAYS" marks and a 24px baseline grid kept in the margins.
- **Picture light** (Night Gallery, r11) over each monitor, the most elegant scarcity idea; needs a 34-40px title step, no brass caps.
- **Engraved pictures** (r11): one per page head and empty state, about 48px, 1.75px lines, beside the icons, never replacing them.
- **Tube behaviour** (Attract Mode, r9): the power-on roll bar and keys and wells with clear affordance; Porcelain Atlas's airglow under the tube.
- **Never bred in**: shaded weekend columns on the Plans month (`.month :is(td,th):nth-child(n+6)` at a 60% slate mix), green-bar banding on slate trays, strung slate date tiles, large mono day numerals.

## What wins, by kind of entrant

- **Informed** took 1st every round from 5 on. The breed the panel names works, and the child beats its parent every time: carry the child, not both.
- **Random** won early on colour (rounds 2-4), then scored 5.0-5.7 from round 5: whole-page change, which the owner rewards, sunk by warm colour and usability rolls (keycaps, centred column, no icons, small targets). No random seeds since round 10.
- **Phosphor mutants** beat unlit parents in rounds 10-11 (7.48 against 7.04, 7.47 against 6.76, 7.52 against 7.00); by round 13 a relight of what was already lit was a near-duplicate (0.1-0.9% changed). Light must light something new.
- **Type mutants** land within about 0.1 of the parent (6.58, 7.11, 6.62; Monospaced lost at 6.32). Worth grafting: about six written steps plus .9rem and 15px steps, a 17px/1.6 body, a slashed zero on Plex Mono, Archivo's width axis on titles.
- **Graphics mutants** lose when pictures replace icons or are costume (6.75, 6.68) and win when a graphic draws data with a job (Metered's needle 7.49; Mapped's shape legend and map 7.78).
- **Crossovers** of same-family parents add polish, not identity; colour can sink one (Bakelite Video's oxblood). The best fix one parent's usability with the other's slate and 0 small targets (Slate Flight Console 6.96; Quote Board at Evening 7.76, carried).
- **Wild** entrants draw the most promise votes and lose on held rules (targets, warm or navy grounds, caps controls, costume), but their ideas spread: Docked Terminal and Tuning Dock became Desk Terminal, Videotex's typing on glass the Home question, Single Quote the page head.
- **Traits that spread**: green-black slate trays; the one-line row to a tabular facts column; head figures and column heads; steel reverse "here"; denim underlined sentence-case links; amber "was due"; Plex with condensed Instrument Sans or Archivo heads; the lit question on glass; latched keys; the terminal folding to Ready; light as data; a shape legend; 0 small targets; words in the bar; Send on the From row; a one-screen month.

## Carried into round 14

**Main lane**

- **Desk Terminal, Joined** (r13-idea-1, 8.33; docked terminal). One cased, lit terminal at the left of a square slate desk. On Home, scrollback (her screen, the day, Next up in inverse, the radar), her question as the 40px headline at the foot of the glass, the box as the tube's last rows over a graphite keyboard ledge; elsewhere a head row first, the terminal sticky or folded to a Ready line. Light as data on the desk: a white-hot NOW lamp with lit rail, a NOW tick in To do, a moving-coil spend meter. Fix: the 290-700px void under the terminal on Home (sticky, or the Contents plate back); the VT323 apostrophe in "What's"; an 8px gap between ways-to-start chips; Vera once on Chat and the thread first on the phone; a 60-80px green pool onto the desk; a 2-3px bezel; the needle's limit tick and ghost peak; "4 more after Next up"; drop the cobalt corner wash and the letterspaced "was due"; graft Mapped's shape legend.
- **Backlit Plate** (r13-idea-2, 7.8, 5 promise votes; long-persistence instrument). A square matte slate plate over one live phosphor screen; light shows only through cuts, where the machine is live ("mind" stencilled, Send a backlit key, pinhole lamps). Cut shape says what it shows: slot time, round window place, square Vera, 4:3 the screen. Its 40px condensed question with a curly apostrophe was rewarded. Fix: "mind" barely blooms; Status one bare column, Settings and Family only restyled (carry the plate grammar everywhere); spare glass in the 4:3 windows; engraved seams between bands; Add in the head; a round Next up radar window on Home; underline rows at hover and focus only; restore the lit pool; thin the case.
- **Quote Board at Evening** (r13-mut-3, crossover, 7.76, 4 promise votes; count board). Single Quote's head on Evening Listing's slate, steel and bone: condensed Archivo title, the figure in its section colour, a stacked unit-and-change line; registers to fixed columns below; a slate rail of numbered keys; #6dff9c only on live things, at full bloom. Fastest glance of round 13 and the only row afterglow that registered; its head was named the standard. Fix: costume (numbered bar keys 1-9, the "0" gear, the Alt footer); filters hidden in folds; the yellow To do "4" beside amber "was due"; Vera's last reply at headline size on Chat; the corner wash; the case.
- **Evening Listing, Traced** (r12-idea-1, 7.62; programme listing). Slate listing with head-column figures over small-caps labels ("4 PLANS"), WHO/DUE/STATE heads, a NOW divider between late and upcoming, "2 late" as a link, no Kind select, rails lit from now, a four-week trace of the plans in Next up's glass, rows that light and fade. Won type in round 12; one top four in round 13. Fix: the bronze setup-row fill that reads as selected; the case; the corner wash; a visible row afterglow.

**Wild lane**

- **Dessau Phosphor** (r13-wild-3, 6.47, 4 promise votes; style ranked it first). Each page a Bauhaus poster: a lowercase Outfit name beside a square of section ink, the page's one live figure on a round phosphor screen, four shapes with four jobs (circle light, square family, bar page, triangle needs a look) and a footer legend. Fix: the 110px title (56-64px); a matte poster below the fold; navy cards (h259), ochre, terracotta and pink; 31 small targets; To do back from cards with ISO dates to rows. Keep the round screen and shape legend, on graphite.
- **Folio Switchboard** (r13-wmut-1, 6.88). The videotex switchboard typeset as a contents page: equal cells, a sommaire Home, numbered pages, a green tube under every plate, Fraunces heads, the family's facts printed large (drive times, due days, counts, initials, folios); only the machine lights. Its figure-setting (fractions, superscript $, the raised h in "2h10", calendar leaves) was admired. Fix: 96px thin folios ("990", "900"); tracked or extended caps on nav and buttons; from round 12, `grid-auto-rows:min-content` with spans, sentence-case keys, one-line rows to a facts column, 32px plate titles, setup in the first and widest cell, and screens that say what the cells do not (late, next due, spend).

**New entrants this round**: a type mutant of Backlit Plate in a serif for the family's text (serif titles failed six times: judge body serif on its own evidence); graphics and phosphor mutants of Quote Board (drawings beside icons, not costume; light on something new); a crossover of Folio Switchboard's structure with Traced's colours; wild entrants in a hand-drawn sketch with a control-panel grid (hue 47) and a 1980s cockpit as one scrolling ribbon (hue 347); and a condensed, denser Dessau.

Carried into round 14 (chosen by advance.py for score and variety): r13-idea-1 Desk Terminal, Joined 8.33 (the best score of the round); r13-idea-2 Backlit Plate 7.8 (new family, not a near-duplicate); r13-mut-3 Quote Board at Evening 7.76 (new family, not a near-duplicate); r12-idea-1 Evening Listing, Traced 7.62 (new family, not a near-duplicate). Carried in the wild lane: r13-wild-3 Dessau Phosphor 6.47; r13-wmut-1 Folio Switchboard 6.88.
