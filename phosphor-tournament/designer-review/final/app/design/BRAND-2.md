# Stage 6: keep the brand, lose its costs

Four fresh blind judges compared your branded version with the plain final from before stage 5
(two each way). **All four said the branded one has clearly the stronger identity**: "a family would
recognise it as their app", "the little green screen app", while the plain one has "no identity to
speak of" and its Vera looks like a fifth family member. **But three of the four would build the
plain one**, because the brand cost something in use, in three specific places. The style lens
(8/10) and the accessibility lens (7/10) said the same. Their reviews are in `reviews-brand/`
(a comment at the top of each blind review says which letter is yours).

This stage keeps every brand element and removes the costs. Do the items in order, render
everything light and dark, desktop and phone, look, fix, render again. Update `STANDARD.md`,
`CHANGES.md` and `type.html`.

## Keep (cost nothing, or add value)

The mark and the wordmark; the "Vera is ready" pill; the radar on Ideas; Settings' key that says
the monitor is the app and the pane is Vera; the brand moments (sign-in, empty day, grown-ups, 404).

## Fix

1. **Vera's sign must read as her at 24 to 32 px, light and dark** (all four judges and both lenses:
   "a dark smudge", "a broken thumbnail"). Crisper, fewer and brighter glyphs, a lit rim, one
   signature element that is the same at every size; at small sizes simplify (a few large lit
   blocks, or a lit cursor in the pane) rather than shrink the big one. Its rounded-square shape
   must stay distinct from the family's round avatars. Check it at real size in the shots.
2. **Mono only on the glass.** The status pill, the radar's ring labels and anything inside a pane
   may be mono. Vera's receipts, her message times and everything else the family reads go back to
   Atkinson (three judges: harder for a 9-year-old, wraps badly on the phone).
3. **Dark mode keeps its hierarchy** (all four judges, style lens). The Ask Vera card keeps a
   distinct deep-green glass fill with a visible edge on its box; the family's primary buttons stay
   green as by day, not cream; no glow on Vera's chat bubbles. Glow stays on the panes and the pill.
4. **The radar earns its place.** Spread the inner rings (a non-linear scale) so the five near
   ideas separate; on desktop let the cards start right under the filters, with the radar beside
   them or after the first row; legible ring labels.
5. **The calendar says who a plan is for without colour alone.** A plan for several people does not
   take the first person's colour: make it neutral with their small avatars (or split it), give
   single-person events their initial too, and add a one-line key on Plans.
6. **Money and clock times look the same everywhere.** "$0.00 of your $2.ØØ" mixes two zeros in one
   figure. Pick one figure style for money and clock times wherever they appear, and show the
   choice in `type.html`. If you try a body digit with an open zero, it must read as part of Atkinson.
7. **Accessibility** (access lens): visually hidden text with the `.sr` clip pattern, never
   `display:none` next to an `aria-hidden` stand-in (the phone starters and the phone Edit links
   lose their names); a visible focus ring on glass; the wordmark cursor and the pill blink for a
   few seconds and then stay lit (no blinking longer than five seconds); key sizes in rem; Status
   figures stack at 320 px; firmer edges on icon buttons and on the disabled arrow.
8. **Small things:** one face for idea titles across pages; Maya's slot colour moved away from the
   "late" red; "Surprise · hidden from Maya" short enough not to wrap in a narrow tile; the kid's
   empty chat should not have two equal greens; the phone "Ready" pill centred with the logo.

Then stop and reply with what changed and anything you declined.
