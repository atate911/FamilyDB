# Enamel

**The idea:** the colours of old enamel signs and good painted interiors. The page is warm grey plaster, the panel is a deep petrol sign, the people's colours are earthy enamels, and Vera's green glass is still the one lit thing.

| Token | Day | Night |
|---|---|---|
| `--paper` / `--paper-2` | #ECE9E5 / #DFDCD7 | #161513 / #22201E |
| `--ink` (petrol-black) | #162025 | #F0ECE7 |
| `--line` / `--edge` | #C9C5C0 / #797570 | #34312E / #847F7A |
| `--band` (the panel) | #0D2D40 | #143344 |
| `--alert` (late, the only red) | #AF3126 | #F58D79 |
| `--warn` / `--warn-soft` | #84571A / #F3E5C5 | #EDBB64 / #2A2112 |
| `--ok`, `--today-bg`, `--vera` | #276C3F, #0B8457, #0A6A4B | #85E3A0, #6DFF9C, #6DFF9C |
| Glass, phosphor, Send | unchanged (#0E1312, #6DFF9C) | unchanged |

| Slot | Colour | Avatar | Stripe (day / night) | Letter |
|---|---|---|---|---|
| p1 Sam | slate blue | #6187CE | #445FB4 / #668DC8 | 4.6:1 |
| p2 Alex | heather | #A49FDA | #7776D4 / #B4A9F3 | 6.7:1 |
| p3 Maya | plum | #AB79A5 | #764778 / #A57B9D | 4.7:1 |
| p4 Theo | ochre | #C1843C | #7C480C / #AF7C3A | 5.2:1 |
| p5 | teal | #69AEA5 | #076357 / #59C2BE | 6.5:1 |
| p6 | duck-egg | #88CADB | #3C889C / #9EDCF2 | 9.1:1 |
| p7 | lichen | #A2AA77 | #788850 / #9DB06B | 6.7:1 |
| p8 | mustard | #D4BD65 | #8D6E00 / #E0CE9B | 8.9:1 |
| p0 | Everyone | #C7C3BE | #847F7A / #A29E98 | house icon |

Going round the wheel, the colours alternate light and dark, so neighbours differ in lightness as well as hue.

**Colour-blind check** (`python3 _kit/check-colour.py`, Machado 2009 simulation, CIEDE2000). The closest pair of avatars is 8.7: plum and teal under deuteranopia, slate blue and plum under protanopia, teal and duck-egg under tritanopia. The closest pair of route stripes is 10.5 by day and 9.8 by night. All 226 contrast pairs pass: text is AA and controls and stripes are at least 3:1, in both themes.

**Where it is weaker**
- Theo's stripe is a dark raw umber, well below his ochre avatar, so it parts from mustard and lichen for colour-blind eyes.
- 8.7 is distinct but not far apart. Names and initials still say who is who.
- Vera's glass and the panel are both very dark (1.3:1). What keeps them apart is hue (green-black against petrol), her round corners and the phosphor ring.
- The late plate on the panel is 2.5:1 against the panel. Its text is 5.6:1.
