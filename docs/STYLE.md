# How the page looks, and why

This is FamilyDB's design: what the page looks like, the few ideas that make it work, and how to
draw any page from them. It was worked out on Home, screen by screen, until Home looked
*designed*: professional, modern, calm, a little technical, and unmistakably one thing. **Home is
the model.** Every other page is drawn the way Home is, and where a page and this document
disagree, the page is moved, not the document.

It is being built now. Home is agreed (in mockups of the real app); the stylesheet, the parts and
then the pages follow, one change at a time. Until a page has moved, it still wears the older parts,
and the code is behind, not this document. When the last page has moved, this paragraph goes.

This document records the design and why, so the next person (an AI agent included) can extend it
without asking. Anything here may change when a better page needs it: change it in the same
change, with the reason. Only the floors under "What does not move" stay put, because they are
about people being able to use the page, its safety, and what kids see, not about taste.

## The idea

**One thing leads. Everything else is quiet, and ready when it is wanted.**

The page is a way to talk to Vera, so on Home the one thing is her box and its Send. Every other
part (what is next, what is left to do, what she knows) is laid out around it in one quiet voice,
smaller, lighter and flatter, so the eye goes to the box first and finds the rest when it looks.

Two sentences say how it looks:

- **Color is the family's.** People are the color on the page: each person's own, on their
  marks. The looks give the page its paper or its dark glass.
- **Type is the machine's.** One engineered face, Saira, at a few widths; precise mono numerals;
  short labels in wide capitals. It reads like a well-made instrument: technical in a quiet way,
  the ghost in the machine, never a costume, never playful.

## Why it works

These are what turned a page of independent parts into one design. Each is a reason, and each is
what to check when a new page "feels off".

- **Constraint makes harmony.** Four type sizes, two weights, two tones, one spacing scale. With
  so few choices, any two things are either clearly the same or clearly different, and the page
  reads as one piece. Before, almost nothing was the same size as anything else, and it looked
  assembled.
- **The same job looks the same everywhere.** A date, a person, a section label, a row, a count:
  each has one shape, wherever it appears. The family learns the page once.
- **Hierarchy comes from contrast, not size.** The box leads because everything around it stopped
  competing, not because it grew. Making the main thing louder never works as well as making the
  rest quieter.
- **Rhythm over decoration.** Equal columns, one left edge, one spacing scale and hairlines hold
  the page together. Frames and fills were mostly noise.
- **Marks over sentences.** A small consistent mark (an initial in a circle, a number in a dot, a
  square to tick) is read in a glance. The words behind it are still there for a screen reader
  and on hover.

## Principles

1. **One thing leads.** Every page has one focal element and at most one primary action. It is
   the largest, highest-contrast thing on the page, and nothing else glows.
2. **Quiet by default.** Supporting content is smaller, lighter and flatter than the main
   content. Something that needs attention asks with a signal (amber, red), never by getting
   bigger or bolder.
3. **Roles, not sizes.** Every piece of text is one of four roles: a label, words, a heading or a
   display. A new element picks a role; it never invents a size, a weight or a gray.
4. **Marks, with words behind them.** Prefer a small mark to a sentence or a pill, and give every
   mark its words: a person's name, the count's meaning, the tick's "Mark done: …". A mark is a
   shorthand for words, never a replacement for them.
5. **Say what is needed.** A row says what a thing is and when, in one line under its title.
   Anything more is on the thing's own page, one tap away.
6. **Structure over frames.** Group with alignment, spacing and hairlines. A card is for a thing
   that should feel like an object (a plan list, the box), not for every group.
7. **A signal means one thing.** Glow means "talk to Vera here". Amber means "needs a look". Red
   means late or broken. Green means working or done. A person's color means that person. Mono
   means a figure or a code. Capitals mean a short label. Nothing else uses them.
8. **Same job, same part.** Reuse a part before drawing a new one; a new part is written down
   here.
9. **Vera is felt, not shown.** She is her name, her words and her screen, never a face or a
   figure (see "Her screen").
10. **Usable first.** Nothing in the look may cost reading, reaching or understanding. The floors
    under "Accessibility" hold for every page, in every look, by day and by night.
11. **Calm first.** If a choice adds noise and nothing else, take it out.

## Composing a page

### The frame

Every page sits in one frame: **the menu, the main column, and the rail.**

- **The menu and the rail are the same width**, and the main column sits centered between them,
  with the same gap on either side. Both side columns sit on the page's own background, set off
  by a hairline, with no card around them, so they sink back and the main column comes forward.
- **The frame grows in steps**, never by stretching words across a wide screen:

  | Window | Menu and rail | Gap | Main column, at most |
  |---|---:|---:|---:|
  | under 1400 px | 240 | 32 | 720 |
  | 1400 px and up | 256 | 48 | 880 |
  | 1800 px and up | 288 | 64 | 1080 |

- **The rail holds the page's supporting content**: on Home, what is left to do and what is left
  to set up; on another page, its explanations, its secondary forms and its "how to read this".
  It is written in the menu's voice: a caps label for each section, rows in the plain weight, a
  hairline between sections. A page with nothing supporting leaves the rail empty rather than
  stretching the main column into it, so every page's main column starts at the same edge.
- **The page header** opens the main column: a caps label for context (on Home, the greeting), the
  page's title or the day as a display line, at most one line in the quiet tone, and a hairline
  under it. The page's one primary action, if it has one, sits at the header's right edge. The
  header's top lines up with the wordmark's, so the page has one top edge.
- **The footer** ends the main column: the mark, the family's line and the version, quiet.

### The test

To draw a page, or to fix one that feels wrong, in this order:

1. **What does somebody come here to do?** That is the focal element. Make it the clearest thing
   on the page, at the top of the main column, under the header.
2. **What do they need to see while doing it?** That is the main column's content, in cards or
   rows below the focal element.
3. **What supports it?** Explanations, secondary forms, status, help: the rail.
4. **Give every piece of text its role**: label, words, heading or display. No other sizes.
5. **For every piece of information, ask whether the reader needs it here.** If not, it lives on
   the thing's own page.
6. **Replace sentences and pills with marks** where a mark already exists, keeping the words
   behind the mark.
7. **Group with alignment and hairlines first**, and with a card only for an object.
8. **Count the signals**: one primary action, one glow, amber and red only where they mean what
   they mean.

## Type

Two faces, both self-hosted (the content policy lets fonts come from this site only):

| Face | What it is | Where |
|---|---|---|
| **Saira**, variable (weight, and width from 50 % to 125 %) | an engineered sans, condensed or wide from one file | every word |
| **JetBrains Mono** 400, 700 | a coding mono with distinct I, l, 1, O and 0 | figures that stand alone, and codes |

Only weights 400 and 700 are used. The width axis carries the variety: the same face is narrow
for display, near its normal width for reading, and wide for labels. That is what makes the page
look like one hand rather than a pairing.

**The four roles**, in rem so a reader's larger text grows every step:

| Role | Size | Saira | Used for |
|---|---:|---|---|
| **Label** | 13 px | 700, width 125 %, capitals, tracked `.16em` | section labels, the menu's group names, a date tile's weekday and month, an eyebrow ("In 2 days"), state tags |
| **Words** | 15 px | 400, width 88 % (700 for a row's title in the main column) | everything read: body, rows, the menu, buttons, links, hints, fields |
| **Heading** | 22 px | 700, width 76 % | a card's title, the hero's question, a featured row's title |
| **Display** | 28 px | 700, width 76 % | the wordmark, the day on Home, a page's title, a date tile's day |

Line height is 1.5 for words, 1.3 in rows, 1.15 for headings and display. Paragraphs stop at about
62 characters.

**Two tones.** Words are `--ink` (what you came for) or `--ink-2` (what supports it), and nothing
else. Hierarchy comes from role and tone together: a row's title is ink, its detail line ink-2;
everything in the rail and the menu is ink-2, and the current place is ink.

**Capitals are labels.** Wide capitals are for labels of about three words at most. A sentence, a
status that is more than a word or two, a button and a link are written in sentence case. Long
runs of tracked capitals shout and are hard to read.

**Figures.** A figure that stands alone (a date tile's day, a time on a plan, money, a count) is
in the mono (`.num`), at weight 400 (700 on a date tile), set to Saira's x-height so the two sit on
one line. A figure inside a sentence ("Fri 9 Oct, 5 pm") stays in Saira (`.fig` marks amounts and
clock times on the rendered page by one filter, so no template has to remember), because mono
digits in proportional words leave visible gaps ("5  pm").

**Codes are mono too.** Model names, keys, ids, commands and any machine text are in the mono.
Saira's capital I and lowercase l are the same plain stick, and its O and 0 nearly the same: in
words the reader's context separates them; in a code nothing does, so codes go where every
character is distinct. This is the cost of Saira, accepted with open eyes: the family's names and
words read in context, and kids' pages are read aloud for tone. If it ever costs a kid a word, the
text role's face is the thing to revisit, not the rule.

**Times** are 12-hour with no leading zero ("9 am", "1:30 pm"), through `dates.clock_time` on the
page and in Telegram; what is stored and what the model is sent stay 24-hour. A number is held to
its unit by a no-break space ("18 min").

## Space and shape

- **One spacing scale**: 4, 8, 16, 24, 32, 48 pixels (`--s1` to `--s8`; the scale's in-between
  steps are the same values). Nothing on the page is spaced by anything else.
- **One card padding**: 24 on every side. Between cards in a column, 24. Inside a row, 8 between
  its lead, body and trail.
- **Two radii**: 8 for rows, boxes, tiles and fields; 16 for cards and the hero. A checkbox is 4.
  A button that stands alone, a tag and the health pill are pills; a button beside a box (Send, the
  mic) takes the box's 8, so the row reads as one piece. Round means a person (an owner mark),
  which is why the checkbox is square.
- **Controls**: a primary button 48 high; every other control 44 (a select, a secondary button, a
  field). The hero's box is at least 88 high.
- **Targets** are 44 by 44 or more. A mark that is drawn smaller (the 16-pixel checkbox, a 20-pixel
  owner mark that opens something) is given a 44-pixel hit area around it, never a 16-pixel one.
- **Hairlines** are 1 pixel in `--line`, and decorative only: under the page header, under every
  section title, between rows, between rail sections, between the side columns and the main
  column.

## Color and light

Color is carried by tokens, in two layers, and keeping them apart is what lets each person choose
how the page looks.

**Underneath are the jobs.** A part never asks for "cream" or "green": it asks for what a color is
for. `--paper` the page, `--card` a card, `--field` inside a box, `--ink` and `--ink-2` words,
`--line` hairlines, `--edge` the edge of anything you press or type into, `--primary` and `--link`
the family's actions, `--vera` and the `--ask-*` family Vera's box, `--send` its Send, `--ok`,
`--warn`, `--alert` the signals, `--p1` to `--p8` the people. These names are the only colors any
rule may use; a color written anywhere but `static/themes.css` is a mistake, and
`tests/test_look.py` and the content-policy check keep it that way.

**On top, a look gives each job its value**, day and night together (`light-dark(day, night)`),
one block per look in `static/themes.css`, listed in `web/looks.py`. Kitchen Table is the default;
each person chooses theirs on the Look page and it follows them to every device (`members.look`,
and the `fdb_look` cookie before sign-in). `static/themes-fallback.css`, written by
`familydb/web/fallback.py`, gives a browser without `light-dark()` plain values. A look is color
only, plus at most five effects (`--fx-page`, `--fx-scan`, `--fx-glow`, `--fx-title`,
`--fx-title-adjust`); it never changes the layout, the type, the sizes or the words. The design is
drawn on Phosphor, where it is at its best, and must hold in every look: a page is checked in at
least Phosphor, Kitchen Table and Ink before it ships.

**Signals**, each with its one meaning, in every look:

| Signal | Means | Shape |
|---|---|---|
| **Glow** | talk to Vera here | the hero's soft halo and its Send's light; in a paper look, a hard offset shadow in its place |
| **Send color** (`--send`) | the one action that matters most | the hero's Send and its focus ring, nothing else |
| **Amber** (`--warn`) | needs a look, set this up | a count dot in the menu, a "Needs a look" tag, the steps left to set up |
| **Red** (`--alert`) | late or broken | words and thin rules, never a fill behind the family's things |
| **Green** (`--ok`) | working, connected, done | a tag, a done checkbox |
| **A person's color** (`--p1`…`--p8`) | that person | their owner mark and avatar, always with their initial |

Everything else is neutral. Kinds of idea are told apart by an icon and a word on a neutral tile.

**Glass and phosphor** are the brand's and Vera's, the same in every look: her screen, the mark,
the wordmark's cursor, and the panes of glass on the pages where the page itself speaks (signing
in, not found, not yours, a first empty day, a tool's raw words). The rule for them is the rule
for glow: they mean Vera or FamilyDB, never the family's own things.

## The parts

Class names are the API. Each part has one anatomy, and a macro in `_ui.html` emits it, so no
template builds one by hand. Person classes are slots (`.p0` to `.p8`), never names.

- **Page header** (`.page-head`): the caps label, the display line, one quiet line, the hairline;
  the page's primary action at its right edge.
- **The hero** (`.ask`, Vera's box): the model for anywhere somebody writes to her. Three rows.
  First, her name as a label and her question as the heading ("What's on your mind?", the box's
  label and Home's `h1`), with **From** (who is asking) at the row's right edge while the family
  shares one password. Then the box, the mic and **Send**, side by side; the box is the largest
  field on the page and Send the one glowing thing. Last, one quiet line: "Share where I am with
  this message" at the left, where it goes ("Goes to the family chat.") at the right. The whole
  card has a faint halo. Chat's box is the same part.
- **Card** (`.card`): padding 24, radius 16, a hairline edge; a head of an icon and a heading, with
  "All plans ›" at its right, and a hairline under the head. Cards live in the main column.
- **Section title**: every section opens with its title and a hairline under it, in the main
  column (a card's heading, 16 below it) and in the rail (the caps label, 8 below it). The line is
  what makes a section start, so nothing else (a fill, a box, a bigger size) is needed to.
- **Row** (`.item`, `.todo`): lead · body · trail. The lead is a date tile, a checkbox or an icon
  tile. The body is the title (words, 700 in the main column, 400 in the rail) and **one** detail
  line in ink-2. The trail is the owner mark and, where the row opens something, a chevron; the
  whole row is the link. Rows are divided by hairlines.
- **Featured row** (the first of Next up): the same row, larger: a big date tile, an eyebrow label
  ("In 2 days"), the title as a heading, the time in the mono, the owner marks and "See the plan ›"
  in the trail, on the same line.
- **Date tile** (`.dt`): weekday and month as labels, the day as a mono figure in 700, on a hairline
  tile. Today's is lit.
- **Checkbox** (`.tick`): a 16-pixel square with 4-pixel corners and a 1.5-pixel ink-2 edge, on
  the first line of the title; its check shows faintly, and fully on hover or focus; done, it fills
  green and the row is struck through and stays. The detail line runs under it from the row's left
  edge, so the checkbox takes one line, not a column. It is a button in its own POST form, named
  "Mark done: …", with a 44-pixel hit area.
- **Owner mark** (`.who`): a 20-pixel circle in the person's color with their initial. Several
  people overlap, three shown and then "+N". The names are its accessible name and its tooltip.
- **Count dot** (`.badge`): a 20-pixel circle with the number, at the item's right edge: red when
  late, amber when it needs a look or a decision, neutral for a gentle count ("2 to rate"). Its
  words ("2 to check") are said to a screen reader and shown on hover.
- **State tag** (`.tag`): a short label in capitals on its signal's wash: Working, Ready, Needs a
  look, Off, Planned. A tag is a word or two; anything longer is a sentence beside it.
- **Buttons**: primary (a filled pill, 48, one a page), secondary (an outline pill, 44), text
  links with a chevron ("All plans ›"). Dangerous is red, and only for what cannot be taken back, folded behind
  a first step.
- **Fields**: a caps label above, the box (44 high, `--edge`, 8 corners), a hint below in ink-2,
  an error above the box in red. "Optional" is part of the label's own words, in its own style.
- **Menu** (`.side`): the mark and wordmark, Vera's state, then each place as an icon and words in
  ink-2, the current one in ink and 700 on a faint fill; groups under a caps label; who is signed
  in at the foot.
- **Rail section**: a caps label with its "All … ›", rows in the rail's voice, a quiet note with a
  small icon where something needs explaining.
- **Health pill** (`.pill-health`): Vera's state for grown-ups, a caps label with a dot ("Vera is
  ready"); when there is something to notice it turns to glass: writing back, resting, can't
  answer.

## Her screen

Vera is never drawn. Where she speaks there is a small pane of glass, as if she were typing: a
**rounded square** (never round, since round means a person), a **lit rim**, a few short **lines of
light**, the newest brightest, and her **signature, a lit prompt `>▮`**, in the bottom-left corner.
It is inline SVG (`svg.vs`, from `vera_screen(size, state)`), crisp at 24 pixels, always
`aria-hidden` with her name in text beside it. Sizes 24 (`.vs--sm`), 32 (`.vs`), 40 (`.vs--lg`, the
hero) and 56 (`.vs--xl`, a kid's empty chat); small sizes have fewer lines, not smaller ones.

It **types** its lines in once on Home as the page opens, then rests lit; it types on a loop only
while a reply is on its way (`.vs--busy`); it goes dark when she can't answer (`.vs--off`), with
the words beside it saying why. It never gets eyes, a mouth, a silhouette or an expression, and its
lines never spell anything. Every persona is a she, by the family's decision (`docs/PERSONAS.md`),
and her name is the one the persona in force gives.

**The mark** is FamilyDB's, not hers: a little monitor with a smile, phosphor on a charcoal
rounded square, never recolored, never without its square, never standing in for her. **The
wordmark** is "FamilyDB" in the display role, followed by a lit cursor block.

## Motion

Few motions, each meaning something, all in CSS, none for long where people read: her screen
types once on Home, and loops only while she is writing back; the flash that says what you just
did lights and fades over a second; where a link lands lights and fades; the wordmark's cursor
blinks for a few seconds and rests; the pill's dot breathes only while she writes back. Under
`prefers-reduced-motion` nothing moves.

## Narrow screens

The frame folds in order, keeping the focal element first and whole.

- **Below about 1100 pixels** the rail moves under the main column, its sections in the same
  order, and the menu stays.
- **At 820 pixels and below** the page is one column under a top bar (the mark, the pill, the
  account) and over a tab bar of five (`--tabbar-total`), the current tab marked on its top edge.
  The header is one line; the hero keeps its three rows, the box full width, Send with its word.
- **Nothing scrolls sideways** at 390 or 320 pixels, except a row of conversation pills. Labels
  that shorten keep the long one as the control's name.

This is the part least tried in the mockups; check every page at 390 and 320 pixels.

## Page by page

Each page names its focal element, what the main column holds, and what the rail holds.

- **Home.** Focal: the hero. Header: the greeting, the day, one line of how things stand. Main:
  Next up (the featured plan, then the next few as rows), what was just added to Ideas, the kids'
  lists. Rail: To do (checkbox rows), then, for an admin, what is left to set up. What a role may
  not do is not offered.
- **Chat.** Focal: the box, the hero's part. Main: the conversation, newest at the bottom, her
  messages beside her screen and the family's in their own color's soft. Rail: the conversations
  (the family's, and the kids', which grown-ups may read along) and who can read this one.
- **Ideas.** Focal: search, with narrowing by kind, person or status folded under it. Main: the
  ideas as rows in one card (kind tile, title, one line of the kind and where or how far, tags,
  owner marks), then the radar, the one instrument in the app. Rail: "Save a thought for later",
  why something has not been looked up, the download. **An idea**: its own page; main: what it
  is, when it is on the calendar, the place, how it went; rail: at a glance, looking it up,
  planning it. **Restaurants**: a card per place, with today's hours and cost.
- **Plans.** Focal: the next plan. Main: Month or List; the list as rows by month (date tile,
  title, when and where on one line, owner marks), Move and Cancel as one quiet line under each.
  Rail on the list: where the plans come from, adding a plan, what happened lately, the download;
  on the month: what is coming (the time beside each date tile), how the last plans went, where
  the plans come from.
- **What is on near home** (its name is the family's, written once in `familydb/happening.py`): a
  third tab of Plans, for grown-ups only, drawn as Plans' list, a heading a day, each find a row
  with no date tile.
- **To do.** Focal: adding one. Main: overdue first under a red heading, then the rest, No date
  last; each a checkbox row whose title opens the to-do's own page. Rail: that she can be told
  instead, the download. The to-do's own page: the form; rail: what to know, what reminders do.
- **Lists.** Focal: the shopping list. Main: each list as checkbox rows, what was got folded under
  "Got". Rail: the other lists.
- **The kids' lists.** Main: each kid's lists at a glance, what Vera flagged, the answers. A kid's
  own page: "A kid's screen".
- **What Vera knows.** Main: each fact as a row under whom it is about, with how sure and where it
  came from, and Forget. Rail: telling her something, how she weighs it, what was forgotten.
- **Family.** Focal: the list of people. Main: each person a row (avatar, name, role, how Vera
  reaches them). Rail: "Add somebody" as a form, the roles. The primary action is the form's Add,
  once; the header's "Add somebody" is a quiet way to it. One person's page: the form; rail:
  signing in, linking Telegram, and taking them off the list, folded in red.
- **Status.** Focal: the verdict, one sentence on a wash. Main: spent today, the last 30 days, how
  each part is doing as rows (a sentence, a tag, at most one action). Rail: recent activity, for an
  admin.
- **Settings.** Main: a row per settings page with how it stands. Rail: setting up, how to read the
  tags. Each settings page: its groups as cards, one Save in a bar that stays in reach; the rail
  lists every settings page. **AI
  model** (`docs/MODELS_PAGE.md`) is a table, the one page dense by design. **Troubleshooting**
  lists what went wrong as sentences first, then the log.
- **Setting up.** Focal: the step's one form. The steps along the top, Back and Next at the foot.
- **The guide** (`/wiki`, grown-ups). Main: the article. Rail: "On this page" (when the page has
  sections), then every section of the guide. Search at the top; no model is asked.
- **You, Look, Sign in.** One form each; Your password keeps what is good to know in the rail. Sign in is the pane, then name and password; the family
  is never listed.
- **Not found, not yours.** The pane: "404 · nothing on the radar", or "403 · signed in Maya · role
  kid", then the page's own words and the way back.

## Words

Spelling is American English ("color", "canceled"; the page is `lang="en-US"`), by the family's
choice; what is stored or named in code stays as it is. `tests/test_american_spelling.py` holds
what the family reads to it. One word for each thing, on every page, in her replies and in
Telegram: Everyone, No date, Connected, Added, Needs a look. Errors are written as the fix ("Give
the idea a name"), never "invalid". The page's wording lives in `web/views.py`. Words are written
for about grade 4 to 7. Dates keep their order ("Sun 27 Sep").

## Accessibility

These are floors: they hold for every page, in every look, by day and by night, and
`tests/test_look.py` measures them.

- **Contrast**: 4.5:1 for words on the page and on a card, 3:1 for the edge of a control and the
  focus ring and a mark on its ground, words on every color used as a fill.
- **Sizes**: type 14 pixels or more, 13 only for capitals, in rem; nothing breaks at 200 % text.
- **Targets**: 44 pixels, by hit area where the mark is smaller.
- **Focus** is a 3-pixel ring on everything, never removed; "Skip to content" on the first Tab.
- **Never by color, never by mark alone.** Every mark has its words: an owner mark its names, a
  count its meaning, a checkbox "Mark done: …", a tag its word, late its "6 days late".
- **Labels.** Every box has one; hints and errors are tied with `aria-describedby`; a wrong box
  gets `aria-invalid`; a fold holding an error opens.
- **Structure.** One `h1` a page, headings in order; the chat thread is `role="log"`.
- **Motion** honors `prefers-reduced-motion`; **forced colors** get real borders wherever a
  background alone shows something; **reflow**: nothing scrolls sideways at 320 pixels.
- **Scripts add, never require.** Every page and every form works with scripting off.

## What does not move

- **The content policy**: `default-src 'self'; style-src 'self'; script-src 'self'; font-src
  'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'`. No inline style, no
  inline script, nothing from anywhere else. A size from data is an SVG attribute or a class.
- **Works with scripting off**: read, every form, send a message.
- **Kids never see costs or workings**: no pill, no money, no limit, no models, no setup, no
  Status (a family decision, `docs/DESIGN.md` section 16).
- **Presents stay hidden from whom they are for**: left out entirely for them, tagged "Hidden from
  Theo" for everyone else; lists are filtered before anything is counted.
- **Looks are color only**, plus the five effects, and keep Vera's glass and phosphor and red for
  late or broken.
- **The accessibility above**, measured, in every look.
- Nothing from an idea, a place or a fetched page is marked safe in a template.
- No page view is a model call (`test_browsing_asks_nothing_of_a_model`).

## A kid's screen

A kid signs in to the same page, in the same frame and look (or her own): there is less of it,
and what is there is worded for her. One natural place to say anything, and each page showing only
what is hers or the family's, with nothing to filter, count or choose between. Every simpler page
is drawn for whoever may not `browse`, never by asking about a role.

Her menu is Home, Chat with Vera, My list, My things to do, Plans and Ideas: no pill, no What Vera
knows, Status, Settings or Family, and no version in her footer.

- **Her Home** opens with her line ("Roller rink tomorrow with Theo, and Sam said yes to your
  sketchbook!"), then the hero, going to her own chat, saying how many messages she has left
  today. Then Next up for you, My list and My things to do, and nothing else.
- **Her chat** is only her own, and says that the grown-ups can read it, at every width. Empty, it
  rests on Vera's screen at 56 pixels. She is told gently when 5 messages are left; when they are
  used up the box closes until tomorrow. No "Share where I am".
- **My things to do** are hers, and she ticks them off herself: the checkbox, what, when in words,
  "Set by Alex". No filters, no search, no count, no reminder workings.
- **Plans** is one list of what is coming. **Ideas** is plain rows, each a link, with nothing to
  search, filter or count, no radar and no workings. A present for her brother shows, tagged
  "Hidden from Theo".
- **My list** opens on the hero, "Tell Vera anything", posting to her chat; there is no second
  form. Under it her three lists (Every day, Christmas, Birthday), each with its countdown, one
  line to each thing: the grip (only while the script runs), its rank in a round badge, what it
  is, a chevron. Tapped, a line opens to its moves. Every line and button is at least 44 pixels.
  Answers come back in words: Yes!, or Not this time with the parent's note. "Your list isn't
  secret: Sam and Alex can see it."
- **The word** is "list" and "I'd like", never "wish", by the family's choice; the code still says
  wish.
- A page that is not hers gets a kind refusal in plain words, never an error.

## Still open

- **Narrow screens** in the new frame are written above but not yet drawn; they are the next thing
  to try.
- **The paper looks** (Kitchen Table, Ink and the rest) have been checked on Home only.
- **Everyone.** An owner mark for a plan that is everyone's shows all of them stacked. Showing no
  mark for the usual case is worth trying once a page has many such rows.
- **A to-do's edit** moved from a link on every row to the row itself opening the to-do's page;
  where the Undo and the quick moves go on that page is to be drawn.
- **Print.** There is no print style yet; a month for the fridge would be the first.
