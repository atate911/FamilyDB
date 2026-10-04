# Fjord

**The idea:** a pale northern sky over deep slate water: a cool, quiet page where the only colours are the family's eight, fjord blue marks what you act on, and Vera's green glass is the one thing that glows.

| Token | Day | Night |
|---|---|---|
| paper / ink | #EEF2F6 / #161C24 | #0F141B / #E6ECF2 |
| line / edge | #C3CDD7 / #6B7886 | #2A323D / #7A8796 |
| panel `--band` | #252B4A | #272E52 |
| link / primary / focus | #2A3C8F / #2C3A80 / #2F55D4 | #AFC0FF / #B4C3FF / #9FB6FF |
| late (only red) / setup | #B42318 / #7A4D00 | #FF8B74 / #F2BA55 |
| today, Vera, glass, phosphor | unchanged | unchanged |

| Person | Avatar | Stripe day / night |
|---|---|---|
| p1 Sam, cornflower | #4C86DF | #2462C8 / #6F95F4 |
| p2 Alex, heather | #9A7EAE | #6A4C8C / #A58DBE |
| p3 Maya, cloudberry | #EB8F38 | #C26D14 / #E8913E |
| p4 Theo, sea | #5EC4C9 | #258B8C / #8DDEE0 |
| p5 pine | #7AAAA0 | #3B5F55 / #8CB3A8 |
| p6 lichen | #DDD585 | #66661C / #D2D87F |
| p7 rye | #B68E69 | #94704F / #C2A07A |
| p8 lupin | #AAB3FC | #7479C6 / #B8B2FF |

**Checks** (`node _kit/palette-check.js`): all 228 contrast pairs pass in both themes, avatar letters included. Colour-blind check (Machado simulation, CIEDE2000), closest pair:
- avatars: 9.3, cornflower and heather, protanopia;
- day stripes: 8.7, cornflower and heather, deuteranopia;
- night stripes: 9.1, cornflower and lupin, protanopia.

In normal vision, no person is within 17.7 of late red or 16.8 of Vera's green.

**Where it is weaker**
- Cornflower and heather are closest for red-green colour-blind eyes; names and initials still say who.
- Simulated, rye nears the night coral and lichen nears Vera's green; late always says "days late".
- Cornflower's and heather's letters pass with little to spare (4.7–4.9:1).
- The setup panel is the one warm, cream thing on a cool page.
