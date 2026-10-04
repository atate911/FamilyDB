**Name:** Tomato Table

**Idea:** It's the same kitchen table in late summer: warm cream and brown ink, one ripe tomato for everything the family does, and Vera as its green sprout, a small lit screen on warm charcoal glass.

All 24 pages are rendered light and dark, at desktop and phone width (96 shots in `shots/`). No page is wider than the screen, every font loads, and I looked at the key pages and fixed what I found. `DIRECTION.md` is 399 words, and STANDARD's colour, type, contrast and brand sections are updated.

**How the brief's three questions are answered:**
- **The tomato:** it is only ever a fill or a line. That covers primary buttons, Send, today's date tile and calendar circle, the current nav row and tab, and link underlines. It replaces the green as the family's accent. Link words stay ink, so tomato never colours text.
- **Late:** red text now means only late or broken. Late is a deep brick (#8E2A16), always written out ("6 days late"), with a filled clock in front that nothing else uses, plus the brick stripe on the row. At night it is coral text.
- **Vera:** she stays undrawn, and the reference's little tomato is gone. Her screen keeps its phosphor green on charcoal glass, now made warmer. The brand mark's square, the favicons and the home-screen icons are warmed to match; I re-rendered the PNGs from the SVGs.
- **Dark mode:** charcoal-brown instead of green-black, cream text, and a tomato edge on the Ask card.

The look also changed: brown-black text, the softer Fraunces letterforms on card titles as well as page titles, slightly rounder corners, and a warm card shadow. Person colours, page content and structure are unchanged. The only markup change is the mark's square colour in the inline SVGs. There is still no inline `style=""` and no script.

**Contrast:** I recalculated every pair in STANDARD §7 for both themes, and all pass. Tomato passes with little to spare: white on tomato is 4.8:1, and at night tomato on a card is 3.4:1 against the 3:1 minimum for controls.

**Unfinished or worth knowing:**
- **Two reds remain.** A tomato button next to a late row still shows two reds, even though they differ in darkness, shape and the clock. Kitchen Table's green against red didn't have this problem. It's the main weakness.
- **Theo's orange is close to the tomato.** The colour difference (ΔE) is 23. His initial always shows, but I didn't change his colour because the brief keeps people's colours.
- **`type.html` has broken images.** Its six reference images in `type/` were already missing from this folder, so its shots show them as broken. I didn't recreate them.
- **I didn't check every shot.** I looked closely at Home, To do, Plans, Chat, Ideas, Status, sign-in, 404, the kid's Home and the states sheet. The other pages I only checked through the renderer's report (fonts loaded, no sideways scrolling).
