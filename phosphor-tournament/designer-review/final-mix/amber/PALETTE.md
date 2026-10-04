# Amber Terminal

**The idea:** a clean light page, navy-black ink and a near-black navy panel, with amber phosphor lighting the next thing you act on, like an old amber terminal, while Vera keeps the green one.

| Token | Day | Night |
|---|---|---|
| `--paper` / `--ink` | #F6F6F3 / #0F1420 | #0F1218 / #ECEEF2 |
| `--band` (panel) | #0B1324 | #18233A |
| `--signal` on `--screen` | #FFB000 on #0B1324 | #FFB627 on #1C2842 |
| `--alert` (late) | #B42318 | #FF7578 |
| `--warn` (setup) | copper #7A3510 | #E89060 |
| `--ok` | #17703F | #7FE3A5 |
| Glass, phosphor | unchanged | unchanged |

**Amber or copper?** Amber is only ever lit: amber letters on navy (today, Tomorrow, Leave by, the primary button), or an amber plate on the panel (you are here). Copper is only ever printed on a paper tint, with ⚠.

| Person | Tone | Avatar, letter | Stripe, night |
|---|---|---|---|
| p1 Sam | cobalt | #3A64C8, white | #6A90FA |
| p2 Alex | violet | #563483, white | #8D67D2 |
| p3 Maya | teal | #3F8C87, ink | #4FA59E |
| p4 Theo | olive | #8E9142, ink | #CBCA73 |
| p5 | plum | #7A5682, white | #B58BBE |
| p6 | sky | #56A9D6, ink | #6DBDF2 |
| p7 | walnut | #6A4428, white | #C28A5F |
| p8 | petrol | #1C4A52, white | #A6CDD5 |

**Checks** (`python3 _kit/palette-check.py`): all 113 pairs pass in both themes (text AA, controls and stripes 3:1). The weakest avatar letter is 4.7:1. Colour-blind (Machado simulation, CIEDE2000): the closest avatars are 11.1 (cobalt and teal, tritanopia). The closest stripes are 8.2 by day (teal and plum, deuteranopia) and 7.9 at night (cobalt and violet, deuteranopia). Amber and copper stay at least 8 apart under every simulation. `_kit/palette-sheet.py` writes `palette.html` from the tokens.

**Where it is weaker**
- Late red and copper are 3.0 apart for protanopes. Late always says "days late", and setup always has ⚠.
- Theo's night stripe is 3.5 from Vera's green for protanopes.
- By day the panel and Vera's glass are both near-black. Her green rim and round corners keep them apart.
- On the night panel the late plate is 3.0:1. Its text is 5.3:1.
- The amber rule beside Leave by is decorative (2.2:1).
