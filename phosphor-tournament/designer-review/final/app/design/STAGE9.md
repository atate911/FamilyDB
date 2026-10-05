# Stage 9: the whole app, part 2: settings and setting up

Continue the same way with the admin's pages, again from `app-reference/` (`settings.html`,
`settings_section.html`, `_settings.html`, `templates/settings/*.html`, `fields.py` for every group
and box with its help, `setup*.html`, `templates/setup/*.html`, `_company_cards.html`,
`_key_steps.html`, `setup.py`, `status.py`):

- `settings.html`: check your existing one against the real `/settings` (a card per section saying
  how it stands).
- One mockup per settings section, each with its real groups, fields, help and save:
  `settings-general.html`, `settings-model.html` (the company-and-key form, key steps, company
  cards, levels), `settings-connections.html` (Telegram, Google Calendar), `settings-lookups.html`,
  `settings-messages.html` (the automatic messages list), `settings-personality.html` (her name,
  character rewrite, notes, lines, about the family), `settings-security.html` (shared password,
  sign everyone out, reveal a key), `settings-spending.html`, `settings-history.html`.
- Setting up a new install: `setup.html` (the overview), one page per step (`setup-you.html`,
  `setup-password.html`, `setup-model.html`, `setup-home.html`, `setup-telegram.html`,
  `setup-family.html`, `setup-calendar.html`), `setup-done.html` and `setup-told.html`.
- Fold groups and long forms the way the real pages do (`<details>`), no scripts.

Render every page light and dark, look, fix, render again. Add to CHANGES.md (stage 9) and
STANDARD.md. Reply with what you made and anything unfinished.

## Also: choosing a theme

The family is going to add **themes**: other colour schemes for the same design, like the palettes
explored in other rounds (four of them, with their stylesheets and notes, are in `theme-sources/`
for reference: Rail yellow, Enamel, Midnight (dark first) and Ink). Kitchen Table stays the default
theme. You don't design the themes; design **where and how they are chosen**:

- On the settings pages (General, or wherever fits best): the family's theme, shown as a row of
  real previews (each a small swatch card or a thumbnail of Home in that theme), with the current
  one marked, and "Light / Dark / Match this device" for the family's default appearance.
- On Your password's page (`/you`, which becomes "You" or "Your account"): each person's own
  choice, "Use the family's theme" or a theme of their own, and their own Light / Dark / Match
  device. Kids get this too (it changes nothing but how their own screen looks).
- Everything works with scripting off: a plain form with radio buttons and Save, reloading in the
  new theme.
- Mock it with Kitchen Table and three or four named placeholder themes (their swatches from
  `theme-sources/` are fine).
