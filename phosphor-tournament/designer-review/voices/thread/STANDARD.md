# FamilyDB · Thread · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth. This document says how to use them.

**The rule behind everything:** FamilyDB is the household's running conversation. Say it first, then show it on the thread: one line down the page, *when* in the margin, *what* beside it, each kind of thing in its own typographic form. A bright pen colour means *a person*, green means *now, today or Vera*, ink means *something you press or picked*, and red means *late or broken*.

*Thread* follows Felt Tip (see `DIRECTION.md`). Pages keep their jobs, words and states; layout, type, the shell and the surface changed. Kids' pages keep their body class (`kid me-pN`).

---

## 0. Layout: the thread

**The thread** (`.tl`, style.css §10) is the spine of Home, the kid's Home, To do, the kid's To do and Plans' "Coming up". It is three columns drawn with padding, not a table:

| Column | Width (desktop / phone) | What goes there |
|---|---|---|
| The margin clock (`.tl__when`) | `--gut` 96 px / 52 px (Plans 76 / 52) | when: weekday in mono capitals over the date ("SUN / 27 Sep"), right-aligned against the line; "Now" for the composer; "No date"; "Today". Always `aria-hidden`: the same date is in the row's text (often as `.sr`) |
| The rail | `--rail` 28 px / 22 px | a 2 px line (`--thread`) and one 14 px node per group (`.tl__h::before`): hollow (`--node`) by default, **filled green** for the next plan (`.tl__grp--today`), **filled red** for a group with late things (`.tl__grp--late`), a green rounded square for "Now" |
| The things | the rest | the group's heading (`.tl__h`: Familjen h2, its link on the right), then its objects |

- **Each object has one typographic form** and never borrows another's:
  - plan → **ticket** (`.ticket`, Familjen 700, 32 px) or **plan row** (`.plan-row`, Familjen 600, 19 px, its kind in mono capitals), always with a **people strip** (`.strip`): the plan's people's pens stacked down its left edge, neutral `--everyone-mark` for Everyone
  - to-do → a **line** (`.todos--tl .todo`): tick, Atkinson 700 title, meta; hairlines between, no card; due date in the margin, red when late
  - wish → a **quote** (`q.wish`, `.rank__title`): Familjen italic 500 in curly quotes in her colour; a parent's answer is a **reply** (`.quote`) threaded under it with a hooked line
  - idea → a **small card** (`.idea-chip`, `.idea`): kind in mono capitals, name in Familjen 600
  - Vera → **typed** (`.msg--vera`, `.vline`): Atkinson Hyperlegible Mono on `--vera-paper` with a 3 px green rule
- **Talk first.** Home's composer is the first entry on the thread ("Now"). Every other page with a sidebar carries **Write to Vera** (`form.say`, charcoal glass, phosphor send) at the foot of the rail, posting to the chat (kids: their own chat). Home and Chat leave it out (one composer per page). On the phone, **Chat is the middle tab** (`.tab--vera`), drawn as a small pane of Vera's glass.
- **Page heads line up with the things** on thread pages (`.page-head--tl` indents by `--gut + --rail` on the desktop), so the greeting, every plan title and every to-do share one left edge.
- **Chat is a transcript** (`.thread` › `.msg`): everyone on one edge, the time in a 76 px margin in mono, then the avatar or Vera's screen, then the words: the family's on a soft wash of their pen (`--p-soft`), Vera's typed in mono on `--vera-paper`. Day separators are mono capitals on a rule. On the phone the margin folds away and the time sits after the name.
- **Page compositions** (desktop):
  - Home: thread (1fr) | aside 300 px (setup, Vera today). Thread order: Now (Ask), Next up (ticket), To do, After that, How did it go, Wish lists, Just added to Ideas.
  - Kid's Home: thread alone, 760 px: Now, Next up for you, My wishes (`.wishlist`), My to-dos, After that, Just added to Ideas.
  - To do: thread (1fr) | Add a to-do (320 px) with the tip under it.
  - Plans: Coming up (thread) | How did it go (340 px), then the month bar and the month, full width.
  - Ideas: search and filters, then **Quick idea** right under them, then the cards, then the map.
  - Chat: conversations (280 px) | the room.

---

## 1. Tokens

All values live on `:root` in `style.css` §2; the thread is §10. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root`.

### Colour

| Token | Light (Thread) | Dark (the thread at night) | Use |
|---|---|---|---|
| `--paper` | #F5F4F8 | #111018 | the page: quiet porcelain, a breath of violet. No texture: the thread is the texture |
| `--thread` / `--node` | #CFCCDA / #8C889E | #3A3848 / #8A879E | the thread's line and its hollow nodes (decorative; the node is 3.1:1 by day anyway) |
| `--paper-2` | #E9E7F0 | #211F2C | tracks, neutral tiles, "Off" tags, the segmented control's well, a several-people calendar block |
| `--card` | #FFFFFF | #1A1924 | objects: tickets, plan rows, idea cards, cards; the current nav item, the phone top bar |
| `--field` | #FFFFFF | #201E2B | inputs, tick rings |
| `--ink` | #1A1830 | #F0EFF6 | violet-black ink: text; the primary button, every picked control, the next plan's edge |
| `--ink-2` | #464358 | #CCC9D9 | secondary text, meta, the margin clock's dates |
| `--ink-3` | #5D5A70 | #A5A2B6 | quiet text: hints, message times, weekday capitals (still AA) |
| `--line` / `--line-2` | #E5E3EC / #D1CEDB | #2A2836 / #3A3848 | hairlines between to-dos, object edges, the calendar grid (decorative only) |
| `--edge` | #7E7B90 | #8A879E | **control edges**: inputs, selects, tick rings, choice pills, quiet buttons (3:1) |
| `--vera` | #0B6E4F | #6DFF9C | Vera's green as text and icons; her name on her messages; "Now". Phosphor in the dark |
| `--vera-bg` / `--on-vera` | #0B8457 / #FFF | #4FE08A / #12101F | the meter fill, a done tick, the felt-tip strike-through, the flash check, the "Yes!" sticker |
| `--vera-soft` / `--vera-line` | #E3F4EA / #B2E0C8 | #10261C / #22513A | Vera's surfaces, the calm pill, the lede links' underline, the ring round "Now" |
| `--vera-paper` | #F1F8F4 | #141F1B | the faint green page Vera's typed messages sit on |
| `--today-bg` / `--on-today` | #0B8457 / #FFF | #6DFF9C / #111018 | **today and next**: the next plan's node on the thread, today's number on the calendar (a filled rounded square), the calendar's top rule |
| `--today-wash` | #EAF8F0 | #13261F | today's calendar cell; the halo round the next plan's node |
| `--gut` / `--rail` | 96 / 28 px (phone 52 / 22) | | the margin clock's width and the rail beside it |
| `--ask-bg` / `--ask-ink` / `--ask-ink-2` | #13121F / #FFF / #C9C6D8 | #0E1A17 / #EAEEF3 / #C3D2CA | the composer and the rail's Write to Vera: the brand's charcoal glass by day, green-rimmed glass at night |
| `--ask-rim` / `--ask-edge` | faint white inset / none | 1.5 px #3E8A66 rim + faint glow / #7D8899 | the Ask card's edge and its box's edge at night |
| `--send` / `--send-2` / `--on-send` | #6DFF9C / #95FFB8 / #121022 | same / #0D1117 | the Ask card's Send, lit phosphor |
| `--link` | #0B6E4F | #8BD3B4 | links: Vera's green by day, a lighter green at night, never phosphor |
| `--primary` / `-2` / `--on-primary` | #1A1830 / #37344F / #FFF | #F0EFF6 / #FFF / #111018 | the one primary button: **ink**, inverted at night, so no accent competes with the people |
| `--ok`, `-soft`, `-line` | #17703F, #E0F5E8, #B4E2C4 | #7FE3A5, #11261B, #24503A | Working, Connected, done |
| `--warn`, `-soft`, `-line` | #7A4D00, #FFF1CC, #EFCF7E | #F5B94A, #2A2112, #5E4620 | **only** “set this up” and “needs a look” |
| `--alert`, `-soft`, `-line` | #B42318, #FDE8E6, #F5C2BD | #FF8B74, #33191A, #5C2E2B | late text, broken, form errors. Nothing else is red |
| `--focus` | #1A1830 | #F0EFF6 | focus ring (phosphor inside the composer and on glass) |
| `--p1…--p8` | p1 #6E9BFF cornflower · p2 #B48CFF violet · p3 #FF6FB0 raspberry · p4 #FF9F45 tangerine · p5 #33C6C0 teal · p6 #8F95FF periwinkle · p7 #B9CF3A lime · p8 #D3A276 caramel | **the same pens** | **the family's felt-tip pens**: avatars, a one-person plan's whole calendar block, the phone month's markers. Always under **dark letters** `--on-p` (#1B1838; #17142B at night), never white |
| `--pN-soft` / `--pN-ink` / `--pN-mark` | e.g. Maya #FFE5F1 / #AD246A / #D63A87 | e.g. Maya #361A2C / #FFAED2 / #FF8CC0 | bubbles and washes / names on soft and on cards / dots, rules and rings on cards (3:1) |
| `--everyone…` (`.p0`) | #DBD8E6, soft #EEECF4, ink #464358, mark #7E7B90 | #4A475E, soft #23212F, ink #CCC9D9, mark #A5A2B6 | Everyone and several-people plans: always neutral (a grey block with each face; the house icon in `--everyone-ink`; a grey people strip) |
| `--me`, `--me-soft`, `--me-ink`, `--me-mark` | from the kid's slot | same | set on `<body>` by `.me-p1…p8` on a kid's pages (with `.kid`): her heading's highlighter underline, her current nav item and tab, the quote marks round her wishes, her top wish's rosette, her account box |
| **Brand** (§9) `--glass` / `--glass-2` / `--glass-line` | #0E1312 / #161D1B / #2A3632 | #070A09 / #0E1312 / #2B3B34 | the charcoal glass of the mark, Vera's screen, the pill and the panes |
| `--glass-ink` / `--glass-ink-2` | #E9F1EC / #B9C6BF | same | text on glass |
| `--phosphor` / `--phosphor-dim` / `--phosphor-glow` | #6DFF9C / 34 % / 50 % | same | lit things on glass, and the Ask card's Send |
| `--cursor` / `--cursor-glow` | #12945A / 35 % | #6DFF9C / 55 % | the wordmark's cursor and the caret in Vera's box |
| `--vs-halo` | #12945A at 35 % | #6DFF9C at 45 % | the 3 px halo round Vera's screen |

**What each colour does.** The porcelain page and white objects are the surface; the thread is a quiet violet-grey line. Ink is for pressing and picking (primary button, selected segment, chosen pill, the next plan's edge and shadow, the "Tomorrow" sticker). Green is now, today and Vera (and "done", which is hers to celebrate). **The bright colours are the people's pens and nothing else**: avatars, the people strip, one-person calendar blocks, washes behind their messages, the quotes round a kid's wishes. Amber says "set this up"; red says late or broken, including a late date in the margin. Never cream paper, soft serif, forest green or sun yellow (Kitchen Table); never a cool grey page with one green accent (the first Kitchen Wall); no lilac wall or dot grid (Felt Tip).

**Why bright pens with dark letters.** The first Kitchen Wall's muted slots needed white letters, which kept them dark and serious. Felt-tip colours are light and loud, so their letters are ink: 6.3:1 or more on every slot, day and night. In light mode a pen colour on white is under 3:1, so wherever a person's colour has to be seen as a mark on a card (dots, rules, rings, a name), the darker `-mark` and `-ink` are used, not the base.

**Maya's slot (p3) is raspberry, not red**, and slot 4 is tangerine, not red-orange, so neither reads as "late" next to `--alert` #B42318. Colour is never the only cue: every person marker carries an initial or the house, and every calendar block carries its time, title and faces.

**Person colours come from the family's data.** The four above are the mockup family. A real install assigns each new person the next colour from the fixed set of eight. Each colour is checked for 4.5:1 with `--on-p` and for its own `-soft`/`-ink` pair (§7).

### Type

Three voices in one conversation. **The family speaks in Atkinson Hyperlegible, Vera types in Atkinson Hyperlegible Mono, and the names of things are set in Familjen Grotesk.**

| Token / step | Size | Face and use |
|---|---|---|
| `--t-xs` | 13 px | **only capitals in the mono** (600, +0.06em): eyebrows, weekday in the margin, kinds of idea, group labels, date-tile and calendar heads; and the phone tab labels (Atkinson 700) |
| `--t-sm` | 14 px | the floor: tags, badges, hints, names on messages; the margin clock's dates (mono 500) |
| `--t-meta` | 15 px | meta lines, small body |
| `--t-vera` | 16 px | **Vera's words**, Atkinson Hyperlegible Mono 400, −0.03em, word-spacing −0.1em, line 1.6 |
| `--t-md` | 17 px | the family's words: body (line 1.5), to-do titles on Home (700) |
| — | 18 px | to-do titles on To do (700); the lede (16 on the phone) |
| — | 19–20 px | a plan's or an idea's name (Familjen 600, −0.01em) |
| `--t-h2` | 22 px | group heads on the thread and card titles (Familjen 600, 20 on the phone); a wish on a list (Familjen italic 500) |
| — | 32 px | the next plan's ticket title (Familjen 700, −0.03em; 24 on the phone) |
| — | 44 px | the next plan's day in the margin (Familjen 700, tabular; 34 on the phone) |
| `--t-h1` | 46 px | page titles (Familjen 700, −0.03em, line 1.04; 36 on the phone) |
| — | 36 / 38 / 48 px | money, Status figures, the big money figure (Familjen 700, tabular) |

- **Fonts** (`fonts/`, self-hosted, Latin): `familjen-var.woff2` (19 KB) and `familjen-italic-var.woff2` (21 KB), weight 400–700, OFL (`familjen-OFL.txt`); `atkinson-mono-var.woff2` (18 KB), weight 200–800, OFL (`atkinson-mono-OFL.txt`); Atkinson Hyperlegible 400/700 as before. Bricolage Grotesque and JetBrains Mono are gone. New files total 57 KB.
- **Why Familjen.** It was drawn for a Stockholm studio called Familjen ("the family"): a grotesque with a cut "a", a hooked "g" and "y", and a slight ink-trap sharpness that gives a title a voice, while staying calmer than Bricolage in long headings. It sets the *names of things*: page titles, plans, places, ideas, figures. A to-do stays Atkinson 700 because a task is a sentence someone reads aloud.
- **Why one italic.** Familjen's italic does one job: **a wish**, inside curly quotes in the kid's colour, so a wish always looks like something someone said.
- **Why Atkinson Hyperlegible Mono.** It comes from the same Braille Institute legibility research as Atkinson, so a kid reads Vera as easily as a parent. It's monospaced, so Vera is typed, never a person, and it ties her lines to her screen's `>▮` prompt. It also keeps the clock: margin times and dates, so every *when* in the app has one voice. The mono is wide, so Vera's lines are tracked in (−0.03em) and set one step smaller than the family's (16 against 17).
- **Sizes are in rem** (16 px = 1 rem). The only px type is inside drawings (the radar, the phone month's 9 px initials).
- **Figures.** `--font-num` is Familjen with `tabular-nums lining-nums` (big dates, money, Status figures, calendar day numbers, wish ranks). **Every amount and clock time in running text** is `.fig`: `"Familjen Figures"`, the same file limited by `unicode-range` to `$ , . 0–9 : ¢`, so a zero is always open. Other numbers in sentences stay Atkinson.
- `.code` switches back to Atkinson for model names, keys and codes.
- Times follow the family's clock setting; the mockup uses the 12-hour clock ("9 am", "12:30 pm").
- `type.html` shows every step and sets real lines live.

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48. Groups on the thread are 32 apart (24 on the phone).
- Radius: `--r-sm` 6 (calendar events, tags), `--r-md` 10 (inputs, plan rows, wish rows, idea chips, banners), `--r-lg` 16 (tickets, cards, the composer, the calendar), `--r-pill` (**buttons**, segmented controls, avatars, badges, starters, choice pills, the health pill). A family member's message is 4 / 16 / 16 / 16 (the corner by the avatar is tight); Vera's is 2 / 10 / 10 / 2 against her rule.
- Shadow: a 1 px violet-tinted line plus a soft 14 px drop under objects, only on hover for rows. The next plan's row has a hard 3 px ink offset shadow, and the "Tomorrow" sticker a 2 px one. No tilts.
- Avatars: 24, 32, 40. Tiles: 32 (idea cards), 40, 56. Nodes: 14.
- Every target is 44 px or more (`--target`). The tick is a 44 px hit area around a 32 px ring.
- Top bar 56 px; tab bar 68 px plus `env(safe-area-inset-bottom)`.

### Moments (style.css §9)

All CSS, played once, **nothing moves under `prefers-reduced-motion`**.

| Moment | Where | What happens |
|---|---|---|
| Now and next | the thread | "Now" is a green rounded node with a soft ring; the next plan's node is filled green with a halo; today on the calendar is a filled green square |
| Next up | Home, the kid's Home, Plans | the next plan stands proud: a 2 px ink edge and 3 px ink shadow on its row; "Tomorrow" is a tilted round sticker |
| Crossing it off | `.todo--done`, `.tick--done` | the tick pops (scale 0.55 → 1.2 → 1) green; a 3 px green line is drawn through the title, left to right |
| A flash that went well | `.banner--ok.flash` | the banner drops in; its check pops, with a burst of seven dots in the family's pens |
| "Yes!" | wish answers (`.rank`, `.wl`, the key) | a filled green sticker, tilted −3° |
| Top wish | a ranked list of two or more | rank 1 wears a rosette: ink by default, the kid's colour on her pages |
| A kid's pages | `body.kid.me-pN` | her heading underlined in her highlighter colour; her current nav item and tab, the quotes round her wishes and her account box in her colour |
| Pressing | buttons, starters, faces, ticks | a 1 px press; faces tilt on hover |

---

## 2. Components

Class names are the API. Person colour classes are **slots** (`.p0…p8`), never names: no `.av--sam`, `.msg--maya`, `.ev--theo`. Each component has one anatomy; variants are modifiers.

| Component | Classes | Variants | When to use |
|---|---|---|---|
| Card | `.card`, `.card__head`, `.card__foot` | `--setup` (amber-tinted) | every group of content |
| Button | `.btn` | `--primary` (one per view), `--quiet`, `--sm`, `[disabled]` | actions; links styled as buttons only for navigation actions |
| Text button | `.textbtn`, `.linkbtn`, `.more` | — | a form action that reads like a link (Delete, Take it off my list); "All plans ›" |
| Badge | `.badge` | `--late` (red), `--act` (ink outline), `--quiet` (plain grey number), `--look` | counts with a word. Loud only for what needs someone now: **late** and **to decide**. “2 to rate” and “1 to check” are quiet |
| State tag | `.tag` | `--ok` Working/Connected/Added · `--better` Could be better/Not connected · `--look` Needs a look · `--broken` Not working · `--off` Off/Optional/No backup · `--when` Tomorrow/Planned · `--been` Went… · `--surprise` | how a thing stands; one tag per thing, words from §3 |
| Health pill | `.pill-health` | `--busy`, `--rest`, `--down` | Vera's state, in the sidebar and phone top bar; parents and admins only. **Quiet when all is well:** "Vera is ready" is a soft-green pill in Atkinson 700 with a still dot. **Glass and mono only when there is something to notice:** writing back (phosphor, the dot breathes until the reply lands), resting (quiet glass ink, hollow dot), can't answer (coral `--glass-alert`, square dot) |
| Avatar | `.av` + slot `.p0…p8` | `--sm` `--lg` | every mention of a person; Everyone (`.p0`) uses the house icon (the family's house, not the brand). Small initials are decorative: the name is always beside them |
| Vera's screen | `svg.vs` (`aria-hidden`) | `--sm` (24) · default (32) · `--lg` (40) · `--xl` (56); `--busy` (answering), `--off` (can't answer) | Vera, wherever she speaks: Ask card, chat, Status, Home's Vera row. A rounded square with a lit `>▮` prompt. **Never a face or figure** (§9) |
| FamilyDB mark | `.mark-fdb` + `.wm` (wordmark) | `--sm`; `.pane__mark` (64) | the brand: bar, sidebar, sign-in, panes, favicon (§9) |
| Glass pane | `.pane` | `--center`; `.brand-row` | brand moments only: sign-in, a first empty day, the grown-ups page, the missing page (§9) |
| Instrument (radar) | `section.mapband` › `details.mapband__fold` › `.instrument__pane` › `svg.radar` | `--wide` (desktop), `--narrow` (phone) | Ideas only, in its own band after all the cards. Desktop: always open (the summary is hidden and `::details-content` is shown). Phone: folded behind "Show the map". Each dot carries the idea's short name; no separate list (§9) |
| Add a to-do | `form.adder--todo` › `.adder__row` + `details.adder__more` | — | One row first: box and Add. Who, when and the reminder sit in `.adder__more`: folded beneath the row on the phone (summary "Who, when, reminder · Nobody picked yet · No date"), always open on the desktop, where Add is a full-width bar at the bottom. The form is `novalidate`: the server checks who and sends it back with the fold open and the error in it |
| Calendar who-marker | `.dots i` via `mini(person)`; `.cal-key` | person initial · house (Everyone) · hollow ring (past) | the phone month's day cells (up to three) and the one-line key under the calendar on Plans. On desktop every event shows its people as small avatars |
| Tile | `.tile` | `--lg`, `--ok` `--better` `--look` `--broken` `--vera` | leading icon for an idea kind (neutral) or a health area (tone) |
| Date tile | `.dt` | `--now`, `--lg` `--sm` | a plan's date where there is no thread (the idea page, the weekend card): the weekday in mono capitals on an ink band, the day in Familjen 700. On thread pages the margin clock replaces it |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--boxed`, `--divided`, `--health` | every list of things that isn't a to-do or an idea card |
| To-do row | `.todos` › `.todo` | `--compact` (Home), `--late` (4 px red rule), `--done` (struck through after a tick), `--ro` (kids: read-only, icon tile instead of tick) | to-dos |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | marking a to-do done; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default **info (neutral card, grey icon)**, `--ok` (mint: all good, done), `--warn` (set this up), `--alert` (broken, errors); size: `--hero`, `--slim` | a message with at most one action. Resting, Off and “for your information” use the neutral default, never mint or yellow. **One “set this up” message per page** |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (charcoal glass, phosphor Send); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page. On Home it is the thread's first entry, "Now" |
| Write to Vera (rail) | `form.say` › `label`, `.say__row` › `textarea` + `button` | — | the foot of the desktop rail on every page except Home and Chat; one line, posts to the chat (kids: their own chat). Hidden with the rail on the phone, where the Chat tab does the job |
| Starters | `.starters` › `.starter` | `--ask` (sends a complete question, `name="prompt"`); plain = a link that fills the box (`?draft=…`) | suggested messages |
| Chat room | `.chat`, `.convos`/`.convo`, `.room`, `.scroller` › `.thread` | `.msg--{person}`, `--mine`, `--vera`, `--pending`, `--failed`, `--system`; `.receipt`; `.earlier`; `.day-sep` | conversations, as a **transcript**: all on one edge, the time (`.msg__by time`) in a 76 px mono margin, the family on their pen's wash, Vera typed in mono on `--vera-paper` with her 3 px green rule. `--mine` is not moved to the right |
| Privacy line | `.privacy` (`--room` on phone) | — | "Sam and Alex can read …"; **at every width** |
| Field | `.field`, `__label`, `__hint`, `__error`; `.req`/`.opt` | `--error` | every input; label above, error above the box, hint below |
| Form | `.form`, `.fieldset`, `.form__row`, `.actions` | — | multi-field forms |
| Choice pills | `.choices` › `.choice` (radio or checkbox) | `--person` | picking from a few; **no default where a choice must be made** |
| Disclosure | `.disclose` (`<details>`) | — | filters and form options folded away (always on the phone) |
| Segmented control | `.seg` | — | view switches (Open / Done / All, Month / List); never wraps |
| Search | `.searchbox` | — | search inputs |
| Faces | `.faces` › `.face` | — | "How did it go?"; three labelled faces; parents only |
| Idea card | `.ideas` › `.idea` | `--unknown` (not looked up); `.ideas--one` | cards on desktop, compact rows on the phone |
| Ranked list | `.ranks` › `.rank`, `.rank__n`, `.rank__move`, `.quote`, `.decide` | `--decide` | wishes |
| Calendar | `.cal`, `.week`, `.day`, `.ev`, `.ev-more`, `.daylink`, `.dots` | slot class on `.ev` (one person: a solid block in their pen, dark words; `.p0`: grey block, left rule, faces), `--past` (grey); `.day--today` (hand-drawn green loop, green top rule, wash), `--we`, `--out` | the month view |
| Settings row | `.slist` › `.srow` | `--look` | lists of sections or destinations (Settings, the account menu) |
| Note | `.note` | — | one quiet line for a connection that isn't set up, on a page that isn't about it (Plans: Google Calendar; Ideas: looking things up) |
| Kind label | `.kind` | — | a kind of idea: icon + word, never a pill |
| Weekend suggestions | `.suggest` inside a Vera bubble | — | Vera's longest message: a short list of ideas with when, drive, price, who, and a “Plan it” form each |
| Read-only to-do | `.todo--ro` | — | a kid's own to-do: the setter's avatar as lead (never a box or ring), a dashed “Not done yet”, and “Tell Vera I did it” (a link that fills her chat box) |
| Key/value | `.kv` | — | facts about one thing |
| Empty state | `.empty` | `--center` | any list or card with nothing in it: what will appear, and how to start it |
| Locked | `.locked` | — | "Ask a parent" where something isn't a kid's to change |
| Back link | `.crumb` | — | first thing on a detail page |
| Person picker | `.people` › `.person-tile` | `[aria-current]` | sign-in |
| Specimen | `.specimen`, `.sheet-sec` | `--wide` | the states sheets only |
| Thread | `.tl` › `.tl__grp` › `.tl__h` + objects; `.tl__when` (margin) | `.tl__grp--now`, `--today`, `--late`; `.tl--narrow` (Plans); `.tl__when--big` (the next plan's day), `--now`; `.tl__note`, `.tl__count` | the spine of Home, the kid's Home, To do and Plans' Coming up (§0) |
| Ticket | `.ticket` › `.strip` + `.ticket__body` (`__tags`, h3, `.meta`, `__acts`) | — | the next plan, once per page |
| People strip | `.strip` › `i.pN` (one per person) | `i.p0` (Everyone: neutral) | down the left edge of every ticket and plan row; decorative (`aria-hidden`): the names are in the meta |
| Plan row | `.plan-rows` › `.tl__i` › `.plan-row` (`__kind`, `__title`, `.meta`) | `--next` (ink edge and shadow) | plans after the next one |
| Wish | `q.wish`; `.rank__title` | — | a wish in her words: Familjen italic, quotes in `--p-mark` or `--me-mark` |
| Wish row / wish list | `.wish-row` (Home: who added, the wish, the count, `1 to decide`); `.wishlist` › `.wl` (the kid's Home) | `.wishlist--mini` | wishes outside the Wishes page |
| Idea chip | `.mini-ideas` › `.idea-chip` (`__kind`, `__title`, `.meta`, `.tag`) | — | "Just added to Ideas" |
| Vera's line | `.vline` (`svg.vs--sm` + text) | — | one line in Vera's typed voice on paper |

---

## 3. Words

One word per thing, on every page, in Vera's replies and in her Telegram messages.

| Thing | Say | Don't say |
|---|---|---|
| the whole family | **Everyone** (house avatar) | Household, Anyone (except "Anyone" as the no-filter choice), All |
| a to-do with no date | **No date** | Any time, Whenever, Whenever suits |
| Telegram / Google Calendar | **Connected / Not connected**; buttons **Connect Telegram**, **Connect Google Calendar** | linked, set up, bot |
| AI keys | **Added / Not added**; **Add key** | Set |
| the weekly message | **Weekend suggestions** | digest, weekend ideas |
| web lookups | **looking things up**; "**look up**" as a verb | lookups (as a noun on family pages) |
| AI calls | **questions answered** | calls, requests, tokens |
| Vera at the limit | **Vera is resting until midnight** (kids: "until tomorrow") | paused, quota, rate limit |
| provider down | **Vera can't answer right now** | error, outage, 503 |
| health states | **Working · Could be better · Needs a look · Not working · Off** | OK/Warning/Error |
| Vera's health | **Vera is ready** (pill; “Ready” on the phone) · **resting until midnight** · **can't answer right now** | answering (kept for a reply being written: “Vera is writing back”) |
| a quick capture | **Quick idea**, button **Save idea** | thought, jot, note |
| an idea that happened | **We went** (button), **Went Thu 1 Oct** (tag) | Mark as been, Done |
| the backup key | **Add a backup key** (everywhere except the key table, which says **Add key**) | Add a key |
| spelling | **British English**, the app's own: colour, kilometres, cancelled, tick off | US spellings |
| plan status | **Tomorrow · Planned · Went Thu 1 Oct** | Scheduled, Completed |
| wish answers (kids and parents alike) | **Yes! · Thinking about it · Not this time · No answer yet**; the nav count is “1 to decide” | Approved, Denied, Pending, To decide, Not decided yet |
| something kept from kids | **Surprise · hidden from Maya**; in a narrow tile, the lock and **Hidden from Maya**. Always says who | private, secret, a bare "Surprise" |
| the starter password | "everyone shares one family password" | the installer's password |
| who can change Settings | "Only admins can change these, and right now that's Sam" | "Only Sam" |
| a backup AI | "If it's down, Vera switches to" / **No backup** | fallback |
| late | "**6 days late**" (parents); "**Was due Sun 27 Sep**" (kids) | Overdue (except the group heading on To do) |

Errors are written as the fix: "Give the idea a name", "A link starts with https://". Never "invalid" or "required field".

---

## 4. Roles

| | Admin (Sam) | Parent (Alex) | Kid (Maya, Theo) |
|---|---|---|---|
| Nav | everything plus *Behind the scenes*: Status, Settings, Family | everything, no *Behind the scenes* | Home, Chat, My wishes, My to-dos, Plans, Ideas, What Vera knows |
| Phone tabs | Home, Plans, **Chat** (middle), To do, Ideas; Wishes, What Vera knows, Status, Settings, Family and Sign out are in the **account menu** behind the avatar (`more.html`) | same, without Status/Settings/Family | Home, Wishes, **Chat** (middle), Plans, To do; Ideas, What Vera knows and Sign out in her menu (`more-kid.html`) |
| Health pill, cost, models, setup | yes | pill and cost; no setup | **never** |
| To-dos | all; tick, add, edit | all; tick, add, edit | **only her own, read-only**; "Sam or Alex tick these off"; she can tell Vera she's done |
| Ideas, plans | change; rate plans | change; rate plans | read only; no faces, no Add, no Edit; "Ask a parent" where a change is expected |
| Wishes | decide | decide | add, rank, take off; sees answers in words |
| Chat | family chat + reads kids' chats | same | own chat + family chat, within her daily message count; warned gently at 5 left; no “Share where I am” |
| Gifts | shown, tagged "Surprise · hidden from …" | same | **left out entirely** (no row, no count, no greyed item) |

Whether a kid may tick her own to-dos or rate a plan is a *family* decision. The app currently says no. If the family allows it later, the kid's to-do row becomes the normal `.todo` with a tick, and `.faces` appear on her Home. No new component is needed.

A kid who opens an admin URL gets `grownups.html`, never an error.

---

## 5. Phone rules (≤ 820 px)

1. **The phone is its own layout, not the desktop stacked.** The sidebar becomes a 56 px top bar (brand, health pill for parents, and the avatar that opens the account menu, with a dot when something inside needs checking) and a **fixed bottom tab bar** of five, role-aware, **with Chat in the middle** as a small pane of Vera's glass (`.tab--vera`, charcoal with a phosphor icon), so writing to Vera is one thumb away from any page. `--tabbar-total` = 68 px + `env(safe-area-inset-bottom)` sets its height and the body's bottom padding, and `scroll-padding-bottom` keeps the focused control clear of it. The current tab has a 3 px green top bar as well as its tint; the Chat tab, when current, gets a green ring round its pane instead.
2. **The list you came for is in the first screen.** On Home the composer leads at full width (box and icon Send, short starters), then the thread begins (the margin narrows to 52 px, the rail to 22 px), so the next plan's ticket shows above the tab bar. The thread's order is the desktop's: Next up, To do, After that (a link: "3 more plans this month"), How did it go, Wish lists, Just added to Ideas (kids: Next up for you, My wishes, My to-dos, After that, Just added to Ideas). Quick-adds are one line; options, filters and sorting fold into `<details>`.
3. Ideas become compact rows: tile, title, "who · drive", tags underneath. The radar folds behind "Show the map" after the rows.
3a. **To do starts with one row to add a to-do** (box and Add) at the top of the list; who, when and the reminder fold beneath it. Nobody is picked by default.
4. **Plans: Coming up first (the thread), then the month header and the Month/List switch, then the month at a glance, then How did it go.** The month grid becomes a month at a glance: day cells are whole-cell links with person markers and a full spoken label. Weekday headers are single letters. A spill-over day shows its month in small capitals beneath the number ("28" over "SEP"), so it never wraps.
5. Settings and More rows use grid areas: icon | text, tag | chevron. The chevron never wraps.
6. The Status model table folds away and stacks; actions sit under their line.
7. **Chat is an app-height room** (on screens shorter than 560 px it falls back to normal page scroll): pills, the privacy line, a scroller that opens at the newest message (column-reverse), the box pinned above the tab bar, and a pinned "Earlier messages" bar with a fade at the top edge. The transcript's time margin folds away: the time follows the name.
8. Starters and choice pills **wrap**; they never scroll sideways. Only the conversation pills scroll, as one row.
9. Nothing scrolls sideways at 390 px; test at 320 px too.
10. In full-page screenshots, the fixed tab bar appears where the first screen ends (844 px). That's correct.

---

## 6. States

Drawn in `states.html`, `states-actions.html` and `states-content.html`.

| State | Where | What shows |
|---|---|---|
| Today's limit reached | pill, Home Ask card, chat box, Status | pill `--rest` "Vera is resting until midnight"; the box closes (`disabled`) with a warn banner giving the reason; Vera says so in the chat; admins get **Change the limit**; Status hero warn plus a full meter |
| A kid's messages used up | kid chat and Ask card | "You've sent all 20 of today's messages. You can write to Vera again tomorrow." No money |
| Vera resting, as a kid sees it | kid chat | "Vera is resting until tomorrow." No money, no limit |
| Vera can't answer | pill, chat, Status | pill `--down`; the box closes with an alert banner; Vera's system bubble keeps the message and offers **Try again**; Status hero alert names the company and the fix (add a backup key); the Vera health row says **Not working**. Kids: "Try again a bit later", no company names |
| Reply pending | chat | the user's bubble, then a dashed Vera bubble "Vera is thinking" (dots; no animation under reduced motion); the box is closed: "The box opens again when she's done." |
| Message failed | chat | the user's bubble with a dashed red edge and "Didn't reach Vera · Try again" (a resend form). The box stays open |
| After an action | the list it changed | flash with Undo, focus moved there; a ticked row stays in place, struck through, for this page view |
| Form errors | any form | error summary first (focus there), links to fields; per-field message above the box tied with `aria-describedby`, `aria-invalid="true"`, thicker red edge; typed values kept; `<details>` holding an error opens |
| First empty day | Home and every list | each empty card says what will appear and how to start it, usually a starter to Vera; setup leads |
| No results | Ideas, To do | "Nothing matches "pizza" for Theo", every active filter in words, **Clear search and filters**, and "Save "pizza" as an idea" |
| Busy day, long plans | calendar | two events, then "+N more" (links to that day in the list); the phone shows up to three markers (initials, the house, a hollow ring). A plan over several days is one bar (`.len2…7`); across a week boundary it is split (`.ev--to` › / `.ev--from` ‹, “continues” in the spoken label) |
| Long titles | everywhere | wrap in full; only calendar events clamp to two lines (full title in the spoken label and on the plan page) |

---

## 7. Accessibility checks

Contrast is computed from the tokens (WCAG 2.2). AA needs 4.5:1 for text and 3:1 for control edges.

| Pair | Use | Light | Dark |
|---|---|---:|---:|
| `--ink` on `--paper` | body text | 15.8 | 16.5 |
| `--ink-2` on `--card` | secondary text | 9.5 | 10.7 |
| `--ink-2` on `--paper` | the margin clock's dates | 8.7 | 11.6 |
| `--ink-3` on `--card` | quiet text, on card | 6.6 | 7.0 |
| `--ink-3` on `--paper` | quiet text and weekday capitals, on the page; message times | 6.1 | 7.6 |
| `--ink-3` on `--paper-2` | quiet text on the grey well | 5.4 | 6.5 |
| `--ink-3` on `--field` | placeholders | 6.7 | 6.2 |
| `--link` on `--card` | links | 6.3 | 9.9 |
| `--link` on `--paper` | links on the page | 5.7 | 10.9 |
| `--vera` on `--card` | Vera's name and green text | 6.3 | 13.5 |
| `--edge` on `--field` | field and tick edge (3:1) | 4.0 | 4.5 |
| `--edge` on `--card` | field edge, icon buttons, quiet buttons (3:1) | 4.1 | 5.0 |
| `--edge` on `--paper` | controls on the page (3:1) | 3.7 | 5.4 |
| `--node` on `--paper` | the thread's hollow node (decorative, 3:1 anyway) | 3.1 | 5.4 |
| `--alert` on `--paper` | a late date in the margin | 6.0 | 8.3 |
| `--vera` on `--vera-paper` | Vera's name on her message | 5.8 | 13.2 |
| `--ink` on `--vera-paper` | Vera's typed words | 16.0 | 14.8 |
| `--today-bg` on `--paper` | the next plan's node (3:1) | 4.3 | 14.8 |
| `--on-primary` on `--primary` | primary button | 17.0 | 16.4 |
| `--primary` on `--paper` | primary button against the page (3:1) | 15.8 | 16.5 |
| `--card` on `--ink` | date-tile weekday band | 17.0 | 15.1 |
| `--on-today` on `--today-bg` | today's band on Home's tile | 4.7 | 14.7 |
| `--on-today` on `--today-bg` | today's number on the calendar | 4.7 | 14.7 |
| `--on-vera` on `--vera-bg` | done tick, meter, flash check, "Yes!" sticker | 4.7 | 11.0 |
| `--on-send` on `--send` | Send on Ask | 14.6 | 14.8 |
| `--ask-ink` on `--ask-bg` | composer text | 18.5 | 15.3 |
| `--ask-ink-2` on `--ask-bg` | composer quiet text, "Write to Vera" label | 11.1 | 11.4 |
| `--ok` on `--ok-soft` | tag Working | 5.4 | 10.2 |
| `--warn` on `--warn-soft` | tag Needs a look | 6.5 | 9.0 |
| `--warn` on `--card` | tag Could be better | 7.3 | 9.8 |
| `--alert` on `--alert-soft` | tag Not working, late badge | 5.6 | 7.1 |
| `--alert` on `--card` | late text, errors | 6.6 | 7.6 |
| `--ink-2` on `--paper-2` | tag Off | 7.6 | 10.4 |
| `--vera` on `--vera-soft` | the calm "Vera is ready" pill, current nav | 5.5 | 12.5 |
| `--p1-ink` on `--p1-soft` | slot 1 name in a bubble | 5.6 | 8.6 |
| `--p3-ink` on `--p3-soft` | Maya's name in a bubble; her current tab label | 5.5 | 9.1 |
| `--ink` on `--p3-soft` | text in Maya's bubble | 14.4 | 13.7 |
| `--everyone-ink` on `--everyone` | Everyone's house avatar | 6.9 | 5.6 |
| `--everyone-mark` on `--card` | Everyone's dot (3:1) | 4.0 | 6.7 |
| `--ink` on `--paper-2` | words on a grey (several people) calendar block | 13.2 | 14.6 |
| `--on-p` on `--p1` … `--p8` | avatar letters, calendar initials, **words on a one-person calendar block** | 6.3 / 6.6 / 6.6 / 8.3 / 8.1 / 6.4 / 9.8 / 7.5 | 6.7 / 6.9 / 7.0 / 8.8 / 8.5 / 6.8 / 10.3 / 7.9 |
| `--p1…8-mark` on `--card` | dots, rules, rings (3:1) | 3.9–4.8 | 7.9–10.9 |
| `--p1…8-ink` on `--p1…8-soft` | names on soft, a kid's tab and nav (lowest of eight) | 5.2 | 8.6 |
| `--card` on `--ink` | selected segment, chosen pill | 17.0 | 15.1 |
| `--phosphor` on `--glass` | phosphor on glass: pill, pane lines, focus ring | 14.7 | 15.6 |
| `--glass-ink` on `--glass` | pane text | 16.3 | 17.3 |
| `--glass-ink-2` on `--glass` | pane quiet text, resting pill | 10.6 | 11.3 |
| `--glass-alert` on `--glass` | "can't answer" pill | 8.2 | 8.7 |
| `--cursor` on `--card` | wordmark cursor (3:1, non-text; it sits on the white sidebar and bar) | 3.9 | 13.5 |
| `--ask-edge` on `--ask-bg` | the Ask box's edge at night (3:1) | n/a | 5.0 |
| Ask rim #3E8A66 on `--paper` | the Ask card's edge at night (3:1) | n/a | 4.5 |

The glass pane has no contrast duty of its own in the dark (it is #070A09 on #0C100F): its 1 px `--glass-line` rim and the phosphor inside carry it. **Focus on glass is phosphor** (`.pane`, `.instrument__pane`, `.pill-health` set `--focus: var(--phosphor)`, 14.7:1), because the ink ring is 1.2:1 there.

Disabled controls are exempt, but each also carries its reason in words.

**Checklist for every page**
- One `h1`; headings in order. (The margin clock is `aria-hidden`; each row carries its date in text.) Chat on the phone keeps its `h1` visually hidden, not `display:none`.
- A visible "Skip to content" link on first Tab. A 3 px focus ring on everything (phosphor on the Ask card). Whole-card links show focus with `:focus-within`.
- No meaning by colour alone: late says "6 days late", tags carry words, calendar events carry a spoken label, badges carry words.
- Every control is named: ticks "Mark done: …", faces "Loved it (Silver Falls hike)", move buttons "Move Ice skates up", Edit "Edit Call the dentist about Theo".
- Form fields have labels; errors are tied with `aria-describedby` and `aria-invalid`; the summary has `role="alert"`; flashes have `role="status"`.
- Chat thread: `role="log"`, focusable (`tabindex="0"`), named.
- Targets are 44 px; type is 14 px or more (13 px only on tab labels and overlines), set in rem; the top and tab bars use `min-height`.
- **Nothing blinks for more than five seconds** (2.2.2): the wordmark cursor blinks twice and stays lit, the pill's dot breathes once. Only things that end on their own move longer: Vera's busy screen and the typing dots, while a reply is on its way.
- `prefers-reduced-motion`: nothing moves at all.
- **Never `display:none` beside an `aria-hidden` stand-in.** When a short label replaces a long one on the phone (starters, Edit links), the long one is hidden with the `.sr` clip pattern, so it stays the control's name.
- Icon-only buttons have `--edge` borders (3.8:1); a disabled one is `--ink-3` with a dashed edge and keeps its reason in words.
- The Status figures stay on one row on phones from 360 px; below that (320 px, 400 % zoom) they stack in one column. `forced-colors`: selected nav, tabs, segments, conversation pills, choices, person tiles, tags and today get real borders.
- Reflow: no sideways scrolling at 320 px or at 200 % zoom (zoom lands on the phone layout).
- Language is grade 4–7. Kids' pages are read aloud for tone.

---

## 8. Notes for the engineer (Jinja, CSP, scripting off)

**Delivery**
- One stylesheet, `/static/style.css`.
- One sprite, `/static/icons.svg`: `{{ icon('car', 'sm') }}` → `<svg class="icon icon--sm" aria-hidden="true"><use href="/static/icons.svg#i-car"/></svg>`. The mockups inline the sprite only because `file://` blocks an external `<use>`.
- Fonts in `/static/fonts/`, with `<link rel="preload" as="font" type="font/woff2" crossorigin href="/static/fonts/atkinson-400.woff2">`. The preload is left out of the mockups for the same `file://` reason.
- CSP: `default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'`.
- **No `style=""`, no inline `<script>`, no `on*=` attributes.** Data-driven geometry uses SVG presentation attributes, which CSP allows: the spend meter's `<rect width>` and `<line x1>`. Calendar placement uses classes (`.c1…c7`, `.span2`, `.lane1…3`).
- Add a CI check that fails on `style="` or `<script>` without `src` in `templates/`.

**Macros** (one per component in §2)
- `page(role, current)` wraps the shell (tab bars per role; the account menu behind the avatar): sidebar or top bar, role-aware nav and tabs, skip link, sprite.
- Then `card`, `banner(tone, size)`, `tag(state)`, `badge(kind, n, word)`, `avatar(person, size)` (emits `av p{{ person.slot }}`), `vera_screen(size, state)` (emits an `aria-hidden` `svg.vs` from the geometry table in §9), `brand_mark(size)` and `wordmark()`, `item`, `todo(todo, viewer)` (picks `--late`, `--done` or `--ro` from the viewer's role), `composer(viewer, state)`, `starters(list)`, `field(...)`, `choices(name, options, required)`, `rank(wish, viewer)`, `idea_card`, `calendar_week`, `empty(title, text, action)`, `flash(message, undo_url)`, `error_summary(errors)`.
- `health(area)` returns one `(state, words, action)` per area: Vera, Spending, Sign-in, Backup, Telegram, Google Calendar, Looking things up. **Every page reads it** (pill, Home, Status, Settings, Ideas banner), so they can't disagree. Settings summary lines are computed, never written as copy.
- `visible_to(viewer)` filters every list for kids: own to-dos only, gifts and surprises removed. Counts are taken *after* filtering.

**Works with scripting off (required)**
- Reading every page, and every form: tick, Undo, add, edit, rate (faces), answer a wish, move a wish up or down, sign in, search and filter (GET), send a message.
- Pattern: POST → redirect → GET (PRG), with a flash in the session and `#anchor` to the changed list. Every form carries a CSRF token.
- Starters: a complete question is `<button name="prompt" value="…">` in its own form; a stem is `<a href="?draft=…#ask-text">`, and the server renders the draft into the textarea with `autofocus`.
- Chat opens at the newest message without script (`.scroller` is `flex-direction: column-reverse` around one `.thread`). The server sends the latest 30 messages; "Earlier messages" is `?before=<id>`; the last message has `id="latest"`.
- **While a reply is pending**, the page includes `<meta http-equiv="refresh" content="3">` (CSP doesn't block it), the box is `disabled`, and the pending bubble carries a visible **“Check for her answer”** link to `#latest`. Remove the meta tag as soon as Vera has answered. After 60 s with no reply, mark the message failed.
  - **Accessibility concern, recorded for the engineer (WCAG 2.2.1, 3.2.5):** a repeating reload moves a screen-reader user back to the top and a magnifier user loses their place. The family's app works this way, so it stays, but keep it as short as possible: back off server-side (3 s, then 5, then 10 s, from the pending message's age), never refresh after 60 s, and keep `chat.js` polling as the normal path so the meta tag is removed on load whenever scripting is on.
- `<details>` for filters and options: no script. Open it server-side when it holds an error or an active filter.
- The month grid's day links, the To do filters and the Plans Month/List switch are plain links.

**Needs a small script (from `/static/*.js`, all optional)**
- `chat.js`: while a reply is pending, poll `/chat/pending` quietly and swap the bubble instead of reloading. It removes the meta refresh on load.
- `draft.js`: keeps an unsent message in `sessionStorage`, and fills the box from a stem starter without a reload.
- `location.js`: *inserts* the "Share where I am with this message" checkbox (it isn't in the server HTML) and, when ticked, adds the position to the form. Kids' label: "(ask a grown‑up first)".
- `password.js`: *inserts* the Show button next to password fields and toggles `type` and `aria-pressed`. Paste and password managers always work.

None of these may be needed to read, send or change anything.

**Data rules the design depends on**
- A to-do knows who set it (`Set by Alex`) and who owns it.
- A wish has rank, answer, who answered and their words.
- An idea or to-do can be a gift or surprise, with the people it's hidden from.
- Plans know who they're for (one person → that person's colour and initial; several or Everyone → neutral with each person's avatar or the house). The macro derives the colour from the people; a template never picks it.
- Kids have a daily message count.

---

## 9. The brand

Thread is the household's running conversation: a quiet porcelain page, one line down it, the people in their bright pens. FamilyDB is the small screen that keeps the conversation going. The brand is that pairing, used a little: **a pane of dark glass with green light, and a typed voice.** The mark is unchanged (not recoloured). The layout, the components and every check in §7 are unchanged by it.

### The brand rule

**The page and the bright pens are the family's. Phosphor on charcoal glass, and the typed mono, are FamilyDB's and Vera's.** Glass and phosphor appear only where one of three things is:

1. **the brand**: the mark, the wordmark, and the brand moments (sign-in, a family's first empty day, the grown-ups page a kid lands on, the missing page);
2. **Vera**: her screen, the Ask card (charcoal glass by day, green-rimmed glass at night, with a phosphor Send);
3. **something live**: the status pill when it has something to say (writing back, resting, can't answer), a reply on its way, the cursor in her box, today's date. When Vera is simply ready the pill is calm and on paper.

Never on the family's own things: names, ideas, to-dos, wishes, plans, and the buttons and links that act on them (those use `--link`, Vera's green by day and a lighter green at night, and `--primary`, ink by day and inverted at night; never phosphor). **The mono is Vera's and the clock's**: her words, the margin's times and dates, label capitals, and the lines on glass. The family's own words are never in the mono, and phosphor never touches paper. Every touch says something true; nothing is only ornament. No dark page in light mode, no CRT curvature, no vignettes, no heavy scanlines, no pixel font.

### The mark

A little monitor with a smile, drawn in one 2 px round-capped stroke (24-unit grid), phosphor `#6DFF9C` on a charcoal `#0E1312` rounded square (radius 8 on 32). It is FamilyDB's, **never Vera's face**, and never stands in for her.

| Use | Size | File or class |
|---|---|---|
| Favicon | 16 px | `brand/favicon-16.png` (from `brand/mark-16.svg`, hand-pixelled so the eyes and smile stay apart) |
| Favicon | 32 px, any | `brand/favicon-32.png`, `brand/favicon.svg` |
| Home-screen icon | 180 px | `brand/apple-touch-icon.png` |
| Home-screen icon | 512 px | `brand/icon-512.png` (from `brand/mark-512.svg`) |
| Sidebar | 34 px | `.brand .mark-fdb` beside the wordmark |
| Phone top bar | 30 px | the same, smaller |
| Settings colour key | 24 px | `.mark-fdb--sm` |
| Glass panes | 64 px | `.pane__mark`, with a soft phosphor glow |

- **Clear space:** at least a quarter of the mark's size on every side (8 px at 34). In the bar, the wordmark sits 10 px away.
- **On the page:** the charcoal square is the mark's own glass, so it sits directly on the white sidebar or top bar; no extra frame or shadow.
- **On dark:** the same file. At night the square is close to the page, so it keeps its own edge from the stroke; nothing is inverted. Never recolour the stroke (no white, no `--vera` green), and never use it without its square.
- Head tags: `favicon.svg` (`image/svg+xml`), `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png` (180). The 512 is for the web manifest.

### The wordmark

"FamilyDB" in **Familjen Grotesk 700**, letter-spacing −0.03em, followed by a **lit cursor**: a block `.42em × .86em`, 0.14em after the B, radius 1.5 px.

- Sizes: 22 px in the sidebar, 20 px in the phone bar, 18 px inside a pane. It is always beside the mark; the link around both is named "FamilyDB, home".
- **On the page:** ink letters, cursor `--cursor` (#12945A, 3.6:1 on the page as a non-text mark) with a faint glow.
- **On dark and on glass:** near-white or glass-ink letters, cursor `--phosphor` with `--phosphor-glow`.
- The cursor blinks twice (2 s each, mostly on), then stays lit: no blinking past five seconds (WCAG 2.2.2). Under `prefers-reduced-motion` it never blinks. The cursor is `aria-hidden`.

### Vera's screen

Vera is never drawn. Where she speaks there is a small pane of glass, as if she were typing: a **rounded square** (never round: round means a person), a **lit rim**, a few short **lines of light**, and her **signature, a lit prompt `>▮`** in the bottom-left corner. The prompt is the same at every size; small sizes have fewer lines, not smaller ones. It is drawn as inline SVG, crisp, with no blur and no scanlines, so it reads at 24 px on a phone. It works whatever the family calls her.

| Size | Class | Lines | Where |
|---|---|---|---|
| 24 px | `.vs--sm` | 1 | Settings colour key, "Suggested by Vera" rows |
| 32 px | `.vs` | 2 | chat messages (her avatar slot), the pending and failed bubbles; a receipt sits inside her message |
| 40 px | `.vs--lg` | 3 | the Ask card, Home's Vera row, Status' Vera row |
| 56 px | `.vs--xl` | 3, larger | the kid's empty chat (the one place she is introduced) |

Geometry (per size, in px): radius 6 / 8 / 10 / 14; rim 1 px inside the edge; lines 3 px tall (4 at 56), rounded; prompt stroke 1.75 / 2 / 2.25 / 3. The macro `vera_screen(size, state)` holds the table.

| State | Class | Looks like |
|---|---|---|
| Ready | `.vs` | rim at 60 %, lines at 45 % with the newest at 90 %, the prompt and cursor fully lit, a soft halo (`--vs-halo`) |
| Answering | `.vs--busy` | the lines light one after another and the cursor blinks, only while a reply is on its way |
| Can't answer | `.vs--off` | the light goes out: rim, lines and prompt turn `--edge` grey, the cursor is hollow, no halo. Visible on white and on charcoal. The words beside it say why |

- The whole screen is `aria-hidden`; Vera's name is always in text next to it.
- **Motion:** only `--busy` moves (it stops when the reply lands), and nothing moves under `prefers-reduced-motion`.
- Halo: `--vs-halo` is a 3 px drop shadow, green by day and phosphor at night, so the pane reads as lit glass on white and as a screen, not a hole, on charcoal.

### The mono: Vera's voice and the clock

Atkinson Hyperlegible Mono (`fonts/atkinson-mono-var.woff2`, 18 KB, weight 200–800; replaces JetBrains Mono). It is used for four things: **Vera's words** wherever she speaks (16 px, 400, tracked −0.03em, on `--vera-paper` on paper); **the margin clock** (times beside messages, dates beside the thread: 14 px 500, weekday in 13 px capitals); **label capitals** (eyebrows, kinds of idea, group labels, date-tile and calendar heads); and **the lines on glass** (the status pill when it has something to say, the line inside a pane, the rail's "Write to Vera"). The family's words, names, to-dos, plans and wishes are never in the mono. Its receipts, suggestion cards and buttons inside Vera's messages switch back to Atkinson, because they are the family's things. The radar's labels stay Atkinson. Numbers and units are kept together with no-break spaces.

### Phosphor elements, their tokens, where they may and may not appear

| Element | Tokens | May appear | May not |
|---|---|---|---|
| The mark | `--glass` (fixed #0E1312 in the file), `--phosphor` | bar, sidebar, sign-in, panes, favicon, icons, Settings' key | as Vera; inside a message; on the family's items |
| Wordmark cursor | `--cursor`, `--cursor-glow` (dark: `--phosphor`) | after "FamilyDB" only; the caret in Vera's box (`caret-color`) | anywhere else as decoration |
| Vera's screen | `--glass`, `--glass-line`, `--phosphor`, `--vs-halo` | wherever Vera is: Ask, chat, Status and Home rows, pending, Settings' key, the kid's empty chat | for a person; as a decoration with no Vera |
| Status pill (when there's something to notice) | `--glass`, `--glass-line`, `--phosphor`, `--phosphor-glow`, `--glass-alert` | sidebar and phone bar, parents only. Writing back: phosphor mono, the dot breathes until the reply lands. Resting: `--glass-ink-2`, hollow dot. Can't answer: `--glass-alert` #FF8B74 (8.2:1 on glass), square dot. When Vera is ready the pill is not glass at all: `--vera-soft`, `--vera`, Atkinson 700, a still dot | kids' pages; anywhere it isn't Vera's real state; "ready" |
| Glass pane | `--glass`, `--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--phosphor` | the four brand moments: sign-in, a first empty day, the grown-ups page, the missing page. Faint scanlines inside are fine | as a card style; around the family's content; more than one per page |
| The radar | `--glass`, `--phosphor` at 14–25 % for rings and axes, `--glass-ink` and `--glass-ink-2` for labels | Ideas only, in its own band after all the cards (folded behind "Show the map" on the phone). Drive time is distance from home on a piecewise scale that gives the first half hour 70 % of the radius (rings at 15 min, 30 min, 1 h, 2 h, 3 h, labelled on alternate sides of the north axis); direction is bearing, north up; "Home" marks the middle. Each dot carries the idea's short name ("Pumpkin patch", "Oaks Park"): the first words of its card's title, so a kid can match it. Ideas in the same direction are fanned a few degrees apart. The SVG is `aria-hidden`: the cards are the list, and each card already says its drive time and direction | between the cards; any second page; a separate numbered list; mono labels. One instrument per page at most. If every idea is inside one ring, show the cards alone |
| Composer glass | `--ask-bg`, `--ask-rim`, `--ask-edge`, `--send` | Home's and the kid's composer ("Now"), the rail's Write to Vera, the phone's Chat tab: charcoal glass with phosphor, and at night a 1.5 px green rim | anywhere else |
| Live glow | `--phosphor-glow`, `--vs-halo` | the writing-back pill, the panes, Vera's screen, the wordmark cursor | the calm "ready" pill, chat bubbles (Vera's included), cards, buttons |

The radar is drawn twice from the same data, so names stay readable: a wide 860 × 440 plot for the desktop (names 15 px, drawn at 1:1) and a narrow 360 × 400 plot for the phone (names 14 px). Ring and compass labels are 13 px Atkinson; every label position is set per idea in the data, so nothing sits on a compass letter.

### Brand moments

- **Sign-in:** a pane with the mark, the wordmark and "awake, Saturday 3 October", then "Who's using FamilyDB?" and the people on paper.
- **A first empty day** (`states-content.html`): "FamilyDB is set up and awake. Welcome, Sam. This is your family's table." on glass, then the empty cards on paper.
- **The grown-ups page** (`grownups.html`): the mark alone at 64 px, glowing, above the explanation; the explanation stays on paper. The mark is its own glass, so no pane around it.
- **The missing page** (`404.html`): a centred pane, the mark, "404 · nothing at this address" in the mono, then "This page isn't here", Go to Home and Ask Vera to find it.

### The dark theme: the thread at night

At night the page is deep ink (`--paper` #111018, `--card` #1A1924), the ink is near-white (#F0EFF6), the thread is a dim violet line (#3A3848), Vera's things, now and today are phosphor (`--vera`, `--today-bg` #6DFF9C), amber (`--warn` #F5B94A) is for what needs a look, coral (`--alert` #FF8B74) for late and broken, including a late date in the margin. People keep their colours: the pens are the same bright colours with the same dark letters (6.8:1 or more), and washes and dots use the lightened `-ink`/`-mark` on tinted `-soft`. Vera's typed messages sit on a dark green page (`--vera-paper` #141F1B).

**The hierarchy holds at night.** The composer stays the one lit block: green-rimmed glass (`--ask-bg` #0E1A17) with the brightest edge on the page and an edged box; the rail's Write to Vera and the phone's Chat tab share it. The primary button inverts to near-white with dark words, the next plan's edge and shadow invert with it, and links are a lighter green (`--link` #8BD3B4), never phosphor. Only the pill, the panes and Vera's screen glow. Every pair is in §7.

By day the composer is the brand's charcoal glass (`--ask-bg` #13121F) with a phosphor Send, so the one dark block on the page is plainly FamilyDB's; its text is 18.5:1.
