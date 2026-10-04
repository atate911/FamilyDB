**Rail yellow**

The idea: like good station signage, a deep rail-blue panel and a crisp light page with blue-black ink, with one signal yellow, always a solid plate under dark letters, marking what you act on next.

- The panel is #0B2C69 (#13336F at night) and the phone's top bar follows it. Links and the primary button are the same blue. The page is #F5F6F8 with #0E1726 ink, and blue-black #0D1420 at night.
- Yellow #FFC917 appears only as a plate: Home's date, the calendar's today, the Leave by label and the panel's "you are here" edge. Setup and warnings are now copper (#A1430B with ⚠ on a peach panel), so they can't be confused with the yellow. Red means late and nothing else; the panel's late plate gets a white rim so it holds against the blue.
- People: cobalt, violet, plum (Maya, no more pink), tangerine, petrol, sky, sand, chestnut. Each has its own letter colour, white or ink (`--pN-on`), and a `-lit` variant for the panel. Every avatar letter passes AA (5.0:1 at worst).
- Colour-blind check, closest pair (CIEDE2000; protanopia / deuteranopia / tritanopia): avatars 12.5 / 12.1 / 15.8, day stripes 9.2 / 10.9 / 7.0, night stripes 6.7 / 6.8 / 7.7. The weakest is cobalt against violet at night.
- Vera's glass, phosphor Send, glow and cursors are unchanged. Her box at night is now green-charcoal (`--ask-field`), so it doesn't pick up the blue page.

Every page is rendered light and dark in `shots/`. `palette.html` is new. `PALETTE.md` is written, and `STANDARD.md` has a new colour section, §7 table and dark-theme paragraph. `_kit/palette-check.py` measures every pair from the tokens: all pass. `_kit/make-palette.py` rebuilds `palette.html` from the tokens.

**Unfinished or weaker:**
- Slots 5–8 have no family member, so their colours appear only on the palette page.
- Sky, sand and tangerine avatars are faint at their edges on white paper; the letter carries them.
- `PALETTE.md` has about 300 words of text, but a raw `wc -w` gives 370 because it counts the table pipes.
