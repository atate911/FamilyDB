# Type review: FamilyDB "Kitchen Table" final design

## Verdict
**7/10.** Pairing Atkinson Hyperlegible with Fraunces 600 is a good, warm and legible choice. The scale has a real floor (14 px, with 17 px body and 17–18 px inputs on the phone), and line length is capped at 62ch. What holds it back is one clever but harmful trick: the "Fraunces Figures" face is listed first in every stack, so every digit **and every full stop, comma, colon, hyphen and slash** in running text renders in a serif inside a sans. On top of that, `tabular-nums` is applied to all prose, the hierarchy is crowded in the 17–20 px band, and a few small alignment slips need fixing.
**Optimise before building? Yes:** the figures-first font stack is in the root tokens (`--font-text`, `--font-head`), so it is cheap to change now and expensive once every template and screenshot test depends on it.

## Protect
- **Pairing and roles** (all pages): Atkinson Hyperlegible 400/700 for words and Fraunces 600 for headings, the Vera mark and the date-tile day number. It is warm, readable for kids, and the two faces are clearly different.
- **Body and input sizes on the phone** (every phone page): 17 px body, 17 px lede, 18 px composer textarea and 17 px fields. iOS won't zoom on focus and kids can read it.
- **Measure** (`.lede`, `.banner__text`, `.msg`, `.measure`): the 62ch caps keep the ledes, banners and chat bubbles comfortable on a 1080 px desktop.
- **Date tile** (Home "Next up", Plans "Coming up"): the 13 px tracked overline weekday over a 28/36 px Fraunces numeral. It is the best typographic object in the system.
- **Money on Status / Home "Vera today"** (`.money`, `.figure dd`): `$0.00` at 44 px Fraunces with a 15 px sans qualifier is a clear figure-and-caption pair.
- **Overline discipline** (`.overline`): only one uppercase tracked style, used only for the sidebar group label and date-tile weekday. Keep it that rare.

## Fix, ranked

**1. Serif punctuation in all prose** (style.css §1 `@font-face "Fraunces Figures"` + `--font-text`; visible on every page)
- Problem: the subset holds `. , : – - / + $ %` as well as digits, and it has no `unicode-range`, yet it sits first in `--font-text`. So the full stop in "Tick one off when it's done." (To do lede), the commas in every Vera reply (Chat), the hyphen in "to-do", "Sign-in" and "12-hour clock", and the colon in "7:48 pm" are all Fraunces glyphs set inside Atkinson. The stated aim ("every number renders in Fraunces") is narrower than what ships. Every reader sees it, and it puts a different voice inside every sentence.
- Fix: remove the punctuation from the body stack. Either rebuild the subset as digits only, or add `unicode-range: U+0030-0039` to both Figures `@font-face` rules. Keep `$ % . , : –` only in a numeric context (see fix 2).
- Severity: major. Effort: S.

**2. Serif digits in running text** (To do meta "Sun 27 Sep", "6 days late"; Chat "Put the hike on Thursday at 10."; lede "4 open, 3 of them late"; Home "Thu 1 Oct", "2 h 5 min drive")
- Problem: in a sentence, a Fraunces "6" or "3" next to Atkinson lowercase reads as a font change. It also replaces Atkinson's own digits, which were drawn for the readers this app cares about (kids, low vision). In chat it changes how the family's own words look ("at 10.").
- Fix: make `--font-text` start with Atkinson. Apply Fraunces Figures with a `.num` class (or scoped selectors) only where figures stand alone or line up: `.money`, `.figure dd`, `.dt__d`, `.rank__n`, `.steps li::before`, `.meter__scale`, `.jobs` cells, `.day__n`, `.seg .n`, `.badge`. Headings can keep Figures first.
- Severity: major. Effort: S–M (token change plus about ten selectors).

**3. Tabular figures on all prose** (style.css §3 `body { font-variant-numeric: lining-nums tabular-nums }`; the subset forces every digit to the zero's width)
- Problem: in running text a tabular "1" leaves a visible gap. "Thu 1 Oct" (Home rate card), "1 pm", "Thursday 1 October, 10 am" (Chat) and "1 more plan to rate" all look loosely spaced. Tabular spacing only helps in columns, and there are almost none.
- Fix: set `proportional-nums` on `body`, and use `tabular-nums` only in `.jobs`, `.figure dd`, `.meter__scale`, `.day__n` and the time column of lists. For the Figures font, build a proportional set too, or keep it for column use only.
- Severity: major. Effort: S.

**4. Figures in the Status "Last 30 days" tiles don't share a baseline** (Status, `.figures`, desktop and phone)
- Problem: "Questions answered" wraps to two lines, so its "6" sits a full line below "$1.26" and "4¢". In the one row built for comparing numbers, the numbers don't line up.
- Fix: make `.figure` a grid with `grid-template-rows: subgrid` (or set `align-content: space-between` with a fixed label height of 2 lines × 1.3). Or shorten the label to "Answered" and put the full wording in the `dt`'s `.sr` text. Bottom-align all `dd`s.
- Severity: minor. Effort: S.

**5. Middle of the scale is too crowded** (card `h2` 20 px; `.idea h3` 20; `.rank__title` 18; `.srow__text b` 18; `.todo__title`/`.item__title` 17 bold; body 17)
- Problem: five levels sit inside 17–20 px, and they are told apart only by face and weight. On Home, the card title "Next up" (h2, 20 px) is smaller than its child "Oaks Park roller rink" (h3, 24 px), so the outline reads upside down. The "How did Silver Falls hike go?" card has no heading at all, just a `<b>` in Atkinson (home.html:160), unlike every other card.
- Fix: use a firmer ratio. Card h2 22 px; item titles stay 17 bold; drop 18 px and fold `.rank__title`/`.srow__text b` into 17 or 20. Make the next-plan title a visually large `p`, or make "Next up" an overline-style label, so the heading levels match the sizes. Give the rate card an `h2` in Fraunces like its siblings.
- Severity: minor. Effort: S.

**6. Too much 700 weight** (tags, badges, starters, `.more`, `.linkbtn`, field labels, `.kv dd`, `.choice`, nav, `.day__n`, `.ev time`, `.face`, `.composer` "Share where I am")
- Problem: Atkinson ships only 400/700, and nearly every small element is 700. On Status (health rows: bold title + bold tag + bold button on one line) and Home (bold tags, bold meta "6 days late", bold Edit) nothing stands out because everything is bold. The 14 px bold tags look heavy, especially in dark mode.
- Fix: keep 700 for titles, buttons, nav and the late text. Set `.tag`, `.badge`, `.more`, `.kv dd`, `.ev time` and `.day__n` to 400, or ship Atkinson Hyperlegible Next with a 500/600 weight and use that for small UI labels.
- Severity: minor. Effort: S.

**7. Leading separators when lines wrap** (To do phone: "Who, when, reminder / · Sam · No date"; Status phone: "Which AI does each job / · for whoever set it up"; Ideas "Filter · Any kind…")
- Problem: the `·` that joins the summary text to its label wraps to the start of the next line, so the line opens with a stray dot.
- Fix: render the summary values as their own `span.val` with `display:block` on the phone, with no leading separator, or put the separator in `::before` only when inline (`.disclose > summary .val::before { content: "· " }` above 820 px).
- Severity: minor. Effort: S.

**8. Model names and codes leave `.code` unevenly** (Settings "AI model" row: `gpt-6-luna` as plain text; Status `.jobs` uses `.code`)
- Problem: on Settings the "6" and both hyphens of `gpt-6-luna` render in Fraunces in the middle of a word. The standard says codes switch to Atkinson, but the template forgets to. Fix 1 and 2 solve most of this, but codes still want `.code`.
- Fix: the `health()`/summary macro wraps model names, keys and codes in `<span class="code">` everywhere, with a CI grep for known model-name patterns outside `.code`.
- Severity: minor. Effort: S.

**9. Sizes below the stated floor** (`.av--sm` 12 px; `.tabbar .badge` 12 px)
- Problem: the standard says 14 px minimum, with 13 px only for tab labels and overlines. The late badge on the phone To do tab ("3") and the small-avatar initials on Plans "Sam and Alex" are 12 px. A white initial at 12 px bold on a coloured disc is the hardest small text in the app for a child to read.
- Fix: set the tab badge to 13 px (it's a digit in a 20 px disc, so it still fits). For `.av--sm`, either raise it to 13 px with a 26 px disc, or record in STANDARD §7 that avatar initials are decorative (the name always sits beside them).
- Severity: minor. Effort: S.

**10. Fraunces is loaded as one static 600 cut** (style.css:16 `fraunces-600.woff2`; STANDARD §1 says "variable optical size")
- Problem: h1 at 40 px and card h2 at 20 px share one optical size. At 40 px ("Good morning, Sam.", "Chat with Vera") the 600 weight looks thick and tightly spaced. The 20 px headings would be better served by a lower opsz. The `letter-spacing: -0.01em` also tightens the small sizes, where it isn't wanted.
- Fix: ship the variable Fraunces (opsz axis, wght fixed at 600, Latin subset) with `font-optical-sizing: auto`. Apply negative tracking only to `h1` (-0.015em) and use 0 for h2/h3. Check that the default SOFT/WONK axis values are pinned.
- Severity: minor. Effort: M.

## Missing
- The `fonts/` folder and CHANGES.md (which holds the Figures build script) are not in `final/source/`. The engineer cannot reproduce the custom subset, and the stylesheet's relative `url("fonts/…")` paths point at nothing.
- No `font-display`/fallback metrics plan for the swap. Atkinson → Arial and Fraunces → Georgia need `size-adjust`/`ascent-override` fallbacks, or the first load reflows every card.
- No `text-wrap: balance` on h1–h3 or ledes, and no `text-wrap: pretty` on body text. This would stop one-word lines like "done." in the To do phone lede and "Falls" in long to-do titles.
- No `overflow-wrap: anywhere` for long unbroken strings (URLs in idea links, addresses, model names) at 320 px.
- No rules for number formats: thousands separators, prices like "$12–18", distances in km vs mi (Settings offers kilometres), or 24-hour times in the tabular columns.
- No specimen for languages or names outside Latin. A family member's name with diacritics or non-Latin script would fall out of the Latin-only subsets.
- No large-text check: the pages are not shown at 200% text size (not zoom) or with iOS Dynamic Type, where the fixed px values (18 px titles, 22/28 px phone headings, 12 px badges) won't scale.
- No style for long numbers in Status (a month of $123.45, 1,204 questions) inside the fixed-width figure tiles on the phone.

## One sentence
Take "Fraunces Figures" out of the body font stack: let Atkinson set every word, digit and comma in running text, and use the serif tabular figures only where numbers stand alone or need to line up.
