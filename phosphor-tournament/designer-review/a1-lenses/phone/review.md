# FamilyDB at 390 px: phone-first review

## Verdict
**6/10.** The look holds up at 390 px. Type is large (17 px body), cards stack cleanly, the Home composer is the first thing below the greeting, and nothing makes the whole page scroll sideways. But the phone layout is the desktop page stacked into one column, not a phone design. The navigation sits at the top and scrolls away. The page tools (quick-add forms, filter stacks) push the actual content a full screen down. A few CSS shortcuts also break things: calendar events become 8 px bars with no text, the reminder state disappears from to-dos, and the Settings chevrons drop onto rows of their own.
**Optimise before building?** Yes. The fixes are mostly CSS and source-order changes that are cheap now, but once every other page copies this pattern they become expensive.

## Protect
- All pages, top bar: "Vera is on" status and the avatar are always visible, so the family can tell at a glance that it's working.
- Home, Ask Vera card: a full-width textarea (84 px) and a full-width 50 px Send button, right under the greeting. This is the right first screen.
- Home, Next up: the date tile ("SUN 4 OCT"), the "Tomorrow" tag, and the drive time and who it's for. The next plan is readable in one glance at phone size.
- To do and Home to-do list: the red left rule plus "6 days late" in red, the clearest overdue signal in the set.
- Chat, conversation switcher: the Family / Maya / Theo pills scroll sideways as one row, and the page title is hidden so the thread starts high.
- Plans, "How did it go?": three 40 px face buttons per past plan, which a kid can answer with a thumb.

## Fix, ranked

**1. Navigation scrolls away and sits out of thumb reach** (all pages, `.tabbar`)
- Problem: the six-tab bar is a static block under the top bar (`.tabbar` has no `position`). On Home (about 3,030 px tall on a 390 px phone, roughly 4½ screens) or Ideas (about 3,300 px), switching section means scrolling all the way back up and then reaching to the top edge of the screen. One-handed parents and small hands get the worst of it.
- Fix: below 820 px, make the tab bar a bottom bar: `position: fixed; bottom: 0; left: 0; right: 0; padding-bottom: env(safe-area-inset-bottom); z-index: 10`, at least 56 px tall, and add `padding-bottom: 88px` to `.main`. Keep the top bar static (brand, "Vera is on", avatar). This is pure CSS and works with scripting off. If fixed positioning is not wanted, at least make the tab bar `position: sticky; top: 0`.
- Severity: major. Effort: S.

**2. Calendar events become unlabeled 8 px bars** (Plans, month grid `.ev` at ≤820 px)
- Problem: the phone CSS sets `.ev` to `font-size:0; height:8px` and `.ev * {display:none !important}`. The event links still exist, but they are about 46×8 px tap targets with no visible text, and `display:none` also removes the time and title from screen readers, so every event is an empty link. Past plans become pale grey bars that are almost invisible (29 Sep, 1 Oct). The "TODAY" label overflows the 54 px cell and squashes the "3" circle ("3 TOD" is clipped). On a phone the month view cannot answer "what's on the 17th?"
- Fix: on the phone, open Plans in the list view (or put "Coming up" directly under the month header and the grid below it). Make each whole day cell the link, at least 44 px tall, with dots for events and a visually hidden label ("Sat 17 Oct: Nutcracker at the Keller, 19:00") instead of `display:none`. Use `.sr` for the text, not `font-size:0`. Hide `.today-l` below 820 px and keep only the filled circle. Give past events a 2 px outlined dot instead of a 78%-opacity grey fill.
- Severity: blocker (accessibility: empty links). Effort: M.

**3. To-dos lose "has a reminder" on phone and on small laptops** (To do, `.trow .rem`)
- Problem: `@media (max-width:1180px) { .trow .rem {display:none} }` hides the "No reminder · Add one" cell at every width below 1180 px. The brief requires each to-do to show whether it has a reminder, and the reminders are the main reason to use To do. A 13-inch laptop at 1152 px loses it as well.
- Fix: do not hide it. On the phone, put it in the meta line after the due date as an icon and text: "🔕 No reminder · Add" or "🔔 Tue 09:00". Remove the 1180 px rule and let `.trow` wrap the meta onto a second line instead.
- Severity: major. Effort: S.

**4. The first to-do and the first idea appear a whole screen down** (To do, `.quick` form; Ideas, `.filters` and `.jot`)
- Problem: on To do, the add form (input, Who, Due, Remind, Add) plus the Telegram notice take about 690 px, and the first to-do starts at about 880 px, below the first screen. On Ideas, the "Add an idea" button, "Save a thought for later", the tabs and four stacked filters plus Show take about 800 px before "Lego set for Theo". People come to these pages to look at the list.
- Fix: To do: one row with the input and a 48 px "Add" button; put Who, Due and Remind in a `<details><summary>Who, when, reminder</summary>` below it. Shrink the Telegram notice to one line ("Reminders need Telegram. Set up ›"). Ideas: keep Search full width with a "Filters (0)" `<details>` next to it that holds Kind, Status and For in a 2-column grid plus Show. Collapse "Save a thought" into a single input row with no heading and helper text. Target: the first list item starts at ≤ 420 px from the top.
- Severity: major. Effort: M.

**5. Home on the phone puts setup and kids' wish lists at the bottom of a 4½-screen page** (Home, source order of `.home-grid`)
- Problem: on desktop "Finish setting up" is top right, beside Ask Vera. On the phone it comes after "Just added to Ideas", at about 1,900 px, and Wish lists and "Vera today" end the page at about 2,500–3,000 px. A parent finishing setup on a phone won't see it, and a kid has to scroll past adult to-dos to reach wish lists.
- Fix: phone order: Ask Vera → Next up (the first plan plus at most 2 more, and a "3 more" link) → To do (overdue only, at most 3, and an "All 4 ›" link) → Finish setting up (collapsed to one line "Setup: 3 steps left ›" after the first visit) → Wish lists (one line per kid) → Just added to Ideas (2 items as rows, not 4 cards) → Vera today. Use CSS `order` on the grid children or reorder the source. Target Home ≤ 2 screens of content below Ask Vera.
- Severity: major. Effort: M.

**6. Settings rows drop the chevron onto a separate line** (Settings, `.srow`)
- Problem: rows without a tag still output an empty `<span></span>`. At ≤820 px it lands in column 3 and pushes `.go` into column 1 of a new row. General, AI model, Spending, Lookups and What has changed each show a lone "›" under the icon, which adds about 50 px per row and makes the list look broken. Rows with a tag put the chevron at the right, so the list is inconsistent.
- Fix: in the mobile block add `.srow .go { grid-column: 3; grid-row: 1 / span 2; align-self: center; }` and `.srow > span:empty { display: none; }`, or stop outputting the empty span. Each row should end up icon | title, line and tag | › at about 76–96 px tall.
- Severity: minor (looks broken, costs scroll). Effort: S.

**7. Status table squeezed into three columns** (Status, "Which AI does each job" and Connections)
- Problem: at 390 px the Job / Answered by / Backup table breaks the model name "gpt-6-/luna" across lines and wraps "Talking with the family" over three lines. In Connections, the Telegram text wraps into a column about 130 px wide ("Not set up · the / family can't / message Vera…") beside a "Set up Telegram" button.
- Fix: below 820 px, render each job as a stacked block: "Chat · Talking with the family" / "gpt-6-luna (OpenAI)" / "Backup: None" tag. Keep model names together with `white-space: nowrap`. In Connections rows, move the action button under the text (`grid-column: 2`) so the text gets the full width.
- Severity: minor. Effort: S.

**8. Small and wrapping controls** (To do `.tick` and filter tabs, Chat "Writing as", text links)
- Problem: the done tick is 34 px, the main action on the To do page and the one kids use most. The Open / Done / Cancelled / All tabs wrap "All" onto a second line inside the pill. "Writing as" wraps "Theo" alone onto a second row. Card links such as "All plans ›", "All to-dos ›", "Look it up" and "Edit" are text-only, about 22 px tall. The Home suggestion chips row cuts "Remi…" at the card edge with no scroll cue.
- Fix: `.tick` 44 px (a 44 px hit area around a 30 px ring). Below 820 px, `.seg` becomes `display:grid; grid-template-columns: repeat(4,1fr)` with `flex-wrap:nowrap`. "Writing as" uses the same horizontal scroll row as `.convos`. Give card-head links and Edit `min-height:44px; display:inline-flex; align-items:center`. Fade the right edge of `.sugg` with a mask gradient so it is clear the row scrolls. Search to-dos field should be full width (it stops about 30 px short).
- Severity: minor. Effort: S.

**9. Chat composer is at the bottom of the page and not pinned** (Chat, `.compose`)
- Problem: with 4 messages the composer is already below the first screen (about 960 px down). In a real thread of weeks of messages, the box is far below, and the page opens at the top (oldest messages) because there is no scripting to scroll it. "Send where I am" sits under the Send button, about 1,320 px down.
- Fix: show only the newest ~30 messages with a "Earlier messages" link at the top. Make `.compose` `position: sticky; bottom: 0` (above the bottom tab bar from fix 1) with the input and Send on one row, and put "Writing as" and "Send where I am" in a `<details>` labelled "Sam · location off". Link to the chat as `chat.html#latest` with `id="latest"` on the last message so it opens at the newest message without scripting.
- Severity: major. Effort: M.

**10. Idea cards too tall for a list of 12** (Ideas, `.ideas` cards at one column)
- Problem: each card is about 150 px (kind tag, status tag, title, who, divider, drive). 12 ideas take about 1,900 px, and a real list of 40 would be 6,000 px. The "Restaurants" tab helps, but browsing is slow, and the "Not looked up yet" dashed cards take the same space.
- Fix: on the phone use a compact row of about 72 px: kind icon tile (40 px) | title (serif, 18 px) with "Theo · 18 min" below | status tag at the right. Keep full cards for the desktop. Paginate or "Show 20 more" at 20.
- Severity: minor. Effort: M.

## Missing
- The "More" page (`more.html`): Wishes, What Vera knows, Status, Settings and Family all sit behind it. A kid's own wish list is two taps deep, so Wishes should be a tab for kid accounts instead of Plans or Status.
- The kid's view of Home, the tab bar and Chat at 390 px (no Settings, own to-dos, own wish list, "Writing as" hidden).
- Long-content states: a real Chat thread (scroll position, older messages), 40+ ideas, a busy month with 3+ events in one day cell, a 40-character idea title in a 54 px calendar cell.
- Empty and first-run phone states: no plans yet, no ideas, no to-dos, and the first-time setup steps at 390 px.
- After-submit states with scripting off: what the page shows after Send on Home (does it go to Chat?), after a quick add, after ticking a to-do (scroll position kept? an "Undo" message?).
- The phone keyboard: the composer and quick-add with the on-screen keyboard open (about 50% of the screen gone), and `inputmode`, `enterkeyhint="send"` and `autocomplete` on each field.
- The narrowest phones (320–360 px) and landscape: the six-tab bar labels and the October header with two 44 px arrows plus "Today" are already tight at 390.
- Idea, plan and to-do detail and edit pages on the phone, and how "Move it" works for a plan without a desktop calendar.

## One sentence
Make the phone layout its own layout. Start with a fixed bottom tab bar and lists that start within the first screen (tools collapsed into `<details>`, calendar → list), because today the phone gets the desktop page stacked into one column.
