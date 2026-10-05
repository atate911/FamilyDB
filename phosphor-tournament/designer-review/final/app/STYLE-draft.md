# How the page looks, and why

The web page's look is called **Kitchen Table**: the family's table, with the family's things on
it. Warm cream paper, a soft serif for headings, a plain and very readable face for everything
else, and each person in a colour of their own wherever they appear. FamilyDB is the small
machine that sits on that table, and it shows as a pane of dark glass with green light on it.
That pairing is the whole idea: **warm paper is the family's; phosphor on charcoal glass is
FamilyDB's and Vera's.**

The rule behind every page fits in a line: **one plain sentence first, cards below it, and a
person's colour wherever that person appears.** Every status is a sentence, not a code.
Saturated colour means a person (or Vera's green). Red means late or broken.

Everything here is carried by one stylesheet (`static/style.css`), a stylesheet for each other
theme (`static/themes/`), a handful of templates and macros, self-hosted fonts and one icon
sprite (`static/icons.svg`). None of it needs a script: every page and every form works with
scripting off, and the few small scripts only make things smoother.

This document is a record of the look as it stands and why, not a fence around it. The design,
the feel and the structure of the pages are meant to evolve with the app, and whoever is working
on it, an AI agent included, is free to change any of them without asking first: a new layout, a
new page, a new theme, a principle rewritten. Update this document in the same change, so the
next person knows what the look is and why. Only the floors under "What does not move" stay put,
because they are about people being able to use the page, it being safe, and what kids see, not
about taste.

The page is a way to talk to **Vera**, and she does what it offers: plans the weekend, keeps the
ideas and the things to do, puts things on the calendar. So the first thing on Home is her
question and the box to answer it, the conversation goes by her name, and everything else is
what she keeps, laid out beside it. She is never drawn (see "Her screen"). Every persona is a
she, by decision (`docs/PERSONAS.md`), so the page's words about her stay "she" and "her"
whichever is chosen, and her name is the one the persona in force gives, the family's own if
they have renamed her.

## Two layers

The look is built in two layers, and keeping them apart is what lets the family change it.

**Underneath are the tokens the parts use.** A component never asks for "cream" or "green". It
asks for what a colour is *for*: `--paper` for the page, `--card` for a card, `--ink` for words,
`--edge` for the border of something you press or type into, `--primary` and `--link` for the
family's actions, `--vera` for Vera's things, `--alert` for late or broken, `--p` for the person
a thing belongs to. These names (listed under "Colour") are the only colours any rule may use. A
colour written anywhere but a theme file is a mistake; `tests/test_themes.py` and the CSP check
keep it that way.

**On top, a theme gives each name its value**, once for day and once for night. Each theme is one
small stylesheet, `static/themes/<name>.css`; Kitchen Table, the default, is
`static/themes/kitchen-table.css`. `style.css` holds no colour of its own, only what every theme
shares: the type, the sizes and the spacing, and the brand's glass and phosphor. Because the parts only ever ask for a job, a new
theme needs no change to any template, and a change to a part reaches every theme at once.

A theme is colour only. It never changes the layout, the type, the sizes, the words or what a
page holds. And two things are the same in every theme, because they carry meaning rather than
taste: **Vera's glass and phosphor**, so she is recognisably herself whatever the page looks
like, and **red, which means late or broken** and nothing else.

What the page does still comes first. The look is there so the family can read, write to her,
decide and change things without effort. Where it is in nobody's way (an empty list, the way in,
a page that is not there, the wait while she answers) it may come forward a little. Pushed too
far, the page is an art project; held back everywhere, it is generic.

## Principles

1. **A real, modern app first.** One clear action per place, 44-pixel targets, a tab bar under
   the thumb on a phone, sentence-case labels, 17-pixel body text. Nothing in the brand may cost
   usability.
2. **One plain sentence first, cards below it.** A page opens with its title and one line of
   purpose; Home and Status open with a sentence that says how things stand ("Roller rink
   tomorrow, and three to-dos are late"). Then the cards. Every state is words: "6 days late",
   "Not connected", "Needs a look".
3. **Saturated colour means a person.** Each member of the family has a colour, on their face,
   their messages, their plans and their dots. Kinds of idea are neutral, told apart by an icon
   and a word. The only other strong colour is Vera's green. Colour is never the only cue: every
   person marker carries an initial, or the house for Everyone.
4. **One meaning per signal.** Red is late or broken. Amber is "set this up" and "needs a look",
   and only those. Mint is "all good" or "done". Dashed means "not yet". Something merely off,
   resting or for your information is neutral.
5. **Paper is the family's, glass is FamilyDB's.** Phosphor on charcoal glass appears only for
   the brand, for Vera and for something live. Never on the family's own things.
6. **Three faces, and a fourth on the glass.** Fraunces for headings, Atkinson Hyperlegible for
   everything read, Fraunces figures for money and clock times. JetBrains Mono only on glass.
7. **What you came for is on the first screen.** On Home, Vera's box and what is next; on a list
   page, the list. Options, filters and rarer forms fold away under `<details>`.
8. **Accessible by construction.** Contrast is measured in both appearances of every theme,
   focus is always visible, every box has a label, sizes are in rem, motion, contrast and
   forced-colour preferences are honoured, and nothing needs a script.
9. **Vera is felt, not shown.** She is a real presence, in her name, her words and her screen,
   and never a character: no face, no figure, no picture of her. The page's words about her say
   what she takes on, not who she is.
10. **Every part does work.** Her question on Home is the label of the box you answer it in, and
    the page's `h1`. The radar's dots carry the names of the cards above them. Anything that is
    only decoration has to be small.
11. **One word for each thing**, on every page, in her replies and in her Telegram messages:
    Everyone, No date, Connected, Added, Weekend suggestions, looking things up. Errors are
    written as the fix ("Give the idea a name"), never "invalid".

## Why it feels like a kitchen table

What the family like is that the page feels like theirs: warm, calm, a little homely, and still
clearly a machine they can trust. Four things make that.

- **Paper, not white.** The page is cream (`#F6F1E7`), the cards a lighter cream (`#FFFCF6`),
  with hairlines in warm sand. It reads as a table with cards laid on it, not a screen of panels.
- **A soft serif on top, a plain face underneath.** Fraunces, its softness turned up on the big
  title, gives a page its voice; Atkinson Hyperlegible, drawn for people who find reading hard,
  carries everything that has to be read.
- **People in colour, everything else quiet.** Because kinds, cards and controls are neutral, the
  family's colours are what the eye finds first: who is going, whose turn, whose message.
- **One pane of glass.** By day the deep-green Ask card and Vera's small screen are the only
  dark things on the page, so they read as the machine on the table and the eye goes there first.

A change that whitens the paper, colours the neutral parts or spreads the glass wider dims all of
that, however small it looks.

## Themes

Kitchen Table is the theme FamilyDB starts with, and the one this document describes. A theme
is colour and nothing else: it can't move a thing, change a face or a size, or reword a page.

**What a theme is.** One file, `static/themes/<name>.css`, with a short header (its name, a line
about it, whether it is made light first or dark first, and the two colours for the browser's
bar) and three blocks of values, all keyed on its own name: the first appearance, the second as
the device asks for it, and the second as somebody chooses it. Every token in the contract is in
both appearances: the surfaces, the words, the rules, the panel down the side (`--side`,
`--side-ink`, `--side-hi`, `--side-mark`, `--side-link`, which let a theme make it dark), the
family's action, today, Vera's colours and her Ask box, the three meanings, the eight people with
their soft, ink, mark and the letter on their avatar (`--pN-on`), and the shadows.

**What no theme may touch.** Vera's glass and phosphor live in `style.css`, the same everywhere,
so she is herself whatever the page looks like. Red means late or broken in every theme, and
nothing else may be mistaken for it. Phosphor green is hers: only her own colours, today, Send
and "done" may come near it. Her Ask box is always dark with light words.

**How a page knows which.** The server writes on `<html>` `data-theme="<name>"` and
`data-mode="auto"`, `"light"` or `"dark"`, links the one theme file, and writes the matching
`color-scheme` and `theme-color`. Auto follows the device; light and dark override it. No script,
no inline style, and no flash of the wrong colours.

**Who chooses.** The family's theme and Light, Dark or Match this device are set in Settings ›
General, under "How it looks". Each person may choose their own on their **You** page; its first
choice, "The family's theme", follows the family's. A person's own choice wins, and changes
nothing but their own screen, on every phone and computer they sign in on. Kids may choose too.
The sign-in page uses the family's, since nobody is known yet.

**The pickers** are plain forms that list whatever theme files are installed. Each theme is a
card, a label round a real radio (`label.theme` › `.theme__card`): a tiny Home drawn by day and
by night, the theme's name and its line. Each half of the tiny Home carries `data-theme` and
`data-mode`, so it is drawn by the theme file itself and can't drift from it. The chosen card is
ringed in ink with a tick; the one in use says "✓ In use". Under them, Light, Dark and Match this
device (`fieldset.choices.appear`). Save posts, redirects, and the page comes back in the new
theme.

**Before a theme ships**, `tests/test_themes.py` checks it: every token present by day and by
night and nothing else in the file; every text pair 4.5:1 or more and every control edge, mark
and focus ring 3:1 or more; letters on each avatar at 4.5:1; the eight people at least 6 apart
(CIEDE2000), in normal vision and under simulated protanopia, deuteranopia and tritanopia; late
red at least 6 from every person, done, the action colour and today, under the same four; and
every other colour well away from phosphor. `_kit/theme-check.py --sheets` draws each theme's
palette sheet, with every swatch and every measurement, for the family to look at before choosing.
Kitchen Table's own people fall short of the colour-blind floor in three places; the test records
those as known until the family decides, and fails anything worse.

## Colour

These are Kitchen Table's values. By day the page is paper. At night it is **phosphor at
night**: charcoal glass instead of paper, cream ink (not white, so the dark stays warm), Vera's
things in phosphor, amber for what needs a look, coral for late, and people in their colours,
lightened.

| Token | Day | Night | Used for |
|---|---|---|---|
| `--paper` | `#F6F1E7` | `#0C100F` | the page |
| `--paper-2` | `#EFE7D7` | `#121816` | the sidebar, tracks, neutral tiles, "Off" tags |
| `--card` | `#FFFCF6` | `#161D1B` | cards and rows |
| `--field` | `#FFFFFF` | `#1B2321` | inside a box you type into, tick rings |
| `--ink` / `--ink-2` / `--ink-3` | `#1D2526` / `#4B5657` / `#596263` | `#EEE8DA` / `#CBC5B6` / `#A3A69E` | words, secondary words, quiet words |
| `--line` / `--line-2` | `#E2D8C4` / `#D3C6AC` | `#24302C` / `#33413C` | hairlines, decorative only |
| `--edge` | `#8A806C` | `#7E8C86` | the edge of anything you press or type into |

**Vera's green.** `--vera` is a deep Kitchen Table green by day (`#1E5C4F`) and phosphor
(`#6DFF9C`) at night: her name and her bubble's rim. The current place in the nav is
`--side-mark`, her green in Kitchen Table. Her surfaces are
`--vera-soft` and `--vera-line`. The **Ask card** is her glass, deep green day and night
(`--ask-bg` `#12382F`, `#0F2A22` at night). At night it also has the brightest edge on the page
(`--ask-rim`) and its box a real edge (`--ask-edge`). Today's date takes `--today-bg`, her green
by day and phosphor at night, because today is the live thing on a calendar.

**The family's actions are not Vera's.** Links (`--link`) and the one primary button on a page
(`--primary`) are Kitchen Table green. At night the button stays green (`#2D7462`) and links
turn a lighter green (`#8BD3B4`); neither is ever phosphor, because phosphor is hers.

**Send.** `--send` (`#F2C14E`, sun yellow) is the Ask card's Send and its focus ring, and
nothing else: the one warm accent, kept for the one action that matters most.

**Tones**, each always with a word:

| Tokens | Day | Night | Means |
|---|---|---|---|
| `--ok`, `-soft`, `-line` | `#2B7148` on `#DDEFE2` | `#7FE3A5` on `#11261B` | Working, Connected, Added, done |
| `--warn`, `-soft`, `-line` | `#7E5108` on `#FBEFD0` | `#F5B94A` on `#2A2112` | only "set this up" and "needs a look" |
| `--alert`, `-soft`, `-line` | `#B3381F` on `#F9E1D9` | `#FF8B74` on `#33191A` | late, broken, form errors |

Red is words and thin rules (a to-do's 4-pixel late edge, a box's error edge), never a fill
behind the family's things.

**People.** The family's colours are eight slots, `--p1` to `--p8`: blue `#2F5D9B`, purple
`#7B4790`, raspberry `#A83C80`, amber-brown `#A2560E`, teal `#0B6A84`, indigo `#5448B0`, olive
`#59661A` and cocoa `#6F4E37`. Each has a `-soft` (bubbles, event fills), an `-ink` (a name on
its soft) and a `-mark` (dots and bars on a card). The server gives each new person the next
slot (`person.slot`); a template never picks a colour, and no class is named after a person.
`.p1` to `.p8` set `--p`, `--p-soft`, `--p-ink` and `--p-mark`, which avatars, bubbles, events
and dots read. At night the soft becomes a tinted charcoal and the ink and mark lighten, so marks
stay at 3:1 or more on a card. **Everyone** (`.p0`) is always neutral grey, with the house icon.

**Tuned apart.** White letters on every slot are 5.4:1 or more. The slots were checked pairwise
under simulated deuteranopia and protanopia: raspberry, not a red-pink, so a person never reads
as "late" (CIEDE2000 58 from `--alert`), and cocoa rather than a second magenta. Eight colours
cannot all stay apart for every eye, which is why colour is never the only cue.

**Glass** is the brand's, the same in every theme: `--glass` (`#0E1312`; `#070A09` at night),
`--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--glass-alert` (coral, "can't
answer"), `--phosphor` (`#6DFF9C`) with `--phosphor-dim` and `--phosphor-glow`, `--cursor`
(`#1B9A55` on paper, phosphor at night) and `--vs-halo`.

## Type

| Face | Where |
|---|---|
| **Fraunces** 600, variable optical size and softness | headings and card titles, the wordmark |
| **Atkinson Hyperlegible** 400, 700 | everything read: body, buttons, labels, the nav, tags, messages, idea titles, the radar's labels |
| **Fraunces figures** 400, 600 | money and clock times, and numbers that stand alone or line up |
| **JetBrains Mono** 400 | words on dark glass, and nowhere else |

All are open-licensed and served from `static/fonts/`, because the content policy lets fonts
come from this site only. Fraunces is a soft, warm serif; Atkinson Hyperlegible was drawn so the
letters people confuse (I, l and 1; O and 0) look different, which matters on a page kids read.

**The one Fraunces choice.** `h1` and the wordmark turn the softness axis to 100
(`font-variation-settings: "SOFT" 100`), rounding the ends of the strokes. At 42 pixels it is
warmer and more its own; at body sizes it would not show. No other heading uses it. Small
Fraunces headings get their spacing back, or "Add a to-do" reads "Adda to-do".

**Figures.** Fraunces Figures is a FamilyDB-built subset of Fraunces' digits and money
punctuation, kept out of the body stack by `unicode-range`. Its tabular cut (`--font-num`,
`.num`) is for numbers that stand alone or line up: date tiles, money, the 30-day figures,
calendar days, wish ranks, setup step numbers. In sentences, **every amount and clock time** is
wrapped in `.fig` by one filter on the rendered page, so no template has to remember, and set in
Fraunces Text Figures, the same digits but proportional, so "1 pm" has no gap. So "$0.00 of your
$2.00" and "7:48 pm" share one open zero. Other numbers in a sentence stay Atkinson, whose
slashed zero is a help to reading. `.code` keeps model names, keys and codes in Atkinson.

**The scale** is in rem, so a reader's larger text grows every step and the order holds:

| Token | Size | Use |
|---|---|---|
| `--t-xs` | 13 px | capitals only: tab labels, `.overline`, a date tile's weekday and month |
| `--t-sm` | 14 px | the floor: tags, badges, hints, names on messages; the mono on glass |
| `--t-meta` | 15 px | meta lines, small body, the eyebrow over a title |
| `--t-md` | 17 px | body (line height 1.5); row and idea titles in 700 |
| `--t-lede` | 18 px | the sentence under a title (16 on a phone) |
| `--t-h3` / `--t-h2` / `--t-h1` | 19 / 23 / 42 px | headings; card titles are `h2`; `h1` is 32 on a phone |
| — | 28 / 34 / 21 px | a date tile's day: normal, Next up, small |
| `--t-display` | 44 px | the big money on Status (other figures 30–32) |

Times follow the family's clock setting, with no leading zero in 12-hour time ("9 am"), and a
number is held to its unit by a no-break space ("18 min"). Paragraphs stop at about 62
characters.

## Shape and space

- **Cards** (`.card`): 18-pixel corners (`--r-lg`), a hairline edge, the faintest shadow. The Ask
  card is the same shape in deep green.
- **Rows, boxes, banners and tiles**: 12-pixel corners (`--r-md`); calendar events 8 (`--r-sm`).
- **Buttons** are pills, at least 46 pixels tall. The primary is green with white letters, one per
  view; the ordinary one an ink outline; the quiet one a hairline on card; the dangerous one red,
  and only for what cannot be taken back.
- **Avatars** are round, at 24, 32 and 40 pixels. Round means a person, which is why Vera's
  screen is square. **Tiles** are rounded squares at 40 and 56.
- **Spacing** runs on a 4-pixel scale, `--s1` to `--s8`: 4, 8, 12, 16, 20, 24, 32, 48.
- **Targets** are 44 pixels or more (`--target`). The tick is a 44-pixel target round a 32-pixel
  ring.
- **Widths.** A 252-pixel sidebar and content up to 1080 pixels; a setting-up step in a 760-pixel
  column. The phone layout is 820 pixels and below.

## Icons

Simple line icons on a 24-unit grid: a 1.8 stroke, round caps and joins, in the colour of the
words beside them, at 16, 20 and 24 pixels. They live in one sprite (`static/icons.svg`) and are
used through the `icon()` macro: `{{ icon('car', 'sm') }}` gives
`<svg class="icon icon--sm" aria-hidden="true"><use href="/static/icons.svg#i-car"/></svg>`. An
icon beside words is hidden from screen readers; one standing alone sits in a control that has a
name. A new icon is drawn on the same grid and stroke, so the set stays one hand.

Kinds of idea are told apart by icon and word on a neutral tile (`.tile`): utensils for a
restaurant, a mountain for an outing, a suitcase for a trip, a ticket for a show. Health areas
use the same tile in a tone (`--ok`, `--look`, `--broken`, `--vera`).

## Her screen

Vera is never drawn. Where she speaks there is a small pane of glass, as if she were typing: a
**rounded square** (never round, since round means a person), a **lit rim**, a few short **lines
of light**, the newest brightest, and her **signature, a lit prompt `>▮`** in the bottom-left
corner. The prompt is the same at every size; small sizes have fewer lines, not smaller ones. It
is inline SVG (`svg.vs`, from the `vera_screen(size, state)` macro), crisp, with no blur and no
scanlines, so it reads at 24 pixels on a phone.

| Size | Class | Lines | Where |
|---|---|---|---|
| 24 px | `.vs--sm` | 1 | small mentions, such as "Suggested by Vera" |
| 32 px | `.vs` | 2 | beside each of her messages, and the waiting and failed bubbles |
| 40 px | `.vs--lg` | 3 | the Ask card, and her rows on Home and Status |
| 56 px | `.vs--xl` | 3 | a kid's empty chat, the one place she is introduced |

**Ready**, it has a 3-pixel halo (`--vs-halo`), Kitchen Table green by day and phosphor at
night, so it reads as lit glass on cream and as a screen, not a hole, on charcoal.
**Answering** (`.vs--busy`), the lines light one after another and the cursor blinks, only while
a reply is on its way. **Can't answer** (`.vs--off`), the light goes out: rim, lines and prompt
turn control-edge grey, the cursor goes hollow, the halo goes, and the words beside it say why.

The screen is always `aria-hidden`, with her name in text beside it. It never gets eyes, a mouth,
a silhouette or an expression, and its lines never spell anything.

## The mark and the name

**The mark** is FamilyDB's, not Vera's: a little monitor with a smile, one 2-pixel round stroke on
a 24-unit grid, phosphor `#6DFF9C` on a charcoal `#0E1312` rounded square. The square is the
mark's own glass, so it sits straight on cream with no frame, and is the same file at night. It
is never recoloured, never used without its square, and never stands in for her. It is the
favicon (16 pixels hand-pixelled, so the eyes and smile stay apart; 32; SVG), the home-screen
icon (180 and 512), 34 pixels in the sidebar, 30 in the phone bar, 20 in the footer and 64,
glowing, on a pane (`.pane__mark`). It keeps a quarter of its size clear on every side.

**The wordmark** (`.wm`) is "FamilyDB" in Fraunces 600 at full softness, followed by a **lit
cursor** (`.wm__cur`), a block `.42em` by `.86em`. On paper the letters are ink and the cursor a
darker green (`--cursor`, 3.2:1 on cream, as a mark); on glass and at night, cream letters and a
phosphor cursor with its glow. It is always beside the mark, and the link round both is named
"FamilyDB, home".

## The parts

Class names are the API. Each part has one anatomy and modifiers for its variants, and a macro
(`card`, `banner`, `tag`, `badge`, `avatar`, `vera_screen`, `todo`, `composer`, `field`,
`choices`, `rank`, `idea_card`, `empty`, `flash`, `error_summary`) emits it, so no template
builds one by hand. Person classes are slots (`.p0` to `.p8`), never names.

- **Page head**: a crumb (`.crumb`) on a page inside another, the title, one line of purpose
  (`.lede`) and the page's one or two actions.
- **Card** (`.card`, `__head`, `__foot`): every group of content. `.card--setup` is the one
  warm-tinted card, for what is left to set up. A card can fold (`details.card.fold`); `--danger`
  gives it a red title and edge.
- **The Ask card** (`.ask` round a `.composer`): "Vera" and her screen (`.ask__who`), her
  question as the box's label and the page's `h1` (`.ask__q`, "What's on your mind?"), the box,
  Send in sun yellow, who it goes to ("Goes to the family chat as Sam."), and her last line from
  the past day with "Continue with Vera" (`.ask__last`).
- **Composer** (`.composer`): writing to her anywhere else, one per page: "Writing as Sam", the
  box, Send. While she answers, rests or cannot answer, it is closed, with a slim banner saying
  why.
- **Health pill** (`.pill-health`, `--busy`, `--rest`, `--down`): Vera's state, for grown-ups.
- **Buttons** (`.btn`, `--primary`, `--quiet`, `--sm`, `--danger`) and **text buttons**
  (`.textbtn`, `.linkbtn`, `.more`, "All plans ›").
- **Badges** (`.badge`): a count with a word in the nav. Loud only for what needs someone now:
  `--late` ("3 late", red) and `--act` ("1 to decide", an ink outline). "2 to rate" is `--quiet`.
- **State tags** (`.tag`), one vocabulary: `--ok` Working, Connected, Yes!; `--better` Could be
  better, Not connected (an outline, a hollow amber dot); `--look` Needs a look (amber, a "!");
  `--broken` Not working; `--off` Off, Optional, No backup; `--when` Tomorrow, Planned; `--been`
  Went Thu 1 Oct, Not this time; `--pending` (dashed) No answer yet, Not done yet; `--surprise`
  "Surprise · hidden from Maya".
- **Avatar** (`.av` with a slot): every mention of a person, their initial in white, the name
  always beside it. Everyone is the house.
- **Item row** (`.items` › `.item`, lead · body · trail, `--boxed`, `--divided`): every list that
  is not to-dos or idea cards.
- **To-do row** (`.todos` › `.todo`): `--compact` on Home, `--late` (a 4-pixel red edge and "6
  days late"), `--done` (struck through, left in place), `--ro` (a kid's). **The tick**
  (`.tick`) is a button in its own POST form.
- **Date tile** (`.dt`): the weekday in capitals, the day in Fraunces figures, the month. Today's
  has a green head (`--now`).
- **Meta line** (`.meta`): owner · due · reminder · drive, under a title.
- **Banner** (`.banner`): a message with at most one action. Neutral by default, `--ok`, `--warn`
  (set this up, once a page), `--alert`; `--hero` and `--slim`. A **flash** (`.flash`,
  `role="status"`) follows a one-tap action, with Undo, and takes focus; an **error summary**
  (`.errors`, `role="alert"`) heads a form that came back. A **note** (`.note`) is one quiet line
  for a connection that is not set up, on a page that is not about it.
- **Fields** (`.field`, `__label`, `__hint`, `__error`, `.req`, `.opt`): the label above, an
  error above the box, the hint below. **Choice pills** (`.choices` › `.choice`): no default where
  a choice must be made. `.disclose` folds options; `.seg` switches a view and wraps rather than
  scrolls.
- **Chat** (`.chat`, `.convos`, `.room`, `.scroller` › `.thread`): her bubbles on card with a
  green rim, the family's in their own colour's soft with the name in its ink. A **receipt**
  (`.receipt`) in her message says what she just did ("Added to Plans · Sun 4 Oct, 1 pm · for
  Maya and Theo"). **Weekend suggestions** (`.suggest`) are a short list in one bubble, each with
  a "Plan it" form. The **privacy line** (`.privacy`) says who can read the conversation, at
  every width.
- **Faces** (`.faces`): "How did it go?", three labelled faces, for grown-ups.
- **Empty state** (`.empty`): what will appear and how to start it. **Locked** (`.locked`): "Ask
  a parent".
- **Key/value** (`.kv`), **data table** (`table.data`, scrolling sideways inside its box, never
  the page), **meter** (an SVG bar, its figure always written beside it).
- The parts of a list page, of Settings and of setting up are under "Page by page"; the glass
  parts (`.pane`, `.mapband`, `svg.vs`, `.mark-fdb`) under the next section.

## The glass and the phosphor

FamilyDB's look is the green screen of the 1980s, kept to a sprinkle: **a pane of dark glass with
green light, set on cream paper.** The layout, the parts and every contrast check are the same
with it or without it.

**The rule.** Glass and phosphor appear only where one of three things is:

1. **the brand**: the mark, the wordmark, and the brand moments;
2. **Vera**: her screen, and the Ask card's deep-green glass;
3. **something live**: the health pill when it has something to say, a reply on its way, the
   caret in her box, today's date.

Never on the family's own things: names, ideas, to-dos, wishes, plans, and the buttons and links
that act on them. **The mono only on the glass.** Every touch says something true. No dark page
in light mode, no screen curvature, no vignette, no heavy scanlines, no pixel font.

**Panes** (`.pane`, `--center`): charcoal glass with a 1-pixel `--glass-line` rim and faint
scanlines, words in `--glass-ink`, its small machine lines (`.pane__line`) in phosphor mono. One
to a page at most, never as a card style:

- **Signing in**: the mark, the wordmark, "awake, Saturday 3 October" and "Ready.", then the
  form on paper.
- **A first empty day**: "FamilyDB is set up and awake. Welcome, Sam. This is your family's
  table.", then the empty cards on paper.
- **The grown-ups page**: the mark alone at 64 pixels, glowing; the words stay on paper.
- **Not found**: "404 · nothing on the radar" in the mono, then "Not found", "There's nothing at
  that address." and Back to the start.
- **Not part of your role**: "403 · signed in Maya · role kid", then the refusal's own words.
- **A first sign-in**: "first sign-in · Maya", over "Choose your own password".
- **A tool's own words** on an admin's history of one message (`.pane--code`): machine text, so
  on glass, in the mono.

**The health pill.** When Vera is ready it is not glass at all: "Vera is ready" in soft green,
Atkinson, a still dot. Only when there is something to notice does it turn to glass and the
mono: **"Vera is writing back"** in phosphor, its dot breathing until the reply lands; **"Vera is
resting until midnight"** in quiet glass ink, a hollow dot; **"Vera can't answer right now"** in
coral, a square dot.

**The radar**, on Ideas only, the one instrument in the app, in its own band after the cards
(`section.mapband` › `details.mapband__fold` › `.instrument__pane` › `svg.radar`). Home is the
middle and north is up; each looked-up idea is a phosphor dot on its true bearing, as far out as
the drive there. The scale gives the first half hour 70 % of the radius, with rings at 15 and 30
minutes, 1, 2 and 3 hours. Each dot carries the idea's short name ("Pumpkin patch"), the first
words of its card's title, so a kid can match it; ideas in the same direction are fanned a few
degrees apart. Its labels are Atkinson, because kids read them. It is drawn twice from the same
data, 860 × 440 for the desktop and 360 × 400 for a phone, each label placed per idea so nothing
sits on a compass letter. The SVG is `aria-hidden`: the cards are the list, and each already
says its drive and direction in words. On a phone it folds behind "Show the map". If every idea
is inside one ring, the cards stand alone.

**Glow** (`--phosphor-glow`, `--vs-halo`) is kept for the writing-back pill, the panes, her
screen and the wordmark's cursor: not the calm pill, not bubbles (hers included), not cards, not
buttons.

## Small things

Each sits where it means something, and none moves for long.

- **The cursor waits.** The wordmark's cursor blinks twice, slowly, then stays lit, the way a
  terminal waits.
- **Her caret** in her box is the wordmark's cursor green.
- **Today is lit**: a filled green disc on a faint wash, never a ring (a ring means focus).
- **A tick stays.** A to-do ticked off stays where it was, struck through, with a flash and Undo.
- **Not yet is dashed**, and nothing else is: her bubble while she thinks, an idea not looked
  up, a wish with no answer, a kid's to-do not done.
- **A spill-over day** on a phone shows its month in small capitals under the number ("28" over
  "SEP"), so it never wraps.
- **Every page ends** on the family's line beside the mark: "A little less planning. A little more
  together."

## On a phone

The phone is its own layout, not the desktop stacked, at 820 pixels and below.

- **The bars.** The sidebar becomes a 56-pixel top bar (the mark and wordmark, the pill for
  grown-ups, and the avatar, which opens the account menu, with a dot when something inside needs
  checking) and a fixed tab bar of five, 68 pixels plus the phone's safe area (`--tabbar-total`).
  The current tab has a 3-pixel green bar on its top edge. `scroll-padding-bottom` keeps the
  focused control clear of it.
- **Tabs by role.** Grown-ups: Home, Chat, Ideas, Plans, To do, with Wishes, What Vera knows,
  Status, Settings, Family, You and Sign out in the account menu. A kid: Home, Chat, Wishes,
  Plans, To do, with Ideas, You and Sign out in hers.
- **The first screen.** On Home the greeting is one small line, the Ask card one row (the box and
  an arrow Send), and the next plan sits above the tab bar. Cards are capped ("3 more plans this
  month"), in the order Ask, Next up, To do, How did it go, Wishes, Ideas.
- **Lists first.** Ideas become compact rows. To do starts with one row to add (box and Add), who,
  when and the reminder folded under it. Filters always fold.
- **Plans**: the month, the Month/List switch, then a month at a glance: each day with plans a
  whole-cell link with up to three markers (an initial in the person's colour, the house for
  Everyone, a hollow ring for a past plan) and a full spoken label.
- **Chat is an app-height room**: the conversation pills, the privacy line, a scroller that opens
  at the newest message, the box pinned above the tab bar, and a pinned "Earlier messages" bar
  with a fade. Shorter than 560 pixels, it falls back to page scroll.
- **Nothing scrolls sideways** at 390 pixels or 320, except the conversation pills, as one row.
  Choice pills wrap. A short label that replaces a long one hides the long one with the `.sr`
  clip, never `display:none`, so it stays the control's name.

Kept on a home screen, the page opens full-screen, with the mark as its icon.

## Page by page

- **The sidebar** (desktop): the mark and wordmark, the pill for grown-ups, then the nav, each
  place with its icon and a badge where something needs someone. An admin's ends with **Behind the
  scenes**: Status, Settings, Family; a parent sees Status. At the foot (`.me`), who is signed
  in, **You** and Sign out, a POST button.
- **Home.** A small greeting and the day, then the big line, what is coming and what is late,
  with links. Then the Ask card. Beside it **Next up** (the next plan with a large date tile, its
  time, drive and who, then "After that") and To do; under them what was just added to Ideas and
  the wish lists. For an admin, "Finish setting up", once; for grown-ups, "How did it go?" and
  "Vera today", what was spent against the limit. What a role may not do is not offered.
- **Chat.** "Chat with Vera". On the desktop the conversations down the side (the family's, and
  the kids', which grown-ups may read along) and the room beside them, growing with the latest 30
  messages; "Earlier messages" reaches back. While a reply is on its way, a dashed bubble of hers
  with her busy screen, "Thinking about the last message…", a "Check for her answer" link, and
  the box closed. A message that did not get through has a red edge and "Didn't reach Vera · Try
  again".
- **Ideas.** Search and Filter first, "Save a thought for later" folded (it goes to the chat:
  "Organise in the chat"), then the cards (`.ideas` › `.idea`) three across: kind, title, who,
  drive and direction in words, tags; `--unknown` is dashed until looked up. Then the radar.
- **An idea.** The crumb, its status and number, who suggested it, the description; the place's
  details; "At a glance" (`.kv`); "Look it up again"; "Record how it went" folded; "Change this
  idea" and "Drop it". Adding or changing one is the same form, "Everything else" folded.
- **Restaurants.** A card per place (`.places` › `.place`): cost, today's hours, a summary,
  drive, who, and "Details may be out of date" when stale.
- **Plans.** The month (`.cal`): each plan a bar in its one person's colour with a 20 % tint;
  several people or Everyone in grey with each face or the house; two to a day, then "+N more".
  A plan over days is one bar (`.len2` to `.len7`), split at a week's edge (`.ev--to`,
  `.ev--from`). A one-line key under it, then Coming up and "How did it go?". The list
  (`.plans-agenda` › `.plan`) is the next 90 days by month, then Recently.
- **To do.** Overdue first, under a red heading; then the rest, No date last; a tick and Edit on
  each. The add form: the box, who and when, then **Add** as a full-width bar on the desktop.
  Nobody is picked; the server says so if nobody is.
- **Wishes.** For grown-ups, each kid's three lists (Every day, Christmas, Birthday, each with
  its countdown) at a glance, what Vera flagged, and the answers. One kid's page has the full
  cards (`.wishes` › `.wish`) with the answer form: a word for the kid, then **Yes!** or **Not
  this time**.
- **What Vera knows** (grown-ups). Each fact (`.mem`) under whom it is about, with "Must", "A
  guess" or "Until …", where it came from in the family's own words, and Forget.
- **Family** (admin). Everyone with role, age, how Vera reaches them and how they sign in; "Add
  somebody" beside the list. Taking somebody off for good is folded in red behind "I'm sure". A
  new starting password is **shown once** in a dashed, selectable box that takes focus. Somebody
  who wrote to the bot and is not known yet is a dashed **knock** (`.knock`).
- **Status.** The verdict as a sentence in a hero banner. Spent today: a meter, "$0.00 of your
  $2.00 daily limit", and a line for a usual day. The last 30 days as three figures, on one row
  from 360 pixels. "How each part is doing": Vera, Spending, Sign-in, Backup, Telegram, Google
  Calendar, Looking things up, each a sentence, a tag and at most one action, worked out once
  (`health(area)`) so no two pages disagree. For an admin, recent activity, each line a link to
  that message's history: the words, the model calls as a table, each tool folded open on glass.
- **Settings** (admin). A row per page (`.slist` › `.srow`) with how it stands, "Needs a look"
  only when the page would say so. Each page (`.settings-layout`) has the crumb, every other page
  down the side above 1000 pixels, and its groups as cards (`.sgroup`). A box (`.setting`) shows
  a quiet "changed" when set here and help that ends with the range; a dropdown's first choice is
  "Default (…)"; a key shows only how it stands, never its value. A list (`.pick`) ends in
  "Another…", whose box shows only while chosen. Fine-tuning folds, saying "2 changed". One Save
  per form, in a bar that stays in reach (`.save-bar`). Commands for the server sit on a plain
  well (`pre.cmd`), never on glass. What she sends unasked is a light each, filled or a ring,
  always beside On or Off.
- **Setting up.** Seven steps, each with a number or a tick and Done, Needed, Recommended or
  Optional; each step page has the steps along the top (`.setup-progress`), "Step 3 of 7 · about
  5 minutes", the form, and Back and Next at the foot.
- **You.** "How it looks for you", then your password.
- **Sign in.** The pane, then your name and your password, both typed. The family is never
  listed, and a wrong name gets the same answer as a wrong password. While the family still shares
  one password, every box asks who it is from, and nobody is picked.

## Accessibility

Contrast is measured from the tokens (WCAG 2.2), by day and by night. Some of Kitchen Table's:

| Pair | Day | Night |
|---|---:|---:|
| `--ink` on `--paper`, body | 13.9 | 15.7 |
| `--ink-3` on `--card` / `--paper-2`, quiet | 6.1 / 5.1 | 6.9 / 7.3 |
| `--link` on `--card` | 7.6 | 9.9 |
| `--on-primary` on `--primary`, the button | 7.8 | 5.5 |
| `--on-send` on `--send`, Send | 9.3 | 9.6 |
| `--ask-ink` on `--ask-bg`, the Ask card | 12.9 | 12.5 |
| `--alert` on `--card`, late | 5.9 | 7.5 |
| `--phosphor` on `--glass` | 14.7 | 15.6 |
| `--edge` on `--field` / `--card`, control edges | 3.9 / 3.8 | 4.6 / 4.9 |
| white on a person's colour | 5.4–7.4 | same |
| a person's mark on `--card` | 5.3–7.3 | 8.4–10.5 |

Every text pair is 4.8:1 or better, every control edge 3.8:1 or better. At night the Ask card's
rim is 4.6:1 against the page, its box's edge 4.4:1.

- **Focus** is a 3-pixel ring on everything: ink by day, cream at night, sun yellow in the Ask
  card, phosphor on glass (14.7:1, where ink would be 1.2:1). A "Skip to content" link shows on
  the first Tab.
- **Labels.** Every box has one; hints and errors are tied with `aria-describedby`, a wrong box
  gets `aria-invalid` and a thicker red edge, values are kept, and a fold holding an error opens.
  Every control is named in full: "Mark done: Call the dentist about Theo", "Move Ice skates up".
- **Never by colour alone.** Late says "6 days late"; tags carry words; events carry a spoken
  label and their people's initials; the pill's dot changes shape.
- **The chat thread** is `role="log"`, named and focusable. One `h1` a page, headings in order.
- **Sizes.** Targets 44 pixels; type 14 pixels or more (13 only for capitals), in rem.
- **Motion.** Nothing blinks for more than five seconds. Only things that end on their own move
  longer: her busy screen, the typing dots and the writing-back dot, while a reply is on its way.
  Under `prefers-reduced-motion` nothing moves at all.
- **Forced colours.** Whatever is shown by a background alone (the current place, segments,
  choices, themes, tags, the pill, ticks, today) gets a real border.
- **Reflow.** Nothing scrolls sideways at 320 pixels or at 200 % zoom.
- **Words** are written for about grade 4 to 7, and the kids' pages are read aloud for tone.
- **Scripts add, never require.** `ask.js` asks quietly for her answer while one is pending (and
  removes the page's refresh), keeps an unsent message, and offers "Share where I am with this
  message"; `dictate.js` adds a mic beside the boxes that take words, where the family allows it;
  `wishes.js` lets a wish be dragged up or down its list, as well as moved with its buttons. A
  `password.js` that adds Show beside a password box is welcome. None is needed to read, send or
  change anything.

## What does not move

- **The content policy**: `default-src 'self'; style-src 'self'; script-src 'self'; font-src
  'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'`. No inline `style`,
  no `<style>` block, no inline script, no `on*=` attribute, nothing from anywhere else. A size
  worked out from data is an SVG attribute (the meter's `<rect width>`) or a class (the
  calendar's `.c1` to `.c7`, `.len2` to `.len7`, `.lane1` to `.lane3`). CI fails on `style="` or
  a `<script>` without `src` in `templates/`.
- **Works with scripting off.** Every page and every form: tick, Undo, add, change, rate, answer
  or move a wish, sign in, search, send a message. Forms post, redirect and come back with a flash
  and an anchor to the list they changed, and carry a CSRF token. The chat opens at the newest
  message by `column-reverse`. While a reply is pending the page refreshes itself, backing off
  (3 seconds, then 5, then 10) and never after 60, when the message is marked failed.
- **Kids never see costs or workings**: no pill, no money, no limit, no models, no company names,
  no setup, no Status. A kid is told "You've sent all 20 of today's messages", or that Vera is
  resting "until tomorrow".
- **Presents stay hidden.** A gift idea or a surprise is left out of a kid's pages entirely: no
  row, no count, no greyed item. Lists are filtered for the viewer (`visible_to(viewer)`) before
  anything is counted. Grown-ups see it tagged, always by name: "Surprise · hidden from Maya".
- **Themes are colour only**, and keep Vera's glass and phosphor and red for late or broken.
- **The accessibility above**, in every theme, by day and by night. A new colour or theme is
  measured against the others on its pages, for typical sight and for deuteranopia and
  protanopia, before it is added.
- Nothing from an idea, a place or a fetched page is marked safe in a template.
- No page view is a model call: only a message sent asks a model
  (`test_browsing_asks_nothing_of_a_model` holds it).

## The look as it stands

These are today's choices, each with its reason. Change any of them when a better page needs it,
and say why here.

- Class names are shared across the stylesheet and are the API: check a new one is not taken.
- A colour is a token, and a token is a job. A part that needs a colour no token gives is a
  question for this document first, so every theme can answer it.
- One primary button a view, one "set this up" a page, one pane a page, one instrument in the
  app. Each is scarce so it keeps its meaning.
- Kinds of idea are neutral, so the family's colours are the colour on the page.
- Money and clock times are one figure style everywhere, by a filter rather than by memory.
- The mono stays on the glass; the glass stays where the brand, Vera or something live is.
- Vera is not drawn, and the mark is not hers. Where she appears, her screen; where the page
  speaks of her, what she takes on.
- The look leans on a few facts the server keeps: each person's slot; who set a to-do and who
  owns it; who a plan is for; a wish's rank, answer and who gave it; whom a present is hidden
  from; a kid's daily message count.
- A new colour, face, glow, motion or theme is written down here, with its reason, in the change
  that brings it. Trying one on a branch needs no entry until it stays.

## Left for later

- **A few states have no Kitchen Table form yet** and borrow the nearest part: a parent reading a
  kid's conversation as a page of its own; the lines for a message held, retrying or lost; the
  mic for speaking instead of typing; Status's full model and price tables; Telegram's
  "connecting" and "refused"; Google's consent and calendar choice.
- **Paper.** There is no print style yet. A month for the fridge would be the first.
- **A 30-day spending chart**: it needs daily figures, and would be SVG `<rect height>`s.
- **For the family to decide**, not the look: whether a kid may tick her own to-dos or rate a plan
  (her row would become the ordinary `.todo`, and faces would appear on her Home; no new part is
  needed); a private chat for each parent; whether a kid may share where she is.

## A kid's screen

A kid signs in to the same page, in the same Kitchen Table look: nothing is drawn differently for
her, there is only less of it, and it is hers. She may choose her own theme on her You page
("Only your own screen changes. Nobody else sees it.").

Her nav is Home, Chat with Vera, My wishes, My to-dos, Plans and Ideas. There is no pill, no What
Vera knows, no Status, Settings or Family, and her footer has no version. **Her Home** opens with
her line ("Roller rink tomorrow with Theo, and Sam said yes to your sketchbook and brush
pens!"), then the Ask card, which goes to her own chat and says how many messages she has left
today, then **Next up for you** (only her plans and Everyone's), her wishes, her to-dos and new
ideas.

**Her chat** is only her own: "Just you and Vera." It says that Sam and Alex can read it, at
every width. Empty, it rests on Vera's screen at 56 pixels and "Nothing said here yet." She is
told gently when 5 messages are left, and when they are used up the box closes until tomorrow.
There is no "Share where I am".

**Her to-dos** are only her own, and read-only (`.todo--ro`): the lead is the face of whoever set
it, never a box or a ring, then when it is due, "Set by Alex", a dashed "Not done yet" and **"Tell
Vera I did it"**, a link that fills her chat box. A late one says "Was due Sun 27 Sep". **Ideas
and plans** she can read but not change: no faces, no Add, no Edit, and "Ask a parent" where a
change would be.

**Her wishes** are hers to keep: Every day, Christmas and Birthday, each with its countdown, most
wanted first. Each card leads with its number and has Top, Up, Down, "Which list" and Move, and
Take off, every button at least 44 pixels for a finger on an iPad. Answers come back in words
(Yes! or Not this time, with the parent's note); what Vera turned away is under "Said no to",
with the reason and "Asked a parent". "Wishes aren't secret: Sam and Alex see your lists."

A page that is not hers gets a kind refusal in plain words, never an error: the grown-ups page for
Settings, setting up and the family list, and the 403 pane for the grown-ups' pages ("This page
is for the grown-ups. Ask a parent if you need it.").
