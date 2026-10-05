# Stage 14: the last answers

The family answered the five questions left in HANDOFF §9.

1. **"Afterglow is only one theme, not a day or night."** Afterglow is a single, fixed look: no
   day version and no night version, one appearance whatever the device or the mode says (as the
   built Phosphor look is dark only: `has_day` false in `looks.py`). Remove Afterglow's day: its
   `[data-theme="afterglow"]` block gives one value per token (no `light-dark()` pairs, or both
   halves the same), the Look page shows Afterglow with a single sample and without the day /
   night choice applying to it (say how the page explains that, in the built page's way for
   Phosphor), and `shots/afterglow/` keeps one set (move `night/` up, delete `day/`). The palette
   sheet shows one column.
2. **"Phosphor is a design system; Afterglow is one derivative of it."** So no renaming: Phosphor
   is the name of the design language (the green-screen family the app was first drawn in),
   Afterglow is one look derived from it, and Kitchen Table is the layout and default look they
   sit on. Rewrite HANDOFF §8.8 and STYLE-draft accordingly: Afterglow keeps its name; the built
   Phosphor look stays on the Look page as it is (it recolours Kitchen Table fine, as stage 11's
   shots show); describe Phosphor as the language Afterglow (and the Phosphor look) come from.
3. **The rest is the designer's call.** Decide each, say the decision and its one-line reason in
   HANDOFF, and make the mockups match:
   - a parent who isn't an admin opening Settings: the friendly "for grown-ups" page or the plain
     refusal;
   - Afterglow's pixel face: titles and wordmark only, more, or none;
   - the motions: keep, drop or bring back (glyphs falling, the 404 powering on, the radar sweep).
   Then empty §9: nothing is left for the family.

Re-render what changes, look, fix. Reply briefly with what changed and the three decisions.
