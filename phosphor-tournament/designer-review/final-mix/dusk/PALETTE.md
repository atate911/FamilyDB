# Dusk

**The idea:** the evening sky when the family gets home: a deep indigo-violet sky for the panel, a dusk-grey page, apricot (the last light) on whatever you do next, the family in sunset colours, and Vera's window the one thing lit green.

| Token | Day | Night |
|---|---|---|
| page / ink | #F4F0EE / #171324 | #110F19 / #F4EFEB |
| panel, top → foot | #251754 → #3B1A5E | #2A1B5C → #401E66 |
| apricot: today, Tomorrow, primary, you are here | #FEA660 | #FDB171 |
| apricot rule / text | #D46B21 / #9C470D | #F7A059 / #FEBA7E |
| focus | #6239BA | #FFBA7D |
| late (only red) / setup ⚠ | #B51C2F / #79520A | #FB7475 / #EEC474 |

| Person | Avatar | Stripe day / night |
|---|---|---|
| p1 Sam, evening blue | #5E84E3 | #5166A1 / #A0BDFE |
| p2 Alex, sea | #04A4A3 | #034D4A / #9BE0D9 |
| p3 Maya, heather | #C29CF5 | #513367 / #A589CB |
| p4 Theo, sun gold | #FBCF3E | #7F5D03 / #F9DA4B |
| p5 sky | #B7E1FE | #0E8CB8 / #C7E6FE |
| p6 olive | #8A9527 | #454601 / #819811 |
| p7 dusk cloud | #AAB0C8 | #4E3A9E / #6D73DA |
| p8 sandstone | #BC9E85 | #563B2C / #B0917F |

Done, Vera's glass and phosphor are unchanged. Every avatar takes the same indigo letter.

**Checks** (`python3 _kit/dusk-check.py`): all 202 contrast pairs pass in both themes (text AA, edges and stripes 3:1); weakest avatar letter 5.1:1.

**Colour-blind** (Machado 2009, CIEDE2000), closest pair: avatars **9.1** (sea, dusk cloud; protanopia), day stripes **9.0** (evening blue, sky; deuteranopia), night stripes **8.0** (sea, sky; deuteranopia). The family's four: 9.6. Late red and apricot stay 10+ apart under every simulation.

**Where it is weaker**
- Day stripes are deep; hue separates them more than lightness.
- Sandstone's and Theo's stripes near late red for red-green colour-blind eyes (2.5–4). Late always says "days late".
- At night the panel is 1.3:1 against the page; Vera's glass is 1.2–1.3:1 against the panel. Hue, round corners and the phosphor ring separate them.
- The late plate on violet is 2.4–2.9:1 (its figure 5.2+).
- Leave by's rule and link underlines are 3.1:1 by day.
- The setup panel is warm sand beside apricot; ⚠ and words carry it.
