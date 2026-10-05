# Stage 12: Afterglow as a look, and the small things that move

## What I made

**Afterglow is a look.** It is one `[data-theme="afterglow"]` block in `themes.css`. It sits on the Look page as the third card, after Phosphor, with a day and a night sample. No page, layout, markup or wording changed for it.

- **Night:** charcoal glass with a breath of green.
- **Day:** pale green-grey paper with deep-green ink.
- **In both:** the band (sidebar, phone top bar) and Vera's Ask box are dark glass with faint scanlines, and Vera is the one thing that glows.
- **Type:**
  - Page titles and the wordmark are in VT323, the pixel face, at the same cap height as Fraunces.
  - Everything people read stays Atkinson Hyperlegible.
  - Card titles stay Fraunces, and money and dates keep Fraunces Figures.

**Every page in Afterglow**, by day and by night, on desktop and on phone, is in `shots/afterglow/day/` and `shots/afterglow/night/` (240 shots). I looked at them all.
- In the first pass the day link green sat too close to late red for protanopes (5.4 against a floor of 6). I moved the day green from `#0B6638` to `#0C6150`, which gives 14.1, and rendered again.
- The theme check passes Afterglow by day and by night, with its effects measured.
- Its palette sheet is `palette/afterglow.html` (shot: `shots/afterglow/palette-afterglow.png`).

**Motion, in Kitchen Table itself (every look):**
- **Vera's sign types itself in:**
  - once on Home as the page opens: about 1.5 s, then its cursor blinks three times and rests lit;
  - on a loop only while she is writing back: the chat's waiting line, and Home's Ask box while the pill says "writing back";
  - still everywhere else.
- **Afterglow:** the "what you just did" flash lights at once and fades over 1.2 s.
- **Landing:** the card, day or plan a link points at lights and fades over 1.8 s.
- **Cursors rest:** the wordmark's cursor blinks for about four seconds, then stays lit.

**`motion.html`** shows each motion in place, with a line on when it plays. It is the fourth states sheet. `shots/motion-frames.png` shows the sign typing frame by frame, in Kitchen Table and in Afterglow.

## How the effects work

Five effect tokens joined the look contract:

| Token | What it does | Every other look | Afterglow |
|---|---|---|---|
| `--fx-page` | a light on the page itself | `none` | a faint green glow at the top left |
| `--fx-scan` | the colour of the scanlines | `transparent` | a 3.5 % pale green line every third pixel |
| `--fx-glow` | how much Vera's things glow, 0–1, and how bright the motions are | `0` | `1` |
| `--fx-title` | the face for page titles and the wordmark | the heading face | VT323 |
| `--fx-title-adjust` | sizes that face to the heading's cap height | `none` | `cap-height .7` |

- **Every look defines them.** The plain values sit in the shared `[data-theme]` block and in Kitchen Table's own block, so a look that wants no effects writes nothing.
- **`style.css` reads them once**, in a new section 11. It is CSS only: no images and no scripts. VT323 is self-hosted (18 KB) and is only downloaded by a look that uses it.
- **Scanlines** are drawn as a background under the words, on the band, Vera's Ask box and the radar's glass. They are never on cards and never a film over text.
  - The old glass panes (sign-in, 404) drew theirs over the words. I moved those under the words too, in every look; they look the same.
- **Glow** is a shadow outside a thing's edge.
- **When they are off:** in forced colours and in print, all of them. Under reduced motion there is nothing to stop, because none of the effects move.
- **Checked with the effects on.** `_kit/looks-check.py` has a new check: it lays the scanline over the band and over Vera's box, and the page light over the paper, then measures the words on top. Afterglow's lowest is 4.70:1 (the floor is 4.5).
- **How Vera stays the one lit thing** when the whole page is glass: with `--fx-glow: 1`,
  - her sign gets a second, wider halo and a fully lit rim;
  - her Send button glows;
  - her chat lines get a soft lit edge.
  - Nothing of the family's glows: their links are a soft mint, their button a pale plate, today a flat chip.
- **The motions** are all CSS (`style.css` section 12).
  - Each new one exists only for people who haven't asked for less motion; the old ones stop under reduced motion.
  - Only the sign and the pill's dot loop, and only while she is working.
  - In Afterglow the lights are brighter (`--fx-glow` takes them from 45 % to 80 %), never longer.

## Decisions I made (and why)

- **Afterglow has a day.** The earlier round's own weakness was that dark is harder to read on a bright phone outdoors or with astigmatism. The look mechanism gives a day for free. The dark band and Ask box keep it reading as Afterglow by day.
- **Afterglow should become "Phosphor" once Kitchen Table ships**: one name, one look, keyed `phosphor`, so a browser that chose Phosphor keeps its green screen. The old Phosphor palette was made for the old layout and retires with it. Until then both stay on the Look page. Details in HANDOFF.md §8.8.
- **The pixel face is for titles only.** It earns its place on big titles. Money, dates and card titles stay in Kitchen Table's faces, so there is still one figure style and some warmth.

## For the family to decide (HANDOFF.md §9, questions 12–15)

1. **Afterglow and Phosphor:** make Afterglow the look called "Phosphor" when Kitchen Table ships (recommended), keep both for good, or give it another name?
2. **Afterglow by day:** keep the day, or make it night only like Phosphor?
3. **The pixel face:** titles and wordmark only (as now), more of it, or none?
4. **The motions:** drop any of these? Bring back any of the old ones I left out (glyphs falling on every busy screen, the 404 powering on, the radar sweep)?

## Also changed, and worth knowing

- **The render kit:** `_kit/render-all.js` now takes screenshots with motions settled at rest. Without that, shots caught the sign half-typed.
- **The theme check:** `_kit/looks-check.py` now checks Afterglow on Kitchen Table's people. Its known colour-blind notes are the same as Kitchen Table's.
- **Home Computer** still fails the check in one place: by night, for tritanopes, its late red is too close to its orange action colour. This is unchanged from stage 11 and is still a question for the family.
- **What the built app needs** is in HANDOFF.md §8.9: five lines per look in `themes.css`, about 50 lines of `style.css`, and new `test_look.py` checks. Afterglow should land with the new layout, because the old layout doesn't read the effects.
- **Kitchen Table's shots** were all re-rendered and compared pixel by pixel with stage 11's. The only changes are the intended ones:
  - the wordmark cursor is now shown at rest, lit;
  - the glass panes' scanlines sit under the words;
  - the Look pages gain the Afterglow card;
  - the states sheets gain a fourth button, and the motion page is new;
  - the radar pane's rounded corners differ slightly in anti-aliasing;
  - Home and Type differ by at most 1 colour level in a handful of pixels.
- **Two stray files are still outside this folder:** `/setup-dump.txt` and an empty `/s10_restructure.py`, left over from a mistake in an earlier stage. They need deleting at the root; I haven't touched them.
