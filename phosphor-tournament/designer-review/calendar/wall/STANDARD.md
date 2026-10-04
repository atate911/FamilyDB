# FamilyDB · Kitchen Wall · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth. This document says how to use them.

**The rule behind everything:** one plain sentence first, cards below it, and a person's colour wherever that person appears. Every status is a sentence, not a code. Saturated colour means *a person*, green means *today or Vera*, ink means *something you press or picked*, and red means *late or broken*.

*Kitchen Wall* is Kitchen Table restyled as the family's wall calendar (see `DIRECTION.md`). The pages, words, layout and states are unchanged; colour, type, surfaces, lines and radii changed.

---

## 1. Tokens

All values live on `:root` in `style.css` §2. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root`.

### Colour

| Token | Light (Kitchen Wall) | Dark (the wall at night) | Use |
|---|---|---|---|
| `--paper` | #F3F5F8 | #0D1117 | page background: cool grey, so white cards read as sheets on a wall |
| `--paper-2` | #E8ECF1 | #141A22 | tracks, neutral tiles, "Off" tags, the segmented control's well |
| `--card` | #FFFFFF | #171D26 | cards, rows, **the sidebar and the phone top bar** |
| `--field` | #FFFFFF | #1C2330 | inputs, tick rings |
| `--ink` | #121A26 | #EAEEF3 | text; also the date tile's weekday band, the primary button and every picked control |
| `--ink-2` | #3F4A5A | #C3CBD6 | secondary text, meta |
| `--ink-3` | #556070 | #9AA5B3 | quiet text: hints, timestamps, calendar weekday heads (still AA) |
| `--line` / `--line-2` | #E1E6ED / #CDD4DE | #252D39 / #364050 | hairlines and the calendar grid (decorative only) |
| `--edge` | #7A8596 | #7D8899 | **control edges**: inputs, selects, tick rings, choice pills, quiet buttons (3:1) |
| `--vera` | #0B6E4F | #6DFF9C | Vera's green as text and icons. Phosphor in the dark |
| `--vera-bg` / `--on-vera` | #0A7A55 / #FFF | #4FE08A / #0D1117 | the meter fill, a done tick |
| `--vera-soft` / `--vera-line` | #E1F3EA / #B5DEC9 | #0F2419 / #22513A | Vera's surfaces, the calm pill, the current nav item |
| `--today-bg` / `--on-today` | #0A7A55 / #FFF | #6DFF9C / #0D1117 | **today**: the calendar's day disc and top rule, the green band of Home's today tile |
| `--today-wash` | #EEF8F2 | #12201B | today's calendar cell |
| `--ask-bg` / `--ask-ink` / `--ask-ink-2` | #0F1720 / #FFF / #C5CFDB | #0E1A17 / #EAEEF3 / #C3D2CA | the Ask Vera card: the brand's charcoal glass by day, green-rimmed glass at night |
| `--ask-rim` / `--ask-edge` | faint white inset / none | 1.5 px #3E8A66 rim + faint glow / #7D8899 | the Ask card's edge and its box's edge at night |
| `--send` / `--send-2` / `--on-send` | #6DFF9C / #95FFB8 / #0F1720 | same / #0D1117 | the Ask card's Send: lit phosphor (was sun yellow). Focus inside the card is phosphor too |
| `--link` | #0B6E4F | #8BD3B4 | links: Vera's green by day, a lighter green at night, never phosphor |
| `--primary` / `-2` / `--on-primary` | #121A26 / #2A3442 / #FFF | #EAEEF3 / #FFF / #0D1117 | the one primary button: **ink**, inverted at night, so no accent colour competes with the people |
| `--ok`, `-soft`, `-line` | #1D6E42, #E2F4E8, #B9E0C6 | #7FE3A5, #11261B, #24503A | Working, Connected, done |
| `--warn`, `-soft`, `-line` | #7A4D00, #FFF4D6, #F0D48A | #F5B94A, #2A2112, #5E4620 | **only** “set this up” and “needs a look” |
| `--alert`, `-soft`, `-line` | #B42318, #FDE8E6, #F5C2BD | #FF8B74, #33191A, #5C2E2B | late text, broken, form errors. Nothing else is red |
| `--focus` | #121A26 | #EAEEF3 | focus ring (phosphor inside the Ask card and on glass) |
| `--p1…--p8` (+ `-soft`, `-ink`, `-mark`) | p1 #2F5D9B · p2 #7B4790 · p3 #A83C80 · p4 #A2560E · p5 #0B6A84 · p6 #5448B0 · p7 #59661A · p8 #6F4E37 | same bases; `-soft` darkens to a tinted charcoal, `-ink`/`-mark` lighten (e.g. p3 soft #2E1A28, mark #EBA6D3) | **person colour slots, unchanged from Kitchen Table**, assigned per member by the server (`person.slot`), never by name. `.p1…p8` set `--p`, `--p-soft`, `--p-ink`, `--p-mark`. New in Kitchen Wall: **a one-person plan on the calendar is a solid block of `--p` with white words**, the way a calendar app paints its calendars |
| `--everyone…` (`.p0`) | #5A6472, soft #EBEEF2, mark #7A8596 | #5E6A79, soft #1E2530, mark #9AA5B3 | Everyone and several-people plans: always neutral (a grey block with each face) |
| `--{person}-soft` / `--{person}-ink` | e.g. Maya #F6E3EF / #9C3777 | e.g. Maya #2E1A28 / #EBA6D3 | chat bubbles, names in bubbles |
| **Brand** (§9) `--glass` / `--glass-2` / `--glass-line` | #0E1312 / #161D1B / #2A3632 | #070A09 / #0E1312 / #2B3B34 | the charcoal glass of the mark, Vera's screen, the pill and the panes |
| `--glass-ink` / `--glass-ink-2` | #E9F1EC / #B9C6BF | same | text on glass |
| `--phosphor` / `--phosphor-dim` / `--phosphor-glow` | #6DFF9C / 34 % / 50 % | same | lit things on glass, and the Ask card's Send |
| `--cursor` / `--cursor-glow` | #12945A / 35 % | #6DFF9C / 55 % | the wordmark's cursor and the caret in Vera's box |
| `--vs-halo` | #12945A at 35 % | #6DFF9C at 45 % | the 3 px halo round Vera's screen |

**What each colour does.** Grey and white are the surface. Ink is for pressing and picking (primary button, selected segment, chosen pill, the date tile's band, the next plan's tile edge). Green is today and Vera, and nothing else saturated is the app's own. People's eight colours carry the rest. Amber says "set this up"; red says late or broken. The cream paper, the beige lines, the forest-and-sun pairing and the warm card fills of Kitchen Table are gone.

**Maya's slot (p3) is raspberry, not red-pink**, so it never reads as "late" (it is further still from the new `--alert` #B42318), and slot 8 is cocoa brown. Checked pairwise under deuteranopia and protanopia (Machado): eight colours can't all stay apart for every eye, so **colour is never the only cue**: every person marker carries an initial or the house, and every calendar block carries its time, title and faces.

**Person colours come from the family's data.** The five above are the mockup family. A real install assigns each new person the next colour from a fixed set of eight. Each colour is checked for 4.5:1 with white letters (now also the words on a calendar block) and for its own `-soft`/`-ink` pair.

### Type

| Token | Size | Use |
|---|---|---|
| `--t-xs` | 13 px | **only** capitals: tab-bar labels, `.overline`; date-tile weekday and month and calendar weekday heads (these three in Manrope 800, +0.1em) |
| `--t-sm` | 14 px | the floor: tags, badges, hints, names on messages; the mono on glass |
| `--t-meta` | 15 px | meta lines, small body; the page eyebrow (Manrope 700; today's green on the phone's Home) |
| `--t-md` | 17 px | body (line height 1.5), row titles (700, 1.25), to-do titles on Home; calendar day numbers (Manrope 800) |
| — | 18 px | to-do titles on To do (700) |
| `--t-lede` | 18 px | the sentence under a page title (16 on phone) |
| `--t-h3` / `--t-h2` / `--t-h1` | 18 / 21 / 40 px (h1 32 on phone) | headings in Manrope: h1 800 at −0.025em, h2 and h3 700; Next up's title is 26 (22 on phone) in 800 |
| — | 28 / 36 / 21 px | date-tile day: normal / Next up and Home's today / small (Manrope 800, tabular) |
| — | 28 px | the month title on Plans (Manrope 800) |
| — | 30 / 32 px | money / Status figures (Manrope 800, tabular) |
| `--t-display` | 44 px | the big money figure on Status |
| `--font-mono` | 14 px | JetBrains Mono 400: text on dark glass only (§9) |

- **Fonts** (`fonts/`, self-hosted, Latin): **Atkinson Hyperlegible** 400/700 for every word (unchanged: chosen for the kids' reading); **Manrope** (`manrope-wght.woff2`, 21 KB, OFL, licence in `fonts/manrope-OFL.txt`; one variable file, weights 500–800, Latin subset with `tnum`, `pnum`, `case`, `kern`) for headings, the wordmark, and every date, time and amount; JetBrains Mono 400 for text on dark glass only. Fraunces and the Fraunces Figures files are gone. No other faces.
- **Why Manrope.** The serif headings and serif figures were most of what read as "recipe site". A calendar's material is dates and times, so the new face is chosen for its figures first: lining, wide, with an open zero and a true tabular set, square-shouldered enough to look like a schedule and to read across a kitchen, with round dots and open apertures that keep it friendly next to Atkinson. One face now does headings and numbers, so the big date, the big money and the "12:30" in a sentence are the same digits.
- **Sizes are in rem** (16 px = 1 rem), so a reader's larger default text size grows every step and the hierarchy keeps its order. The only px type is inside drawings (the radar, the phone month's 9 px initials).
- **Tracking.** Manrope headings are tracked in (h1 −0.025em, Next up and the money −0.02em, h2 −0.01 to −0.015em) and given `word-spacing: .06em` back, so titles stay crisp without words running together. No alternates are switched on.
- **Figures.** `--font-num` is Manrope with `tabular-nums lining-nums`: `.num`, date tiles, money, the 30-day figures, calendar day numbers, wish ranks, setup step numbers, segment counts and the meter scale. **Every amount and clock time in running text** is `.fig` (added by one filter on the rendered page): the family `"Manrope Figures"`, the same file limited by `unicode-range` to `$ , . 0–9 : ¢`, set proportional, at the weight of the line around it, so "$0.00 of your $2.00" and "7:48 pm" always have the open zero. Other numbers in running text ("3 to-dos", "last 30 days") stay Atkinson, with its slashed zero.
- `.code` switches back to Atkinson (with its slashed zero) for model names, keys and codes.
- Times follow the family's clock setting; the mockup uses the 12-hour clock with no leading zero ("9 am", "12:30 pm").
- `type.html` shows every step and sets real lines live.

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48.
- Radius (crisper than Kitchen Table): `--r-sm` 6 (calendar events, tags, segments), `--r-md` 8 (inputs, rows, banners, tiles, **buttons**, icon buttons), `--r-lg` 12 (cards, the Ask card, the calendar), `--r-pill` (avatars, badges, starters, choice pills, the health pill).
- Shadow: a 1 px cool shadow under cards; lift on hover only. No warm shadows.
- Avatars: 24, 32, 40. Tiles: 40, 56.
- Every target is 44 px or more (`--target`). The tick is a 44 px hit area around a 32 px ring.
- Top bar 56 px; tab bar 68 px plus `env(safe-area-inset-bottom)`.

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
| Date tile | `.dt` | `--now` (the next plan: heavier ink edge), `--today` (green band: Home's today tile only), `--lg` `--sm` | a plan's date; on the desktop Home, today's date beside the greeting (`aria-hidden`: the eyebrow line says the same date; hidden on the phone to keep the first screen) |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--boxed`, `--divided`, `--health` | every list of things that isn't a to-do or an idea card |
| To-do row | `.todos` › `.todo` | `--compact` (Home), `--late` (4 px red rule), `--done` (struck through after a tick), `--ro` (kids: read-only, icon tile instead of tick) | to-dos |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | marking a to-do done; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default **info (neutral card, grey icon)**, `--ok` (mint: all good, done), `--warn` (set this up), `--alert` (broken, errors); size: `--hero`, `--slim` | a message with at most one action. Resting, Off and “for your information” use the neutral default, never mint or yellow. **One “set this up” message per page** |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (charcoal glass, phosphor Send); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page |
| Starters | `.starters` › `.starter` | `--ask` (sends a complete question, `name="prompt"`); plain = a link that fills the box (`?draft=…`) | suggested messages |
| Chat room | `.chat`, `.convos`/`.convo`, `.room`, `.scroller` › `.thread` | `.msg--{person}`, `--mine`, `--vera`, `--pending`, `--failed`, `--system`; `.receipt`; `.earlier`; `.day-sep` | conversations |
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
| Calendar | `.cal`, `.week`, `.day`, `.ev`, `.ev-more`, `.daylink`, `.dots` | slot class on `.ev` (one person: a solid block in their colour, white words; `.p0`: grey block, left rule, faces), `--past` (grey); `.day--today` (green disc, green top rule, wash), `--we`, `--out` | the month view |
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

1. **The phone is its own layout, not the desktop stacked.** The sidebar becomes a 56 px top bar (brand, health pill for parents, and the avatar that opens the account menu, with a dot when something inside needs checking) and a **fixed bottom tab bar** of five, role-aware, with `--tabbar-total` = 68 px + `env(safe-area-inset-bottom)` for its height and the body's bottom padding, and `scroll-padding-bottom` so the focused control is never under it. The current tab has a 3 px green top bar as well as its tint.
2. **The list you came for is in the first screen.** On Home, Ask Vera is one row (box and icon Send) with short starters, so the next plan and anything late show above the tab bar; cards are capped with “3 more plans” and “All 4 to-dos”, and the card order is Ask, Next up, To do, How did it go, Wishes, Ideas (kids: Ask, My wishes, My to-dos, Next up, Ideas). Quick-adds are one line; options, filters and sorting fold into `<details>`. Order: heading, lede, the list, then the tools.
3. Ideas become compact rows: tile, title, "who · drive", tags underneath. The radar folds behind "Show the map" after the rows.
3a. **To do starts with one row to add a to-do** (box and Add) at the top of the list; who, when and the reminder fold beneath it. Nobody is picked by default.
4. **Plans: the month header, then the Month/List switch, then the month at a glance, then Coming up.** The month grid becomes a month at a glance: day cells are whole-cell links with person markers and a full spoken label. Weekday headers are single letters. A spill-over day shows its month in small capitals beneath the number ("28" over "SEP"), so it never wraps.
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
| `--ink` on `--paper` | body text | 16.0 | 16.2 |
| `--ink-2` on `--card` | secondary text | 9.0 | 10.3 |
| `--ink-3` on `--card` | quiet text, on card | 6.4 | 6.8 |
| `--ink-3` on `--paper` | quiet text, on paper | 5.8 | 7.6 |
| `--ink-3` on `--paper-2` | quiet text on grey | 5.4 | 7.0 |
| `--ink-3` on `--field` | placeholders | 6.4 | 6.3 |
| `--link` on `--card` | links | 6.3 | 9.7 |
| `--link` on `--paper` | links on paper | 5.7 | 10.9 |
| `--vera` on `--card` | Vera's name and green text | 6.3 | 13.3 |
| `--edge` on `--field` | field and tick edge (3:1) | 3.7 | 4.4 |
| `--edge` on `--card` | field edge, icon buttons, quiet buttons (3:1) | 3.7 | 4.7 |
| `--on-primary` on `--primary` | primary button | 17.5 | 16.2 |
| `--primary` on `--paper` | primary button against the page (3:1) | 16.0 | 16.2 |
| `--card` on `--ink` | date-tile weekday band | 17.5 | 14.5 |
| `--on-today` on `--today-bg` | today's disc and today's tile band | 5.3 | 14.8 |
| `--today-bg` on `--card` | today disc against the cell (3:1) | 5.3 | 13.3 |
| `--on-vera` on `--vera-bg` | done tick, meter | 5.3 | 11.1 |
| `--on-send` on `--send` | Send on Ask | 14.1 | 14.8 |
| `--ask-ink` on `--ask-bg` | Ask card text | 18.0 | 15.3 |
| `--ask-ink-2` on `--ask-bg` | Ask card quiet text | 11.4 | 11.4 |
| `--ok` on `--ok-soft` | tag Working | 5.5 | 10.2 |
| `--warn` on `--warn-soft` | tag Needs a look | 6.6 | 9.0 |
| `--warn` on `--card` | tag Could be better | 7.3 | 9.6 |
| `--alert` on `--alert-soft` | tag Not working, late badge | 5.6 | 7.1 |
| `--alert` on `--card` | late text, errors | 6.6 | 7.4 |
| `--ink-2` on `--paper-2` | tag Off | 7.6 | 10.7 |
| `--vera` on `--vera-soft` | the calm "Vera is ready" pill, current nav | 5.4 | 12.8 |
| `--p1-ink` on `--p1-soft` | slot 1 name in a bubble | 5.5 | 7.9 |
| `--maya-ink` on `--maya-soft` | Maya's name in a bubble | 5.3 | 8.4 |
| `--ink` on `--maya-soft` | text in Maya's bubble | 14.3 | 13.9 |
| `--everyone-mark` on `--card` | Everyone's dot (3:1) | 3.7 | 6.8 |
| `--ink` on `--paper-2` | words on a grey (several people) calendar block | 14.7 | 15.0 |
| white on `--p1` … `--p8` | avatar letters, calendar initials, **words on a one-person calendar block** | 6.6 / 6.7 / 5.8 / 5.4 / 6.2 / 7.2 / 6.3 / 7.4 | same |
| white on `--everyone` | Everyone's avatar | 6.0 | 5.5 |
| `--p1…8-mark` on `--card` | dots, rules (3:1) | 5.3–7.3 | 8.3–10.3 |
| `--paper` on `--ink` | selected segment, chosen pill | 16.0 | 16.2 |
| `--phosphor` on `--glass` | phosphor on glass: pill, pane lines, focus ring | 14.7 | 15.6 |
| `--glass-ink` on `--glass` | pane text | 16.3 | 17.3 |
| `--glass-ink-2` on `--glass` | pane quiet text, resting pill | 10.6 | 11.3 |
| `--glass-alert` on `--glass` | "can't answer" pill | 8.2 | 8.7 |
| `--cursor` on `--paper` | wordmark cursor (3:1, non-text) | 3.6 | 14.8 |
| `--ask-edge` on `--ask-bg` | the Ask box's edge at night (3:1) | n/a | 5.0 |
| Ask rim #3E8A66 on `--paper` | the Ask card's edge at night (3:1) | n/a | 4.5 |

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

Kitchen Wall is the family's calendar on the kitchen wall: a bright grid, today in green, people in their colours. FamilyDB is the small screen that runs it. The brand is that pairing, used a little: **a pane of dark glass with green light, set on a white wall.** It is a sprinkle. The layout, the components and every check in §7 are unchanged by it.

### The brand rule

**The white wall is the family's. Phosphor on charcoal glass is FamilyDB's and Vera's.** Glass and phosphor appear only where one of three things is:

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
- **On the page:** the charcoal square is the mark's own glass, so it sits directly on the white sidebar or top bar; no extra frame or shadow.
- **On dark:** the same file. At night the square is close to the page, so it keeps its own edge from the stroke; nothing is inverted. Never recolour the stroke (no white, no `--vera` green), and never use it without its square.
- Head tags: `favicon.svg` (`image/svg+xml`), `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png` (180). The 512 is for the web manifest.

### The wordmark

"FamilyDB" in **Manrope 800**, letter-spacing −0.03em (tight, like a clock face's numerals), followed by a **lit cursor**: a block `.42em × .86em`, 0.14em after the B, radius 1.5 px.

- Sizes: 21 px in the sidebar, 20 px in the phone bar, 18 px inside a pane. It is always beside the mark; the link around both is named "FamilyDB, home".
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

### The mono: only on the glass

JetBrains Mono 400, self-hosted (`fonts/jetbrains-mono-400.woff2`, 21 KB), 14 px. **Only on dark glass:** the status pill when it has something to say (writing back, resting, can't answer) and the lines inside a pane ("404 · nothing at this address"). The radar is glass but its labels are Atkinson, because kids read them. Never on paper: Vera's message times, her receipts and everything the family reads are Atkinson, with money and clock times in Manrope figures (§1 Type). Numbers and units are kept together with no-break spaces.

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
| Live glow | `--phosphor-glow`, `--vs-halo` | the writing-back pill, the panes, Vera's screen, the wordmark cursor | the calm "ready" pill, chat bubbles (Vera's included), cards, buttons |

The radar is drawn twice from the same data, so names stay readable: a wide 860 × 440 plot for the desktop (names 15 px, drawn at 1:1) and a narrow 360 × 400 plot for the phone (names 14 px). Ring and compass labels are 13 px Atkinson; every label position is set per idea in the data, so nothing sits on a compass letter.

### Brand moments

- **Sign-in:** a pane with the mark, the wordmark and "awake, Saturday 3 October", then "Who's using FamilyDB?" and the people on paper.
- **A first empty day** (`states-content.html`): "FamilyDB is set up and awake. Welcome, Sam. This is your family's table." on glass, then the empty cards on paper.
- **The grown-ups page** (`grownups.html`): the mark alone at 64 px, glowing, above the explanation; the explanation stays on paper. The mark is its own glass, so no pane around it.
- **The missing page** (`404.html`): a centred pane, the mark, "404 · nothing at this address" in the mono, then "This page isn't here", Go to Home and Ask Vera to find it.

### The dark theme: the wall at night

At night the page is blue-black slate (`--paper` #0D1117, `--card` #171D26), the ink is near-white (#EAEEF3), Vera's things and today are phosphor (`--vera`, `--today-bg` #6DFF9C), amber (`--warn` #F5B94A) is for what needs a look, coral (`--alert` #FF8B74) for late and broken, and people keep their colours: the solid calendar blocks keep the same bases (white words still 5.4:1 or more), bubbles and dots use the lightened `-ink`/`-mark` on tinted charcoal `-soft`.

**The hierarchy holds at night.** The Ask card stays the one lit block: green-rimmed glass (`--ask-bg` #0E1A17) with the brightest edge on the page and an edged box. The primary button inverts to near-white with dark words (16.2:1), the date tile's band inverts with it, and links are a lighter green (`--link` #8BD3B4), never phosphor. Vera's bubbles have no glow; only the pill, the panes and her screen glow. Every pair is in §7.

By day, the Ask card is the brand's charcoal glass (`--ask-bg` #0F1720) with a phosphor Send (was deep green with a sun-yellow Send), so the one dark block on a white wall is plainly FamilyDB's; its text is 18.0:1.
