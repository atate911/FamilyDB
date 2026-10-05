# Midnight

**The idea:** FamilyDB as a screen in a dark kitchen at night, with a blue-black page, a darker panel, soft-white ink, each person's colour lit like a window, and Vera's green glass the one green light among them.

Night was designed first and is the default. Day is the same kitchen with the lights on, and its panel stays midnight.

**Done:**
- Every page re-rendered in both themes: `shots/` (day) and `shots/dark/` (night).
- `palette.html` shows the idea as a night and day scene side by side. It also shows the eight people night beside day, the people through each colour-blind simulation, the signals, and every token.
- `PALETTE.md` written, and `STANDARD.md`'s colour section updated.

**Checks:**
- All 224 contrast pairs pass. The weakest avatar letter is 6.4:1.
- Colour-blind check, closest pairs: avatars 8.4 (moon blue and lagoon, tritanopia); day stripes 7.4 (apricot and ochre, tritanopia).

**Unfinished:**
- Nothing yet lets a family pick a theme, so "dark by default" means dark unless the device asks for light. A Settings choice that writes `data-theme` on `<html>` would make night the default on every device. The CSS already supports it.
- The night panel is only 1.07:1 against the page. Hue and a hairline edge carry it.
- Ochre and apricot sit close to set-up amber for colour-blind eyes. Setup always shows ⚠ and words.
