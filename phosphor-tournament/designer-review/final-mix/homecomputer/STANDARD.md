# FamilyDB · House Log (round 6) · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth; this document says how to use them.

**The rule behind everything:** FamilyDB is the family's logbook. **Vera keeps the ruling, everybody writes the lines.** Every list has a margin, and dates, times and numbers go there in the mono. The words go beside it, in Atkinson, and each person writes in their own colour. Sections are ruled heads, not boxes. A bright colour means *a person*, orange means *this one* (today, the one button, what to do next), green means *Vera*, ink means *something you picked*, and red means *late or broken*.

*House Log* replaces Felt Tip (`history/`). The pages, words and states are unchanged. Layout, type, colour and the shell changed (see `DIRECTION.md`). New markup hooks: `.runhead`, `.greet`, `.lede--info`, `.ask--hero`, `.board`, `.next--narrow`, `.leave`, `.route`, `.drive-fig`, `.dir-*`, `.log__m`, `.todo--m`, `.item--log`, `.item__body`, `.ideas-head`, `.ranks--mini`, `.wishline`, `.adder--log`, `.home-grid--kid`, `.notes`. Kids' pages keep the body class `kid me-pN`.

---

## 0. Layout

**The page.** On the desktop, the brown-black panel (248 px) sits on the left and the page on the right (max 1120 px). Every page except Home opens with a **running head**: `.runhead`, `aria-hidden`, with "FamilyDB · *page*" on the left and the date on the right, in wide capitals over a hairline. On a kid's pages it reads "Maya’s pages · …" and is ruled in her colour. Then the page title: one `h1`, condensed, 40 px. Home has the one-line greeting instead (below).

**The margin.** `--mw` is 116 px on the desktop, 76 px in side columns and 68 px on the phone. It is the column for *when*: a date and a time in Martian Mono (`.log__m`: the date in 650 weight, the time or weekday under it), a big condensed date (`.dt`), a rank, an entry number, or who and when in the chat. Lists that have a margin:

| List | margin | column 2 (44 px) | body | trail |
|---|---|---|---|---|
| To-dos (`.todo.todo--m`) | **the due column**: due date and weekday, and "6 days late" in red under it ("No date" when none) | the tick (or, for kids, who set it) | title, owner, reminder, tags | Edit |
| Plans (`.item.item--log`) | date, time | `.route`: the **route stripe** (6 px, split into the colours of the people going; Everyone grey) | title, kind, people | `.drive-fig`: the drive time as a figure |
| Next up (`.next`, the departure board) | "Tomorrow" stamp, date, and the time in 36 px condensed | `.route` | 36 px title, people, drive, actions | `.leave`: **Leave by 12:30 pm**, 72 px, behind a 2 px ink rule: the biggest figure on Home |
| Chat (`.msg`) | name (Barlow Condensed capitals) and time (mono), right-aligned, then the face | | the words, beside a 3 px rule in the person's colour | |
| Wishes (`.rank`) | the rank, 52 px condensed | | wish, answer, the parent's note | move up and down |
| Ideas (`.idea`) | No. (the list is `<ol reversed>`, so the newest has the highest number) | | kind · idea · for · drive · status | |

**Sections, not cards.** `.card` is now an open section: a 3 px ink rail (`--rule`) over a condensed head (`.card__head h2`, 26 px). It has no box, padding, radius or shadow. Rows inside are divided by hairlines. Only three things sit on a tinted ground: the setup panel (`.card--setup`, amber), banners, and Vera's glass (Ask, panes, the radar).

**Home** (`.home-grid`): **the greeting is one line** (`.greet`: the date in orange Barlow Condensed capitals, then "Good morning, Sam." as a 26 px `h1`), over a hairline. Under it is **today as information** (`.lede--info`, 22 px ink, with its links). Then **Ask Vera, the hero** (`.ask--hero`, full width), then **Next up as a departure board** (`.board`, full width), then To do (left) and the side notes (right, 320 px: Finish setting up, How did it go, Wish lists, Just added to Ideas, Vera today). On the first screen, desktop and phone, you get the greeting, Ask Vera and the next plan with Leave by. On the phone the setup banner comes after the board. The kid's Home (`.home-grid--kid`) has the same greeting and her Ask hero, then Next up for you (`.next--narrow`: Leave by under the plan) and Ideas on the left, and My wishes and My to-dos on the right.

**Plans:** the month name in 48 px condensed, with the arrows and Today. The month is a ruled table. **Saturday and Sunday are 1.45× wider** (`.cal { --cols }`), because that's where the family's plans are. Every event carries its route stripe down the left edge. Below the month are Coming up (a board: margin, route, plan, drive figure) and How did it go, side by side.

**To do:** the add box is the book's next line (`.adder--log`, its label in the margin). The Open/Done/Cancelled/All tabs and Search come next, then ruled group heads (`.group-h`: "OVERDUE · 3" in red with a red rule, "NO DATE · 1").

**Chat:** conversations as a ruled list on the left (the current one has a 4 px ink bar), and the room as a transcript. The box sits under the words' column.

**Ideas:** tabs, search and filters, then the **index** (`.ideas-head` column heads: No., Kind, Idea, For, Drive from home, Status), then the radar band and Quick idea. **The drive column stays at every width**: a figure (`.drive-fig`) with the direction in capitals beside an arrow turned to point that way (`.dir-n…nw`). Below 1180 px the kind becomes a label over the title and the column heads go. On the phone a row is number, kind, title, for, tags, with the drive figure on the right.

**The panel** (sidebar, from The Board, 248 px): the brown-black keyboard surround (`--band`, the family stripe down its right edge) with putty-white sign lettering (Barlow Condensed 600, 20 px). It holds the brand, Vera's ready pill, the pages with their icons and with counts aligned right (late as a solid red plate, "to decide" as a white-edged plate), the "Behind the scenes" group, and the person and Sign out on a raised plate at the foot. **You are here is an inverted plate**: putty-white with brown-black letters and a 5 px orange edge (the kid's colour on her pages). `.side` re-sets `--ink`, `--line`, `--focus` (phosphor) and the rest, so every component inside reads right on navy. The Log's numbered contents are gone. **Only the panel is brown-black**: no section, card or board on the page takes the band colour. On the phone the top bar is the same brown-black, with the family stripe along its foot, and the tab bar is paper with a 3 px ink rail and the current tab as an ink plate.

---

## 1. Tokens

All values live on `:root` in `style.css` §2. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root`.

### Colour

**Home Computer** (the colour round, `PALETTE.md`, `palette.html`). The family machine of the early 80s set beside FamilyDB's green screen. Each part of the machine has one job: the **putty case** is the page, the **brown-black keyboard surround** is the panel, the **striped badge colours** are the family's eight pens, **one orange key** means "this one", and the **green screen** is Vera's alone. Red is only late.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | #E3E1DC | #171513 | the page: putty, a light warm grey, never cream |
| `--paper-2` | #D4D1CA | #23201C | wells, hover rows, the weekend wash, "Off" tags, disabled |
| `--card` / `--field` | #F6F5F2 / #F8F7F4 | #1E1B18 / #211E1A | keycap white: inputs, tick boxes; today's calendar cell |
| `--ink` / `--rule` | #1D1915 | #EEEAE3 | brown-black text; the ruled heads (3 px), picked controls, the current tab |
| `--ink-2` / `--ink-3` | #3D3731 / #575049 | #CBC4BA / #A59D92 | secondary text and margin times; quiet text and labels (still AA) |
| `--line` / `--line-2` | #BAB6AE / #A29D94 | #37322C / #4B453E | moulded seams: hairlines between rows (decorative) |
| `--edge` | #6C665E | #8A8378 | control edges (3:1) |
| `--band`, `--on-band`, `--on-band-2`, `--band-line`, `--band-hi` | #231C17, #F3F0EA, #C4BBAF, #3C3229, #322921 | #2E251E, #F5F1EA, #C9BFB2, #463A30, #3B3027 | **the panel** and the phone's top bar only: the keyboard surround. Its right edge carries **the family stripe** (four 3 px bands in `--p3 --p4 --p1 --p2`); the phone's top bar carries it along its foot (a kid's top bar has her own 4 px rule instead) |
| `--signal` / `--signal-2` / `--on-signal` | #F07C1E / #F69540 / #1D1915 | #F57F22 / #FF9A4A / #171513 | **the orange key**: the Tomorrow stamp, a Yes!, the edge of "you are here", today's day number. Always a filled key under ink letters |
| `--signal-ink` | #8F3E00 | #FF9B4D | orange as words |
| `--primary` / `--primary-2` / `--on-primary` / `--primary-edge` | #F07C1E / #F69540 / #1D1915 / #1D1915 | #F57F22 / #FF9A4A / #171513 / #F57F22 | the one primary button: the orange key, edged in ink by day |
| `--today-bg` / `--on-today` / `--today-ink` / `--today-rule` / `--today-wash` | #F07C1E / #1D1915 / #8F3E00 / #B35200 / #F6F5F2 | #F57F22 / #171513 / #FF9B4D / #F57F22 / #2A1F15 | **today**: the greeting's date in orange capitals, the calendar's orange day number, a 3 px orange rule over a keycap-white cell |
| `--link` / `--link-line` | #1D1915 / #D2691A | #EEEAE3 / #E0782A | links are ink with an orange underline that turns ink and thicker on hover |
| `--focus` | #1D1915 | #EEEAE3 | the 3 px ring (phosphor on glass and on the panel) |
| `--done` / `--on-done` | #1D1915 / #F6F5F2 | #EEEAE3 / #171513 | a ticked box, the strike-through and a good flash's check: a key pressed in ink |
| `--vera`, `--vera-bg`, `--vera-soft`, `--vera-line` | #0A6A4B, #0B8457, #D3EADD, #9FCFB5 | #6DFF9C, #4FE08A, #0F2419, #22513A | **Vera's green, and only hers**: her name and rule, her tile, the ready pill, receipts, the spend meter |
| `--ok` (+ `-soft`, `-line`) | #17703F | #7FE3A5 | working: the machine is well (Status, banners that went well) |
| `--warn` (+ `-soft`, `-line`) | #8F3E00 on #F3E0C3 | #FF9B4D on #2B1F12 | set this up, needs a look: the orange key as a wash, always with ⚠ |
| `--alert` (+ `-soft`, `-line`) | #B0241A | #FF8B74 | **late, broken, errors**: the only red |
| `--alert-plate` / `--on-alert-plate` | #D3392B / #FFF | same | the late count on the panel |
| `--p1…--p8`, `--on-p1…8` | see below | same | avatars and a kid's tab, under their own letter: `--ink-k` (#1D1915) or `--ink-w` (#F7F5F0), whichever passes AA. `.pN` sets `--on-p` |
| `--pN-soft` / `-ink` / `-mark` | see below | see below | soft: a one-person plan's wash, "mine" in the chat, a kid's current tab; ink: names on soft and on paper; mark: **route stripes**, a person's rule, the ruling of a kid's pages |
| `--everyone…` | #C7C3BB, soft #D9D6D0, ink #3D3731, mark #6C665E | #4D4741, #24211D, #CBC4BA, #A59D92 | Everyone and several-people plans: neutral putty |
| `--me…` | from the kid's slot | same | `.kid.me-pN`: her running head, every ruled head, her h1 underline, her tab and rank 1 |
| Brand: `--glass…`, `--phosphor…`, `--cursor`, `--ask-…`, `--send` | unchanged (§9) | | Vera's glass and FamilyDB's mark; `--ask-ring` is phosphor at 30 % by day |

**The eight pens.** Sticker colours from the badges and stripes of those machines. Round the wheel, deep and light take turns, so neighbours differ in lightness as well as hue. No pink, no pastel, no red, no green.

| Slot | Pen | Avatar, letter | Soft / ink / mark, day | Soft / ink / mark, night |
|---|---|---|---|---|
| p1 (Sam) | cobalt | #2F5FD0, white | #D9E5FB / #2452C2 / #2453C3 | #1B253D / #9EBBFF / #3565D7 |
| p2 (Alex) | violet | #A684E0, ink | #E8E0F8 / #6A47A0 / #8664C2 | #28203A / #CDB5FA / #AC8AE6 |
| p3 (Maya) | mustard | #E0AE2E, ink | #F1E4C6 / #7C4F00 / #A27200 | #2F2408 / #EBC15A / #E3B000 |
| p4 (Theo) | turquoise | #2BA8A4, ink | #CFEAE7 / #006562 / #008E81 | #0E2A29 / #6FD0CB / #00B6B2 |
| p5 | walnut | #66482E, white | #ECE2D9 / #66482E / #5E4832 | #2C231C / #D2B79E / #A4805F |
| p6 | sky | #7CC3F0, ink | #D5E8F5 / #145F88 / #5B7F9A | #152837 / #A3D6F6 / #7CC8F2 |
| p7 | petrol | #1F5F6E, white | #D6E7EB / #1F5F6E / #226170 | #15292E / #93C3CF / #4E95A6 |
| p8 | aubergine | #4E2A6E, white | #E8DFF5 / #4E2A6E / #4C286C | #291F35 / #C9B0E6 / #9A72C6 |

**What each colour does.** The page is putty and ink with hairline seams; there are no coloured sheets. **The bright colours are the people's**, the stripe on the panel is the family's first four of them, and **orange is the one signal**: today, the one primary button, the next plan's Tomorrow stamp, a Yes!, what to set up next, and the edge of "you are here". **Green is Vera's** (and "working"), **red is late**. Colour is never the only cue: late says "days late", setup carries ⚠, people have names and letters. Never cream paper, hot or bubblegum pink, sugary pastels, a navy panel, or green anywhere that isn't Vera.

**Checks** (`python3 _kit/palette-check.py`, from the tokens in this file): every text pair is AA and every edge and stripe 3:1, in both themes (§7). Colour-blind (Machado 2009 simulation, CIEDE2000), closest pair: avatars 10.4, day stripes 7.1, night stripes 7.6. `_kit/stripe-tune.py` chose the stripe shades; `_kit/palette-sheet.py` writes `palette.html` and style.css §10.

### Type

| Token | Size | Use |
|---|---|---|
| `--t-xs` | 13 px | rarely: the smallest capitals inside drawings and dense tables |
| — | 14 px | labels: Barlow Condensed 700 capitals, +0.06em (running heads, group heads, column heads, Leave by) |
| — | 16 px | phone tab labels, Barlow Condensed 700 |
| — | 20 px | the panel's page names, Barlow Condensed 600 (700 when current) |
| `--t-sm` | 14 px | the floor: tags, badges, hints; **the margin's mono**; chat times |
| `--t-meta` | 15 px | meta lines, small body, group heads (Barlow Condensed 700 capitals) |
| `--t-md` | 17 px | body (line 1.5), row titles (700) |
| — | 18 / 20 px | to-do titles / wish titles (Atkinson 700) |
| `--t-lede` | 19 px | the sentence under a page title (17 on the phone) |
| `--t-h3` / `--t-h2` / `--t-h1` | 20 / 26 / 40 px (h2 24, h1 32 on the phone) | Barlow: h1 820 at 72 % width, line 0.95; h2 800 at 78 %; h3 750 at 85 %. **Titles earn their space**: the page says what it is and gets out of the way |
| — | 26 px | Home's greeting `h1` (22 on the phone), Barlow Semi Condensed 700; its date in 14 px Condensed capitals, orange (`--today-ink`) |
| — | 22 px | today as information (`.lede--info`, 19 on the phone), Atkinson, ink |
| — | 72 px | **Leave by** (`.leave__t`; 56 in a narrow column, 48 on the phone), Barlow 820 at 68 %, tabular: the biggest figure on Home |
| — | 36 px | Next up's title and time (28 and 24 on the phone), 820 at 72 % |
| — | 24 px | a drive figure (`.drive-fig`, 20 on the phone), 800 at 72 %; "about" at 62 % |
| — | 52 / 34 / 26 px | margin dates (`.dt--lg` / normal / small) and ranks, Barlow 820 at 70 %, tabular |
| — | 48 px | the month on Plans (30 on the phone) |
| — | 44 / 56 px | money / display money and Status figures (Barlow 820 at 70 %) |
| `--font-mono` | 14 px | Martian Mono 450 at 75 % width: the margin, the contents numbers, chat times, calendar event times, the meter scale; and text on glass |

- **Round 6:** Barlow (The Board's three files: `barlow-semicondensed-700`, `barlow-condensed-600`, `barlow-condensed-700`, 60 KB (the new type now totals 99 KB with Martian Mono), OFL, `fonts/barlow-OFL.txt`) replaces Archivo. Semi Condensed 700 (`--font-head`) sets titles, the greeting, section heads and the wordmark. Condensed (`--font-num`) sets labels (14 px capitals, +0.06em), the panel, tabs, and every big figure. `.fig` uses "Barlow Figures", the Condensed file limited to figures. Archivo left because Barlow does both its jobs, more crisply, and the total stays at two faces plus Atkinson. Any width or weight figures quoted below for Archivo now read: Barlow at 700.
- **Fonts** (`fonts/`, self-hosted, Latin, 128 KB new): **Atkinson Hyperlegible** 400/700 for every word (unchanged, chosen for the kids' reading). **Barlow** (`archivo-var.woff2`, 90 KB, OFL, licence in `fonts/archivo-OFL.txt`; weight 100–900, width 62–125 %) for titles, labels, the wordmark, avatar initials and big figures. **Martian Mono** (`martian-mono-var.woff2`, 38 KB, OFL; weight 100–800, width 75–112.5 %) for the margin and the glass. Bricolage Grotesque and JetBrains Mono are gone. No other faces.
- **Why this pairing.** A logbook speaks in two registers: the printed ruling (heads, labels, the margin) and the handwriting (the entries). Barlow is a grotesque from the newspaper tradition with a real width axis. Condensed and heavy, it makes tall, editorial heads that fit a strong title on a short line, which gives the page its voice and keeps more content above the fold. Wide and in capitals, it makes the labels and running heads, which read as technical. Martian Mono at 75 % is narrow enough for "Sat 17 Oct" in a 116 px margin, and every figure is the same width, so dates and times line up down the edge. Atkinson stays for everything people read.
- **Sizes are in rem** (16 px = 1 rem), so every step grows with the reader's text size.
- **Figures.** Big numbers (`.dt__d`, `.money`, `.figure dd`, `.day__n`, `.rank__n`) are Barlow condensed, tabular. **Every amount and clock time in running text** is `.fig` (the "Barlow Figures" family: the same file limited by `unicode-range` to `$ , . 0–9 : ¢`), at the weight of the line, so a zero is always open. Inside the margin, chat times and event times, `.fig` inherits the mono.
- Headings have `word-spacing: .06em`, because the condensed face's word space is tight.
- `type.html` shows every step and sets real lines live.

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48. Sections in a column are 48 px apart (32 px in the side notes and on the phone).
- Radius: crisp, square-cut like signs. Rails over sections and heads are **3 px ink** (round 6; were 2). `--r-sm` 3 (tags, badges), `--r-md` 4 (buttons, inputs, tick boxes, faces, quick-pick buttons, choice pills), `--r-lg` 6 (Ask, panes, the radar). **Round only for people** (avatars), the health pill and the phone's conversation pills.
- No shadows. Depth comes from rules: 2 px ink over a section, 1 px hairline between rows.
- Avatars: 24, 32 (28 in the chat margin), 40. The tick is a 44 px hit area around a 30 px square box.
- Every target is 44 px or more (`--target`). The top bar is 56 px. The tab bar is 68 px plus `env(safe-area-inset-bottom)`.

### Moments (style.css §9)

Small marks in the book, all CSS, each played once. **Nothing moves under `prefers-reduced-motion`.**

| Moment | Where | What happens |
|---|---|---|
| Today | Home's greeting; the calendar | the date in orange on Home's one-line greeting; on the calendar, the orange-key day number with an orange top rule over a keycap-white cell |
| Next up | Home, the kid's Home, an idea's page | a departure board: the time big in the margin, the route stripe, "Tomorrow" stamped as the orange key, and **Leave by** as the biggest figure |
| Crossing it off | `.todo--done`, `.tick--done` | the box is pressed in ink and pops, then an ink line is ruled through the title, left to right |
| A flash that went well | `.banner--ok.flash` | the banner drops in, and its check is stamped in an ink square |
| "Yes!" | wish answers | an orange-key stamp in Condensed capitals |
| Top wish | a ranked list of two or more | rank 1 is in ink, or in the kid's colour on her pages |
| A kid's pages | `body.kid.me-pN` | her book is ruled in her colour: the running head, every section rule, the contents, her h1 underline, her tab |

---

## 2. Components

Class names are the API. Person colour classes are **slots** (`.p0…p8`), never names: no `.av--sam`, `.msg--maya`, `.ev--theo`. Each component has one anatomy; variants are modifiers.

| Component | Classes | Variants | When to use |
|---|---|---|---|
| Section (`card`) | `.card`, `.card__head`, `.card__foot` | `--setup` (amber panel) | every group of content: a 2 px ink rule over a condensed head; no box |
| Button | `.btn` | `--primary` (ink, one per view), `--quiet` (edge), `--sm`, `[disabled]` | rectangular, radius 4, 1.5 px edge |
| Text button | `.textbtn`, `.linkbtn`, `.more` | — | a form action that reads like a link (Delete, Take it off my list); "All plans ›" |
| Badge | `.badge` | `--late` (red), `--act` (ink outline), `--quiet` (plain grey number), `--look` | counts with a word. Loud only for what needs someone now: **late** and **to decide**. “2 to rate” and “1 to check” are quiet |
| State tag | `.tag` | `--ok` Working/Connected/Added · `--better` Could be better/Not connected · `--look` Needs a look · `--broken` Not working · `--off` Off/Optional/No backup · `--when` Tomorrow/Planned · `--been` Went… · `--surprise` | how a thing stands; one tag per thing, words from §3 |
| Health pill | `.pill-health` | `--busy`, `--rest`, `--down` | Vera's state, in the sidebar and the phone's top bar; parents only. Calm: soft green, Atkinson 700, a still dot. Glass and Martian Mono only when there is something to notice |
| Avatar | `.av` + slot `.p0…p8` | `--sm` `--lg` | every mention of a person; round, because round means a person. Everyone (`.p0`) uses the house icon |
| Vera's screen | `svg.vs` (`aria-hidden`) | `--sm` (24) · default (32) · `--lg` (40) · `--xl` (56); `--busy` (answering), `--off` (can't answer) | Vera, wherever she speaks: Ask card, chat, Status, Home's Vera row. A rounded square with a lit `>▮` prompt. **Never a face or figure** (§9) |
| FamilyDB mark | `.mark-fdb` + `.wm` (wordmark) | `--sm`; `.pane__mark` (64) | the brand: bar, sidebar, sign-in, panes, favicon (§9) |
| Glass pane | `.pane` | `--center`; `.brand-row` | brand moments only: sign-in, a first empty day, the grown-ups page, the missing page (§9) |
| Instrument (radar) | `section.mapband` › `details.mapband__fold` › `.instrument__pane` › `svg.radar` | `--wide` (desktop), `--narrow` (phone) | Ideas only, in its own band after all the cards. Desktop: always open (the summary is hidden and `::details-content` is shown). Phone: folded behind "Show the map". Each dot carries the idea's short name; no separate list (§9) |
| Add a to-do | `form.adder--todo` › `.adder__row` + `details.adder__more` | — | One row first: box and Add. Who, when and the reminder sit in `.adder__more`: folded beneath the row on the phone (summary "Who, when, reminder · Nobody picked yet · No date"), always open on the desktop, where Add is a full-width bar at the bottom. The form is `novalidate`: the server checks who and sends it back with the fold open and the error in it |
| Calendar who-marker | `.dots i` via `mini(person)`; `.cal-key` | person initial · house (Everyone) · hollow ring (past) | the phone month's day cells (up to three) and the one-line key under the calendar on Plans. On desktop every event shows its people as small avatars |
| Tile | `.tile` | `--lg`, `--ok` `--better` `--look` `--broken` `--vera` | leading icon for an idea kind (neutral) or a health area (tone) |
| Margin date | `.dt` (`.dt__wd`, `.dt__d`, `.dt__m`) | `--now` (the next plan: weekday in ink under a 3 px ink rule), `--today` (the orange stamp: Home's greeting only, `aria-hidden`), `--lg` `--sm` | a big date in the margin: weekday label, the day in Barlow condensed, the month label. No box |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--log` (margin · route stripe · body · drive figure), `--divided`, `--health` | every list of things that isn't a to-do or an idea; rows are divided by hairlines |
| To-do row | `.todos` › `.todo` | `--m` (with a `.log__m` margin: due date and weekday), `--compact` (Home), `--late` (a 3 px red rule outside the margin edge), `--done`, `--ro` (kids: who set it in the tick column) | to-dos |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | a 30 px square box in a 44 px hit area; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default **info (neutral card, grey icon)**, `--ok` (mint: all good, done), `--warn` (set this up), `--alert` (broken, errors); size: `--hero`, `--slim` | a message with at most one action. Resting, Off and “for your information” use the neutral default, never mint or yellow. **One “set this up” message per page** |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (charcoal glass, phosphor Send); `.ask--hero` (Home and the kid's Home: full width, 44 px screen, her line in the mono after a lit `>`, Atkinson on a kid's page, her head and line on one row, an 80 px box and an 80 px Send, then the foot line; no starters); in a chat room the composer is on the same glass (`.room .composer`); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page. **Every box for writing to Vera is on her glass, with her phosphor Send** |
| Quick pick | `.starter` (plain button) | — | a few one-tap values inside a form, such as the due-date picks on Edit a to-do. **Not used for Vera**: Ask Vera has no suggested messages (round 6) |
| Chat room | `.chat`, `.convos`/`.convo`, `.room`, `.scroller` › `.thread` | `.msg--person` (+ slot), `--mine` (her soft wash), `--vera` (green rule), `--pending` (dashed rule), `--failed` (dashed red rule), `--system`; `.receipt`; `.earlier`; `.day-sep` (a label and a hairline) | a transcript: who and when in the margin, the words beside the person's rule |
| Privacy line | `.privacy` (`--room` on phone) | — | "Sam and Alex can read …"; **at every width** |
| Field | `.field`, `__label`, `__hint`, `__error`; `.req`/`.opt` | `--error` | every input; label above, error above the box, hint below |
| Form | `.form`, `.fieldset`, `.form__row`, `.actions` | — | multi-field forms |
| Choice pills | `.choices` › `.choice` (radio or checkbox) | `--person` | picking from a few; **no default where a choice must be made** |
| Disclosure | `.disclose` (`<details>`) | — | filters and form options folded away (always on the phone) |
| Tabs (`seg`) | `.seg` | — | view switches (Open / Done / All, Month / List): a 1.5 px edged strip, Barlow Condensed 18 px; the current one is an **inverted ink plate**; counts in the mono; wraps |
| Search | `.searchbox` | — | search inputs |
| Faces | `.faces` › `.face` | — | "How did it go?"; three labelled faces; parents only |
| Idea index | `ol.ideas[reversed]` › `.idea`; `.ideas-head` | `--unknown` | a numbered table on the desktop (No. · Kind · Idea · For · Drive from home · Status), compact numbered rows on the phone |
| Ranked list | `.ranks` › `.rank`, `.rank__n`, `.rank__move`, `.quote`, `.decide` | `--decide`; `.ranks--mini` (Home) | wishes: the rank big in the margin; the parent's answer as a margin note (`.quote`, a 2 px rule) |
| Calendar | `.cal`, `.week`, `.day`, `.ev`, `.ev-more`, `.daylink`, `.dots` | slot class on `.ev` (a text line: mono time, Atkinson title, a 4 px rule in the person's mark colour on their soft wash; `.p0` neutral), `--past` (no wash, grey rule); `.day--today` (green stamp, rule, wash), `--we` (wider, washed), `--out` | the month view |
| Settings row | `.slist` › `.srow` | `--look` | lists of sections or destinations (Settings, the account menu) |
| Note | `.note` | — | one quiet line for a connection that isn't set up, on a page that isn't about it (Plans: Google Calendar; Ideas: looking things up) |
| Kind label | `.kind` | — | a kind of idea: icon + word, never a pill |
| Weekend suggestions | `.suggest` inside a Vera message | — | Vera's longest message: a short list of ideas with when, drive, price, who, and a “Plan it” form each |
| Read-only to-do | `.todo--ro` | — | a kid's own to-do: the setter's avatar as lead (never a box or ring), a dashed “Not done yet”, and “Tell Vera I did it” (a link that fills her chat box) |
| Key/value | `.kv` | — | facts about one thing |
| Empty state | `.empty` | `--center` | any list or card with nothing in it: what will appear, and how to start it |
| Locked | `.locked` | — | "Ask a parent" where something isn't a kid's to change |
| Back link | `.crumb` | — | first thing on a detail page |
| Person picker | `.people` › `.person-tile` | `[aria-current]` | sign-in |
| Running head | `.runhead` (`aria-hidden`) | — | the first line of every page: book and page left, date right |
| Margin cell | `.log__m` (+ `b` for the date) | — | a date and a time, or a date and a weekday, in the mono |
| Route stripe | `span.route` › `i.pN` (`aria-hidden`) | `--key` (in the calendar key) | a plan's people as one 6 px bar split into their `-mark` colours (Everyone `.p0` grey). On Home, Coming up and every calendar event; the names are always in the text too |
| Drive figure | `.drive-fig` › `b` (+ `small` for "about"), `.drive-fig__l` or `.dir.dir-{n,nne,ne,e,se,s,sw,w,nw}` | `--none` ("Not looked up yet") | a drive time in its own right-hand column: plans (with "drive") and ideas (with the direction and a turned arrow) |
| Departure board | `.board` › `.next` (`.next__when`, `.next__time`, `.route`, `.next__body`, `.leave`, `.leave__l`, `.leave__t`) | `--narrow` (Leave by under the plan) | the next plan on Home, the kid's Home and an idea's page |
| Today's line | `.lede--info` | — | Home: the sentence that says what matters today, set bigger than the greeting |
| Greeting | `.greet` (+ `.greet__date`) | — | Home: one line, the date in orange capitals and a 26 px `h1` |
| Specimen | `.specimen`, `.sheet-sec` | `--wide` | the states sheets only |

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
| Phone tabs | Home, Chat, Ideas, Plans, To do; Wishes, What Vera knows, Status, Settings, Family and Sign out are in the **account menu** behind the avatar (`more.html`) | same, without Status/Settings/Family | Home, Chat, Wishes, Plans, To do; Ideas, What Vera knows and Sign out in her menu (`more-kid.html`) |
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

1. **The phone is its own layout, not the desktop stacked.** The sidebar becomes a 56 px top bar (brand, health pill for parents, and the avatar that opens the account menu, with a dot when something inside needs checking) and a **fixed bottom tab bar** of five, role-aware, with `--tabbar-total` = 68 px + `env(safe-area-inset-bottom)` for its height and the body's bottom padding, and `scroll-padding-bottom` so the focused control is never under it. The top bar and tab bar are paper with a 2 px ink rule. The current tab has a 4 px ink bar on its top edge and a grey tint (the kid's colour on her pages).
2. **The first screen is greeting, Ask Vera and the next plan.** On Home: the one-line greeting, today's line, Ask Vera (head with a 32 px screen, a 72 px box, icon Send, and "Goes to the family chat as Sam"), then the board, with **Leave by** right under its date line. The setup banner comes after the board. Cards are capped with "3 more plans" and "All 4 to-dos". The card order is Ask, Next up, setup, To do, How did it go, Wishes, Ideas (kids: Ask, My wishes, My to-dos, Next up, Ideas). Quick-adds are one line; options, filters and sorting fold into `<details>`.
3. The Ideas index becomes compact rows: number, title, "kind · who · drive", tags underneath. The radar folds behind "Show the map" after the rows.
3a. **To do starts with one row to add a to-do** (box and Add) at the top of the list; who, when and the reminder fold beneath it. Nobody is picked by default.
4. **Plans: the month header, then the Month/List switch, then the month at a glance, then Coming up.** The month grid becomes a month at a glance: day cells are whole-cell links with person markers and a full spoken label. Weekday headers are single letters. A spill-over day shows its month in small capitals beneath the number ("28" over "SEP"), so it never wraps.
5. Settings and More rows use grid areas: icon | text, tag | chevron. The chevron never wraps.
6. The Status model table folds away and stacks; actions sit under their line.
6a. **The margin goes on a line of its own.** On the phone a to-do is tick | (due · late on one line, then the title) | Edit, and a plan is route | (date · time, then the title) | drive figure. Titles keep the full width. The chat puts the name and time on one line over the words, with the face beside them.
7. **Chat is an app-height room** (on screens shorter than 560 px it falls back to normal page scroll): pills, the privacy line, a scroller that opens at the newest message (column-reverse), the box pinned above the tab bar, and a pinned "Earlier messages" bar with a fade at the top edge.
8. Choice pills and quick picks **wrap**; they never scroll sideways. Only the conversation pills scroll, as one row.
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
| Vera can't answer | pill, chat, Status | pill `--down`; the box closes with an alert banner; Vera's system message keeps the message and offers **Try again**; Status hero alert names the company and the fix (add a backup key); the Vera health row says **Not working**. Kids: "Try again a bit later", no company names |
| Reply pending | chat | the user's message, then a dashed Vera message "Vera is thinking" (dots; no animation under reduced motion); the box is closed: "The box opens again when she's done." |
| Message failed | chat | the user's message with a dashed red rule and "Didn't reach Vera · Try again" (a resend form). The box stays open |
| After an action | the list it changed | flash with Undo, focus moved there; a ticked row stays in place, struck through, for this page view |
| Form errors | any form | error summary first (focus there), links to fields; per-field message above the box tied with `aria-describedby`, `aria-invalid="true"`, thicker red edge; typed values kept; `<details>` holding an error opens |
| First empty day | Home and every list | each empty card says what will appear and how to start it, in words (usually "Tell Vera…"); Ask Vera sits on the same page, so there are no suggested-message buttons; setup leads |
| No results | Ideas, To do | "Nothing matches "pizza" for Theo", every active filter in words, **Clear search and filters**, and "Save "pizza" as an idea" |
| Busy day, long plans | calendar | two events, then "+N more" (links to that day in the list); the phone shows up to three markers (initials, the house, a hollow ring). A plan over several days is one bar (`.len2…7`); across a week boundary it is split (`.ev--to` › / `.ev--from` ‹, “continues” in the spoken label) |
| Long titles | everywhere | wrap in full; only calendar events clamp to two lines (full title in the spoken label and on the plan page) |

---

## 7. Accessibility checks

Contrast is computed from the tokens (WCAG 2.2). AA needs 4.5:1 for text and 3:1 for control edges.

| Pair | Use | Light | Dark |
|---|---|---:|---:|
| `--ink` on `--paper` | body text, heads, rules | 13.4 | 15.2 |
| `--ink-2` on `--paper` | secondary text, margin times | 9.0 | 10.5 |
| `--ink-3` on `--paper` | quiet text, labels, entry numbers | 6.1 | 6.8 |
| `--ink-3` on `--paper-2` | quiet text on a well or the weekend wash | 5.2 | 6.0 |
| `--ink-3` on `--card` | placeholders | 7.3 | 6.4 |
| `--ink-3` on `--warn-soft` | quiet text in the setup panel | 6.1 | 6.0 |
| `--edge` on `--paper` | control edges, tick boxes (3:1) | 4.3 | 4.9 |
| `--edge` on `--card` | field edges (3:1) | 5.2 | 4.6 |
| `--on-primary` on `--primary` | the primary button, the orange key | 6.3 | 6.9 |
| `--primary-edge` on `--paper` | the primary button's edge (3:1) | 13.4 | 6.9 |
| `--on-signal` on `--signal` | Tomorrow stamp, Yes! | 6.3 | 6.9 |
| `--today-ink` on `--paper` | the greeting's date | 5.6 | 8.7 |
| `--on-today` on `--today-bg` | today's day number | 6.3 | 6.9 |
| `--today-rule` on `--today-wash` | today's rule against its cell (3:1) | 4.7 | 6.1 |
| `--on-done` on `--done` | done tick, flash check | 16.0 | 15.2 |
| `--vera` on `--paper` | Vera's name and rule | 5.1 | 14.2 |
| `--vera` on `--vera-soft` | the ready pill | 5.2 | 12.8 |
| `--on-vera` on `--vera-bg` | Vera tile | 4.7 | 10.7 |
| `--ok` on `--ok-soft` | tag Working | 4.8 | 10.3 |
| `--warn` on `--warn-soft` | tag Needs a look, setup panel | 5.7 | 7.7 |
| `--warn` on `--paper` | step numbers | 5.6 | 8.7 |
| `--alert` on `--alert-soft` | tag Not working, late badge | 5.0 | 7.1 |
| `--alert` on `--paper` | late text, "OVERDUE" head, errors | 5.2 | 8.0 |
| `--pN-ink` on `--pN-soft` (lowest of eight) | names on soft, a kid's current tab | 5.4 | 7.9 |
| `--pN-ink` on `--paper` (lowest of eight) | names in the chat margin | 5.2 | 9.4 |
| `--ink` on `--pN-soft` (lowest of eight) | words on a one-person event, "mine" | 13.6 | 12.6 |
| `--ink-2` on `--pN-soft` (lowest of eight) | an event's time | 9.1 | 8.7 |
| `--pN-mark` on `--paper` (lowest of eight) | route stripes, a person's rule (3:1) | 3.1 | 3.5 |
| `--pN-mark` on `--card` (lowest of eight) | stripes on a keycap cell (3:1) | 3.7 | 3.3 |
| `--on-pN` on `--pN` (lowest of eight) | avatar letters | 5.2 | 5.2 |
| `--everyone-mark` on `--paper` | Everyone's stripe (3:1) | 4.3 | 6.8 |
| `--everyone-ink` on `--everyone` | the house avatar | 6.7 | 5.3 |
| `--on-band` on `--band` | panel text | 14.8 | 13.3 |
| `--on-band-2` on `--band` | panel quiet text, inactive page names | 8.9 | 8.3 |
| `--on-band-2` on `--band-hi` | the account plate | 7.5 | 7.1 |
| `--band` on `--on-band` | you are here plate | 14.8 | 13.3 |
| `--on-alert-plate` on `--alert-plate` | the late count on the panel | 4.8 | 4.8 |
| `--alert-plate` on `--band` | the late plate against the panel (3:1) | 3.5 | 3.1 |
| `--phosphor` on `--band` | wordmark cursor on the panel | 13.2 | 11.7 |
| `--ask-ink-2` on `--ask-bg` | Vera's line in the mono on the hero | 11.6 | 11.7 |
| `--on-send` on `--send` | Send | 14.7 | 14.8 |
| `--phosphor` on `--glass` | phosphor on glass | 14.7 | 15.6 |
| `--glass-ink` on `--glass` | pane text | 16.3 | 17.3 |
| `--glass-alert` on `--glass` | can't answer pill | 8.2 | 8.7 |

The glass pane has no contrast duty of its own in the dark (it is #070A09 on #0C100F): its 1 px `--glass-line` rim and the phosphor inside carry it. **Focus on glass is phosphor** (`.pane`, `.instrument__pane`, `.pill-health` set `--focus: var(--phosphor)`, 14.7:1), because the ink ring is 1.2:1 there.

Disabled controls are exempt, but each also carries its reason in words.

**Checklist for every page**
- One `h1`; headings in order. (Home's today tile is `aria-hidden`; the eyebrow line beside it carries the date.) Chat on the phone keeps its `h1` visually hidden, not `display:none`.
- A visible "Skip to content" link on first Tab. A 3 px focus ring on everything (phosphor on the Ask card). Whole-card links show focus with `:focus-within`.
- No meaning by colour alone: late says "6 days late", tags carry words, calendar events carry a spoken label, badges carry words.
- Every control is named: ticks "Mark done: …", faces "Loved it (Silver Falls hike)", move buttons "Move Ice skates up", Edit "Edit Call the dentist about Theo".
- Form fields have labels; errors are tied with `aria-describedby` and `aria-invalid`; the summary has `role="alert"`; flashes have `role="status"`.
- Chat thread: `role="log"`, focusable (`tabindex="0"`), named.
- Targets are 44 px; type is 14 px or more (13 px only on tab labels and overlines), set in rem; the top and tab bars use `min-height`.
- **Nothing blinks for more than five seconds** (2.2.2): the wordmark cursor blinks twice and stays lit, the pill's dot breathes once. Only things that end on their own move longer: Vera's busy screen and the typing dots, while a reply is on its way.
- `prefers-reduced-motion`: nothing moves at all.
- **Never `display:none` beside an `aria-hidden` stand-in.** When a short label replaces a long one on the phone (Edit links, Send), the long one is hidden with the `.sr` clip pattern, so it stays the control's name.
- Icon-only buttons have `--edge` borders (4.3:1); a disabled one is `--ink-3` with a dashed edge and keeps its reason in words.
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
- Then `card`, `banner(tone, size)`, `tag(state)`, `badge(kind, n, word)`, `avatar(person, size)` (emits `av p{{ person.slot }}`), `vera_screen(size, state)` (emits an `aria-hidden` `svg.vs` from the geometry table in §9), `brand_mark(size)` and `wordmark()`, `item`, `todo(todo, viewer)` (picks `--late`, `--done` or `--ro` from the viewer's role), `composer(viewer, state)`, `field(...)`, `choices(name, options, required)`, `rank(wish, viewer)`, `idea_card`, `calendar_week`, `empty(title, text, action)`, `flash(message, undo_url)`, `error_summary(errors)`.
- `health(area)` returns one `(state, words, action)` per area: Vera, Spending, Sign-in, Backup, Telegram, Google Calendar, Looking things up. **Every page reads it** (pill, Home, Status, Settings, Ideas banner), so they can't disagree. Settings summary lines are computed, never written as copy.
- `visible_to(viewer)` filters every list for kids: own to-dos only, gifts and surprises removed. Counts are taken *after* filtering.

**Works with scripting off (required)**
- Reading every page, and every form: tick, Undo, add, edit, rate (faces), answer a wish, move a wish up or down, sign in, search and filter (GET), send a message.
- Pattern: POST → redirect → GET (PRG), with a flash in the session and `#anchor` to the changed list. Every form carries a CSRF token.
- Chat opens at the newest message without script (`.scroller` is `flex-direction: column-reverse` around one `.thread`). The server sends the latest 30 messages; "Earlier messages" is `?before=<id>`; the last message has `id="latest"`.
- **While a reply is pending**, the page includes `<meta http-equiv="refresh" content="3">` (CSP doesn't block it), the box is `disabled`, and the pending message carries a visible **“Check for her answer”** link to `#latest`. Remove the meta tag as soon as Vera has answered. After 60 s with no reply, mark the message failed.
  - **Accessibility concern, recorded for the engineer (WCAG 2.2.1, 3.2.5):** a repeating reload moves a screen-reader user back to the top and a magnifier user loses their place. The family's app works this way, so it stays, but keep it as short as possible: back off server-side (3 s, then 5, then 10 s, from the pending message's age), never refresh after 60 s, and keep `chat.js` polling as the normal path so the meta tag is removed on load whenever scripting is on.
- `<details>` for filters and options: no script. Open it server-side when it holds an error or an active filter.
- The month grid's day links, the To do filters and the Plans Month/List switch are plain links.

**Needs a small script (from `/static/*.js`, all optional)**
- `chat.js`: while a reply is pending, poll `/chat/pending` quietly and swap the message instead of reloading. It removes the meta refresh on load.
- `draft.js`: keeps an unsent message in `sessionStorage`, and nothing else.
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

House Log is the family's logbook: paper and ink, ruled heads, a margin of dates and times, people in their own colour. FamilyDB is the small screen that keeps it, and Vera keeps the ruling. The brand is that pairing, used a little: **a pane of dark glass with green light, on a ruled page.** The mark is unchanged (not recoloured): its charcoal and phosphor are the one dark, lit thing among the family's bright pens. It is a sprinkle. The layout, the components and every check in §7 are unchanged by it.

### The brand rule

**The paper, the ink and the bright pens are the family's. Phosphor on charcoal glass is FamilyDB's and Vera's.** Glass and phosphor appear only where one of three things is:

1. **the brand**: the mark, the wordmark, and the brand moments (sign-in, a family's first empty day, the grown-ups page a kid lands on, the missing page);
2. **Vera**: her screen, the Ask card (charcoal glass by day, green-rimmed glass at night, with a phosphor Send);
3. **something live**: the status pill when it has something to say (writing back, resting, can't answer), a reply on its way, the cursor in her box, today's date. When Vera is simply ready the pill is calm and on paper.

Never on the family's own things: names, ideas, to-dos, wishes, plans, and the buttons and links that act on them (those use `--link`, ink with an orange underline, and `--primary`, the orange key; never phosphor). **Mono only on the glass**: nothing printed on paper is in the mono. Every touch says something true; nothing is only ornament. No dark page in light mode, no CRT curvature, no vignettes, no heavy scanlines, no pixel font.

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
- **On the page:** the charcoal square is the mark's own glass, so it sits directly on the brown-black of the panel or top bar; no extra frame or shadow.
- **On dark:** the same file. At night the square is close to the page, so it keeps its own edge from the stroke; nothing is inverted. Never recolour the stroke (no white, no `--vera` green), and never use it without its square.
- Head tags: `favicon.svg` (`image/svg+xml`), `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png` (180). The 512 is for the web manifest.

### The wordmark

"FamilyDB" in **Barlow 820 at full width**, letter-spacing −0.03em, followed by a **lit cursor**: a block `.42em × .82em`, 0.12em after the B, radius 1 px.

- Sizes: 22 px in the sidebar, 20 px in the phone bar, 18 px inside a pane. The mark is 32 px in the sidebar and 28 px in the phone bar. It is always beside the mark; the link around both is named "FamilyDB, home".
- **On the page:** ink letters, cursor `--cursor` (#12945A, 3.6:1 on the page as a non-text mark) with a faint glow.
- **On dark and on glass:** near-white or glass-ink letters, cursor `--phosphor` with `--phosphor-glow`.
- The cursor blinks twice (2 s each, mostly on), then stays lit: no blinking past five seconds (WCAG 2.2.2). Under `prefers-reduced-motion` it never blinks. The cursor is `aria-hidden`.

### Vera's screen

Vera is never drawn. Where she speaks there is a small pane of glass, as if she were typing: a **rounded square** (never round: round means a person), a **lit rim**, a few short **lines of light**, and her **signature, a lit prompt `>▮`** in the bottom-left corner. The prompt is the same at every size; small sizes have fewer lines, not smaller ones. It is drawn as inline SVG, crisp, with no blur and no scanlines, so it reads at 24 px on a phone. It works whatever the family calls her.

| Size | Class | Lines | Where |
|---|---|---|---|
| 24 px | `.vs--sm` | 1 | Settings colour key, "Suggested by Vera" rows |
| 32 px | `.vs` | 2 | chat messages (her avatar slot), the pending and failed messages; a receipt sits inside her message |
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

### The mono: the margin and the glass

Martian Mono at 75 % width, self-hosted (`fonts/martian-mono-var.woff2`, 38 KB), 14 px. Felt Tip kept the mono for the glass only; House Log gives it a second job, **the margin**, because the margin is the book's ruling and Vera keeps the book. On paper it sets **only figures-and-dates**: margin dates and times, entry numbers, the contents numbers, chat times, event times, the meter scale and tab counts. It **never** sets a sentence, a name, a title or anything a kid has to read as words; those are Atkinson. On glass it sets the status pill when it has something to say and the lines inside a pane. The radar's labels stay Atkinson.

### Phosphor elements, their tokens, where they may and may not appear

| Element | Tokens | May appear | May not |
|---|---|---|---|
| The mark | `--glass` (fixed #0E1312 in the file), `--phosphor` | bar, sidebar, sign-in, panes, favicon, icons, Settings' key | as Vera; inside a message; on the family's items |
| Wordmark cursor | `--cursor`, `--cursor-glow` (dark: `--phosphor`) | after "FamilyDB" only; the caret in Vera's box (`caret-color`) | anywhere else as decoration |
| Vera's screen | `--glass`, `--glass-line`, `--phosphor`, `--vs-halo` | wherever Vera is: Ask, chat, Status and Home rows, pending, Settings' key, the kid's empty chat | for a person; as a decoration with no Vera |
| Status pill (when there's something to notice) | `--glass`, `--glass-line`, `--phosphor`, `--phosphor-glow`, `--glass-alert` | sidebar and phone bar, parents only. Writing back: phosphor mono, the dot breathes until the reply lands. Resting: `--glass-ink-2`, hollow dot. Can't answer: `--glass-alert` #FF8B74 (8.2:1 on glass), square dot. When Vera is ready the pill is not glass at all: `--vera-soft`, `--vera`, Atkinson 700, a still dot | kids' pages; anywhere it isn't Vera's real state; "ready" |
| Glass pane | `--glass`, `--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--phosphor` | the four brand moments: sign-in, a first empty day, the grown-ups page, the missing page. Faint scanlines inside are fine | as a card style; around the family's content; more than one per page |
| The radar | `--glass`, `--phosphor` at 14–25 % for rings and axes, `--glass-ink` and `--glass-ink-2` for labels | Ideas only, in its own band after all the cards (folded behind "Show the map" on the phone). Drive time is distance from home on a piecewise scale that gives the first half hour 70 % of the radius (rings at 15 min, 30 min, 1 h, 2 h, 3 h, labelled on alternate sides of the north axis); direction is bearing, north up; "Home" marks the middle. Each dot carries the idea's short name ("Pumpkin patch", "Oaks Park"): the first words of its card's title, so a kid can match it. Ideas in the same direction are fanned a few degrees apart. The SVG is `aria-hidden`: the cards are the list, and each card already says its drive time and direction | between the cards; any second page; a separate numbered list; mono labels. One instrument per page at most. If every idea is inside one ring, show the cards alone |
| Ask card glass | `--ask-bg`, `--ask-rim`, `--ask-edge`, `--send` | Home's and the kid's Ask card: charcoal glass with a phosphor Send, and at night a 1.5 px green rim, a faint inner glow and a real edge on its box | anywhere else |
| Live glow | `--phosphor-glow`, `--vs-halo` | the writing-back pill, the panes, Vera's screen, the wordmark cursor | the calm "ready" pill, chat messages (Vera's included), cards, buttons |

The radar is drawn twice from the same data, so names stay readable: a wide 860 × 440 plot for the desktop (names 15 px, drawn at 1:1) and a narrow 360 × 400 plot for the phone (names 14 px). Ring and compass labels are 13 px Atkinson; every label position is set per idea in the data, so nothing sits on a compass letter.

### Brand moments

- **Sign-in:** a pane with the mark, the wordmark and "awake, Saturday 3 October", then "Who's using FamilyDB?" and the people on paper.
- **A first empty day** (`states-content.html`): "FamilyDB is set up and awake. Welcome, Sam. This is your family's table." on glass, then the empty cards on paper.
- **The grown-ups page** (`grownups.html`): the mark alone at 64 px, glowing, above the explanation; the explanation stays on paper. The mark is its own glass, so no pane around it.
- **The missing page** (`404.html`): a centred pane, the mark, "404 · nothing at this address" in the mono, then "This page isn't here", Go to Home and Ask Vera to find it.

### The dark theme: the book under a lamp

At night the machine is in a room with the lamp off. The page is warm brown-black (`--paper` #171513), the ink putty-white (#EEEAE3), and the ruled heads invert with it. The panel is a shade lighter brown (#2E251E), so it still stands beside the page, and its family stripe keeps its colours. The orange key stays the same orange (#F57F22, ink letters 6.9:1), and as words it lifts to #FF9B4D. Coral (#FF8B74) means late or broken. Vera's things are phosphor (`--vera` #6DFF9C), and only hers. People keep their avatar colours; their rules use the lighter night `-mark` and their names the lighter `-ink`, on dark tinted `-soft`. The Ask block stays the one lit pane: green-rimmed glass with a real edge on its box. A ticked box is pressed in putty-white. Every pair is in §7.
