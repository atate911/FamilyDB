# Aubergine & Brass

**The idea:** a well-kept house: warm stone walls, aubergine-black ink beside a deep aubergine panel, brushed brass on whatever you act on next, the family in jewel tones, and Vera's green glass the one lit thing.

| Token | Day | Night |
|---|---|---|
| page / ink | #E9E6E4 / #1E1220 | #141115 / #EEE9E6 |
| panel | #2B1530 | #2F1936 |
| brass (you are here, Tomorrow, today) | #CFA650 | #DDB865 |
| primary button | aubergine, brass letters | brass plate |
| focus | #5E2C66 | #E6C677 |
| late / setup (copper, ⚠) | #B3261E / #7C3E0A | #FF8B7A / #D9823F |
| Vera, glass, phosphor | unchanged | unchanged |

| Person | Avatar | Stripe day / night |
|---|---|---|
| Sam, sapphire | #2F5CDA | #3F6EEB / #4E7EF8 |
| Alex, amethyst | #61318B | #62239A / #D9BEF9 |
| Maya, peacock | #0BAEAF | #0E8A8B / #18BDBF |
| Theo, topaz | #C06E08 | #B06A00 / #F38E12 |
| p5 peridot | #8FAB54 | #6F8640 / #A6C367 |
| p6 cerulean | #0B6B88 | #05546B / #3199C0 |
| p7 tiger's eye | #86501C | #6A3A12 / #A8683C |
| p8 tanzanite | #7E7FCB | #5A50C6 / #9FA1FD |

**Checks** (`python3 _kit/palette-check.py`): all 198 contrast pairs pass in both themes. The weakest avatar letter is 4.7:1. Colour-blind (Machado simulation, CIEDE2000), closest pairs:
- avatars: 9.0 (Alex and p6, deuteranopia)
- day stripes: 7.5 (Theo and p5, protanopia)
- night stripes: 7.4 (Sam and p6, tritanopia)
- the family's four: 10.9 or more

**Where it is weaker**
- Alex's night stripe is a pale amethyst. Its lightness is what keeps it apart from sapphire and tanzanite.
- For protanopes, copper is about 4 from late red. Late always says "days late" and setup always has ⚠.
- Tiger's eye (unused) is the colour nearest red for deuteranopes.
- Today's brass stamp is 1.8:1 against the stone. Its letters (7.9:1) carry it.
- Today's calendar wash is close to cream.
