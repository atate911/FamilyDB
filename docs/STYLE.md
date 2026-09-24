# How the page looks, and why

The web page's look is called **Phosphor**: a modern family planner, lit the way an old green
screen was. It is a present-day app first (calm charcoal surfaces, a friendly sans, line icons,
generous space) and the old monitor survives in it as *light*, not as costume: a phosphor-green
glow on the handful of things that deserve attention, and nowhere else. Anyone who sat in front of
a green monochrome monitor should feel a flicker of recognition; nobody should feel they are
using a theme.

It was not always this restrained. The first pass leaned hard into the CRT (pixel type, pixel
icons, scanlines, a boot screen); the family asked for something more modern that only evokes it,
and this is that. The rule that came out of it: **nostalgia shows up as light and small winks,
never as a style the page is imitating.**

Everything here is carried by one stylesheet (`src/familydb/web/static/style.css`), a handful of
templates, two open-licensed typefaces and one icon sprite, with no script beyond the one the page
already had. A change to the page should be checked against this document.

## Principles

1. **A real, modern app first.** Layout, spacing, controls and type are those of a good
   present-day product: one clear action per place, 44-pixel targets, a tab bar under the thumb
   on a phone, sentence-case labels, readable type. Nothing retro may cost usability.
2. **The CRT survives as light.** Phosphor green glows only where attention belongs: the mark
   and cursor in the bar (and the bot's face), the primary button, the box being typed in, the
   key words of the home page's greeting, the next plan, live status and finished tasks, the
   day's spend, and the 404. The icon tile beside a page title glows in that page's colour, and
   amber glows for *today*. If everything glowed, nothing would.
3. **Colour says where you are.** Each part of the site has one colour, and each kind of idea has
   one; colour is used to tell things apart, never as decoration, and never on its own.
4. **Two voices.** DM Sans for everything read; DM Mono, sparingly, for the machine's small voice:
   times and figures, the small labels above data, the name in the bar.
5. **Keep the eye still.** A page's title, its one line of purpose and its one or two actions sit
   together at the top. What you do with a thing sits beside it. What is next is the first thing
   on the home page. The chat's box is under the newest line, with Send beside who is sending.
6. **A few quiet winks.** The blinking cursor after the name. "Ready" above the sign-in. "No
   signal" and a momentary flicker on the page that is not there. A whisper of scanlines inside
   the home page's glow. A month that prints as green-bar paper. Each is small, none is in the
   way, and all motion stops for anyone who asks for less.
7. **Accessible by construction.** Contrast is measured, focus is always visible, every box has a
   label, motion, contrast and forced-colour preferences are honoured, and nothing needs a script.

## Colour

Surfaces are charcoal with a breath of green in them, the colour of a screen switched off. Words
are near-white; green is light, not text.

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#0b0e0d` | the page, with a faint green afterglow at the top |
| `--surface` / `-2` / `-3` | `#121615` / `#171c1a` / `#1d2321` | cards, hover, selected |
| `--field` | `#0e1211` | inside a box you type into |
| `--line` / `--line-2` | `#232a27` / `#2f3834` | hairlines and dividers |
| `--edge` | `#5c6862` | the border of a box you type into: 3.1:1 on a surface |
| `--ink` | `#edf2ef` | text, 17:1 |
| `--ink-2` | `#bac5bf` | secondary text, 10:1 |
| `--dim` | `#919e98` | quiet text, 6.6:1 |
| `--faint` | `#7d8a84` | placeholders, ids and meta icons, 5:1 |

The colours, each readable as text on a surface (the ratio is against `--surface`), and each
carrying dark text (`--on-bright`) when it is a fill:

| Token | Value | Belongs to |
|---|---|---|
| `--green` | `#6dff9c` (14:1) | the brand, the primary button, focus, what is next and live; Home, Chat, Status, Settings |
| `--lilac` | `#b7a4ff` (8.5:1) | Ideas; events and kinds the family made up |
| `--cyan` | `#6cd4ff` (10.9:1) | Plans, and the month on every date |
| `--lemon` | `#f7dc78` (13:1) | Things to do, open tasks, activities |
| `--amber` | `#ffbf5f` (11:1) | the Family, grown-ups' faces, restaurants, today, anything needing a look |
| `--pink`, `--blue`, `--orange` | 9.7, 8.8, 9.4:1 | shows and children's faces, trips, seasonal ideas |
| `--red` | `#ff6b6b` (6.6:1) | only what went wrong or cannot be undone |

**Sections.** `base.html` works out which part of the site a page belongs to from the view that
drew it and puts `in-ideas`, `in-plans` and so on on the `<body>`; the stylesheet sets `--accent`
from it. The icon tile beside the page title, the icon of the current place in the bar, the chosen
tab's icon and the page's links take `--accent`.

**Kinds.** A kind label (`kind_label` in `_ui.html`) carries `kind-restaurant`, `kind-outing` and
so on, in that kind's colour; a card holding one takes the colour for its hover glow.

## Type

| Face | Where |
|---|---|
| **DM Sans** (variable, 100–1000, optical sizes 9–40) | everything read: titles, headings, body, buttons, the bar, labels, the chat |
| **DM Mono** (400, 500) | times and figures (the spend, table numbers, opening hours), the small uppercase labels above data, the month on a date, the name in the bar, the tools a reply used |

Both are under the SIL Open Font License and served from `static/fonts/` (about 90 kB) because
the content policy lets fonts come from this site only. DM Sans is friendly and current; DM Mono is
its sibling with just enough typewriter in it to carry the old screen without dressing up as it.

Page titles are 700 weight, tight (-0.025em), 1.9–2.6rem; the home headline goes to 4rem.
Section headings are 1.2rem semibold. Body is 1rem at 1.6. Paragraphs stop at about 60 characters.

## Shape and space

- Cards: 16px corners, a hairline edge, the faintest top highlight. The home greeting is 22px.
- Buttons and boxes: 10px corners, 44px tall. The primary button is phosphor green with a soft
  glow; the secondary is a raised neutral; the quiet one is an outline; the dangerous one is red
  text on an outline until hovered.
- Pills (tags, "in 2 days") are fully rounded; the status of an idea is a coloured pill.
- Spacing runs on a quarter-rem scale; cards sit 1.25rem apart; content is at most 74rem wide,
  the chat 52rem so the eye does not cross the screen between a question and its answer.

## Icons

Line icons from [Lucide](https://lucide.dev) (ISC licence, `static/LICENSE-icons.txt`), from
one pinned release, gathered into one sprite (`static/icons.svg`) by `scripts/icons.py`, and
used through the `icon()` macro in `templates/_ui.html`. They are drawn with a 1.75 stroke in the
colour of the words beside them; an icon beside words is hidden from screen readers, one standing
alone gets a label. To add one, put its name in `ICONS` in the script and run
`uv run python scripts/icons.py`; never edit the sprite by hand.

**The mark** is the page's own: a little monitor with a smile, drawn on the same grid and stroke.
It is the favicon, the bot's face in the chat, and the mark in the bar, where it glows.

## The parts

- **Page head** (`page_head` in `_ui.html`): breadcrumbs for a page inside another, the page's
  icon on a tile of its colour, the title, one line of purpose, and the page's actions on the
  right.
- **Card**, **segmented tabs**, **pills**, **notices** (a green dot for what a form said, a red
  one for an error).
- **Date** (`chip` in `_ui.html`): a small calendar leaf, the month in cyan above the day. Today
  is amber; the next plan, on the home page, glows green. `views.date_chip` splits the date.
- **Relative time**: "tomorrow", "in 2 days" as a small pill beside the date, so a wrapped line
  never starts with a separator.
- **Live dot**: green, gently breathing; the status page's lights are dots that are lit, hollow
  (red) or half lit (amber), with words beside them.
- **Meter**: an SVG bar (the content policy allows no inline style, so widths are SVG
  attributes), always with its figure written beside it.

## Page by page

- **The bar.** On a phone the five everyday places (Home, Chat, Ideas, Plans, To do) are a tab
  bar along the bottom, the current one marked by a pill in its colour; Family, Status and
  Settings and signing out are icons at the top. From 52rem everything is one bar that stays at
  the top while the page scrolls.
- **Home.** The greeting and the two things most people came for (ask about the weekend, add an
  idea) on the left, lit from below; **Next up** on the right: the next plan, its date glowing.
  Then anything left to set up, what else is coming, and what was added lately.
- **Chat.** A messaging layout: the bot on the left with its mark, the family on the right with
  their initial; a typing indicator while it thinks; one box with the message on top and From,
  Send where I am and Send along the bottom, lit green while you write.
- **Ideas.** A grid of cards with the kind in colour, where, who, how long and the cost; the quick
  note that Chat turns into an idea is folded away so the list is on the first screen.
- **An idea.** The idea on the left; what you do with it (the calendar, plan it, record how it
  went) in a column beside the title; the place's details below.
- **Plans.** A list of dates, and a month with today in amber and plans as cyan slips; on a phone
  the month is the busy days as a list.
- **Things to do**, **Family**, **Settings** (with an index and a save bar that stays in reach),
  **Status** (three monitors, then the day's spend as the one big glowing number), **Sign in**,
  **Not found** (a glowing 404 that flickers now and then).
- **On paper.** Printing turns any page into green-bar printout: black on white with a pale green
  band on every other line. The month on the fridge.

## Accessibility

- Text contrast is at least 4.5:1 everywhere (see the tables); boxes you type into have a 3:1
  edge. Placeholders are hints, never labels.
- Focus is a green ring on everything, offset from the control.
- Every box has a label joined to it by `for`; the chat's message box has one for screen readers
  only, since the box itself says what it is for.
- Nothing is said by colour alone: the chat tells voices apart by side and face; status lights
  differ in shape and carry words; kinds and statuses are written out.
- `prefers-reduced-motion` stops the cursor, the typing dots, the breathing dots and the 404's
  flicker. `prefers-contrast: more` lifts secondary text and edges and takes away the glow and the
  scanlines. Forced colours keep dots, boxes, dates and faces outlined.
- The page works with scripts off; the only script is still `static/locate.js`.

## Rules the look has to keep

- The content policy is `default-src 'self'` with `style-src 'self'`: no inline `style`
  attributes, no `<style>` blocks, no fonts or pictures from anywhere else. Anything that needs a
  computed size is SVG with attributes.
- A few pieces of markup are what the tests read, and they stay exactly as they are:
  `class="panel card"` on each card of the ideas and restaurants lists, `class="said"` with the
  text right after it, `<summary>Move it</summary>` on a plan that can be moved, `class=" today"`
  on today in the month.
- Class names are shared across the whole stylesheet: check a new one is not already taken (a
  meter once borrowed `.bar` from the top bar and flattened it).
- A new colour, face, glow or motion goes here first, with the reason.

## Left for later

- **A light theme.** The page is dark on every device, by choice. A daylight version would be a
  line on the settings page, like everything else the family can change.
