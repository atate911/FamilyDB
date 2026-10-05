# Home Computer

**The idea:** the family machine of the early 80s beside FamilyDB's green screen: a putty case for the page, a brown-black keyboard for the panel, the striped badge colours for the family's pens, one orange key for "this one", and the green screen kept for Vera.

| Token | Day | Night | Job |
|---|---|---|---|
| `--paper` / `--ink` | #E3E1DC / #1D1915 | #171513 / #EEEAE3 | putty case; brown-black ink |
| `--band` | #231C17 | #2E251E | panel, family stripe on its edge |
| `--signal` | #F07C1E | #F57F22 | today, primary button, Tomorrow, Yes!, you are here |
| `--warn` | #8F3E00 | #FF9B4D | set up, with ⚠ |
| `--alert` | #B0241A | #FF8B74 | late, the only red |
| `--done` | ink | putty-white | a ticked box |
| Glass, phosphor | unchanged | unchanged | Vera's alone |

| Pen | Avatar, letter | Stripe day / night |
|---|---|---|
| p1 Sam, cobalt | #2F5FD0, white | #2453C3 / #3565D7 |
| p2 Alex, violet | #A684E0, ink | #8664C2 / #AC8AE6 |
| p3 Maya, mustard | #E0AE2E, ink | #A27200 / #E3B000 |
| p4 Theo, turquoise | #2BA8A4, ink | #008E81 / #00B6B2 |
| p5 walnut | #66482E, white | #5E4832 / #A4805F |
| p6 sky | #7CC3F0, ink | #5B7F9A / #7CC8F2 |
| p7 petrol | #1F5F6E, white | #226170 / #4E95A6 |
| p8 aubergine | #4E2A6E, white | #4C286C / #9A72C6 |

**Checks** (`python3 _kit/palette-check.py`): all 214 contrast pairs pass in both themes; the weakest avatar letter is 5.25:1. Colour-blind check (Machado, CIEDE2000), closest pairs: avatars **10.4** (violet and sky, deuteranopia), day stripes **7.1** (cobalt and violet, protanopia), night stripes **7.6** (turquoise and sky, tritanopia).

**Where it is weaker**
- Maya's mustard sits next to the orange key, 4.9 apart for deuteranopes at night.
- Sky's day stripe is greyed to keep 3:1.
- Walnut (unused) is 5.2 from late red for protanopes. Late always says "days late".
- "Working" stays green, beside Vera's green.
