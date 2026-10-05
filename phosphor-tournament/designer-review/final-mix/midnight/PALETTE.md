# Midnight

**The idea:** FamilyDB as a screen in a dark kitchen at night, with a blue-black page, a darker panel, soft-white ink, each person's colour lit like a window, and Vera's green glass the one green light among them.

**Night was designed first** and is the default on `:root`. Day is the same kitchen with the lights on, and its panel stays midnight. Day applies when the device asks for light, or with `data-theme="light"`.

| Token | Night | Day |
|---|---|---|
| page / ink | #0B1020 / #E3E8F3 | #EEF1F7 / #0B1020 |
| line / control edge | #262F47 / #7884A3 | #C4CAD8 / #6C7489 |
| panel `--band` | #04060D | #0A0F1E |
| Ask glass / Send | #07130F / #6DFF9C | #0E1312 / #6DFF9C |
| late, the only red | #FF7369 | #B42318 |
| set up (sodium amber) / done | #F6B04A / #7FE3A5 | #8A4B00 / #17703F |
| today, Vera | #6DFF9C | #0B8457 |
| focus (moonlight) | #9DB9FF | #2D4FC4 |

| Person | Avatar (both themes) | Day stripe |
|---|---|---|
| p1 Sam, moon blue | #96B5FB | #607FCA |
| p2 Alex, iris | #958DF5 | #5144A0 |
| p3 Maya, lagoon | #69BAB8 | #016868 |
| p4 Theo, apricot | #ECB489 | #B17443 |
| p5 heather | #A78BC2 | #614978 |
| p6 sky | #95DAF8 | #277895 |
| p7 ochre | #C6950A | #936E09 |
| p8 sage | #93A066 | #586328 |

Every avatar takes a midnight letter, and the weakest is 6.4:1. At night the avatar is also the stripe, with a 9 px glow.

## Checks

`node _kit/palette.js check` measures 224 contrast pairs and every one passes (4.5:1 for text, 3:1 for edges, stripes and plates). The colour-blind test uses the Machado 2009 simulation and CIEDE2000 distances. Closest pairs:
- avatars and night stripes: 8.4, moon blue and lagoon (tritanopia);
- day stripes: 7.4, apricot and ochre (tritanopia);
- the family's four: 8.4.

`_kit/people-search.js` found the people. `build` and `sheet` write `style.css` and `palette.html` from the same values.

## Where it is weaker

- At night the panel is only 1.07:1 against the page. A hairline edge and the plates carry it.
- Vera's glass against the panel is 1.07:1 (ΔE 7.7). Hue, her phosphor rim and her round corners keep them apart.
- By day apricot and ochre stripes are 7.4 apart for tritanopes. Names are always beside them.
- Ochre and apricot near set-up amber for colour-blind eyes; setup always shows ⚠.
- Nothing yet lets a family choose a theme. A setting that writes `data-theme` would make night the default on every device.
