Stage 10 is done. HANDOFF.md and STYLE-draft.md are written, and the stylesheet is rebuilt so that adding a theme means adding one file. Every page still looks the same: I rendered all 57 again (228 screenshots, no warnings, no inline style or script). The two test themes are in `shots/themes/`.

**HANDOFF.md**
- **Page map:** every mockup is matched to its real template, route and view. Two names swap: the mockup's `plans.html` is the real month view, and `plans-list.html` is the real `/plans`. It also lists 17 things the app can't produce yet, each with the smallest server change: a colour slot per person, the health pill, the nav counts, who a plan is for, and others.
- **Components:** each component in STANDARD.md is matched to a Jinja macro, changed or new.
- **Stylesheet:** how the new one replaces the old, the fonts and brand files, and the `<head>` lines.
- **Rules kept:**
  - The content security policy, everything working with scripts off, the measured accessibility numbers, kids seeing no costs, and presents hidden.
  - The hooks the new markup must keep for `ask.js`, `dictate.js` and `wishes.js`. `menu.js` is retired, because the drop-down menu is gone.
- **Words:** every wording change, for `views.py` and the templates.
- **Order of work:** thirteen pull requests, each leaving the app working, with what to test after each.
- **Tests:** the markup the current tests probably check that will change. The test suite isn't in this folder, so this list is inferred rather than taken from the tests.

**STYLE-draft.md** is the new `docs/STYLE.md`, in the voice and structure of the current one, with a Themes section added.

**Built for themes**
- **Two layers:**
  - `style.css` now holds only what every theme shares: type, spacing, sizes, and Vera's glass and phosphor.
  - Every colour lives in `themes/kitchen-table.css`.
  - An audit found and replaced every colour written outside the tokens, including the white avatar letters and the colours inside the FamilyDB logo's markup.
- **How a theme applies:** each page carries `data-theme` and a light/dark/auto mode on `<html>`, and links one theme file. I recommend one file per theme over one shared file; HANDOFF §8 says why. Section 8 also has the full list of tokens a theme must set, what stays the same in every theme, and step-by-step instructions for adding one.
- **Proof:** I ported Rail yellow and Midnight by copying their colours into the new token names, then rendered Home, Plans and a kid's Home in each, light and dark. Five things broke, and each was fixed in the system rather than in the themes:
  - the sidebar assumed it would always be light;
  - its links couldn't be read on a dark panel;
  - avatar letters were always white;
  - the tab bar's shadow was a fixed brown;
  - the theme previews held their own copies of each theme's colours.
- **Checks as a test:** `_kit/theme-check.py` checks every theme file for contrast, for the eight people and late red staying distinct to colour-blind eyes, and for phosphor green kept for Vera. It also writes a palette sheet per theme into `palette/`.
  - **Midnight** passes everything.
  - **Rail** fails at night: its late red is too close to three of its people's colours for colour-blind eyes. That's a flaw in Rail's colours, which is what the test is there to catch. Because of it, the checker exits with a failure in this folder until Rail is fixed or left out.
  - **Kitchen Table** falls short in three places, recorded as known exceptions for the family to decide on.

**Also fixed:**
- The wordmark's cursor never blinked because of a typo; it now blinks twice and stays lit.
- The kid's Home still showed "Thinking about it" on a wish, which the real app doesn't have; it now shows "No answer yet".
- The theme picker now lists only the three installed themes. Enamel and Ink had no files and are gone.

**Open questions for the family** (HANDOFF §9):
1. Kitchen Table's people colours fail the colour-blind check. Theo's ochre and slot 7's olive look the same to protanopes, and late red sits next to Theo's ochre for deuteranopes. Retune slots 4, 5 and 7, or accept the recorded exception?
2. Ship Midnight as it is, fix Rail's night colours first, or design themes properly later?
3. The design shows Status only to admins, but the app shows it to parents too. Which should it be?
4. Should a present name exactly whom it's hidden from, or keep "hidden from the kids"? Naming one person needs a new column.
5. Should a parent who isn't an admin see the friendly "for grown-ups" page, or the plain refusal?
6. Should to-dos get their own Edit page, or keep editing in a fold on the row?
7. Is "Set by Alex" on a kid's to-do worth recording who set each to-do from now on?
8. Keep setup's word "installer", or change it?

Two slips outside the folder: shell commands left `/setup-dump.txt` (a copy of the setup templates, from stage 9) and an empty `/s10_restructure.py` at the filesystem root. Deleting files there needs your approval, so they're still there: `rm /setup-dump.txt /s10_restructure.py` removes both.

This reply is also saved as `reply-stage10.md`.
