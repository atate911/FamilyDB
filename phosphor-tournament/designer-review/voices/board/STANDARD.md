# FamilyDB · The Board · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth. This document says how to use them.

**The rule behind everything:** the family's day is set like a departure board. Every list of things with a time reads left to right: **when · whose line · what · the one figure you act on**. A person's colour marks that person wherever they appear. Green means *today or Vera*, ink means *something you press or picked* (and "you are here", as an inverted plate), and red means *late or broken*. Every status is said in words.

*The Board* (see `DIRECTION.md`) follows Felt Tip. The pages keep their jobs, words and states. Layout, type, colour, surfaces and the moments changed. Home, Plans, To do, Ideas, the kid's Home and Wishes were re-composed around new components (§2: Board, departure row, route stripe, board to-dos, destinations board, line diagram). Kids' pages still carry `kid me-pN` on `<body>`.

---

## 1. Tokens

All values live on `:root` in `style.css` §2. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root` (the one exception is the pane's pure-white hover, kept from before). Two places re-set tokens locally so every component inside them reads right: `.side` and `.topbar` (the fascia), and `.board__head` and `.room__head` (the band). There, `--ink` becomes `--on-band` and `--focus` becomes phosphor.

### Colour

| Token | Light | Dark (the board after dark) | Use |
|---|---|---|---|
| `--paper` | #F3F1EC | #0B1019 | the page: warm enamel. No pattern |
| `--paper-2` | #E6E3DA | #1B2434 | tracks, neutral tiles, "Off" tags, the segmented control's well, a several-people calendar block |
| `--card` / `--field` | #FFFFFF / #FFFFFF | #131B28 / #1A2333 | panels, board rows / inputs, tick boxes |
| `--ink` | #111A2B | #F2F4F8 | signal navy: text, every panel's top rail, the page rule, date-plate bands, the primary button, picked controls, the current tab |
| `--ink-2` / `--ink-3` | #3B4457 / #585F70 | #C9CFDA / #9BA4B5 | secondary / quiet text (AA on card, paper and paper-2) |
| `--line` / `--line-2` | #E4E1D9 / #CFCBC1 | #222C3D / #334056 | hairlines between rows (decorative) |
| `--edge` | #7A808F | #7F8AA0 | **control edges** (3:1): inputs, ticks, choice pills, quiet and icon buttons |
| `--band` / `--on-band` / `--on-band-2` | #111A2B / #FFF / #B9C2D3 | #1F2B40 / #F2F4F8 / #B9C2D3 | **the band**: the sidebar and phone-bar fascia, a board's head strip, the chat room's head, the calendar's weekday row |
| `--band-line` / `--band-hi` | #2A3550 / #222D44 | #2E3B55 / #2A3852 | rules and hover inside the band |
| `--alert-on-band` | #FF8B74 | #FF8B74 | the red block on an Overdue band (decorative; the word carries it) |
| `--vera`, `--vera-bg`, `--vera-soft`, `--vera-line` | as Felt Tip | as Felt Tip | Vera's green; the calm pill; done ticks; the "Yes!" plate; the lede's route underline (`--vera-bg`) |
| `--today-bg` / `--on-today` / `--today-wash` | #0B8457 / #FFF / #EAF6EF | #6DFF9C / #0B1019 / #10231D | **today**: the green Today plate on Home, the calendar day's filled number, its 5 px top bar and wash |
| `--ask-bg` / `--ask-ink` / `--ask-ink-2` | #111A2B / #FFF / #C3CBD9 | #0E1A17 / #EAEEF3 / #C3D2CA | Ask Vera: the information point, a navy panel with a phosphor top rail and Send (green-rimmed glass at night) |
| `--link` | #0B6E4F | #8BD3B4 | links |
| `--primary` / `--on-primary` | #111A2B / #FFF | #F2F4F8 / #0B1019 | the one primary button: ink, inverted at night |
| `--ok`, `--warn`, `--alert` (+ `-soft`, `-line`) | as Felt Tip | as Felt Tip | Working / set this up / late and broken |
| `--on-alert` | #FFF | #0B1019 | letters on the solid red **late plate** (`.badge--late`) |
| `--p1…--p8` (+ `-soft`, `-ink`, `-mark`) | the eight Felt Tip colours, unchanged | unchanged | **each person's line colour**: bullets (avatars), route-stripe segments, a one-person calendar block, message edges, a kid's page rule. Always under dark letters `--on-p` (#111A2B; #17142B at night) |
| `--everyone…` (`.p0`) | #D9D6CE, soft #EEECE6, ink #3B4457, mark #7A808F | #4A5468, #1E2738, #D6DBE4, #9BA4B5 | Everyone: neutral stone; its route segment is `--everyone-mark` |
| `--me…` | from the kid's slot | same | her page rule, her current tab plate, her card pictograms, her rank-1 plate, her wish line |
| Brand `--glass…`, `--phosphor…`, `--cursor` | unchanged | unchanged | §9. The wordmark's cursor is phosphor on the fascia and `--cursor` green on paper |

**What each colour does.** Enamel and white panels are the surface; navy is the structure (fascia, bands, rails, rules, plates). The structure is what makes a page recognisable as FamilyDB with the logo covered. **The bright colours are the people's lines and nothing else**: no kind of idea, state or decoration gets one, except the short bar of the family's colours under a "done" flash. Green is today and Vera. Amber says "set this up". Red says late or broken, and the late badge is the only solid red block anywhere. Never cream paper and soft serif (Kitchen Table), never a cool grey page with hairlines and one accent (Calendar), never the lilac wall (Felt Tip).

**Why navy, and why warm enamel.** Wayfinding signs are dark letters on light panels with dark bands. The navy carries the hierarchy, so the people's colours can stay bright and still read as people. The page is warm rather than cool grey so the family's colours, not the chrome, set the mood.

Maya's slot (p3) is raspberry, not red. Colour is never the only cue: every person marker carries an initial or the house, and every route stripe sits beside the names.

### Type

| Token / step | Size | Face | Use |
|---|---|---|---|
| `--t-h1` | 56 px (42 phone) | Barlow Semi Condensed 700, −0.015em, line 1 | the page title, over the 4 px ink rule |
| — | 36 px (28 phone) | Semi Condensed 700 | the next departure's name (Home) |
| `--t-h2` / `--t-h3` | 24 / 21 px | Semi Condensed 700 | card and section titles / small titles |
| — | 26 px (23 phone) | **Barlow Condensed 700** | a board's name on its band |
| — | 68 px (52 phone), "pm" 24 | Condensed 700, tabular | **the leave-by figure** |
| — | 32 px (40 big row, 26 phone), am/pm 18 | Condensed 700 / 600 | the board's when column |
| — | 20 px, label 14 px caps | Condensed 600 | the board's right-hand figure (drive, due, how late at 18 px 700) |
| — | 34 / 48 / 28 px | Condensed 700, tabular | date plates: normal / large / small; calendar days 24 px |
| — | 44 px | Condensed 700, tabular | money and Status figures; wish ranks 34 px |
| — | 20 px (sidebar), 16 (tab labels), 19 (segments), 17 (badges) | Condensed 600–700 | navigation and counts |
| `--t-sm` caps | 14 px, +0.1em | Condensed 700 capitals | **the only capitals**: board column heads, plate weekdays, the eyebrow (18 px), group heads, day breaks in chat |
| `--t-lede` | 19 px (16 phone) | Atkinson 400 | the sentence under a page title |
| — | 18 px | Atkinson 700 | row titles: to-dos, plans, ideas, wishes |
| `--t-md` | 17 px, line 1.5 | Atkinson 400 | body |
| `--t-meta` / `--t-sm` | 15 / 14 px | Atkinson | meta lines / tags, hints (the floor) |
| `--font-mono` | 14 px | JetBrains Mono 400 | text on dark glass only (§9) |

- **Fonts** (`fonts/`, self-hosted, Latin, OFL; licence in `fonts/barlow-OFL.txt`): `barlow-condensed-600.woff2`, `barlow-condensed-700.woff2`, `barlow-semicondensed-700.woff2` (60 KB together, subset with `tnum`, `lnum`, `pnum`, `case`, `kern`). **Atkinson Hyperlegible** 400/700 is unchanged, for the kids' reading. JetBrains Mono 400 is on glass only. Bricolage is removed.
- **Why Barlow.** It is a grotesk drawn from California's highway signs, licence plates and rail signage: slightly rounded, low contrast, firm. It reads like a sign, not like an app default. One family in two widths gives the board a single voice. Condensed fits times and dates into tight columns at sizes you can read across a room. Semi Condensed gives headings weight without shouting. Its figures are tabular and lining, with an open zero.
- **Mixed case everywhere**, as on British and Californian road signs, because whole word shapes are read faster than capitals. Capitals are kept for 14 px column heads and plate weekdays, which nobody has to read to use the page.
- **Figures.** `--font-num` is Barlow Condensed (`tabular-nums lining-nums`) on `.num`, date plates, `.day__n`, `.money`, `.figure dd`, `.rank__n`, `.seg .n`, `.dep__time`, `.dep__big`, `.dep__fig`, `.todo__due`, `.idea__far`. **Amounts and clock times inside a sentence stay in Atkinson** (`.fig` only sets lining figures), so a line a kid reads is in one face.
- Sizes are in rem. Times follow the family's clock setting (mockup: 12-hour, "9 am", "12:30 pm").
- `type.html` shows every step and sets real lines live.

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48.
- **Signs are cut square; only people are round.** Radius `--r-sm` 3 (tags, plates, ticks, calendar events), `--r-md` 4 (buttons, inputs, rows, banners), `--r-lg` 6, `--r-pill` 5 (formerly round controls are now rectangles). Avatars and the dots of the phone month stay circles: a circle is a person.
- **Rails and rules:** every `.card`, `.slist`, `.figure` and setup card hangs from a `--rail` 4 px ink top edge (square top corners, 4 px bottom radius). The page head sits on a 4 px ink rule (3 px on the phone, 6 px in the kid's colour on her pages). A board's column heads sit on a 2 px ink rule. The Ask card's rail is phosphor.
- Shadow: a 1 px line only; lift on hover for calendar events. No tilts anywhere.
- Avatars: 24, 32, 40. Tiles: 40, 56. Rank plates 52 (40 in Home's list). Route stripe 8 px (6 phone).
- Every target is 44 px or more. The tick is a 44 px hit area around a 32 px square box. Board Edit buttons are 44 px icon buttons with an `--edge` border.
- Top bar 56 px; tab bar 68 px plus `env(safe-area-inset-bottom)`, with a 3 px ink top rule.

### Moments (style.css §9)

All CSS, each played once, **nothing moves under `prefers-reduced-motion`**.

| Moment | Where | What happens |
|---|---|---|
| Today | Home's Today plate; the calendar | a green-banded plate "Today · 3 · Sat · Oct"; on the calendar a filled green number, a 5 px green top bar and "Today" beside it (desktop) |
| The next departure | Home, kid Home | "Tomorrow" is a lit ink plate; the leave-by figure flips in once, like a split-flap board |
| Crossing it off | `.todo--done`, `.tick--done` | the tick fills green with a short pop, then a straight 3 px green rule is drawn through the title |
| A flash that went well | `.banner--ok.flash` | the banner slides in; its check is a green plate with a short bar of the family's five colours wiping in beneath it |
| "Yes!" | wish answers | a solid green plate |
| Top wish | a ranked list of two or more | rank 1 is the filled plate, in the kid's colour on her pages, ink elsewhere; on Wishes the plates are joined by her line |
| A kid's pages | `body.kid.me-pN` | her page rule, current nav edge, tab plate, card pictograms and account rail are her colour |

---

## 2. Components

Class names are the API. Person colour classes are **slots** (`.p0…p8`), never names: no `.av--sam`, `.msg--maya`, `.ev--theo`. Each component has one anatomy; variants are modifiers.

| Component | Classes | Variants | When to use |
|---|---|---|---|
| Card | `.card`, `.card__head`, `.card__foot` | `--setup` (amber) | every group of content that isn't a board. Hangs from the 4 px ink rail; its icon is a pictogram (white symbol on an ink square; the kid's colour on her pages) |
| **Board** | `section.board` › `.board__head` (band: pictogram, `h2`, `.board__n` count, `.more`) › `.board__cols` (column heads, `aria-hidden`) › rows › `.board__foot` | `--late` (red block on the band) | **any list of things with a time or a distance**: Next up, To do, Coming up, Overdue, All ideas. The band re-sets `--ink`, `--link`, `--focus` locally |
| Departure row | `.deps` › `.dep` (`a` when it opens the plan): `.dep__when` (`.dep__day`, `.dep__time`), `.route`, `.dep__main` (`.dep__title`, `.meta`), `.dep__fig` | `--next` (the big row: `h3`, `.next__acts`, `.dep__leave` with `.dep__big`) | a plan on a board. When · whose line · what · one figure (drive, or drive and kind). `.board-cols-dep` sets matching column heads |
| Route stripe | `span.route` › `i.pN` per person (`aria-hidden`) | `i.p0` (Everyone) | the left edge of every departure row: one segment per person going, in their colour. Never the only cue: names and bullets are in the row |
| Board to-dos | `ul.todos.todos--board` › `.todo` with `p.todo__due` (date, then `.late` or `.muted`) and an icon-only `.todo__edit` (its name in `.sr`) | `--late` (6 px red edge) | to-dos on Home and To do. On the phone the due line drops under the title |
| Destinations board | `ul.ideas.ideas--board` › `.idea` with `p.idea__far` (`b` drive, `.way.way--{n,nne,ne,e,se,s,sw,w,nw}` with `#i-dir`) | `--unknown` ("Not looked up yet") | Ideas: pictogram · idea and who · kind · drive and direction. `.board-cols-ideas` for the heads |
| Way | `.way.way--s` + `#i-dir` icon | eight bearings and nne | a direction beside its word ("↓ south"); also in meta lines on Home |
| Button | `.btn` | `--primary` (one per view), `--quiet`, `--sm`, `[disabled]` | actions. Rectangles (4 px), 2 px ink edge; quiet ones have the 1.5 px `--edge` |
| Text button | `.textbtn`, `.linkbtn`, `.more` | — | a form action that reads like a link (Delete, Take it off my list); "All plans ›" |
| Badge | `.badge` | `--late` (solid red plate, white letters), `--act` (ink outline), `--quiet` (plain number), `--look` | counts with a word, in Barlow Condensed. Loud only for **late** and **to decide** |
| State tag | `.tag` | `--ok` Working/Connected/Added · `--better` Could be better/Not connected · `--look` Needs a look · `--broken` Not working · `--off` Off/Optional/No backup · `--when` Tomorrow/Planned · `--been` Went… · `--surprise` | how a thing stands; one tag per thing, words from §3 |
| Health pill | `.pill-health` | `--busy`, `--rest`, `--down` | Vera's state, in the sidebar and phone top bar; parents and admins only. **Quiet when all is well:** "Vera is ready" is a soft-green pill in Atkinson 700 with a still dot. **Glass and mono only when there is something to notice:** writing back (phosphor, the dot breathes until the reply lands), resting (quiet glass ink, hollow dot), can't answer (coral `--glass-alert`, square dot) |
| Avatar (line bullet) | `.av` + slot `.p0…p8` | `--sm` `--lg` | every mention of a person: a disc in their line colour with the initial in Barlow Condensed. Everyone (`.p0`) uses the house icon. Small initials are decorative: the name is always beside them |
| Vera's screen | `svg.vs` (`aria-hidden`) | `--sm` (24) · default (32) · `--lg` (40) · `--xl` (56); `--busy` (answering), `--off` (can't answer) | Vera, wherever she speaks: Ask card, chat, Status, Home's Vera row. A rounded square with a lit `>▮` prompt. **Never a face or figure** (§9) |
| FamilyDB mark | `.mark-fdb` + `.wm` (wordmark) | `--sm`; `.pane__mark` (64) | the brand: bar, sidebar, sign-in, panes, favicon (§9) |
| Glass pane | `.pane` | `--center`; `.brand-row` | brand moments only: sign-in, a first empty day, the grown-ups page, the missing page (§9) |
| Instrument (radar) | `section.mapband` › `details.mapband__fold` › `.instrument__pane` › `svg.radar` | `--wide` (desktop), `--narrow` (phone) | Ideas only, in its own band after all the cards. Desktop: always open (the summary is hidden and `::details-content` is shown). Phone: folded behind "Show the map". Each dot carries the idea's short name; no separate list (§9) |
| Add a to-do | `form.adder--todo` › `.adder__row` + `details.adder__more` | — | One row first: box and Add. Who, when and the reminder sit in `.adder__more`: folded beneath the row on the phone (summary "Who, when, reminder · Nobody picked yet · No date"), always open on the desktop, where Add is a full-width bar at the bottom. The form is `novalidate`: the server checks who and sends it back with the fold open and the error in it |
| Calendar who-marker | `.dots i` via `mini(person)`; `.cal-key` | person initial · house (Everyone) · hollow ring (past) | the phone month's day cells (up to three) and the one-line key under the calendar on Plans. On desktop every event shows its people as small avatars |
| Tile | `.tile` | `--lg`, `--ok` `--better` `--look` `--broken` `--vera` | leading icon for an idea kind (neutral) or a health area (tone) |
| Date plate | `.dt` | `--now` (2 px ink edge), `--today` (green band "Today", Home's page head only, `aria-hidden`, desktop), `--lg` `--sm` | a date: weekday on an ink band, the day in Barlow Condensed, square cut |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--boxed`, `--divided`, `--health` | every list of things that isn't a to-do or an idea card |
| To-do row | `.todos` › `.todo` | `--compact`, `--late` (6 px red edge), `--done`, `--ro` (kids) | to-dos outside a board (the kid's own, the states sheets). On a board use `.todos--board` |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | marking a to-do done; a 32 px square box in a 44 px target; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default **info (neutral card, grey icon)**, `--ok` (mint: all good, done), `--warn` (set this up), `--alert` (broken, errors); size: `--hero`, `--slim` | a message with at most one action. Resting, Off and “for your information” use the neutral default, never mint or yellow. **One “set this up” message per page** |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (charcoal glass, phosphor Send); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page |
| Starters | `.starters` › `.starter` | `--ask` (sends a complete question, `name="prompt"`); plain = a link that fills the box (`?draft=…`) | suggested messages |
| Chat room | `.chat`, `.convos`/`.convo`, `.room` (head on the band), `.scroller` › `.thread` | `.msg--person` (6 px edge in their `-mark`), `--mine` (edge on the right), `--vera` (green edge), `--pending`, `--failed`, `--system`; `.receipt`; `.earlier`; `.day-sep` (a rule with the day on an ink plate) | conversations |
| Privacy line | `.privacy` (`--room` on phone) | — | "Sam and Alex can read …"; **at every width** |
| Field | `.field`, `__label`, `__hint`, `__error`; `.req`/`.opt` | `--error` | every input; label above, error above the box, hint below |
| Form | `.form`, `.fieldset`, `.form__row`, `.actions` | — | multi-field forms |
| Choice pills | `.choices` › `.choice` (radio or checkbox) | `--person` | picking from a few; **no default where a choice must be made** |
| Disclosure | `.disclose` (`<details>`) | — | filters and form options folded away (always on the phone) |
| Segmented control | `.seg` | — | view switches; the current segment is an ink plate; Barlow Condensed |
| Search | `.searchbox` | — | search inputs |
| Faces | `.faces` › `.face` | — | "How did it go?"; three labelled faces; parents only |
| Idea card | `.ideas` › `.idea` | `--unknown`; `.ideas--one`; **`.ideas--board`** on the Ideas page | cards elsewhere (states sheets); compact rows on the phone |
| Ranked list | `.ranks` › `.rank`, `.rank__n` (a platform-number plate), `.rank__move`, `.quote`, `.decide` | `--decide`; **`.ranks--line`** (plates joined by the kid's line) | wishes |
| Calendar | `.cal`, `.week`, `.day`, `.ev`, `.ev-more`, `.daylink`, `.dots` | slot class on `.ev` (one person: solid block in their colour; `.p0`: stone block, faces), `--past`; `.day--today` (filled green number, 5 px green top bar, wash, "Today" label on desktop), `--we`, `--out` | the month as a timetable: weekdays on the navy band |
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

1. **The phone is its own layout, not the desktop stacked.** The sidebar becomes a 56 px top bar (brand, health pill for parents, and the avatar that opens the account menu, with a dot when something inside needs checking) and a **fixed bottom tab bar** of five, role-aware, with `--tabbar-total` = 68 px + `env(safe-area-inset-bottom)` for its height and the body's bottom padding, and `scroll-padding-bottom` so the focused control is never under it. The top bar is the navy fascia. The tab bar has a 3 px ink top rule, and the current tab is an inverted ink plate (the kid's colour on her pages).
2. **The list you came for is in the first screen.** On Home that is the greeting, then the Next up board's big row with **Leave by 12:30 pm** across the full width, then the To do board. The later departures are folded behind “3 more plans this month”. The order is Next up, To do, Ask Vera (one row: box and icon Send, short starters), How did it go, Wishes, Ideas. Kids: Next up, My wishes, My to-dos, Ask Vera, Ideas. Ask moved below the board because Chat is its own tab. Quick-adds are one line; options, filters and sorting fold into `<details>`. Order: heading, lede, the list, then the tools.
3. The destinations board keeps its rows: pictogram, title, “kind · who”, and the drive figure with its direction arrow on the right; tags go underneath. The radar folds behind "Show the map" after the rows.
3a. **To do starts with one row to add a to-do** (box and Add) at the top of the list; who, when and the reminder fold beneath it. Nobody is picked by default.
4. **Plans: Coming up (the board), then the month header and its Month/List switch, then the month at a glance, then How did it go.** Departure rows put the figure under the title. The month grid becomes a month at a glance: day cells are whole-cell links with person markers and a full spoken label. Weekday headers are single letters. A spill-over day shows its month in small capitals beneath the number ("28" over "SEP"), so it never wraps.
5. Settings and More rows use grid areas: icon | text, tag | chevron. The chevron never wraps.
6. The Status model table folds away and stacks; actions sit under their line.
7. **Chat is an app-height room** (on screens shorter than 560 px it falls back to normal page scroll): pills, the privacy line, a scroller that opens at the newest message (column-reverse), the box pinned above the tab bar, and a pinned "Earlier messages" bar with a fade at the top edge.
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
| `--ink` on `--paper` | body text | 15.4 | 17.3 |
| `--ink-2` on `--card` | secondary text | 9.8 | 11.1 |
| `--ink-3` on `--card` | quiet text on a panel | 6.4 | 6.9 |
| `--ink-3` on `--paper` | quiet text on the page | 5.7 | 7.6 |
| `--ink-3` on `--paper-2` | quiet text on stone | 5.0 | 6.2 |
| `--ink-3` on `--field` | placeholders | 6.4 | 6.3 |
| `--link` on `--card` / `--paper` | links | 6.3 / 5.5 | 9.9 / 11.0 |
| `--vera` on `--card` | Vera's name and green text | 6.3 | 13.5 |
| `--edge` on `--card` | field, tick, icon-button and quiet-button edges (3:1) | 4.0 | 5.0 |
| `--edge` on `--paper` | controls on the page (3:1) | 3.5 | 5.5 |
| `--on-band` on `--band` | fascia and band text, board names, weekday heads | 17.4 | 12.9 |
| `--on-band-2` on `--band` | nav items, quiet text in the band | 9.7 | 7.9 |
| `--band` on `--on-band` | the current nav item (inverted plate) | 17.4 | 12.9 |
| `--phosphor` on `--band` | focus ring and wordmark cursor on the band | 13.6 | 11.3 |
| `--card` on `--ink` | date-plate weekday, "Tomorrow" plate, current tab, selected segment, chosen pill, chat day plate | 17.4 | 15.7 |
| `--on-primary` on `--primary` | primary button | 17.4 | 15.7 |
| `--on-alert` on `--alert` | the late plate (badge) | 6.6 | 8.3 |
| `--alert` on `--card` | "6 days late", errors | 6.6 | 7.6 |
| `--alert` on `--alert-soft` | tag Not working | 5.6 | 7.1 |
| `--on-today` on `--today-bg` | Today plate band; today's number on the calendar | 4.7 | 14.9 |
| `--vera` on `--today-wash` | "Today" beside the calendar number | 5.6 | 12.8 |
| `--on-vera` on `--vera-bg` | done tick, meter, flash check, "Yes!" plate | 4.7 | 11.2 |
| `--on-send` on `--send` | Send on Ask | 14.6 | 14.8 |
| `--ask-ink` / `--ask-ink-2` on `--ask-bg` | Ask card text / quiet text | 17.4 / 10.7 | 15.3 / 11.4 |
| `--ok` on `--ok-soft` | tag Working | 5.4 | 10.2 |
| `--warn` on `--warn-soft` / `--card` | Needs a look / Could be better | 6.5 / 7.3 | 9.0 / 9.8 |
| `--ink-2` on `--paper-2` | tag Off | 7.6 | 10.0 |
| `--vera` on `--vera-soft` | the calm "Vera is ready" pill | 5.5 | 12.5 |
| `--ink` on `--everyone` / `--paper-2` | words on a stone (several people) calendar block | 12.0 / 13.6 | 6.9 / 14.1 |
| `--everyone-ink` on `--everyone` | Everyone's house bullet | 6.7 | 5.5 |
| `--everyone-mark` on `--card` | Everyone's route segment and dot (decorative; 3:1 anyway) | 4.0 | 6.9 |
| `--on-p` on `--p1` … `--p8` | bullet letters, words on a one-person calendar block, **a kid's current tab plate** | 6.5 / 6.7 / 6.8 / 8.5 / 8.3 / 6.6 / 10.0 / 7.6 | 6.7 / 6.9 / 7.0 / 8.8 / 8.5 / 6.8 / 10.3 / 7.9 |
| `--p1…8-mark` on `--card` | message edges, dots (3:1) | 3.9–4.8 | 7.9–10.9 |
| `--p1…8-ink` on `--p1…8-soft` | names in a message (lowest of eight) | 5.2 | 8.6 |
| `--phosphor` on `--glass` | phosphor on glass: pill, pane lines, focus ring | 14.7 | 15.6 |
| `--glass-ink` / `--glass-ink-2` on `--glass` | pane text / quiet text | 16.3 / 10.6 | 17.3 / 11.3 |
| `--glass-alert` on `--glass` | "can't answer" pill | 8.2 | 8.7 |
| `--cursor` on `--paper` | wordmark cursor off the band (sign-in, panes use phosphor) (3:1, non-text) | 3.4 | 13.5 |
| `--ask-edge` on `--ask-bg` | the Ask box's edge at night (3:1) | n/a | 5.0 |

Route stripes, rails, rules and the red block on an Overdue band are decorative: the names, words and headings beside them carry the meaning.

The glass pane has no contrast duty of its own in the dark (it is #070A09 on #0C100F): its 1 px `--glass-line` rim and the phosphor inside carry it. **Focus on glass is phosphor** (`.pane`, `.instrument__pane`, `.pill-health` set `--focus: var(--phosphor)`, 14.7:1), because the ink ring is 1.2:1 there.

Disabled controls are exempt, but each also carries its reason in words.

**Checklist for every page**
- One `h1`; headings in order. (Home's Today plate and every board's column heads are `aria-hidden`; the eyebrow and each row carry the same facts.) Chat on the phone keeps its `h1` visually hidden, not `display:none`.
- A visible "Skip to content" link on first Tab. A 3 px focus ring on everything (phosphor on the Ask card). Whole-card links show focus with `:focus-within`.
- No meaning by colour alone: late says "6 days late", tags carry words, calendar events carry a spoken label, badges carry words.
- Every control is named: ticks "Mark done: …", faces "Loved it (Silver Falls hike)", move buttons "Move Ice skates up", Edit "Edit Call the dentist about Theo".
- Form fields have labels; errors are tied with `aria-describedby` and `aria-invalid`; the summary has `role="alert"`; flashes have `role="status"`.
- Chat thread: `role="log"`, focusable (`tabindex="0"`), named.
- Targets are 44 px; type is 14 px or more (13 px only on tab labels and overlines), set in rem; the top and tab bars use `min-height`.
- **Nothing blinks for more than five seconds** (2.2.2): the wordmark cursor blinks twice and stays lit, the pill's dot breathes once. Only things that end on their own move longer: Vera's busy screen and the typing dots, while a reply is on its way.
- `prefers-reduced-motion`: nothing moves at all.
- **Never `display:none` beside an `aria-hidden` stand-in.** When a short label replaces a long one on the phone (starters, Edit links), the long one is hidden with the `.sr` clip pattern, so it stays the control's name.
- Icon-only buttons (including the board's Edit) have `--edge` borders (4.0:1); a disabled one is `--ink-3` with a dashed edge and keeps its reason in words.
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

The Board is the family's day set like a departure board: navy fascia and bands, white panels on warm enamel, each person a line colour. FamilyDB is the small screen that runs the board. The brand is that pairing: **the station's signage is the family's; a pane of dark glass with green light is FamilyDB's.** The mark is unchanged (not recoloured). It sits at the top of the navy fascia like the operator's badge on a station sign. The navy structure is the voice and is not glass: phosphor never lights the family's items.

### The brand rule

**The board, its bands and the line colours are the family's. Phosphor on charcoal glass is FamilyDB's and Vera's.** Glass and phosphor appear only where one of three things is:

1. **the brand**: the mark, the wordmark, and the brand moments (sign-in, a family's first empty day, the grown-ups page a kid lands on, the missing page);
2. **Vera**: her screen, the Ask card (charcoal glass by day, green-rimmed glass at night, with a phosphor Send);
3. **something live**: the status pill when it has something to say (writing back, resting, can't answer), a reply on its way, the cursor in her box, today's date. When Vera is simply ready the pill is calm and on paper.

Never on the family's own things: names, ideas, to-dos, wishes, plans, and the buttons and links that act on them (those use `--link`, Vera's green by day and a lighter green at night, and `--primary`, ink by day and inverted at night; never phosphor). **Mono only on the glass**: nothing printed on paper is in the mono. Every touch says something true; nothing is only ornament. No dark page in light mode, no CRT curvature, no vignettes, no heavy scanlines, no pixel font.

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
- **On the fascia:** the charcoal square is the mark's own glass, so it sits directly on the navy sidebar or top bar; its phosphor stroke carries it (13.6:1 on the band). No extra frame or shadow.
- **On dark:** the same file. At night the square is close to the page, so it keeps its own edge from the stroke; nothing is inverted. Never recolour the stroke (no white, no `--vera` green), and never use it without its square.
- Head tags: `favicon.svg` (`image/svg+xml`), `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png` (180). The 512 is for the web manifest.

### The wordmark

"FamilyDB" in **Barlow Semi Condensed 700**, letter-spacing +0.005em, set like the name on a station fascia, followed by a **lit cursor**: a block `.42em × .86em`, 0.14em after the B, radius 1.5 px.

- Sizes: 24 px in the sidebar, 20 px in the phone bar, 18 px inside a pane. It is always beside the mark; the link around both is named "FamilyDB, home".
- **On the fascia (sidebar, phone bar) and on glass:** white or glass-ink letters, cursor `--phosphor` with `--phosphor-glow` (`.side` and `.topbar` set `--cursor` to phosphor).
- **On paper** (rare: specimens): ink letters, cursor `--cursor` #12945A (3.4:1, non-text).
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

### The mono: only on the glass

JetBrains Mono 400, self-hosted (`fonts/jetbrains-mono-400.woff2`, 21 KB), 14 px. **Only on dark glass:** the status pill when it has something to say (writing back, resting, can't answer) and the lines inside a pane ("404 · nothing at this address"). The radar is glass but its labels are Atkinson, because kids read them. Never on paper: her receipts and everything the family reads are Atkinson; names and times on messages are Barlow Condensed, like a line on the board (§1 Type). Numbers and units are kept together with no-break spaces.

### Phosphor elements, their tokens, where they may and may not appear

| Element | Tokens | May appear | May not |
|---|---|---|---|
| The mark | `--glass` (fixed #0E1312 in the file), `--phosphor` | bar, sidebar, sign-in, panes, favicon, icons, Settings' key | as Vera; inside a message; on the family's items |
| Wordmark cursor | `--cursor`, `--cursor-glow` (dark: `--phosphor`) | after "FamilyDB" only; the caret in Vera's box (`caret-color`) | anywhere else as decoration |
| Vera's screen | `--glass`, `--glass-line`, `--phosphor`, `--vs-halo` | wherever Vera is: Ask, chat, Status and Home rows, pending, Settings' key, the kid's empty chat | for a person; as a decoration with no Vera |
| Status pill (when there's something to notice) | `--glass`, `--glass-line`, `--phosphor`, `--phosphor-glow`, `--glass-alert` | sidebar and phone bar, parents only. Writing back: phosphor mono, the dot breathes until the reply lands. Resting: `--glass-ink-2`, hollow dot. Can't answer: `--glass-alert` #FF8B74 (8.2:1 on glass), square dot. When Vera is ready the pill is not glass at all: `--vera-soft`, `--vera`, Atkinson 700, a still dot | kids' pages; anywhere it isn't Vera's real state; "ready" |
| Glass pane | `--glass`, `--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--phosphor` | the four brand moments: sign-in, a first empty day, the grown-ups page, the missing page. Faint scanlines inside are fine | as a card style; around the family's content; more than one per page |
| The radar | `--glass`, `--phosphor` at 14–25 % for rings and axes, `--glass-ink` and `--glass-ink-2` for labels | Ideas only, in its own band after all the cards (folded behind "Show the map" on the phone). Drive time is distance from home on a piecewise scale that gives the first half hour 70 % of the radius (rings at 15 min, 30 min, 1 h, 2 h, 3 h, labelled on alternate sides of the north axis); direction is bearing, north up; "Home" marks the middle. Each dot carries the idea's short name ("Pumpkin patch", "Oaks Park"): the first words of its card's title, so a kid can match it. Ideas in the same direction are fanned a few degrees apart. The SVG is `aria-hidden`: the cards are the list, and each card already says its drive time and direction | between the cards; any second page; a separate numbered list; mono labels. One instrument per page at most. If every idea is inside one ring, show the cards alone |
| Ask card | `--ask-bg`, `--ask-rim`, `--ask-edge`, `--send` | Home's and the kid's Ask card: the information point, a navy panel with a 4 px phosphor rail and a phosphor Send by day; green-rimmed glass with an edged box at night | anywhere else |
| Live glow | `--phosphor-glow`, `--vs-halo` | the writing-back pill, the panes, Vera's screen, the wordmark cursor | the calm "ready" pill, chat bubbles (Vera's included), cards, buttons |

The radar is drawn twice from the same data, so names stay readable: a wide 860 × 440 plot for the desktop (names 15 px, drawn at 1:1) and a narrow 360 × 400 plot for the phone (names 14 px). Ring and compass labels are 13 px Atkinson; every label position is set per idea in the data, so nothing sits on a compass letter.

### Brand moments

- **Sign-in:** a pane with the mark, the wordmark and "awake, Saturday 3 October", then "Who's using FamilyDB?" and the people on paper.
- **A first empty day** (`states-content.html`): "FamilyDB is set up and awake. Welcome, Sam. This is your family's table." on glass, then the empty cards on paper.
- **The grown-ups page** (`grownups.html`): the mark alone at 64 px, glowing, above the explanation; the explanation stays on paper. The mark is its own glass, so no pane around it.
- **The missing page** (`404.html`): a centred pane, the mark, "404 · nothing at this address" in the mono, then "This page isn't here", Go to Home and Ask Vera to find it.

### The dark theme: the board after dark

At night the page is near-black (`--paper` #0B1019), panels are slate (`--card` #131B28), and the bands lift to a lighter slate (`--band` #1F2B40) so the structure still shows. The ink is near-white (#F2F4F8). Vera's things and today are phosphor (`--vera`, `--today-bg` #6DFF9C), amber (`--warn` #F5B94A) means it needs a look, and coral (`--alert` #FF8B74) means late or broken. The late plate is coral with dark letters (8.3:1). People keep their line colours with the same dark letters (6.7:1 or more), and message edges use the lightened `-mark`.

**The hierarchy holds at night.** Rails, the page rule and every inverted plate flip to near-white, so "you are here" and the date plates still stand out. The primary button inverts to near-white with dark words (15.7:1). Links are a lighter green (`--link` #8BD3B4), never phosphor. The Ask card is the one green-rimmed block. Only the pill, the panes and Vera's screen glow. Every pair is in §7.

By day, the Ask card is a navy panel with a phosphor rail and Send. Its text is 17.4:1.
