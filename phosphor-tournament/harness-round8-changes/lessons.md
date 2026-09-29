# What the judges have learned so far

Read this before designing. It is the panel's accumulated feedback across rounds: follow it
unless your direction has a reason not to, and then say the reason.

From round 8 the rules changed, so read the older notes with this in mind. The css budget is
25,000 characters, so the "N of 15,000" notes below are history, not a limit. Every entrant may
change the page's markup. Random entrants roll structure (layout, type system, controls, icons,
motion, pacing) as well as colour; they get a studio crit and one revision; and the best of them
has a protected place among the four carried on. Mutants make two or three changes, one of them
structural, and one mutant each round is a crossover of two carried winners.

## The brief, in the owner's words

- Keep the green on black and the bright green phosphor (#6dff9c) as the signature colour.
- "All the bright green on a black background is a little bright and too contrasty"; it "just
  needs a little more variation".
- "There could also be some other subtle and tasteful colors used to augment the green so it
  doesn't appear completely monochromatic. The CRT is just a theme, not a strict limit."
- (Family feedback on the original: "that looks like the Matrix".)

## What the Phosphor Interface is (the owner's definition)

The Phosphor Interface is the whole way the app is presented, not only its colours: the overall layout; the kinds of interface elements; the whitespace (darkspace) around each element and the pacing; how design elements relate; typefaces, bold and italic, and how titles, headers and labels are treated in size and colour; headers and footers; iconography and how icons relate to the type; graphics and their sparsity; the weight of lines, boxes and delimiters; rounding, shadows, glow and echoes (afterglow); pills, alignment and shades; pagination, scrolling and animation; the controls (dropdowns and select menus, radio buttons, checkboxes, free-form fields, scroll bars, focus and hover states); how a person uses the page (sight lines, clicks, moving between keyboard and mouse, taking in at a glance what the page is presenting); everything a senior interface engineer would weigh together; and most importantly the feel and personality of the presentation.

## What this decides

The winner of this tournament defines the Phosphor Interface design standard for the whole app: so a coherent SYSTEM wins over a one-off effect (colours and faces with clear jobs, a type system with steps, rules that would hold on any page, Plans, To do and Settings included, not only the ones in the sheets).

## The owner, on typesetting (from round 4)

"I enjoy typesetting/pagination in general and will appreciate even minor optimization of typography." A sixth judge now scores typography and typesetting, and any palette may
carry typographic refinements (README: "Typesetting"), whatever its roll.

## The owner, on rules (from round 4)

"For the purposes of this experimentation, treat the design constraints like README and other .md files as loose guidelines, not hard and fast rules. They were written to help, not restrict." Everything in this file, the harness README and docs/STYLE.md is a guideline:
break one when the page is better for it, and say why. Only the harness's hard checks refuse a
palette (the owner's asks, the page's integrity, plain legibility). From round 4 a palette may
also use a library of open-licence faces (README).

## The owner's direction (weighs above everything below)

"Bright green where it needs to be to maintain the motif, more grounded coloration elsewhere." The bright #6dff9c belongs where the Phosphor motif needs it: the mark,
the primary button, the glowing key word, focus, live lights, the monitors. Everywhere else the
colour should be GROUNDED: natural, material, real-world tones (stone, clay, slate, linen, ink,
wood, moss, denim, pewter) carried in solid things with a job (cards, bubbles, headings, labels,
lines, fields, the bar), not more glow, neon or coloured light. A second glowing colour is not
grounded; a calm, solid, lower-chroma companion is.

## The owner's word after seeing round 1's winners

"Those look nearly identical... the changes need to reflect more of the page content, not a
wash in the corner or a few icons." A palette whose difference from today is confined to the
greeting's corner, the links and the Home pill has failed, however tasteful. Carry the
companion and the calmer tones across the whole page with every role your README offers
(from round 3: heading, label, card-edge, secondary, bubble, bezel, bar, ambient and a tinted
surface), so Home below the fold, Chat, Ideas and Status all look different from today at a
glance, while the bright #6dff9c on green-black stays the signature.

## The owner, on refinements (from round 3)

"Small visual enhancements or refinements, even if there is a degree of randomness (changing
in size, spacing, fonts, text size, orientation, headers/labels, icons, or anything else to
improve visual appeal) are welcome, but not necessary. We are mimicking natural selection
here." So from round 3 a palette may carry small CSS refinements (README, "Refinements beyond
colour"): random entrants bring mutations, informed entrants breed the winners' traits, and
winners carry theirs on unchanged.

## Round 1 (twelve directions, five judges)

- The companion only shows in three places: the greeting's top-right wash, the accent (links,
  title tiles, the current place in the bar on Home, Vera, Status and Settings, and the phone's
  Home pill), and the top afterglow (invisible at topGlow 1.2 or less). A companion must be
  clearly visible where it lives, or the family will not notice it.
- Warm companions (amber, coral, brass, sand) turn bronze, khaki or brown when diluted at low
  alpha over green-black; cool ones (lilac, violet, slate blue, cyan) stay clean. Sample the
  greeting's corner pixel (README) and compare with today's (23,33,35).
- Stone, sand and parchment links read as plain text or as disabled: a link must look like a
  link (clearly coloured).
- A warm accent (amber, coral) on Status sits beside the red "off" rings and the amber "needs a
  look", and reads as a warning.
- Page glow below about 0.6-0.7 flattens the Send button and the glowing "mind": calmer, not
  lifeless.
- Lifting the ground greys the black (slate) and a strongly tinted ground (teal, olive) turns
  the page one colour family: both weaken the green jumping off a switched-off screen. Soften
  the ink rather than greying the black.
- A teal halo round a green core looks off-register: a phosphor blooms in its own colour.
- All-analogous companions (teal, cyan) still read as one hue family.
- Ideas, 404 and Sign in look the same in every palette: the radar monitor and two filled green
  buttons dominate them. A slightly calmer screen helps; the rest is layout, not palette.
- Changes too subtle to notice at a glance score badly with every judge: the family must be
  able to see the difference from today.
- Mint and lilac (a soft complementary violet with real jobs) was the clear favourite; a
  second phosphor (amber) was the most period-true; the calmest palette (Night Shift) answered
  "too bright and contrasty" best but its companion was invisible.
- Watch for resemblance to editor themes (Dracula's purple and green on blue-grey, Nord,
  Solarized, Gruvbox, Tokyo Night): it makes a palette feel borrowed.
- New floor from round 1: the accent must stay apart from the section colours (it sits beside
  them in the bar and the phone's tab bar).

## Round 1 polish and final panel (five finalists)

Final four carried into round 2: Aurora (7.7), Mint and Lilac (6.9), Moss and Brass (6.8),
Night Shift (6.5). Amber Companion (6.2) dropped out.

- Keep the brand exactly #6dff9c: every judge marked Night Shift down for easing it to
  #70ef9d ("the Send button visibly lost its spark"). Calm comes from the ink, the glows and
  the monitors, not the signature.
- Keep the ground near today's #0b0e0d: a lifted ground reads grey at noon and a blacker one
  adds contrast. One neutral temperature: lavender lines on green surfaces read as two.
- Aurora won because its azure wash is the one companion that reads as LIGHT (samples
  (21,38,49)), its sky-cyan pill is the crispest active state on the phone, and the signature
  is exact. Its links were called a little stock ("generic dark-mode link"), and its top
  afterglow over a teal-leaning ground came out slate-teal.
- Moss and Brass is the only palette that changes the mood BELOW the fold (warm ivory ink and
  warm surfaces all the way down Home); the others look like today once the greeting scrolls
  away. That made it an identity, not an accent, for the style and soul judges. But its warm
  lamp wash still sampled bronze (50,42,23), and brass links above the orange "Finish setting
  up" panel and a brass pulse on Status read as warnings to the product and skeptic judges.
- Lilac is the most distinctive single companion (green's complement), but at low chroma it
  goes grey-mauve on Status and in the phone pill; its afterglow greyed the top of the page.
- The cool companions keep Status (a health page) reading "fine"; warm ones put a caution
  pulse at its top.
- Still unsolved by any palette: Ideas, Sign in and 404 stay about 95% green (the radar monitor
  and filled green buttons). A palette can help only through calmer monitors (screenGlow about
  0.75) and a visible top afterglow; the rest is a component change.
- Small cross-palette note: the "Send where I am" location icon uses the people orange, which
  beside an unticked box can read as an alert.

## Round 2

Top four, carried on: Evening Study r2-idea-3 (6.9), Late Set r2-rand-2 (6.86), Blue Hour r2-idea-4
(6.8), Lamplit Room r2-idea-1 (6.56). All four of round 1's winners fell: Aurora 6th at 6.08, Moss
and Brass 5.62, Mint and Lilac 5.5, Night Shift 4.66.

- Why the order: each winner topped a different lens. Evening Study (style 7.6) gave Lilac's orchid
  enough chroma (#d797f0, C 0.14) to read orchid on Status (green share 86.7% down to 57.8%) and in
  the phone pill (74,56,81), inside Moss's ivory room. Blue Hour (feedback 7.6, product 7.5) was the
  calmest palette with #6dff9c and the black exact. Late Set (skeptic 7.0) changed the most of the
  page. Lamplit Room (soul 8.0) kept warmth in opaque solids, cool colour in light, and real P1
  monitors. Round 1's corner-and-accent pattern now scores as "nearly identical": Aurora and Radar
  Flash moved least below the fold (mean dE 0.82 and 0.65), and Aurora's sky-cyan link reads stock.
- Late Set refines round 1's praise of Moss: ivory ink and warm cards are a temperature shift, felt
  rather than seen (Lamplit's cards (19,23,16) against today's (18,22,21)). Share of pixels more
  than 5 dE from today: Late Set 4.1% of Home below the fold, 6.9% of Chat, 18.6% of the phone;
  every other entrant 1.0-2.6%, 1.3-3.2% and 7.5-11.7%. The blue went into job-bearing solids, not
  the ground: surface-3 #18283a (the family's chat bubbles, the current place, the phone's tab bar,
  date tiles, "in N days" pills), field #091119, line #1d3047, line-2 #2b3e58, edge #597398, over a
  near-green-black ground (#091010). Baker's Dawn's tinted petrol ground (#091211) failed again.
- Never leave the accent on the brand. Late Set's accent and lit defaulted to #6dff9c, so the links,
  title tiles and phone pill kept the glare exactly where the owner clicks, and every lens marked it
  down. The winners put links and the pill on the companion and lit and outing on a sage (#86d9a6,
  #89dfa8, #8adfb0), leaving the full green to Send, "mind", the mark and the monitors. Judges'
  accents for Late Set: periwinkle #9fb2f6 to #a8b2fb (check outing #6daafb, plans #57d4ee) or a
  quiet mint #8ce7bf to #8fd9b6.
- Every judge's fixes breed Late Set's device into the others: a companion-tinted surface-3 (and
  bar), a non-green accent, ink near 12:1. Over a warm room tint surface-3 only and keep the lines in
  the room's temperature: plum #201d23 to #221c27 for Evening Study (bar about #141119), cobalt
  #1a2130 to #1b2030 for Blue Hour, #1b2128 for Lamplit. If the lines go blue the card fills must
  follow (Late Set's steel lines over #0f1717 cards read as two temperatures; surface about
  #0f1619). Moss-warm cards and the monitor bezel read khaki or "military"; neutralise them (surface
  #131614, surface-2 #181b19) and let the ink carry the warmth.
- Calm is measured in the ink, with floors under everything else. Ink in the 12s (Blue Hour 12.1,
  Late Set 12.3, Baker's Dawn 12.3) read calmer; 13.1-13.6 read as today with a tint; Lantern
  Night's 14.95 barely moved. Aim near 12:1 (ink #d2ccbf, ink-2 #b3aea2, dim #96938a) but keep the
  smallest text at 5:1 or more (Blue Hour's 4.92 was the lowest). Round 1's calmer monitors have a
  limit: Blue Hour's whiter #7ff3b9 (h160) at screenGlow 0.65 and Baker's Dawn's sea-glass #58f0ba
  (h166) became a second green and lost the period screen; keep the screen at h145-155 (#7af2a8)
  and screenGlow 0.72-0.85. The deep on-hue halo #2eac66 muddied the greeting's green pool to
  (21,42,29): lighten it (#36b872 to #3fc27c) at glow 0.9-1.0, or drop it.
- Diluted light, extended: rose fails like amber, in every role. Pine and Alpenglow's rose corner
  sampled wine ((47,34,39) to (55,36,45)) and its topGlow 2.4 haze a mauve smudge (30,24,27);
  Lantern Night's warm afterglow laid rust-brown (32,22,16) under the bar on every page. Rose and
  pink links beside the red "off" rings read as one alarm family, as amber did. Cobalt was the
  richest light (Blue Hour's corner (24,36,57)); violet glows only at full chroma (Evening Study's
  corner read lavender-grey (37,38,52) to product; fix: wash #7a62f6 aiming at (34,34,62)).
  Green-family companions (jade, sea-glass) count as more green, however calm.
- Borrowed and repeated looks, measured: Evening Study's #d797f0 is 6.4 dE from Dracula's #bd93f9,
  and no orchid that clears the Wishes floor gets past about 6.6, so only the warm room keeps it
  apart (skeptic's nudge: h322, #dc95e6). Blue Hour's #84a8fd is nearly Tokyo Night's #7aa2f7 (move
  to #93a3ff-#95a3fb, h272-278); Late Set's steel ink leans Nord (warm it to about #c8d2dd). The
  field formed three near-duplicate clusters (blue corner and sky pill; violet corner and orchid
  link; ivory on moss): keep at most one of each. Moving learned section colours costs points too
  (Evening Study's Ideas blue #5593e6, the dimmest in the bar; Pine's kids' pink turned orchid).
- Still open: Ideas, Sign in and 404 are about 95% green in all twelve; the only visible exception
  was Late Set's navy filter fields and tab on Ideas. Round 1's "visible afterglow" needs topGlow
  about 1.8-2.2 in a clean cool hue (1.4 sampled an invisible (17,20,24)): judges ask Late Set for
  #4a60e6 at 1.5-1.6 in place of the brand at 1.0, and Evening Study to move #8a86f0 (an indigo-grey
  haze at 1.8) toward #8c7bff at 2.0-2.2. The people-orange "Send where I am" icon is still unfixed
  in every palette; product asks for it on the accent or dim across the board.

## Round 3

Top four, carried on: Plum Ink r3-idea-2 (6.74), Navy Room r3-idea-1 (6.46), Desert Night r3-rand-4 (6.4), Reading Room r3-rand-1 (6.04). All four of round 2's winners fell to the bottom: Late Set 4.92, Evening Study 3.92, Blue Hour 3.7, Lamplit Room 3.4.

- Why the order: the companion has to live in solids on every page. The winners put it in cards, card-edge, bubbles, tiles, the bar, fields, headings and bezels. Round 2's corner, links and pill now measure as today (0.8-1.0% of Home below the fold over 10 dE; Late Set 2.9%). Plum Ink won on coherence: each role has one job, and its section ticks at the headings were the round's best variation device. Navy Room made the largest calm change (Status mean dE 6.19). This settles round 2's "tint surface-3 only": tint the cards too, but at C about 0.015-0.02. Plum's C 0.010 cards (#181418) read grey-mauve and barely register.
- The coloured monitor bezel is the round's discovery. It is the first thing in three rounds to change Ideas, Sign in and 404, which partly answers the problem left open since round 1. Putty (Desert Night #a49681) reads as a real IBM 5151 or Apple Monitor II, but the soul lens was the only one that liked it at that lightness. Everyone else asked for a deeper putty, #8a7d6a to #7d7263, so the case is not the brightest non-green area on the page. Dark cases (walnut, plum, navy) stay calm. Navy plastic reads modern rather than 1980s.
- New harness-wide check: a card-edge role must not override the "needs a look" panels. Plum Ink, Reading Room and Desert Night lost the amber edge on "Finish setting up" (sampled (48,41,50), (94,72,53) and (111,99,75), against today's (100,78,41)). Over tinted cards, keep `.setup, .restaurants-link, .trouble { background-color: #131612 }` and an amber border (#644e29), as Navy Room does.
- The rule that the accent must be a clear non-green now also covers sage and mint (it was only the brand before). Russet Orchard, Claret Boathouse and Rose Embers left their links and phone pill on sage, which reads as today, less like a link, and gives a mushy pill. Stock blues fail as well: Listening Booth's #4b8efe is about 7 dE from GitHub's; soften it to about #6a8fee-#7a9cf6. Turquoise (#62bcb8) counts as green-family too; the asks were #6aaed8-#6fb2d8 (h230-235).
- Green share has a floor. Blue titles, blue lit and blue ambient (Listening Booth: 25.8% green, 12.7% on Status) and Navy Room's drained Status (17.8%) make the green read as a button on someone else's theme. Keep lit and the Status panel/tile icons on sage #86d9a6 or the brand. Keep h1 in cream (#e6dcc6-#e8dfcc) when titles would otherwise take the companion. Home's box has lost its resting green border in every entrant (today it samples (97,149,115)); restore it with `.ask { border-color: color-mix(in srgb, var(--brand) 38%, var(--line-2)); }`.
- Chat: put Vera's bubble on the screen's green-black (#111712-#121714) and the family's in the companion. Two bubbles in one hue (Navy Room) separate the speakers too little. Three temperatures in one thread (Listening Booth's kraft beside navy) is too many.
- Rooms, refined: brown in solids reads as coffee (walnut #191511 to #171411; Reading Room's smallest text was also 4.66:1, so lift faint to #90887f). Rose and wine fail again: a firelight inset under each card reads as an effect, the claret starters read as tags, and red beside green is seasonal. Orange, green and black flirts with Halloween. The cobalt corner (25,37,60) is now a three-way duplicate (Navy Room, Reading Room, Blue Hour). Desert Night still has today's corner; a night-sky wash (#3a5fd0-#3f64d6 at about 2.0-2.2) was the common ask. Navy #12151e sits 1.8-2.9 dE from Tokyo Night and GitHub Dark; warm it half a step (#13161d-#14161f).
- Refinements worth breeding everywhere: Plum Ink's gap between the gift icon and "The kids' wishes", Listening Booth's larger chat text, and tabular numbers with `text-wrap: pretty`. Keep the section ticks to Coming up and Lately added, possibly as 3px rounded bars, so they do not read as confetti. The Dracula nudge (#d797f0 to #dc95e6) is still asked for. Rose Embers' phone tab bar grew about 10px and clipped the Next up title; check the tab bar's height.

## Round 4

Top four, carried on: Slate Console r4-idea-1 (6.96), Composing Room r4-idea-2 (6.83), Cloth and Glass r4-rand-6 (6.47), Indigo Noren r4-rand-1 (6.43). The carried four fell: Navy Room 6.2, Desert Night 5.73, Plum Ink 5.1, Reading Room 3.94.

- Why the order: the winners stopped changing only colour and gave each material one job. Green-black glass (#111712) is for what the machine shows (the greeting, Vera's bubble, date leaves, tubes). One cool, low-chroma solid (slate at C about 0.014, pewter rules, or indigo cloth) is for what the family owns. This refines round 3's rule that the companion must live in solids: it does, but at lower chroma than Navy Room, and never on Vera's bubble. Slate Console is Navy Room with the blue measured down (green share 70% against Navy's 35%). Composing Room lets the black ground carry the page between rules. Losers either added more green (Zinc Garden's leaf links, Sonar Watch, Harbour Celadon, Kitchen Clock's moss: 71-90% green, which reads as monochrome) or added a strong second hue (Cloth and Glass's indigo bar #161935 and top glow at 2.0 put back more blue than Navy Room).
- "Support the green" means cool neutrals: slate, pewter, iron, glass. It does not mean more green-family colour (moss, lichen, lime, leaf), and it does not mean warm or complementary companions (sand, turquoise, putty, plum, bronze). Olive or lichen card edges read close to the rejected brown borders. Warm edges also blur the amber "needs a look" panels, so they are a system fault as well as a matter of taste.
- TRAITS that spread (in the winners): cases in grey pewter or iron, not navy or putty. Indigo Noren's chin, with vent or grille slots and a power light, was the most convincing CRT in four rounds. Other winning traits: thick-and-thin head rules with a double rule under the bar (Composing Room); a sage cursor or tick at section heads; mono for the machine's small things (said-by, times, dates) with tabular figures; a 58ch lede and a 62ch chat measure; Plex Sans with Plex Mono; one 2px offset :focus-visible outline everywhere (Cloth and Glass); and the gift-icon gap. TRAITS that fade (in the losers): synthetic small caps (none of the served faces has smcp); a global `"opsz" 40` on every h1, which crowds the greeting and sign-in title ("What'son your mind?"); scope it to `.page-head h1`. Also fading: mono h1 page titles ("Sign in / to FamilyDB" wraps); four typefaces; a lifted green-grey ground (Sonar Watch; "do not grey the black" holds again); and window title bars (they read as Bootstrap headers).
- Cursors are the new confetti risk. Four entrants put one at headings. Use one device, in lit sage #86d9a6 at about 0.7-0.8 opacity with little or no glow, on a few section heads (Coming up, Lately added, To do, the Plans month). A full-brand block after every h1 reads as an editable text caret and as one more neon spot beside Send.
- Mono caps heads carry the terminal but need limits. At 1rem/600 they outweigh the card titles, and "FINISH SETTING UP" shouts in amber. Set them at about 0.9-0.95rem, weight 500-600, 0.06-0.1em tracking. Exempt `.setup > h2, .trouble > h2` (sentence-case sans). Apply one heading style on both ground and panels.
- Cases, refined: the bezel now changes Ideas, Sign in and 404, but every light case (pewter #5d6165, platinum #54585e, iron #52595e, putty) is still the brightest non-green thing there. Keep it at about #44494f-#4b5055. A power light must be brand green #6dff9c or amber, never madder #d8577a, which reads as a recording or error dot beside Status's red rings.
- Bugs to check in every entrant. Slate Console's `var(--brand)` does not resolve (the stylesheet names it `--green`), so Home's box edge sampled cream (214,208,196). Every r4 entrant kept the amber setup edge (about (113,87,42)); round 3's fix holds. Washes at 1.4-1.6 sampled invisible ((21,28,35)): use about 2.0 or set 0. Composing Room's box-versus-set split hangs on a `:not()` list; it needs a `.set` class, and forms should stay boxed. Keep Ideas at its learned violet (#ae9bff-#b58cec); #a878db is dim at 4.79:1.
- Open problem: the cool-slate cluster (Slate Console, Indigo Noren, Harbour Celadon, Navy Room) is near-duplicate (2.2-3.1 dE), and slate sits on GitHub Dark (surface-2 0.7 dE from #161b22). Nudge it toward the green-black family (surface #13171b, card-edge #2e343b). Every lens proposed the same breed: Slate Console's colour jobs, Indigo Noren's monitor chin with a green LED, and Composing Room's rules, measure and restrained cursor. Touch targets are still unenlarged everywhere (45 of 57 Home targets are under 44px).

Candidate principles for the Phosphor Interface standard:
1. Glass for the machine, one grounded cool neutral for the family. Green-black is kept for what the machine shows and says. The companion is low-chroma (C 0.014 or less) and never green-family, warm or saturated.
2. The CRT is carried by hardware and type, not by more green. That means dark grey cases with a chin (L below about 0.40), mono for the machine's metadata, and one restrained cursor device.
3. The black ground is never greyed or tinted. Structure (rules, glass wells) may replace boxes, but the gaps must read as a switched-off screen.

## Round 5

Top four carried on: r5-idea-1 Slate Galley 7.67; r5-idea-2 Front Panel 7.31; r4-idea-1 Slate Console 6.5; r4-idea-2 Composing Room 6.3.

- Why the order: structure beat colour. The only two entrants that defined components and used them on every page won, and their colour change was modest (10-16% of pixels over 5 dE). Those components were a masthead, set versus boxed, legends in the frame lines, and a new layout. The warm rolls (Lacquer oxblood, Night Sleeper madder, Almond linen, Heather plum) all scored at or below today, which confirms round 4's cool-neutral rule for a fifth time. Red companions read as Christmas and blur Status's red "off" rings. A red pill for the current tab or Home reads as an alert. Teal and petrol rolls (Smoke and Lichen at h213, Kettle and Glaze) failed as one blue-green family near Oceanic Next and Solarized. This refines "support the green": a cool companion must also sit away from teal, at about h235-260.
- Refines round 4: structure alone drains colour. Both winners left Status and Home below the fold as mostly bare black (12-16% changed), which reads monochrome again, and every lens asked for grounded colour back. Pair a set page with a slate well or slate column fills (`.in-status .panel{background:#12171b}`), a slate bar (--bar #10151a), and slate date leaves. The target is that the companion shows on Status and on Home below the fold, and not only in the rules.
- Layout finally answers the Ideas problem. Front Panel's tube beside the filters (`@media(min-width:64rem){.scope.has-screen{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr)}}`) was the first entrant in five rounds to get idea cards above the fold. Keep the radar at 8rem or less and use `.crt a{white-space:nowrap}` so "#7 Pumpkin patch at Bi-Mart farm" does not wrap. On Home, three columns need a reading floor, `minmax(34ch,1.25fr) minmax(24ch,.85fr) minmax(30ch,1fr)` and `.agenda .rel{white-space:nowrap}`; otherwise the "in N days" pills drop to their own line. Slate Galley put To do under Coming up and left the right column empty (Home 2300px tall): fill it.
- Selected state: only the selected item is raised. Front Panel raised every key and made the current one darker, so selection read backwards; nine keycaps on Settings read as costume. Keep keys flat with a transparent background, and give `[aria-current]` the latched key (#2a3240 to #232a35, 1px skirt) or a surface-3 lift. A 4px dot is too small for "you are here" in the bar. A family bubble with a key gradient looks pressable, so bubbles stay flat.
- TRAITS that spread (in the winners): the masthead (title, deck and one action on one baseline over an Oxford rule led in the page's colour); a `.set` class; rule-weight tokens (--rule, --hair); `appearance: base-select` slate pickers; lamp checkboxes; 2.75rem touch targets (Slate Galley: 3 of 57 under 44px, against 45); condensed tracked caps legends set into the frame line (Front Panel); a 5px lamp dot for "you are here"; the dark case #474c52 / #3f4449 with chin, vents and a green power light, which all lenses kept. The seed refinement "tabular figures" (Smoke and Lichen) and its dotted leaders from each section head to its link also spread; hide the leaders below about 40rem. TRAITS that fade (in the losers): "a thin coloured rule along the top edge of each panel" (Heather's selvedge threads made eight-colour confetti, and a yellow thread on To do hinted "due"); "section headings with a short underline or overline" in red (Night Sleeper's livery); dashed topstitching, which collides with the dashed "pending" bubble; Recursive or other code-like body faces; a global `font-variation-settings !important`; square lattice panes beside rounded panels. Round 4's full-brand block after every h1 fades again (Composing Room was marked down by every lens). Serif titles (Newsreader, Fraunces) were handsome but pulled off the CRT, which leaves them an open question for the owner.
- Refines round 4's "cursors are the confetti risk": coloured rule leads are too. Four leads on Home (cyan, violet, lemon, pink) edged toward confetti. Keep coloured leads on Coming up and Lately added only, and give the others pewter #47535b.
- Bugs to check in every entrant. The cascade: a later `.panel{border-color}` erased Front Panel's amber setup edge (sampled (43,48,53) against about (100,78,41)); use `.setup.setup` or order the rules, and add this as a harness check. Checkbox focus: base `input:focus{outline:none}` (0,1,1) beats `:focus-visible` (0,1,0), and a palette border overrides the green focus border, so add `input[type=checkbox]:focus-visible,input[type=radio]:focus-visible{outline:2px solid var(--brand);outline-offset:2px}`. Lamp checkboxes also need a tick. Legend patches painted in var(--bg) break on a panel, so use a `--legend-bg` token. The 44px hit areas inflate the head rows: take them out of the line box with a negative block margin. Masthead decks run to three lines on Wishes, Memory and Personality: cap them at about 40-52ch with `text-wrap:balance` and stack them under the title below about 900-1100px. Front Panel's CSS hit its budget (14,889 of 15,000), so factor repeated shadows into tokens.
- Open problems: Chat's green share on Front Panel is 24.8%; lift Vera's glass edge to about a 30% brand mix. Slate still sits near GitHub Dark; the nudge to surface #13171b / card-edge #2e343b has still not been bred in. Sign in and 404 are still dominated by the monitor. The breed every lens asked for: Slate Galley's system, targets and mastheads; Front Panel's Home and Ideas layouts, legends and lamps; flat keys; slate fills on Status.

Candidate principles for the Phosphor Interface standard:
4. Every element has one drawing that holds on every page. Read is set under a rule, act is a slate box, the machine is glass, the machine's body is a dark case, and "you are here" is a lamp or a latched key. A palette that only recolours today's components does not meet the standard.
5. Structure never replaces grounded colour. Each page, Status and Home below the fold included, shows the cool companion in a fill, not only in rules on black.
6. Red and teal are never companions, and selection is never red. Red beside the phosphor reads as seasonal or an alert and blurs the one colour that means off. Teal makes one blue-green family with the green.

## Round 6

Top four by score: r6-idea-1 Slate Proof 7.84; r6-idea-2 Radar Room 7.59; r5-idea-2 Front Panel 6.67; r5-idea-1 Slate Galley 6.46. Carried into round 7 (for score and variety): r6-idea-1 Slate Proof; r6-idea-2 Radar Room; r5-idea-2 Front Panel; r4-idea-1 Slate Console (Slate Galley passed over as Slate Proof's same-family sibling).

- Round 5's "structure drains colour" is now answered, which confirms it. Slate Proof is Slate Galley plus slate trays (#12181e) under the Oxford rules on Home below the fold, Status, Plans and the kids' wishes. That one change took the family from 6.46 to 7.84 and put it first with four of seven lenses. Front Panel and Slate Galley, with outlines on bare black, both fell back. Refinement: a tray and a raised box must differ by more than their edge. Tray #12181e against box #13171b is only 1.7 dE. Try tray #11161b with box #161b21, edge #2e343b and `box-shadow:0 1px 0 #0008`.
- A new component idea can beat typesetting. Radar Room's flight strip (designator block, body, right-aligned tabular mono facts column, racked on a pewter rail) grows out of the page's own "on the radar". It is one drawing used on Coming up, To do, Status, the Settings nav, the Plans month and the Ideas list. It won soul and style (8.2 each). Its risk is density: grey mass (#1b2126/#242c35 strips, a fully filled month grid, nine raised keys in the Settings nav) reads as an admin table or spreadsheet. Give it a gap of at least 8px, a 1px rail, fill #182024-#191f24 (toward green-black), transparent month cells, and a latched item for the current nav entry only.
- The Ideas page, refined again: list first with a compact portrait scope beside it (Radar Room: six strips above the fold) beats round 5's tube beside the filters. The breed every lens named is Slate Proof's page frame (masthead, rules, trays, type steps, focus) with Radar Room's strip as the list component inside trays, above all on To do and Status, and its Ideas layout.
- The chinned pewter case is load-bearing. Radar Room dropped the chin, vents and power light for a flush ring, and soul, feedback and system all marked it down. Keep a chinned case at least on Home's Next up, the 404 and Sign in. Flush scopes are fine on Status and Ideas.
- TRAITS that spread (in the winners): slate trays under rules; the strip with a facts column; IBM Plex Sans plus Plex Mono as one superfamily (it reads period-IBM, not code-editor); a stepped scale written into the CSS (3rem / 1.3 / 1.1 / 1 / .78 caps); both focus fixes (checkbox ring and `select:open` ring); hit areas that bring Home to 1 of 57 targets under 44px. TRAITS that fade (in the losers): the Tea House seed's two refinements, "Recursive for the whole page" (code-editor, for the second time) and "kind labels as small filled chips" (candy stickers that outrank the titles; tint them instead, `color-mix(in srgb,var(--kind) 14%,<surface>)`). Also fading: "headings a heavier weight with tighter letter-spacing" and "body text a touch larger" (Night Herbarium and Lantern Garden, both in the bottom half); brass bezels, holders and tags (steampunk, trophy-like on low-value data); bead or lantern strings under heads (they read as perforated rules); condensed "trail-sign" heads (sporty, and a fourth face). Seeds worth one more try, recoloured: Orchard Brass's bezel ring in pewter, Tea House's leaf corner on date leaves only, and Recursive Casual for mastheads alone.
- Colour, confirmed again. Every warm roll (cork, brass, kraft straw #383424, olive leather) read khaki. Samples: Tea House bubble (56,54,41), Orchard Status panels (23,23,17). Brass and cork also collide with the amber "needs a look" and people-orange. Violet at h302-311 (Night Herbarium, Lantern Garden) is Dracula, and the two were near-duplicates at 3-4 dE. The lifted frost at h205 sampled (26,34,35) and read grey-teal. New in this round: a glow halo on the phone pill is light, not a grounded solid.
- Bugs to check in every entrant. A global `.crt a{white-space:nowrap}` (round 5's advice) pushed Next up's link below its orphaned "›". Scope the nowrap to the link text (`.next-up .next-more{display:flex;gap:.5ch;white-space:nowrap}`) and check "[18 MIN NW]" on the Ideas radar. The open select loses its ring (Radar Room and four others): `select:open,select:focus-visible{outline:2px solid var(--brand);outline-offset:2px}`. Subgrid facts columns jump on long rows, so fix the width (`3.5rem minmax(0,1fr) var(--facts,11.5rem)`). Black checkbox wells (#0d1116) read as holes; use #1b2126 with a 1.5px #5b6570 edge. Moving sections visually (order, `display:contents`) breaks Tab order, so check the whole Tab sequence. Home's three columns also need `text-wrap:pretty` on titles, and the setup list should stay one column below about 80rem. Radar Room lost the round people-orange avatars and the phone pill; keep both.
- Open problems: Chat changes least in every entrant, so put the thread on a tray (`.in-chat .thread{background:#12181e;border-radius:12px;padding:1rem}`) and lift Vera's glass edge to a 30% brand mix. The greeting lost its second light; a periwinkle wash #5b6fd8-#6a7fd8 at about 2.0 aims near (26,32,54). Home's columns end about 130px apart, so move the kids' wishes line under To do. Sign in and 404 are still dominated by the monitor. Slate Proof's CSS is at 14,392 of 15,000, so factor the Oxford gradients into `--ox`. Smallest-text contrast was under 5:1 in Radar Room (4.72), Slate Console and Tea House (4.79).

Candidate principles for the Phosphor Interface standard:
7. Each list is one component with fixed slots (what it is, what it says, its facts), and the facts sit in an aligned tabular column the eye can read straight down.
8. Read content sits in a slate tray and act content in a raised box, and the two are told apart by fill and elevation, not only by an edge.
9. Every focusable control, open pickers and checkboxes included, shows the green ring, and the visual order of sections matches the Tab order.

## Round 7

Top four by score: r7-idea-1 Galley Rack 8.23; r6-idea-1 Slate Proof 7.46; r6-idea-2 Radar Room 7.01; r7-idea-2 Signal Box 6.99.

- The breed round 6 named worked, and by a clear margin: Galley Rack (Slate Proof's masthead, Oxford rails, trays and targets, with Radar Room's strip as the one list drawing inside the trays) was top four with all seven lenses and first with six. It is the first entrant whose change shows on Home below the fold, Chat, Ideas, Status, To do and Sign in alike, which is the owner's heaviest test. Its parents each scored about 0.4-0.6 lower than last round only because the child now does what they do and more. Its remaining faults are finish, not direction. Chat stutters with two rules about 36px apart (keep one: `.in-chat .masthead{background:none;padding-bottom:.5rem}`). Ideas Search is clipped at about 156px (`minmax(12rem,1.6fr)` floor, or For and Filter on a second row below 80rem). Trays stretch into empty slack (about 85px under To do, about 100px under Who answers and Keys on Status). A 3.5rem designator holding only a Status lamp is dead space (`2.25rem minmax(0,1fr)`). A '#N'-only facts cell wastes width (`--facts:3.25rem`).
- Refines round 6: level column feet are not worth empty tray. Let a tray end with its rows (`align-self:start`) and fill the gap by moving content. The kids' wishes go under To do (`'coming todo' 'coming wishes' 'lately eat'`), which also shortens Home by about 80px.
- Kind-tinted designators are the round's best answer to "not completely monochromatic" without neon, but 10% (`color-mix(in srgb,var(--kind) 10%,#1e2530)`) is too faint. Cyan and violet barely read, and restaurant amber and activity tint to warm grey-brown. Lift the cool kinds to 14-16%. Hold the warm kinds (people, todo, seasons, restaurants) to about 6%, or leave their block plain slate with only the icon in the kind colour.
- Signal Box's mimic-panel track is the round's most original component. Keep three parts of it: the lamp legend (#6dff9c lights only "now" and live, the clearest statement yet of scarce, meaningful glow); the horizontal fortnight line for Home's Coming up; and due times hung in a margin on To do. Drop the rest. Tracks on every page read as a git graph or subway map. Chat as a one-sided log loses "mine versus hers". Stamps wrap in a margin narrower than about 7.5rem. 'Add an idea' sat on the track's elbow. Rails ran 15-20px past their last lamp. A thin slate plate on bare black repeats round 5's "structure drains colour".
- TRAITS. In the winners: one strip with designator, body and facts inside slate trays; kind tints in the designator; DM Sans or Plex heads with a Plex Mono facts column; a thread tray on Chat with a 3px #a3aef5 edge on the family bubble; the cobalt greeting wash #4f60e6 at about 2.5 (the right amount of blue; add no more); a tray with the chinned tube beside the words on Sign in, and a portrait tube on 404; and dotted leaders to each head's link. In the losers, each seed's refinements faded. "Tighter, denser spacing" (Orchard) gave narrow columns and more small targets (16/57). "An airier page overall" (Pewter Dome) made Home 2206px long, more scrolling for no gain in finding. "A comfortable 60-70ch reading measure" (Headland Light) passed unnoticed under the mulberry. Also fading: a serif for titles (Fraunces or Newsreader in all four serif rolls, which each pulled the page off the CRT and made a fourth face; Fraunces reads chunky or toy-like); italic decks (they slow reading at small size); a graduated tick scale under every head (it reads as a perforated edge); a debossed inner rule (double borders on every board); wood grain (kitsch); and a portrait tube with spare glass on Ideas. Worth one more try, recoloured into the cool system: Lantern Clay's strung date tiles in slate (clay only on the day number, if at all); Headland Light's shaded weekend columns on the Plans month (`.month :is(td,th):nth-child(n+6)` at a 60% slate mix), a cheap comprehension win; its 0/97 To do targets; and green-bar banding on slate trays, not sage.
- Colour, confirmed again, with new samples. Terracotta date tiles read as rust bricks, and a clay phone pill reads as an alert beside the amber "needs a look". Bark reads olive-khaki. Mulberry reads aubergine or wine, and its heather-pink links sit beside the red off rings. Indigo cloth (#171523) with orchid links reads as Dracula and as pink. A warm-grey pewter with a serif reads as Claude.ai's own home screen. New this round: a green-family companion (sage-leaf trays) reads as more monochrome, not less. The companion must be off the green family altogether, not only off the brand (this extends round 3's sage and mint rule from the accent to the surfaces).
- Open problems. Slate with periwinkle is now the predictable identity, and Galley Rack's tray and strip still sit on GitHub Dark. Style, system and skeptic all asked for the nudge toward green-black (tray #0f1517-#11161a, strip #161c1f-#161c20, surface #151b1e, edge #2e343b), which has been asked for since round 4 and never bred in. Make it this time. The strip hover afterglow is barely visible, and Signal Box lost it. The '[18 MIN NW]' radar wrap is still in most entrants (scope nowrap to `.crt .dist`). The Next up '›' orphan is still in Slate Proof, Headland Light and Signal Box. The glow halo on Galley Rack's phone pill should be a tinted solid with a 2px cap. Its CSS is at 14,486 of 15,000, so fold `--ox` and `--lift` into shared tokens. Whether to offer a serif is the owner's open question; if asked, try Newsreader 400 on h1 and h2 only, never the greeting.

Candidate principles for the Phosphor Interface standard:
10. Grounded colour carries content, not decoration: every page's lists, thread and status sit on a cool, non-green material, so the difference from today shows below the fold as well as in the greeting.
11. Light behaves as a tube's did: #6dff9c marks only what is live or acted on, and anything that lights on hover fades back over about 900 ms.
12. A container is as tall as its content. Balance columns by placing sections, never by stretching an empty tray.

Carried into round 8 (chosen by advance.py for score and variety): r7-idea-1 Galley Rack 8.23 (the best score of the round); r7-rand-5 Indigo Bindery 5.7 (the protected random slot); r6-idea-2 Radar Room 7.01 (new family, not a near-duplicate); r7-idea-2 Signal Box 6.99 (new family, not a near-duplicate). Slate Proof passed over as Galley Rack's same-family sibling; Front Panel stepped out for the protected slot.
