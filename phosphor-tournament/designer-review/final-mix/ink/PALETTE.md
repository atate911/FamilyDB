# Ink

**The idea:** almost no colour (a white page, black ink, a black panel, untinted greys), so the only colours on screen are the family's eight inks, late red and Vera's green glass.

| Token | Day | Night |
|---|---|---|
| page / ink | #FFFFFF / #000000 | #121212 / #FFFFFF |
| panel | #000000 | #000000, #3D3D3D edge |
| links, button, done, setup | ink (setup on #EBEBEB, with ⚠) | white |
| late, the only red | #D60000 | #FF5A4F |
| today, Vera | #0B8457 | #6DFF9C |
| Ask glass | #0A1611 | #0A1611 |

| Person | Avatar, letter | Stripe day / night |
|---|---|---|
| Sam, ultramarine | #2A16D6, white | #2A16D6 / #5A49E2 |
| Alex, cyan | #1CC2D8, black | #00A2B2 / #1CC2D8 |
| Maya, violet | #8A41FB, white | #8A41FB / #8550FF |
| Theo, tangerine | #FF8C33, black | #F76300 / #FF8C33 |
| p5 chrome yellow | #FFD12E, black | #A0943B / #FFD12E |
| p6 cornflower | #5B94FA, black | #5491FF / #5B94FA |
| p7 grape | #6B0781, white | #6B0781 / #9B32A9 |
| p8 umber | #8C5A00, white | #8C5A00 |

**Checks** (`python3 _kit/palette-check.py`): all 202 contrast pairs pass in both themes. The weakest avatar letter is 5.0:1. Colour-blind check (Machado 2009, CIEDE2000), closest pair:
- avatars: 10.1 (tangerine and yellow, deuteranopia)
- the family's four: 12.4
- day stripes: 7.0
- night stripes: 6.3 (ultramarine and violet, protanopia)

`_kit/palette-sheet.py` rebuilds `palette.html`.

**Where it is weaker**
- Done, Working and Set up lost their green and amber. Ink, ⚠ and words carry them, so they are quieter at a glance.
- Yellow can't be a stripe on white. Its stripe is olive-gold, the one that doesn't match its avatar.
- For red-blind eyes, umber is the person nearest late red (5.6). Late always says "days late".
- At night, only a hairline separates the black panel from the #121212 page.
- On the grey weekend wash, the four lightest stripes drop to 2.7:1.
- The panel and Vera's glass are both near-black. Her green tint, rim and round corners keep them apart.
