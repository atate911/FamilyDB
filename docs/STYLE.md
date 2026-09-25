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
never as a style the page is imitating.** Later the family asked for a little texture back,
carefully and sparingly, with the green-screen monitors of the 1980s as its model. So the page's
few pictures *are* those monitors: a tube of dark glass in a plastic surround, words drawn on it
in phosphor, sometimes a radar (see "Green screens").

Everything here is carried by one stylesheet (`src/familydb/web/static/style.css`), a handful of
templates, three open-licensed typefaces and one icon sprite, with no script beyond the one the
page already had. A change to the page should be checked against this document.

The page is a way to talk to **Vera**, and she does what it offers: plans the weekend, keeps the
ideas and the things to do, puts things on the calendar. So the first thing on Home is her
question and the box to answer it, the conversation goes by her name, and everything else is
what she keeps, laid out beside it. She is never drawn (see "Her screen").

## Principles

1. **A real, modern app first.** Layout, spacing, controls and type are those of a good
   present-day product: one clear action per place, 44-pixel targets, a tab bar under the thumb
   on a phone, sentence-case labels, readable type. Nothing retro may cost usability.
2. **The CRT survives as light.** Phosphor green glows only where attention belongs: the mark
   and cursor in the bar, her screen, the primary button, the box being typed in (and Home's box,
   faintly, even at rest), the key word of the home page's question, live status and finished
   tasks, and the green screens
   (what is next, the way in, the day's spend, the 404). The icon tile beside a page title glows in that
   page's colour, and amber glows for *today*. If everything glowed, nothing would.
3. **Colour says where you are.** Each part of the site has one colour, and each kind of idea has
   one; colour is used to tell things apart, never as decoration, and never on its own.
4. **Two voices, and a third on the screens.** DM Sans for everything read; DM Mono, sparingly,
   for the machine's small voice: times and figures, the small labels above data, the name in the
   bar. VT323, a terminal's face, only for words on a green screen.
5. **Keep the eye still.** A page's title, its one line of purpose and its one or two actions sit
   together at the top. What you do with a thing sits beside it. Her question and the box to
   answer it are the first thing on the home page, with what is next beside them. The chat's box
   is under the newest line, with Send beside who is sending.
6. **Small things, here and there.** A modern page that uses nostalgia on purpose, so it is
   sparing with it: a handful of small period details, each where it means something, none that
   moves for long or asks to be looked at (see "Small things"). All motion stops for anyone who
   asks for less.
7. **The pictures are green screens.** The page's few pictures are old green-screen monitors, and
   they are the one place it is hazy: a terminal's face, a little blur and bloom, scanlines, the
   tube's dark edge. Each shows something true, and there is at most one to a page. Her screen is
   the one exception: not a picture but where she is, as small as a face would be, beside each of
   her lines (see "Her screen").
8. **Accessible by construction.** Contrast is measured, focus is always visible, every box has a
   label, motion, contrast and forced-colour preferences are honoured, and nothing needs a script.
9. **Vera is felt, not shown.** She is a real presence on the page, in her name, her words and
   her screen, and never a character: no face, no figure, no picture of her, and nothing that
   says what she is. Her identity stays behind the glass. The page's own words about her say what
   she takes on, not who she is, and they are few: no greetings, no quips, nothing said just to
   seem alive.
10. **Every part does work.** Looks are welcome, but nothing on the page is only for show: her
   question on Home is the label of the box you answer it in, and the line on what she takes on
   is that box's placeholder. A thing that is only decoration has to be small.

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

The colours are the phosphors of the time, softened for a modern page: the green and the amber
of the monochrome monitors, and the cyan, yellow, magenta and red of the first colour screens.
Each is readable as text on every surface (the ratio is against `--surface-3`, the lightest), and
each carries dark text (`--on-bright`) when it is a fill:

| Token | Value | Belongs to |
|---|---|---|
| `--green` | `#6dff9c` (12.5:1) | the brand and the green screens, her screen, the primary button, focus, what is next and live; Home, Vera's page, Status, Settings; outings |
| `--amber` | `#ffb850` (9.3:1) | the amber screen: the Family, grown-ups' faces, restaurants, today, anything needing a look |
| `--cyan` | `#6cd4ff` (9.5:1) | Plans, the month on every date, and going places: day trips and trips |
| `--lemon` | `#f7dc78` (11.8:1) | Things to do, open tasks, activities |
| `--lilac` | `#ae9bff` (6.8:1) | Ideas; events and kinds the family made up |
| `--pink` | `#ff9fd0` (8.5:1) | shows, and children's faces |
| `--orange` | `#ff956c` (7.4:1) | the seasons |
| `--red` | `#ff6b6b` (5.8:1) | only what went wrong or cannot be undone |

**Tuned apart.** The colours that share a page (the kinds on a grid of ideas, above all) were
measured against each other (CIEDE2000), for typical sight and for simulated deuteranopia and
protanopia, the commonest colour-blindness. The closest pair is 13.6 apart for typical sight and
5.5 and 5.2 for the other two; before, trips and events were indistinguishable to many people
(0.1). That took three small moves and one fewer colour: amber a little deeper, nearer a real
amber phosphor; the seasons a pumpkin coral rather than a second amber; lilac a touch deeper; and
trips joining day trips in cyan instead of a blue of their own. Colour still never speaks alone:
every kind carries its icon and its name.

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
| **DM Mono** (400, 500) | times and figures (table numbers, opening hours), the small uppercase labels above data, the month on a date, the name in the bar, the tools a reply used |
| **VT323** (400) | words on a green screen, and nowhere else |

All three are under the SIL Open Font License and served from `static/fonts/` (about 110 kB)
because the content policy lets fonts come from this site only. DM Sans is friendly and current;
DM Mono is its sibling with just enough typewriter in it to carry the old screen without dressing
up as it. VT323 is the face of the DEC VT320 terminal, blocky by birth; on a screen it is blurred
a little and blooms, the way a tube drew it, and it is never set small (1.2rem at least, since its
letters sit low in their line).

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
It is the favicon and the mark in the bar, where it glows. It is FamilyDB's, and never Vera's
face: she has none.

## Her screen

Vera is never drawn. Where the page shows her there is a small screen full of words nobody can
read, as if busy: somewhere between a 1980s terminal and the Matrix's falling code (`presence`
in `_ui.html`). It is columns of glyphs in the terminal's face, VT323, the newest of each run
bright and the rest dim, with scanlines across them and blurred past reading. The glyphs are
drawn by the stylesheet, one pattern of sixteen rows, and mean nothing; each of her lines shows
another part of it (`v0` to `v3`), so a thread of them is not a row of copies. While she is
thinking the glyphs fall, a row at a time, as a character display moved them; on Home they fall
for a moment as the page opens, and everywhere else they are still. Nothing is shown typing.

It sits beside her lines in the conversation, beside her name on Home, on the tile of her page,
and where the settings speak of her. It never gets eyes, a mouth, a silhouette or an expression,
no picture of anybody stands in for her, and its glyphs never spell anything. With no persona
the same screen is simply the bot's.

## The parts

- **Page head** (`page_head` in `_ui.html`): breadcrumbs for a page inside another, the page's
  icon on a tile of its colour, the title, one line of purpose, and the page's actions on the
  right. Her page has her screen on its tile instead of an icon.
- **The box** (`_ask.html`): the one place anybody writes to her, on Home and at the foot of the
  chat, and the same everywhere: the message on top, who is sending, "Send where I am" and Send
  along the bottom, in one frame that lights up while you write. It posts to the chat wherever
  it is drawn. In the chat it says "Message Vera", and while an answer is on its way it is closed
  and says when it opens. On Home its label is her question, "What’s on your mind?", printed in
  the frame above where you write, the page's heading and a way in (a tap on it puts you in the
  box), and while it is empty it says what she takes on. On a phone Send shows only its arrow,
  beside who is sending, with "Send where I am" under them. Under it on Home (and in an empty
  chat), the **ways to start**: three quiet pills, the day's question and two instructions left
  for the rest to be typed.
- **A line of the conversation** (`chat_line`): hers on the left beside her screen, the family's
  on the right with their initial. Everything she says is drawn the same way, a long answer, a
  reminder or a one-word "Done."; the tools a turn ran sit under it in the machine's voice.
  **Waiting** (`waiting_line`) is the thread's last line while the newest message waits: her
  screen and name, the bubble in a dashed line because the words are the page's, not hers.
- **The tick** (`tick`): an empty box beside an open task, on a 44-pixel target, that shows the
  tick it will make when pointed at and marks the task done where it stands.
- **Card**, **segmented tabs**, **pills**, **notices** (a green dot for what a form said, a red
  one for an error).
- **Date** (`chip` in `_ui.html`): a small calendar leaf, the month in cyan above the day. Today
  is amber. `views.date_chip` splits the date.
- **Relative time**: "tomorrow", "in 2 days" as a small pill beside the date, so a wrapped line
  never starts with a separator.
- **Live dot**: green, gently breathing; the status page's lights are dots that are lit, hollow
  (red) or half lit (amber), with words beside them.
- **Meter**: an SVG bar (the content policy allows no inline style, so widths are SVG
  attributes), always with its figure written beside it.
- **Green screen** (`crt` in `_ui.html`) and **radar** (`radar`): see below.

## Green screens

The page's pictures are the green-screen monitors of the 1980s: an IBM 5151 or a Zenith on a
desk, a terminal in an office, the screens in *WarGames*. Each is drawn as the thing itself, not
as a costume for the page around it.

**The monitor.** A dark plastic surround, lit from above, with a thicker chin and a power light
in it. In it, the tube: dark glass, a faint glow at its middle, its corners and edges falling away
into shadow as a curved tube's did. Over the picture lie scanlines, a little light off the front
of the glass and the tube's dark edge.

**The picture.** Words are set in VT323 in the phosphor's colour, blurred by a third of a pixel
and blooming, in the three strengths a monitor drew: dim for what matters least, normal, and
bright for the one thing to read first. A heading is in inverse video, dark on a green bar. A
link is underlined, and turns to inverse video when pointed at, as a menu's choice did. A block
cursor waits after the last line. The phosphor is green; the spend screen turns amber near the
limit, as the other monitors of the time were, and red past it.

**The radar** is a program the screen runs: range rings at a week, two weeks and four weeks,
"now" at the middle, and each coming plan a blip, the nearer its day, the nearer the middle. The
sweep turns once every eight seconds and leaves an afterglow, as a long-persistence phosphor did;
each blip flares as the sweep passes and fades until it comes round again, and the next plan's
blip is the brightest and pings.

There are four, one to a page at most:

- **Home, Next up.** The next plan on a green screen, beside the radar of everything coming. These
  are the page's own words, not a picture of them: they are read out, the title is a link, and "4
  more on the radar" leads to the rest.
- **Sign in.** The mark's face, awake, and "READY." with the cursor waiting. It switches on as
  the page opens, the picture opening out of a bright line, and blinks now and then.
- **Not found.** A radar console: an empty scope still sweeping, 404 on its face, and beside it
  the range, no contacts, "?NOT FOUND" and "READY.". It switches on as the page opens. The page
  a member reaches when only an admin may go there is the same console, with 403 on its face,
  who is signed in and "?FOR AN ADMIN".
- **Status.** The day's spend, a bar of twenty cells in brackets and the share of the limit,
  beside the same said in words.

How they are built, since the content policy allows no inline style and no script:

- A screen is HTML and CSS; the radar and the face are SVG. `views.radar_blips` works out where
  each plan goes on the dial (Jinja has no trigonometry), spreading them by the golden angle so
  none sits on another, each on one of twelve bearings. The sweep is a conic gradient turning on
  `--sweep`, and each blip's flare is timed to it by a negative delay: the `.b0` to `.b11` rules.
  The twelve bearings in `views.py` and those twelve rules change together.
- The spend bar is characters, `[####................]`, twenty cells worked out in the template:
  VT323 has no block characters, and a terminal would have drawn it this way.
- A screen that is only a picture is `aria-hidden`, and what it shows is always said in words on
  the page; Next up is the exception, because its words are the page's own. With less motion
  asked for, nothing switches on or blinks, the sweep rests at twelve o'clock and every blip stays
  lit. With more contrast, the blur, bloom and scanlines go. With forced colours, a screen that is
  only a picture is left out and Next up keeps its words in a plain box; on paper the same.

## Small things

The page is modern first and uses the old screens on purpose, so it is sparing with them. Beyond
the green screens there are only a few small details, each where it means something; none moves
for more than a moment, and none asks to be looked at.

- **Afterglow.** Whatever lights up (a card, a button, the box being typed in, the chat's box)
  does so at once and fades out over a second, falling fast and then lingering, as a tube's
  glow did. `--afterglow` and `--glow-in` in the stylesheet.
- **OK.** A form that worked says so the way an old machine answered a command: a small green
  OK before the words.
- **The caret** in any box is phosphor green, and **selected text** is in inverse video, dark
  on green.
- **Cursors rest.** The cursor after the name, and those on the screens, blink for a few seconds
  when a page opens and then stay lit, so nothing blinks at you while you read.
- **A lit tile.** The icon beside a page's title sits on a small screen of its part's colour,
  with a faint raster of its own.
- **Landing.** Where a link on the same page lands ("4 more on the radar", the settings index)
  lights up and fades.
- **On paper.** A printed page is green-bar paper, with tractor-feed holes and a perforation
  down both edges.

## Page by page

- **The bar.** On a phone the five everyday places (Home, Vera, Ideas, Plans, To do) are a tab
  bar along the bottom, the current one marked by a pill in its colour; Family, Status and
  Settings, the name of whoever is signed in (their own password) and signing out are icons at
  the top; Family and Settings are shown only to an admin, who alone may change them. From 52rem
  everything is one bar that stays at the top while the page scrolls. The conversation's place
  goes by her name, with the conversation's icon; with no persona it is Chat.
- **Home.** Signed the way her lines are (her screen, her name, the day), then the box to answer
  her in, its label her question, "What’s on your mind?", with the one word lit, and the ways to
  start under it; under those, how the conversation stands: what she said last (the last day's,
  cut to three lines) or what she is waiting on, and the way into the chat. All of it on the
  left, lit from below; **Next up** on the right, on a green screen beside the
  radar of everything coming (on a phone the words run round the scope, under the box). Then
  anything left to set up, what else is coming, what is left to do with a tick for each, and
  what was added lately, with a way to add one without her.
- **Vera** (the chat). A messaging layout under her name: her lines on the left beside her
  screen, the family's on the right with their initial; while she thinks, her waiting line at the
  foot of the thread and the box closed; the box under the newest line.
- **Ideas.** A grid of cards with the kind in colour, where, who, how long and the cost; the quick
  note that Chat turns into an idea is folded away so the list is on the first screen.
- **An idea.** The idea on the left; what you do with it (the calendar, plan it, record how it
  went) in a column beside the title; the place's details below.
- **Plans.** A list of dates, and a month with today in amber and plans as cyan slips; on a phone
  the month is the busy days as a list.
- **Things to do** (an open task is ticked off where it stands), **Family**, **Settings** (with an
  index and a save bar that stays in reach),
  **Status** (three monitors, then the day's spend on a green screen beside the same in words),
  **Sign in** (the mark's face on a green screen, then who you are and your password, or the one
  question while the family still shares a password), **For an admin** (the 404's console with
  403 on its face, for a page only an admin changes), **Not found** (a radar
  console with nothing on it, and one way home).
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
- `prefers-reduced-motion` stops the cursors, the glyphs falling on her screen, the breathing dots, the
  screens switching on, the face's blink, the radar's sweep, the 404's flicker, the afterglow and
  the landing glow. `prefers-contrast:
  more` lifts secondary text and edges and takes away the glow, the blur and the scanlines,
  the tiles' raster and her screen's included.
  Forced colours keep dots, boxes, dates and initials outlined, draw her screen as an empty
  outlined square, show a task's tick only when pointed at, leave out the screens that are only
  pictures, and keep Next up's words in a plain box.
- Words on a green screen are at least 1.2rem; dim phosphor is 7.6:1 on the tube, normal and
  bright more.
- The page works with scripts off; the only script is `static/ask.js`, the box's: it keeps what
  is being written, fills the box from the ways to start, and sends where the phone is. Without
  it the ways to start are links, and nothing typed is kept across a change of page.

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
- At most one green screen to a page, and only where it shows something true. VT323 and blur
  stay on the screens, and scanlines on the screens and in the home page's glow; everywhere else
  the page is sharp and modern.
- A new colour is measured against the others that share its pages, for typical sight and for
  deuteranopia and protanopia, before it is added.
- A new small thing has to mean something where it is, and may not move for more than a moment.
- Vera is never drawn: no face, figure, picture or expression, and the mark is never hers. Where
  she appears, her screen, and its glyphs never spell anything; where the page speaks of her,
  what she takes on, never what she is.
- A new colour, face, glow or motion goes here first, with the reason.

## Left for later

- **A light theme.** The page is dark on every device, by choice. A daylight version would be a
  line on the settings page, like everything else the family can change.
