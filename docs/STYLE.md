# How the page looks, and why

The web page has a look of its own, called **Phosphor**: a calm, dark, present-day app with an
old green screen in its heart. It is nostalgia, not replication. Anyone who sat in front of a
green monochrome monitor, a home computer on the family television or a colour set showing its
test card should feel a flicker of recognition; nobody should feel they are using a museum
piece. The CRT is one player on the page, never the whole picture.

Everything here is carried by one stylesheet (`src/familydb/web/static/style.css`), a handful of
templates, three open-licensed typefaces and some pixel drawings, with no script beyond the one
the page already had. This document is what a change to the page should be checked against.

## Principles

1. **A modern app first.** Layout, spacing, controls and reading type are those of a good
   present-day app: generous space, one clear action per place, touch targets of at least 44
   pixels, a tab bar under the thumb on a phone. The retro touches sit on top of that and never
   cost usability.
2. **The CRT lives where a screen is drawn.** Scanlines, glass glare and a curved-tube vignette
   appear only on things the page depicts as screens: the little monitor on the home page, the
   spending readout on the status page, the brand mark, the sign-in screen's mark and the test
   card on the page that is not there. The page background is clean.
3. **Pixel type glows, reading type is sharp.** The big display type (headlines, dates, sums of
   money) is set in a pixel face with a soft phosphor bloom: a slight blur, a glow in its own
   colour and, on headlines, a faint red and blue fringe where the three guns of a colour set
   never quite met. Anything read as a sentence is crisp.
4. **Colour means something.** Green is the brand and the one thing to press. Each part of the
   site, and each kind of idea, has its own phosphor, so a colour always answers "where am I?"
   or "what is this?". Colour is never the only way something is said.
5. **Keep the eye still.** The title of a page and the one or two things it is for sit on one
   line. What you do with a thing sits beside it, not below its reference detail. The chat's
   box is directly under the newest line, with who is sending and the Send button side by side.
6. **Delight in small doses.** A cursor that waits, a monitor that warms up, a kite, a boot
   banner, a test card that slips its hold now and then, a horizon at the foot of every page.
   Each is small, none is in the way, and all of them stop for anyone who asks for less motion.
7. **Accessible by construction.** Contrast is measured, not judged by eye; focus is always
   visible; every control has a label; motion, contrast and forced-colour preferences are
   honoured; nothing needs a script.

## Colour

The surfaces are charcoal with the faintest green in them, the colour of a screen switched off.
Words are near-white, never green: a paragraph is for reading, not for glowing.

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#0a0d0c` | the page |
| `--panel` / `--panel-hi` | `#111614` / `#171e1b` | cards and panels |
| `--field` | `#0b0f0e` | inside anything you type into |
| `--line` / `--line-hi` | `#222b27` / `#33413a` | hairlines, dividers |
| `--edge` | `#5a6a62` | the border of a box or a quiet button: 3.2:1 on a panel |
| `--ink` | `#eef2ef` | text |
| `--dim` | `#a3b1a9` | secondary text: 8:1 on a panel |
| `--faint` | `#75857c` | placeholders and ids: 4.9:1 on a field |

The phosphors, each bright enough to read as text on a panel (7:1 and up, red 6.6:1), and each
with dark text (`--on-bright`) when it is a fill:

| Token | Value | Belongs to |
|---|---|---|
| `--green` | `#6dff9c` | the brand, every primary button, Home, Chat, Status, Settings, the bot |
| `--lilac` | `#b69cff` | Ideas, and ideas of a kind the family made up |
| `--cyan` | `#5fd4ff` | Plans, and every date on the page |
| `--lemon` | `#ffe27a` | Things to do, open tasks |
| `--amber` | `#ffb84d` | the Family, people's faces, food and restaurants, today, anything wanting attention |
| `--pink`, `--blue`, `--orange` | | the kinds: shows, trips, seasonal ideas; children's faces |
| `--red` | `#ff6b6b` | only what went wrong or cannot be undone |

**Sections.** `base.html` works out which part of the site a page belongs to from the view that
drew it and puts `in-ideas`, `in-plans` and so on on the `<body>`; the stylesheet sets
`--accent` from it. The headline, the prompt above it, the lit corner of every panel, the tabs,
links and focused boxes all take `--accent`. Each link in the bar carries its own section's
colour, so the icon there is already the colour of the page it leads to.

**Kinds.** A card's kind label (`kind_label` in `_ui.html`) carries `kind-restaurant`,
`kind-outing` and so on; a card, a home-page tile or an idea page that holds one takes that
kind's colour for its corner, its hover glow, its icons and, on the idea page, its headline.
Restaurants are amber, outings green, day trips cyan, trips blue, shows pink, seasonal ideas
orange, activities lemon, events and anything new lilac.

**Status** keeps its meanings: a lit green square for working, a hollow red one for not, a
half-lit amber one for partly. The shape and the words beside it say the same thing as the
colour.

## Type

Three faces, all under the SIL Open Font License, served from `static/fonts/` because the
content policy lets fonts come from this site only (about 95 kB together, Latin subsets):

| Face | Voice | Where |
|---|---|---|
| **VT323** | the screen | page headlines, the brand, the day on a date, the month, the sum spent, big letters on faces. Always with the phosphor bloom. |
| **IBM Plex Sans** | the people | everything read as a sentence: descriptions, card titles, section headings, buttons, the bar, form boxes, the family's own chat lines. |
| **IBM Plex Mono** | the machine | small labels above boxes, eyebrows, tags, times and figures, tables, and every line the bot says in the chat. |

IBM's Plex is a quiet nod to the terminals the green screen came from, and it is simply a good
modern face. The chat's split is deliberate: the bot speaks in the machine's type, the family in
the people's, so the two voices look different before a word is read.

Sizes: headlines 2.6–3.5rem (5rem on the home page), section headings 1.3rem semibold, body
1rem at 1.6 line height, labels 0.7rem with wide tracking. Paragraphs stop at about 60–70
characters.

## Shape and space

- Panels: 16px corners, a hairline edge, a slightly lighter top, and one **lit corner** at the
  top left in the page's colour: the signature detail, like the corner of a screen catching the
  light.
- Buttons and boxes: 10px corners, 44px tall. The primary button is solid green with a soft
  glow; the secondary is outlined; the quiet one is barely there; the dangerous one is red and
  outlined, filling only on hover.
- Spacing runs on a quarter-rem scale; panels sit 1.25rem apart, page heads have 1.75rem below
  them and a hairline under the title.
- Content is at most 76rem wide; the chat is 56rem so the eye does not cross the screen between
  a question and its answer.

## Icons and pictures

Every picture is pixel art, drawn as text in `scripts/pixels.py` (a character per pixel) and
written out as SVG made only of square runs, so it is crisp at any size and never blurry at the
edges. Change a drawing there and run `uv run python scripts/pixels.py`; never edit the SVG by
hand.

- **Icons** (`static/icons.svg`, one sprite, used through the `icon()` macro in
  `templates/_ui.html`) are 12 by 12 and take the colour of the words around them. They are
  crispest at 12, 18, 24 and 36 pixels, and those are the only sizes the stylesheet uses. An
  icon beside words is hidden from screen readers; an icon standing alone is given a label.
- **The brand mark** is a little monitor with a smiling face, also the favicon, the bot's face in
  the chat and the mark on the sign-in screen.
- **The home page's screen** (`art/sunset.svg`) is a Saturday evening: a dithered dusk sky, a
  setting sun cut by two bands of cloud, home with the porch light on, and the family holding
  hands on the hill with the dog running ahead and the youngest flying a kite. It warms up like a
  picture tube when the page opens.
- **The horizon** (`art/horizon.svg`) closes every page: hills, pines, flowers and a lit window.
- **The test card** (`art/testcard.svg`) is the page that is not there: the old colour bars, with
  NO SIGNAL across them, and now and then the picture slips.

## The parts

These live in the stylesheet under their own headings and are used the same way everywhere.

- **Page head** (`page_head` in `_ui.html`): a prompt-style path (`>~/plans/month`, the one nod to
  the command line up top), the headline, an optional line under it, and the page's one or two
  actions on the right, where the eye lands after the title.
- **Panel**, **card** (a panel whose whole face is the link), **tabs** (a pair of keys, the chosen
  one lit in the page's colour).
- **Date chip** (`chip` in `_ui.html`): a plan's day as a tear-off calendar leaf, the number lit
  cyan, or amber when it is today. `views.date_chip` splits the date for it.
- **Notice**: what a form said, with a green `>` badge; an error, with a red `!`.
- **Lights** on the status page, and the **readout**: today's spend as a lit figure with a meter
  drawn in block characters, out of the day's limit, going amber past three quarters and red at
  the limit.
- **Setup checklist** on the home page: `[ ]` boxes in amber until everything is connected.

## Page by page

- **The bar.** On a phone the five places a day is spent (Home, Chat, Ideas, Plans, To do) are
  a tab bar along the bottom, under the thumb; the three for looking after it (Family, Status,
  Settings) and signing out are icons at the top. From 52rem everything is one bar at the top,
  which stays put while the page scrolls; Home is the name at the left.
- **Home.** The greeting and the two things most people came for (ask about the weekend, add an
  idea) first, then anything left to set up, then what is coming up beside what was added lately.
  On a phone the little monitor is left out so what is coming up is on the first screen.
- **Chat.** The bot's lines down the left with its face, the family's to the right with their
  initial on an amber tile; the newest bot line ends in a waiting cursor; while it is thinking,
  a blinking block says so. The box sits right under the newest line.
- **Ideas.** Cards in a grid, each with its kind in colour, where, who, how long and the cost in
  amber. The quick note that Chat turns into an idea is folded away so the list is on the first
  screen, and fits on one row when opened.
- **An idea.** The idea on the left; what you do with it (on the calendar, plan it, record how
  it went, how it went) in a column on the right, beside the title rather than under the opening
  hours. On a phone the doing comes before the place's details.
- **Plans.** A timeline of date chips. The month is a grid with today in amber, weekends faintly
  lit and each plan a cyan slip; on a phone just the busy days, as a list.
- **Things to do.** Cards with a checkbox that fills green when done, the reminder in amber, and
  editing folded away.
- **Family.** Each person as a face with their initial, amber for grown-ups and pink for
  children, grey when switched off.
- **Status.** The three monitors (who answers, keys, what is connected) side by side, then the
  spending readout and its tables, what is waiting and what is worth a look.
- **Settings.** A long page, so an index of it down the side (above it on a phone), and the big
  form's Save button stays in reach at the bottom of the screen while the form is on it.
- **Sign in.** A home computer waking up: the monitor, a banner, `PLENTY OF WEEKENDS FREE`,
  `READY.`, and the one question it has. The bar is left out.
- **Nowhere.** The test card, NO SIGNAL, and one button home.
- **On paper.** Printing turns any page into green-bar printout, black on white with a pale green
  band on every other line: the month on the fridge.

## Accessibility

- Text contrast is at least 4.5:1 everywhere, 7:1 and up for most; boxes and quiet buttons have
  an edge of at least 3:1 against what they sit on. Placeholders are hints, never labels.
- Focus is a near-white ring on everything, distinct from every accent.
- Every box has a visible label joined to it by `for`; checkboxes read as sentences.
- Nothing is said by colour alone: the chat tells voices apart by side, type and face; lights
  differ in shape; states and kinds are written as words.
- `prefers-reduced-motion` stops every animation (the cursor, the warm-up, the slipping test
  card, the breathing lights). `prefers-contrast: more` lifts secondary text and edges and takes
  away the glow, the blur and the scanlines. Forced colours keep the lights, boxes and faces
  outlined.
- The page works with scripts off; the only script is still `static/locate.js`.

## Rules the look has to keep

- The content policy is `default-src 'self'` with `style-src 'self'`: no inline `style`
  attributes, no `<style>` blocks, no fonts or pictures from anywhere else. Pictures that need a
  size are SVG with presentation attributes, or text (the spending meter is block characters).
- A few pieces of markup are what the tests read, and they stay exactly as they are:
  `class="panel card"` on each card of the ideas and restaurants lists, `class="said"` with the
  text right after it, `<summary>Move it</summary>` on a plan that can be moved, `class=" today"`
  on today in the month.
- A new colour, face, icon size or motion goes here first, with the reason.

## Left for later

- **A light theme.** The page is dark on every device, by choice: it is the brand. A daylight
  version ("green-bar paper", the print style carried to the screen) would be a line on the
  settings page, like everything else the family can change.
- **Section colours in the chat's history.** The bot's lines could carry the colour of what it
  did (a plan in cyan, an idea in lilac), once the log says which kind of thing each reply was.
