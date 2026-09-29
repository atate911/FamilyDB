# The Phosphor Kit

The original page's lit-tube marks. CSS is from `/home/user/FamilyDB/src/familydb/web/static/style.css` as written (whitespace aside), cut to the
declarations that draw the light; headings give its lines. RM (reduced motion), MC (more contrast)
and FC (forced colours) are as its rules compute in Chromium, not always as STYLE.md says. Shots:
`rounds/r10/out/00-current/shots/`; crops: `tmp-phosphor/`.

## The DNA in one paragraph

A bright phosphor (#6dff9c, 15.2:1) on a green-black (#0b0e0d), giving off light wherever it
appeared. Lit words, marks and the button had a two-layer halo, tight then wide. The monitors
drew VT323 blurred a third of a pixel under three halos, behind scanlines, a sheen and a dark
curved edge. Lamps were glowing dots on the black: breathing status lights, power lights, the
radar's hub and blips, block cursors, her screen's glyphs. Surfaces caught a
faint top-edge highlight, a haze hung at the top, Home's greeting was lit from below through
scanlines, and the light behaved like phosphor: on at once, fading over 1.2s, breathing, sweeping.
**Scarcity:** where the phosphor is, the halo shows at 100%; elsewhere the page is grounded, one
green screen to a page. Glare (halos everywhere, blurred body text, page-wide scanlines) loses it
as surely as a halo too faint to see. `home.png`: 1px under Send (x=200) the pool reads
(37,80,52), the box beside it about (14,26,20); the top haze (14,23,18) just under the bar
mid-page, (11,14,13) at the sides, only (11,15,14) through the bar.

## How it reaches a design

- **Main palette:** every effect is there. `theme.py` re-tints each `rgb(109 255 156 / a)`: off
  the screens to `halo` if set, else `lit` on its LIT_LINES (a field's caret and edge, checks, the
  OK fill, meters, setup steps, a done task, the ask box's focus), else `brand`, alpha times
  `glow`; on the screens (L1122-1349, L1367-1414) to `screen` times `screenGlow`, as are the
  `color-mix(in srgb, var(--phosphor) N%, transparent)` there; L129 to `top-glow` times `topGlow`.
  `--accent` mixes (E9, E11) and MC/FC are never scaled. To restore the light, set all three to
  1.0 (the leaders: 0.9-0.95, 0.8, 1.0, `lit` #86d9a6) and drop css that cancels an effect: a
  shadow, filter or animation of `none`, a pseudo-element off, an opaque bar or tray over a glow.
- **Your `css` is not re-tinted.** Write `color-mix(in srgb, var(--brand) 45%, transparent)` for
  `rgb(109 255 156 / 0.45)`, or use `--screen`, `--lit`, `--accent`; there is no `--halo` or
  `--top-glow` in a main palette (theme.py defines `--halo` only on a clean sheet): write the
  colour out. Hot cores are the phosphor and white: `#a9ffc7` is
  `color-mix(in srgb, var(--screen) 58%, #fff)`, `rgb(146 255 184)` 73%, `rgb(210 255 225)` 30%,
  `#dcffe8` 24%, `#e4fff0` 17%.
- **A clean sheet** gets only the tokens (`--halo`, `--wash`, `--bezel`, `--bar` when set),
  `--sans`, `--mono`, `--terminal` and the faces; it copies `--glow`, `--afterglow`, `--glow-in`,
  `--shadow`, `--phosphor*`, `--sweep`, keyframes and Access. Glow numbers do nothing there.
- **Own markup:** keep `_ui.html`'s structure: `.crt > .crt-tube`; `.radar > svg, .radar-sweep,
  .radar-say`, the svg's `.radar-rim/-ring/-cross/-ticks/-label/-hub` and `.blip.bN > .blip-ping,
  .blip-halo, .blip-core`; `.presence.vN > .presence-glass`; `svg.crt-face` with `.eye` paths.

Tokens, L75-80:
```css
  --glow: 0 0 0 1px rgb(109 255 156 / 0.35), 0 8px 28px -10px rgb(109 255 156 / 0.7);
  --afterglow: 1.2s cubic-bezier(0.2, 0.7, 0.3, 1);
  --glow-in: 0.12s;
  --shadow: inset 0 1px 0 rgb(255 255 255 / 0.035), 0 12px 32px -22px rgb(0 0 0 / 0.9);
```

## E1 `lit-word` (L194-197): the layered halo on a lit word
A tight bloom inside a wide faint one, which is how the eye knows a thing gives off light.
**Where:** `.glow`, on "mind" in Home's question (`_ask.html` L17).
```css
.glow { color: var(--green); text-shadow: 0 0 0.45em rgb(109 255 156 / 0.45), 0 0 1.3em rgb(109 255 156 / 0.22); }
```
**Bring back:** one or two machine words per view, 1.2rem and up, never body copy; flat below
`glow` about 0.6-0.7 (lessons.md). **RM:** static. **MC:** no halo (L2102).

## E2 `mark` (L251-275, 2065, 2072): the mark's bloom and the cursor
The smiling monitor on a dark tile, strokes bleeding light, a halo round the tile, and a glowing
block cursor that blinks 8 times, then stays lit. **Where:** the bar (`base.html` L54-55), the
foot (L130).
```css
.brand-mark { color: var(--green); background: radial-gradient(circle at 50% 35%, #173022, #0e1512 70%);
  border: 1px solid rgb(109 255 156 / 0.28); border-radius: 11px; box-shadow: 0 0 22px -6px rgb(109 255 156 / 0.55); }
.brand-mark .icon { width: 1.3rem; height: 1.3rem; stroke-width: 2; filter: drop-shadow(0 0 3px rgb(109 255 156 / 0.75)); }
.caret { flex: none; width: 0.5rem; height: 1.05rem; margin-left: -0.35rem; background: var(--green);
  border-radius: 1px; box-shadow: 0 0 10px rgb(109 255 156 / 0.8); animation: blink 1.2s steps(1) 8; }
.foot-mark .icon { color: var(--green); filter: drop-shadow(0 0 3px rgb(109 255 156 / 0.6)); }
@keyframes blink { 50% { opacity: 0; } }
```
**Bring back:** the icon's drop-shadow full, even on a calm page. **RM:** cursor lit, still.
**MC:** the tile's halo and both icons' glow go; the caret keeps its glow. **FC:** caret
CanvasText.

## E3 `button-glow` (L75, 527-546): the primary button's ring and pool
A 1px ring and light pooled 8px under the button, as if the tube lit the desk; brighter on hover,
then fading. **Where:** `button, .button`; the other kinds set `box-shadow: none`.
```css
button, .button { background: var(--green); box-shadow: var(--glow);
  transition: background-color 0.15s, box-shadow var(--afterglow), border-color 0.15s, color 0.15s, transform 0.08s; }
button:hover, .button:hover { background: var(--green-hover);
  box-shadow: 0 0 0 1px rgb(109 255 156 / 0.5), 0 10px 34px -10px rgb(109 255 156 / 0.85);
  transition-duration: 0.15s, var(--glow-in), 0.15s, 0.15s, 0.08s; }
```
**Bring back:** one primary per view; calm the rest as secondaries (`"quietFilter": true`, or a
variant's classes), not by flattening all. **RM:** switches at once. **MC:** no ring or pool at
rest (L2103); hover still lights both (`button:hover` outranks it).

## E4 `box-glow` (L586-615, 926-931, 1452): the box being typed in
The edge turns phosphor, with a 3px soft ring, a 22px bloom and a green caret, fading once you
leave. Home's box glows faintly even at rest. **Where:** every field, the ask box, sign in.
```css
input[type="text"], input[type="password"], input[type="search"], input[type="url"], input[type="date"], input[type="time"],
input[type="datetime-local"], input:not([type]), textarea, select {
  caret-color: var(--green); transition: border-color var(--afterglow), box-shadow var(--afterglow); }
input:focus, textarea:focus, select:focus { outline: none; border-color: var(--green);
  box-shadow: 0 0 0 3px rgb(109 255 156 / 0.16), 0 0 22px -6px rgb(109 255 156 / 0.55); transition-duration: var(--glow-in); }
.ask:focus-within { border-color: var(--green); box-shadow: var(--shadow), 0 0 0 3px rgb(109 255 156 / 0.14), 0 0 30px -8px rgb(109 255 156 / 0.5); transition-duration: var(--glow-in); }
.welcome .ask { background: rgb(9 12 11 / 0.72); border-color: color-mix(in srgb, var(--green) 30%, var(--edge));
  box-shadow: var(--shadow), 0 0 38px -20px rgb(109 255 156 / 0.6); }
```
L931 `.welcome .ask:focus-within` repeats `.ask:focus-within`'s border and glow.
**Bring back:** caret and edges take `lit` (L601, 612, 928), as does the ask box's glow (L931,
1452); a field's ring and bloom (L613) and Home's resting halo (L929) stay `brand`/`halo`. **RM:**
on and off at once. **MC:** fields and the chat's box keep it; Home's box loses its resting halo
(L2104) but lights fully when typed in (`.welcome .ask:focus-within` outranks it).

## E5 `focus` (L147-148, 1217): the focus ring and inverse selection
```css
::selection { color: var(--on-bright); background: var(--green); }
:focus-visible { outline: 2px solid var(--green); outline-offset: 3px; border-radius: 6px; }
.crt a:focus-visible { outline-color: var(--phosphor); }
```
A crisp 2px line 3px off the control (`focus-*.png`), always `brand`, never calmed. RM and MC
leave it.

## E6 `top-haze` (L127-134, 240): the afterglow at the top of every page
A faint ellipse over the top, as if a screen had just gone off; the 82% bar all but hides it, so
it shows as a green breath just below.
```css
html { background: radial-gradient(60% 38% at 50% -10%, rgb(109 255 156 / 0.075), transparent 70%), var(--bg);
  background-repeat: no-repeat; }
.bar { background: rgb(11 14 13 / 0.82); }
```
**Bring back:** `topGlow`, `top-glow`; the `bar` token draws the bar at 88%, a translucent bar
shows more. **RM, MC:** static, untouched.

## E7 `greeting-glow` (L896-913): Home lit from below, through scanlines
The greeting glows from its bottom-left corner, a whisper of `wash` top right. Light scanlines
(white 2.8%, 1px in 4) lie only inside the glow, the one place off a monitor that has them.
```css
.welcome { background: radial-gradient(70% 90% at 0% 100%, rgb(109 255 156 / 0.13), transparent 62%),
  radial-gradient(45% 70% at 100% 0%, rgb(108 212 255 / 0.07), transparent 70%), var(--surface); }
.welcome::before { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(to bottom, rgb(255 255 255 / 0.028) 0 1px, transparent 1px 4px);
  -webkit-mask-image: radial-gradient(60% 90% at 0% 100%, #000, transparent 75%);
  mask-image: radial-gradient(60% 90% at 0% 100%, #000, transparent 75%); }
```
**Bring back:** `glow`, `wash`, `washGlow`; another hero may take the `::before`, never
page-wide. **RM:** static. **MC:** the scanlines go (L2101); the glow stays.

## E8 `edge-light` (L80, 508, 871): top-edge highlights
A 1px white line inside the top: 3.5% on cards (`--shadow`), 5% on the chosen tab, 8% on a
monitor's case (E12); a sheen on glass (E14, E17). At 8% a card reads as plastic.
```css
  --shadow: inset 0 1px 0 rgb(255 255 255 / 0.035), 0 12px 32px -22px rgb(0 0 0 / 0.9);
.tabs a[aria-current="page"] { color: var(--ink); background: var(--surface-3); box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.05); }
```
**RM, MC:** kept (MC drops it only with a whole shadow, as on Home's box).

## E9 `afterglow` (L78-79, 836-848, 1051-1053): on at once, fading over a second
Every lit thing (buttons, fields, cards in their kind's colour, ticks, starters, steps, choices)
lights in 0.12s and fades over 1.2s (`motion-glow-0..3.png`): long on the resting rule,
short on the lit one.
```css
.card { transition: border-color var(--afterglow), background-color 0.2s, transform 0.2s, box-shadow var(--afterglow); }
.card:has(h2 a):hover { background: var(--surface-2); border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
  box-shadow: var(--shadow), 0 0 40px -18px color-mix(in srgb, var(--accent) 60%, transparent); transform: translateY(-2px); }
.idea-card:hover, .card:has(h2 a):hover { transition-duration: var(--glow-in), 0.15s, 0.2s, var(--glow-in); }
```
**Bring back:** each glow you add: `transition: box-shadow var(--afterglow)` at rest,
`transition-duration: var(--glow-in)` when lit. **RM:** switches at once. **MC:** unchanged.

## E10 `landed` (L835, 2092): an anchored panel flashes and fades
```css
.panel:target, :target > .panel, .fold:has(> :target) { animation: landed 1.8s cubic-bezier(0.2, 0.7, 0.3, 1); }
@keyframes landed { from { box-shadow: var(--shadow), 0 0 0 1px rgb(109 255 156 / 0.65), 0 0 40px -6px rgb(109 255 156 / 0.55); } }
```
**RM:** no flash. **MC:** flashes as usual.

## E11 `lit-tile` (L464-479, 290, 327): the icon on a small lit screen
The title's icon on a tiny screen of its section's colour: a halo, a raster 1px in 3, the icon
glowing; so do the bar's current place and the settings menu's icon, not the settings tiles.
```css
.title-icon { color: var(--accent);
  background: repeating-linear-gradient(to bottom, rgb(0 0 0 / 0.22) 0 1px, transparent 1px 3px), color-mix(in srgb, var(--accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); border-radius: 13px;
  box-shadow: 0 0 26px -8px color-mix(in srgb, var(--accent) 60%, transparent); }
.title-icon .icon { filter: drop-shadow(0 0 3px color-mix(in srgb, var(--accent) 70%, transparent)); }
nav a[aria-current="page"] .icon { color: var(--accent); filter: drop-shadow(0 0 5px color-mix(in srgb, var(--accent) 70%, transparent)); }
.menu.here > summary .icon { color: var(--accent); filter: drop-shadow(0 0 5px color-mix(in srgb, var(--accent) 70%, transparent)); }
```
**Bring back:** fed by `--accent`, so companions become light here. **RM:** static. **MC:** the
tile's halo, glow and raster go (L2103-2109); the bar's and menu's icons keep theirs (they outrank
`.icon`). **FC:** the tile is outlined.

## E12 `monitor` (L1131-1158): the case, its spill and the power light
Plastic lit from above, a deep shadow, an 80px phosphor spill (the tube lights the room), a power
light glowing in the chin. **Where:** Next up, sign in, 404/403, spend, On the radar.
```css
.crt {
  --phosphor: var(--green);
  --phosphor-bright: color-mix(in srgb, var(--phosphor) 45%, #fff);
  --phosphor-dim: color-mix(in srgb, var(--phosphor) 64%, #07120c);
  --phosphor-glass: color-mix(in srgb, var(--phosphor) 9%, #060a08);
  border-radius: 24px; background: linear-gradient(180deg, #1d2321, #151a18 45%, #101412); border: 1px solid #2c3431;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.08), inset 0 -2px 3px rgb(0 0 0 / 0.35),
    0 28px 50px -34px rgb(0 0 0 / 0.95), 0 0 80px -36px color-mix(in srgb, var(--phosphor) 45%, transparent);
}
.crt::after { content: ""; position: absolute; right: 1.25rem; bottom: 0.55rem; width: 0.4rem; height: 0.4rem;
  background: var(--phosphor); border-radius: 50%; box-shadow: 0 0 6px var(--phosphor); }
```
**Bring back:** `bezel` redraws the case, `screenGlow` scales the spill; keep spill and light on
a thin case. Spend re-lights it via `--phosphor` (L1655-1656: amber near the limit, red past).
**RM:** static. **MC:** all stays. **FC:** outlined, unlit; a picture-only monitor (sign in,
404/403, spend) is left out.

## E13 `tube` (L1159-1176): glass, text bloom and blur
Glass lit at the middle, a dark rim, a vignette; every word VT323 (1.5rem, never under 1.2rem)
with three halos and a 0.35px blur.
```css
.crt-tube { position: relative; isolation: isolate; overflow: hidden;
  color: var(--phosphor); font: 400 1.5rem/1.15 var(--terminal);
  background: radial-gradient(125% 115% at 50% 40%, var(--phosphor-glass), #07100b 55%, #030705);
  border-radius: 17px / 19px; box-shadow: inset 0 0 0 1.5px #020403, inset 0 0 36px 6px rgb(0 0 0 / 0.72);
  text-shadow: 0 0 1px color-mix(in srgb, var(--phosphor) 80%, transparent),
    0 0 9px color-mix(in srgb, var(--phosphor) 45%, transparent), 0 0 24px color-mix(in srgb, var(--phosphor) 20%, transparent); }
.crt-tube > :not(.radar) { position: relative; filter: blur(0.35px); }
```
**Bring back:** `screenGlow` 1.0 (0.8 thins the bloom); blur only the tube. **RM:** static.
**MC:** the halos go; glass, vignette and the words' blur stay (MC's and FC's `.crt-tube > *` is
weaker than `.crt-tube > :not(.radar)`). STYLE.md means the blur to go: add
`.crt-tube > :not(.radar) { filter: none; }` to your MC block.

## E14 `scanlines` (L1179-1197): scanlines, sheen and falloff
Dark 1px lines every 3px at 40%, over them a sheen at the top left and the edge falling to 60%
black (`tmp-phosphor/nextup.png`).
```css
.crt-tube::before { content: ""; position: absolute; inset: 0; z-index: 3; pointer-events: none;
  background: repeating-linear-gradient(to bottom, rgb(2 5 3 / 0.4) 0 1px, transparent 1px 3px); }
.crt-tube::after { content: ""; position: absolute; inset: 0; z-index: 4; pointer-events: none; border-radius: inherit;
  background: radial-gradient(85% 50% at 26% 4%, rgb(255 255 255 / 0.075), transparent 62%),
    radial-gradient(135% 125% at 50% 42%, transparent 55%, rgb(0 0 0 / 0.6)); }
```
**RM:** static. **MC/FC:** gone.

## E15 `strengths` (L1200-1228, 955-964): dim, normal, bright, inverse and the cursor
Three strengths (E12's `--phosphor-dim`, `--phosphor-bright`). A heading is inverse video with a
glow, a link (underlined 2px) goes inverse when pointed at, the block cursor blinks 10 times,
then waits lit. `.rel` (L955-964) is bright, uppercase, in `[ ]` pseudo-brackets; the spend bar
is characters, `[####....]`.
```css
.crt .bright { color: var(--phosphor-bright); }
.crt .dim { color: var(--phosphor-dim); text-shadow: 0 0 6px color-mix(in srgb, var(--phosphor) 25%, transparent); }
.crt .inverse, .crt a:hover { color: #04100a; background: var(--phosphor); text-decoration: none; text-shadow: none;
  box-shadow: 0 0 14px color-mix(in srgb, var(--phosphor) 55%, transparent); }
.crt-cursor { display: inline-block; width: 0.45em; height: 0.62em; margin-left: 0.2em; background: currentColor;
  box-shadow: 0 0 8px currentColor; animation: blink 1.06s steps(1) 10; }
```
**RM:** the cursor lit, still. **MC:** the dim halo goes; the inverse bar's and cursor's glow stay.

## E16 `power-on` (L1231, 2083-2088): switching on
The picture opens out of a bright line in 0.6s, on sign in and 404/403 only.
```css
.crt.power-on .crt-tube > * { animation: power-on 0.6s cubic-bezier(0.2, 0.7, 0.2, 1); }
@keyframes power-on { 0% { opacity: 0; transform: scale(1, 0.01); } 30% { opacity: 1; transform: scale(1, 0.01); }
  65% { transform: scale(1, 1.03); } 100% { opacity: 1; transform: none; } }
```
**Bring back:** start at `opacity: 0.05`, since the harness wants arrivals above 0. **RM:** none,
the picture is there at once. **MC:** plays.

## E17 `radar` (L1238-1348, 2080-2082): scope, hub, sweep with afterglow, and blips
Rings, cross and ticks in phosphor, blurred and drop-shadowed, round a lit hub; labels at 55%. A
conic sweep turns every 8s, a bright beam and a fading wedge. Each blip is a hot core in a soft
halo, the purest glowing dot on black: it flares as the sweep passes, rests at 30% (62% for the
next), never out; the next pings. Every radar today sits in a monitor, so `.crt .radar` drops
its own glass, outline and 48px halo (L1245-1249) and the tube's scanlines cover it; `.radar::after` (L1337-1348: sheen, scanlines, falloff) draws only on a radar alone.
**Where:** Next up, Ideas' map, 404/403 (`tmp-phosphor/v-home-radar.png`).
```css
.radar { --sweep: 8s; aspect-ratio: 1; overflow: hidden; isolation: isolate; border-radius: 50%; }
.radar svg { filter: blur(0.35px) drop-shadow(0 0 2px rgb(109 255 156 / 0.55)); }
.radar-rim { stroke: rgb(109 255 156 / 0.4); }  .radar-ring { stroke: rgb(109 255 156 / 0.2); }
.radar-cross { stroke: rgb(109 255 156 / 0.12); }  .radar-ticks { stroke: rgb(109 255 156 / 0.42); }
.radar-hub { fill: rgb(146 255 184 / 0.75); }
.radar-label { font: 500 10px var(--mono); fill: rgb(109 255 156 / 0.55); }
.radar-sweep { position: absolute; inset: 0; border-radius: 50%; background: conic-gradient(transparent 0deg 230deg,
  rgb(109 255 156 / 0.04) 255deg, rgb(109 255 156 / 0.12) 315deg, rgb(109 255 156 / 0.26) 350deg, rgb(146 255 184 / 0.45) 360deg);
  animation: sweep var(--sweep) linear infinite; }
.radar-sweep::after { content: ""; position: absolute; left: calc(50% - 0.5px); top: 1%; width: 1px; height: 49%;
  background: linear-gradient(to top, rgb(146 255 184 / 0.15), rgb(210 255 225 / 0.9)); box-shadow: 0 0 6px 1px rgb(109 255 156 / 0.55); }
.blip { opacity: 0.9; animation: blip var(--sweep) cubic-bezier(0.15, 0.7, 0.35, 1) infinite var(--at, 0s); }
.blip-halo { fill: rgb(109 255 156 / 0.24); }
.blip-core { fill: #a9ffc7; }
.blip.next { --rest: 0.62; opacity: 1; }
.blip.next .blip-halo { fill: rgb(109 255 156 / 0.4); }
.blip.next .blip-core { fill: #e4fff0; }
.blip-ping { fill: none; stroke: rgb(146 255 184 / 0.9); stroke-width: 1; opacity: 0.4; transform: scale(2.2); transform-box: fill-box;
  transform-origin: center; animation: ping var(--sweep) cubic-bezier(0.15, 0.7, 0.35, 1) infinite var(--at, 0s); }
.b1 { --at: calc(var(--sweep) * -11 / 12); }
.crt .radar { background: none; outline: 0; box-shadow: none; }
.crt .radar::after { display: none; }
@keyframes sweep { to { transform: rotate(1turn); } }
@keyframes blip { 0% { opacity: 1; } 62%, 100% { opacity: var(--rest, 0.3); } }
@keyframes ping { 0% { opacity: 0.9; transform: scale(1); } 32%, 100% { opacity: 0; transform: scale(3.6); } }
```
Lines are `fill: none; stroke-width: 1`; `.b2`-`.b11` run `* -10 / 12` to `* -1 / 12`.
**Bring back:** keep blip halos, hub and the lines' drop-shadow, or it is a diagram. **RM:** the
sweep rests at twelve; blips at 0.9 (next 1), its ping a still ring at 2.2x, 40%. **MC:** the lines' blur and drop-shadow go (L2107), and a lone
radar's halo and glass; hub, blips, halos and sweep stay. **FC:** hidden.

## E18 `flicker` (L1320-1335, 2078): the 404 on the scope
Two halos and a 0.4px blur, catching for an instant every 6s like a tube losing its picture.
```css
.radar-say { position: absolute; inset: 0; display: grid; place-items: center; color: var(--green);
  text-shadow: 0 0 0.3em rgb(109 255 156 / 0.6), 0 0 0.9em rgb(109 255 156 / 0.28); filter: blur(0.4px);
  animation: flicker 6s linear infinite; }
.crt .radar-say { font: 400 clamp(3.5rem, 16vw, 4.75rem)/1 var(--terminal); letter-spacing: 0; }
@keyframes flicker { 0%, 91%, 94%, 100% { opacity: 1; } 92% { opacity: 0.55; } 93% { opacity: 0.9; } }
```
**RM:** steady. **MC:** no halo or blur; it still flickers.

## E19 `her-screen` (L1375-1439, 2076): glyphs nobody can read
VT323 columns, dim trails under bright heads, glowing, blurred and scan-masked, on a phosphor
centre with a halo: at 36px, glowing dots on black (`tmp-phosphor/presence.png`). It falls a row
at a time while she thinks, once as Home opens. **Where:** her lines and name, her page's tile,
Who answers, the settings menu.
```css
.presence, .title-icon.presence, .section-icon.presence { position: relative; overflow: hidden;
  background: radial-gradient(circle at 50% 45%, rgb(109 255 156 / 0.16), #06110b 72%);
  border: 1px solid rgb(109 255 156 / 0.32); box-shadow: 0 0 18px -6px rgb(109 255 156 / 0.6); }
.glyph.presence { width: 1.1rem; height: 1.1rem; border-radius: 4px; box-shadow: 0 0 10px -3px rgb(109 255 156 / 0.65); }
.presence-glass { position: absolute; inset: 0; font-size: 6px;
  -webkit-mask-image: repeating-linear-gradient(to bottom, #000 0 2px, rgb(0 0 0 / 0.4) 2px 3px);
  mask-image: repeating-linear-gradient(to bottom, #000 0 2px, rgb(0 0 0 / 0.4) 2px 3px); }
.presence-glass::before, .presence-glass::after { top: calc(var(--from, 0) * -0.85em);
  left: calc(var(--across, 0) * -1ch); font: 400 1em/0.85 var(--terminal); white-space: pre; filter: blur(0.3px); }
.presence-glass::before { content: "…"; /* L1406 */ color: rgb(109 255 156 / 0.62); text-shadow: 0 0 2px rgb(109 255 156 / 0.55); }
.presence-glass::after { content: "…"; /* L1411 */ color: #dcffe8; text-shadow: 0 0 2px #a9ffc7, 0 0 5px rgb(109 255 156 / 0.85); }
.presence.v1 { --from: 4; --across: 3; }  .presence.v2 { --from: 8; --across: 1; }  .presence.v3 { --from: 12; --across: 5; }
.thread:not(.brief) .pending.is-thinking .presence-glass::before,
.thread:not(.brief) .pending.is-thinking .presence-glass::after { animation: fall 2.4s steps(16) infinite; }
.speaker .presence-glass::before, .speaker .presence-glass::after { animation: fall 2.4s steps(16) 1; }
@keyframes fall { from { transform: translateY(-13.6em); } to { transform: none; } }
```
Copy `content` whole from L1406 and L1411 (16 rows three times, broken by `\A`, so the fall
loops). Small, never a face. **RM:** still. **MC:** no mask, blur, glyph glow or tile halo; the
centre stays and the small `.glyph` keeps its halo (it outranks `.presence`). **FC:** an empty
outlined square.

## E20 `lamps` (L1645-1648, 2073): live lights that glow and breathe
A 0.62rem lit dot (`.light`, round), 8px glow and 18px halo, breathing every 3.2s; off a hollow
red ring, partly on a half-lit amber dot, so the shape says it too. **Where:** Status.
```css
.light.on { background: var(--green); box-shadow: 0 0 8px var(--green), 0 0 18px rgb(109 255 156 / 0.45); animation: breathe 3.2s ease-in-out infinite; }
.light.off { border: 2px solid var(--red); }
.light.part { border: 2px solid var(--amber); background: linear-gradient(90deg, var(--amber) 50%, transparent 50%); }
@keyframes breathe { 50% { opacity: 0.55; } }
```
An earlier build (git `01bfa69`, L841-848) had one before "Next up":
```css
.live { width: 0.5rem; height: 0.5rem; background: var(--green); border-radius: 50%;
  box-shadow: 0 0 8px var(--green); animation: breathe 2.6s ease-in-out infinite; }
```
**Bring back:** a lamp wherever something is live, with words (a `::before`, or a variant's
element); the thinking dots stay retired. **RM:** lit, still. **MC:** glow kept. **FC:** outlined.

## E21 `lit-states` (L697-711, 1108, 1573, 1616, 1908-1914, 1952, 2215-2224): small halos
OK badge, error dot, done task, today in amber (a date's leaf, the month), the current step, the
chosen AI company, the mic listening. Beside them, unhaloed green on a 6-12% tint: `.said`,
`.state.done`, CHANGED, done statuses, a hovered starter (L697, 735, 1503, 1779, 1916-1922, 1983,
1988).
```css
.said::before { content: "OK"; background: var(--green); box-shadow: 0 0 10px rgb(109 255 156 / 0.45); }
.error::before { content: ""; width: 0.55rem; height: 0.55rem; background: var(--red); border-radius: 50%; box-shadow: 0 0 8px var(--red); }
.task-done .task-box { background: var(--green); border-color: var(--green); box-shadow: 0 0 14px -4px rgb(109 255 156 / 0.8); }
.chip.is-today { border-color: rgb(255 184 80 / 0.55); box-shadow: 0 0 22px -8px rgb(255 184 80 / 0.7); }
table.month td.today time { color: var(--on-bright); background: var(--amber); box-shadow: 0 0 18px -2px rgb(255 184 80 / 0.65); }
.setup-progress a[aria-current="step"] { border-color: rgb(109 255 156 / 0.55); box-shadow: 0 0 22px -10px rgb(109 255 156 / 0.7); }
.setup-progress a[aria-current="step"] > span[aria-hidden] { color: var(--on-bright); background: var(--green); box-shadow: 0 0 10px rgb(109 255 156 / 0.5); }
.choice.chosen { border-color: var(--green); box-shadow: var(--shadow), 0 0 0 1px var(--green), 0 0 30px -12px rgb(109 255 156 / 0.6); }
button.mic.listening { box-shadow: 0 0 0 4px rgb(109 255 156 / 0.18), 0 0 22px -4px rgb(109 255 156 / 0.7);
  animation: listening 1.4s ease-in-out infinite; }
@keyframes listening { 50% { box-shadow: 0 0 0 8px rgb(109 255 156 / 0.08), 0 0 22px -4px rgb(109 255 156 / 0.7); } }
```
**Bring back:** LIT_LINES fills (OK, done task, step number, chosen card) take `lit`; other halos
stay `brand`, the mic always. Keep each tight (negative spread, 22px or less): a state, not a lamp.
**RM:** static; the mic's ring holds at 4px (also L2225-2227). **MC:** only the done task loses
its halo (L2103); today's leaf and date keep theirs (`.chip.is-today` outranks `.chip`), as do the
rest.

## E22 `face` (L2028-2030, 2089): the mark's face awake on sign-in
```css
.crt .crt-face { width: 8.5rem; overflow: visible; filter: blur(0.35px) drop-shadow(0 0 5px color-mix(in srgb, var(--phosphor) 60%, transparent)); }
.crt-face path { fill: none; stroke: var(--phosphor); stroke-width: 3.2; stroke-linecap: round; }
.crt-face .eye { transform-box: fill-box; transform-origin: center; animation: eyes 7s ease-in-out infinite; }
@keyframes eyes { 0%, 92%, 100% { transform: none; } 94%, 96% { transform: scaleY(0.12); } }
```
**RM:** eyes open. **MC:** no blur or glow on the face. **FC:** left out with its monitor.

## Access (L2094-2110), cut to the light
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
@media (prefers-contrast: more) {
  .welcome::before, .radar::after, .crt-tube::before, .crt-tube::after { display: none; }
  .glow, .radar-say, .chip-day, .crt-tube, .crt .dim { text-shadow: none; }
  button, .button, .title-icon, .brand-mark, .chip, .task-done .task-box, .radar,
  .welcome .ask, .presence, .title-icon.presence, .section-icon.presence { box-shadow: none; }
  .presence-glass { -webkit-mask-image: none; mask-image: none; }
  .presence-glass::before, .presence-glass::after { filter: none; text-shadow: none; }
  .icon, .brand-mark .icon, .title-icon .icon, .foot-mark .icon, .radar svg, .radar-say,
  .crt-tube > *, .crt .crt-face { filter: none; }
  .title-icon { background: color-mix(in srgb, var(--accent) 12%, transparent); }
}
```
MC's `:root` line (L2100) lifts the greys. Some rules lose to stronger ones (E3, E4, E11, E13,
E19, E21); copied as is, they behave as the original. FC (L2111-2126) outlines lamps, ticks,
dates, faces, tiles and her screen, makes the caret CanvasText, hides picture-only screens, the
radar, power light and scanlines. Print (L2130-2173, untouched by theme.py) is green-bar paper with tractor-feed holes. A clean
sheet carries all three blocks.

## Bringing it back into a design

1. `brand`/`screen` exactly #6dff9c; calm from ink, surfaces and fewer lit things, not duller green.
2. Full light on the mark and cursor, one primary per view, the box being typed in, focus, lamps,
   the key word, the monitors, her screen; elsewhere only material light (E8).
3. Main palette: the three numbers at 1.0, nothing zeroed. Clean sheet: E1-E21 as `color-mix`.
4. Two layers to every glow, on the afterglow pair; monitors keep E12-E17; keep RM, MC, FC.

**The harness refuses** inline `style` or handlers, a `<style>` element (SVG too), any script
(CSS `javascript:`/`expression(`, SVG), `@import`, anything from outside; `url()` only to the
page's files (relative or `/static/...`) or `data:image/`. Also `|safe`/`Markup`, a kept form
without its csrf or once token, a sprite that drops an icon.
