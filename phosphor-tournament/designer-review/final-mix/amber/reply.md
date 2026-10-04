I've finished **Amber Terminal**: the new palette in light and dark, `palette.html`, `PALETTE.md`, and the colour section of `STANDARD.md` rewritten. All 25 pages are re-rendered at desktop and phone width in both themes (100 shots), with no font failures or overflow.

**The idea:** a clean light page, navy-black ink and a near-black navy panel, with amber phosphor lighting the next thing you act on, like an old amber terminal, while Vera keeps the green one.

**How it works:**
- **Amber is always lit on navy.** It appears as amber letters on a navy chip (today's date, "Tomorrow", the Leave by label, the phone's current tab), as an amber plate (you are here), or as the primary button (navy with an amber label by day, an amber plate at night).
- **Setup and warnings are copper** (#7A3510), always printed on a paper tint with ⚠, never lit. That's how amber and copper stay apart. By day they're 48 ΔE apart, and at night they stay at least 8 apart under every colour-blind simulation.
- **The eight people:** cobalt (Sam), violet (Alex), teal (Maya, replacing the pink), olive (Theo), then plum, sky, walnut and petrol for the unused slots. Each avatar letter is white or ink, whichever passes AA; the weakest is Maya's at 4.7:1.
- **Colour-blind check:** the closest pair of avatars is about 11 ΔE apart. The closest route stripes are 8.2 apart by day (teal and plum) and 7.9 at night (cobalt and violet), both under deuteranopia.
- **Contrast:** all 113 pairs pass in both themes (AA for text, 3:1 for controls and stripes).
- **Vera's glass and phosphor** are unchanged and at the same strength.

**Not perfect:**
- Late red and copper are only 3.0 apart for people with protanopia. Late always says "days late" and setup always has ⚠, so colour isn't the only cue.
- Theo's olive stripe at night is 3.5 from Vera's green for protanopia.
- By day the panel and Vera's glass are both near-black. Her green rim and round corners keep them apart.
- On the night panel the red late plate is 3.0:1 against the navy, though its text is 5.3:1.

**Unfinished:** nothing that blocks this. Two judgement calls you may want to look at:
- To give the amber date its navy backing, the greeting's date and the Leave by label each got 1–2 px of padding. That's the only layout change.
- The dark sign-in page's "Who's writing" box uses the primary button, so its Send is amber, not Vera's green.

**Other changes:**
- In `style.css`, avatars now take a per-person letter colour (`--pN-on`), which needed small selector edits.
- There was no earlier palette-check script in `_kit/`, so I wrote my own. `python3 _kit/palette-check.py` measures every pair and fails if a floor isn't met. `python3 _kit/palette-sheet.py` rebuilds `palette.html` from the tokens; rerun it whenever a colour changes.

Files are in `dir-c-amber`:
- `style.css`
- `palette.html`
- `PALETTE.md`
- `STANDARD.md`
- `_kit/palette-check.py`
- `_kit/palette-sheet.py`
- `_kit/colourlib.py`
- `shots/`
