# How the page looks, and why

The page's look is **Phosphor**: a modern family planner lit the way an old green screen was. It is
a present-day app first (calm charcoal surfaces, a friendly sans, line icons, generous space). The
old monitor survives as *light*, not costume: a phosphor-green glow on the few things that deserve
attention, and nowhere else.

The family want a page that only evokes the CRT (no pixel type, pixel icons, scanlines everywhere
or boot screen). The rule: **nostalgia shows up as light and small winks, never as a style the page
is imitating.** They also want a little texture, used sparingly, with 1980s green-screen monitors as
its model, so the page's few pictures *are* those monitors: a tube of dark glass in a plastic
surround, words in phosphor, sometimes a radar (see "Green screens").

One stylesheet (`src/familydb/web/static/style.css`), a handful of templates, three open-licensed
typefaces and one icon sprite carry it. The look depends on no script; the page's four are the
box's (`ask.js`), the bar menu's (`menu.js`), the wish lists' (`wishes.js`) and the mic's
(`dictate.js`).

This document records the look and why; it is not a fence. Design, feel and page structure are
meant to evolve, and anyone working on the app, an AI agent included, may change them without
asking (a layout, a page, a picture, a principle). Update this document in the same change. Only
the floors under "What does not move" stay put: they are about use, safety and cost, not taste.

The page is a way to talk to **Vera**, who plans the weekend, keeps the ideas and things to do and
puts things on the calendar. So Home opens with her question and the box to answer it, the
conversation goes by her name, and everything else is what she keeps, beside it. She is never drawn
(see "Her screen"). Every persona is a she, by decision (`docs/PERSONAS.md`), so the page's words
stay "she" and "her"; her name is the persona's in force, or the family's own if they renamed her.

## Two layers

**On top is what it does, and that is Vera**: talking to her and everything she keeps. It decides
what each page holds and in what order, and wins wherever the layers meet (principles 1, 10).

**Underneath is the look**: a visual language, kept to on purpose, that gives the page one coherent
feel and a personality. There is always one (colours, type and layout exist whether chosen or not),
so the questions are which, and how hard to push it. The language is Phosphor.

The look has flair where flair is useful and steps back wherever it could get between somebody and
what they came to do: reading, writing to her, deciding, changing something. Where it is in nobody's
way (an empty list, a thing just done, the way in, a missing page, the wait while she thinks) it
comes forward and should be fun. Pushed too far the page is an art project; held back everywhere it
is dull. The line is walked place by place, not found once.

**Where it stands.** The language is settled; how hard it is pushed, and whether it has enough
personality, is close and still tuned in small steps that cost nothing the page does. "Settled" says
where the family have got to, not what may be tried: what they like ("Why the green jumps") is what
a change weighs first.

## Principles

1. **A real, modern app first.** Layout, spacing, controls and type are those of a good present-day
   product: one clear action per place, 44-pixel targets, a tab bar under the thumb on a phone,
   sentence-case labels, readable type. Nothing retro may cost usability.
2. **The CRT survives as light.** Phosphor green glows only where attention belongs: the mark and
   cursor in the bar, her screen, the primary button, the box being typed in (Home's, faintly even
   at rest), the key word of Home's question, live status, finished tasks, and the green screens. A
   title's icon tile glows in that page's colour; amber glows for *today*. If everything glowed,
   nothing would.
3. **Colour says where you are.** Each part of the site has one colour, and each kind of idea has
   one; colour tells things apart, never decorates, and never speaks alone.
4. **Two voices, and a third on the screens.** DM Sans for everything read; DM Mono, sparingly, for
   the machine's small voice (times, figures, small labels above data, the name in the bar); VT323,
   a terminal's face, only on the screens and on hers.
5. **Keep the eye still.** A page's title, its one line of purpose and its one or two actions sit
   together at the top; what you do with a thing sits beside it. Her question and box are first on
   Home, with what is next beside them; the chat's box is under the newest line.
6. **Small things, here and there.** A handful of period details, each where it means something,
   none that moves for long or asks to be looked at ("Small things"). All motion stops for anyone
   who asks for less.
7. **The pictures are green screens.** The page's few pictures are old green-screen monitors, the
   one place it is hazy (blur, bloom, scanlines, the tube's dark edge). Each shows something true;
   at most one to a page. Her screen is the exception: not a picture but where she is, as small as a
   face, beside each of her lines.
8. **Accessible by construction.** Contrast is measured, focus always visible, every box labelled,
   motion, contrast and forced-colour preferences honoured, and reading, every form and sending a
   message work without a script.
9. **Vera is felt, not shown.** She is a real presence in her name, her words and her screen, and
   never a character: no face, figure or picture, and nothing that says what she is. The page's
   words about her say what she takes on, not who she is, and are few: no greetings, no quips,
   nothing said just to seem alive.
10. **Every part does work.** Nothing is only for show: her question on Home is the label of the box
    you answer it in, and the line on what she takes on is its placeholder. Pure decoration has to
    be small.

## Why the green jumps

The family like the green jumping off the black, and the glow: with that contrast and light the page
looks alive. Four things make it:

- **Bright colour on near-black.** A vivid green nearly as bright as the white words, on charcoal
  almost black: 15.2:1 against the page, 12.5:1 on the lightest surface. It reads as light coming
  off the screen, not paint.
- **A glow in layers, as a tube bloomed.** A glowing word has a tight halo and a wide faint one
  (`.glow`); the primary button a ring and pooled light (`--glow`); screen words three halos and a
  third of a pixel of blur. A soft halo is one way the eye tells something gives off light.
- **Light that behaves as a tube's did.** What lights up does so at once and fades over a second,
  live dots breathe, the radar's sweep leaves an afterglow.
- **Scarcity.** Glow is kept for where attention belongs (principle 2); everything else is
  near-white and quiet grey.

A change that greys the black, dulls the green, flattens the glow or spreads it wider dims all of
that, however small it looks.

## Colour

Surfaces are charcoal with a breath of green, the colour of a switched-off screen. Words are
near-white; green is light, not text. Ratios are on a card (`--surface`).

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#0b0e0d` | the page, with a faint green afterglow at the top |
| `--surface` / `-2` / `-3` | `#121615` / `#171c1a` / `#1d2321` | cards, hover, selected |
| `--field` | `#0e1211` | inside a box you type into |
| `--line` / `--line-2` | `#232a27` / `#2f3834` | hairlines and dividers |
| `--edge` | `#5c6862` | border of a box you type into: 3.1:1 on a surface |
| `--ink` | `#edf2ef` | text, 16:1 |
| `--ink-2` | `#bac5bf` | secondary text, 10:1 |
| `--dim` | `#919e98` | quiet text, 6.6:1 |
| `--faint` | `#7d8a84` | placeholders, ids and meta icons, 5:1 |

The colours are the phosphors of the time, softened: the green and amber of monochrome monitors and
the cyan, yellow, magenta and red of the first colour screens. Each is readable as text on every
surface (ratio against `--surface-3`, the lightest) and carries dark text (`--on-bright`) as a fill:

| Token | Value | Belongs to |
|---|---|---|
| `--green` | `#6dff9c` (12.5:1) | the brand and green screens, her screen, primary button, focus, what is next and live; Home, Vera's page, Status, Settings; outings |
| `--amber` | `#ffb850` (9.3:1) | the amber screen: Family, Memory and Your password, grown-ups' faces, restaurants, today, anything needing a look |
| `--cyan` | `#6cd4ff` (9.5:1) | Plans, the month on every date, going places: day trips and trips |
| `--lemon` | `#f7dc78` (11.8:1) | Things to do, open tasks, activities |
| `--lilac` | `#ae9bff` (6.8:1) | Ideas; events and kinds the family made up |
| `--pink` | `#ff9fd0` (8.5:1) | shows, and children's faces |
| `--orange` | `#ff956c` (7.4:1) | the seasons |
| `--red` | `#ff6b6b` (5.8:1) | only what went wrong or cannot be undone |

**Tuned apart.** Colours that share a page (above all the kinds on the ideas grid) are measured
against each other (CIEDE2000), for typical sight and simulated deuteranopia and protanopia. The
closest pair is 13.6 apart for typical sight, 5.5 and 5.2 for the other two. Hence amber near a real
amber phosphor, the seasons a pumpkin coral rather than a second amber, and trips sharing day trips'
cyan (a blue of their own would sit almost on events' lilac for many people). Every kind also
carries its icon and name.

**Sections.** `base.html` works out which part of the site a page belongs to from its view and puts
`in-ideas`, `in-plans` etc. on `<body>`; the stylesheet sets `--accent` from it. The title's icon
tile, the current place's icon in the bar, the chosen tab's icon and the page's links take
`--accent`.

**Kinds.** A kind label (`kind_label` in `_ui.html`) carries `kind-restaurant`, `kind-outing` etc.
in that kind's colour; a card holding one takes it for its hover glow.

## Looks

Phosphor is the default. A browser can wear another, chosen on the Look page (`/look`, in the bar's
menu, for anybody signed in, a kid included): **Midnight**, **Home Computer**, **Ink**, **Enamel**,
**Rail yellow** and **Fjord**, from the palette sheets the family looked at. A look changes colour
and nothing else; everything in this document describes Phosphor, with colours read from the look in
force.

**How it is built.** Every colour in `style.css` is a token; a look is a set of them. Phosphor
writes its tokens at the top of `style.css` in the names every palette sheet uses (`--paper`,
`--card`, `--ink`, `--band`, `--primary`, `--today`...); "Names the page uses" there maps the page's
older names (`--bg`, `--surface`, `--green`) onto them. `static/themes.css` holds one block per look
with day and night values together, `light-dark(day, night)`, so the page follows the device or is
held to one by the Look page (`data-mode` on `<html>`). A theme block is `[data-theme="rail"]`, not
`:root`, so a sample on the Look page is drawn in its own colours by putting its name on the sample.
A look names every token Phosphor does, since Phosphor's sit on `<html>` and would show through; a
test holds that.

**The choice is a cookie** (`fdb_look`, "rail.dark") set by the Look page's form, in this browser
only: a phone and a wall tablet may differ, and it costs the database nothing, so it is not a
setting, not a tool, and nothing the model can reach. Anything the cookie says that is not a look
here is Phosphor (`looks.parse`). The browser's own bar and scrollbars follow (`theme-color`,
`color-scheme`, from `web/looks.py`).

The looks and their ideas: Phosphor, charcoal with a breath of green, lit like a screen. Midnight,
made for night, a blue-black kitchen with each colour a lit window (its bar darker than the page,
by day too). Home Computer, an early-80s family machine: putty case, one orange key, brown-black
keyboard bar. Ink, almost no colour: white, black, untinted greys. Enamel, old enamel signs: warm
grey plaster, earthy colours, deep petrol bar. Rail yellow, station signage: crisp page, one signal
yellow, deep rail blue bar, the current page a yellow plate. Fjord, a pale northern sky over slate
water, slate indigo bar.

**In every look:** the green screens, radar, her screen and the mark are glass, dark with phosphor
green, so Vera is the one lit thing whatever the page wears (`--screen`, never the page's own
green). Colour never speaks alone, red is for late and what went wrong, and a kid sees the same
page in its colours.

**The paper looks are quiet.** Phosphor and Midnight tell the parts of the site apart by colour.
The other four keep colour for people and signals, as their sheets do, so a part of the site is not
coloured there (`--sect`: links are the look's link colour on every page); a kind of idea still
shows in its icon, name and colour. The glow is the look's `--bloom`: 1 on Phosphor, about a third
on the paper looks, none on Ink, so a hovered card casts a shadow, not a halo.

**Measured, in both modes.** For each look, by day and night, `tests/test_look.py` holds the floors
of "Accessibility": 4.5:1 for words on the page and a card (4:1 for a colour on a hover's wells),
3:1 for a box's edge and the focus ring, and words on each colour used as a fill. A look that
cannot keep them is not offered. A new look is a block in `themes.css` and a line in `looks.py`
(name, blurb, panel colour, which that test holds to the CSS) and nothing else.

**Not yet.** The palette sheets colour each family member (stripes on plans, a face in your own
colour); the page's avatars are one colour a look. Building it wants the family's say on who gets
which. There is no household default look: each browser chooses.

## Type

**DM Sans** (variable, optical sizes 9-40) for everything read; **DM Mono** (400, 500) for times and
figures, small uppercase labels above data, the month on a date, the name in the bar and the tools a
reply used; **VT323** for words on a green screen and the glyphs on hers, nowhere else. All three
are SIL Open Font License, served from `static/fonts/` (about 110 kB) because the content policy
allows fonts from this site only. DM Mono has just enough typewriter to carry the old screen without
dressing up as it. VT323 (the DEC VT320's face) is blurred a little and blooms on a screen, and
where it is to be read is never set smaller than 1.2rem (its letters sit low in their line).

Page titles: 700 weight, -0.025em, 1.9-2.6rem. Home's heading is her question, the box's label,
smaller (1.3-1.6rem) since it sits in the box's frame. Section headings 1.2rem semibold. Body 1rem
at 1.6. Paragraphs stop at about 60 characters.

## Shape and space

- Cards: 16px corners, a hairline edge, the faintest top highlight. Buttons and boxes: 10px corners,
  44px tall. Pills are fully rounded; an idea's status is a coloured pill.
- Primary button: phosphor green with a soft glow; secondary a raised neutral; quiet an outline;
  dangerous red text on an outline until hovered.
- Spacing on a quarter-rem scale; cards 1.25rem apart; content at most 74rem wide, the chat 52rem so
  the eye does not cross the screen between a question and its answer.

## Icons

Line icons from [Lucide](https://lucide.dev) (ISC, `static/LICENSE-icons.txt`), one pinned release,
gathered into one sprite (`static/icons.svg`) by `scripts/icons.py`, used through the `icon()` macro
in `_ui.html`: 1.75 stroke, in the colour of the words beside them; beside words hidden from screen
readers, alone given a label. To add one, put its name in `ICONS` in the script and run
`uv run python scripts/icons.py`; never edit the sprite, favicon or home-screen icons by hand.

**The mark** is the page's own: a little monitor with a smile, on the same grid and stroke. It is
the favicon, the mark in the bar (where it glows) and the home-screen icon: phosphor green on
charcoal filling the square (the phone rounds the corners itself and would show black through
anything transparent), with a margin that round masks leave alone. A phone takes no SVG there, so
the script draws PNGs from the same shapes. It is FamilyDB's, never Vera's face: she has none.

## Her screen

Vera is never drawn. Where the page shows her there is a small screen full of words nobody can
read, as if busy, between a 1980s terminal and the Matrix's falling code (`presence` in
`_ui.html`): columns of VT323 glyphs, the newest of each run bright and the rest dim, scanlines
across, blurred past reading. The stylesheet draws the glyphs from one sixteen-row pattern; each of
her lines shows another part of it (`v0` to `v3`), so a thread is not a row of copies. While she
thinks the glyphs fall a row at a time, as a character display moved them; on Home they fall for a
moment as the page opens; elsewhere they are still. Nothing is shown typing.

It sits beside her lines in the conversation, beside her name on Home, on the tile of her page and
where the settings speak of her. It never gets eyes, a mouth, a silhouette or an expression, no
picture of anybody stands in for her, and its glyphs never spell anything. With no persona it is
simply the bot's.

## The parts

Each lives in `_ui.html`, `_ask.html` or `_settings.html`, which show the markup. What is decided:

- **Page head** (`page_head`): breadcrumbs for a nested page, the icon on a tile of the page's
  colour (her page: her screen instead), title, one line of purpose, actions on the right.
- **The box** (`_ask.html`; the new frame's is `_composer.html`, whose chat box also has **Add a
  photo**, a plain file field under the words): the one place anybody writes to her, on Home and at
  the chat's foot,
  always posting to the chat: message on top; who is sending, "Send where I am" and Send along the
  bottom; one frame that lights up while you write. In the chat it says "Message Vera" and, while an
  answer is on its way, is closed and says when it opens. On Home its label is her question,
  "What’s on your mind?", printed above where you write, the page's heading and a way in (a tap
  puts you in the box); while empty it says what she takes on. On a phone Send shows only its arrow.
  Under it on Home (and in an empty chat) are the **ways to start**: three quiet pills, the day's
  question and two instructions left for the rest to be typed.
- **A line of the conversation** (`chat_line`): hers left beside her screen, the family's right with
  their initial; everything she says drawn the same way, long answer or "Done."; the tools a turn
  ran sit under it in the machine's voice. **Waiting** (`waiting_line`) is the last line while the
  newest message waits: her screen and name, the bubble dashed because the words are the page's,
  not hers. Under a reminder of hers, the buttons Telegram shows (Done, In an hour, Tomorrow) are
  a row of small quiet buttons inside her bubble, one row per task, gone once it is done; under a
  reply whose turn changed something, a quiet Undo, gone once used or a day on. A form's notice
  carries the same Undo at its right end when what it did can be taken back.
- **The tick** (`tick`): an empty box beside an open task, a 44-pixel target, showing the tick it
  will make when pointed at and marking the task done where it stands.
- **Date** (`chip`): a calendar leaf, the month in cyan above the day; today amber. **Relative time**
  is a small pill beside the date, so a wrapped line never starts with a separator.
- **Live dot**: green, breathing; Status's lights are lit, hollow (red) or half lit (amber) dots with
  words beside them. **Meter**: an SVG bar (widths are attributes; no inline style), always with its
  figure written beside it. **Notices**: a small green OK for what a form said, a red dot for an
  error.
- **Green screen** (`crt`) and **radar** (`radar`): see below.
- **A setting** (`box` in `_settings.html`): label, a small green CHANGED when set on the page, the
  box, help a screen reader hears with it. Empty, a box shows the default it falls back to; a
  dropdown's first choice says it in words, "Default (Thursday)", never "thu" or "true". Long lists
  are grouped (time zones under their region, each as its place first so typing a city finds it,
  then its offset that day). A stored value a dropdown does not offer is offered too, so a save
  never loses it. Related settings sit in a panel; fine-tuning is a folded `<details>` that opens
  itself when one of its boxes is wrong and says, folded, how many were changed.
- **Section card** (on `/settings`): icon, name, how the part stands, an arrow; a part needing a look
  says so in amber, in words. Tiles do not glow: nine lit tiles would light nothing.

## Green screens

The page's pictures are 1980s green-screen monitors (an IBM 5151 or a Zenith on a desk, a terminal
in an office, the screens in *WarGames*), each drawn as the thing itself, not a costume for the page.

**The monitor.** A dark plastic surround, lit from above, a thicker chin with a power light. In it,
the tube: dark glass, a faint glow at its middle, corners and edges falling into shadow as a curved
tube's did. Over the picture: scanlines, a little light off the glass, the tube's dark edge.

**The picture.** VT323 in the phosphor's colour, blurred a third of a pixel and blooming, in three
strengths: dim for what matters least, normal, bright for the one thing to read first. A heading is
inverse video, dark on a green bar. A link is underlined and turns inverse when pointed at, as a
menu's choice did. A block cursor waits after the last line. The spend screen turns amber near the
limit, as other monitors did, and red past it.

**The radar** is a program the screen runs: range rings at one, two and four weeks, "now" at the
middle, each coming plan a blip, nearer the middle the nearer its day. The sweep turns once every
eight seconds with an afterglow; each blip flares as the sweep passes and fades until it comes
round; the next plan's blip is brightest and pings. On Ideas the same scope is a map: home at the
middle, north up, each saved place a blip on its real bearing and as far out as the drive there,
rings at a quarter of an hour, three quarters and two hours by road, the nearest pinging.

Five, at most one to a page:

- **Home, Next up.** The next plan beside the radar of everything coming. Its words are the page's
  own, not a picture of them: read out, the title a link, "4 more on the radar" leading on.
- **Sign in.** The mark's face, awake, and "READY." with the cursor waiting. It switches on as the
  page opens (the picture opening out of a bright line) and blinks now and then.
- **Not found.** A radar console: an empty scope still sweeping, 404 on its face, beside it the
  range, no contacts, "?NOT FOUND" and "READY.". It switches on as the page opens. An admin-only
  page reached by a member is the same console with 403, who is signed in, their role and "?FOR AN
  ADMIN".
- **Status.** The day's spend: a twenty-cell bar in brackets and the share of the limit, beside the
  same in words.
- **Ideas, On the radar.** Where the listed places are, with how many, the nearest and furthest,
  each a link. It follows the filters and is drawn only when home is set and something listed is on
  the map. Its words are the page's own, and each card says its drive and direction ("about 19 min
  south of home"), so the map shows nothing the page does not say.

Built without inline style or script:

- A screen is HTML and CSS; the radar and the face are SVG. `views.radar_blips` places each plan on
  the dial (Jinja has no trigonometry), spread by the golden angle so none sits on another, each on
  one of twelve bearings; `views.places_radar` puts each place on its true bearing and times its
  flare to the nearest of the twelve. The sweep is a conic gradient turning on `--sweep`; each
  blip's flare is timed to it by a negative delay in the `.b1` to `.b11` rules (the first bearing
  needs none). The twelve bearings in `views.py` and those rules change together.
- The spend bar is characters, `[####................]`, twenty cells worked out in the template:
  VT323 has no block characters, and a terminal would have drawn it this way.
- A picture-only screen is `aria-hidden` and what it shows is always said in words on the page (Next
  up's words are the page's own). With less motion nothing switches on or blinks, the sweep rests at
  twelve o'clock and every blip stays lit. With more contrast, blur, bloom and scanlines go. With
  forced colours (and on paper) a picture-only screen is left out and Next up keeps its words in a
  plain box.

## Small things

A few small details beyond the green screens, each where it means something. They sit where people
read and do, so none moves for more than a moment or asks to be looked at.

- **Afterglow.** Whatever lights up (card, button, the box typed in) does so at once and fades over
  a second, fast then lingering, as a tube's glow did (`--afterglow`, `--glow-in`).
- **OK.** A form that worked answers as an old machine did: a small green OK before the words.
- **The caret** is phosphor green; **selected text** is inverse video, dark on green.
- **Cursors rest.** The cursor after the name and those on screens blink a few seconds when a page
  opens, then stay lit, so nothing blinks at you while you read.
- **A lit tile.** The icon beside a title sits on a small screen of its part's colour with a faint
  raster.
- **Landing.** Where a link lands ("4 more on the radar", "Change a key" on Status) lights up and
  fades.
- **On paper.** A printed page is green-bar paper (black on white, a pale green band on every other
  line) with tractor-feed holes and a perforation down both edges. The month on the fridge.

## Page by page

The templates show the layout; these are the decisions.

- **The bar.** On a phone the everyday places (Home, Vera, Ideas, Plans, To do, and Kids’ lists or
  My list for a kid) are a bottom tab bar, the current one a pill in its colour; Memory, Family,
  Status and a last tile are icons at the top (no Memory or Status for a kid; Family only for an
  admin, who alone may change it). From 52rem it is one bar that stays at the top. For an admin the
  Status icon carries a light while something only an admin can fix goes on (`web/status.light`):
  amber with a ▲ for a look, red with a ■ while the family cannot be answered, said in words to a
  screen reader. A parent's never lights: the fix is not theirs. The last tile opens a menu (a
  `<details>`, working with scripts off): for an admin the Settings gear, listing every settings
  page, then who is signed in, Your password and Sign out; anybody else sees their own name and only
  those three. That keeps the bar to four icons however many settings pages there are. The
  conversation's place goes by her name (Chat with no persona), shown only to a role that may talk
  to her. Kept on a phone's home screen the page opens full-screen (`display: standalone`, status
  bar black), so the tab bar and the page's own ways back are all there is.
- **Home.** Signed as her lines are (her screen, name, the day), then the box, its label her question
  with the one word lit, the ways to start, then how the conversation stands: her last line (the
  last day's, cut to three lines) or what she is waiting on, and the way into the chat. All on the
  left, lit from below; **Next up** on the right, a green screen beside the radar (on a phone the
  words run round the scope, under the box). Then anything left to set up, what else is coming, what
  is left to do with a tick each, and what was added lately with a way to add one without her. What
  a role may not do is not offered (`familydb/roles.py`): without the chat, the day and the page's
  name stand where her question would; without changing things, each tick is an empty box; only an
  admin sees what is left to set up.
- **Vera** (the chat). Her lines left beside her screen, the family's right with their initial;
  while she thinks, her waiting line at the foot and the box closed.
- **Ideas.** A grid of cards: kind in colour, where, who, how long, cost. The quick note Chat turns
  into an idea is folded away so the list is on the first screen. An idea's page has what you do
  with it (calendar, plan it, record how it went) in a column beside the title.
- **Plans.** A list of dates, and a month with today amber and plans as cyan slips; on a phone the
  month is the busy days as a list.
- **Settings.** A card to each part, saying how it stands and marking in amber what needs a look;
  each part a short page, the others listed down the side where there is room, with one Save in a
  bar that stays in reach while its form is on screen. A box that offers a list (a company's models
  with their place in its lineup and price; the chats the weekend ideas can go to) is a real
  dropdown, since a phone barely shows a typed box's suggestions, ending in "Another…", which opens
  a box to type one the list lacks. The stylesheet shows that box only while "Another" is chosen
  (`:has()`); a browser without it shows the box always, read only when "Another" is chosen. General
  ends with where the page is served and a guide to giving it a name, in numbered steps with
  commands to copy; typing the name fills it into them and saves nothing, since how the page is
  reached is the server's to change. Messages opens with what she sends unasked: each kind as a
  light, when it goes, what it costs and how often it went in the last month, with the way to its
  switch; then the latest, each folded to a line that opens to the words sent.
- **What she remembers**: each memory under whom it is about, with its source and a way to forget
  it; adding one, and what was forgotten, folded below.
- **Status**: what needs an admin first, when anything does, edged in red (a model going or gone with
  a secondary button to put the suggested one in, posting the settings page's own form); three
  monitors; the day's spend on a green screen beside the same in words; Models and prices (a light
  per list the daily check read, a table of changes in the last thirty days, and the judgements,
  each with what it said and why and a button to put in what waits or put back what it changed); for
  an admin, the week's activity, each line a link to that message's or lookup's history (what was
  said, every call as a row of figures, each tool folded to a line opening to what it was given and
  gave back).
- **Sign in**: the mark's face on a green screen, then who you are and your password, or the one
  question while the family still shares a password.
- **Lists**, for whoever may change things (in the sidebar, and first under For the family in the
  phone's menu, for the shop): a card per list, the shopping list first, each thing
  with the same tick as a to-do, a box to add to it (one a line), and what was got folded away
  under "Got", struck through, with Put back beside each and one button to clear them.
- **Your password** also holds **Notifications on this device**: one sentence of what a notice
  says (that she has a message, never her words), a line saying how it stands on this device, and
  one button to turn it on or off. With scripts off the line says that it needs them; on an iPhone
  or iPad that cannot, it says how to add the page to the Home Screen.

## Accessibility

- Text contrast is at least 4.5:1 everywhere (see the tables); boxes you type into have a 3:1 edge.
  Placeholders are hints, never labels.
- Focus is a ring in the look's focus colour (phosphor green on Phosphor, ink or a blue on the
  others) on everything, offset from the control.
- Every box has a label joined by `for`; the chat's message box has one for screen readers only,
  since the box says what it is for.
- Nothing is said by colour alone: the chat tells voices apart by side and face; status lights
  differ in shape and carry words; kinds and statuses are written out.
- `prefers-reduced-motion` stops the cursors, the glyphs falling on her screen, the breathing dots,
  the screens switching on, the face's blink, the radar's sweep, the 404's flicker, the afterglow
  and the landing glow. `prefers-contrast: more` lifts secondary text and edges and removes the
  glow, blur, scanlines, the tiles' raster and her screen's. Forced colours keep dots, boxes, dates
  and initials outlined, draw her screen as an empty outlined square, show a task's tick only when
  pointed at, leave out picture-only screens, and keep Next up's words in a plain box.
- Words on a green screen are at least 1.2rem; dim green phosphor is 5.8:1 at the tube's brightest,
  normal and bright more.
- Reading, every form and sending a message work with scripts off; each script only adds, and what
  is missing without it:
  - `dictate.js` (while the family has it on): a round mic inside the right-hand end of each box that
    takes words, and beside Send; pressed it turns phosphor green and its ring breathes (still under
    reduced motion) while the browser writes down what is said. Without it there is no mic; a phone
    keyboard's own still works.
  - `wishes.js` (wish lists only): a three-line grip to drag a wish into place, sending the wish's
    own Move form. Without it the Top, Up and Down buttons inside each wish do the same.
  - `ask.js` (the box): keeps what is being written, fills the box from the ways to start, sends
    where the phone is, looks again for an answer only while nobody is writing. Without it the ways
    to start are links, "Send where I am" is not shown, nothing typed survives a page change, and
    the page looks again with a meta refresh.
  - `menu.js`: closes the bar's menu on a click elsewhere or Escape; otherwise its own button does.

## What does not move

- The content policy is `default-src 'self'` with `style-src 'self'` and `script-src 'self'`: no
  inline `style` attributes, `<style>` blocks or inline script, and no fonts, pictures or scripts
  from elsewhere. A computed size is SVG with attributes.
- The accessibility above. A new colour is measured against the others that share its pages (typical
  sight, deuteranopia, protanopia) before it is added, and a new look keeps the contrast floors by
  day and night (`tests/test_look.py`).
- Nothing from an idea, a place or a fetched page is marked safe in a template.
- No page view is a model call: the page reads what is stored and words its own lines, and only a
  message sent asks a model (`test_browsing_asks_nothing_of_a_model`).

## The look as it stands

Today's choices; their reasons are above. Change any when a better page needs it, and say why here.

- A few pieces of markup are what the tests read: `class="panel card"` on each card of the ideas and
  restaurants lists, `class="said"` with the text right after it, `<summary>Move it</summary>` on a
  movable plan, `class=" today"` on today in the month. Change them and the tests together.
- Class names are shared across the whole stylesheet: check a new one is not taken (`.bar` is the
  top bar; anything else given it takes the bar's rules).
- A change to the look says whether it is in a place where somebody reads, writes, decides or
  changes something (the look steps back) or in nobody's way (it comes forward), and why.
- One green screen to a page, where it shows something true. VT323 and blur stay on the screens, and
  scanlines on the screens and in the home page's glow; elsewhere the page is sharp and modern.
- A new colour, face, glow or motion is written down here, with the reason, in the change that
  brings it. Trying one on a branch needs no entry until it stays.

## Left for later

- **A light Phosphor.** Phosphor has no day, by choice: the dark is half its look, and the same
  green on white is 1.3:1. The daylight looks are their own languages ("Looks").
- **A look for the household.** A default the family sets for browsers that have not chosen would be
  a line in `store.settings` and `web/fields.py`; not yet needed.

## A kid's screen

A kid signs in to the same page in the same Phosphor look (the family asked for limited changes,
`docs/WISHES.md`): less of it, worded and laid out for her. The rule is one natural place to say
anything, and each page showing only what is hers or the family's, with nothing to filter, count or
choose between. Vera sorts what she says, so the page never asks which box a thing belongs in.
Every simpler page is drawn for whoever may not `browse` (`familydb/roles.py`), never by asking
about a role.

- **Her bar** has no Memory, Status, Family or Settings.
- **Home** is her box with Vera, its label her question and its placeholder what she brings
  ("Something you’d like, a question, something fun to do…"), with no ways to start (they would be
  words to say instead of her own). Then Next up, and My list (pink, the kids' colour since the
  Family page first gave it to their faces): a parent's latest yes lit green with sparkles, a no
  quiet beside a heart, the top three of her everyday list, and how far off Christmas and her
  birthday are. Under that, coming up and her things to do side by side; no ideas added lately, no
  restaurants.
- **Things to do** is "My things to do": her open ones as a checklist drawn as Home draws it
  (`checklist` in `_ui.html`), what and when in words. She ticks each off herself, here and on Home
  (`own_tasks`), and is told "Done: Pack swim bag!" with no number. No search, status, count or
  reminder workings.
- **Plans** is one list of what is coming, with no List and Month to choose between.
- **Ideas** is plain cards (kind, title, where), each a link: no search, filters, count, radar, ids
  or how an idea is looked up.

Nothing on her screen offers what she may not do: empty lists ask her to tell Vera, never to add an
idea or plan one.

**The word.** The page says "list" and "I’d like", not "wish": the family found "wish" too
aspirational. The code, tools and `docs/WISHES.md` still say wish, since that is what the model is
told and renaming it would change every request.

**Her list** (`/wishes`, `wishes.html`) opens on one big box, "Tell Vera anything", full width and
headed in the size of Home's question: the chat's own box (`_ask.html`), posting to her
conversation. There is no second form for adding to her list: she says it her way ("can I get a
kite", "let's go to the zoo") and Vera sorts it onto the list, into an idea or reminder, or just
answers. A parent's view of her list has the add form instead, and so does a kid who may not talk to
Vera, as the one way left to add.

Under it, one line to each wish (a line of buttons under each made the list hard to read): the grip
on the left (drawn only while `wishes.js` runs, and outside the line's summary so a drag never opens
it), its number in a round pink badge, the one she wants most filled in, what it is, a small pencil
when it has a note, a chevron. Tapped, the line opens (a native `<details>`) to the note, Top (from
third place down), Up and Down, moving it to another list, taking it off, and for a parent the
answer. Every line and button is at least 44px, for a finger on an iPad. What was turned away is
headed "Not on your list" and says what to do next ("a house rule: ask a parent"), not the
grown-ups' word. A parent sees the same lists as the Kids’ lists, with Yes! and Not this time inside
each, and a card on Home with each kid's.
