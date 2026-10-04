# Ultramarine

**The idea:** one saturated fountain-pen blue for everything the family does, on a bright white page under a midnight panel, with people in every colour but blue and Vera alone in phosphor.

| Token | Day | Night |
|---|---|---|
| page / ink | #FFFFFF / #0B0D14 | #0B0D18 / #EEF0F8 |
| hairline / control edge | #D6DAE4 / #6D7487 | #272B3E / #7A8199 |
| panel `--band` | #0E1550 | #131A56 |
| ultramarine fill (button, today, you are here, a tick) | #1F37E6 | #4A5CFF |
| links, focus | #1F37E6 | #9AA6FF |
| late (the only red) / set up / done | #C4252C / #8A5000 / #17703F | #FF8D80 / #F5B94A / #7FE3A5 |
| glass / phosphor | #0E1312 / #6DFF9C | unchanged |

| Person | Day (letter) | Night |
|---|---|---|
| p1 Sam, cerulean | #0A7DA4 (white) | #6ADCFF |
| p2 Alex, teal | #0BA08D (ink) | #59A28E |
| p3 Maya, violet | #A172FF (ink) | #A978FD |
| p4 Theo, cinnamon | #8E3E06 (white) | #D9731C |
| p5 ochre | #A97F10 (ink) | #F3BA30 |
| p6 aubergine | #5E2370 (white) | #B895CC |
| p7 sage | #87975F (ink) | #C0D3A6 |
| p8 slate | #2F4848 (white) | #A5CDCF |
| Everyone | #CDD1DA, stripe #6A7080 | #4A5064 |

By day, dark and mid colours alternate, so neighbours differ in lightness as well as hue. At night every colour takes an ink letter.

## Checks

`python3 _kit/palette-check.py`: all 230 contrast pairs pass in both themes (text AA, edges, stripes and plates 3:1). The weakest avatar letter is 4.7:1.

**Colour-blind** (Machado 2009, CIEDE2000): the closest pair is **9.8** (sage and ochre stripes by day, protanopia). Avatars: 9.9 by day, 10.5 at night. Among the family's four: 9.9 (Sam and Alex, tritanopia). `palette.html` shows every row simulated.

## Where it is weaker

- Sam and Alex are both cool and the closest of the four; names and initials sit beside them.
- Theo's cinnamon is the person nearest late red under simulation (7.2). Late always says "days late".
- At night the blue is two colours: a #4A5CFF fill (white text 4.9:1) and periwinkle links.
- The panel and Vera's glass are close in value (1.1:1). Hue, her round corners and the phosphor ring keep them apart.
- A kid's colour on the panel and top bar is decoration only (down to 1.5:1). The inverted plate says where you are.
- Maya's violet is the people colour nearest the ultramarine, so her lede links are ink.
