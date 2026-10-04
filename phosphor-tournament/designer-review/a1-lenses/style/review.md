# Visual style review: FamilyDB "Kitchen Table" mockup

## Verdict
**7/10.** The base is warm, calm and well made: cream paper, a deep green for Vera, one sunny yellow accent, a friendly serif for headings, generous rounded cards and an even 20 px rhythm. A family would feel "this is ours and it's tidy". But it has no character. Vera is a letter "V" in a circle, there are no drawings anywhere, the colours for people and for kinds of idea clash, red is used too much, and several phone layouts fall apart in ways that look careless.

**Optimise before building?** Yes. The colour roles and Vera's identity have to be settled before the first template is built, because every page inherits them.

## Protect
- The palette tokens in `style.css` (`--paper` #F6F1E7, `--card` #FFFCF6, `--vera` #1E5C4F, `--sun` #F2C14E). Warm and quiet, not "software blue".
- Home, the "Ask Vera" card: a dark green slab with a yellow Send button is the one loud thing on the page, and it's the right thing.
- Fraunces headings with Atkinson Hyperlegible body text (e.g. "Good morning, Sam.", "Oaks Park roller rink"). It feels like a family notebook and stays readable for kids.
- The tear-off calendar date tiles (Home "Next up" SUN 4 OCT, Plans "Coming up"). The best small piece of craft in the set.
- Ideas, dashed-border cards for "Not looked up yet" (Lego set, Board game night). A quiet, honest way to show a state without a warning colour.
- Plans, "How did it go?" with three face buttons. Simple enough for a kid.

## Fix, ranked

**1. Give Vera a face** (all pages: `.av-vera` in Ask Vera card, chat bubbles, phone chat tab; brand mark)
- Problem: Vera is a serif "V" in a circle with a yellow dot, drawn the same way as the family avatars (S, A, M, T circles). In Chat, Vera's avatar is no different in kind from Alex's. There is no mascot and there are no drawings on any of the seven pages. Kids are asked to talk to a letter. The app has no memorable face, and the warm palette has nothing to carry it.
- Fix: draw a simple Vera character that comes from the existing logo: a round, soft-cornered figure in `--vera` green, with the `--sun` dot as her "spark" (a hair clip or antenna). Make it single-colour plus sun, built from flat shapes and readable at 24 px. Draw 4 poses as inline SVG: *hello* (Ask Vera card, replacing the faint sun circle at `.ask::before`), *thinking* ("Vera is looking it up"), *done* (Chat confirmation, Status "working"), *sorry* (limit reached, Vera down). Use the 24 px head as her chat avatar so she reads as a different kind of member than the people. Use no other illustration style; line icons stay as they are.
- Severity: major. Effort: M.

**2. Separate person colours from kind colours** (Ideas cards, Plans calendar events, Home "Next up" tags)
- Problem: people have colours (Maya #C4486F pink, Theo #C66A12 orange, Alex #7B4790 purple, Sam blue), and the kinds of idea reuse the same hues: the Activity chip is pink, Restaurant is coral, Show is lilac-purple, Trip and Day trip are blue. On Plans the calendar colours events by kind, so the pink "Oaks Park roller rink" looks like Maya's and the purple "Nutcracker" looks like Alex's. A family reads colour as "whose". There are about 11 hues in play, so Ideas looks like confetti.
- Fix: reserve saturated colour for the four people (and green for Vera). Make kind chips neutral: `--paper-2` background, `--ink-2` text, with the kind icon carrying the meaning. Colour calendar events by who they're for (the person colour as a 3 px left bar, with a soft tint at ~15%), and use a neutral bar for "Anyone". Then Theo can spot his things across Ideas, Plans and To do.
- Severity: major. Effort: M.

**3. Use red once per screen, not everywhere** (sidebar `.nav .count`, To do overdue rows, Status "Backup if it fails", Settings banner)
- Problem: solid red badges sit on To do (3) and Settings (1) on every page. To do stacks a red OVERDUE heading, red left bars on every card (phone), red clocks and red "N days late". Status opens with a big green "Vera is working, and well under budget" and then shows three red "None" pills plus an amber warning. The family gets told off on every visit, and the page contradicts itself.
- Fix: nav counts use the soft variant that already exists (`.count.soft`: `--sun-soft` background, `--warn` text). Keep solid red only for a broken state (Vera down, over the limit). On To do, keep the red "6 days late" text and drop the red left bar and red heading icon (use `--ink-2`). On Status, change the "None" pills to a neutral "No backup" tag and keep the single amber notice below. Rule: at most one red element per viewport.
- Severity: major. Effort: S.

**4. Repair the phone layouts that break** (phone Settings rows, To do filter, Plans today cell, Ideas filters)
- Problem: on phone Settings, the chevron drops onto its own line under the icon for General, AI model, Spending and Lookups, but sits on the right for rows with a tag. On To do, the Open/Done/Cancelled/All control wraps "All" onto a second row inside a lumpy pill, and the search box stops short of full width. On Plans, the today cell is cropped to "3 TODA" and the green day circle is squashed into an oval. On Ideas, the four filters stack into about 600 px of form before the first idea. These read as unfinished.
- Fix: settings row as a 3-column grid `40px 1fr 20px` with the chevron always vertically centred on the right, and the tag under the summary text. Segmented control below 420 px: `display:grid; grid-template-columns:repeat(4,1fr)` with 14 px labels, or a horizontal scroll strip; search `width:100%`. Today cell on phone: just the filled green circle with the number (`aspect-ratio:1; width:28px`) and no "TODAY" word. Ideas on phone: put the filters behind a `<details>` "Filter (3)" summary, so the list starts on screen 1.
- Severity: major. Effort: S.

**5. Make the controls visible against the cream** (To do tick circle, input borders, muted captions)
- Problem: the tick circle and field borders use `--line-2` #D3C6AC on `--card`, which is a 1.65:1 contrast, well under the 3:1 needed for controls. The main thing a kid taps on To do is a faint beige ring. `--ink-3` #6E7778 is 3.74:1 on `--paper-2` (Status "Last 30 days" tile captions, "Calls to the AI") and 4.08:1 on `--paper` ("Newest first", "Only parents see this").
- Fix: give the tick circle a 2 px border in `--ink-3` (4.5:1), filling with `--vera` and a white check when ticked. Input borders: #A8997A. Darken `--ink-3` to #5C6566 (about 4.9:1 on `--paper-2`). Keep `--line` for card borders, where it is only decoration.
- Severity: major. Effort: S.

**6. Self-host the two typefaces** (`<link>` to fonts.googleapis.com in every page)
- Problem: the pages pull Fraunces and Atkinson from Google. The brief says the app loads nothing from elsewhere, and it runs on the family's own server. If the link is dropped, the fallback is Georgia and Segoe/system-ui, which loses most of the warmth (Fraunces is doing a lot of the "kitchen table" work).
- Fix: ship woff2 files: Fraunces 600 (opsz axis, Latin subset) and Atkinson Hyperlegible 400/700. Use `@font-face` with `font-display: swap`. That is about 150 KB in total.
- Severity: major (for the look to survive). Effort: S.

**7. Show the phone calendar's content, not coloured lines** (phone Plans, month grid)
- Problem: on phone, each plan becomes a 6 px coloured bar with no words. Past plans are grey bars. You can't tell what's on the 24th without leaving the page, and the colour carries all the meaning.
- Fix: below 600 px, make List the default view and keep Month as an option. In the month grid, use one 8 px dot per plan in the person colour (after fix 2), and make each day with plans a link to that day's list. Put the "Coming up" card directly under the grid with no gap.
- Severity: major. Effort: M.

**8. Give the Ideas grid some pictures** (Ideas cards; Home "Just added to Ideas")
- Problem: Ideas has 12 identical cream cards that differ only by a 14 px chip, so it looks like a database, not a list of nice things to do. Home's "Just added" already has a better pattern: a 56 px tinted tile with the kind icon. The drive line shows a compass arrow in a grey circle (↓, ↗, ←) that reads like a stock-market trend, not "south of home".
- Fix: reuse the Home tile on Ideas cards: a 48 px rounded square, `--paper-2` tint and the kind icon in `--ink-2`, top left. Later, add a small set of spot drawings in Vera's style for empty and seasonal moments. Replace the arrow with words ("27 min south") as Home's "Next up" already does, or drop it.
- Severity: minor. Effort: M.

**9. Tidy the Ask Vera card** (Home, `.ask`)
- Problem: the decorative sun circle (`.ask::before`, 240 px) cuts behind the Send button on desktop, so the button sits on a half-tone edge. The third quick-reply chip "Save an idea…" wraps alone onto a second row. On phone the chips run off the edge ("Remi…") with no hint that they scroll.
- Fix: replace the circle with Vera's *hello* pose, top right, clear of the input (see fix 1). Give the chips `flex-wrap:nowrap; overflow-x:auto` on both sizes, with a 24 px fade on the right edge using `mask-image`, or keep them on one row by shortening the first to "This weekend?".
- Severity: minor. Effort: S.

**10. Check the slashed zero** (all times and money: "10:00", "$0.00", "$2.00")
- Problem: Atkinson Hyperlegible draws 0 with a slash, so times and prices look like code ("1Ø:ØØ"). Next to Fraunces numerals ("$0.00" big on Status) they don't match. This is part of what makes Status and Spending feel technical.
- Fix: decide on purpose. Either accept it as a legibility feature, or set times and money in Fraunces (`.num { font-family: Fraunces; font-variant-numeric: lining-nums tabular-nums; }`) so numbers look the same everywhere.
- Severity: minor. Effort: S.

## Missing
- Dark mode: no `prefers-color-scheme` in `style.css`. It's used on phones at bedtime, so it needs green-black surfaces and a dimmer sun.
- Vera's states as visuals: thinking/typing, "looking it up", over the daily limit, AI down, "I didn't catch that".
- Empty states with a drawing: no ideas yet, no plans this month, a kid's empty wish list (Home shows "No wishes yet" as plain grey text).
- A kid's view: the same pages as Maya sees them. Larger tap targets, her colour as the accent, no money.
- Done and cancelled to-dos, and a ticked circle: what success looks like, and whether it is satisfying enough for a kid.
- Sign-in and first-time setup: the first impression, where the mascot and the warmth matter most.
- Long and messy content: long idea names, 4+ plans on one calendar day, many family members, non-Latin names in avatars.
- Favicon, home-screen icon and Telegram bot avatar, drawn from the same mark so Vera looks the same on the website and in Telegram.

## One sentence
Draw Vera as a real character, built from the green house and the sun dot, and make her the face of the app, so the family is talking to someone, not to a "V".
