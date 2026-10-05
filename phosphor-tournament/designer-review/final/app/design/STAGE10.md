# Stage 10: ready to build

Prepare the design to be built into the real app (the engineers will work in `src/familydb/web/`;
you work only here). Write `HANDOFF.md` (as long as it needs, plainly written), covering:

1. **Page map:** every mockup → its real template, route and the view that feeds it; which real
   templates are replaced, merged or new; anything in the mockups the app can't produce today
   (data or a server class it doesn't emit, such as a person's colour slot or a kid's body class),
   each with the smallest server change that would provide it.
2. **Components:** each component in STANDARD.md → the Jinja macro in `_ui.html` / `_ask.html` /
   `_settings.html` it becomes or replaces, with its parameters; new macros to add.
3. **Stylesheet:** how `style.css` here replaces `static/style.css`: tokens, sections, what's dead in
   the current one; fonts and brand files to add to `static/`, with their preload lines.
4. **Rules kept:** the content security policy (no inline style or script), scripting off, the
   existing scripts (`ask.js`, `menu.js`, `wishes.js`, `dictate.js`) and what each needs from the
   new markup; accessibility (the measured contrasts, targets, focus, forced colours); kids never
   seeing costs, models or workings; presents hidden.
5. **Words:** every wording change from the current `views.py`/templates, listed, for `views.py`.
6. **Order of work:** a sequence of small pull requests that keeps the app working after each
   (for example: tokens and fonts → shell → Home → …), each with what to test.
7. **Tests that will change:** markup the current tests pin (look for page text and classes the
   templates carry) that the new design changes.
8. **Open questions** for the family, if any remain.

Also write `STYLE-draft.md`: the new `docs/STYLE.md` for the app, in the voice and structure of the
current one (`app-reference/STYLE.md`), describing this design as it will stand once built.

Reply with a summary and the open questions.

## And: built for themes

The family will add **themes** (other colour schemes for the same design; `theme-sources/` has four
explored palettes as examples). They won't be designed now, but the build must make adding one a
matter of adding a file. Make that true here, and add a **"Themes"** section to `HANDOFF.md`:

1. **Two layers of tokens in `style.css`.** Components use only *semantic* tokens (page, card, ink,
   rules, the action colour, today, late, set up, done, focus, the eight people with their soft,
   ink and mark variants, Vera's glass and phosphor…). A theme is nothing but a set of values for
   those tokens, light and dark. Audit `style.css`: no literal colour outside the token blocks
   (list and fix any you find), no component reaching for a raw palette value.
2. **The theme contract:** the full list of tokens a theme must define; which tokens are fixed
   across every theme and why (Vera's glass and phosphor, and the meaning of red, are the family's
   decisions); what a theme may and may not change (colour only: never layout, type or wording);
   the floors every theme must pass (AA text, 3:1 controls, avatar letters, the colour-blind
   separation of the eight people, red never confused with anything, Vera's green never used for
   anything else).
3. **How a theme is applied without breaking the content security policy:** the server sets
   attributes on `<html>` (for example `data-theme="kitchen-table"` and a mode of light, dark or
   auto) from the signed-in person's choice or the family's; each theme is its own stylesheet
   (`static/themes/<name>.css`, loaded by a `<link>`, or a block keyed on the attribute: weigh the
   two and recommend one). No inline style, no script needed. Auto follows
   `prefers-color-scheme`; light and dark override it. The `theme-color` meta tag and the web
   manifest follow the theme.
4. **What the app must store:** a family default (one line in `store.settings.BEHAVIOUR` and
   `web/fields.py`), a per-person choice (a members column: say what migration), and the
   per-person light/dark choice; who may change what (every person their own; an admin the
   family's).
5. **Checks as tests:** the designers' contrast and colour-blind scripts (`theme-sources/` and your
   own `_kit/`) turned into a test that runs over every theme file, so a theme that fails a floor
   can't be merged; and the palette sheet (`palette.html`, as the other designers made) as a
   generated page per theme for the family to look at.
6. **Prove it:** port two of the explored palettes as theme files *only to test the contract*
   (Rail yellow and Midnight: one light-first, one dark-first), by moving their values into the new
   token names, not redesigning them. Render Home, Plans and the kid's Home in each, light and dark
   (`shots/themes/`). Anything that breaks (a hard-coded colour, a component that assumed the paper
   was light) is a fix to the system, listed in HANDOFF.md.
7. **Adding a theme, step by step,** as the engineers and the family will do it.
