# FamilyDB · Kitchen Table · the standard

This is the reference for building FamilyDB's web pages. The mockups (`*.html`), `style.css`, `icons.svg` and `fonts/` in this folder are the source of truth. This document says how to use them.

**The rule behind everything:** one plain sentence first, cards below it, and a person's colour wherever that person appears. Every status is a sentence, not a code. Saturated colour means *a person* (or Vera's green), and red means *late or broken*.

---

## 1. Tokens

All values live on `:root` in `style.css` §2. Dark mode redefines the same names under `@media (prefers-color-scheme: dark)`. Never write a hex value outside `:root`.

### Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | #F6F1E7 | #181713 | page background |
| `--paper-2` | #EFE7D7 | #211F1A | sidebar, tracks, neutral tiles, "Off" tags |
| `--card` | #FFFCF6 | #24221D | cards, rows |
| `--field` | #FFFFFF | #2B2923 | inputs, tick rings |
| `--ink` | #1D2526 | #F1EBDD | text |
| `--ink-2` | #4B5657 | #D2CAB9 | secondary text, meta |
| `--ink-3` | #596263 | #ADA594 | quiet text: hints, timestamps (still AA) |
| `--line` / `--line-2` | #E2D8C4 / #D3C6AC | #38342C / #4A4539 | decorative borders only |
| `--edge` | #8A806C | #8F8771 | **control edges**: inputs, selects, tick rings, choice pills (3:1) |
| `--vera` | #1E5C4F | #7CC7AE | Vera's green as text and icons, links |
| `--vera-bg` / `--on-vera` | #1E5C4F / #FFF | #2D7462 / #FFF | primary buttons, Vera's mark, today |
| `--vera-soft` / `--vera-line` | #DCEAE2 / #B9D3C6 | #1E332D / #2F5047 | Vera's surfaces, info banners |
| `--ask-bg` / `--ask-ink` / `--ask-ink-2` | #1E5C4F / #FFF / #D7E7DF | #1D4239 / #F4EFE3 / #C7D9D0 | the Ask Vera card |
| `--sun` / `--on-sun` | #F2C14E / #1D2526 | #EDBD52 / #1D2526 | the Ask card's Send only |
| `--ok`, `-soft`, `-line` | #2B7148, #DDEFE2, #BFDCC8 | #86CFA0, #1D3125, #2E4B38 | Working, Connected, done |
| `--warn`, `-soft`, `-line` | #7E5108, #FBEFD0, #EBD69B | #F0C873, #362B17, #574522 | set this up, needs a look, resting |
| `--alert`, `-soft`, `-line` | #B3381F, #F9E1D9, #EFC3B6 | #FF9277, #3C221B, #5E3328 | late text, broken, form errors |
| `--focus` | #1D2526 | #F1EBDD | focus ring (yellow `--sun` inside the Ask card) |
| `--sam` `--alex` `--maya` `--theo` `--everyone` | #2F5D9B #7B4790 #B03F66 #A2560E #596263 | same (everyone #6B7374) | avatars, a person's calendar event bar |
| `--{person}-soft` / `--{person}-ink` | e.g. Maya #F8E3EA / #A63B60 | e.g. Maya #35212A / #F2A3BE | chat bubbles, event fills, names in bubbles |

**Person colours come from the family's data.** The five above are the mockup family. A real install assigns each new person the next colour from a fixed set of eight. Each colour is checked for 4.5:1 with white letters and for its own `-soft`/`-ink` pair.

### Type

| Token | Size | Use |
|---|---|---|
| `--t-xs` | 13 px | **only** tab-bar labels and `.overline` (sidebar group label, date-tile weekday) |
| `--t-sm` | 14 px | the floor: tags, badges, hints, timestamps |
| `--t-meta` | 15 px | meta lines, small body |
| `--t-md` | 17 px | body, row titles |
| `--t-lede` | 19 px | the sentence under a page title (17 on phone) |
| `--t-h3` / `--t-h2` / `--t-h1` | 20 / 24 / 40 px (h1 30 on phone) | headings in Fraunces 600 |
| `--t-display` | 44 px | money on Status |

- **Fonts** (`fonts/`, self-hosted, Latin): Atkinson Hyperlegible 400/700 for words; Fraunces 600 (variable optical size) for headings.
- **Fraunces Figures** 400/600: a FamilyDB-built subset of Fraunces with *tabular, lining* digits and `$ % . , : – - / +` only. It is listed first in both stacks, so **every number renders in Fraunces and every word falls through to Atkinson**, with no markup. The source script is described in CHANGES.md (fontTools: instance at opsz 18, set every digit's advance to the zero's width, centre the glyphs).
- `.code` switches back to Atkinson (with its slashed zero) for model names, keys and codes.
- Times follow the family's clock setting; the mockup uses the 12-hour clock with no leading zero ("9 am", "12:30 pm").

### Space, radius, size

- Spacing `--s1…--s8`: 4, 8, 12, 16, 20, 24, 32, 48.
- Radius: `--r-sm` 8 (calendar events), `--r-md` 12 (inputs, rows, banners, tiles), `--r-lg` 18 (cards, the Ask card), `--r-pill`.
- Avatars: 24, 32, 40. Tiles: 40, 56.
- Every target is 44 px or more (`--target`). The tick is a 44 px hit area around a 32 px ring.
- Top bar 56 px; tab bar 68 px plus `env(safe-area-inset-bottom)`.

---

## 2. Components

Class names are the API. Each component has one anatomy; variants are modifiers.

| Component | Classes | Variants | When to use |
|---|---|---|---|
| Card | `.card`, `.card__head`, `.card__foot` | `--setup` (sun-tinted) | every group of content |
| Button | `.btn` | `--primary` (one per view), `--quiet`, `--sm`, `[disabled]` | actions; links styled as buttons only for navigation actions |
| Text button | `.textbtn`, `.linkbtn`, `.more` | — | a form action that reads like a link (Delete, Take it off my list); "All plans ›" |
| Badge | `.badge` | `--late`, `--look`, `--soft` | nav and card counts, **only for things that need someone** ("3 late", "2 to rate", "1 to decide", "1 to check"); always with a word |
| State tag | `.tag` | `--ok` Working/Connected/Added · `--better` Could be better/Not connected · `--look` Needs a look · `--broken` Not working · `--off` Off/Optional/No backup · `--when` Tomorrow/Planned · `--been` Went… · `--surprise` | how a thing stands; one tag per thing, words from §3 |
| Health pill | `.pill-health` | `--rest`, `--down` | Vera's state, in the sidebar and phone top bar; parents and admins only |
| Avatar | `.av` + `.av--{person}` | `--sm` `--lg` | every mention of a person; Everyone uses the house icon |
| Vera's mark | `.mark` | `--sm` `--lg` | Vera, wherever she speaks; her initial from the persona's name; **never a face or figure** |
| Tile | `.tile` | `--lg`, `--ok` `--better` `--look` `--broken` `--vera` | leading icon for an idea kind (neutral) or a health area (tone) |
| Date tile | `.dt` | `--now` `--lg` `--sm` | a plan's date |
| Meta line | `.meta` (+ `.late`) | — | owner · due · reminder · drive under a title |
| Item row | `.items` › `.item` (lead · body · trail) | `--boxed`, `--divided`, `--health` | every list of things that isn't a to-do or an idea card |
| To-do row | `.todos` › `.todo` | `--compact` (Home), `--late` (4 px red rule), `--done` (struck through after a tick), `--ro` (kids: read-only, icon tile instead of tick) | to-dos |
| Tick | `.tick` (a `<button>` in its own POST form) | `--done` | marking a to-do done; never for kids |
| Banner | `.banner` + `.banner__ic`, `.banner__text` | tone: default info, `--ok`, `--warn`, `--alert`; size: `--hero`, `--slim` | a message with at most one action. **Tone rule:** not set up yet → warn; broken or blocking → alert; for your information → info; all good / done → ok |
| Flash | `.banner.banner--ok.flash` (`role="status"`, `tabindex="-1"`) | — | after any one-tap action, with Undo |
| Error summary | `.banner.banner--alert.errors` (`role="alert"`) | — | top of a form that came back with errors |
| Composer | `.composer`, `__row`, `__who`, `__foot`, `__send` | inside `.ask` (dark green, sun Send); `--sample`; closed (`textarea[disabled]` + a slim banner saying why) | writing to Vera; one per page |
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
| Settings row | `.slist` › `.srow` | `--look` | lists of sections or destinations (Settings, More) |
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
| plan status | **Tomorrow · Planned · Went Thu 1 Oct** | Scheduled, Completed |
| wish answers | **Yes! · Thinking about it · Not this time · Not decided yet** | Approved, Denied, Pending |
| something kept from kids | **Surprise · hidden from Maya** | private, secret |
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
| Phone tabs | Home, Chat, Plans, To do, More | same | Home, Chat, Wishes, To do, More |
| Health pill, cost, models, setup | yes | pill and cost; no setup | **never** |
| To-dos | all; tick, add, edit | all; tick, add, edit | **only her own, read-only**; "Sam or Alex tick these off"; she can tell Vera she's done |
| Ideas, plans | change; rate plans | change; rate plans | read only; no faces, no Add, no Edit; "Ask a parent" where a change is expected |
| Wishes | decide | decide | add, rank, take off; sees answers in words |
| Chat | family chat + reads kids' chats | same | own chat + family chat, within her daily message count |
| Gifts | shown, tagged "Surprise · hidden from …" | same | **left out entirely** (no row, no count, no greyed item) |

Whether a kid may tick her own to-dos or rate a plan is a *family* decision. The app currently says no. If the family allows it later, the kid's to-do row becomes the normal `.todo` with a tick, and `.faces` appear on her Home. No new component is needed.

A kid who opens an admin URL gets `grownups.html`, never an error.

---

## 5. Phone rules (≤ 820 px)

1. **The phone is its own layout, not the desktop stacked.** The sidebar becomes a 56 px top bar (brand, health pill for parents, avatar) and a **fixed bottom tab bar** of five, role-aware. Badges sit on the tab: a late count on To do, and a dot on More when something inside needs checking.
2. **The list you came for is in the first screen.** Quick-adds are one line; options, filters and sorting fold into `<details>`. Order: heading, lede, the list, then the tools.
3. Ideas become compact rows: tile, title, "who · drive", tags underneath.
4. **Plans open on the list.** The month grid becomes a month at a glance: day cells are whole-cell links with dots and a full spoken label. Weekday headers are single letters.
5. Settings and More rows use grid areas: icon | text, tag | chevron. The chevron never wraps.
6. The Status model table folds away and stacks; actions sit under their line.
7. **Chat is an app-height room**: pills, the privacy line, a scroller that opens at the newest message (column-reverse), the box pinned above the tab bar, and a pinned "Earlier messages" bar with a fade at the top edge.
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
| No results | Ideas, To do | "Nothing matches "pizza" for Theo", every active filter in words, **Clear search and filters**, and "Save "pizza" as a thought" |
| Busy day | calendar | two events, then "+N more" (links to that day in the list); the phone shows up to three dots |
| Long titles | everywhere | wrap in full; only calendar events clamp to two lines (full title in the spoken label and on the plan page) |

---

## 7. Accessibility checks

Contrast is computed from the tokens (WCAG 2.2). AA needs 4.5:1 for text and 3:1 for control edges.

| Pair | Use | Light | Dark |
|---|---|---:|---:|
| `--ink` on `--paper` | body text | 13.9 | 15.1 |
| `--ink-2` on `--card` | secondary text | 7.4 | 9.8 |
| `--ink-3` on `--card` | quiet text, on card | 6.1 | 6.5 |
| `--ink-3` on `--paper` | quiet text, on paper | 5.6 | 7.3 |
| `--ink-3` on `--paper-2` | quiet text, sidebar | 5.1 | 6.7 |
| `--vera` on `--card` | links | 7.6 | 8.0 |
| `--vera` on `--paper` | links on paper | 6.9 | 9.1 |
| `--edge` on `--field` | field and tick edge (3:1) | 3.9 | 4.1 |
| `--edge` on `--card` | field edge on card (3:1) | 3.8 | 4.4 |
| `--on-vera` on `--vera-bg` | primary button | 7.8 | 5.5 |
| `--on-sun` on `--sun` | Send on Ask | 9.3 | 8.9 |
| `--ask-ink` on `--ask-bg` | Ask card text | 7.8 | 9.7 |
| `--ask-ink-2` on `--ask-bg` | Ask card quiet text | 6.1 | 7.5 |
| `--ok` on `--ok-soft` | tag Working | 4.9 | 7.5 |
| `--warn` on `--warn-soft` | tag Needs a look | 6.0 | 8.7 |
| `--warn` on `--card` | tag Could be better | 6.7 | 10.0 |
| `--alert` on `--alert-soft` | tag Not working, late badge | 4.8 | 6.7 |
| `--alert` on `--card` | late text, errors | 5.9 | 7.3 |
| `--ink-2` on `--paper-2` | tag Off | 6.2 | 10.1 |
| `--vera` on `--vera-soft` | tag Tomorrow | 6.3 | 6.8 |
| `--sam-ink` on `--sam-soft` | Sam's name in a bubble | 5.5 | 7.4 |
| `--alex-ink` on `--alex-soft` | Alex's name in a bubble | 5.5 | 7.6 |
| `--maya-ink` on `--maya-soft` | Maya's name in a bubble | 5.0 | 7.7 |
| `--theo-ink` on `--theo-soft` | Theo's name in a bubble | 5.1 | 8.1 |
| `--ink` on `--maya-soft` | text in Maya's bubble | 12.8 | 12.6 |
| white on `--sam` / `--alex` / `--maya` / `--theo` | avatar letters | 6.6 / 6.7 / 5.6 / 5.4 | same |
| white on `--everyone` | Everyone's avatar | 6.3 | 4.9 |

Disabled controls are exempt, but each also carries its reason in words.

**Checklist for every page**
- One `h1`; headings in order. Chat on the phone keeps its `h1` visually hidden, not `display:none`.
- A visible "Skip to content" link on first Tab. A 3 px focus ring on everything (sun-yellow on the Ask card). Whole-card links show focus with `:focus-within`.
- No meaning by colour alone: late says "6 days late", tags carry words, calendar events carry a spoken label, badges carry words.
- Every control is named: ticks "Mark done: …", faces "Loved it (Silver Falls hike)", move buttons "Move Ice skates up", Edit "Edit Call the dentist about Theo".
- Form fields have labels; errors are tied with `aria-describedby` and `aria-invalid`; the summary has `role="alert"`; flashes have `role="status"`.
- Chat thread: `role="log"`, focusable (`tabindex="0"`), named.
- Targets are 44 px; type is 14 px or more (13 px only on tab labels and overlines).
- `prefers-reduced-motion`: the typing dots don't move. `forced-colors`: selected nav, tabs, segments, conversation pills, choices, person tiles, tags and today get real borders.
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
- `page(role, current)` wraps the shell: sidebar or top bar, role-aware nav and tabs, skip link, sprite.
- Then `card`, `banner(tone, size)`, `tag(state)`, `badge(kind, n, word)`, `avatar(person, size)`, `mark(size)`, `item`, `todo(todo, viewer)` (picks `--late`, `--done` or `--ro` from the viewer's role), `composer(viewer, state)`, `starters(list)`, `field(...)`, `choices(name, options, required)`, `rank(wish, viewer)`, `idea_card`, `calendar_week`, `empty(title, text, action)`, `flash(message, undo_url)`, `error_summary(errors)`.
- `health(area)` returns one `(state, words, action)` per area: Vera, Spending, Sign-in, Backup, Telegram, Google Calendar, Looking things up. **Every page reads it** (pill, Home, Status, Settings, Ideas banner), so they can't disagree. Settings summary lines are computed, never written as copy.
- `visible_to(viewer)` filters every list for kids: own to-dos only, gifts and surprises removed. Counts are taken *after* filtering.

**Works with scripting off (required)**
- Reading every page, and every form: tick, Undo, add, edit, rate (faces), answer a wish, move a wish up or down, sign in, search and filter (GET), send a message.
- Pattern: POST → redirect → GET (PRG), with a flash in the session and `#anchor` to the changed list. Every form carries a CSRF token.
- Starters: a complete question is `<button name="prompt" value="…">` in its own form; a stem is `<a href="?draft=…#ask-text">`, and the server renders the draft into the textarea with `autofocus`.
- Chat opens at the newest message without script (`.scroller` is `flex-direction: column-reverse` around one `.thread`). The server sends the latest 30 messages; "Earlier messages" is `?before=<id>`; the last message has `id="latest"`.
- **While a reply is pending**, the page includes `<meta http-equiv="refresh" content="3">` (CSP doesn't block it) and the box is `disabled`. Remove the meta tag as soon as Vera has answered. After 60 s with no reply, mark the message failed.
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
- Plans know who they're for (one person → that person's colour; several or Everyone → neutral with avatars).
- Kids have a daily message count.
