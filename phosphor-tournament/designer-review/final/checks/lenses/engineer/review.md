# FamilyDB final design: build review (front-end engineering lens)

Source read: `final/source/` (the brief mentions `a1/source/`, which isn't in this folder). I read all of `style.css` (887 lines) and `STANDARD.md`, scanned all 20 HTML pages, looked at all four overviews, and opened the full-length desktop Chat, Status and states-content pages and the phone Chat and states-content pages. I couldn't render anything in a browser here, so widths and overflow below are worked out from the CSS rules, not measured.

## Verdict
**7.5 / 10.** The source is unusually ready for Flask and Jinja. No page has a `style=""`, an inline `<script>` or an `on*=` handler. Every action is a plain GET or POST form, the chat opens at the newest message with no script, and the standard already lists the macros, the CSP header and the PRG pattern. It loses marks for a handful of structural problems that would be built straight into the templates: person colours are tied to the mockup family's names, Ideas has two copies of one form control, the tab bar ignores the iPhone home-indicator area, and the desktop chat grows without limit.

**Optimise before building?** Yes. The person-colour classes (`.av--sam`, `.msg--maya`, `.ev--theo`…) can't describe a real family without inline styles, and every page uses them, so they must change in `style.css` before any template is written.

## Protect
1. **CSP-clean markup on all 20 pages.** There are no `style=""`, inline scripts or `on*=` attributes, and the spend meter on Status draws its data with SVG attributes (`<rect width>`, `<line x1>`) instead of styles.
2. **The Chat scroller** (`chat.html` `.scroller`, `flex-direction: column-reverse`, `role="log"`). It opens at the newest message with scripting off, and "Earlier messages" is a plain `?before=` link.
3. **Every action is a form**: the To do tick is a `<button>` in its own POST form, search and filters on Ideas and To do are GET with `role="search"`, and filters fold into `<details>` (`.disclose`). This works with scripting off and fits PRG plus flash messages directly.
4. **Tokens on `:root`, with dark mode only redefining them** (`style.css` §2). The dark overview needed no per-component rules, so the theme stays cheap to maintain.
5. **`minmax(0, 1fr)` and `min-width: 0` on every grid track.** Long titles wrap in full and the tick, chevron and Edit stay put (states-content "Long titles": idea card and to-do row, desktop and phone).
6. **The calendar is placed with classes, not geometry** (`.c1…c7`, `.lane1…3`, `+N more`). On the phone each day cell is one `.daylink` with a full spoken label (`plans.html`), so the server can render it with no script and no inline style.

## Fix, ranked

**1. Person colours are hard-coded to the mockup family** (`style.css` `--sam/--alex/--maya/--theo` tokens, `.av--sam`, `.msg--sam`, `.ev--sam`, `.dots i.d-maya`; every page)
- Problem: STANDARD §1 says each real person gets "the next colour from a fixed set of eight", but the CSS can only colour people named Sam, Alex, Maya and Theo. With inline styles banned, a template has no way to colour "Jordan". The phone calendar dots already show the gap: only `.d-maya` has a colour, and Plans renders the other people's dots as `<i class="">` (grey). Every page with an avatar, bubble, event or dot is affected.
- Fix: replace the names with slot classes `.p1…p8`. Each slot sets `--p`, `--p-soft` and `--p-ink` (light and dark), and the components read those variables: `.av { background: var(--p) }`, `.msg { --m-bg: var(--p-soft); --m-ink: var(--p-ink) }`, `.ev { --e-bg: var(--p-soft); --e-bar: var(--p) }`, `.dots i { background: var(--p) }`. Store the slot on the person row, and have `avatar(person)` emit `av p{{ person.slot }}`. Keep `--everyone` as its own slot.
- Severity: **blocker**. Effort: **M**.

**2. Two sort controls on Ideas, and both are submitted** (`ideas.html` line 75 `select name="sort" class="desk-only"` and line 83 `select name="sort2" class="field phone-only"`)
- Problem: `display: none` doesn't stop a control from being submitted, so every search sends both `sort` and `sort2`. The server can't tell which one the person changed. On a phone, picking "Nearest first" arrives next to a hidden `sort=Newest first`. A tablet rotated across 820 px swaps which one is visible.
- Fix: keep one `<select name="sort">` and move it with CSS (put it in the `.finder` grid on desktop; at ≤820 px place it inside the disclosure body using grid areas, or simply leave it in the disclosure at every width). Add a rule to the standard: never duplicate a form control per breakpoint. While in there, the mockup's `<option>`s have no `value` attributes; the macro must emit values and `selected`.
- Severity: **major**. Effort: **S**.

**3. The phone tab bar eats the iPhone home-indicator inset** (`style.css` line 738 `.tabbar`, line 744 `body`, line 861 `.chat`)
- Problem: `.tabbar` has `height: 68px` with `box-sizing: border-box` and `padding-bottom: calc(6px + env(safe-area-inset-bottom))`. On an iPhone with a 34 px inset (and `viewport-fit=cover` is set on every page), the content box shrinks to about 22 px for a 24 px icon plus a 13 px label, so the tabs clip or overflow. `body { padding-bottom: 68px }` and the chat height `100dvh - 56 - 68` also ignore the inset, so the bottom of every list, and the chat box's "Share where I am" line, sit under the bar.
- Fix: add `--tabbar-total: calc(var(--tabbar-h) + env(safe-area-inset-bottom, 0px))`, and use it for `.tabbar { height }`, `body { padding-bottom }` and the `.chat` height calc.
- Severity: **major**. Effort: **S**.

**4. The desktop chat room grows without limit** (`style.css` line 598 `.scroller { flex: 1 0 auto }`; `chat.html`)
- Problem: on desktop the room grows with the thread, and the comment there says so. The mockup has 4 messages; the real server sends 30. The page will then be several screens tall and open scrolled to the top, so you see the oldest of the 30 first and the box to write in is far below the fold. That contradicts "Chat opens at the newest message" and the brief's "write to Vera straight away".
- Fix: use the phone model on desktop too. Give `.room` a height of `calc(100vh - <page head>)` with a `min-height` of about 480 px, set `.scroller { flex: 1 1 0; min-height: 0; overflow-y: auto }` (column-reverse then opens at the bottom with no script), and keep the composer pinned in the room. After PRG, redirect to `/chat#latest` as the standard says.
- Severity: **major**. Effort: **S**.

**5. The custom "Fraunces Figures" font: a build step that also takes over prose punctuation** (`style.css` lines 12–13, `--font-text`; STANDARD §1)
- Problem: the subset includes `. , : – - / +`, and it is listed first in the body font stack with no `unicode-range`. So every full stop, comma, colon and hyphen in body text ("St. Helens", "Bi-Mart", "gpt-6-luna" outside `.code`) renders in the serif, not Atkinson Hyperlegible. Atkinson's distinct digits, the reason it was chosen for kids, are also replaced. The font itself is a FamilyDB-only fontTools build: `fonts/` and the `CHANGES.md` that describes the script are not in the delivered folder. That leaves a build step someone has to own and rerun.
- Fix: take "Fraunces Figures" out of `--font-text`. Keep Fraunces with `font-variant-numeric: lining-nums tabular-nums` (already on `body`) for headings, `.money`, `.figure dd`, `.dt__d` and `.rank__n`. Ship stock Atkinson and Fraunces woff2 files with their OFL licences. If the team keeps the subset anyway, at least add `unicode-range: U+0030-0039, U+0024` so prose punctuation stays in Atkinson.
- Severity: **major**. Effort: **S**.

**6. Calendar `.span2` clashes with a page class, and only Saturday can span** (`style.css` line 634 `.c6.span2`, line 665 `.span2 { grid-column: 1 / -1 }`, line 708 `.signin .span2`)
- Problem: `.span2` means "two days" in the calendar and "full row" on Status and sign-in. Only `.c6.span2` is defined. A Wed–Thu plan rendered as `.ev.c3.span2` falls through to the global rule and stretches across the whole week. Plans of 3 or more days, and plans that cross a week boundary (Sun → Mon), aren't specified.
- Fix: rename to `.ev-len2…7 { grid-column-end: span N }`, and keep `.span-all` for page layouts. The `calendar_week` macro splits a plan at the week edge and marks the pieces as "continues" and "continued" in the spoken label. Add a busy-week specimen with a 3-day plan crossing Sunday to states-content.
- Severity: **major**. Effort: **S**.

**7. `white-space: nowrap` on every button and tag** (`style.css` line 178 `.btn`, line 194 `.tag`)
- Problem: STANDARD §5.9 says nothing scrolls sideways at 320 px or at 200 % zoom. At 320 px the Plans phone banner gives its button a column of about 200 px, but "Connect Google Calendar" at 17 px bold plus 40 px of padding needs about 250 px. The same applies to the button under each Status health row on the phone. Surprise tags grow with the names they hide ("Surprise · hidden from Maya and Theo"). In a 3-column idea card at 1001–1180 px (inner width about 240 px) they overflow the card. Text-only zoom (Firefox, iOS text size) makes both worse.
- Fix: `.btn { white-space: normal; text-align: center; max-width: 100% }` (keep `nowrap` only on `.btn--sm` in toolbars) and `.tag { white-space: normal }`. Add 320 px and 1024 px to the screenshot set.
- Severity: **major**. Effort: **S**.

**8. Meta refresh every 3 s while Vera is thinking** (STANDARD §8, "While a reply is pending")
- Problem: with scripting off this means up to 20 full page renders in 60 s. Each render recomputes `health()`, the 30-message thread and the nav badges on a small home server. Each reload also resets scroll and focus, and screen readers announce a new page every 3 s.
- Fix: back off from the server side (`content="3"`, then 5, then 10, computed from the pending message's age). Make `health()` and the badge counts cached (see Missing). Keep `chat.js` polling as the normal path, as specified.
- Severity: **minor**. Effort: **S**.

**9. Segmented controls hide their overflow** (`style.css` line 351 `.seg { overflow-x: auto; scrollbar-width: none }`; To do "Open · Done · Cancelled · All", Plans "Month · List", the states-sheet nav)
- Problem: "never wraps" combined with a hidden scrollbar means that at 320 px or with large text, "All" or "Cancelled" sits off the edge with nothing to show it's there. Kids won't find it.
- Fix: on the phone make `.seg` a grid with `grid-auto-flow: column; grid-auto-columns: 1fr` and allow the labels to wrap onto two lines. Drop `scrollbar-width: none`.
- Severity: **minor**. Effort: **S**.

**10. Fallbacks and stylesheet tidy-up** (`style.css`)
- Problem: `.chat { height: calc(100dvh …) }` (line 861) has no `vh` line before it, so a browser without `dvh` drops the whole declaration and the phone room loses its height. `.day--we` uses `color-mix()` (line 626) where a token would do. `.techie`, `.av .icon`/`.av > .icon`, `.tag__more` and `.idea__for` are each declared twice. `.privacy--room` lives outside the phone section (line 877). The Ideas markup carries the drive time twice per card (`.idea__foot` and `.drive.phone-only`). Each of these costs the person maintaining one stylesheet later.
- Fix: add `height: calc(100vh - …)` before the `dvh` line. Add `--we-bg` to both themes. Merge the duplicate rules into their component sections. Render the drive time once and lay it out with CSS. Test the chat box with the iOS keyboard open (the fixed tab bar plus the room height is the riskiest phone interaction in the app).
- Severity: **minor**. Effort: **S**.

## Missing
- **CSRF tokens.** None of the mockup's 60-odd forms has one. Make a `form(action, method)` macro that always emits the hidden token, and lint for `<form method="post">` without it.
- **Cached `health()`.** The pill and nav badges appear on every page, so they must not call OpenAI, Telegram or Google on each request. Cache them with a short time-to-live and let only Status "Check again" force a live check.
- **Cost guard on chat POST.** One-tap `.starter--ask` buttons, Send, and "Try again" each spend money. A double click or a refresh after POST must not ask twice, so use an idempotency key per message and disable on submit. Kids need a server-side message counter, not just the words.
- **Long lists.** No page shows paging or a cap: Ideas with 200 cards, To do "Done" and "All" after a year, Memory, and "What has changed". Add `?page=` links and a "Showing 50 of 212" line.
- **Locale settings the markup assumes.** Monday-first weeks, the 12-hour clock, `$` and ¢, "km" and weekday abbreviations are written into the mockups. The macros need them to come from the General settings.
- **Font files and licences, favicon and touch icon.** `fonts/` is absent from the delivered folder.
- **A breakpoint test matrix:** 320, 390, 820/821, 1000/1001, 1180, 1280 and 1920 px, at 200 % zoom, in dark mode and in forced colours, plus the CI check for `style="` and inline `<script>` that STANDARD §8 already proposes.
- **Very wide screens.** `.wrap` caps at 1080 px, which is good, but the Chat room and the calendar have no cap shown above 1280 px. A 1920 px calendar row with three lanes is untested.

## One sentence
Before any template is written, swap the name-based person colour classes for eight data-driven slot classes (`.p1…p8`). Every page depends on them, and they're the one part of this design that can't be built for a real family as drawn.
