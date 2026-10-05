**Dusk.** The evening sky when the family gets home: a deep indigo-violet sky for the panel, a dusk-grey page, apricot (the last light) on whatever you do next, the family in sunset colours, and Vera's window the one thing lit green.

- **Panel:** #251754, deepening to violet #3B1A5E at its foot. The phone's top bar uses the same colours.
- **Page:** dusk-grey #F4F0EE with indigo-black ink. At night the page is deep indigo #110F19.
- **Apricot (#FEA660):** today's stamp, the Tomorrow stamp, Leave by's rule, the one primary button (an apricot plate with an ink edge by day), the edge of "you are here", and link underlines. Today used to be green. Now green belongs only to Vera and to done.
- **Red:** late, and nothing else. It's a cool crimson (#B51C2F), kept away from apricot. Setup is honey-coloured and always comes with ⚠.
- **People:** evening blue, sea, heather (Maya, no more pink), sun gold, sky, olive, dusk cloud and sandstone. Every avatar has the same indigo letter.
- **Phosphor:** Vera's glass, Send, the cursor, the ready pill and the mark are unchanged. They're easier to tell from a violet panel than they were from navy.

**Checks** (`python3 _kit/dusk-check.py`): all 202 contrast pairs pass in both themes. The weakest avatar letter is 5.1:1. Closest pairs under colour-blind simulation (ΔE2000):
- avatars: 9.1
- day stripes: 9.0
- night stripes: 8.0

That's in the same range as the earlier six. Ultramarine's 9.8 is still the best.

**Unfinished or weaker:**
- Some day stripes are very deep.
- For red-green colour-blind eyes, the sandstone and sun-gold stripes come close to late red. The word "late" always goes with the red.
- At night the panel is only 1.3:1 against the page. Its violet, not its lightness, sets it apart.
- The late plate on the panel is 2.4–2.9:1 against the violet. Its figure is 5.2:1 or more.
- Leave by's rule and link underlines are 3.1:1 by day, just over the line.
- Vera's own glass pane still has two hex values outside `:root`, as it did before this round. I didn't touch them.
- One copy change: type.html said "the navy panel" twice. It now says "the panel".
