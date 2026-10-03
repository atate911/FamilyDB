# The finale: four designs, every page, and a draft standard

This folder is where the tournament stops for the owner. Nothing under `src/` is touched.

## What is here

| | |
|---|---|
| `PHOSPHOR_STANDARD_DRAFT.md` | The draft of the Phosphor Interface standard: the signature, the light, colour, line language, type, page by page, components, floors, a kit of the best element per slot, and three options with a recommendation. |
| `championship.md` | Round 21: eight designs, eight lenses, the table, and what each lens said of the four finalists. |
| `four-homes-desktop.jpg`, `four-todo-desktop.jpg`, `four-homes-phone.jpg` | The four finalists side by side (Home, To do, and the phone's Home). Good first look. |
| `mockups/<id>/` | Every page of each finalist, desktop (1280 wide) and phone (390 wide at 1.5x), as full-page JPEGs in `desktop/` and `phone/`, with `sheet-desktop.jpg` and `sheet-phone.jpg` for an overview. 34 pages each, 4 designs. |
| `designs/<id>/` | Each finalist's `palette.json`, its markup and stylesheet (`variant/`) and the themed `style.css`, so it can be served and re-rendered with the harness. |

The ids: `r20-mut-3` Grid Console, Keyed; `r20-mut-1` Desk Terminal, Even Dock; `r19-mut-2` Track
Diagram, Rail Keys; `r20-mut-2` Lit Index, Ledger Rail.

## The four, in championship order

1. **Grid Console, Keyed** (7.84). Teal-black console, lit rails with keyed nodes, condensed heads
   with coloured numerals, latched pills, a green Add key. The consensus choice: top four on all
   eight lenses.
2. **Desk Terminal, Even Dock** (7.59). A glass column on every page, the question typed on the
   glass, a Contents plate, ledger rows. The best soul and usability scores.
3. **Track Diagram, Rail Keys** (7.48). Serif titles with counts, the rail from Vera's screen to
   the box, amber "was due" stamps. The best list and signal; a phone composer to fix.
4. **Lit Index, Ledger Rail** (7.40). A poster question with a lit MIND?, numbered index, a ledger
   To do. The strongest identity and type; the weakest line language.

Chosen for score and variety: they are four different families and the top four by score.

## Notes on reading the mockups

- The pages are rendered from the demo family's data (short names, no long titles, no empty or
  error states, no kid's view). They are what the panel saw, not a stress test.
- A phone page is a full-page capture. The tab bar is fixed, so on a tall page it can appear
  once in the middle of the picture; that is the capture, not the design.
- Only Home, Ideas, Chat, Status, Plans, To do and Settings were seen by the judges. The other
  pages (Family, Memory, Wishes, You, Setup, Sign in, 404, the settings sections) are shown so
  the owner can check them, and they are the first place a flaw is likely to be.
- Stills cannot show motion (breathing lamps, the afterglow, a screen switching on).

## What the owner decides

1. Which of the three options in section 13 of the draft, or none.
2. Whether the standard is one of the four whole, or a composite built from the kit of parts
   (more work and less simple; the owner's simplicity rule applies to each transplant).
3. What to do about the doubts in section 14, chiefly the unjudged pages and real data.
4. When to turn a choice into a change to `src/familydb/web/static/style.css` and the templates,
   with `docs/STYLE.md` and the tests that pin markup updated in the same change.

## How it was produced

`../harness-selection/` (`README.md`, `finale_setup.py`, `finale_render.js`, `finale_run.sh`,
`finale_pack.py` and the per-round files). Round 21 had no screen: the eight went straight to the
eight lenses. The finale's page renders were made with `finale_run.sh` against each finalist's own
server; the JPEGs by `finale_pack.py`.
