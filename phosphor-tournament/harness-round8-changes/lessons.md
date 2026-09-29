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

## Round 8

Top four by score: r8-idea-1 Signal Galley 7.87; r8-idea-2 Reverse Video 7.86; r7-idea-1 Galley Rack 7.16; r8-mut-3 Plotting Room 6.51.

- Signal Galley won by doing what round 7 asked: Galley Rack's strips and trays moved onto green-black slate (tray #0f1519, strip #161c20, surface #151b1e, edge #2e343b), plus Signal Box's three parts (fortnight line with one breathing #6dff9c now lamp, To do's timetable margin with amber 'was due' read first, trays ending with their rows). This closes the green-black open problem from rounds 4-7. Its loss is sameness: Status and Settings are near-copies of Galley Rack, Chat splits times into two gutters, and 15% cyan day tiles read teal (take 9-10% over #1c2328, cyan on the month label only). Galley Rack is now superseded by its child; keep only one of the two.
- Reverse Video is new and proves the period can be carried by grammar, not paint: square steel windows with legends set in the frame, reverse video for 'here' (bar, tabs, settings menu, phone cell), unboxed rows, IBM Plex Sans with Plex Mono (VT323 only on the tubes), rounded glass only for the machine. It had the best measures (green share 33%, hue entropy .64, 0/56 small targets) and fixed Ideas' clipped Search, Status past the fold and the month past the fold. Its faults are loudness: the pale #89a2b5 reverse block (take #6e8496-#7a93a6, and a tinted solid #26313a with a 2px #a7c2d5 cap on the phone), .88rem mono-caps legends that shout (500 .78rem, .08em), links set into frame lines that read as labels, a double frame on every window. Risk from the owner's lens: least green entrant (18.7% on Status).
- Refines round 7's slate identity: the judges now want one breed of the two leaders, Signal Galley's materials and Home line with Reverse Video's legends in the tray rails, its reverse video for 'this one', its Send on the From row on the phone, and a single frame (double only for a dialog), companion nudged from periwinkle toward steel-cyan.
- TRAITS. In the winners: green-black slate trays, one strip macro with a tabular mono facts column, timetable margins (due times hung, Chat times in a gutter), a lamp legend where #6dff9c means only now and live, Plex Sans with Plex Mono, square family surfaces against round machine glass, and the lit glass greeting pool. Fading: every random seed's layout roll that left empty margin or length (Magic Eye's and Side-Head Bindery's hanging heads leave switched-off black; Attract Mode's uniform tiles ran Home to 2345px); 'controls: terminal commands' and 'printed form' rolls (bracket buttons read as gimmick, underline-only fields and ruled ask boxes lose the field and the focus ring); soft pills and a left nav rail (generic SaaS, rail empty below Status, phone tab dots lose recognition); serif titles and italic decks, again; the Iris hue turn (+30 degrees toward Dracula); a board 5 dE above black (Plotting Room: invisible, reads as a halo). Worth grafting, recoloured cool: Magic Eye's one-line programme-guide rows with right-aligned tabular facts and its one-screen month; Iris's three-column desk with heads on one baseline (at 72rem or more); Attract Mode's large mono day numerals and VT323 for field and weekday labels.
- Random entrants (5.29-5.61) changed the whole page, which the owner's test rewards, and still lost on colour already rejected: wine and rose with green read Christmas and alert (Magic Eye; 3.3 from the owner, 8 from style, the widest split of the round), oat on #473e33 edges reads khaki, coral beside danger red reads pink with navy 'more blue than necessary'. All three also dropped or weakened the greeting's glass pool, which the soul lens calls load-bearing. Mutants fared worse than their informed rivals because each point change was too small to see (Iris) or moved the wrong way (Side-Head Bindery kept the indigo and added empty margin). The crossover (Plotting Room) did best of the bred entrants because Galley's colours on Radar Room's structure were safe, but it is about 80% Radar Room below the fold: a crossover of two same-family parents adds polish, not identity.
- Colour: amber must keep one job ('needs a look'); Reverse Video's amber 'today' on the month and today's orange '28' disc break it (use steel reverse video for today). Rose labels (~h341) beside red off-lamps read as alarm. Lifted #1a2025 panels grey the page rather than grounding it. Mono-caps tracking above about .05em looks over-spaced.
- Open problems: no entrant answered the owner's case critique; every slate entrant still ships the 30px-rounded, .8rem-thick pewter slab. Carry a thinner, squarer case with a fine groove, vents and a power LED (Radar Room's flush scope is the direction). Moved controls (frame-line tabs, bottom-frame links, margin tabs, rails) are unverified for Tab order, since health.json records only the first 18 stops. Reverse Video's CSS is at 24.5k of 25k (fold the frame into one `--frame` token).

Candidate principles for the Phosphor Interface standard:
13. Only the machine is rounded: family surfaces are square, glass and tubes carry the radius, so what speaks and what is kept read apart at a glance.
14. A field always looks like a field: a filled, bounded box with a visible #6dff9c focus ring, never an underline or a rule alone.
15. The lit glass greeting stays in every page's design; a variant may change everything below it, never remove it.

Carried into round 9 (chosen by advance.py for score and variety): r8-idea-1 Signal Galley 7.87 (the best score of the round); r8-rand-1 Magic Eye 5.61 (the protected random slot, the best of round 8's random entrants); r8-idea-2 Reverse Video 7.86 (new family, not a near-duplicate); r8-mut-3 Plotting Room 6.51 (new family, not a near-duplicate).

## Round 9

Top four by score: r9-idea-2 Programme Guide 8.11; r9-idea-1 Signal Legend 7.51; r9-idea-3 Flight Deck 7.44; r8-idea-1 Signal Galley 7.1.

- Programme Guide won (in 8 top fours, 8 promise votes) because its identity comes from typesetting rather than paint, which is what the owner's "reflect more of the page content" asked for: slate bands with a head column, one-line rows read along a dotted leader to a tabular facts column on Home, Ideas, To do, Status and Settings alike, condensed Instrument Sans heads, the kind named in its own colour at the row's end, and a tuning scale under the bar with a needle under the current page. It had 9 idea rows above the fold, Home in 1646px, a one-screen month and 0 small targets. It also gave the best answer yet to the case critique: a thin, grooved case with vents, an LED and scanlines. This refines round 8's graft of Magic Eye's rows: they win once they sit on slate and lose the wine. Its fixes: heads wrap in the 10rem head column ("Finish / setting up"), so widen it to 11.5-12rem or set heads at 1.3rem with text-wrap:balance, and stack them above the rows below about 72rem (40rem on the phone). Head links in spaced mono caps read as labels; set them in sentence case, underlined, in denim (#9db6d6). Draw a leader only where a facts cell follows, give the facts fixed sub-columns, and cap the row at about 60-62rem. Swap the VT323 field labels, which are fuzzy and a fourth voice, for Plex Mono 500 at .72rem with .04em tracking. A needle for "here" does not survive the squint, so use Signal Legend's reverse block. Nothing is live below the fold, so graft the breathing now lamp into Coming up's next date.
- Signal Legend (7.51) is the consensus breed done faithfully: rail legends, steel reverse video for "here" (bar, tabs, Settings, today on the month, so amber keeps one job), square ticks and underlined rail links. It was the clearest state system on the panel. It lost on being too close to its parent, and its steel is so low in chroma that the page reads greyer than Signal Galley. Plex Sans Bold at 3rem is clunky, and its Chat times sit far from the bubbles. Refines round 8: "quiet the steel" can go too far. Keep the reverse block but give the companion enough chroma to carry a mood.
- FAILED REACHES. (1) Flight Deck (7.44, 8 promise votes) has the best-argued colour code since round 1: a 1982 EFIS glass cockpit was a CRT, so cyan means entered or selected by the family, bone means data, amber means caution and green means on. It also answered the case critique with thin, square, screwed faceplates. It fell short because actions and disclosures were set as caps legends in the demarcation lines ("ADD SOMETHING TO DO", "SAVE A THOUGHT FOR LATER"), setup links were drawn as checkboxes, .76rem Martian Mono legends made heads smaller than their rows, seven full-brand bars on Status spread the glow, and its cyan sits about 5 dE from Tokyo Night. To try again, keep the code and the faceplates, keep every action a button, and calm the Status lamps. (2) Signal Lines (6.86, the feedback judge's 8.6, but 6.1-6.7 from the skeptic, system and type judges) carried Signal Box's rings and tracks onto every page. It confirms round 7: the lines earn their place where they carry order (Chat's track, To do's timetable, the setup track), and read as a git graph where they only decorate (a ring on every head). Round tick lamps look like timeline stops, the 5px dot for "here" is too weak, and a form inside the To do bracket costs about 500px on the phone. To try again, draw lines only where there is sequence, keep ticks square, and pair them with Flight Deck's faceplate and a cyan near #8fbfdc. (3) Attract Mode's power-on roll bar was the best tube behaviour of the round, and its keys and wells had the clearest affordance, so keep both. (4) Porcelain Atlas's section discs in the bar, words for Memory, Family and Status, and the airglow under the tube are worth keeping. (5) The departures-board Next up in Plotting Room, Rehung failed because a 5:1 tube is not a period screen (they were 4:3) and it enlarged the pewter slab.
- TRAITS. The informed entrants took the top three places. The random entrants (5.04, 5.00) again lost on usability rolls: 41-45 of 56 Home targets were under 44px. Attract Mode's "keycaps" controls rolled about 36px keys and a latched tab that reads backwards (the chosen one looks off). Porcelain Atlas's "single centred reading column" ran Home to 2942px and left half the desktop empty, its "no icons beside words" roll lost recognition on the phone tab bar, and serif body text at .8rem is thin on dark. Both rolled ground hue 169 "a step lighter", and the teal-graphite read as one blue-green family with the phosphor, as in rounds 4-6. The mutants were worst of all. Magic Eye, Retitled (4.48) added Fraunces, which wrapped in the margin and faded for the fifth time, while the softer text was invisible. Plotting Room, Rehung (6.06) got one step brighter ink, against the calm brief, and a rearranged Home that grew 170px. The crossover Bakelite Video (5.66) showed that structure transfers cleanly (it kept 0 small targets and Reverse Video's grammar) but that colour does not rescue or sink it evenly: the oxblood filled every window, and squinted it read as Christmas, with red off-rings on red Status and a greige "here" block that looks disabled. Its legends at .68rem were too small. There was no separate type or graphics mutant this round. The type traits the panel rewarded were condensed Instrument Sans heads over text-width body with Plex Mono facts (seven steps), label-over-data rows, and tabular numerals. It did not reward VT323 labels, Fraunces or Newsreader, Figtree (generic SaaS), all-caps nav and buttons, or mono caps under .72rem. On graphics, it rewarded the tuning scale, faceplate screws, scanlines, and lines that carry sequence. It did not reward a ring round every icon, dots for "here", or starfields.
- Colour roles: amber keeps one job, confirmed by every informed entrant fixing today's amber disc. Suggested companions were a lower-chroma cyan of about #8fbfdc (less blue than periwinkle) and a denim link colour of #9db6d6. Oxblood, wine and rose failed again wherever they filled a surface. Only a material used sparingly can work.
- Usability was raised by the owner. The panel found these recurring faults: links and disclosures re-set as caps legends, controls redrawn as diagram marks, "here" as a needle or dot, and a message's time far from its bubble. Send on the From row, the one-screen month and one green primary per page were rewarded everywhere. Four judges ask for a dedicated usability judge scoring tasks (find the next plan, tick a to-do, send as someone, see what's broken, filter Ideas) on desktop and phone.
- Open problems: no entrant yet combines Programme Guide's listing, Signal Legend's now lamp, rail legends and reverse video, and Flight Deck's colour code and faceplate. Below the fold is still dead on the leader. The pewter slab survives in every Signal child except Signal Legend's thinner one.

Candidate principles for the Phosphor Interface standard:
16. Every list is one row read to an aligned facts column: title, leader, then tabular facts in fixed sub-columns, the same on every page.
17. A control keeps the drawing people already know: a box to tick, an underline to follow, a raised key to press, and a filled cell for "here". The period grammar dresses it and never replaces it.
18. Each colour has one job across the whole page, stated as a code (for example cyan for what the family chose, amber for caution, #6dff9c for live), and no surface is filled with a hue that has a job.

Carried into round 10 (chosen by advance.py for score and variety): r9-idea-2 Programme Guide 8.11 (the best score of the round); r9-idea-1 Signal Legend 7.51 (new family, not a near-duplicate); r9-idea-3 Flight Deck 7.44 (new family, not a near-duplicate); r8-idea-2 Reverse Video 7.09 (new family, not a near-duplicate). Carried in the wild lane: r9-rand-1 Attract Mode 5.04; r9-rand-2 Porcelain Atlas 5.0.

## Round 10

Top four by score: r10-idea-1 Evening Listing 7.9; r10-idea-3 Track Diagram 7.57; r10-mut-5 Signal Legend Relit 7.48; r10-mut-4 Flight Deck, Lit 7.47.

- WHY WINNERS WON. Evening Listing is the first entrant whose single row drawing holds on every page: bands with a head column, a one-line row, a leader only where a fact follows, tabular sub-columns (date, time, relative day), steel reverse video for "here", denim underlined sentence-case links, and 0 small targets. The system, type, interaction, usability and skeptic judges would write it into the standard. Track Diagram won the owner's lens (9.1) because it is the first since round 7 to carry Signal Box's lines through every page with restraint. It uses lines only where there is order: the Coming up track with a lit now lamp, the setup track, amber margin lamps on To do, Chat hung from Vera's mark and ending in a green ring, a ring-and-bracket page head, and a dot under the current page in the bar. This refines the round 7 and 9 lesson: lines carrying order now win outright. What lost was glow. The leaders run at glow 0.9 and screen 0.81 on #74f0a3, and side by side at 1.6x their halos are thinner than today's. That is now the panel's largest soul deficit.
- THE LIGHT (the owner's latest word, "bring back some of the original phosphor effect"). The two relit mutants answered it, and both reached the top four on a parent that did not. They used exact #6dff9c tubes at screenGlow 1.0, E1's two-layer halo on "mind", E3's ring and pool on Send, the bloom and scanlines, and lamps as glowing dots (0 0 4px brand/.8, 0 0 12px brand/.35). This refines the round 9 "dim it for calm" direction. Scarcity comes from how few things are lit, not from dimming them. Flight Deck, Lit's rule "lit versus matte" is the cleanest statement of it. Signal Legend Relit's glowing bubble edges show how fast the light spreads to things that are not live. Keep the page glow near 0.9 and put 1.0 only on the phosphor list.
- FAILED REACHES. (1) Docked Terminal (6.85, 7 promise votes, the most of the round) docked the machine in one lit glass column with a green pool, and on the phone the composer is pinned above the tab bar. Usability scored it 8.1, and it was the only entrant whose composer Tab order matches the drawing. What failed was indigo raised keys everywhere, including five "ALL →" keys on Home, which read as Bootstrap navy. It also had dead black under a short column and a small tube at 0.8. To try again: indigo for actions only, the "see more" links as underlined sentence-case chalk links, a status summary in the column on every page, and the tube at 1.0. (2) Figure Ground (6.41, 5 promise) had the most rigorous new rule: numbered chapters, with each plate led by a figure drawn from its own data. It had the strongest "here" in the squint (paper reverse) and was the only entrant that marks LATE on the To do page. It failed on mono-caps buttons, text-only phone tabs, 14 small targets, a 2437px Home, an unlit greeting, and paper-grey cells that were the brightest thing that is not green. (3) Bench Scope (5.98, 5 promise) had the round's most meaningful phosphor: the scope draws the family's coming weeks as glowing pulses, with Ideas in XY mode. It failed on its one-type-size twist (the question fell to 15px, and the squint shows no hierarchy), extended caps tracked at .2em, and an instrument-grey ground with aluminium nameplates and oxblood knobs. (4) Night Timetable (6.55, 4 promise) made Vera's line the spine of a three-column Home and had dot-matrix boards. It failed on copper-brown family bubbles, a hazard stripe, filled yellow arrow tiles, number discs in place of tab icons, and 34 small targets. The skeptic's rule is to graft the graphics, not the grounds. Each wild graft must bring the 44px targets and the lit greeting with it.
- TRAITS. There were no random seeds this round. The informed entrants took 1st and 2nd, and the relighting mutants took 3rd and 4th above their carried parents: Relit 7.48 against Signal Legend 7.04, and Lit 7.47 against Flight Deck 6.76. Relighting was the one mutation that could be seen at page scale. The type mutant Reverse Video, Reset (6.58, parent 6.56) collapsed about forty sizes onto six major-third steps and added a slashed zero ("zero"). The system and type judges want that written scale. But the smallest step made 12.8px legends rank below 16px rows, and its ss01/ss02 schoolbook a and g softened Plex, so add a .9rem step. The graphics mutant Programme Guide, Drafted (6.75, below its parent's 7.25) got credit for numbered setup balloons. Its callouts, head leaders and "80 COL / 25 LN" dimensions were faint costume that tells the family nothing. The crossover Atlas After Hours (6.29) kept the glass greeting with an airglow and a single-job cyan. It lost on Newsreader titles (serif lost for the sixth time), teal-graphite plates (the rounds 4-6 blue-green trap) and dots replacing the nav icons. The wild mutant Figured Atlas (5.22) had a constellation mark for each kind; its kind filter with icons was a real aid. It lost on Fraunces, a centred column (Home 2831px), cobalt plates and 27 small targets. The wild carried entrants came last (5.03, 4.66). The type panel rewarded condensed Instrument Sans or Archivo heads, Plex Mono for figures only, a slashed zero, numbered steps and FIG captions. It did not reward Braun all-lowercase, tracked mono or extended caps on buttons, Newsreader or Fraunces, or one size for every word. The graphics panel rewarded data-drawn pictures (the scope trace, the Braun waveform and drive-time dial, Figure Ground's wiring and late-bars figures) and lines carrying order. It did not reward screws, hazard stripes, starfields, drafted dimensions, or dots for "here" (dots were last in the interaction squint ranking).
- COLOUR ROLES. The skeptic found five entrants (Signal Legend, Relit, Flight Deck, Lit and Track Diagram) filling the setup tray in olive-bronze. Amber must be an edge and a ring, never a surface. Warm kind tints on plates (Restaurant, Seasonal) read brown, so keep the kind colour in the ring lamp alone. Lifted grounds lost again: Braun at #161a17 with #252320 surfaces, the instrument grey, and the teal-graphite. Red for now, late and error at once made "today" an alarm. The steel could take a breath more chroma (about #9cc4dc to #9fb9cc), since Relit is 77% green-and-grey. The lemon and amber kind words make up 38% of the neon that is not green.
- OPEN PROBLEMS. Only Figure Ground marks late on the To do page. The views.task_row `late` change should ship with the winner, with "was due" in amber as on Home. Evening Listing's head column is empty (about 230px) on Ideas and To do: put the count, the Add action and the All/Restaurants switch there, or collapse it. The pewter L-bracket on every band should become one top rule. The row hover afterglow is invisible and needs a steel or sage wash fading over 0.9-1.2s. Date lines wrap ("Tuesday 29 / September" on Lit, and Vera's date on Evening Listing). Desktop Chat in Relit, Night Timetable and Figure Ground drops the family-on-the-right split. The breed every lens asks for is Evening Listing's listing with Track Diagram's tracks and timetable Chat (date once, each time at its bubble) and Relit's light on the phosphor list only.

Candidate principles for the Phosphor Interface standard:
19. Light is a list, not a level. The things that are live (the mark, "mind", Send, the now lamp, the status lamps and the monitors) glow at full strength (exact #6dff9c, screenGlow 1.0, layered halo), and everything else is matte. Calm comes from how short the list is, never from dimming the tube.
20. A line is drawn only where there is order (a sequence, a thread, a timetable), and ends in a lamp that says where you are.
21. Type is a written scale of a few steps, in which a legend or head never ranks below the rows it governs. Controls and "see more" links are sentence case, never tracked caps.

Carried into round 11 (chosen by advance.py for score and variety): r10-idea-1 Evening Listing 7.9 (the best score of the round); r10-idea-3 Track Diagram 7.57 (new family, not a near-duplicate); r10-mut-5 Signal Legend Relit 7.48 (new family, not a near-duplicate); r10-mut-4 Flight Deck, Lit 7.47 (new family, not a near-duplicate). Carried in the wild lane: r10-idea-2 Docked Terminal 6.85; r10-wild-4 Figure Ground 6.41.
