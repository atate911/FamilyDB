# FamilyDB design review: buildability and robustness

## Verdict
**7/10.** The base is unusually portable: one 560-line stylesheet built on custom properties, real `<form method="post">` and `<form method="get">` controls, no script anywhere, and visible `:focus-visible` outlines. It maps cleanly onto Jinja macros. But about 30 inline `style=""` attributes and the external Google Fonts link will not pass the stated CSP. The Home suggestion buttons post a duplicate `text` field, "Send where I am" cannot work with scripting off, and the phone calendar and phone Settings rows break visibly.

**Optimise before building?** Yes. The fixes are small now, but once they have been copied into 15+ templates they become a hunt across the codebase. The CSP violations in particular stop the pages rendering correctly on day one.

## Protect
- **All pages, `style.css` `:root` tokens.** Colours, kind colours (`.k-*` setting `--kb`/`--kf`) and person colours are variables. Keep this single-stylesheet, token-driven approach. Do not add a utility framework.
- **To do and Home, `.tick` buttons.** Each tick is its own `<form method="post">` with `aria-label="Mark done: …"`. It works with no JS and needs only a CSRF hidden input added. Keep this pattern for every one-tap action, including the faces on Plans' "How did it go?".
- **Ideas, `.filters` GET form with a "Show" button.** Filtering is shareable in the URL and needs no JS. Keep it a GET form and keep the button.
- **Chat, "Writing as" `<fieldset>` of visually styled radios (`.pick`).** It is native and keyboard operable, and has its own focus ring (`.pick input:focus-visible + span`).
- **All pages, `:focus-visible` 3px ink outline,** plus the yellow variant inside the green Ask Vera box (`.ask :focus-visible`). Focus stays visible on every surface.
- **Responsive approach.** Grids use `minmax(0,1fr)`, `.main`/`.card` use `min-width:0`, and there are three breakpoints (1180/1000/820). Long text wraps instead of blowing out columns, as seen in Home "Lava tubes at Ape Cave" and Ideas "Pumpkin patch at Bi-Mart farm".

## Fix, ranked

**1. Remove every inline style so the pages survive the CSP** (Home, Ideas, Status, To do, Plans, Chat, Settings)
- Problem: the mockup has about 30 `style=""` attributes. Most are spacing (`margin-top:14px`, the `list-style:none` `<ul>` on To do), but some carry data: the Home spend bar `style="width:1%"`, every distance arrow on Home and Ideas `style="transform:rotate(180deg)"` (eight different angles), and the Ideas card's "Look it up" link `style="position:relative;z-index:1"`. With `style-src` lacking `'unsafe-inline'`, all of these are dropped silently. The arrows then all point north, which is wrong information. The bar fills nothing, and "Look it up" sits under the card's stretched-link overlay and cannot be clicked. Everyone is affected, and nothing shows an error.
- Fix: spacing becomes classes (`.mt-s`, `.list-reset`). Make the arrow eight sprite symbols (`#dir-n`, `#dir-ne` … `#dir-nw`) chosen in Jinja, or put an SVG `transform="rotate(…)"` *attribute* on the `<path>`. Presentation attributes are not blocked by CSP. Make the bars native `<meter value="0.00" max="2.00">`, which is styleable and accessible, or an inline SVG `<rect width="1%">`. Add `.idea .foot a { position:relative; z-index:1 }` to the stylesheet. Add a CI check (`grep -r 'style="' templates/`) so none come back.
- Severity: blocker. Effort: S.

**2. Self-host the fonts and drop the Google Fonts `<link>`** (every page, `<head>`)
- Problem: every page loads `fonts.googleapis.com`. The brief says the app loads nothing from elsewhere, and the CSP would have to allow two Google origins. A self-hosted family server also leaks each page view to Google. If it is blocked, every page falls back to Georgia and Segoe UI, and the heading metrics shift.
- Fix: put the WOFF2 subsets in `/static/fonts/`: Atkinson Hyperlegible 400/700 Latin, and Fraunces 600 only, static rather than the variable `opsz` axis. That is about 4 files and about 120 KB. Add `@font-face` with `font-display: swap` at the top of `style.css`, and `<link rel="preload">` only the 400 body weight.
- Severity: blocker (it conflicts with the stated rules). Effort: S.

**3. Fix the Home suggestion chips: they post the wrong text** (Home, `.sugg` buttons in Ask Vera)
- Problem: the three chips are `<button name="text" value="…">` in the same form as `<textarea name="text">`. Clicking "What should we do next weekend?" posts `text=&text=What…`, and Flask's `request.form["text"]` returns the first, empty value. "Remind me to…" and "Save an idea…" are half-sentences, so submitting them sends Vera a fragment and starts a paid AI call. Without JS they cannot pre-fill the box. This hurts every family member who taps a chip, especially kids.
- Fix: rename the chip field to `name="prompt"`. If the server gets a complete prompt ("What should we do next weekend?"), it sends it. For the two stems, make the chips plain links: `<a href="/chat?draft=Remind+me+to+">` renders Chat with the textarea pre-filled and `autofocus`. On phone, also let the chips wrap (remove `.sugg { flex-wrap:nowrap; overflow-x:auto }`), because the clipped "Remi…" in the phone screenshot has no visible scroll cue.
- Severity: major. Effort: S.

**4. Replace the phone calendar's text-less bars** (Plans, `.cal` at ≤820px)
- Problem: at phone width `.ev { font-size:0 }` and `.ev * { display:none !important }` turn each plan into an 8px colour bar. Hidden children leave each `<a>` with no accessible name, so a screen reader says "link, link". The tap target is 8px tall against a 44px minimum, and the colours alone carry the meaning. Today's cell label is cut to "TOD" (phone Plans, Sat 3). A day with four plans has no limit. `role="grid"` is declared without rows or gridcells, which is invalid ARIA. On desktop `.ev b` has `text-overflow:ellipsis` but no `white-space:nowrap`, so long titles wrap and stretch the row instead of truncating.
- Fix: below 820px, don't shrink the month grid. Make the month view a compact grid of dots linked to `#day-9`, followed by the list view (which already exists) as the main content. Or simply default phones to List and give Month a link. Hide `.today-l` on phone and use only the filled circle. Cap each cell at 2 events plus "+N more" (Jinja `loop.index <= 2`). Remove `role="grid"`, or build the calendar as a `<table>`. Add `white-space:nowrap` to `.ev b`.
- Severity: major. Effort: M.

**5. "Send where I am" cannot work without JavaScript** (Chat, compose footer checkbox)
- Problem: the browser's location comes only from the Geolocation API, which is script. With scripting off, or under a strict CSP with no JS file written, the checkbox posts `where=on` and nothing else. The server has no idea where the user is. Users think they shared their location when they didn't.
- Fix: either (a) ship it as progressive enhancement in the one static JS file, and render the checkbox only from JS so it never appears when it can't work; or (b) with no JS, replace it with a text field: "Where are you? (optional)", placeholder "e.g. Hawthorne library". Say which one in the spec. Don't leave a control that does nothing.
- Severity: major. Effort: S.

**6. Fix the phone Settings rows' orphaned chevrons** (Settings, `.srow` at ≤820px)
- Problem: the 820px rule makes `.srow` 3 columns while the row still has 4 children (icon, text, tag, chevron). The chevron wraps to a second line under the icon (phone Settings: "General", "AI model", "Spending" each show a lone `›` bottom-left). Every row grows about 50px, and on "Sign-in and security" the tag and chevron end up on a separate line. It looks broken, and it is the page a parent opens to fix things.
- Fix: at ≤820px use `grid-template-columns: auto minmax(0,1fr) auto; grid-template-areas: "ic txt go" "ic tag go";` with `.srow .go { grid-area: go; align-self:center }` and `.srow .tag { grid-area: tag }`. Rows without a tag collapse the second row, because empty grid rows take no height.
- Severity: major (visible on the most important admin page). Effort: S.

**7. Show the reminder state on the To do list below 1180px** (To do, `.trow .rem`)
- Problem: `@media (max-width:1180px) { .trow .rem { display:none } }` hides "No reminder / Add one" on every phone, tablet and small laptop. The brief says each to-do shows "whether it has a reminder". On a 1280 laptop at 110% zoom it also disappears. Meanwhile each phone row is about 350px tall (phone To do: title, owner and date are stacked on separate lines), so 3 overdue items fill two screens. On phone the quick-add form also sits above the list, so the first overdue item starts about 1,700px down.
- Fix: keep the reminder as an icon-only bell (or bell-off) inside the date cell: `<span class="c late">… Sun 27 Sep · 6 days late <svg aria-label="No reminder">`. Join owner, date and reminder into one `.meta` line on phone, as Home already does for to-dos. That makes each row about 110px. On phone, put quick-add after the list, or collapse it into a `<details><summary>+ Add a to-do</summary>`, which needs no JS.
- Severity: major. Effort: S.

**8. Use an SVG sprite instead of inline SVG paths** (all pages)
- Problem: icons are pasted inline: 43 `<svg>` on Home, 42 on Ideas, 36 on To do. The same 3-path car icon repeats on every idea card and plan row. Templates get hard to read, the page weight grows with the number of items, and changing an icon means search and replace. The brief says the app has an icon sprite.
- Fix: one `static/icons.svg` with `<symbol id="car" viewBox="0 0 24 24">…`, plus a Jinja macro `{{ icon('car', 'sm') }}` that emits `<svg class="icon sm" aria-hidden="true"><use href="/static/icons.svg#car"/></svg>`. Keep `.icon { stroke: currentColor }`, which works through `<use>`. Inline the logo only once.
- Severity: minor (major for maintenance). Effort: S.

**9. Make the Chat page usable once the thread gets long** (Chat, `.thread` and `.compose`)
- Problem: the thread is rendered oldest-first above the compose box, with no limit. With scripting off the page loads at the top, so after a month of messages the newest reply and the box to write in are thousands of pixels down, especially on phone (phone Chat already puts the box at about 1,900px with only 4 messages). "Reload if nothing shows" means the POST returns before Vera's answer exists, and nothing comes back on its own.
- Fix: render only the last 30 messages, with an "Earlier messages" link (`?before=<id>`) at the top. After posting, redirect to `/chat#latest` with `id="latest"` on the last message, so the browser jumps there with no JS. Either keep the request open until Vera replies (usually seconds) and then redirect (Post/Redirect/Get), or add `<meta http-equiv="refresh" content="4">` only while a reply is pending. On desktop, consider putting the compose box above the thread at narrow heights. Also remove the duplicate `<span class="sr">Send</span>` on the Send button, which makes screen readers say "Send Send" on desktop.
- Severity: major. Effort: M.

**10. Make the skip link visible on focus; use `:focus-within` instead of `:has()`** (all pages, `.sr` skip link; Ideas, `.idea:has(h3 a:focus-visible)`)
- Problem: "Skip to content" uses `.sr`, which stays clipped when it gets focus. The first Tab press goes to an invisible element, which confuses keyboard users. Ideas card focus depends on `:has()`, which is missing in Firefox before 121 and Safari before 15.4 (older family iPads). There the card gets no outline, because the link's own outline is set to `none`, so focus becomes invisible. The status table on phone Status breaks "gpt-6-luna" across two lines because three columns are squeezed into 330px.
- Fix: add `.sr.skip:focus { position:static; width:auto; height:auto; clip:auto; padding:8px 14px; background:var(--card) }`. Replace the `:has()` rule with `.idea:focus-within { outline:3px solid var(--focus); outline-offset:3px }` and drop `outline:none` on the link. On the Status `.jobs` table at ≤820px, stack each row as a block (job, then "gpt-6-luna · OpenAI · Backup: none") with `display:block` on `tr/td`, or add `white-space:nowrap` to `.model`.
- Severity: minor. Effort: S.

## Missing
- **Kid view:** none of the seven pages is drawn as Maya or Theo. The real templates need explicit `{% if user.is_parent %}` branches for the Settings and Status nav, the setup card and cost. The phone "More" page (`more.html`), which on phone is the only way to reach Wishes, Memory, Status and Settings, is also not drawn.
- **Empty and overflow states:** Home with 0 plans or 0 to-dos, Ideas with 0 results after filtering, To do with 40 open items (the Home card has no "show 5, then link" limit), Ideas at 200 items (no pagination), and a calendar day with 5 plans.
- **Error and flash states:** form validation messages (empty to-do title, due date in the past), a CSRF token that has expired (a laptop left open overnight), "Vera is over today's limit", and an AI provider error shown in Chat. There is no `.flash` / `.field-error` style in `style.css`.
- **Degraded status:** only the green "Vera is working" verdict is drawn. The red/amber versions of `.verdict`, the topbar "Vera is on" pill and the Home "Vera today" card need to be designed for when the key fails or spend hits the limit.
- **Long and odd content:** a 120-character to-do title, an idea name with no spaces (a URL pasted in), a family member with a long name in the `.pick` chips, and 6+ family members (the 4-avatar `.avs` stack and the "Writing as" row).
- **Zoom and wide screens:** at 200% zoom on a 1280 laptop, the 820px breakpoint switches to the phone layout. That is fine, but the tabbar's 6 columns at 12px labels need checking. Over 1440px, `.wrap` caps at 1060px with a large empty right side, which is acceptable but should be confirmed.
- **Date input:** the `type="date"` picker shows "mm/dd/yyyy" (US) on the To do quick-add while the rest of the app writes "Sun 27 Sep". The locale comes from the browser, so the app needs a decided format and a server-side parser that accepts what each browser sends.
- **The dark green Ask box on very small or zoomed screens:** at 320px width the 18px textarea plus Send stack takes most of the first screen, and this state is not drawn.

## One sentence
Before any template is written, move every inline `style=""` (bars, arrows, z-index, spacing) into the stylesheet or SVG attributes and self-host the fonts. Otherwise the CSP silently breaks the arrows, the spend bars and the "Look it up" links on day one, and nobody notices until a user does.
