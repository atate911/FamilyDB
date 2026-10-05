# Stage 11: themes are already in the app — fit the handoff to them

While you worked, the family's engineers built theme support into the **current** app (still the
old Phosphor design). `app-reference/built-looks/` has what landed: the new `style.css` (every
colour a token, in palette-sheet names), `themes.css` (one `[data-theme="…"]` block per look, each
token written `light-dark(day, night)`), `looks.py` (the looks, a per-browser cookie `fdb_look`,
modes auto / light / dark set as `data-mode` on `<html>`), `look.html` (the Look page at `/look`,
for anybody signed in, kids included), `base.html`, the tests (`test_look.py`) and the updated
`STYLE.md` ("Looks"). `COMMITS.txt` has the two commit summaries.

That mechanism is now the app's. Your stage-10 theme plan (one file per theme, a family default and
a per-person choice stored on the server) differs from it. Fit the design and the handoff to what
was built, rather than the other way round:

1. **Token names.** Compare your `themes/kitchen-table.css` tokens with the built ones. Where the
   built names cover the same role, adopt them; where Kitchen Table needs roles the built set
   lacks (the eight people and their variants, Vera's glass, today, set up…), say exactly which to
   add, so one contract serves every look. Change your files to match and re-render to prove
   nothing moved (`shots/` should not change).
2. **Kitchen Table as a look.** Write it as it would sit in `themes.css`: one
   `[data-theme="kitchen-table"]` block with `light-dark()` values, plus whatever `style.css`
   must stop assuming (the built default, Phosphor, is dark only). Say whether Kitchen Table
   should replace Phosphor as the default when the new design ships, and what happens to the
   existing looks (Midnight, Home Computer, Ink, Enamel, Rail yellow, Fjord) under the Kitchen
   Table layout: they recolour any layout, so check they still read on Kitchen Table's shapes
   (render Home in two of them from the built `themes.css`, `shots/looks/`).
3. **The Look page.** Your stage-9 pickers (Settings › General for the family, "You" for each
   person) were drawn for a server-stored choice. Redraw the chooser as the built Look page in
   Kitchen Table (`look.html`): per browser, kids included. Keep the family default and the
   per-person choice only as a clearly marked later step (the built STYLE.md lists them as not
   yet built), with what each would need.
4. **HANDOFF.md:** rewrite section 8 (Themes) around the built mechanism; update the page map
   (`/look`), the order of work and the tests list (`test_look.py` holds every look to the token
   set and the contrast floors: say what Kitchen Table changes there). Update `STYLE-draft.md`'s
   Themes section to match the built "Looks" section's facts.

Re-render, look, fix. Reply with what changed and anything the family should decide.
