# FamilyDB design review: generalist

## Verdict
**7 / 10.** On desktop this is a warm, calm, clearly organised family tool. The paper-and-forest palette, the Fraunces headings and the plain-spoken copy ("Roller rink tomorrow, and three to-dos have slipped past their dates") make it feel like a household object and not an admin panel, and every page answers its own question in the first screen. The phone layouts were made by collapsing the desktop grids, not designed for the phone. As a result, rows break (Settings, Status, To do), filters push the content off the first screen, and the parts a kid or a worried parent needs most (Wishes, the Settings alert) end up behind "More". The pages also never show what a kid sees, although the brief says kids must be able to use it.

**Optimise before building?** Yes. The phone, which the family will use most, needs its own layout rules, and fixing that in the mockup is far cheaper than fixing it in nine more templates.

## Protect
1. **Home, "Ask Vera" panel**: a dark-green block with the input and a yellow Send button as the first thing on the page, plus suggestion chips. It is the clearest "start here" in the set.
2. **Home and Plans, date tiles** (SUN / 4 / OCT, FRI / 9): instantly readable by a kid, and the same on every page.
3. **Copy voice everywhere**: page ledes, "Only parents see this.", "No tag means it's fine as it is", the Status headline "Vera is working, and well under budget." Plain, honest, non-technical.
4. **Settings, the summary line and tag on each row** ("Needs a look" / "Could be better" / no tag) with the "Reading this list" legend. This is exactly what the brief asked for.
5. **Status, the "Spent today" bar** with its "a usual day ≈ $0.04" marker and the line about what happens at the limit. It explains cost without numbers anxiety.
6. **Chat, the per-person colours and avatars** (Sam blue, Alex purple, Maya pink, Theo orange), reused in to-do owners, idea "for" and "Writing as". Also the note "Parents can read the kids' chats. Maya and Theo see a note saying so".

## Fix, ranked

**1. Settings rows break on phone** (Settings phone, every `.srow`)
- Problem: on the phone, the chevron drops onto its own line under the text in a bottom-left gutter ("General", "AI model", "Spending", "Lookups", "What has changed"). Rows without a tag still render an empty grid cell, so they wrap differently from rows with one. Each row becomes about 130 px tall, the list reads as broken, and the parent who has to fix "Needs a look" scrolls about 4 screens.
- Fix: below 820px, use `grid-template-columns: 44px 1fr 20px` with `grid-template-areas: "ic text go" "ic tag go"`, put the tag under the summary, and drop the empty `<span>` when there is no tag. Centre the chevron vertically on the right. The target row height is 72–88 px.
- Severity: major. Effort: S.

**2. Phone navigation hides what kids and the Settings alert need** (all pages, phone tab bar)
- Problem: the six tabs are Home/Chat/Ideas/Plans/To do/More. Wishes, a kid's main page, is behind "More", and the red "1" that marks Settings on desktop has no equivalent on phone (More shows no dot). The bar also sits at the top under the header, which is far from the thumb on a 390px screen.
- Fix: move the tab bar to a fixed bottom bar (`position: sticky; bottom: 0`, with 56px of tap targets and `env(safe-area-inset-bottom)`). Make the five tabs depend on role: parents get Home, Chat, Plans, To do, More, and kids get Home, Chat, To do, Wishes, More. Ideas moves into More for kids, or stays and Plans moves. Carry the highest-severity badge onto More (a red dot when any Settings row "Needs a look").
- Severity: major. Effort: M.

**3. No kid view is drawn** (Home, To do, Chat, as Maya or Theo)
- Problem: every page is shown as Sam, a parent. The brief says kids see different things and must be able to use it, but nothing shows a kid's Home: their own to-dos, their wish list with drag/rank, their own chat. Cost, setup and "Vera today" panels must disappear. Without this, engineers will build a parent page with things hidden, and the kid's page will feel empty.
- Fix: draw Home and Wishes for Maya before building. Home: "Hi Maya", Ask Vera, "Your to-dos", "Your wish list" (ranked 1–n with up/down buttons that work without JS, as small forms), and "Next family plan". Use larger tap targets (48px), no money and no setup.
- Severity: major. Effort: M.

**4. Settings and the other pages contradict each other about lookups** (Settings › Lookups vs Ideas header and Status table)
- Problem: Settings says "Lookups: Off: Vera won't look things up on the web". Meanwhile Ideas says "Vera has looked up 10", shows "Look it up" links, and Status lists "Web lookups → gpt-6-luna". A non-technical parent can't tell which is true, and the Settings page exists to give them that confidence.
- Fix: generate every summary line from the same state as the pages. If lookups are off, the Ideas lede should say "Lookups are off; turn them on in Settings", "Look it up" should be hidden or point to that setting, and the Status row should show "Off" in place of a model. Add a rule to the build spec that each settings summary must be computed, never written as copy.
- Severity: major. Effort: S.

**5. Ideas filters push the list off the first phone screen** (Ideas phone, filter block)
- Problem: on the phone, the title, Add button, "Save a thought", the tabs, "Newest first", Search, Kind, Status, For and Show stack into about a screen of controls before the first idea. Kids browsing ideas see forms, not ideas.
- Fix: on phone, show only the search field plus a "Filters" `<details>` (closed by default, with the number of active filters in its summary, e.g. "Filters · 1"). Put Kind/Status/For inside it as three selects with Show. Move "Save a thought for later" below the tabs as a single-line input with Save. The first idea card should start within 500px of the top.
- Severity: major. Effort: S.

**6. To-do rows and filters waste space on phone** (To do phone, list rows and status tabs)
- Problem: each overdue row is about 300 px tall, because owner, date and "days late" each sit on their own line. The Open/Done/Cancelled/All segmented control wraps "All" onto a second line inside a pill, and search does not span the width. Four to-dos take two screens, and the tick, which is the main action, is small next to a big empty area. The quick-add form (4 fields + Add) also sits above the list, so overdue items start on screen 2.
- Fix: keep owner and due on one meta line ("Alex · Sun 27 Sep · 6 days late"), with the 44px tick on the left and Edit as a pencil icon button on the right. Make the filter a horizontally scrollable row of four tabs that never wraps (`flex-wrap: nowrap; overflow-x: auto`) and the search full width. On phone, put the list first and collapse quick-add to one input with a "More options" `<details>` for Who/Due/Remind.
- Severity: major. Effort: S.

**7. The Status "Which AI does each job" table collapses badly on phone** (Status phone)
- Problem: three columns at 390px force "gpt-6-luna" to break into "gpt-6- / luna" and the job description to wrap to 4 lines. The "None" backup pills float mid-row. This is the page a parent opens when something seems wrong.
- Fix: below 600px, render each job as a stacked row: line 1 "Chat — gpt-6-luna (OpenAI)", line 2 "Backup: none" in the alert colour. Never break model names (`white-space: nowrap`).
- Severity: minor. Effort: S.

**8. Calendar "today" and multi-day plans on phone** (Plans phone, month grid)
- Problem: the today cell shows a clipped "3 TOD" label. Plans are reduced to unlabeled colour bars, so a kid can't tell what the purple bar on the 17th is without scrolling to "Coming up". Cannon Beach weekend is drawn as two unrelated chips (Sat "08:00", Sun "all day") on desktop, not as one span.
- Fix: on phone, drop the "TODAY" word and use only the filled green number circle. Make each day cell a link to that day's anchor in the "Coming up" list, and show a 2–3 letter initial or icon in the bar. Draw multi-day plans as one continuous bar across days on both widths, with the title on the first day only.
- Severity: minor. Effort: M.

**9. Slashed zeros in times and money** (all pages, Atkinson Hyperlegible digits: "13:ØØ", "$2.ØØ", "1Ø:ØØ")
- Problem: the body face's slashed zero is built for telling 0 from O, but here it lands mostly in times and prices, where it reads as "Ø" and looks like a glitch to a kid. It also clashes with the Fraunces numerals in "$0.00" and the date tiles.
- Fix: set times, dates and amounts in a `.num` style that uses a face or alternate with a plain zero (test Atkinson Hyperlegible Next's alternates, or use Fraunces with `font-variant-numeric: tabular-nums lining-nums` for figures). Keep the slashed zero only for codes and keys.
- Severity: minor. Effort: S.

**10. Fonts load from Google, and the setup card is hard to find on phone** (all pages `<head>`; Home phone)
- Problem: every page links `fonts.googleapis.com`. On a family-run private server, that leaks visits to a third party and breaks the type offline, which goes against the "loads nothing from anywhere else" constraint. Separately, on phone Home, "Finish setting up" (3 steps, parent only) falls to about the 4th screen, below Just added to Ideas.
- Fix: self-host Atkinson Hyperlegible 400/700 and Fraunces 600 as WOFF2 with `font-display: swap`, subset to Latin, at roughly 150 KB total. On phone Home, while setup is unfinished, show a one-line strip under the greeting for parents ("3 setup steps left · Continue") linking to the full card.
- Severity: minor. Effort: S.

## Missing
- **Kid's Home and Wishes page**, including the ranking interaction without JavaScript (up/down buttons as forms) and how a parent's "yes/no" on a wish looks to the kid.
- **Empty and first-run states**: no ideas, no plans this month, zero to-dos ("All done 🎉"), and Chat before anyone has said anything. The Wish lists card ("No wishes yet" twice) shows how flat these get without design.
- **Limit reached / Vera down**: the "Vera is on" header pill, the Home "Ask Vera" panel and Chat need a visible state for "Vera has hit today's $2.00 limit" and "OpenAI isn't answering". Today the only failure styling is on Status.
- **Sending and waiting in Chat without JS**: what the page shows after Send (pending bubble, "Reload if nothing shows" is only small print), plus the error if a message fails.
- **Dark mode and high-contrast**: the tokens on `:root` are light only. Phones at night will flash cream paper.
- **Long content and many items**: 40 ideas, long titles, a 6-person family in "Writing as", a busy calendar day (3+ plans in one cell, "+2 more").
- **Form validation and confirmation**: errors on Add a to-do or Add an idea (missing title, past due date), and a confirmation after ticking or cancelling, with undo.
- **The "More" page on phone** (linked as `more.html` but not drawn), which holds Wishes, What Vera knows, Status and Settings.

## One sentence
Design the phone version as its own layout, with a role-aware bottom tab bar, compact list rows and collapsed filters, and draw it first for Maya rather than Sam.
