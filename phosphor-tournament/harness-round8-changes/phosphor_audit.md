# Phosphor audit: what round 10's six carried designs kept of the original's light

Designs: r9-idea-2 Programme Guide (PG), r9-idea-1 Signal Legend (SL), r9-idea-3 Flight Deck (FD), r8-idea-2 Reverse Video (RV), r9-rand-1 Attract Mode (AM), r9-rand-2 Porcelain Atlas (PA). None has a clean sheet: all six render over the original stylesheet and override parts of it.

How this was judged: the same place in each design's shots and the original's (`rounds/r10/out/<id>/shots/`), cropped and enlarged 2-4x, plus pixel measures. "Gx" below is green over the ground, G - (R+B)/2, sampled in a band just outside the lit thing, so a halo shows as a number. The cause of each difference is named from the stylesheet each design was actually served (`out/<id>/style.css`) and its palette's `css`. Crops are in `tmp-phosphor/pa/`.

One caveat: the original was shot on 28 September and the designs on the 29th. So the brief thread under Home's box ("Continue with Vera", with her screen by her last line) is missing from all six Home shots because the demo's last line is by then two days old. Every variant still has that markup, so it is not counted as a loss.

## 1. The original's CRT effects

From docs/STYLE.md ("Why the green jumps", "Her screen", "Green screens", "Small things"), style.css and the 00-current shots:

1. **The key word's layered glow.** `.glow` puts two halos on "mind" in Home's question: 0.45em at 0.45, and 1.3em at 0.22.
2. **The mark and caret in the bar.** The tile has a 22px halo, the icon a 3px drop-shadow, and the block caret a 10px glow; the caret blinks eight times and then rests.
3. **The bar's lit current page.** The current page's icon glows in that page's colour (5px drop-shadow).
4. **The primary button.** A 1px ring at 0.35 and light pooled under it (`--glow`: 0 8px 28px -10px at 0.7).
5. **The field being typed in.** A green edge, a 3px ring at 0.16 and a 22px glow.
6. **Home's box at rest.** It keeps a faint phosphor even before you type (0 0 38px -20px at 0.6).
7. **The tube's bloom.** VT323 in three halos (1px/9px/24px at 80/45/20%).
8. **The rest of the tube.** VT323 in three strengths, a 0.35px blur, scanlines (1px in 3 at 0.4), light off the front of the glass, the dark curved edge (vignette to 0.6), inverse-video headings and the block cursor.
9. **The case's halo.** Green light spilling round the monitor's plastic (0 0 80px -36px at 45%).
10. **Power lights.** A glowing dot in each monitor's chin.
11. **The radar.** An 8s sweep with a conic afterglow and a bright edge; blips as a hot core in a halo that flare as the sweep passes; the next one pings; rings and ticks carry a drop-shadow; the 404 flickers.
12. **Live lamps.** Status dots with 8px and 18px halos that breathe over 3.2s.
13. **Highlights along top edges.** `--shadow` puts an inset 1px at 0.035 on every card; the case has one at 0.08.
14. **The page's afterglow at the top.** A radial green at 0.075.
15. **The greeting lit from below.** A green radial at 0.13 in its bottom left, with a cyan wash opposite.
16. **Scanlines in the greeting's glow.** 1px in 4, masked to the glow.
17. **Her screen.** Glyph columns with bright heads, a scanline mask, a 0.3px blur and an 18px halo.
18. **The lit title tile.** Its accent's tint, its own raster (1px in 3 at 0.22), a 26px glow and a glowing icon.
19. **The focus ring.** 2px green, offset 3px.
20. **Amber for today.** A glowing amber disc or chip (18-22px).
21. **The afterglow on hover.** A card lights with a 40px glow in its colour that fades over 1.2s, and a link's landing does the same.

**The glowing dots on black the owner remembers.** In the original these are items 10, 11 and 12 with the caret and the glyph heads: lamps, power lights, blips and the radar's hub, each a small hot core in a soft halo on near-black. The original has no dot field of its own.

## 2. The matrix

K kept, W weakened, L lost, R replaced by its own equivalent that still reads as light.

| # | Effect | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| 1 | Key word glow | K | K | K | K | W | W |
| 2 | Mark and caret | K | K | W | K | K | K |
| 3 | Lit current page in the bar | L | L | L | L | L | L |
| 4 | Button ring and pooled light | K | K | K | W | W | W |
| 5 | Field being typed in glows | L | K | L | W | W | W |
| 6 | Home box glowing at rest | L | K | L | L | L | L |
| 7 | Tube bloom | W | W | W | W | K | K |
| 8 | Tube: strengths, blur, scanlines, glass, edge, cursor | K | K | K | K | K | K |
| 9 | Case halo round the monitor | W | L | L | W | W | K |
| 10 | Power lights | K | K | K | K | K | K |
| 11 | Radar: sweep, afterglow, blips, ping, flicker | K | K | K | K | K | K |
| 12 | Live lamps, glow and breathing | W | K | L | W | W | W |
| 13 | Top-edge highlights | W | K | K | W | K | K |
| 14 | Afterglow at the top of the page | K | K | K | K | R | L |
| 15 | Greeting lit from below | K | K | K | K | L | R |
| 16 | Scanlines in the greeting | K | K | K | K | L | L |
| 17 | Her screen | W | W | W | W | W | K |
| 18 | Lit title tile, raster and glow | W | W | L | L | L | L |
| 19 | Focus ring | K | K | K | K | K | W |
| 20 | Amber today | L | L | L | W | K | W |
| 21 | Afterglow on hover | W | R | W | W | W | W |
| | **Kept or replaced** | **10** | **15** | **10** | **9** | **9** | **9** |

## 3. The evidence, effect by effect

**1. Key word.** Crops `c-mind.png` (home.png, around "mind", at 2x). Halo 3-12px above the ground, then the glow in the letters' counters:

| | Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| Halo | 4.4 | 5.4 | 5.2 | 4.0 | 3.2 | 2.6 | 3.0 |
| Counters | 24 | 24 | 25 | 22 | 22 | 17 | 12 |

- **AM**: `glow: 0.49` halves both halos, to 0.221 and 0.108 (its style.css line 209).
- **PA**: `halo: #72ce97` at 0.84 softens them, and Newsreader's thin strokes carry less light.

**2. Mark and caret.** Crop `c-brand.png` (the bar, 20-200 x 0-60, 3x). All six glow. FD cut the tile's halo to `0 0 16px -6px` at 0.5; measured round the tile, Gx is 2.9 against the original's 5.0. The caret's cursors blink and rest everywhere; nobody overrides them.

**3. Lit current page.** Crop `c-nav.png` (chat.png, the "Vera" item, 3x). The original's icon is green with a halo. Every design sets `filter: none` and marks the page with something unlit instead:
- PG: a denim needle.
- SL and RV: steel reverse video.
- FD: a cyan box.
- AM: a sunken well with a teal icon.
- PA: every line icon hidden (`.icon{position:absolute;width:1px}`), with an accent underline.

**4. Button.** Measured on lost.png, where the ground below "Back to the start" is empty. Gx 6, 10 and 16px below the button:

| | Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| +6px | 25.3 | 23.6 | 22.3 | 22.0 | 11.8 | 9.8 | 16.6 |
| +10px | 18.3 | 17.0 | 16.4 | 15.2 | 6.2 | 8.4 | 10.9 |
| +16px | 10.3 | 9.9 | 8.4 | 8.4 | 2.6 | 6.5 | 6.5 |

- **RV**: `button{box-shadow:0 0 0 1px .3, 0 6px 22px -12px .7}`.
- **AM**: a keycap, with a 3px green-black travel edge and `0 0 20px -8px`.
- **PA**: `--glow: ... 0 6px 22px -14px`.

**5. Field being typed in.** Profile across the sign-in field (login.png) and crop `c-field.png` (controls-field). The original has a ring at 33-36 and a tail from 15 down to 10 over 10px.
- **SL** keeps both in its calmer sage (`lit`): ring 31-34, tail from 13 down to 8.
- **PG and FD** set `input:focus{box-shadow:none}`, leaving an edge and a crisp outline with no halo.
- **RV**: ring 9 and no tail.
- **AM**: ring 17 and an unlit edge.
- **PA**: ring 7.

**6. Home box at rest.** Profile outward from the box's left edge (home.png). The original falls from 12 to 4 over 20px. SL runs from 14.6 down to 7.4. PG, FD and RV are flat at 4.5-7 right from the edge, though their edges are brighter (38% brand); AM and PA are flat.
- **FD**: `.welcome .ask{box-shadow:none}`.
- **RV**: replaced with a black drop shadow.
- **AM**: a sunk deck with an inset shadow.
- **PA**: took the frame away.
- **PG**: no rule touches this glow. It dies because PG sets `--shadow: none`, and the base declares `box-shadow: var(--shadow), 0 0 38px ...`. With `none` inside a list the whole declaration is invalid, so the glow is dropped. See section 5.

**7 and 8. The tube.** Crops `c-nextup.png` and `c-tube.png` ("NEXT UP / Pho Oregon", 3x). The picture is intact in all six: the inverse heading, the underlined link, the cursor, the scanlines, the glass sheen and the dark edge. Nobody overrides `.crt-tube::before/::after` or the blur. Scanline row-to-row difference is 3.6-4.9 against the original's 4.0.

Bloom 2-6px from the letters:

| Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|
| 17.0 | 12.2 | 12.7 | 12.6 | 12.6 | 15.1 | 15.0 |

The four related designs set `screen: #74f0a3` with `screenGlow: 0.8`. That cuts the three halos to 64/36/16% and gives letter cores of (193,248,214) against (190,255,210): a paler, quieter tube.

**9. Case halo.** Measured on lost.png, outward from the monitor's left edge, 2px against 45px: the original is 9.2 against 2.6.

| | Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| Halo above ground | 6.6 | 4.4 | none | none | 4.2 | 4.5 | 5.2 |

- **SL**: `.crt{box-shadow: inset 0 0 0 1px #59616a, inset 0 1px 0 ..., 0 1px 0 #0008}` has no phosphor term.
- **FD**: `.crt{box-shadow: ..., 0 16px 30px -20px #000}` has none either.
- **PG** keeps it narrower (`0 0 70px -40px`), and on Home it sits in the blue wash.

**10. Power lights.** In the chin of every monitor in every design, each with a 5-6px glow. FD adds a dark second switch beside it.

**11. Radar.** Crops `c-radar-next.png`, `c-radar404.png` and `c-motion-on.png`. The sweep turns, leaves its wedge, and the blips flare and ping in all six.
- The related four draw it at 0.8 strength.
- PG's Next up scope is 6.5rem against 9rem, so its blips read small.
- SL, FD and RV stack the 404 console upright with an 11rem scope.
- AM adds a line of light that runs down the glass as each monitor switches on (`.crt::before`, `@keyframes scan`), a real period touch.

**12. Live lamps.** Crop `c-dots.png` (status.png, first light, 4x). Halo 8px and 10px from the centre:

| | Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| 8px | 20.9 | 9.2 | 19.3 | rail | 21.3 | 12.2 | 9.5 |
| 10px | 11.4 | 4.0 | 11.8 | rail | 12.1 | 9.4 | 4.6 |

- **PG**: `.light.on{box-shadow:0 0 6px}`.
- **SL**: a 3px ring plus 9px.
- **FD**: a 4px rail with no halo and no breathing (`.lights .light{animation:none;box-shadow:none}`).
- **RV**: `.light.on{animation:none}`. The halo stays but the lamp no longer breathes; it reads brightest only because it is caught at full opacity.
- **AM**: 8px at 70%.
- **PA**: a 0.55rem dot.

SL also adds a new one: the NOW station at the head of Home's timeline, 12px with a 3px ring and a 12px glow, breathing (`.stations::before`; crop `c-new.png`). It is the one genuinely new glowing dot on black in the field.

**13. Top-edge highlights.** Cards keep the inset light in SL (`--lift` .045), FD (`--machined` .04), AM (.03, with keys at .07 and a .5 highlight on the button) and PA (panels .05 plus a top sheen). PG's `--lift` has no inset and it sets `--shadow:none`; RV sets `--shadow:none` and `.panel{box-shadow:none}`. Both keep the highlight only on the monitor's case.

**14. Afterglow at the top.** Sampled on lost.png at (640,75) against the ground: the original is (13,19,16) against (11,14,13). The related four are identical. AM's is teal, at (19,33,27) (`top-glow #77cfce`, `topGlow .7`, plus a teal ambient). PA's is a blue zenith (`rgb(70 104 180/.2)`), which reads as night sky rather than a tube.

**15 and 16. The greeting.** Crop `c-greetglow.png` (bottom left of the greeting, 2x). Green in the corner, then the scanlines, measured as the period-4 amplitude over the same 36 rows:

| | Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|---|
| Green | 15.2 | 12.5 | 14.4 | 14.0 | 15.5 | 5.6 | 11.2 |
| Scanlines | 2.10 | 2.18 | 2.03 | 1.99 | 2.03 | 0.06 | 0.09 |

- **AM** repaints `.welcome::before` as a full-width band, with only 0.06 green behind Next up.
- **PA** repaints it as a green airglow at the horizon (`c-rand2-horizon.png`), with a green hairline. That is a real equivalent of the light, but it has no scanlines.

**17. Her screen.** Crop `c-presence.png` (chat, her last line, 4x). The glyphs, bright heads and scanline mask are the same in all six. Halo 1-6px out, above the ground:

| Orig | PG | SL | FD | RV | AM | PA |
|---|---|---|---|---|---|---|
| 4.9 | 2.7 | 2.7 | 2.9 | 2.7 | 3.1 | 6.4 |

For the related four it is `screenGlow .8` again: `0 0 18px -6px rgb(116 240 163/.48)`. PG makes the one beside her name on Home larger (7.5px glyphs), a gain.

**18. Lit title tile.** Crop `c-tile.png` (Status title, 4x).
- **PG** keeps the raster and a faint glow, but in denim.
- **SL** keeps the raster and a green tint, but `box-shadow:none` and the icon's `filter:none` put out the glow.
- **FD**: `background: color-mix(...)`, which replaces the raster, and no glow.
- **RV**: `background: var(--win)`.
- **AM**: a teal keycap.
- **PA**: a star in the accent colour.

**19. Focus ring.** Crop `c-focus.png`. A 2px brand ring, squared, in five. PA's is 1px with a 4px halo at 14%.

**20. Amber today.** From the plans.png montage.
- **PG**: a denim outline.
- **SL**: steel reverse video.
- **FD**: a green NOW outline, with no glow.
- **RV**: an amber fill with no glow.
- **AM**: the amber disc with its glow; the base rule is untouched.
- **PA**: an amber square with `box-shadow:none`.

**21. Afterglow on hover.** Crop `c-motion-glow.png`. The timing survives everywhere (0.9-1s out), but the light mostly does not:
- **SL** lights a 1px ring plus a 14px glow in the kind's colour.
- **PG**: a denim needle.
- **FD**: a 2px bar.
- **RV**: a steel bar.
- **AM**: a 1px ring.
- **PA**: an underline.

`--shadow:none` also voids the card-hover glow, the chat box's focus glow and the landing glow in PG, RV and PA. Those are not in any shot, but they follow from the same invalid declarations.

## 4. Per design

**Programme Guide (PG).**
- Kept: the key word, the mark, the button's pool, the whole tube picture, power lights, radar, the greeting's light and scanlines, the top afterglow, the focus ring.
- Weakened: bloom and her screen's halo (`screenGlow .8`); the case halo (70px -40px); lamps (6px, one halo); the title tile (raster kept, but denim); card highlights and hover.
- Lost: the lit current page, the field's glow, Home's box at rest (by the `--shadow:none` bug, not by intent), amber today.
- Added: a glowing `>` prompt in the box, a faint phosphor halo on her bubbles, and a bigger screen of hers on Home.
- In one line: the light is mostly there at 80-90%. Two of its losses are accidents of one token.

**Signal Legend (SL).**
- Kept: the key word, the mark, the button's pool, the field glow and Home's box at rest (both in sage), lamps with halo and breathing, card highlights, the greeting's light and scanlines, the top afterglow, radar, the tube picture, focus.
- Weakened: bloom and her screen's halo (`.8`); the title tile (raster kept, glow off).
- Lost: the case halo, the lit current page, amber today.
- Replaced: the hover afterglow, with a ring and glow in the kind's colour.
- Added: the breathing NOW dot on the timeline.
- In one line: the most light kept of the six. What is missing is the monitor's spill, a bit of bloom, and the lit tile and page icon.

**Flight Deck (FD).**
- Kept: the key word, the button's pool, the greeting's light and scanlines, the top afterglow, machined highlights, radar, the tube picture, focus, power lights.
- Weakened: the mark's halo, bloom, her screen, hover.
- Lost: the case halo, the lit current page, the field glow, Home's box at rest, the lamps (now unlit rails), the lit tile, amber today (now a green outline).
- In one line: the cockpit discipline took out most of the small lights round the family's things. The tubes and the greeting still glow; the lamps, the box and the tile do not.

**Reverse Video (RV).**
- Kept: the key word, the mark, the greeting's light and scanlines, the top afterglow, radar, the tube picture, focus, power lights.
- Weakened: the button (half its pool), the field's ring, bloom, the case halo, lamps (their glow kept, their breathing stopped), card highlights (`--shadow:none`), amber (fill, no glow), hover, her screen.
- Lost: the lit current page, Home's box at rest, the lit tile.
- In one line: most of the light is there but dimmer. The biggest single cut is the button.

**Attract Mode (AM).**
- Kept: the mark, the tube's bloom at 0.89, the case, radar, amber today with its glow, focus, highlights, the lamps' breathing.
- Weakened: everything scaled by `glow .49`: the key word, the button (a keycap), the field ring, the lamps' halo, her screen, hover.
- Replaced: the top afterglow, now teal.
- Lost: the lit current page, Home's box at rest, the greeting's green and its scanlines, the lit tile.
- Added: a line of light sweeping down each monitor as it switches on.
- In one line: the monitors are the most alive of the six, but the page round them is lit teal, and green only where a screen runs.

**Porcelain Atlas (PA).**
- Kept: the mark, the tube's bloom at 0.88, the case halo, radar, her screen, panel highlights, power lights.
- Weakened: the key word, the button, the field, lamps, the focus ring (1px), amber, hover.
- Replaced: the greeting's light, now a horizon airglow.
- Lost: the green afterglow (now a blue sky), the greeting's scanlines, the lit tile (a star), the lit current page with all its icons, Home's box at rest.
- Added: a porcelain star field in the margins. These are dots on black, but not phosphor ones.
- In one line: the console is fully lit and the page round it is a night sky. The CRT survives as one object, not as the page's light.

## 5. Overall

**What the field lost most**, in order:
1. **The lit current page in the bar**: lost in all six. Every "you are here" became unlit (reverse video, a needle, a box, a well, an underline).
2. **Home's box glowing at rest**: lost in five; only Signal Legend keeps it. This was the page's first lit thing after the key word.
3. **The lit title tile**, a small screen with a raster and a glow: lost in four, weakened in two.
4. **The tube's halo**: weakened in the four related designs by `screen #74f0a3` with `screenGlow .8`. Bloom is down about a quarter and her screen's halo about 45%. The picture is intact; it just glows less.
5. **Amber today**: lost in three, weakened in two.
6. **The field's glow while typing**: lost in two, weakened in three.
7. **The case's green spill**: lost in the two designs the owner likes best.
8. **The lamps**: breathing and haloed in the original; now thinner, still, or rails in five.

The hover afterglow keeps its timing but has lost its light in five.

**What survived everywhere:** the monitors themselves (VT323 in its strengths, blur, scanlines, glass, dark edge, cursor, power light), the radar with its sweep, afterglow and blips, the mark and caret, the focus ring, and in four designs the greeting's green light with its scanlines. The motif's core is intact. What went is the scatter of small lights round it, which the original used to make the page feel switched on.

**Which design kept the most:** Signal Legend. It has 15 of 21 kept or replaced, and it is the only one to keep the box glowing at rest, the field's glow and full-strength lamps. It even adds a glowing, breathing dot. Programme Guide and Flight Deck follow with 10.

**Getting the light back without undoing the designs** (each is a small change to one design's palette):
- **Programme Guide, Reverse Video and Porcelain Atlas.** Set `--shadow: 0 0 #0000` instead of `none`. That restores Home's resting glow, the card-hover glow, the chat box's focus glow and the landing glow at once. Today each is an invalid `var(--shadow), glow` declaration.
- **The four related designs.** Set `screenGlow` back to 1.0 (or `screen` to #6dff9c): the bloom and her screen's halo return.
- **Signal Legend and Flight Deck.** Append `0 0 80px -36px color-mix(in srgb, var(--phosphor) 45%, transparent)` to their `.crt` box-shadow lists.
- **Lamps.** Give Flight Deck's rails `box-shadow: 0 0 8px var(--brand)` and let them breathe, and drop Reverse Video's `animation:none`.
- **The typed-in field.** Put the 22px `lit` halo back beside the crisp ring in Programme Guide and Flight Deck.
- **Tiles, page icon and today.** Restore the title tile's raster (`repeating-linear-gradient(to bottom, rgb(0 0 0/.22) 0 1px, transparent 1px 3px)`) and a small glow in each design's own accent. Give the reverse-video or boxed current page a faint accent glow on its edge, and today a small amber glow.
