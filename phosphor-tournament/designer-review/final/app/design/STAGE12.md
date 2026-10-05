# Stage 12: an Afterglow look for Kitchen Table

The family: **"Can we also make a theme that fits the final layout, but based on Afterglow
(scanlines)? I don't want to rewrite the whole interface just for the Afterglow theme, it should
just be a selectable theme over the actual interface that incorporates the visual feel of
Afterglow. I still like the phosphor as a concept, so perhaps it can just be a theme on top of
Kitchen Table."**

`afterglow-ref/` holds Afterglow as another designer made it in an earlier round (your Kitchen Table
restyled phosphor-first: green-black glass day and night, phosphor glow, scanlines, a pixel face
for titles, and a light version): its stylesheet, direction, brief and shots.

Make **Afterglow a look** for the Kitchen Table interface, in the mechanism you fitted in stage 11
(a `[data-theme="afterglow"]` block, chosen on the Look page like any other):

1. **Same interface.** No page, layout, markup or wording changes for it. If the feel needs
   something colour tokens can't carry (scanlines, glow, a lit edge, perhaps a terminal face for
   the biggest titles), add it to the theme contract as a small set of **effect tokens** every look
   defines (Kitchen Table and the other looks set them to "none" or their plain value), consumed
   once in `style.css`. Keep it few, documented and CSS-only: no images, no scripts, nothing inline.
2. **Scanlines and glow with care:** never over the words people read (on surfaces and the glass,
   not as a film over text), subtle enough that every contrast floor still passes with them on,
   switched off under `prefers-reduced-motion` if they move, under `forced-colors`, and for print.
   Vera's glass and phosphor must still read as hers: in a look that is all glass, decide how her
   things stay the one lit thing (brighter, lit edge, her sign), and say how.
3. **Type:** Atkinson Hyperlegible stays for everything read. A terminal or pixel face for the big
   titles is allowed only as an effect token, if it earns its place, self-hosted and small.
4. **Night and day:** Afterglow is night first. Give it a day version too (the earlier light
   version is a starting point), or make the case that it should be night only, as the built
   Phosphor look is.
5. **Its relation to Phosphor:** the app's current default look is Phosphor (dark only, the old
   design). Say whether Afterglow on Kitchen Table should become what "Phosphor" means once Kitchen
   Table ships (one name, one look), and what to name it.
6. **Check it everywhere:** render every page in Afterglow, night and day, desktop and phone
   (`shots/afterglow/`); look, fix, render again. Run the theme check on it. Add its palette sheet.
7. Update `HANDOFF.md` (the Themes section: effect tokens, Afterglow, what the built `themes.css`
   and `test_look.py` would need) and `STYLE-draft.md`.

Reply with what you made, how the effects work, and anything for the family to decide.

## And: keep some of the old motion, tastefully, in Kitchen Table itself

The family again: **"If we can keep some of the animations (like the little matrix-appearing icon)
but tastefully integrated into Kitchen Table, that would be nifty."**

The current app (the old Phosphor design) has a handful of small motions. They are described in
`afterglow-ref/current-app-motion.md` (from its STYLE.md: "Her screen" and "Small things"), with the
CSS in `current-app-motion-css.txt`, the full `current-app-style.css`, the `presence` macro in
`presence-macro.txt`, and its VT323 font if present. The "matrix-appearing icon" is **her
screen**: a small pane of unreadable glyphs that fall a row at a time while she is thinking, and
for a moment on Home as the page opens, then rest. The others: things light up at once and fade
over a second (afterglow), cursors blink for a few seconds then stay lit, a link's landing place
lights and fades, the 404 screen powers on, live dots breathe.

Bring the best of these into **Kitchen Table itself** (every look, not only Afterglow), adapted to
its shapes:

- **Vera's sign (`.vs`) comes alive the same way:** its rows fill in as if typed, or its glyphs fall
  a row at a time, once as Home opens and continuously only while she is writing back (the health
  pill's "writing back", the chat's waiting line); still otherwise. It must stay small, never
  readable as words, never a face.
- Pick the few others that suit a calm kitchen-table page (the afterglow fade on what you just
  did, the landing glow, cursors that rest) and leave the rest. Nothing moves for more than a
  moment where people read, nothing loops except while she is working, everything stops under
  `prefers-reduced-motion`, and everything is CSS (the app's scripts don't animate).
- In the Afterglow look the same motions may be a little brighter (an effect token), never longer.
- Since screenshots can't show motion, add `motion.html`: one page that shows each motion in place
  with a line on when it plays (and render it), and list them in STANDARD.md and STYLE-draft.md
  under "Small things".
