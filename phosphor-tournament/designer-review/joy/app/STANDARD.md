# FamilyDB · Fridge Door · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth. This document says how to use them.

**The rule behind everything:** one plain sentence first, cards below it, and a person's colour wherever that person appears. Every status is a sentence, not a code. Saturated colour means *a person* (or Vera's green), and red means *late or broken*.

---

## 1. Tokens

All values live on `:root` in `style.css` §2. Fridge Door restyles Today Line (itself a restyle of Kitchen Table): the pages, components and words are unchanged. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root`.

### Colour

The page is a planner's **lilac with a faint printed dot grid** (`--dot`, 24 px), with white cards that sit on it on a 3 px lip (`--lip`). Ink is deep indigo. **One accent, "now" green**, marks time and action: today, the plan nearest to now, links, the one primary button. **People's colours are the family's palette**: clear felt-tip colours used for avatars, event bars and tints, bubbles and stickers. **The viewer wears their own colour** (`--me…`) where they are: the current nav item and tab, their account card, the highlighter under each page title, and a kid's own wish ranks. There is no warm fill and no yellow except amber for "set this up" and "needs a look".

| Token | Light (Fridge Door) | Dark (kitchen lights down) | Use |
|---|---|---|---|
| `--paper` | #F2F0FA | #121122 | page background, under the dot grid |
| `--dot` / `--lip` | #D6D2EA / #DAD6EC | #23213A / #0A0916 | the printed dot grid; the 3 px lip under cards, rows and tiles (both decorative) |
| `--paper-2` | #E7E4F4 | #18172B | sidebar, tracks, neutral and kind tiles, date-tile weekday band, "Off" tags |
| `--card` | #FFFFFF | #1E1D33 | cards, rows, the top and tab bars on the phone |
| `--field` | #FFFFFF | #26253D | inputs, tick rings |
| `--ink` | #1A1838 | #F1F0FA | text |
| `--ink-2` | #45425F | #CAC7DE | secondary text, meta |
| `--ink-3` | #5C5875 | #A6A2BE | quiet text: hints, timestamps, weekday heads (still AA) |
| `--line` / `--line-2` | #E3E0EF / #CDC9E0 | #2C2A45 / #3B3858 | hairlines, decorative only |
| `--edge` | #7F7A9A | #857FA3 | **control edges**: buttons (with a 3.5 px bottom edge), inputs, selects, tick rings, choices (3:1) |
| `--accent` / `-2` / `-soft` / `-line` | #007A4D / #00603C / #DDF6E8 / #A9E3C4 | #5CE0A0 / #86EBBB / #12302A / #23573F | **"now"**: the today sticker, the next plan's leaf, the "Tomorrow" sticker, today's cell. `-2` is the lip under green stickers |
| `--today-bg` / `--on-today` | #007A4D / #FFF | #6DFF9C / #121122 | today's disc, the today sticker, the next plan's weekday band, "Tomorrow" |
| `--link` | #00704A | #5CE0A0 | links (never phosphor) |
| `--primary` / `-2` / `-lip` / `--on-primary` | #007A4D / #00603C / #004A2E / #FFF | #11704A / #0D6442 / #063D28 / #FFF | the one primary button per view, with its darker lip. Deeper at night so it never reads as Vera's phosphor |
| `--me` / `-soft` / `-ink` / `-mark` | the viewer's slot (`.p1…p8` values) | same, dark values | the current nav item (lip and icon disc), the current tab, the account card's lip, the page title's highlighter (`-mark` at 24 %), a kid's own wish ranks. Set from the signed-in person's slot; the mockups find it with `:has()` on the top bar's avatar, the engineer emits it from `page()` |
| `--vera` | #007A4D | #6DFF9C | Vera's name and green text. Phosphor at night |
| `--vera-bg` / `--on-vera` | #007A4D / #FFF | #4FE08A / #121122 | Vera tiles, the meter fill |
| `--vera-soft` / `--vera-line` | #DDF6E8 / #A9E3C4 | #11291F / #22513A | Vera's surfaces, her bubble's rim, the calm "Vera is ready" pill |
| `--ask-bg` / `--ask-ink` / `--ask-ink-2` | #15142A / #FFF / #CFCDE2 | #0B0A18 / #F1F0FA / #CAC7DE | the Ask Vera card: the brand's dark glass (indigo-black to sit on lilac), a command bar |
| `--ask-rim` / `--ask-edge` | faint white inset / none | 1.5 px #3E8A66 rim + faint glow / #857FA3 | the Ask card's edge and its box's edge at night |
| `--send` / `-2` / `-lip` / `--on-send` | #6DFF9C / #8DFFB2 / #2FB863 / #0E1312 | same | the Ask card's Send (a lit key with a green lip) and its focus ring |
| `--ok`, `-soft`, `-line` | #00703F, #DDF6E8, #A9E3C4 | #7FE8AE, #12302A, #23573F | Working, Connected, done, the ticked-off row, the flash sticker, the "Yes!" sticker |
| `--warn`, `-soft`, `-line` | #7A4E05, #FFF0CC, #EDCF7F | #F5B94A, #2C2414, #5E4620 | **only** "set this up" and "needs a look". The setup card is a white card with a 3 px amber top rule |
| `--alert`, `-soft`, `-line` | #C0321A, #FDE3DC, #F3B9AA | #FF8B74, #371A1F, #66302F | late text, broken, form errors. **Red means only late or broken** |
| `--focus` | #1A1838 | #F1F0FA | focus ring (lit green `--send` inside the Ask card, phosphor on glass) |
| `--p1…--p8` (+ `-soft`, `-ink`, `-mark`) | p1 #2257D6 blue · p2 #8A3CC9 violet · p3 #C22A79 raspberry · p4 #B54E00 orange · p5 #06778C teal · p6 #5443D6 indigo · p7 #5F7012 moss · p8 #7A4E30 cocoa | same bases; `-soft` a tinted indigo-charcoal, `-ink`/`-mark` lit (e.g. p3 soft #361A2C, mark #F5A3CD) | **person colour slots**, assigned per member by the server (`person.slot`), never by name. Calendar events: a 4 px bar in `--p-mark` and an 18 % tint of it. Person tiles at sign-in sit on a lip of their colour. The tick's burst uses all eight |
| `--everyone…` (`.p0`) | #5C5875, soft #EEECF6, mark #7F7A9A | #5E5A7C, soft #26253D, mark #A6A2BE | Everyone: always neutral |
| `--{person}-soft` / `--{person}-ink` | e.g. Maya #FDE4F0 / #B0236C | e.g. Maya #361A2C / #F5A3CD | chat bubbles, names in bubbles |
| **Brand** (§9) `--glass` / `--glass-2` / `--glass-line` | #0E1312 / #161D1B / #2A3632 | #070A09 / #0E1312 / #2B3B34 | the charcoal glass of the mark, Vera's screen, the pill and the panes |
| `--glass-ink` / `--glass-ink-2` | #E9F1EC / #B9C6BF | same | text on glass |
| `--phosphor` / `--phosphor-dim` / `--phosphor-glow` | #6DFF9C / 34 % / 50 % | same | lit things on glass |
| `--cursor` / `--cursor-glow` | #007A4D / 25 % | #6DFF9C / 55 % | the wordmark's cursor and the caret in Vera's box |
| `--vs-halo` | #007A4D at 30 % | #6DFF9C at 45 % | the 3 px halo round Vera's screen |

**Why green stays the accent.** Every other hue is a person's (eight slots), red is late and amber is "set this up". The only colour that belongs to no one is FamilyDB's own green. Fridge Door keeps it to "now" and action. "Where you are" moved to the viewer's own colour, so green means time, and colour means people.

**Why lilac.** Grey read as a default and cream read as a recipe site. A cool lilac with a dot grid reads as a planner page someone chose, sits behind every person's colour without fighting it, and turns into deep indigo at night.

**Maya's slot (p3) is raspberry, not red-pink**, so it never reads as "late". Slot 8 is cocoa. Eight colours can't all stay apart for every eye, so **colour is never the only cue**: every person marker carries an initial or the house.

**Person colours come from the family's data.** A real install gives each new person the next colour from a fixed set of eight. Each one is checked for 4.5:1 with white letters (5.2 to 7.1) and for its own `-soft`/`-ink` pair.

### Type

Two faces for the family: **Atkinson Hyperlegible for reading, Bricolage Grotesque for what you'd write big on the fridge** (headings, dates, clock times, money, counts, the wordmark). `type.html` shows every step live.

| Token | Size | Use |
|---|---|---|
| `--t-xs` | 13 px | **only** capitals (Bricolage 700–800, +0.08em): tab-bar labels (Atkinson), `.overline`, date-tile weekday and month, calendar weekday heads |
| `--t-sm` | 14 px | the floor: tags, badges, hints, names on messages; the mono on glass |
| `--t-meta` | 15 px | meta lines, small body |
| `--t-md` | 17 px | body (line height 1.5), row titles (700, 1.25), to-do titles on Home; the today sticker over Home's greeting (Bricolage 700) |
| — | 18 px | to-do titles on To do (700) |
| `--t-lede` | 18 px | the sentence under a page title (16 on phone) |
| `--t-h3` / `--t-h2` / `--t-h1` | 18 / 21 / 44 px (h1 36 on phone) | headings in Bricolage 700 (h1 800, −0.03em, with the viewer's highlighter; h2 −0.02em). Next up's title is 26 (23 on phone), 800; the month title on Plans 32 (24 on phone), 800; To do's group heads 18, 800 |
| — | 28 / 38 / 22 / 15 px | day number: date tile / Next up / small / month grid (Bricolage 800, tabular, −0.04em) |
| — | 32 / 32 px | money / Status figures (Bricolage 800, tabular, −0.03em) |
| `--t-display` | 48 px | the big money figure on Status |
| `--font-mono` | 14 px | JetBrains Mono 400: text on dark glass only (§9) |

- **Fonts** (`fonts/`, self-hosted, Latin): Atkinson Hyperlegible 400/700 for words. **Bricolage Grotesque** for the voice: `bricolage-var.woff2`, 69 KB, one variable file instanced to `wght` 500–800 and `opsz` 12–72, Latin, OFL in `fonts/bricolage-OFL.txt`. JetBrains Mono 400 for text on dark glass only. No other faces. Inter is gone.
- **Why Bricolage.** It is a modern grotesk with a hand in it. Big, its ink traps and wide round letters make "Good morning, Sam." feel said, not printed. Small, its optical sizes (set by the browser from the font size, `font-optical-sizing: auto`) open the letters so a 13 px weekday stays clear. Its open apertures match Atkinson's, so the two read as one family's handwriting and print, not two products. It still reads as software, not a bookish serif.
- **Figures.** `--font-num` is Bricolage with `--num-feat` (`tnum`). Use it where numbers stand alone or line up (`.num`, date tiles, the month grid, money, Status figures, wish ranks, setup step numbers, the meter scale, segment counts). **Every amount and clock time in running text** is `.fig` (added by one filter on the rendered page). It switches only digits and their punctuation to Bricolage (`"Bricolage Figures"`, the same file limited with `unicode-range`, `size-adjust` 102 %). It is proportional and follows the line's weight; 400 resolves to the file's 500, which matches Atkinson's colour. Other numbers in sentences ("3 to-dos") stay Atkinson.
- Avatar initials are Bricolage 800.
- `.code` switches back to Atkinson (with its slashed zero) for model names, keys and codes.
- **Sizes are in rem** (16 px = 1 rem). The only px type is inside drawings (the radar, the phone month's 9 px initials).
- Times follow the family's clock setting. The mockup uses the 12-hour clock with no leading zero ("9 am", "12:30 pm").

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48.
- Radius: soft, like die-cut stickers. `--r-sm` 6 (calendar events, tags), `--r-md` 12 (buttons, inputs, rows, banners, tiles, date tiles), `--r-lg` 18 (cards, the Ask card, the calendar, ranks). `--r-pill` for people (avatars), Vera's pill, starters, choices, segmented controls, badges, the today sticker. Round icon buttons and banner icons.
- **Edges: the lip.** Cards, boxed rows, to-dos, ranks, date tiles and the calendar sit on `--shadow` (`0 3px 0 var(--lip)`). Buttons and faces have a 3.5 px bottom edge that presses to 1.5 px on `:active`. The primary's lip is `--primary-lip`. Green stickers sit on `--accent-2`. Hovered whole-card links lift 2 px with `--shadow-lift`.
- **Kind shapes** (idea tiles, neutral `--paper-2`): food is a circle (plate); outing, seasonal and compass are an arch; trip, day trip and show are a ticket (notched with a mask); gift is a box with a ribbon cross; activity, event and games are a squircle tilted −6°. The mockups pick the shape from the icon with `:has()`; the engineer may emit `.tile--kind-food` and so on instead.
- Avatars: 24, 32, 40. Tiles: 40, 56.
- Every target is 44 px or more (`--target`). The tick is a 44 px hit area around a 32 px ring.
- Top bar 56 px; tab bar 68 px plus `env(safe-area-inset-bottom)`.

### Moments (CSS only, once, never under reduced motion)

| Moment | Where | What happens |
|---|---|---|
| Ticked off | `.todo--done`, `.tick--done` | the row turns `--ok-soft` with a green strike; the ring pops (scale .6 → 1, `--ease-pop`) and a burst of eight dots in the people's colours stays around it for this page view |
| After an action | `.flash.banner--ok` | the icon is a round green sticker at −10°, stuck on with a small bounce, with the same burst |
| Today | Home's date, `.day--today`, `.dt--now`, "Tomorrow" in `.next__tags` | the date is a green pill sticker at −2°; today's month number sits on a disc at −6°; the next plan's leaf is tilted −3° with a green band; "Tomorrow" is a green sticker |
| A wish said yes | `.tag--ok` on wish pages | a green "Yes!" sticker at −3° |
| A kid's own pages | kid pages (`--me`) | the current tab, highlighter and wish ranks in her colour; her top wish's rank is tilted |
| "Loved it" | `.face[value=loved]` | on hover it warms to the accent; faces tilt a little on hover |

The finished state is drawn without motion, so a reduced-motion or no-script reader sees the same celebration, still. Nothing moves longer than 0.6 s.

---

## 2. Components

Class names are the API. Person colour classes are **slots** (`.p0…p8`), never names: no `.av--sam`, `.msg--maya`, `.ev--theo`. Each component has one anatomy; variants are modifiers.

| Component | Classes | Variants | When to use |
|---|---|---|---|
| Card | `.card`, `.card__head`, `.card__foot` | `--setup` (3 px amber top rule) | every group of content |
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
| Date tile | `.dt` | `--now` (accent weekday band) `--lg` `--sm` | a plan's date, drawn as a calendar leaf: weekday band, day, month |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--boxed`, `--divided`, `--health` | every list of things that isn't a to-do or an idea card |
| To-do row | `.todos` › `.todo` | `--compact` (Home), `--late` (4 px red rule), `--done` (struck through after a tick), `--ro` (kids: read-only, icon tile instead of tick) | to-dos |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | marking a to-do done; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default **info (neutral card, grey icon)**, `--ok` (mint: all good, done), `--warn` (set this up), `--alert` (broken, errors); size: `--hero`, `--slim` | a message with at most one action. Resting, Off and “for your information” use the neutral default, never mint or yellow. **One “set this up” message per page** |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (charcoal glass, lit green Send); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page |
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
| Calendar | `.cal`, `.week`, `.day`, `.ev`, `.ev-more`, `.daylink`, `.dots` | `.ev--{person}`, `--past`; `.day--today`, `--we`, `--out` | the month view |
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
| `--ink` on `--paper` | body text | 15.1 | 16.5 |
| `--ink-2` on `--card` | secondary text | 9.6 | 10.0 |
| `--ink-3` on `--card` | quiet text, on card | 6.8 | 6.7 |
| `--ink-3` on `--paper` | quiet text, on paper | 6.0 | 7.6 |
| `--ink-3` on `--paper-2` | quiet text, sidebar | 5.4 | 7.1 |
| `--ink-3` on `--field` | placeholders | 6.8 | 6.0 |
| `--link` on `--card` | links | 6.1 | 9.9 |
| `--link` on `--paper` | links on paper | 5.4 | 11.2 |
| `--accent` on `--accent-soft` | "Tomorrow" in the list, accent tags | 4.7 | 8.5 |
| `--vera` on `--card` | Vera's name and green text | 5.4 | 12.9 |
| `--edge` on `--field` | field and tick edge (3:1) | 4.1 | 3.9 |
| `--edge` on `--card` | button and field edge, icon buttons (3:1) | 4.1 | 4.3 |
| `--edge` on `--paper` | buttons on the page (3:1) | 3.6 | 4.9 |
| `--on-primary` on `--primary` | primary button | 5.4 | 6.1 |
| `--primary` on `--paper` | primary button against the page (3:1) | 4.8 | 3.0 |
| `--on-today` on `--today-bg` | today disc, today sticker, next plan band, "Tomorrow" sticker | 5.4 | 14.6 |
| `--today-bg` on `--card` | today disc and line (3:1) | 5.4 | 12.9 |
| `--on-send` on `--send` | Send on Ask | 14.7 | 15.3 |
| `--ask-ink` on `--ask-bg` | Ask card text | 18.0 | 17.4 |
| `--ask-ink-2` on `--ask-bg` | Ask card quiet text | 11.6 | 11.9 |
| `--ok` on `--ok-soft` | tag Working | 5.4 | 9.5 |
| `--card` on `--ok` | "Yes!" sticker, flash sticker tick | 6.2 | 11.0 |
| `--warn` on `--warn-soft` | tag Needs a look | 6.4 | 8.7 |
| `--warn` on `--card` | tag Could be better, setup step numbers | 7.2 | 9.3 |
| `--alert` on `--alert-soft` | tag Not working, late badge | 4.6 | 6.9 |
| `--alert` on `--card` | late text, errors | 5.7 | 7.2 |
| `--ink-2` on `--paper-2` | tag Off | 7.6 | 10.6 |
| `--vera` on `--vera-soft` | the calm "Vera is ready" pill | 4.7 | 12.1 |
| `--p1-ink` on `--p1-soft` | slot 1 name in a bubble; Sam's current tab | 5.9 | 7.7 |
| `--p3-ink` on `--p3-soft` | Maya's name in a bubble; her current tab | 5.3 | 8.2 |
| `--p4-ink` on `--p4-soft` | Theo's name in a bubble | 5.4 | 8.7 |
| `--ink` on `--p3-soft` | text in Maya's bubble | 14.2 | 13.9 |
| `--everyone-mark` on `--card` | Everyone's dot (3:1) | 4.1 | 6.7 |
| `--paper` on `--ink` | selected segment, picked choice | 15.1 | 16.5 |
| `--cursor` on `--paper` | wordmark cursor (3:1, non-text) | 4.8 | 14.6 |
| `--ink` on the title highlighter (`--me-mark` 24 % on paper, every slot) | page titles | 10.5 min | 9.2 min |
| `--phosphor` on `--glass` | phosphor on glass: pill, pane lines, focus ring | 14.7 | 15.6 |
| `--glass-ink` on `--glass` | pane text | 16.3 | 17.3 |
| `--glass-ink-2` on `--glass` | pane quiet text, resting pill | 10.6 | 11.3 |
| `--glass-alert` on `--glass` | "can't answer" pill | 8.2 | 8.7 |
| `--ask-edge` on `--ask-bg` | the Ask box's edge at night (3:1) | n/a | 5.2 |
| Ask rim #3E8A66 on `--paper` | the Ask card's edge at night (3:1) | n/a | 4.5 |
| white on `--p1` … `--p8` | avatar letters, calendar initials, nav icon disc, a kid's rank stickers | 6.2 / 5.9 / 5.4 / 5.2 / 5.2 / 6.7 / 5.5 / 7.1 | same |
| white on `--everyone` | Everyone's avatar | 6.8 | 6.5 |
| `--p1…8-mark` on `--card` | dots, event bars (3:1) | 5.2–7.1 | 7.8–10.8 |
| `--ink` on an event fill (mark 18 % on card) | calendar event text | 12.9–13.3 | 9.4–10.1 |

The glass pane has no contrast duty of its own in the dark (it is #070A09 on #121122): its 1 px `--glass-line` rim and the phosphor inside carry it. **Focus on glass is phosphor** (`.pane`, `.instrument__pane`, `.pill-health` set `--focus: var(--phosphor)`, 14.7:1), because the ink ring is 1.2:1 there.

Disabled controls are exempt, but each also carries its reason in words.

**Checklist for every page**
- One `h1`; headings in order. Chat on the phone keeps its `h1` visually hidden, not `display:none`.
- A visible "Skip to content" link on first Tab. A 3 px focus ring on everything (lit green on the Ask card). Whole-card links show focus with `:focus-within`.
- No meaning by colour alone: late says "6 days late", tags carry words, calendar events carry a spoken label, badges carry words.
- Every control is named: ticks "Mark done: …", faces "Loved it (Silver Falls hike)", move buttons "Move Ice skates up", Edit "Edit Call the dentist about Theo".
- Form fields have labels; errors are tied with `aria-describedby` and `aria-invalid`; the summary has `role="alert"`; flashes have `role="status"`.
- Chat thread: `role="log"`, focusable (`tabindex="0"`), named.
- Targets are 44 px; type is 14 px or more (13 px only on tab labels and overlines), set in rem; the top and tab bars use `min-height`.
- **Nothing blinks for more than five seconds** (2.2.2): the wordmark cursor blinks twice and stays lit, the pill's dot breathes once. Only things that end on their own move longer: Vera's busy screen and the typing dots, while a reply is on its way.
- `prefers-reduced-motion`: nothing moves at all. The moments (§1) show their finished state, still: the tick's burst, the tilted stickers. Buttons don't press and cards don't lift.
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

Fridge Door is the family's calendar and fridge: a lilac planner page, a grotesk with a hand in it, people in their own felt-tip colours, stickers when things get done. FamilyDB is the small machine that runs it. The brand is that pairing, used a little: **a pane of dark glass with green light, stuck on the family's door.** It is a sprinkle. The layout, the components and every check in §7 are unchanged by it.

### The brand rule

**The lilac page, the stickers, the people's colours and the accent are the family's. Phosphor on charcoal glass is FamilyDB's and Vera's.** Glass and phosphor appear only where one of three things is:

1. **the brand**: the mark, the wordmark, and the brand moments (sign-in, a family's first empty day, the grown-ups page a kid lands on, the missing page);
2. **Vera**: her screen, the Ask card (charcoal glass with a lit Send, day and night);
3. **something live**: the status pill when it has something to say (writing back, resting, can't answer), a reply on its way, the cursor in her box, today's date (the accent sticker by day, a phosphor-green sticker at night). When Vera is simply ready the pill is calm and on the page.

Never on the family's own things: names, ideas, to-dos, wishes, plans, and the buttons and links that act on them (those use `--link` and `--primary`: the accent green by day; at night a lighter green for links and a deeper one for the primary button, never phosphor). **Mono only on the glass**: nothing printed on the page is in the mono. Every touch says something true; nothing is only ornament. No dark page in light mode, no CRT curvature, no vignettes, no heavy scanlines, no pixel font.

### The mark

A little monitor with a smile, drawn in one 2 px round-capped stroke (24-unit grid), phosphor `#6DFF9C` on a charcoal `#0E1312` rounded square (radius 8 on 32). Unchanged from Kitchen Table. On the lilac page it reads as an app icon, or a magnet on the fridge. It is FamilyDB's, **never Vera's face**, and never stands in for her.

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
- **On the page:** the charcoal square is the mark's own glass, so it sits directly on lilac or white; no extra frame, lip or shadow (the lip is for the family's things).
- **On dark:** the same file. At night the square is close to the page, so it keeps its own edge from the stroke; nothing is inverted. Never recolour the stroke (no white, no accent green), and never use it without its square.
- Head tags: `favicon.svg` (`image/svg+xml`), `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png` (180). The 512 is for the web manifest.

### The wordmark

"FamilyDB" in **Bricolage Grotesque 800**, letter-spacing −0.03em, followed by a **lit cursor**: a block `.42em × .86em`, 0.14em after the B, radius 1.5 px. The family's voice for the name, the machine's cursor after it: the brand's pairing in one word.

- Sizes: 22 px in the sidebar, 20 px in the phone bar, 18 px inside a pane. It is always beside the mark; the link around both is named "FamilyDB, home".
- **On the page:** ink letters, cursor `--cursor` (the accent, 4.8:1 on the page) with a faint glow.
- **On dark and on glass:** white or glass-ink letters, cursor `--phosphor` with `--phosphor-glow`.
- The cursor blinks twice (2 s each, mostly on), then stays lit: no blinking past five seconds (WCAG 2.2.2). Under `prefers-reduced-motion` it never blinks. The cursor is `aria-hidden`.

### Vera's screen

Vera is never drawn. Where she speaks there is a small pane of glass, as if she were typing: a **rounded square** (never round: round means a person), a **lit rim**, a few short **lines of light**, and her **signature, a lit prompt `>▮`** in the bottom-left corner. Unchanged by Fridge Door: Vera stays the one crisp, machine-made thing on a page of stickers, which is how you can tell her from the family. It is drawn as inline SVG, crisp, with no blur and no scanlines, so it reads at 24 px on a phone.

| Size | Class | Lines | Where |
|---|---|---|---|
| 24 px | `.vs--sm` | 1 | Settings colour key, "Suggested by Vera" rows |
| 32 px | `.vs` | 2 | chat messages (her avatar slot), the pending and failed bubbles |
| 40 px | `.vs--lg` | 3 | the Ask card, Home's Vera row, Status' Vera row |
| 56 px | `.vs--xl` | 3, larger | the kid's empty chat (the one place she is introduced) |

Geometry (per size, in px): radius 6 / 8 / 10 / 14; rim 1 px inside the edge; lines 3 px tall (4 at 56), rounded; prompt stroke 1.75 / 2 / 2.25 / 3. The macro `vera_screen(size, state)` holds the table.

| State | Class | Looks like |
|---|---|---|
| Ready | `.vs` | rim at 60 %, lines at 45 % with the newest at 90 %, the prompt and cursor fully lit, a soft halo (`--vs-halo`) |
| Answering | `.vs--busy` | the lines light one after another and the cursor blinks, only while a reply is on its way |
| Can't answer | `.vs--off` | the light goes out: rim, lines and prompt turn `--edge` grey, the cursor is hollow, no halo. Visible on the page and on charcoal. The words beside it say why |

- The whole screen is `aria-hidden`; Vera's name is always in text next to it.
- **Motion:** only `--busy` moves (it stops when the reply lands), and nothing moves under `prefers-reduced-motion`.
- Halo: `--vs-halo` is a 3 px drop shadow, the accent green by day and phosphor at night.

### The mono: only on the glass

JetBrains Mono 400, self-hosted (`fonts/jetbrains-mono-400.woff2`, 21 KB), 14 px. **Only on dark glass:** the status pill when it has something to say and the lines inside a pane ("404 · nothing at this address"). The radar is glass but its labels are Atkinson, because kids read them. Never on the page: Vera's message times, her receipts and everything the family reads are Atkinson, with money and clock times in Bricolage (§1 Type). Numbers and units are kept together with no-break spaces.

### Phosphor elements, their tokens, where they may and may not appear

| Element | Tokens | May appear | May not |
|---|---|---|---|
| The mark | `--glass` (fixed #0E1312 in the file), `--phosphor` | bar, sidebar, sign-in, panes, favicon, icons, Settings' key | as Vera; inside a message; on the family's items |
| Wordmark cursor | `--cursor`, `--cursor-glow` (dark: `--phosphor`) | after "FamilyDB" only; the caret in Vera's box (`caret-color`) | anywhere else as decoration |
| Vera's screen | `--glass`, `--glass-line`, `--phosphor`, `--vs-halo` | wherever Vera is | for a person; as a decoration with no Vera |
| Status pill (when there's something to notice) | `--glass`, `--glass-line`, `--phosphor`, `--phosphor-glow`, `--glass-alert` | sidebar and phone bar, parents only. When Vera is ready the pill is not glass at all: `--vera-soft`, `--vera`, Atkinson 700, a still dot | kids' pages; anywhere it isn't Vera's real state |
| Glass pane | `--glass`, `--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--phosphor` | the four brand moments. Faint scanlines inside are fine | as a card style; around the family's content; more than one per page |
| The radar | `--glass`, `--phosphor` at 14–25 % for rings and axes, `--glass-ink` and `--glass-ink-2` for labels | Ideas only, in its own band after all the cards (folded behind "Show the map" on the phone). Geometry and labels as before | between the cards; any second page; mono labels |
| Ask card glass | `--ask-bg`, `--ask-rim`, `--ask-edge`, `--send` | Home's and the kid's Ask card: charcoal glass, a white box and a lit green Send; at night a 1.5 px green rim, a faint inner glow and a real edge on its box | anywhere else |
| Live glow | `--phosphor-glow`, `--vs-halo` | the writing-back pill, the panes, Vera's screen, the wordmark cursor | the calm "ready" pill, chat bubbles, cards, buttons |

The radar is drawn twice from the same data: a wide 860 × 440 plot for the desktop (names 15 px) and a narrow 360 × 400 plot for the phone (names 14 px). Ring and compass labels are 13 px Atkinson.

### Brand moments

- **Sign-in:** a pane with the mark, the wordmark and "awake, Saturday 3 October", then "Who's using FamilyDB?" and the people on the page.
- **A first empty day** (`states-content.html`): "FamilyDB is set up and awake. Welcome, Sam. This is your family's table." on glass, then the empty cards.
- **The grown-ups page** (`grownups.html`): the mark alone at 64 px, glowing, above the explanation; the explanation stays on a card.
- **The missing page** (`404.html`): a centred pane, the mark, "404 · nothing at this address" in the mono, then "This page isn't here", Go to Home and Ask Vera to find it.

### The dark theme: the kitchen lights down

At night the page is deep indigo with a darker dot grid (`--paper` #121122, `--card` #1E1D33, lips nearly black), the ink is near-white (#F1F0FA), today and Vera's things are phosphor (`--today-bg`, `--vera` #6DFF9C; the today sticker turns phosphor with indigo letters), links a lighter accent (#5CE0A0), amber (`--warn` #F5B94A) is for what needs a look, coral (`--alert` #FF8B74) for late and broken, and people keep their colours, lit (`-ink`, `-mark`) on tinted indigo (`-soft`). The viewer's highlighter and tab follow.

**The hierarchy holds at night.** The Ask card stays the one dark-glass block, with the brightest edge on the page and an edged box. The primary button is a deeper green (#11704A, white text 6.1:1, 3.0:1 against the page, with its lip) so it never reads as Vera's lit Send. Vera's bubbles have no glow; only the pill, the panes and her screen glow. Every pair is in §7.
