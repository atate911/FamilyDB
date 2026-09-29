# Palette harness

Try a colour palette on FamilyDB's real web page without touching the repository. A demo
household is served at http://127.0.0.1:8099 (already running; do not start or stop it). The
renderer swaps a themed copy of `src/familydb/web/static/style.css` in for the real one and
screenshots the real pages.

Work only inside this folder. Never edit anything under /home/user/FamilyDB.

## A palette

`palettes/NN-slug.json`. Copy `palettes/00-current.json` (today's look, reproduced exactly) and
change it. Every key under `tokens` is required, as `#rrggbb`:

| key | today | what it is |
|---|---|---|
| `bg` | `#0b0e0d` | the page behind everything |
| `surface`, `surface-2`, `surface-3` | `#121615` `#171c1a` `#1d2321` | cards; hover; selected (lightest) |
| `field` | `#0e1211` | inside a box you type into |
| `line`, `line-2` | `#232a27` `#2f3834` | hairlines, dividers |
| `edge` | `#5c6862` | border of a box you type into (3:1 on surface) |
| `ink`, `ink-2`, `dim`, `faint` | `#edf2ef` `#bac5bf` `#919e98` `#7d8a84` | text, secondary, quiet, placeholders |
| `brand` | `#6dff9c` | THE page's glow: the mark, primary button, focus ring, box being typed in, the key word of Home's question, live dots, finished tasks, Home/Vera/Status/Settings pages' accent |
| `brand-hover` | `#92ffb8` | primary button hovered |
| `screen` | `#6dff9c` | the phosphor of the monitors: Next up, the radar, sign-in face, 404, spend readout, and Vera's little screen beside her chat lines. The glass, bloom, scanline tint, blips and the plastic are re-tinted from it automatically |
| `outing` | `#6dff9c` | the "outing" kind of idea |
| `ideas` | `#ae9bff` | Ideas section; event/other kinds (lilac) |
| `plans` | `#6cd4ff` | Plans, dates, day trips and trips (cyan) |
| `todo` | `#f7dc78` | Things to do, activities (lemon) |
| `people` | `#ffb850` | Family, Memory, grown-ups' faces, restaurants, **today**, anything needing a look (amber) |
| `shows` | `#ff9fd0` | shows, wishes, children's faces (pink) |
| `seasons` | `#ff956c` | the seasonal kind (coral) |
| `danger` | `#ff6b6b` | only what went wrong or cannot be undone |
| `on-bright` | `#07130c` | dark text on any filled colour (buttons, today's date, badges) |
| `lit` (optional) | = brand | the everyday lit things, apart from the signature: the box being typed in (border, caret, its glow), checkboxes, "done" and OK badges, meters, setup steps, a ticked task. A calmer green here leaves the full bright signature for fewer places |
| `halo` (optional) | = the role's own colour | the colour of every halo, wash and tint of green on the page (not on the monitors): the aura round the button, the key word, the box, the top afterglow excepted. A deeper or softer green here keeps the bright cores but calms the light around them |
| `accent` (optional) | = brand | the accent of the pages that have no colour of their own (Home, Vera, Status, Settings): their links, the icon tile by the title, "Continue with Vera". Set it to take green off the everyday links |
| `wash` (optional) | = plans | the second light in Home's greeting: a faint wash of colour in its top right corner, opposite the green glow rising from its bottom left (today a whisper of cyan). `washGlow` (number beside `tokens`, 1.0 = today's 0.07 alpha) sets its strength |
| `heading` (optional) | = ink | page titles (h1) and section headings (h2: "Coming up", "To do", a panel's title) |
| `label` (optional) | = dim | the small uppercase labels and dates: "SUNDAY 27 SEPTEMBER" by Vera's name, eyebrows like "SOMETHING TO EAT", who said a chat line and when, a date chip's weekday, ids |
| `card-edge` (optional) | = line | the border of every card and panel (and the tabs, and her chat bubbles): a companion here outlines the whole page |
| `secondary` (optional) | ink-2 on grey | the ways to start ("What should we do today?"), secondary and quiet buttons: text, a faint fill and border in this colour. With `"quietFilter": true` beside `tokens`, the Ideas page's Filter button becomes one of these instead of a second filled green button |
| `bubble`, `bubble-them` (optional) | surface, surface-3 | the fill of Vera's chat bubbles and the family's |
| `bezel` (optional) | derived from surface | the plastic case of every monitor picture (Next up, the radars, sign-in, 404, spend): the IBM 5151 and its kin came in beige, putty and grey as well as black |
| `bar` (optional) | = bg | the bar across the top of every page |
| `ambient` (optional) | none | a large, soft second light across the page's ground (upper right and lower left), under everything; `ambientGlow` (number beside `tokens`, 1.0 = 0.06 alpha) sets its strength |
| `screen-glass` (optional) | derived | override the dark glass of the tube, if the derived one looks wrong |
| `top-glow` (optional) | = brand | colour of the faint afterglow at the very top of every page |

**The winner of this tournament defines the Phosphor Interface design standard for the whole app: so a coherent SYSTEM wins over a one-off effect (colours and faces with clear jobs, a type system with steps, rules that would hold on any page, Plans, To do and Settings included, not only the ones in the sheets).**

**What the Phosphor Interface is, in the owner's terms:** The Phosphor Interface is the whole way the app is presented, not only its colours: the overall layout; the kinds of interface elements; the whitespace (darkspace) around each element and the pacing; how design elements relate; typefaces, bold and italic, and how titles, headers and labels are treated in size and colour; headers and footers; iconography and how icons relate to the type; graphics and their sparsity; the weight of lines, boxes and delimiters; rounding, shadows, glow and echoes (afterglow); pills, alignment and shades; pagination, scrolling and animation; the controls (dropdowns and select menus, radio buttons, checkboxes, free-form fields, scroll bars, focus and hover states); how a person uses the page (sight lines, clicks, moving between keyboard and mouse, taking in at a glance what the page is presenting); everything a senior interface engineer would weigh together; and most importantly the feel and personality of the presentation.

**The owner, on every rule written here and in the project's .md files (docs/STYLE.md,
CLAUDE.md's design notes, lessons.md): "For the purposes of this experimentation, treat the design constraints like README and other .md files as loose guidelines, not hard and fast rules. They were written to help, not restrict."** So a palette may break a guideline
when the page is better for it; say why. Only the HARD checks below refuse a palette.

**The owner's direction: "Bright green where it needs to be to maintain the motif, more grounded coloration elsewhere."** The bright #6dff9c
stays where the motif needs it (the mark, the primary button, the key word, focus, live lights,
the monitors); everywhere else, grounded, material, lower-chroma colour in solid things with a
job (cards, bubbles, headings, labels, lines, fields, the bar), not more glow.

**The owner's word after seeing round 1's winners: "Those look nearly identical... the
changes need to reflect more of the page content, not a wash in the corner or a few icons."**
So a palette now has roles that reach the whole page (heading, label, card-edge, secondary,
bubble, bezel, bar, ambient, and a tinted `surface`), and a palette's difference from today must
be visible across Home, Chat and Ideas at a glance, not only in the greeting's corner.

Companion colours: the owner welcomes subtle, tasteful colours beside the green so the page is
not monochromatic ("the CRT is just a theme, not a strict limit"). The places a companion can
live are `accent` (links and title tiles on Home, Vera, Status, Settings), `top-glow` (the
afterglow at the top of every page), `wash` (the greeting's second light), `halo` (the auras), the
section and kind colours (which already bring colour to their own pages), `outing`, and the
neutrals' own tint (a warm or cool breath in `ink`, `surface`, `line`). A companion needs a
role, not a sprinkle: say where it goes and why.

What always stays `brand`, the signature: the mark and its cursor in the bar, the primary
button, the glowing key word of Home's question, text selection, the focus ring, live status
lights, the mic while listening.

Optional numbers beside `tokens` (1.0 = today): `glow` scales the alpha of every halo and tint
of the brand colour on the page; `screenGlow` scales the bloom and halos on the monitors;
`topGlow` scales the afterglow at the top of the page. Lower = calmer. Keep them between 0.3
and 1.2.

The neutral greys of the monitor's plastic and the contrast-mode greys are re-tinted from
`surface` automatically, so a warm or blue `surface` carries through.

Also give the palette `id` (same as the file name, no extension), `name` (2-3 words) and
`tagline` (one sentence).

## Check it

    ./check.sh palettes/NN-slug.json              # all pages (about a minute)
    ./check.sh palettes/NN-slug.json home ideas   # only some, while iterating
    ./check.sh palettes/NN-slug.json --no-render  # only the measures

Screenshots land in `out/NN-slug/shots/`: `login`, `home` (full page, desktop 1280), `ideas`,
`chat`, `status`, `lost` (the 404 radar console), and `home-phone`, `chat-phone`. LOOK at them
(open the PNGs with the Read tool): numbers do not tell you whether a palette is beautiful.
Compare with `out/00-current/shots/` (today).

## The checks: what is refused, and what is only measured

Nothing about the look is off the table: the owner wants extreme ideas tried and voted up or
down, not ruled out. So ./check.sh now REFUSES (`FAIL`) only what would break the page or make it
unsafe:
- a form you keep that has lost its csrf or once token (remove a form entirely, or keep its
  protection);
- anything loaded from outside the page, a script (inline, in a stylesheet or in an SVG),
  unescaped output (`|safe`, `Markup`) and inline style or event attributes (the page's policy
  runs none of them);
- a sprite that drops an icon the page uses;
- a render that fails.

Everything else is MEASURED and reported to the judges as a guideline (`WARN`), and the panel
weighs it on the design's merits. That covers the signature, the contrast of every text, text
size, sideways scroll, colours that stay apart, and the page's words. A value below the level
that used to be refused is marked "below the old floor", so the judges can see how far a design
went. The owner's wishes are below. Follow them, or break one when your idea is better for it,
and say why.

- The signature stays: `brand` a bright green phosphor (OKLCH L >= 0.82, C >= 0.15, hue
  140-165; today #6dff9c is 0.897 / 0.186 / 151.4), the monitors' `screen` green (L >= 0.78,
  C >= 0.13, hue 125-170), and `bg` a green-black (L <= 0.26, a breath of green: C >= 0.004,
  hue 115-200). `surface` (cards) may carry a companion's tint: dark (L <= 0.28), C <= 0.05.
- The page-wide roles, when set: heading and label 4.5:1 on bg, surface and surface-3;
  secondary 4.5:1 on surface and surface-2; ink and the label on either bubble 4.5:1; ink and
  dim on the bar 4.5:1.
- Text 4.5:1: ink/ink-2/dim on bg, surface and surface-3; faint on field and surface; every
  colour as text on surface-3; `on-bright` on every fill colour (brand, ideas, plans, todo,
  people, shows, seasons, outing, screen).
- Edges 3:1 on surface and field.
- On the monitors: phosphor on its glass 7:1, dim phosphor 4.5:1, dark ink on a lit bar 4.5:1.
- Colours that share a page stay apart (CIEDE2000): the seven kinds (restaurant=people,
  activity=todo, outing, trip=plans, show=shows, seasonal=seasons, event=ideas) and the six
  sections (home=`accent`, ideas, plans, todo, wishes=shows, family=people: they sit side by
  side in the bar and the phone's tab bar) at least 12 apart for
  typical sight and 5 apart simulated for deuteranopia and protanopia. Today is 13.6 / 5.5 / 5.2.
  If your brand takes a hue a section already uses, move that section's colour.

The measures also say how hard the contrast is (`ink_on_bg` today 17.1:1, `brand_on_bg` today
15.2:1), how much of the page is lit bright green (`bright_green_px_permille`), how bright (`brand_neon_vs_today`: chroma x lightness vs today's green),
how green (`green_share_of_colour_pct` in the screenshots: today 66-96%) and how varied
(`hue_entropy`, 0-1: today 0.18-0.41) the page is.

## Sampling a colour off a screenshot

To see what a faint light really comes out as on the page (a warm wash can turn bronze or brown
at low alpha over green-black), read the pixel:

    ./venv/bin/python -c "from PIL import Image; im=Image.open('out/ID/shots/home.png').convert('RGB'); print(im.getpixel((1150,120)), im.getpixel((100,640)))"

(1150,120) is the top right of Home's greeting (the `wash`: today (23,33,35)), (100,640) its bottom left (the
green glow: today (29,50,37)). A warm wash that samples as (48,44,31) reads as bronze.

## Refinements beyond colour (optional)

The owner: "small visual enhancements or refinements, even if there is a degree of randomness
(changing in size, spacing, fonts, text size, orientation, headers/labels, icons, or anything
else to improve visual appeal) are welcome, but not necessary. We are mimicking natural
selection here."

A palette may carry them as `"css"` (a string, or a list of strings) beside `tokens`: ordinary
CSS rules appended after everything else, so they win. Read
/home/user/FamilyDB/src/familydb/web/static/style.css for the selectors (the page's structure:
`.bar`, `.places`, `main`, `.page-head h1`, `.eyebrow`, `.section-head h2`, `.panel`, `.card`,
`.idea-card`, `.chip` (date tiles), `.starters a`, `.thread`, `.bubble`, `.said-by`, `.tabs`,
`button`, `.button.secondary`, `.crt`, `.welcome` ...) and use the page's own custom properties
(`var(--accent)`, `var(--r-lg)`, `var(--mono)`, ...). Every role name above is also a custom property you
can use in css: `var(--brand)`, `var(--lit)`, `var(--screen)`, `var(--outing)`, `var(--ideas)`,
`var(--plans)`, `var(--todo)`, `var(--people)`, `var(--shows)`, `var(--seasons)`, `var(--danger)`
(the stylesheet's own names, `--green`, `--lilac`, `--cyan`, ... work too).

- Faces: the page's own three, DM Sans (variable: weight 100-1000, optical size 9-40, e.g.
  `font-variation-settings: "opsz" 32`), DM Mono 400 and 500 and VT323 (`var(--sans)`,
  `var(--mono)`, `var(--terminal)`), AND a library of open-licence faces that would ship in
  static/fonts if chosen:
  - sans: IBM Plex Sans, Inter, Geist, Space Grotesk, Hanken Grotesk, Red Hat Text, Atkinson
    Hyperlegible, Nunito, Manrope, Figtree, Outfit, Lexend, Instrument Sans;
  - condensed and wide: IBM Plex Sans Condensed, Barlow Condensed, Archivo (width 62-125),
    Bricolage Grotesque (optical size and width);
  - serif: Source Serif 4, Literata, IBM Plex Serif, Fraunces, Newsreader;
  - mono: IBM Plex Mono, Geist Mono, JetBrains Mono, Red Hat Mono, Spline Sans Mono, Azeret Mono,
    Fira Code, Victor Mono, Martian Mono, Space Mono, Share Tech Mono, Chivo Mono, Recursive;
  - CRT and pixel: Workbench and Sixtyfour (their BLED axis draws phosphor bleed, SCAN draws
    scanlines: heavy above about 30, so keep them to the tubes and use them lightly), Doto (a
    dot-matrix, ROND rounds its dots), Pixelify Sans, Silkscreen.
  Just name
  one in `font-family` (e.g. `font-family: "IBM Plex Mono", var(--mono);`) and the check adds
  its @font-face rules. Variable axes where the face has them: Recursive (wght, slnt, CASL, CRSV,
  MONO), Fraunces (opsz, wght, SOFT, WONK), Newsreader, Source Serif 4, Literata and Inter (opsz,
  wght), Bricolage Grotesque (opsz, wdth, wght), Archivo, Martian Mono and Instrument Sans (wdth,
  wght), Workbench and Sixtyfour (BLED, SCAN), Doto (wght, ROND), and wght for most of the rest.
  Text rendering is yours too: `font-optical-sizing`, `font-variation-settings`,
  `font-feature-settings` (ss01, cv.., zero, tnum, onum), `font-variant-*`, `font-kerning`,
  `font-synthesis: none`, `text-rendering`, `text-wrap`,
  `text-box: trim-both cap alphabetic`, and underline thickness, offset and skip-ink.
- Budget: up to 60000 characters of css appended to today's stylesheet, or a clean sheet of
  your own ("A clean sheet" below). Decorative pseudo-elements may be switched off with `content: none`.
- Refused by the check: `@import`, `expression(`, `javascript:` and any `url(` to an outside
  address. Everything else is yours, `display: none` and `content:` included; the words the
  page shows are measured and reported, not refused.
- Measured on the rendered pages and reported to the judges: sideways scroll on any page,
  desktop or phone, and the smallest words a person reads (today's smallest is 11.5px).
- Keep them small and purposeful: a refinement is a mutation that survives only if the judges
  find the page more appealing. Winners carry theirs on to the next round.

## Typesetting (the owner enjoys it)

The owner: "I enjoy typesetting/pagination in general and will appreciate even minor optimization of typography." Any palette may carry typographic refinements in `css`,
whatever its roll. CSS reaches most of what a typesetter would tune here:
- scale and hierarchy: `font-size`, `font-weight`, `letter-spacing` and `line-height` per level
  (`h1`, `.page-head h1`, `h2`, `.section-head h2`, `.card h2`, `body`, `.eyebrow`, `.said-text`)
- `text-wrap: balance` (headings) and `text-wrap: pretty` (paragraphs); `hyphens: auto`
- figures: `font-variant-numeric: tabular-nums | oldstyle-nums | lining-nums | slashed-zero`
- `font-variant-caps: small-caps | all-small-caps`; `font-feature-settings` ("ss01", "cv..."
  where the face has them); `font-kerning: normal`
- optical sizes: `font-optical-sizing: auto` or `font-variation-settings: "opsz" N` (DM Sans
  9-40, Fraunces 9-144, Newsreader 6-72)
- measure: `max-width` in `ch` on `.said-text`, `p`
- rhythm: margins and gaps on one unit (`main`, `.panel`, `.section-head`, `.thread`)
Measured, not refused: the smallest words (today's are 11.5px). Hanging punctuation is not
supported by this Chromium, so hang quotes and bullets by hand (a negative indent, or the list
pulled into the margin). The library faces carry their full OpenType features and true italics:
`tnum`, `onum`, `smcp`, `zero`, stylistic sets and character variants work where the face has
them. Arrows, box-drawing, block and geometric glyphs are included too.

## A palette's own markup (variants)

Every entrant may change the page's markup too, not only its stylesheet, when its idea needs it:
a random entrant when its roll's structure (layout, controls, icons, pacing) calls for it, a
WILDCARD for any reason, a MUTANT when one of its rolled changes is structural (copy the parent's
`variants/<parent>/` to `variants/<your id>/` first, when it has one, so everything else it had
stays), a CROSSOVER from its structure parent's variant, and INFORMED entrants when the brief or
the page calls for it. The traits stay traceable through each round's `seeds.json` and
`args.json`, which record every roll. Put your own copies of any templates in `variants/<id>/templates/` (same
file names as /home/user/FamilyDB/src/familydb/web/templates/, e.g. `home.html`, `base.html`,
`_ui.html`; copy the real one and change it) and any pictures or icons in
`variants/<id>/static/` (e.g. your own `icons.svg`, keeping every icon it had; new svg, png or
webp pictures). ./check.sh then serves your page from its own server for your render only;
nothing touches the repository.

The arrangement, size, position and even the existence of every element are yours. Move,
resize, merge, hide or remove anything, forms, fields, links and whole sections included. What
your templates remove (fields, form actions, links, icons) is written to
`variants/<id>/removed.txt` and shown to the judges beside your design, to weigh what the family
would lose against what the page gains. Say in your notes why you removed it. Refused on a
variant:
- a form you keep that has lost its csrf token;
- new scripts, inline style attributes, inline event handlers, unescaped output (|safe,
  Markup) or outside addresses (the page's security policy).

The page's words are MEASURED, not refused. Each page's words are compared with today's and the
share that differs is reported to the judges. Moving, regrouping and restyling cost nothing;
rewording headings and labels, or dropping or adding words, shows in that share. Do it when your
idea is better for it, and say what you changed and why, because the family's wording would
follow a winner.
Layout, element types, grouping, order, headers and footers, icons and pictures are yours.

## A clean sheet

A design may start from nothing instead of from today's stylesheet. Write your own complete
stylesheet in `variants/<id>/sheet.css` and set `"sheet": "variants/<id>/sheet.css"` in the
palette file. The check then serves your sheet INSTEAD of today's 104 KB stylesheet, with only
two things added:
- your tokens, as custom properties (`--bg`, `--surface`, `--ink`, `--green` or `--brand`,
  `--screen`, `--accent`, the section colours and any page-wide role you set);
- the `@font-face` rules of the library faces your sheet names.

Nothing of today's look is inherited: layout, type, spacing, cards, the bar, the monitors,
controls, focus rings and motion are all yours to draw. Read today's stylesheet
(/home/user/FamilyDB/src/familydb/web/static/style.css) for the page's structure and its
functional rules, and keep what the page needs to work:
- `[hidden] { display: none }`;
- visually hidden text, if you keep it hidden (it is still read out);
- the bar's menu (a `details`) and the ask box's states;
- `prefers-reduced-motion`;
- a visible focus ring.

The budget is 200,000 characters. `url(` may name the page's own files (a relative path or
`/static/...`, for your pictures), never an outside address. `@import` is refused.

## Graphics, pictures and icons

Graphics are as open as colour and type, and big changes are welcome where they make the page
better. There are two routes.
- Icons. The page draws every icon from one sprite, `static/icons.svg`, through the `icon`
  macro in `_ui.html` (`<use href="…icons.svg#i-NAME">`). To redraw them, copy
  /home/user/FamilyDB/src/familydb/web/static/icons.svg to `variants/<id>/static/icons.svg` and
  redraw the symbols inside it (a mutant starts from its parent's sprite when it has one).
  Every `<symbol id="i-…">` it had must stay (the check refuses a sprite that drops one), and you
  may add your own. Draw to its 24-unit grid, in
  `currentColor`, so CSS still colours them.
- Pictures. Put SVG, PNG or WebP files in `variants/<id>/static/` and place them through your
  templates: `<img src="{{ url_for('static', filename='name.svg') }}" alt="">` (decorative:
  empty alt), or inline `<svg>` in a template, or a new `<symbol>` in your sprite used through the
  `icon` macro. CSS may load your pictures too: `url(name.svg)` is resolved relative to
  `/static/`, so `variants/<id>/static/name.svg` is `url(name.svg)` or `url(/static/name.svg)`.
  Small `data:image/` URIs are allowed as well.

The rules:
- Words in a picture are counted and measured as the page's words. Mark a decorative drawing
  `aria-hidden="true"` (as the radar is) and give an `<img>` an empty alt, so its lettering is
  neither counted nor read as the smallest text.
- In an inline `<svg>` use presentation attributes (`fill`, `stroke`, `stroke-width`,
  `opacity`) or classes styled from your css. A `<style>` element is refused, because the
  page's policy would block it. An inline `<svg>` needs no `xmlns`.
- In the sprite, a filled icon sets `fill="currentColor" stroke="none"` on its own shapes, or
  your css changes `.icon`. Attributes on the sprite's root never reach a `<use>`.
- There are no scripts inside an SVG, and nothing loads from outside.
- A picture must earn its place: light enough to read over, and drawn in one style with the
  type and the lines.
- The render shows your pictures on every page they reach, in the full-size shots and the
  strips.

## What the judges see beyond the pages

How the pages are shot: about 1.8s after each page loads, with motion on. An arrival must finish
within about 1.5s and start from a dim colour or a low opacity, never 0 (an element at opacity 0
counts as missing and its words as dropped). The details strip finds its elements by class, so
keep these on whatever you draw, adding your own classes beside them (an element you remove
leaves its cell in the strip empty, which the judges will see): `.idea-card` on each
idea's card or row, `.next-up` on the Next up monitor, `#title` and `.field.wide` on the new-idea
form's title field, `label.check` on its checkboxes, and `details.menu > summary` on the bar's
menu.

- `strips/<id>-details.png`: the controls (a field being typed in, a ticked box, a focused
  select, the bar's menu open), focus rings at four Tab stops, the afterglow fading after the
  pointer leaves a card, and Next up's monitor switching on. Style the controls too: selects
  (`appearance: base-select` draws a stylable picker in the page, with `::picker(select)`),
  checkboxes and radios (`accent-color`, or `appearance: none` and your own drawing), fields,
  `:focus-visible`, hover and press states, scroll bars (`scrollbar-color`, `scrollbar-width`),
  and motion (`--afterglow`, `--glow-in`, the animations; keep `prefers-reduced-motion`).
- `strips/<id>-squint.png` and `sheets/squint.png`: Home, Ideas and Chat blurred, the squint
  test: what does the eye find first, is the page's purpose and its main action clear at a glance?
- `health.json`: the Tab order on Home, and how many click targets are under 44px.
- Rendered pages now also include Plans (the month), To do, Settings, a settings page
  (General) and the new-idea form, with scroll bars visible.
