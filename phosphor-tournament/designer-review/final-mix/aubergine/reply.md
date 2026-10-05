**Aubergine & Brass**: a well-kept house. Warm stone walls (a grey, not cream), aubergine-black ink beside a deep aubergine panel, brushed brass on whatever you act on next, the family in jewel tones, and Vera's green glass as the one lit thing.

How it differs from the six earlier palettes: the panel is plum-black, not navy, and the ink is that same aubergine darkened to near black. Brass is a single thing you can point to: the "you are here" plate, the Tomorrow stamp, today's stamp, the rule beside Leave by, link underlines and the primary button. By day that button is an aubergine plate with brass lettering; at night it becomes a brass plate. Setup is copper and always carries ⚠, late is the only red, and done is green. Vera's glass, phosphor Send, glow, cursor and smiling-monitor mark are unchanged and at full strength. Their green-black stays clearly apart from the plum panel.

**The people:** sapphire (Sam), amethyst (Alex), peacock (Maya), topaz (Theo), then peridot, cerulean, tiger's eye and tanzanite. Maya's pink is gone. None of the eight is pink, red, Vera's green or gold.

**Checks:**
- **Contrast:** all 198 pairs pass in both themes, measured by script from the tokens. The weakest avatar letter is 4.7:1.
- **Colour-blind check:** the closest pair is 9.0 for avatars, 7.5 for day stripes and 7.4 for night stripes (CIEDE2000; about 5 is a clear difference). Among the family's four it never drops below 10.9.

**Unfinished, or weaker:**
- `DIRECTION.md` still describes round 6's navy panel; I only updated `STANDARD.md`, as the brief asked.
- Alex's night stripe is a pale amethyst. Its lightness is the only thing keeping it apart from sapphire and tanzanite for red-green colour-blind eyes.
- By day, copper and late red are about 4 apart for protanopes. The words ("days late") and ⚠ carry the difference.
- Today's brass stamp has only 1.8:1 against the page; its letters (7.9:1) carry it. Today's wash on the calendar is close to cream.

Every page was re-rendered light and dark, and fonts loaded with no overflow. I looked at the desktop and phone shots, fixed what they showed, and rendered again.

I added five scripts to `_kit/`: a contrast and colour-blind checker, the search that found the people's colours, the script that writes those colours into `style.css`, a sheet generator that builds `palette.html` from the tokens, and their shared colour maths. In `style.css`, apart from the tokens, I only added colour hooks: a letter colour per person, the brass "you are here" plate, and the date and Leave by in brass.

Files are in the folder:
- `PALETTE.md`
- `palette.html`
- `STANDARD.md` (colour section and §7 contrast table)
- `reply.md` (this reply, short form)
- `shots/` and `shots/dark/`
