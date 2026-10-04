# Type review: FamilyDB "Kitchen Table"

## Verdict
**7/10.** Fraunces for headings with Atkinson Hyperlegible at 17px for body is a warm, readable pairing that suits a family, and the desktop hierarchy is clear. The details let it down. Atkinson's slashed zero is used for every time and price, so "09:00" looks like "Ø9:ØØ". The stylesheet has about twenty font sizes and almost everything is bold, and on the phone the 1.5 line height, long table headers and wrapping rows make Status, To do and Plans fall apart.

**Optimise before building? Yes.** Numerals, the size scale and the phone rules are global CSS decisions, cheap to fix now and expensive to fix after they have spread through about fifteen more pages.

## Protect
1. The pairing: Fraunces 600 for h1–h3, date tiles and money, and Atkinson Hyperlegible for everything else (all pages; `style.css` lines 37–44).
2. Body at 17px with 1.5 leading, and the same 17px on the phone. Don't shrink it for density (`body`, line 37 and line 489).
3. The h1 on Home ("Good morning, Sam.", 42px desktop, 32px phone) with a short plain-language lede under it. The lede sets the tone.
4. The date tiles (`.dt`): small uppercase weekday over a Fraunces numeral, used for the next plan and the "coming up" list on Home and as the tick-free anchor of each row.
5. Status, "Spent today": a big Fraunces `$0.00` next to a quiet sans "of your $2.00 daily limit". This big-number-plus-quiet-context pattern works and should be reused for the stats.
6. Plain sentence-case wording in labels ("6 days late", "Whenever suits", "Vera hasn't looked it up yet"). The red bold "6 days late" in the To do meta line is the clearest status signal in the app.

## Fix, ranked

**1. Slashed zeros in every time, date and price** (Home "Next up" list `09:00 · 2 h 5 min drive`; Home "Vera today" `of $2.00 a day`; Status meter scale `$0 … $2.00`, "About $0.04 a day"; Plans calendar `10`, `20`, `30`; To do date column)
- Problem: Atkinson Hyperlegible's default zero has a slash. In running text that is fine, but in time and money clusters it reads as "Ø9:ØØ" and "$2.ØØ". This is the most repeated numeric content in the app, and it is noisy and foreign-looking to kids. The slashed calendar digits (10, 20, 30) also look different from the plain 1–9 next to them.
- Fix: add a numeric utility, `.num { font-family: "Fraunces", Georgia, serif; font-variant-numeric: lining-nums tabular-nums; font-weight: 600; }`, and wrap times, prices, counts and calendar day numbers in it. Fraunces' zero has no slash, and the app already uses Fraunces for `$0.00` and the date tiles. If sans figures are preferred, test Atkinson Hyperlegible Next and check that its default zero is unslashed before adopting it. Also drop leading zeros on times ("9:00", not "09:00"). It saves a glyph and reads the way families speak.
- Severity: major. Effort: S.

**2. Too many sizes and too much bold: collapse to a scale** (whole `style.css`)
- Problem: the sans text alone uses 11, 12, 13, 14, 15, 15.5, 16, 17 and 18px, and the serif uses 19, 20 (inline in chat.html), 21, 22, 23, 26, 28, 30, 32, 34, 42 and 44px (inline in status.html). Steps 1px apart don't read as different levels, they just look like mistakes. Weight is overused too: nav, buttons, labels, links, meta, names, tags, seg controls, to-do titles and "late" are all 700, so bold stops meaning "important". On Home's To do card the title, the owner chip and "6 days late" all compete. The section heading "Next up" (h2, 23px) is also smaller than the item inside it, "Oaks Park roller rink" (h3, 26px).
- Fix: define tokens and use only these. Sans: `--t-xs:13px` (uppercase labels only), `--t-sm:15px` (meta, help), `--t-md:17px` (body, row titles), `--t-lg:19px` (lede). Serif: `--h3:20px`, `--h2:24px`, `--h1:40px` desktop / 30px phone, `--display:44px` (money only). Remove the 11, 12, 14, 15.5, 16 and 18px values and the inline `style="font-size:…"`. Weights: 700 for titles, buttons, the active nav and alerts; 400 for meta, labels next to inputs, names in chips and non-current seg tabs. Make the `.next h3` the same size as or smaller than the card h2, or demote the card heading to the eyebrow style and keep the plan title as the visual h2.
- Severity: major. Effort: M.

**3. Status "Which AI does each job" table on the phone** (Status, phone, `.jobs`)
- Problem: three columns at 390px. The tracked uppercase headers wrap to "ANSWERED / BY" and "BACKUP IF / IT FAILS", the model name breaks mid-token as "gpt-6- / luna", and the job description wraps to three lines ("The weekly / 'what should / we do'"). A parent checking cost on a phone can't scan it.
- Fix: below 820px, turn each row into a stacked block: job name 17/700 with its description 15/400 beneath, then a two-item definition line, "Answered by **gpt-6-luna** (OpenAI) · Backup **None**". Apply `white-space: nowrap` to model IDs everywhere. Write the headers in sentence case ("Answered by", "If it fails") at 13px with .04em tracking, not .06em uppercase.
- Severity: major. Effort: S.

**4. Line height on wrapped titles and stacked rows** (Home phone "Next up" list; To do phone rows; Settings phone rows)
- Problem: every bold title inherits 1.5. When "Mount St. Helens / day trip" or "Book the campsite at / Silver Falls" wraps on the phone, the gap between its own lines is nearly as big as the gap to the meta line, so title and meta look like three unrelated lines. On To do (phone) each overdue row becomes about 350px tall, with the owner and the date on separate lines and big gaps, so you see only two to-dos per screen.
- Fix: `line-height: 1.25` for `.soon .t`, `.todo .t`, `.trow .t`, `.srow b`, `.mini-idea b`, `.idea h3`; `margin-top: 2px` before the meta line. On the phone, put the To do row meta on one line: `.trow` becomes title, then a single `.meta` row "Alex · Sun 27 Sep · **6 days late**", with Edit as an icon button, not a separate text column.
- Severity: major. Effort: S.

**5. Small text that is too small or clipped on the phone** (Plans calendar; tab bar; date tiles)
- Problem: on the phone the calendar weekday headers drop to 11px and the today cell shows "3 TODA", where the `.today-l` label is cut off by the cell edge. Tab bar labels are 12px bold and the badge digit is 11px. `.dt.sm .wd` (FRI, SAT) is 11px. Kids and older eyes struggle below 13px, and uppercase at 11px with no tracking is worse.
- Fix: set a 13px minimum anywhere in the app. Hide `.today-l` below 820px (the filled circle already says "today") and add `aria-current="date"` on the cell. Use single-letter weekday headers on the phone ("M T W T F S S", 13px, `abbr title="Monday"`). Tab labels 13px/700; badge 12px; `.dt.sm .wd` 12px with .06em tracking.
- Severity: major. Effort: S.

**6. Tabular alignment in lists and numbers** (To do date column; Status stats and meter scale; Home "coming up"; Plans day numbers)
- Problem: no `font-variant-numeric` anywhere in the stylesheet. Times down the Home "Next up" list (09:00, 19:00, 08:00) and the To do date column ("Sun 27 Sep", "Mon 28 Sep", "Thu 1 Oct") don't line up, and calendar numerals shift width cell to cell. On Status the three stat values (6, $1.26, 0%) sit at different optical sizes.
- Fix: `font-variant-numeric: tabular-nums lining-nums` on `.meta`, `.trow .c`, `.meter-scale`, `.stat .v`, `.cell .n`, `.big-money`, `.ev time` (or via the `.num` class from fix 1). On To do, write dates as "27 Sep" in the column and put the weekday in the small line, so the dates align on the numeral.
- Severity: minor. Effort: S.

**7. Uppercase tracked labels used too widely** (Status table headers; To do "OVERDUE · 3"; sidebar "BEHIND THE SCENES"; calendar headers)
- Problem: four different uppercase styles (13px .08em, 15px .06em, 13px .06em, 12px .08em). The 15px uppercase To do group heading "OVERDUE · 3" is louder than the h1-level page content beneath it, and uppercase hurts word-shape recognition for young readers.
- Fix: one style, `.overline { font-size:13px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }`, used only for the sidebar group label and the date-tile weekday. Make To do group headings sentence case, 17px/700: "Overdue (3)" in alert red, "Whenever (1)" in ink-2.
- Severity: minor. Effort: S.

**8. Web fonts are fetched from Google** (every page `<head>`)
- Problem: the app runs on the family's own server and "loads nothing from anywhere else". Each page asks fonts.googleapis.com for the fonts, which leaks each visit to a third party and fails on an offline home network. The fallbacks then change the look and the metrics (Georgia for Fraunces is much wider), and the layouts tuned to these widths, such as "October 2026" with `min-width:200px`, shift. Only Fraunces 600 is requested, but `.brand b` asks for 700, which gets faux-bolded.
- Fix: self-host woff2 subsets (Latin + Latin-1) of Atkinson 400/700 and Fraunces variable (opsz 9–144, wght 600–700), with `font-display: swap` and `size-adjust`/`ascent-override` tuned fallbacks (`Georgia` for Fraunces, `Arial` for Atkinson). Preload the two body files.
- Severity: major. Effort: S.

**9. Wrapping controls on the phone** (To do phone filter "Open / Done / Cancelled" with "All" alone on a second row; Settings phone chevron on its own line under "General" and "AI model"; Home phone suggestion chips cut off as "Remi…")
- Problem: these break at word level, which makes the type look broken. "All" orphaned in a giant pill and the lone "›" each cost a row. The clipped chip reads as a typo.
- Fix: seg on the phone, `flex-wrap:nowrap; overflow-x:auto` or tabs at 15px with 12px padding (four labels fit in 358px). Settings `.srow` on the phone: keep the chevron in column 3, spanning rows. Suggestion chips: let them wrap onto two lines instead of scrolling sideways, since kids don't discover horizontal scroll.
- Severity: minor. Effort: S.

**10. Measure of prose** (page ledes; Status verdict; Settings attention banner; chat bubbles on desktop)
- Problem: there is no max line length. Ledes and banner text can run to the full 1060px wrap, about 120 characters at 17–18px; the Settings "One thing needs a look" sentence and the Ideas lede already run long on desktop. Chat bubbles cap at 78% of the thread, which is about 75 characters, fine now but long on wide screens.
- Fix: `max-width: 62ch` on `.lede`, `.verdict p`, `.attn .grow`, `.notice p`, `.side-card p`; `.msg { max-width: min(78%, 60ch) }`.
- Severity: minor. Effort: S.

## Missing
- Long names and long text: a 60-character idea title in a 3-column card, a German or Dutch place name, a to-do of 2–3 lines. Line clamp rules (`-webkit-line-clamp: 2` for cards, full text on detail pages) are needed.
- Large money and counts: "$12.48 of your $20.00" and "1,284 calls" in the stat tiles and the 44px `$` figure at 390px. Show that the number doesn't overflow, and decide on separators and currency.
- Browser text zoom at 200% and the OS "larger text" setting on phones: the fixed px sizes and fixed `.trow` columns (130/150/150px) need checking. Prefer rem.
- Empty, error and loading copy styles: Vera "thinking" in chat, "over the limit" on Status, a failed lookup on an idea card. There is no type style for an error message or inline field validation.
- Long chat messages: Vera's weekend digest with a list, links, times and prices inside a bubble. Rules are needed for lists, bold and paragraph spacing in `.bub`.
- Date and time formats: 24-hour vs 12-hour, and "Sun 27 Sep" vs "Sep 27", follow the General setting ("°C and kilometres"), which the type must handle in tabular columns.
- A kid's view: a reading-age check of the smallest text that a kid actually sees (wish list, to-do meta, chat timestamps).
- Print or export of the plans month and the to-do list, which families do print, with a print stylesheet.

## One sentence
Bring every number (times, prices, counts and dates) onto one lining, tabular, unslashed figure style, because numbers are what this family reads most and right now they are the noisiest thing on the page.
