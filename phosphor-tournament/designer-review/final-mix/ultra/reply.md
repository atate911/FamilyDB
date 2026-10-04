The palette is **Ultramarine**.

**The idea:** one saturated fountain-pen blue for everything the family does, on a bright white page under a deep midnight-blue left panel, with people in every colour but blue and Vera alone in phosphor green.

**What changed**
- **The blue (#1F37E6):** links, the one primary button, "you are here", today's stamp and its ring on the calendar, and a ticked box all use it. Today and ticks were green before. Green now means only Vera and "done", and red still means only late.
- **The panel:** midnight blue, #0E1550 by day and #131A56 at night. The phone's top bar matches it.
- **The page:** bright white with crisp blue-black ink by day, and a blue-black page at night.
- **The people:** Sam is cerulean, Alex teal, Maya violet and Theo cinnamon. The other four slots are ochre, aubergine, sage and slate. By day the colours alternate dark and mid-tone, so neighbours also differ in lightness. Maya's pink is gone.
- **Vera's glass and phosphor:** unchanged and at today's strength in both themes.
- **Markup:** colour only, except one tweak. On Maya's own pages, her opening-line links stay ink with her violet underline, so her violet isn't set against the blue.

**Checks**
- **Contrast:** a new script (`_kit/palette-check.py`) reads the tokens from `style.css` and checks 230 pairs across both themes. All pass: text meets AA and controls, stripes and plates meet 3:1. The weakest avatar letter is 4.7:1.
- **Colour-blind:** simulated for protanopia, deuteranopia and tritanopia. The closest pair anywhere is 9.8 (the sage and ochre stripes by day, under protanopia). Among the family's four, the closest is Sam and Alex at 9.9 under tritanopia.
- **Renders:** I rendered every page, light and dark, desktop and phone (100 shots), with no font or overflow warnings, and looked through them.

**Delivered**
- `palette.html` shows the six colours and their jobs, the blue on the real buttons and tabs, the eight people as avatars and stripes, each person seen through the three colour-blind simulations, the signals, the panel beside Vera's glass, and every token. A second script (`_kit/make-palette.py`) rebuilds it from the tokens.
- `PALETTE.md` is under 350 words.
- `STANDARD.md`'s colour section, contrast table and night-theme notes are updated.

**Unfinished, or for the family to judge**
- **New people's colours:** the family hasn't seen them yet. Theo especially goes from orange to a dark cinnamon by day, which is orange again at night.
- **Theo and red:** cinnamon is the person nearest to late red under the simulations (7.2). Late items always also say "days late".
- **Two blues at night:** buttons and today use a #4A5CFF fill, while links and focus use a lighter periwinkle (#9AA6FF).
- **Panel and glass:** they are close in brightness (1.1:1). Hue, Vera's rounded corners and her phosphor ring keep them apart.
- **A kid's colour on the panel:** where it edges the panel and the phone's top bar, I treated it as decoration and didn't hold it to 3:1. It drops to 1.5:1 at night. The inverted white plate still shows where you are.
- **Type page wording:** `type.html` still says "navy panel". That's copy rather than colour, so I left it.
