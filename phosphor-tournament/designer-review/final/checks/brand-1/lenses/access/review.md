# FamilyDB final design: accessibility review

Lens: WCAG 2.2 AA and beyond, plus low vision, dyslexia, colour blindness and one-handed phone use. I worked from the four overviews, the full-length desktop, phone and dark pages, every HTML file, `style.css` and `STANDARD.md`. I computed contrast from the CSS tokens with the WCAG 2.x formula and simulated colour blindness on the person colours with the Machado matrices. There was no browser here, so the reflow and zoom findings are worked out from the CSS, not from renders. Each fix is tagged **Real failure** (fails a WCAG criterion, or the standard's own rule) or **Judgement call**.

## Verdict
**7 / 10.** The foundations are better than most shipped apps. Every text pair in the tokens passes AA (my numbers match §7 of the standard: the lowest is `--ink-3` on `--paper-2` at 5.1:1). It uses Atkinson Hyperlegible at 17 px with a 14 px floor and a 62ch measure, has 44 px targets, says "late" in words, and has a proper error pattern. But a few small, real failures sit exactly where kids and screen-reader users go first: on the phone the Ask Vera starter buttons have no accessible name, the Edit links lose the word "Edit", focus can't be seen on the glass panes, and the dark Ask box has no visible edge.

**Optimise before building?** No. Every failure below is a markup or token fix of size S or M in `style.css` and the mockups, with nothing structural to redesign. Fix them in the source first, because the engineer will copy it.

## Protect
1. **Type system** (`style.css` §2–3): Atkinson Hyperlegible 17/1.5 body text, a 14 px floor, `.measure`/`.lede`/`.banner__text` capped at 62ch, and slashed zeros kept in running text. This is the right choice for dyslexic and low-vision readers.
2. **The tick** (To do, Home: `.tick`): a 44 px hit area around a 32 px ring, its own POST form, and the name "Mark done: Call the dentist about Theo". The Edit link sits at the other end of the row, so a mis-tap can't do both.
3. **Lateness in words, not just red** (To do `.todo--late` + "6 days late"; kids get "Was due Sun 27 Sep"). Tags always carry a word (Needs a look, Could be better, Off), and each also has its own shape (fill, hollow dot, dashed).
4. **Form error pattern** (`states-actions.html`): a summary with `role="alert"` that gets focus and links to each field, `aria-invalid` and `aria-describedby` on the field, the message above the box, typed values kept, and errors written as the fix.
5. **Keyboard scaffolding**: a visible "Skip to content", a 3 px `:focus-visible` ring everywhere (sun-yellow inside the Ask card, 7.7:1), `scroll-padding-bottom` so the fixed tab bar never hides the focused control, and a chat log with `role="log"` that is focusable and named.
6. **Kids' words and the grown-ups page** (`home-kid`, `todo-kid`, `wishes-kid`, `grownups`): short, plain sentences (around grade 2–4), e.g. "Sam or Alex tick these off. Done? Tell Vera, and she'll let them know." A kid who opens an admin page gets a kind page, not an error.

## Fix, ranked

**1. Phone starter buttons lose their accessible name** (Home, kid Home and kid Chat: `.starter` in the Ask card)
- Problem: **Real failure (4.1.2 Name, Role, Value; 2.5.3 Label in Name).** On the phone, `.starter .long { display:none }` removes the full text, and the visible `.short` span is `aria-hidden="true"`. "Next weekend?", "Remind me…" and "Save an idea…" (and the kids' "This weekend?", "I wish for…" and "Help me with…") are therefore buttons and links with no name at all. VoiceOver and TalkBack read "button", and Voice Control can't target them. These are the first controls a kid meets.
- Fix: at ≤ 820 px, hide `.long` with the `.sr` clip pattern instead of `display:none`, and keep `.short` `aria-hidden`. The name stays "What should we do next weekend?", which contains the visible "Next weekend?". Add a rule to the standard: never pair `display:none` with an `aria-hidden` stand-in.
- Severity: **blocker**. Effort: S.

**2. On the phone, "Edit" disappears from the edit link's name** (To do and Home: `.todo__edit`)
- Problem: **Real failure (2.4.4 Link Purpose, 2.5.3 Label in Name).** `.todo__edit .lbl { display:none }` on the phone leaves only the `.sr` text, so the pencil link is announced as "Call the dentist about Theo". That sounds like the to-do itself, and "Tap Edit" in Voice Control finds nothing.
- Fix: hide `.lbl` visually with the clip pattern, not `display:none`, or move "Edit" into the `.sr` span ("Edit: Call the dentist about Theo"). The standard already asks for this name.
- Severity: major. Effort: S.

**3. Focus ring is invisible on glass panes in light mode** (404: "Go to Home" and "Ask Vera to find it"; any link put in a `.pane`)
- Problem: **Real failure (2.4.7 Focus Visible; 1.4.11 at 3:1).** `--focus` is `#1D2526` and the pane is `--glass` `#0E1312`, which is **1.2:1**. Against the green primary button the ring is 2.0:1. A keyboard user on the missing page can't see where they are. Dark mode is fine (cream on glass, 16:1).
- Fix: `.pane, .instrument__pane { --focus: var(--phosphor); }` (14.7:1 on glass). Add the pane to the focus specimens.
- Severity: major. Effort: S.

**4. The dark-mode Ask Vera box has no visible edge** (Home and kid Home, dark: `.ask textarea`)
- Problem: **Real failure (1.4.11 Non-text Contrast).** `.ask textarea { border-color: transparent }` leaves the fill to mark the field. In light mode that is white on deep green (12.9:1), but in dark it is `#1B2321` on `#0A0E0D`, **1.21:1**. In `dark/home.jpg` the box reads as a faint smudge, which low-vision users at night will miss. The Ask card itself is also 1.01:1 against the page in dark mode.
- Fix: in the dark block, give `.ask textarea` a `1.5px solid var(--edge)` border (`#7E8C86`, 4.6:1 on the field), or lighten the field to at least 3:1 against `--ask-bg`.
- Severity: major. Effort: S.

**5. The pending reply reloads the page every 3 s with scripting off** (Chat: `<meta http-equiv="refresh" content="3">`, STANDARD §8)
- Problem: **Real failure (2.2.1 Timing Adjustable, Level A; WCAG failure technique F41; also 3.2.5).** Each reload throws a screen-reader user back to the top and makes a magnifier user lose their place. The standard records the concern but keeps the refresh. The back-off helps, but it still fails.
- Fix: drop the meta refresh. With scripting off, the visible "Check for her answer" link (already drawn) is the mechanism, and `chat.js` polls quietly when scripting is on. If a fallback is wanted, make it opt-in: a "Keep checking for me" link to `?wait=1` that alone carries the refresh.
- Severity: major. Effort: S.

**6. Endless blinking on every page** (every page: the wordmark cursor `.wm__cur`, and the health pill dot `.pill-health::before`)
- Problem: **Real failure (2.2.2 Pause, Stop, Hide, Level A).** Both animate `infinite` beside the navigation. `prefers-reduced-motion` helps people who know to set it, but it isn't a pause mechanism on the page. A blinking block next to the menu is a known distraction for readers with ADHD or dyslexia.
- Fix: end each animation within 5 s. For the cursor, `animation-iteration-count: 2`, then it stays lit. For the dot, one breath, then it stays still. Keep the reduced-motion rule. The Vera-is-busy glyphs and typing dots can stay, because they stop when the reply lands and the box is closed while they run.
- Severity: major. Effort: S.

**7. Who a plan is for is shown by colour alone in the calendar** (Plans desktop: single-person `.ev`, e.g. "Nutcracker at the Keller"; Plans phone: `.dots`)
- Problem: **Real failure (1.4.1 Use of Colour) for sighted users.** The spoken labels are good, but on screen a one-person event is only a pink bar, and on the phone month only a coloured dot. Under deuteranopia simulation, Maya's pink (`#B03F66` → `#737063`) is almost the same as Everyone's grey mark (`#8A806C` → `#88826D`), Theo's orange becomes olive near both, and Sam and Alex are both blue. Separately, slot colours `--p2` `#7B4790` and `--p8` `#8C3E86` have identical lightness (1.00:1) and nearly the same hue, so a family of eight gets two "same" people.
- Fix: on desktop, show the avatar initial on every event, as Sun 4 Oct already does. On the phone, draw the dots as 14 px initials (or add a day list under the month), and add a shape for Everyone (the house). Replace `--p8` with a hue far from `--p2`, and check all eight slots pairwise under deuteranopia and protanopia.
- Severity: major. Effort: M.

**8. Key sizes are in px, so they ignore the browser's text-size setting** (`.todo__title` 18px, `.rank__title` 18px, `.srow__text b` 18px, `.composer textarea` 18px, `.next h3` 26/22px, `.ask__head h2` 22px, `.month-nav h2` 28px, `.money` 30px, `.figure dd` 32px, `.person-tile b` 18px, `.wm` 22px)
- Problem: **Judgement call** (1.4.4 is still met through zoom). Body and headings are in rem, but these are in px. With a 24 px browser default, body text grows to about 25 px while to-do and wish titles stay at 18 px, so the hierarchy flips for exactly the low-vision users who set it. The fixed `height` on `.topbar` (56 px) and `.tabbar` (68 px) will also clip larger labels.
- Fix: convert these to rem (18px → 1.125rem, and so on), and use `min-height` on the top and tab bars.
- Severity: minor. Effort: S.

**9. Status figures likely overflow at 320 px / 400 % zoom** (Status phone: `.figures` kept at three columns)
- Problem: **Real failure risk (1.4.10 Reflow), computed rather than rendered.** At 320 px each figure gets about 56 px of content width, but "$1.26" in 24 px Fraunces Figures needs about 70 px and can't wrap. The standard asks for a 320 px test, and no 320 px render is supplied.
- Fix: `@media (max-width: 400px) { .figures { grid-template-columns: 1fr; } }`, or two columns with the third wrapping. Then render all seven pages at 320 px and check them.
- Severity: minor. Effort: S.

**10. Icon-only buttons have faint edges, and the disabled arrow almost vanishes** (Wishes and kid Wishes: `.rank__move .iconbtn`; Plans: the month arrows)
- Problem: **Judgement call** (the ink icon carries identification, so 1.4.11 is technically met). The circle edge is `--line-2`, 1.65:1 on card. The disabled "Move up" arrow is drawn in `--line-2` on card (1.65:1), so low-vision kids ranking wishes see one arrow, not a pair with one switched off.
- Fix: use `--edge` (3.8:1) for `.iconbtn` borders, matching the other controls. Keep disabled arrows at `--ink-3` with a dashed edge, and add visible "Top" text (or keep the `.sr` reason) so the state is shown, not just faded.
- Severity: minor. Effort: S.

## Missing
- A **focus specimen sheet**: no screenshot shows a focused state. Draw focus on a button, tick, choice pill, idea card, `.item` row with a trail button (`:focus-within` plus the button's own ring gives two rings), tab bar, glass pane and Ask card, in light and dark.
- **Forced colours** for the phone calendar dots and the today wash: `.dots i` are background-only, so in Windows High Contrast they disappear. Add `forced-color-adjust: none` or a `CanvasText` border.
- A hidden **`autocomplete="username"` field** on sign-in (value = the picked person), so password managers fill the right password for each tile (supports 3.3.8 Accessible Authentication).
- **Announcing Vera's reply** when `chat.js` swaps the pending bubble: append it inside the `role="log"` region and don't move focus. Also announce the kid's "5 messages left" warning politely.
- **Page language**: `lang="en-US"`, but the standard mandates British English. Set `en-GB` so screen readers and hyphenation match the words.
- **One-handed reach**: for a parent, Wishes ("1 to decide") lives only behind the avatar at the top right, the hardest tap one-handed on a large phone. The Home "Wish lists" card reaches it, but it is fifth on the phone. Check that the "1 to decide" row stays in thumb reach, or show the count on the avatar dot in words.
- **Real-device passes**: VoiceOver iOS and TalkBack on Home, Chat and To do; 200 % and 400 % zoom on desktop (the chat falls back to page scroll under 560 px high, so check that); text spacing (1.4.12) against the line-clamped calendar events.
- **Session and sign-out timing** for a kid on a shared computer: if sessions expire, warn first and keep the typed message (2.2.1, 3.3.7).

## One sentence
Stop hiding text with `display:none` next to an `aria-hidden` stand-in. That one CSS habit strips the names from the Ask Vera starters kids tap first and the word "Edit" from every phone edit link, so switch it to the `.sr` clip pattern and write the rule into the standard.
