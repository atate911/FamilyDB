# Metro lines

**The idea:** the family as a transit map: a white sheet, black ink, a deep navy key panel, and each person one flat line colour, the same on an avatar, a route stripe and a rule.

## Palette (light / dark)

| Token | Light | Dark |
|---|---|---|
| page / ink | #FFFFFF / #0D0F12 | #0D0F12 / #EEF0F3 |
| hairline / control edge | #D6D9DF / #737A85 | #2C3138 / #7F8690 |
| panel `--band` | #0F1B33 | #172441 |
| today, Vera | #0B8457 | #6DFF9C |
| set up / late | #7A4D00 / #B42318 | #F5B94A / #FF8B74 |
| glass / phosphor | #0E1312 / #6DFF9C | unchanged |

| Person (line) | Light | Dark |
|---|---|---|
| p1 Sam (blue) | #3D5FF1 | #7593E3 |
| p2 Alex (teal) | #066C78 | #14B1C4 |
| p3 Maya (violet) | #5530B8 | #8350F9 |
| p4 Theo (amber) | #CF7A11 | #D9781E |
| p5 (sky) | #4A98C7 | #41CAFF |
| p6 (plum) | #9C4C9A | #AF49B3 |
| p7 (bronze) | #9F6910 | #F2B652 |
| p8 (petrol) | #14424F | #337E8B |
| Everyone (grey) | #8A919B | #8A919B |

Each line's base is also its mark. Each has one wash, an ink for names, and a white or black avatar letter, whichever passes AA (lowest 4.67:1).

## Checks

`node _kit/palette-check.js style.css`: every floor passes in both themes (AA text, 3:1 controls and stripes).

**Colour-blind** (Machado simulation, CIEDE2000): the closest pair is teal/plum at **ΔE 7.7** (light, deuteranopia) and teal/sky at **ΔE 8.2** (dark, tritanopia). Among the family's four, the closest pair is 11.2 light and 8.5 dark. No line comes within 6.8 of late red or 7.2 of Vera's green.

## Weaker

- Pairs under ΔE 8 can be confused alone; names and faces always say who.
- Bronze (p7, unused) is near red for deuteranopes (6.8). Theo's amber is near the night coral for tritanopes (6.9), but late also says "days late".
- Night plum is the nearest to pink.
- The dark panel is only 1.25:1 against the dark page. Hue, not value, separates them.
